import datetime
import json
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from orders.models import SOMain

FIELD_MAP = {
    'so_id': 'sc_number',
    'status': 'sc_status',
    'creator': 'created_by',
    'so_date': 'sc_date',
    'employee_id': 'salesman',
    'customer_id': 'cu_code',
    'ship_per': 'ship_via',
    'ship_date': 'crd',
    'ship_from': 'port_of_load',
    'origin': 'origin',
    'ship_to': 'ship_to',
    'season': 'port_of_disch',
    'order_no': 'cust_order',
    'order_date': 'order_date',
    'pay_by': 'payment_term_code',
    'sonettotal': 'net_total_amt',
    'doc_amt': 'doc_net_total_amt',
    'sogrsttotal': 'gross_total_amt',
    'remarks': 'remark',
    'last_po': 'last_po_no',
    'extra3_char': 'container_qty',
    'extra4_char': 'container_size',
    'adatetime': 'mod_time',
    'posted': 'posted',
    't1': 'department_no',
    't6': 'trade_term',
    'company': 'company',
    'ttl_qty': 'total_qty',
    'ttl_cbm': 'total_cbm',
    'ttl_grs_wt': 'total_gross_wt',
    'merchan1': 'user_id',
}

DECIMAL_FIELDS = {
    'net_total_amt',
    'doc_net_total_amt',
    'gross_total_amt',
    'total_qty',
    'total_cbm',
    'total_gross_wt',
}

DATETIME_FIELDS = {
    'sc_date',
    'crd',
    'order_date',
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
    dt = datetime.datetime.fromisoformat(str(value))
    return timezone.make_aware(dt) if timezone.is_naive(dt) else dt


def _parse_decimal(value):
    if value is None or value == '':
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class Command(BaseCommand):
    help = "Import SOMAST JSON export into PostgreSQL SOMAIN table."

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
            for source_field, target_field in FIELD_MAP.items():
                value = row.get(source_field)
                if target_field in DATETIME_FIELDS:
                    value = _parse_datetime(value)
                elif target_field in DECIMAL_FIELDS:
                    value = _parse_decimal(value)
                elif isinstance(value, str):
                    value = _sanitize_text(value)
                mapped[target_field] = value

            sc_number = _sanitize_text(mapped.pop('sc_number', None))
            if not sc_number:
                continue

            obj, created = SOMain.objects.update_or_create(
                sc_number=sc_number,
                defaults=mapped,
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

            self.stdout.write(self.style.SUCCESS(f"Imported SOMAIN {obj.sc_number}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created: {created_count}, Updated: {updated_count}",
            ),
        )
