# Virtual Environment Guide for Windows

## What is a Virtual Environment?

A virtual environment is an isolated Python environment that allows you to install packages specific to your project without affecting other Python projects or your system Python installation.

## Step-by-Step Guide

### Step 1: Open Command Prompt or PowerShell

- Press `Win + R`, type `cmd` or `powershell`, and press Enter
- Or right-click in the project folder and select "Open in Terminal" / "Open PowerShell window here"

### Step 2: Navigate to Your Project Directory

```bash
cd C:\dev\qa_workflow_automation
```

### Step 3: Create Virtual Environment

```bash
python -m venv venv
```

This creates a folder named `venv` in your project directory.

**Alternative if you have multiple Python versions:**
```bash
python3 -m venv venv
# or
py -3.9 -m venv venv
```

### Step 4: Activate the Virtual Environment

**For Command Prompt (cmd):**
```bash
venv\Scripts\activate.bat
```

**For PowerShell:**
```bash
venv\Scripts\Activate.ps1
```

**If you get an execution policy error in PowerShell, run:**
```bash
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**For Git Bash:**
```bash
source venv/Scripts/activate
```

### Step 5: Verify Activation

When activated, you should see `(venv)` at the beginning of your command prompt:

```
(venv) C:\dev\qa_workflow_automation>
```

### Step 6: Install Dependencies

```bash
pip install -r requirements.txt
```

Or install individually:
```bash
pip install Django>=4.2 Pillow>=10.0.0 openpyxl>=3.1.0 python-dateutil>=2.8.0
```

### Step 7: Run Your Django Project

```bash
# Run migrations
python manage.py migrate

# Create superuser (first time only)
python manage.py createsuperuser

# Start the development server
python manage.py runserver
```

### Step 8: Deactivate (When Done)

When you're finished working, deactivate the virtual environment:

```bash
deactivate
```

The `(venv)` prefix will disappear from your prompt.

---

## Quick Reference Commands

| Action | Command |
|--------|---------|
| Create venv | `python -m venv venv` |
| Activate (cmd) | `venv\Scripts\activate.bat` |
| Activate (PowerShell) | `venv\Scripts\Activate.ps1` |
| Install packages | `pip install -r requirements.txt` |
| Deactivate | `deactivate` |
| Check Python version | `python --version` |
| List installed packages | `pip list` |

---

## Troubleshooting

### "python is not recognized"
- Make sure Python is installed and added to PATH
- Try `py` instead of `python`
- Check installation: `py --version`

### "Execution Policy" error in PowerShell
```bash
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Virtual environment not activating
- Make sure you're in the project directory
- Check that `venv` folder exists
- Try using full path: `C:\dev\qa_workflow_automation\venv\Scripts\activate`

### Packages not installing
- Make sure virtual environment is activated (see `(venv)` prefix)
- Upgrade pip: `python -m pip install --upgrade pip`
- Try: `pip install --upgrade pip setuptools wheel`

---

## Best Practices

1. **Always activate** the virtual environment before working on the project
2. **Never commit** the `venv` folder to version control (it's in .gitignore)
3. **Recreate venv** if you move the project to a different computer
4. **Keep requirements.txt updated**: `pip freeze > requirements.txt`

---

## Visual Guide

```
C:\dev\qa_workflow_automation> python -m venv venv
C:\dev\qa_workflow_automation> venv\Scripts\activate.bat
(venv) C:\dev\qa_workflow_automation> pip install -r requirements.txt
(venv) C:\dev\qa_workflow_automation> python manage.py migrate
(venv) C:\dev\qa_workflow_automation> python manage.py runserver
... server running ...
(venv) C:\dev\qa_workflow_automation> deactivate
C:\dev\qa_workflow_automation>
```


