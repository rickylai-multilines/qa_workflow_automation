import argparse
import datetime
import json
import os
import re
from decimal import Decimal

import pyodbc

FOXPRO_FIELDS = [
    ('product_id', 'product_id'),
    ('bar_code', 'bar_code'),
    ('lookupid', 'lookupid'),
    ('class_id', 'class_id'),
    ('class1', 'class1'),
    ('packing', 'packing'),
    ('attribute1', 'attribute1'),
    ('attribute3', 'attribute3'),
    ('attribute4', 'attribute4'),
    ('attribute5', 'attribute5'),
    ('supplier_id', 'supplier_id'),
    ('product_name', 'product_name'),
    ('unit_price', 'unit_price'),
    ('unit_price2', 'unit_price2'),
    ('unit_price3', 'unit_price3'),
    ('unit_cost', 'unit_cost'),
    ('ctn_qty', 'ctn_qty'),
    ('ctn_unit', 'ctn_unit'),
    ('ctn_pack', 'ctn_pack'),
    ('ctn_packqty', 'ctn_packqty'),
    ('length', 'length'),
    ('hight', 'hight'),
    ('width', 'width'),
    ('measure_unit', 'measure_unit'),
    ('cuft', 'cuft'),
    ('cbm', 'cbm'),
    ('net_wt', 'net_wt'),
    ('grs_wt', 'grs_wt'),
    ('group1', 'group1'),
    ('group2', 'group2'),
    ('quota_desc', 'quota_desc'),
    ('custom_code', 'custom_code'),
    ('discontinued', 'discontinued'),
    ('desc', 'desc_'),
    ('cdate', 'cdate'),
    ('adate', 'adate'),
    ('photo', 'photo'),
    ('price_term', 'price_term'),
    ('price_term2', 'price_term2'),
    ('price_term3', 'price_term3'),
    ('cost_term', 'cost_term'),
    ('date6', 'date6'),
    ('creator', 'creator'),
]


def _serialize_value(value):
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _parse_foxpro_datetime(value):
    if value is None or value == '':
        return None
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.date):
        return datetime.datetime.combine(value, datetime.time.min)

    text = str(value).strip()
    if not text:
        return None

    # Handle prefixes like "L:2026/04/23 15:54 USER"
    if re.match(r'^[A-Za-z]:', text):
        text = text[2:].strip()

    def try_parse(candidate):
        for fmt in (
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d %H:%M',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%m/%d/%y %I:%M:%S %p',
            '%m/%d/%Y %I:%M:%S %p',
            '%m/%d/%y %I:%M %p',
            '%m/%d/%Y %I:%M %p',
        ):
            try:
                return datetime.datetime.strptime(candidate, fmt)
            except ValueError:
                continue
        return None

    # First parse the full value directly (important for AM/PM values).
    parsed = try_parse(text)
    if parsed:
        return parsed

    # Then try stripping a trailing user token, e.g. "... PM JAMIE" or "... 15:54 LEOMA".
    parts = text.split()
    if len(parts) >= 4:
        candidate = " ".join(parts[:-1])
        parsed = try_parse(candidate)
        if parsed:
            return parsed

    for fmt in (
        '%Y/%m/%d %H:%M:%S',
        '%Y/%m/%d %H:%M',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%m/%d/%y %I:%M:%S %p',
        '%m/%d/%Y %I:%M:%S %p',
        '%m/%d/%y %I:%M %p',
        '%m/%d/%Y %I:%M %p',
    ):
        try:
            return datetime.datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def main():
    parser = argparse.ArgumentParser(description="Export PRODUCTS rows to JSON.")
    parser.add_argument('--dsn', default=os.getenv('FOXPRO_DSN', 'Fox Pro ERP'))
    parser.add_argument('--limit', type=int, default=1)
    parser.add_argument('--all', action='store_true', help='Export all rows (ignore --limit)')
    parser.add_argument('--since-hours', type=int, default=None, help='Filter by adate in last N hours')
    parser.add_argument('--since-days', type=int, default=None, help='Filter by adate in last N days')
    parser.add_argument('--order-by', default='product_id')
    parser.add_argument('--output', default=os.path.join(os.getcwd(), 'foxpro_products_export.json'))
    args = parser.parse_args()

    select_fields = [f"{field} AS {alias}" for field, alias in FOXPRO_FIELDS]
    cutoff = None
    if args.since_hours is not None:
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=args.since_hours)
    elif args.since_days is not None:
        cutoff = datetime.datetime.now() - datetime.timedelta(days=args.since_days)

    where_clause = ''
    incremental_mode = (args.since_hours is not None) or (args.since_days is not None)

    if args.all or incremental_mode:
        query = (
            f"SELECT {', '.join(select_fields)} "
            f"FROM PRODUCTS{where_clause} ORDER BY {args.order_by}"
        )
    else:
        query = (
            f"SELECT TOP {args.limit} {', '.join(select_fields)} "
            f"FROM PRODUCTS{where_clause} ORDER BY {args.order_by}"
        )

    conn = pyodbc.connect(f"DSN={args.dsn};")
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
    finally:
        conn.close()

    export_keys = [alias for _, alias in FOXPRO_FIELDS]
    output = []
    for row in rows:
        row_dict = dict(zip(export_keys, row))
        if cutoff:
            adate_dt = _parse_foxpro_datetime(row_dict.get('adate'))
            cdate_dt = _parse_foxpro_datetime(row_dict.get('cdate'))
            if not ((adate_dt and adate_dt >= cutoff) or (cdate_dt and cdate_dt >= cutoff)):
                continue
        serialized = {key: _serialize_value(value) for key, value in row_dict.items()}
        output.append(serialized)

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(output)} row(s) to {args.output}")


if __name__ == '__main__':
    main()
