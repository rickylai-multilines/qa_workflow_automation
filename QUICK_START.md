# Quick Start Guide - Preview the System

## Option 1: Quick Preview with SQLite (No PostgreSQL needed)

### Step 1: Navigate to Project Directory
```bash
cd C:\dev\qa_workflow_automation
```

### Step 2: Create Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

**Note:** If you get an error installing `psycopg2-binary`, you can skip it for SQLite preview:
```bash
pip install Django>=4.2 Pillow>=10.0.0 openpyxl>=3.1.0 python-dateutil>=2.8.0
```

### Step 4: Use SQLite Settings (Temporary)
Rename the settings file temporarily:
```bash
# Backup original settings
copy qa_workflow\settings.py qa_workflow\settings_postgresql.py

# Use SQLite settings
copy qa_workflow\settings_sqlite.py qa_workflow\settings.py
```

Or manually edit `qa_workflow/settings.py` and change the DATABASES section to:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

### Step 5: Run Migrations
```bash
python manage.py migrate
```

### Step 6: Create Superuser
```bash
python manage.py createsuperuser
```
Enter username, email (optional), and password when prompted.

### Step 7: Start Development Server
```bash
python manage.py runserver
```

### Step 8: Access the System
Open your web browser and go to:
- **Admin Interface:** http://127.0.0.1:8000/admin/
- **Dashboard:** http://127.0.0.1:8000/

Login with the superuser credentials you created.

---

## Option 2: Full Setup with PostgreSQL

### Prerequisites
- PostgreSQL 14+ installed and running
- Database `qa_workflow_db` created

### Steps
1. Follow Steps 1-3 from Option 1
2. Edit `qa_workflow/settings.py` and update database credentials:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': 'qa_workflow_db',
           'USER': 'postgres',
           'PASSWORD': 'your_password',
           'HOST': 'localhost',
           'PORT': '5432',
       }
   }
   ```
3. Follow Steps 5-8 from Option 1

---

## What You'll See

### Admin Interface (http://127.0.0.1:8000/admin/)
- Login with superuser credentials
- Access to all models:
  - Products
  - Product Stages
  - Compliance Documents
  - Test Requirements
  - ERP Orders & Shipments

### Dashboard (http://127.0.0.1:8000/)
- QA owner dashboard
- Product list view
- Product detail view

---

## Create Sample Data

After logging into admin:
1. Go to **Products** → **Add Product**
2. Fill in required fields (BMUK Item No., MTL Ref NO., Description, etc.)
3. Save - this will automatically create the 5 QA stages (R/A/F/M/G)
4. You can then add compliance documents and test requirements

---

## Troubleshooting

**Import Error for psycopg2:**
- For quick preview, use SQLite (Option 1)
- Or install PostgreSQL and psycopg2-binary

**Port already in use:**
```bash
python manage.py runserver 8001
```

**Migration errors:**
```bash
python manage.py makemigrations
python manage.py migrate
```

---

## Next Steps

Once previewed, you can:
- Import data from Excel using: `python manage.py import_excel file.xlsx`
- Customize the models and views
- Set up PostgreSQL for production
- Deploy to Windows Server


