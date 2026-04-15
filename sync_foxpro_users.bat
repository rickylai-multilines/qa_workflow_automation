@echo off
setlocal

REM === Configuration ===
set PROJECT_DIR=C:\dev\qa_workflow_automation
set PY32=C:\Users\ricky_lai\AppData\Local\Programs\Python\Python311-32\python.exe
set VENV_ACTIVATE=%PROJECT_DIR%\venv\Scripts\activate.bat
set DSN=Fox Pro ERP
set HOURS=48

set USERS_JSON=%PROJECT_DIR%\foxpro_users_export.json
set LOG_FILE=%PROJECT_DIR%\sync_foxpro_users.log

cd /d "%PROJECT_DIR%"

echo === Users sync start %DATE% %TIME% === >> "%LOG_FILE%"

REM Export updated USERS (FoxPro -> JSON)
"%PY32%" "%PROJECT_DIR%\foxpro_export_users.py" --dsn "%DSN%" --since-hours %HOURS% --order-by employee_id --output "%USERS_JSON%" >> "%LOG_FILE%" 2>&1

REM Import into Postgres (JSON -> Postgres)
call "%VENV_ACTIVATE%"
python manage.py import_users_json --path "%USERS_JSON%" >> "%LOG_FILE%" 2>&1

echo === Users sync end %DATE% %TIME% === >> "%LOG_FILE%"

endlocal
