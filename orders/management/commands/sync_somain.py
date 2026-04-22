import datetime
import os

import pyodbc
from django.core.management.base import BaseCommand, CommandError

from orders.models import SOMain


FOXPRO_FIELDS = [
    ('so_id', 'sc_number'),
    ('status', 'sc_status'),
    ('creator', 'created_by'),
    ('so_date', 'sc_date'),
    ('employee_id', 'salesman'),
    ('customer_id', 'cu_code'),
    ('ship_per', 'ship_via'),
    ('ship_date', 'crd'),
    ('ship_from', 'port_of_load'),
    ('origin', 'origin'),
    ('ship_to', 'ship_to'),
    ('season', 'port_of_disch'),
    ('order_no', 'cust_order'),
    ('order_date', 'order_date'),
    ('pay_by', 'payment_term_code'),
    ('sonettotal', 'net_total_amt'),
    ('doc_amt', 'doc_net_total_amt'),
    ('sogrsttotal', 'gross_total_amt'),
    ('remarks', 'remark'),
    ('last_po', 'last_po_no'),
    ('extra3_char', 'container_qty'),
    ('extra4_char', 'container_size'),
    ('adatetime', 'mod_time'),
    ('posted', 'posted'),
    ('t1', 'department_no'),
    ('t6', 'trade_term'),
    ('company', 'company'),
    ('ttl_qty', 'total_qty'),
    ('ttl_cbm', 'total_cbm'),
    ('ttl_grs_wt', 'total_gross_wt'),
    ('merchan1', 'user_id'),
    ('sal_ccy', 'sc_currency'),
    ('sal_exchan', 'sc_ex_rate'),
    ('pur_ccy', 'po_currency'),
    ('pur_total', 'po_total_amount'),
    ('inv_total', 'inv_total_amount'),
    ('charge1', 'charge1_desc'),
    ('charge1_amt', 'charge1_amount'),
    ('charge1_curr', 'charge1_currency'),
    ('charge1_rate', 'charge1_cur_rate'),
    ('charge2', 'charge2_desc'),
    ('charge2_amt', 'charge2_amount'),
    ('charge2_curr', 'charge2_currency'),
    ('charge2_rate', 'charge2_cur_rate'),
    ('charge3', 'charge3_desc'),
    ('charge3_amt', 'charge3_amount'),
    ('charge3_curr', 'charge3_currency'),
    ('charge3_rate', 'charge3_cur_rate'),
    ('charge4', 'charge4_desc'),
    ('charge4_amt', 'charge4_amount'),
    ('charge4_curr', 'charge4_currency'),
    ('charge4_rate', 'charge4_cur_rate'),
]


def _normalize_datetime(value):
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.date):
        return datetime.datetime.combine(value, datetime.time.min)
    return value


class Command(BaseCommand):
    help = "Sync one or more SOMAST records into PostgreSQL SOMAIN table."

    def add_arguments(self, parser):
        parser.add_argument('--dsn', default=os.getenv('FOXPRO_DSN', 'Fox Pro ERP'))
        parser.add_argument('--limit', type=int, default=1)
        parser.add_argument('--order-by', default='so_id')

    def handle(self, *args, **options):
        dsn = options['dsn']
        limit = options['limit']
        order_by = options['order_by']

        select_fields = [field for field, _ in FOXPRO_FIELDS]
        query = (
            f"SELECT TOP {limit} {', '.join(select_fields)} "
            f"FROM SOMAST ORDER BY {order_by}"
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
            self.stdout.write(self.style.WARNING("No rows returned from SOMAST."))
            return

        created_count = 0
        updated_count = 0

        for row in rows:
            row_dict = dict(zip(select_fields, row))
            mapped = {}
            for source_field, target_field in FOXPRO_FIELDS:
                value = row_dict.get(source_field)
                mapped[target_field] = _normalize_datetime(value)

            sc_number = mapped.pop('sc_number')
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

            self.stdout.write(
                self.style.SUCCESS(f"Synced SOMAIN {obj.sc_number}"),
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created: {created_count}, Updated: {updated_count}",
            ),
        )
