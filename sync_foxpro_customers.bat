@echo off
setlocal

REM === Configuration ===
set PROJECT_DIR=C:\dev\qa_workflow_automation
set PY32=C:\Users\ricky_lai\AppData\Local\Programs\Python\Python311-32\python.exe
set VENV_ACTIVATE=%PROJECT_DIR%\venv\Scripts\activate.bat
set DSN=Fox Pro ERP
set HOURS=48

set CUSTOMERS_JSON=%PROJECT_DIR%\foxpro_customers_export.json
set LOG_FILE=%PROJECT_DIR%\sync_foxpro_customers.log

cd /d "%PROJECT_DIR%"

echo === Customers sync start %DATE% %TIME% === >> "%LOG_FILE%"

REM Export updated CUSTOMER (FoxPro -> JSON)
"%PY32%" "%PROJECT_DIR%\foxpro_export_customers.py" --dsn "%DSN%" --since-hours %HOURS% --order-by customer_id --output "%CUSTOMERS_JSON%" >> "%LOG_FILE%" 2>&1

REM Import into Postgres (JSON -> Postgres)
call "%VENV_ACTIVATE%"
python manage.py import_customers_json --path "%CUSTOMERS_JSON%" >> "%LOG_FILE%" 2>&1

echo === Customers sync end %DATE% %TIME% === >> "%LOG_FILE%"

endlocal
