@echo off
setlocal

set PROJECT_DIR=C:\apps\qa_workflow_automation
set VENV_ACTIVATE=%PROJECT_DIR%\venv\Scripts\activate.bat
set LOG_DIR=%PROJECT_DIR%\logs
set LOG_FILE=%LOG_DIR%\sync_wip_daily_reminder.log

cd /d "%PROJECT_DIR%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
echo === WIP Reminder start %DATE% %TIME% === >> "%LOG_FILE%"

call "%VENV_ACTIVATE%"
python manage.py send_wip_reminders >> "%LOG_FILE%" 2>&1

echo === WIP Reminder end %DATE% %TIME% === >> "%LOG_FILE%"
endlocal
