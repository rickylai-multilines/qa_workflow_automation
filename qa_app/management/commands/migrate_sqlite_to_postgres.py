"""
Management command to migrate data from SQLite to PostgreSQL
"""
import os
import json
import subprocess
import sys
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from django.db import connections


class Command(BaseCommand):
    help = 'Migrate data from SQLite database to PostgreSQL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sqlite-db',
            type=str,
            default='db.sqlite3',
            help='Path to SQLite database file (default: db.sqlite3)'
        )
        parser.add_argument(
            '--backup',
            action='store_true',
            help='Create backup of SQLite database before migration'
        )

    def handle(self, *args, **options):
        sqlite_db = options['sqlite_db']
        backup = options['backup']

        # Check if SQLite database exists
        if not os.path.exists(sqlite_db):
            self.stdout.write(
                self.style.ERROR(f'SQLite database not found: {sqlite_db}')
            )
            self.stdout.write(
                self.style.WARNING('If you want to start fresh, just run: python manage.py migrate')
            )
            return

        self.stdout.write(self.style.SUCCESS('Starting migration from SQLite to PostgreSQL...'))
        self.stdout.write('')

        # Step 1: Backup SQLite database if requested
        if backup:
            backup_file = f'{sqlite_db}.backup'
            import shutil
            shutil.copy2(sqlite_db, backup_file)
            self.stdout.write(self.style.SUCCESS(f'✓ Backup created: {backup_file}'))

        # Step 2: Close all database connections
        self.stdout.write('Step 1: Closing database connections...')
        connections.close_all()
        self.stdout.write(self.style.SUCCESS('✓ Connections closed'))

        # Step 3: Export data from SQLite using subprocess
        self.stdout.write('')
        self.stdout.write('Step 2: Exporting data from SQLite...')
        
        export_file = 'data_export.json'
        
        # Create a temporary settings file for SQLite export
        temp_settings = self._create_temp_settings_for_sqlite(sqlite_db)
        
        try:
            # Use subprocess to run dumpdata with SQLite settings
            self.stdout.write('  Running dumpdata command...')
            result = subprocess.run(
                [
                    sys.executable,
                    'manage.py',
                    'dumpdata',
                    '--natural-foreign',
                    '--natural-primary',
                    '--settings',
                    temp_settings,
                    '--output',
                    export_file
                ],
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            
            if result.returncode != 0:
                raise Exception(f'Dumpdata failed: {result.stderr}')
            
            # Check file size
            if not os.path.exists(export_file):
                raise Exception('Export file was not created')
                
            file_size = os.path.getsize(export_file)
            if file_size == 0:
                self.stdout.write(
                    self.style.WARNING('No data found in SQLite database. Starting fresh.')
                )
                os.remove(export_file)
                if os.path.exists(temp_settings):
                    os.remove(temp_settings)
                return
            
            self.stdout.write(self.style.SUCCESS(f'✓ Data exported to: {export_file}'))
            self.stdout.write(f'  File size: {file_size:,} bytes')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error exporting data: {str(e)}')
            )
            if os.path.exists(temp_settings):
                os.remove(temp_settings)
            return

        # Step 3: Clean up temp settings
        if os.path.exists(temp_settings):
            os.remove(temp_settings)

        # Step 4: Verify PostgreSQL connection
        self.stdout.write('')
        self.stdout.write('Step 3: Verifying PostgreSQL connection...')
        try:
            connections.close_all()
            from django.db import connection
            connection.ensure_connection()
            self.stdout.write(self.style.SUCCESS('✓ PostgreSQL connection successful'))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'PostgreSQL connection failed: {str(e)}')
            )
            self.stdout.write('Please check your database settings in qa_workflow/settings.py')
            return

        # Step 5: Run migrations on PostgreSQL
        self.stdout.write('')
        self.stdout.write('Step 4: Running migrations on PostgreSQL...')
        try:
            call_command('migrate', verbosity=0)
            self.stdout.write(self.style.SUCCESS('✓ Migrations completed'))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Migration failed: {str(e)}')
            )
            return

        # Step 6: Load data into PostgreSQL
        self.stdout.write('')
        self.stdout.write('Step 5: Loading data into PostgreSQL...')
        try:
            call_command('loaddata', export_file, verbosity=1)
            self.stdout.write(self.style.SUCCESS('✓ Data loaded successfully'))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error loading data: {str(e)}')
            )
            self.stdout.write('You may need to manually fix data conflicts')
            return

        # Step 7: Cleanup
        self.stdout.write('')
        self.stdout.write('Step 6: Cleaning up...')
        
        # Ask if user wants to keep export file
        keep_export = input('Keep export file (data_export.json)? [y/N]: ').lower() == 'y'
        if not keep_export:
            os.remove(export_file)
            self.stdout.write('✓ Export file removed')
        else:
            self.stdout.write(f'✓ Export file kept: {export_file}')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('Migration completed successfully!'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write('')
        self.stdout.write('Next steps:')
        self.stdout.write('1. Test your application: python manage.py runserver')
        self.stdout.write('2. Verify data in admin: http://127.0.0.1:8000/admin/')
        self.stdout.write('3. Once verified, you can delete the SQLite database if desired')

    def _create_temp_settings_for_sqlite(self, sqlite_db_path):
        """Create a temporary settings module for SQLite export"""
        import tempfile
        
        # Read original settings
        settings_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                     'qa_workflow', 'settings.py')
        
        with open(settings_file, 'r', encoding='utf-8') as f:
            settings_content = f.read()
        
        # Replace database config with SQLite
        sqlite_config = f"""DATABASES = {{
    'default': {{
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': r'{os.path.abspath(sqlite_db_path).replace(chr(92), chr(92)+chr(92))}',
    }}
}}"""
        
        # Find and replace DATABASES section
        import re
        pattern = r'DATABASES\s*=\s*\{[^}]+\{[^}]+\}[^}]+\}'
        settings_content = re.sub(pattern, sqlite_config, settings_content, flags=re.DOTALL)
        
        # Write to temp file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
        temp_file.write(settings_content)
        temp_file.close()
        
        return temp_file.name

