@echo off
setlocal

REM === Configuration ===
set PROJECT_DIR=C:\apps\qa_workflow_automation
set PY32=C:\Users\erpadmin\AppData\Local\Programs\Python\Python311-32\python.exe
set VENV_ACTIVATE=%PROJECT_DIR%\venv\Scripts\activate.bat
set DSN=Fox Pro ERP
set JSON_DIR=%PROJECT_DIR%\json
set LOG_DIR=%PROJECT_DIR%\logs
set UPDATE_WINDOW_DAYS=2

set POMAIN_JSON=%JSON_DIR%\foxpro_pomain_export.ndjson
set LOG_FILE=%LOG_DIR%\sync_foxpro_pomain.log

cd /d "%PROJECT_DIR%"
if not exist "%JSON_DIR%" mkdir "%JSON_DIR%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo === POMAIN sync start %DATE% %TIME% === >> "%LOG_FILE%"

REM Export all POMAST records (FoxPro -> NDJSON)
"%PY32%" "%PROJECT_DIR%\foxpro_export_pomain.py" --dsn "%DSN%" --all --order-by po_id --format ndjson --output "%POMAIN_JSON%" >> "%LOG_FILE%" 2>&1

REM Import into Postgres:
REM - insert if missing
REM - update existing only when ModifiedByDate is within last %UPDATE_WINDOW_DAYS% days
call "%VENV_ACTIVATE%"
python manage.py import_pomain_json --path "%POMAIN_JSON%" --update-window-days %UPDATE_WINDOW_DAYS% >> "%LOG_FILE%" 2>&1

echo === POMAIN sync end %DATE% %TIME% === >> "%LOG_FILE%"

endlocal
