# Migrate Data from SQLite to PostgreSQL

This guide will help you migrate your existing SQLite data to PostgreSQL.

## Prerequisites

1. ✅ PostgreSQL database `qa_workflow_db` is created
2. ✅ PostgreSQL connection is configured in `settings.py`
3. ✅ SQLite database file (`db.sqlite3`) exists in your project directory

## Method 1: Automated Migration (Recommended)

### Step 1: Make sure PostgreSQL is ready

```bash
# Activate virtual environment
cd C:\dev\qa_workflow_automation
venv\Scripts\activate

# Verify PostgreSQL connection
python manage.py dbshell
# Type \q to exit if connection works
```

### Step 2: Run the migration command

```bash
# Run automated migration (creates backup automatically)
python manage.py migrate_sqlite_to_postgres --backup

# Or without backup
python manage.py migrate_sqlite_to_postgres
```

The command will:
1. ✅ Create backup of SQLite database (if --backup flag used)
2. ✅ Export all data from SQLite to JSON file
3. ✅ Verify PostgreSQL connection
4. ✅ Run migrations on PostgreSQL
5. ✅ Load data into PostgreSQL
6. ✅ Clean up temporary files

---

## Method 2: Manual Migration

### Step 1: Export data from SQLite

First, temporarily switch back to SQLite in `settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

Then export the data:

```bash
# Activate virtual environment
venv\Scripts\activate

# Export all data to JSON
python manage.py dumpdata --natural-foreign --natural-primary > data_export.json
```

### Step 2: Switch to PostgreSQL

Update `settings.py` back to PostgreSQL (already done):

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

### Step 3: Run migrations on PostgreSQL

```bash
# Make sure PostgreSQL database exists first
python manage.py migrate
```

### Step 4: Load data into PostgreSQL

```bash
python manage.py loaddata data_export.json
```

### Step 5: Verify migration

```bash
# Start server and check admin
python manage.py runserver
```

Visit http://127.0.0.1:8000/admin/ and verify your data is there.

---

## Troubleshooting

### Error: "No such table" during export

This means your SQLite database is empty or doesn't exist. You can start fresh:

```bash
# Just run migrations on PostgreSQL
python manage.py migrate
python manage.py createsuperuser
```

### Error: "Duplicate key" during loaddata

This usually means:
- Data already exists in PostgreSQL
- Primary keys conflict

**Solution:** Clear PostgreSQL database first (if starting fresh):

```sql
-- Connect to PostgreSQL
psql -U postgres -h localhost -p 5541 -d qa_workflow_db

-- Drop all tables (WARNING: This deletes all data!)
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;

-- Exit
\q
```

Then run migrations again:
```bash
python manage.py migrate
python manage.py loaddata data_export.json
```

### Error: "Connection refused" or "could not connect"

- Check PostgreSQL is running
- Verify port 5541 is correct
- Check password in settings.py
- Verify database `qa_workflow_db` exists

### Error: Foreign key constraint violations

The `--natural-foreign` and `--natural-primary` flags should handle this, but if you still get errors:

1. Export without natural keys first
2. Manually fix the JSON file
3. Or clear and recreate the database

---

## Verification Checklist

After migration, verify:

- [ ] All products are visible in admin
- [ ] Product stages are linked correctly
- [ ] Compliance documents are attached
- [ ] Test requirements are associated
- [ ] User accounts are migrated
- [ ] No data is missing

---

## Cleanup

After successful migration:

1. **Keep SQLite backup** (recommended for safety):
   ```bash
   # SQLite file is at: db.sqlite3
   # Keep it as backup for now
   ```

2. **Remove export file** (optional):
   ```bash
   del data_export.json
   ```

3. **Remove SQLite database** (only after confirming everything works):
   ```bash
   del db.sqlite3
   ```

---

## Notes

- The migration preserves all relationships between models
- User passwords are preserved (hashed)
- File uploads (images, documents) need to be copied manually if stored outside database
- Media files in `media/` folder should work automatically

---

## Need Help?

If you encounter issues:
1. Check the error message carefully
2. Verify PostgreSQL connection: `python manage.py dbshell`
3. Check that database exists: `psql -U postgres -h localhost -p 5541 -l`
4. Review the migration command output for specific errors


