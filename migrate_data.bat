@echo off
setlocal
set PROJECT_DIR=%~dp0
if "%PROJECT_DIR:~-1%"=="\" set PROJECT_DIR=%PROJECT_DIR:~0,-1%
set JSON_DIR=%PROJECT_DIR%\json
set LOG_DIR=%PROJECT_DIR%\logs
set EXPORT_JSON=%JSON_DIR%\data_export.json
set LOG_FILE=%LOG_DIR%\migrate_data.log

if not exist "%JSON_DIR%" mkdir "%JSON_DIR%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

cd /d "%PROJECT_DIR%"

echo ========================================
echo SQLite to PostgreSQL Migration
echo ========================================
echo.

echo Step 1: Exporting data from SQLite...
echo Temporarily switching to SQLite in settings.py...
echo.

REM Create a backup of current settings
copy qa_workflow\settings.py qa_workflow\settings_postgresql.py.bak

REM Create SQLite settings temporarily
python -c "import os; content = open('qa_workflow/settings.py', 'r', encoding='utf-8').read(); content = content.replace('django.db.backends.postgresql', 'django.db.backends.sqlite3'); content = content.replace(\"NAME': 'qa_workflow_db',\", \"NAME': BASE_DIR / 'db.sqlite3',\"); open('qa_workflow/settings.py', 'w', encoding='utf-8').write(content)"

echo Exporting data...
python manage.py dumpdata --natural-foreign --natural-primary > "%EXPORT_JSON%" 2>> "%LOG_FILE%"

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to export data
    REM Restore settings
    copy qa_workflow\settings_postgresql.py.bak qa_workflow\settings.py
    pause
    exit /b 1
)

echo.
echo Step 2: Restoring PostgreSQL settings...
copy qa_workflow\settings_postgresql.py.bak qa_workflow\settings.py

echo.
echo Step 3: Running migrations on PostgreSQL...
python manage.py migrate

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Migrations failed
    pause
    exit /b 1
)

echo.
echo Step 4: Loading data into PostgreSQL...
python manage.py loaddata "%EXPORT_JSON%" >> "%LOG_FILE%" 2>&1

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to load data
    pause
    exit /b 1
)

echo.
echo ========================================
echo Migration completed successfully!
echo ========================================
echo.
echo Next steps:
echo 1. Test: python manage.py runserver
echo 2. Check admin: http://127.0.0.1:8000/admin/
echo.
pause
endlocal
