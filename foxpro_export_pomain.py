import argparse
import datetime
import json
import os
from decimal import Decimal

import pyodbc

FOXPRO_FIELDS = [
    ('po_id', 'po_id'),
    ('status', 'status'),
    ('po_date', 'po_date'),
    ('employee_id', 'employee_id'),
    ('customer_id', 'customer_id'),
    ('supplier_id', 'supplier_id'),
    ('ship_date', 'ship_date'),
    ('ship_from', 'ship_from'),
    ('origin', 'origin'),
    ('ship_to', 'ship_to'),
    ('season', 'season'),
    ('order_no', 'order_no'),
    ('sc_date', 'sc_date'),
    ('pay_by', 'pay_by'),
    ('fob_cif', 'fob_cif'),
    ('pur_exchan', 'pur_exchan'),
    ('pur_ccy', 'pur_ccy'),
    ('sonettotal', 'sonettotal'),
    ('doc_amt', 'doc_amt'),
    ('remarks', 'remarks'),
    ('charge1', 'charge1'),
    ('charge1_amt', 'charge1_amt'),
    ('charge1_cur', 'charge1_cur'),
    ('charge1_rate', 'charge1_rate'),
    ('charge2', 'charge2'),
    ('charge2_amt', 'charge2_amt'),
    ('charge2_cur', 'charge2_cur'),
    ('charge2_rate', 'charge2_rate'),
    ('charge3', 'charge3'),
    ('charge3_amt', 'charge3_amt'),
    ('charge3_cur', 'charge3_cur'),
    ('charge3_rate', 'charge3_rate'),
    ('charge4', 'charge4'),
    ('charge4_amt', 'charge4_amt'),
    ('charge4_cur', 'charge4_cur'),
    ('charge4_rate', 'charge4_rate'),
    ('quo_code', 'quo_code'),
    ('due_date', 'due_date'),
    ('extra1_cha', 'extra1_cha'),
    ('extra3_cha', 'extra3_cha'),
    ('extra4_cha', 'extra4_cha'),
    ('extra7_dat', 'extra7_dat'),
    ('extra8_dat', 'extra8_dat'),
    ('shipmark', 'shipmark'),
    ('cdate', 'cdate'),
    ('ddate', 'ddate'),
    ('adatetime', 'adatetime'),
    ('posted', 'posted'),
    ('t1', 't1'),
    ('lab_id', 'lab_id'),
    ('ttl_qty', 'ttl_qty'),
    ('ttl_grs_wt', 'ttl_grs_wt'),
    ('ttl_net_wt', 'ttl_net_wt'),
    ('ttl_cbm', 'ttl_cbm'),
    ('merchan1', 'merchan1'),
]


def _serialize_value(value):
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def main():
    parser = argparse.ArgumentParser(description="Export POMAST rows to JSON/NDJSON.")
    parser.add_argument('--dsn', default=os.getenv('FOXPRO_DSN', 'Fox Pro ERP'))
    parser.add_argument('--limit', type=int, default=1)
    parser.add_argument('--all', action='store_true', help='Export all rows (ignore --limit)')
    parser.add_argument('--since-hours', type=int, default=None, help='Filter by adatetime in last N hours')
    parser.add_argument('--since-days', type=int, default=None, help='Filter by adatetime in last N days')
    parser.add_argument('--order-by', default='po_id')
    parser.add_argument('--output', default=os.path.join(os.getcwd(), 'foxpro_pomain_export.json'))
    parser.add_argument('--format', choices=['json', 'ndjson'], default='json')
    parser.add_argument('--fetch-size', type=int, default=2000)
    args = parser.parse_args()

    cutoff = None
    if args.since_hours is not None:
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=args.since_hours)
    elif args.since_days is not None:
        cutoff = datetime.datetime.now() - datetime.timedelta(days=args.since_days)

    where_clause = ''
    if cutoff:
        cutoff_str = cutoff.strftime('%Y-%m-%d %H:%M:%S')
        where_clause = f" WHERE adatetime >= {{^{cutoff_str}}}"

    select_fields = [f"{field} AS {alias}" for field, alias in FOXPRO_FIELDS]
    if args.all:
        query = (
            f"SELECT {', '.join(select_fields)} "
            f"FROM POMAST{where_clause} ORDER BY {args.order_by}"
        )
    else:
        query = (
            f"SELECT TOP {args.limit} {', '.join(select_fields)} "
            f"FROM POMAST{where_clause} ORDER BY {args.order_by}"
        )

    export_keys = [alias for _, alias in FOXPRO_FIELDS]
    written = 0
    conn = pyodbc.connect(f"DSN={args.dsn};")
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        with open(args.output, 'w', encoding='utf-8') as f:
            if args.format == 'json':
                f.write('[')
                first = True
                while True:
                    batch = cursor.fetchmany(args.fetch_size)
                    if not batch:
                        break
                    for row in batch:
                        row_dict = dict(zip(export_keys, row))
                        serialized = {key: _serialize_value(value) for key, value in row_dict.items()}
                        if not first:
                            f.write(',\n')
                        json.dump(serialized, f, ensure_ascii=False)
                        first = False
                        written += 1
                f.write(']')
            else:
                while True:
                    batch = cursor.fetchmany(args.fetch_size)
                    if not batch:
                        break
                    for row in batch:
                        row_dict = dict(zip(export_keys, row))
                        serialized = {key: _serialize_value(value) for key, value in row_dict.items()}
                        json.dump(serialized, f, ensure_ascii=False)
                        f.write('\n')
                        written += 1
    finally:
        conn.close()

    print(f"Wrote {written} row(s) to {args.output}")


if __name__ == '__main__':
    main()
