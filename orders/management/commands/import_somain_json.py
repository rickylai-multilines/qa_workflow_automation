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
    'sal_ccy': 'sc_currency',
    'sal_exchan': 'sc_ex_rate',
    'pur_ccy': 'po_currency',
    'pur_total': 'po_total_amount',
    'inv_total': 'inv_total_amount',
    'charge1': 'charge1_desc',
    'charge1_amt': 'charge1_amount',
    'charge1_curr': 'charge1_currency',
    'charge1_rate': 'charge1_cur_rate',
    'charge2': 'charge2_desc',
    'charge2_amt': 'charge2_amount',
    'charge2_curr': 'charge2_currency',
    'charge2_rate': 'charge2_cur_rate',
    'charge3': 'charge3_desc',
    'charge3_amt': 'charge3_amount',
    'charge3_curr': 'charge3_currency',
    'charge3_rate': 'charge3_cur_rate',
    'charge4': 'charge4_desc',
    'charge4_amt': 'charge4_amount',
    'charge4_curr': 'charge4_currency',
    'charge4_rate': 'charge4_cur_rate',
}

DECIMAL_FIELDS = {
    'net_total_amt',
    'doc_net_total_amt',
    'gross_total_amt',
    'total_qty',
    'total_cbm',
    'total_gross_wt',
    'sc_ex_rate',
    'po_total_amount',
    'inv_total_amount',
    'charge1_amount',
    'charge1_cur_rate',
    'charge2_amount',
    'charge2_cur_rate',
    'charge3_amount',
    'charge3_cur_rate',
    'charge4_amount',
    'charge4_cur_rate',
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
    text = str(value).strip()
    for fmt in (
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S',
        '%Y/%m/%d %H:%M:%S',
        '%m/%d/%y %I:%M:%S %p',
        '%m/%d/%Y %I:%M:%S %p',
        '%m/%d/%y %I:%M %p',
        '%m/%d/%Y %I:%M %p',
    ):
        try:
            dt = datetime.datetime.strptime(text, fmt)
            return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
        except ValueError:
            continue
    dt = datetime.datetime.fromisoformat(text)
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
