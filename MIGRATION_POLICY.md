# Migration Policy (Local + Server)

This project uses a strict migration policy to avoid migration conflicts between local and server environments.

## Rules

1. **Create migrations only on local development machine**
   - Do not run `makemigrations` on the server during normal deployment.
2. **Commit migration files to GitHub**
   - Always include new files under `orders/migrations/` (or other app migrations) in your commit.
3. **Server only runs `migrate`**
   - Deployment server should apply committed migrations, not generate new ones.

## Standard local workflow

```bash
python manage.py makemigrations
python manage.py migrate
git add .
git commit -m "Add migration for <change>"
git push origin main
```

## Standard server workflow

```bash
git pull --ff-only origin main
python manage.py migrate
```

## Deployment guardrail

`deploy.ps1` now runs:

```bash
python manage.py makemigrations --check --dry-run
```

before `migrate`.

- If model changes exist without migration files, deployment fails early.
- This prevents server-generated migrations and keeps environments aligned.

## Emergency only

If you must bypass the check temporarily:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\deploy.ps1 -SkipMigrationCheck
```

Then create/fix migration files in local and push properly as soon as possible.
