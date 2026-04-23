import datetime
import json
import re
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from orders.models import POMain

FIELD_MAP = {
    'po_id': 'po_number',
    'status': 'po_status',
    'po_date': 'po_date',
    'employee_id': 'salesman',
    'customer_id': 'customer_code',
    'supplier_id': 'supplier_id',
    'ship_date': 'po_ship_date',
    'ship_from': 'ship_from',
    'origin': 'origin',
    'ship_to': 'ship_to',
    'season': 'port_of_disch',
    'order_no': 'customer_order_number',
    'sc_date': 'sc_date',
    'pay_by': 'payment_term_code',
    'fob_cif': 'trade_term',
    'pur_exchan': 'po_exchange_rate',
    'pur_ccy': 'po_currency',
    'sonettotal': 'po_net_total',
    'doc_amt': 'po_doc_net_total',
    'remarks': 'po_remarks',
    'charge1': 'charge1_desc',
    'charge1_amt': 'charge1_amount',
    'charge1_cur': 'charge1_currency',
    'charge1_rate': 'charge1_curr_rate',
    'charge2': 'charge2_desc',
    'charge2_amt': 'charge2_amount',
    'charge2_cur': 'charge2_currency',
    'charge2_rate': 'charge2_curr_rate',
    'charge3': 'charge3_desc',
    'charge3_amt': 'charge3_amount',
    'charge3_cur': 'charge3_currency',
    'charge3_rate': 'charge3_curr_rate',
    'charge4': 'charge4_desc',
    'charge4_amt': 'charge4_amount',
    'charge4_cur': 'charge4_currency',
    'charge4_rate': 'charge4_curr_rate',
    'quo_code': 'sc_number',
    'due_date': 'po_due_date',
    'extra1_cha': 'po_port_of_loading',
    'extra3_cha': 'po_container_qty',
    'extra4_cha': 'po_container_size',
    'extra7_dat': 'sc_ship_date',
    'extra8_dat': 'sc_date_alt',
    'shipmark': 'po_ship_mark',
    'adatetime': 'modified_time',
    'posted': 'posted',
    't1': 'department_id',
    'lab_id': 'year',
    'ttl_qty': 'po_total_qty',
    'ttl_grs_wt': 'po_total_gross_wt',
    'ttl_net_wt': 'po_total_net_wt',
    'ttl_cbm': 'po_total_cbm',
    'merchan1': 'merchandiser',
}

DECIMAL_FIELDS = {
    'po_exchange_rate',
    'po_net_total',
    'po_doc_net_total',
    'charge1_amount',
    'charge1_curr_rate',
    'charge2_amount',
    'charge2_curr_rate',
    'charge3_amount',
    'charge3_curr_rate',
    'charge4_amount',
    'charge4_curr_rate',
    'po_total_qty',
    'po_total_gross_wt',
    'po_total_net_wt',
    'po_total_cbm',
}

DATETIME_FIELDS = {
    'po_date',
    'po_ship_date',
    'sc_date',
    'po_due_date',
    'sc_ship_date',
    'sc_date_alt',
    'created_by_date',
    'modified_by_date',
    'modified_time',
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


def _parse_bool(value):
    if value is None or value == '':
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, Decimal)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {'t', 'true', '1', 'y', 'yes'}:
        return True
    if text in {'f', 'false', '0', 'n', 'no'}:
        return False
    return None


def _split_user_datetime(value):
    """
    FoxPro cdate/ddate stores combined datetime + user text (width 30).
    Example: "2026/04/01 14:30 JACKIE"
    """
    if value is None:
        return None, None
    text = _sanitize_text(value)
    if not text:
        return None, None
    # Handle prefixes like "L:2026/04/22 17:53 LEOMA" or "X:2026-04-22 17:53:00 USER"
    match = re.match(
        r'^(?:[A-Za-z]\:)?\s*(\d{4}[/-]\d{2}[/-]\d{2})\s+(\d{2}:\d{2}(?::\d{2})?)\s+(.+)$',
        text,
    )
    if match:
        date_part, time_part, user_part = match.groups()
        normalized_date = date_part.replace('/', '-')
        time_str = f"{normalized_date} {time_part}"
        for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S'):
            try:
                dt = datetime.datetime.strptime(time_str, fmt)
                dt = timezone.make_aware(dt) if timezone.is_naive(dt) else dt
                return _sanitize_text(user_part), dt
            except ValueError:
                continue
    parts = text.split()
    if len(parts) >= 3:
        user = parts[-1]
        time_str = " ".join(parts[:-1])
        for fmt in ('%Y/%m/%d %H:%M', '%Y/%m/%d %H:%M:%S', '%Y-%m-%d %H:%M:%S'):
            try:
                dt = datetime.datetime.strptime(time_str, fmt)
                dt = timezone.make_aware(dt) if timezone.is_naive(dt) else dt
                return _sanitize_text(user), dt
            except ValueError:
                continue
    # Fallback: if format cannot be parsed, keep as user text only.
    return text[:50], None


class Command(BaseCommand):
    help = "Import POMAST JSON/NDJSON export into PostgreSQL POMAIN table."

    def add_arguments(self, parser):
        parser.add_argument('--path', required=True)
        parser.add_argument(
            '--audit-only',
            action='store_true',
            help='Update only CreatedBy/CreatedByDate/ModifiedBy/ModifiedByDate fields.',
        )

    def handle(self, *args, **options):
        path = options['path']
        audit_only = options['audit_only']
        rows = []
        try:
            is_ndjson = path.lower().endswith('.ndjson')
            if not is_ndjson:
                with open(path, 'r', encoding='utf-8') as f:
                    rows = json.load(f)
                    if not isinstance(rows, list):
                        raise CommandError("JSON must be a list of rows (or NDJSON lines).")
        except FileNotFoundError as exc:
            raise CommandError(f"File not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON: {exc}") from exc

        created_count = 0
        updated_count = 0

        def process_row(row):
            nonlocal created_count, updated_count
            mapped = {}
            for source_field, target_field in FIELD_MAP.items():
                value = row.get(source_field)
                if target_field in DATETIME_FIELDS:
                    value = _parse_datetime(value)
                elif target_field in DECIMAL_FIELDS:
                    value = _parse_decimal(value)
                elif target_field == 'posted':
                    value = _parse_bool(value)
                elif isinstance(value, str):
                    value = _sanitize_text(value)
                mapped[target_field] = value

            created_by, created_by_date = _split_user_datetime(row.get('cdate'))
            modified_by, modified_by_date = _split_user_datetime(row.get('ddate'))
            mapped['created_by'] = _sanitize_text(created_by)
            mapped['created_by_date'] = created_by_date
            mapped['modified_by'] = _sanitize_text(modified_by)
            mapped['modified_by_date'] = modified_by_date

            po_number = _sanitize_text(mapped.pop('po_number', None))
            if not po_number:
                return

            if audit_only:
                mapped = {
                    'created_by': mapped.get('created_by'),
                    'created_by_date': mapped.get('created_by_date'),
                    'modified_by': mapped.get('modified_by'),
                    'modified_by_date': mapped.get('modified_by_date'),
                }

            obj, created = POMain.objects.update_or_create(
                po_number=po_number,
                defaults=mapped,
            )
            if created:
                created_count += 1
            else:
                updated_count += 1
            self.stdout.write(self.style.SUCCESS(f"Imported POMAIN {obj.po_number}"))

        if is_ndjson:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    process_row(json.loads(line))
        else:
            for row in rows:
                process_row(row)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created: {created_count}, Updated: {updated_count}",
            ),
        )
