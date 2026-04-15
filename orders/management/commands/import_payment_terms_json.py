import datetime
import json
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from orders.models import PaymentTerm

FIELD_MAP = {
    'code': 'term_code',
    'terms': 'description',
    'duedays': 'due_day',
    'discount': 'discount',
    'cdate': 'created_time',
    'adate': 'mod_time',
    'status': 'status',
}

DECIMAL_FIELDS = {
    'due_day',
    'discount',
}

DATETIME_FIELDS = {
    'created_time',
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


def _parse_decimal(value):
    if value is None or value == '':
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


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
    help = "Import TERMS JSON export into PostgreSQL PaymentTerm table."

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
            created_time, created_by = _split_user_datetime(row.get('cdate'))
            mod_time, mod_by = _split_user_datetime(row.get('adate'))
            for source_field, target_field in FIELD_MAP.items():
                value = row.get(source_field)
                if target_field == 'created_time':
                    value = created_time
                if target_field == 'mod_time':
                    value = mod_time
                if target_field in DATETIME_FIELDS:
                    value = _parse_datetime(value)
                elif target_field in DECIMAL_FIELDS:
                    value = _parse_decimal(value)
                elif isinstance(value, str):
                    value = _sanitize_text(value)
                mapped[target_field] = value

            if created_by and not mapped.get('created_by'):
                mapped['created_by'] = _sanitize_text(created_by)
            if mod_by:
                mapped['mod_by'] = _sanitize_text(mod_by)

            term_code = _sanitize_text(mapped.pop('term_code', None))
            if not term_code:
                continue

            obj, created = PaymentTerm.objects.update_or_create(
                term_code=term_code,
                defaults=mapped,
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

            self.stdout.write(self.style.SUCCESS(f"Imported PaymentTerm {obj.term_code}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created: {created_count}, Updated: {updated_count}",
            ),
        )
