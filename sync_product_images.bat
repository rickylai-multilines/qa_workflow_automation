@echo off
setlocal

REM === Sync product images from network drive to local Product_images ===
REM Use UNC path (\\server\share\path) instead of Y: - mapped drives are per-session
REM and may not exist when run from Task Scheduler or other contexts.
REM If your path differs, update SOURCE below. Y: maps to \\192.168.1.108\iTrader
set SOURCE=\\192.168.1.108\iTrader\mtl\PHOTOS
set DEST=C:\apps\qa_workflow_automation\Product_images
set LOG_DIR=C:\apps\qa_workflow_automation\logs
set LOG_FILE=%LOG_DIR%\sync_product_images.log

REM Create destination if it doesn't exist
if not exist "%DEST%" mkdir "%DEST%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo === Sync start %DATE% %TIME% === >> "%LOG_FILE%"

REM Robocopy: copy only new or updated files (skip same/older)
REM /E = copy subdirectories including empty
REM /XO = exclude older (only copy if source is newer or file missing in dest)
REM /R:2 /W:5 = retry 2 times, wait 5 sec (for network glitches)
robocopy "%SOURCE%" "%DEST%" /E /XO /R:2 /W:5 /NP /NDL /NJH /NJS >> "%LOG_FILE%" 2>&1

REM Robocopy exit codes: 0-7 = success (some copied), 8+ = errors
if %ERRORLEVEL% GEQ 8 (
    echo Sync completed with errors. Exit code: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo Sync completed. Exit code: %ERRORLEVEL% >> "%LOG_FILE%"
)

echo === Sync end %DATE% %TIME% === >> "%LOG_FILE%"
endlocal
