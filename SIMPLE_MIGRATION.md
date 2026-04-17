# Simple SQLite to PostgreSQL Migration

## Method 1: Manual Steps (Most Reliable)

### Step 1: Export from SQLite

**Temporarily switch settings.py to SQLite:**

Edit `qa_workflow/settings.py` and change the DATABASES section to:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

**Then export data:**

```bash
cd C:\dev\qa_workflow_automation
venv\Scripts\activate
python manage.py dumpdata --natural-foreign --natural-primary > data_export.json
```

### Step 2: Switch Back to PostgreSQL

Edit `qa_workflow/settings.py` and change back to PostgreSQL (already configured):

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'qa_workflow_db',
        'USER': 'postgres',
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': 'localhost',
        'PORT': '5541',
    }
}
```

### Step 3: Run Migrations on PostgreSQL

```bash
python manage.py migrate
```

### Step 4: Load Data

```bash
python manage.py loaddata data_export.json
```

### Step 5: Verify

```bash
python manage.py runserver
```

Visit http://127.0.0.1:8000/admin/ to verify your data.

---

## Method 2: Using Python Script

Create a file `export_sqlite.py`:

```python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qa_workflow.settings')
django.setup()

# Temporarily switch to SQLite
from django.conf import settings
settings.DATABASES['default'] = {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': os.path.join(os.path.dirname(__file__), 'db.sqlite3'),
}

# Close all connections
from django.db import connections
connections.close_all()

# Export
from django.core.management import call_command
with open('data_export.json', 'w') as f:
    call_command('dumpdata', '--natural-foreign', '--natural-primary', stdout=f)

print("Export complete! Now switch back to PostgreSQL and run: python manage.py loaddata data_export.json")
```

Run it:
```bash
python export_sqlite.py
```

Then switch back to PostgreSQL and load:
```bash
python manage.py migrate
python manage.py loaddata data_export.json
```

---

## Quick Check

After migration, verify data:

```bash
python manage.py shell
```

```python
from qa_app.models import Product
print(f"Products count: {Product.objects.count()}")
```


