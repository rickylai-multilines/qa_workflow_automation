@echo off
setlocal

REM === Configuration ===
set PROJECT_DIR=C:\dev\qa_workflow_automation
set PY32=C:\Users\ricky_lai\AppData\Local\Programs\Python\Python311-32\python.exe
set VENV_ACTIVATE=%PROJECT_DIR%\venv\Scripts\activate.bat
set DSN=Fox Pro ERP
set HOURS=48

set PRODUCTS_JSON=%PROJECT_DIR%\foxpro_products_export.json
set LOG_FILE=%PROJECT_DIR%\sync_foxpro_products.log

cd /d "%PROJECT_DIR%"

set MODE=%~1
if "%MODE%"=="" set MODE=incremental

echo === Products sync start %DATE% %TIME% === >> "%LOG_FILE%"
echo Mode: %MODE% >> "%LOG_FILE%"

REM Export PRODUCTS (FoxPro -> JSON)
if /I "%MODE%"=="full" (
    REM Full export: all PRODUCTS
    "%PY32%" "%PROJECT_DIR%\foxpro_export_products.py" --dsn "%DSN%" --all --order-by product_id --output "%PRODUCTS_JSON%" >> "%LOG_FILE%" 2>&1
) else (
    REM Incremental export: changed in last %HOURS% hours
    "%PY32%" "%PROJECT_DIR%\foxpro_export_products.py" --dsn "%DSN%" --since-hours %HOURS% --order-by product_id --output "%PRODUCTS_JSON%" >> "%LOG_FILE%" 2>&1
)

REM Import into Postgres (JSON -> Postgres)
call "%VENV_ACTIVATE%"
python manage.py import_products_json --path "%PRODUCTS_JSON%" >> "%LOG_FILE%" 2>&1

echo === Products sync end %DATE% %TIME% === >> "%LOG_FILE%"

endlocal
