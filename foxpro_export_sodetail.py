import argparse
import datetime
import json
import os
from decimal import Decimal

import pyodbc

FOXPRO_FIELDS = [
    ('so_id', 'so_id'),
    ('po_id', 'po_id'),
    ('product_id', 'product_id'),
    ('bar_code', 'bar_code'),
    ('custref', 'custref'),
    ('quantity', 'quantity'),
    ('ctn_unit', 'ctn_unit'),
    ('unit_price', 'unit_price'),
    ('supplier_id', 'supplier_id'),
    ('customer_id', 'customer_id'),
    ('product_name', 'product_name'),
    ('sequence', 'sequence'),
    ('desc', 'desc_'),
    ('adate', 'adate'),
    ('marks', 'marks'),
    ('extra_1', 'extra_1'),
    ('extra_2', 'extra_2'),
    ('extra_3', 'extra_3'),
    ('adatetime', 'adatetime'),
    ('net_wt', 'net_wt'),
    ('grs_wt', 'grs_wt'),
    ('posted', 'posted'),
    ('ctn_qty', 'ctn_qty'),
    ('ctn_pack', 'ctn_pack'),
    ('length', 'length'),
    ('hight', 'hight'),
    ('width', 'width'),
    ('measure_unit', 'measure_unit'),
    ('packing', 'packing'),
    ('cbm', 'cbm'),
    ('cuft', 'cuft'),
    ('nb_ctns', 'nb_ctns'),
    ('custom_code', 'custom_code'),
    ('attribute4', 'attribute4'),
    ('ccy', 'ccy'),
    ('material_name', 'material_name'),
    ('photo1', 'photo1'),
]


def _serialize_value(value):
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def main():
    parser = argparse.ArgumentParser(description="Export SODTL rows to JSON.")
    parser.add_argument('--dsn', default=os.getenv('FOXPRO_DSN', 'Fox Pro ERP'))
    parser.add_argument('--limit', type=int, default=1)
    parser.add_argument('--all', action='store_true', help='Export all rows (ignore --limit)')
    parser.add_argument('--since-hours', type=int, default=None, help='Filter by Adate in last N hours')
    parser.add_argument('--since-days', type=int, default=None, help='Filter by Adate in last N days')
    parser.add_argument('--order-by', default='so_id')
    parser.add_argument('--output', default=os.path.join(os.getcwd(), 'foxpro_sodetail_export.json'))
    parser.add_argument('--format', choices=['json', 'ndjson'], default='json')
    parser.add_argument('--fetch-size', type=int, default=2000)
    args = parser.parse_args()

    select_fields = [f"{field} AS {alias}" for field, alias in FOXPRO_FIELDS]
    cutoff = None
    if args.since_hours is not None:
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=args.since_hours)
    elif args.since_days is not None:
        cutoff = datetime.datetime.now() - datetime.timedelta(days=args.since_days)

    where_clause = ''
    if cutoff:
        cutoff_str = cutoff.strftime('%Y/%m/%d %H:%M')
        where_clause = f" WHERE LEFT(adate, 16) >= '{cutoff_str}'"

    if args.all:
        query = (
            f"SELECT {', '.join(select_fields)} "
            f"FROM SODTL{where_clause} ORDER BY {args.order_by}"
        )
    else:
        query = (
            f"SELECT TOP {args.limit} {', '.join(select_fields)} "
            f"FROM SODTL{where_clause} ORDER BY {args.order_by}"
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
