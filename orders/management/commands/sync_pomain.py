import datetime
import os
from decimal import Decimal

import pyodbc
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from orders.models import POMain

FOXPRO_FIELDS = [
    ('po_id', 'po_number'),
    ('status', 'po_status'),
    ('po_date', 'po_date'),
    ('employee_id', 'salesman'),
    ('customer_id', 'customer_code'),
    ('supplier_id', 'supplier_id'),
    ('ship_date', 'po_ship_date'),
    ('ship_from', 'ship_from'),
    ('origin', 'origin'),
    ('ship_to', 'ship_to'),
    ('season', 'port_of_disch'),
    ('order_no', 'customer_order_number'),
    ('sc_date', 'sc_date'),
    ('pay_by', 'payment_term_code'),
    ('fob_cif', 'trade_term'),
    ('pur_exchan', 'po_exchange_rate'),
    ('pur_ccy', 'po_currency'),
    ('sonettotal', 'po_net_total'),
    ('doc_amt', 'po_doc_net_total'),
    ('remarks', 'po_remarks'),
    ('charge1', 'charge1_desc'),
    ('charge1_amt', 'charge1_amount'),
    ('charge1_cur', 'charge1_currency'),
    ('charge1_rate', 'charge1_curr_rate'),
    ('charge2', 'charge2_desc'),
    ('charge2_amt', 'charge2_amount'),
    ('charge2_cur', 'charge2_currency'),
    ('charge2_rate', 'charge2_curr_rate'),
    ('charge3', 'charge3_desc'),
    ('charge3_amt', 'charge3_amount'),
    ('charge3_cur', 'charge3_currency'),
    ('charge3_rate', 'charge3_curr_rate'),
    ('charge4', 'charge4_desc'),
    ('charge4_amt', 'charge4_amount'),
    ('charge4_cur', 'charge4_currency'),
    ('charge4_rate', 'charge4_curr_rate'),
    ('quo_code', 'sc_number'),
    ('due_date', 'po_due_date'),
    ('extra1_cha', 'po_port_of_loading'),
    ('extra3_cha', 'po_container_qty'),
    ('extra4_cha', 'po_container_size'),
    ('extra7_dat', 'sc_ship_date'),
    ('extra8_dat', 'sc_date_alt'),
    ('shipmark', 'po_ship_mark'),
    ('adatetime', 'modified_time'),
    ('posted', 'posted'),
    ('t1', 'department_id'),
    ('lab_id', 'year'),
    ('ttl_qty', 'po_total_qty'),
    ('ttl_grs_wt', 'po_total_gross_wt'),
    ('ttl_net_wt', 'po_total_net_wt'),
    ('ttl_cbm', 'po_total_cbm'),
    ('merchan1', 'merchandiser'),
]

DATETIME_FIELDS = {
    'po_date', 'po_ship_date', 'sc_date', 'po_due_date',
    'sc_ship_date', 'sc_date_alt', 'modified_time',
    'created_by_date', 'modified_by_date',
}

DECIMAL_FIELDS = {
    'po_exchange_rate', 'po_net_total', 'po_doc_net_total',
    'charge1_amount', 'charge1_curr_rate',
    'charge2_amount', 'charge2_curr_rate',
    'charge3_amount', 'charge3_curr_rate',
    'charge4_amount', 'charge4_curr_rate',
    'po_total_qty', 'po_total_gross_wt', 'po_total_net_wt', 'po_total_cbm',
}


def _parse_datetime(value):
    if value is None or value == '':
        return None
    if isinstance(value, datetime.datetime):
        return timezone.make_aware(value) if timezone.is_naive(value) else value
    if isinstance(value, datetime.date):
        dt = datetime.datetime.combine(value, datetime.time.min)
        return timezone.make_aware(dt)
    return value


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
    if value is None:
        return None, None
    text = str(value).strip()
    if not text:
        return None, None
    parts = text.split()
    if len(parts) >= 3:
        user = parts[-1]
        time_str = " ".join(parts[:-1])
        for fmt in ('%Y/%m/%d %H:%M', '%Y/%m/%d %H:%M:%S', '%Y-%m-%d %H:%M:%S'):
            try:
                dt = datetime.datetime.strptime(time_str, fmt)
                dt = timezone.make_aware(dt) if timezone.is_naive(dt) else dt
                return user, dt
            except ValueError:
                continue
    return text[:50], None


class Command(BaseCommand):
    help = "Sync one or more POMAST records into PostgreSQL POMAIN table."

    def add_arguments(self, parser):
        parser.add_argument('--dsn', default=os.getenv('FOXPRO_DSN', 'Fox Pro ERP'))
        parser.add_argument('--limit', type=int, default=1)
        parser.add_argument('--order-by', default='po_id')

    def handle(self, *args, **options):
        dsn = options['dsn']
        limit = options['limit']
        order_by = options['order_by']

        select_fields = [field for field, _ in FOXPRO_FIELDS] + ['cdate', 'ddate']
        query = (
            f"SELECT TOP {limit} {', '.join(select_fields)} "
            f"FROM POMAST ORDER BY {order_by}"
        )

        try:
            conn = pyodbc.connect(f"DSN={dsn};")
        except pyodbc.Error as exc:
            raise CommandError(f"ODBC connection failed: {exc}") from exc

        try:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
        except pyodbc.Error as exc:
            raise CommandError(f"FoxPro query failed: {exc}") from exc
        finally:
            conn.close()

        if not rows:
            self.stdout.write(self.style.WARNING("No rows returned from POMAST."))
            return

        created_count = 0
        updated_count = 0

        for row in rows:
            row_dict = dict(zip(select_fields, row))
            mapped = {}
            for source_field, target_field in FOXPRO_FIELDS:
                value = row_dict.get(source_field)
                if target_field in DATETIME_FIELDS:
                    value = _parse_datetime(value)
                elif target_field in DECIMAL_FIELDS:
                    value = _parse_decimal(value)
                elif target_field == 'posted':
                    value = _parse_bool(value)
                elif isinstance(value, str):
                    value = value.strip()
                mapped[target_field] = value

            created_by, created_by_date = _split_user_datetime(row_dict.get('cdate'))
            modified_by, modified_by_date = _split_user_datetime(row_dict.get('ddate'))
            mapped['created_by'] = created_by
            mapped['created_by_date'] = created_by_date
            mapped['modified_by'] = modified_by
            mapped['modified_by_date'] = modified_by_date

            po_number = mapped.pop('po_number')
            if not po_number:
                continue

            obj, created = POMain.objects.update_or_create(
                po_number=po_number,
                defaults=mapped,
            )
            if created:
                created_count += 1
            else:
                updated_count += 1
            self.stdout.write(self.style.SUCCESS(f"Synced POMAIN {obj.po_number}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created: {created_count}, Updated: {updated_count}",
            ),
        )
