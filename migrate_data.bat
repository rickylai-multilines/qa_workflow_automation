@echo off
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
python manage.py dumpdata --natural-foreign --natural-primary > data_export.json

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
python manage.py loaddata data_export.json

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


