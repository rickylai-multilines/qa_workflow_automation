@echo off
setlocal

REM === Configuration ===
set PROJECT_DIR=C:\apps\qa_workflow_automation
set PY32=C:\Users\erpadmin\AppData\Local\Programs\Python\Python311-32\python.exe
set VENV_ACTIVATE=%PROJECT_DIR%\venv\Scripts\activate.bat
set DSN=Fox Pro ERP
set HOURS=48
set JSON_DIR=%PROJECT_DIR%\json
set LOG_DIR=%PROJECT_DIR%\logs

set SUPPLIERS_JSON=%JSON_DIR%\foxpro_suppliers_export.json
set LOG_FILE=%LOG_DIR%\sync_foxpro_suppliers.log

cd /d "%PROJECT_DIR%"
if not exist "%JSON_DIR%" mkdir "%JSON_DIR%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

set MODE=%~1
if "%MODE%"=="" set MODE=incremental

echo === Suppliers sync start %DATE% %TIME% === >> "%LOG_FILE%"
echo Mode: %MODE% >> "%LOG_FILE%"

REM Export updated SUPPLIER (FoxPro -> JSON)
if /I "%MODE%"=="full" (
    REM Full export: all SUPPLIER rows
    "%PY32%" "%PROJECT_DIR%\foxpro_export_suppliers.py" --dsn "%DSN%" --all --order-by supplier_id --output "%SUPPLIERS_JSON%" >> "%LOG_FILE%" 2>&1
) else (
    REM Incremental export: changed in last %HOURS% hours
    "%PY32%" "%PROJECT_DIR%\foxpro_export_suppliers.py" --dsn "%DSN%" --since-hours %HOURS% --order-by supplier_id --output "%SUPPLIERS_JSON%" >> "%LOG_FILE%" 2>&1
)

REM Import into Postgres (JSON -> Postgres)
call "%VENV_ACTIVATE%"
python manage.py import_suppliers_json --path "%SUPPLIERS_JSON%" >> "%LOG_FILE%" 2>&1

echo === Suppliers sync end %DATE% %TIME% === >> "%LOG_FILE%"

endlocal
