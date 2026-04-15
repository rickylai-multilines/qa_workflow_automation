import datetime
import json

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils import timezone

from orders.models import FoxUser, Department, UserProfile

FIELD_MAP = {
    'employee_id': 'user_id',
    'first_name': 'user_name',
    'password': 'password',
    'adate': 'mod_time',
    'divi': 'department_id',
    'depthead': 'department_user_level',
}

DATETIME_FIELDS = {
    'mod_time',
}


def _sanitize_text(value):
    if value is None:
        return None
    text = str(value)
    if '\x00' in text:
        text = text.replace('\x00', '')
    return text.strip() if text else text


def _parse_datetime(value):
    if value is None or value == '':
        return None
    if isinstance(value, datetime.datetime):
        if timezone.is_naive(value):
            return timezone.make_aware(value)
        return value
    if isinstance(value, datetime.date):
        dt = datetime.datetime.combine(value, datetime.time.min)
        return timezone.make_aware(dt)
    text = str(value).strip()
    if not text:
        return None
    try:
        dt = datetime.datetime.fromisoformat(text)
        return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
    except ValueError:
        pass
    for fmt in ('%Y/%m/%d %H:%M', '%Y/%m/%d %H:%M:%S', '%Y-%m-%d %H:%M:%S'):
        try:
            dt = datetime.datetime.strptime(text, fmt)
            return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
        except ValueError:
            continue
    try:
        excel_serial = float(text)
        base = datetime.datetime(1899, 12, 30)
        dt = base + datetime.timedelta(days=excel_serial)
        return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
    except ValueError:
        return None


def _split_user_datetime(value):
    if value is None:
        return None, None
    if isinstance(value, (datetime.datetime, datetime.date)):
        return _parse_datetime(value), None
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return None, None
        parts = trimmed.split()
        if len(parts) >= 3:
            user = parts[-1]
            time_str = " ".join(parts[:-1])
            parsed_time = _parse_datetime(time_str)
            if parsed_time:
                return parsed_time, user
        parsed_time = _parse_datetime(trimmed)
        return parsed_time, None
    return None, None


class Command(BaseCommand):
    help = "Import USERS JSON export into PostgreSQL User table."

    def add_arguments(self, parser):
        parser.add_argument('--path', required=True)

    def handle(self, *args, **options):
        path = options['path']
        try:
            with open(path, 'r', encoding='utf-8') as f:
                rows = json.load(f)
        except FileNotFoundError as exc:
            raise CommandError(f"File not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON: {exc}") from exc

        if not isinstance(rows, list):
            raise CommandError("JSON must be a list of rows.")

        created_count = 0
        updated_count = 0

        for row in rows:
            mapped = {}
            mod_time, mod_by = _split_user_datetime(row.get('adate'))
            for source_field, target_field in FIELD_MAP.items():
                value = row.get(source_field)
                if target_field == 'mod_time':
                    value = mod_time
                if target_field in DATETIME_FIELDS:
                    value = _parse_datetime(value)
                elif isinstance(value, str):
                    value = _sanitize_text(value)
                mapped[target_field] = value

            if mod_by:
                mapped['mod_by'] = _sanitize_text(mod_by)

            user_id = _sanitize_text(mapped.pop('user_id', None))
            if not user_id:
                continue

            obj, created = FoxUser.objects.update_or_create(
                user_id=user_id,
                defaults=mapped,
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

            department_id = _sanitize_text(mapped.get('department_id'))
            if department_id:
                level = (_sanitize_text(mapped.get('department_user_level')) or 'NORMAL').upper()
                first_name = _sanitize_text(mapped.get('user_name')) or ''
                password = _sanitize_text(mapped.get('password')) or ''

                auth_user, _ = User.objects.get_or_create(username=user_id)
                auth_user.first_name = first_name
                auth_user.is_active = True
                auth_user.is_staff = level == 'ADMIN'
                auth_user.is_superuser = level == 'ADMIN'
                if password:
                    auth_user.set_password(password)
                auth_user.save()

                profile, _ = UserProfile.objects.get_or_create(user=auth_user)
                profile.is_supervisor = level == 'SUPERVISOR'
                profile.department = Department.objects.filter(code=department_id).first()
                profile.save()

            self.stdout.write(self.style.SUCCESS(f"Imported User {obj.user_id}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created: {created_count}, Updated: {updated_count}",
            ),
        )
