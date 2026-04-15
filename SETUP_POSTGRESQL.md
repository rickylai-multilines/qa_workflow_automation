# PostgreSQL Setup Guide

## Database Configuration

The project has been configured to use PostgreSQL with the following settings:
- **Host:** localhost
- **Port:** 5541
- **Database:** qa_workflow_db
- **User:** postgres
- **Password:** (configured in settings.py)

## Step 1: Create the Database

Before running migrations, you need to create the database in PostgreSQL.

### Option A: Using pgAdmin (GUI)

1. Open pgAdmin
2. Connect to your PostgreSQL server (localhost:5541)
3. Right-click on "Databases" → "Create" → "Database..."
4. Enter database name: `qa_workflow_db`
5. Click "Save"

### Option B: Using psql Command Line

1. Open Command Prompt or PowerShell
2. Connect to PostgreSQL:
   ```bash
   psql -U postgres -h localhost -p 5541
   ```
3. Enter your password when prompted: `multiL@%%$1786`
4. Create the database:
   ```sql
   CREATE DATABASE qa_workflow_db;
   ```
5. Exit psql:
   ```sql
   \q
   ```

### Option C: Using SQL Command Directly

```bash
psql -U postgres -h localhost -p 5541 -c "CREATE DATABASE qa_workflow_db;"
```

## Step 2: Install PostgreSQL Driver

Make sure `psycopg2-binary` is installed:

```bash
# Activate virtual environment first
venv\Scripts\activate

# Install PostgreSQL driver
pip install psycopg2-binary
```

If you encounter issues installing `psycopg2-binary`, you can try:
```bash
pip install psycopg2
```

## Step 3: Run Migrations

After creating the database, run migrations:

```bash
# Make sure virtual environment is activated
venv\Scripts\activate

# Run migrations
python manage.py migrate
```

## Step 4: Create Superuser

```bash
python manage.py createsuperuser
```

## Step 5: Start Server

```bash
python manage.py runserver
```

## Troubleshooting

### Connection Error: "could not connect to server"

- **Check PostgreSQL is running:** Open Services (services.msc) and verify PostgreSQL service is running
- **Check port:** Verify PostgreSQL is listening on port 5541
- **Check firewall:** Make sure port 5541 is not blocked

### Authentication Failed

- Verify the password in `qa_workflow/settings.py` matches your PostgreSQL password
- Check that the user `postgres` exists and has proper permissions

### Database Does Not Exist

- Make sure you created the database `qa_workflow_db` first (see Step 1)

### psycopg2 Installation Issues

If `psycopg2-binary` fails to install on Windows:
1. Install Microsoft Visual C++ Build Tools
2. Or use pre-compiled wheel: `pip install psycopg2-binary --only-binary :all:`
3. Or install PostgreSQL client libraries separately

## Verify Connection

Test the database connection:

```bash
python manage.py dbshell
```

If successful, you'll see the PostgreSQL prompt. Type `\q` to exit.

## Migration from SQLite to PostgreSQL

If you had data in SQLite and want to migrate:

1. Export data from SQLite:
   ```bash
   python manage.py dumpdata > data.json
   ```

2. Switch to PostgreSQL (already done in settings.py)

3. Run migrations:
   ```bash
   python manage.py migrate
   ```

4. Load data into PostgreSQL:
   ```bash
   python manage.py loaddata data.json
   ```

## Notes

- The database configuration is in `qa_workflow/settings.py`
- Never commit passwords to version control in production (use environment variables)
- For production, consider using environment variables for sensitive data


