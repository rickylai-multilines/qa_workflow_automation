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

set SOMAIN_JSON=%JSON_DIR%\foxpro_somain_export.json
set SODETAIL_JSON=%JSON_DIR%\foxpro_sodetail_export.json
set LOG_FILE=%LOG_DIR%\sync_foxpro_hourly.log

cd /d "%PROJECT_DIR%"
if not exist "%JSON_DIR%" mkdir "%JSON_DIR%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo === Sync start %DATE% %TIME% === >> "%LOG_FILE%"

REM Export updated SOMAST (FoxPro -> JSON)
"%PY32%" "%PROJECT_DIR%\foxpro_export_somain.py" --dsn "%DSN%" --since-hours %HOURS% --order-by so_id --output "%SOMAIN_JSON%" >> "%LOG_FILE%" 2>&1

REM Export updated SODTL (FoxPro -> JSON)
"%PY32%" "%PROJECT_DIR%\foxpro_export_sodetail.py" --dsn "%DSN%" --since-hours %HOURS% --order-by so_id --output "%SODETAIL_JSON%" >> "%LOG_FILE%" 2>&1

REM Import into Postgres (JSON -> Postgres)
call "%VENV_ACTIVATE%"
python manage.py import_somain_json --path "%SOMAIN_JSON%" >> "%LOG_FILE%" 2>&1
python manage.py import_sodetail_json --path "%SODETAIL_JSON%" >> "%LOG_FILE%" 2>&1
python manage.py sync_wip_orders >> "%LOG_FILE%" 2>&1

echo === Sync end %DATE% %TIME% === >> "%LOG_FILE%"

endlocal
