@echo off
setlocal

REM === Configuration ===
set PROJECT_DIR=C:\apps\qa_workflow_automation
set PY32=C:\Users\erpadmin\AppData\Local\Programs\Python\Python311-32\python.exe
set VENV_ACTIVATE=%PROJECT_DIR%\venv\Scripts\activate.bat
set DSN=Fox Pro ERP
set HOURS=48

set SUPPLIERS_JSON=%PROJECT_DIR%\foxpro_suppliers_export.json
set LOG_FILE=%PROJECT_DIR%\sync_foxpro_suppliers.log

cd /d "%PROJECT_DIR%"

echo === Suppliers sync start %DATE% %TIME% === >> "%LOG_FILE%"

REM Export updated SUPPLIER (FoxPro -> JSON)
"%PY32%" "%PROJECT_DIR%\foxpro_export_suppliers.py" --dsn "%DSN%" --since-hours %HOURS% --order-by supplier_id --output "%SUPPLIERS_JSON%" >> "%LOG_FILE%" 2>&1

REM Import into Postgres (JSON -> Postgres)
call "%VENV_ACTIVATE%"
python manage.py import_suppliers_json --path "%SUPPLIERS_JSON%" >> "%LOG_FILE%" 2>&1

echo === Suppliers sync end %DATE% %TIME% === >> "%LOG_FILE%"

endlocal
