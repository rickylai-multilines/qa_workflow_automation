import datetime
import json
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from orders.models import Customer

FIELD_MAP = {
    'customer_id': 'customer_id',
    'customer_code': 'customer_code',
    'employee_id': 'salesman',
    'company_name': 'customer_name',
    'contact_name': 'contact_person',
    'address': 'address1',
    'address2': 'address2',
    'address3': 'address3',
    'address4': 'address4',
    'country': 'country',
    'city': 'city',
    'region': 'region',
    'postal_code': 'postal_code',
    'phone': 'tel',
    'phone1': 'tel1',
    'phone2': 'tel2',
    'contact1': 'contact_person1',
    'contact2': 'contact_person2',
    'fax': 'fax',
    'telex': 'mobile',
    'cable': 'email',
    'cust_pay': 'payment_term',
    'status': 'status',
    'ship_to': 'ship_to',
    'fob_cif': 'trade_term',
    'cdate': 'created_time',
    'adate': 'mod_time',
    't6': 'port_of_loading',
    'remarks2': 'po_remark',
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
    help = "Import CUSTOMER JSON export into PostgreSQL Customer table."

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
                elif isinstance(value, str):
                    value = _sanitize_text(value)
                mapped[target_field] = value

            if created_by and not mapped.get('created_by'):
                mapped['created_by'] = _sanitize_text(created_by)
            if mod_by:
                mapped['mod_by'] = _sanitize_text(mod_by)

            customer_id = _sanitize_text(mapped.pop('customer_id', None))
            if not customer_id:
                continue

            obj, created = Customer.objects.update_or_create(
                customer_id=customer_id,
                defaults=mapped,
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

            self.stdout.write(self.style.SUCCESS(f"Imported Customer {obj.customer_id}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created: {created_count}, Updated: {updated_count}",
            ),
        )
