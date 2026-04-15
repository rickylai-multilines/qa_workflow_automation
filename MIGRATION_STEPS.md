# Step-by-Step Migration Guide

## Current Status
Settings are switched to SQLite. We need to:
1. Run migrations on SQLite (to create tables)
2. Export data
3. Switch back to PostgreSQL
4. Run migrations on PostgreSQL
5. Load data

## Step 1: Run Migrations on SQLite

```bash
cd C:\dev\qa_workflow_automation
venv\Scripts\activate
python manage.py migrate
```

This will create all the tables in SQLite.

## Step 2: Export Data from SQLite

```bash
python manage.py dumpdata --natural-foreign --natural-primary > data_export.json
```

## Step 3: Switch Back to PostgreSQL

I'll help you switch settings.py back to PostgreSQL after export.

## Step 4: Run Migrations on PostgreSQL

```bash
python manage.py migrate
```

## Step 5: Load Data into PostgreSQL

```bash
python manage.py loaddata data_export.json
```

## Step 6: Verify

```bash
python manage.py runserver
```

Visit http://127.0.0.1:8000/admin/ to verify your data.


