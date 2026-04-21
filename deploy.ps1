param(
    [string]$ProjectPath = "C:\apps\qa_workflow_automation",
    [string]$Branch = "main",
    [string]$VenvPath = ".\venv",
    [string]$ServiceName = "",
    [switch]$SkipPip,
    [switch]$SkipMigrate,
    [switch]$SkipCollectstatic,
    [switch]$SkipRestart
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Invoke-Checked {
    param([string]$Command)
    Write-Host "PS> $Command"
    Invoke-Expression $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE: $Command"
    }
}

Write-Step "Starting deployment"
Write-Host "ProjectPath: $ProjectPath"
Write-Host "Branch:      $Branch"
Write-Host "VenvPath:    $VenvPath"
Write-Host "ServiceName: $ServiceName"

if (-not (Test-Path $ProjectPath)) {
    throw "Project path not found: $ProjectPath"
}

Set-Location $ProjectPath

Write-Step "Checking git working tree"
$status = git status --porcelain
if ($status) {
    throw "Working tree is not clean. Commit/stash/revert changes before deploy."
}

Write-Step "Pull latest code from GitHub"
Invoke-Checked "git fetch origin"
Invoke-Checked "git checkout $Branch"
Invoke-Checked "git pull --ff-only origin $Branch"

$venvActivate = Join-Path $VenvPath "Scripts\Activate.ps1"
if (-not (Test-Path $venvActivate)) {
    throw "Virtual environment activation script not found: $venvActivate"
}

Write-Step "Activating virtual environment"
. $venvActivate

if (-not $SkipPip) {
    Write-Step "Installing/updating Python dependencies"
    Invoke-Checked "python -m pip install --upgrade pip"
    Invoke-Checked "pip install -r requirements.txt"
}

if (-not $SkipMigrate) {
    Write-Step "Running Django migrations"
    Invoke-Checked "python manage.py migrate"
}

if (-not $SkipCollectstatic) {
    Write-Step "Collecting static files"
    Invoke-Checked "python manage.py collectstatic --noinput"
}

Write-Step "Running Django system checks"
Invoke-Checked "python manage.py check"

if (-not $SkipRestart -and $ServiceName) {
    Write-Step "Restarting Windows service: $ServiceName"
    Restart-Service -Name $ServiceName -Force
    Start-Sleep -Seconds 2
    $svc = Get-Service -Name $ServiceName
    if ($svc.Status -ne "Running") {
        throw "Service '$ServiceName' is not running after restart."
    }
    Write-Host "Service status: $($svc.Status)" -ForegroundColor Green
} elseif (-not $SkipRestart -and -not $ServiceName) {
    Write-Step "Skipping service restart (no service name provided)"
    Write-Host "Provide -ServiceName <name> to restart automatically."
}

Write-Step "Deployment completed successfully"
Invoke-Checked "git log -1 --oneline"
