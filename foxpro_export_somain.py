import argparse
import datetime
import json
import os
import re
from decimal import Decimal

import pyodbc

FOXPRO_FIELDS = [
    'so_id',
    'status',
    'creator',
    'so_date',
    'employee_id',
    'customer_id',
    'ship_per',
    'ship_date',
    'ship_from',
    'origin',
    'ship_to',
    'season',
    'order_no',
    'order_date',
    'pay_by',
    'sonettotal',
    'doc_amt',
    'sogrsttotal',
    'remarks',
    'last_po',
    'extra3_char',
    'extra4_char',
    'adatetime',
    'posted',
    't1',
    't6',
    'company',
    'ttl_qty',
    'ttl_cbm',
    'ttl_grs_wt',
    'merchan1',
    'sal_ccy',
    'sal_exchan',
    'pur_ccy',
    'pur_total',
    'inv_total',
    'charge1',
    'charge1_amt',
    'charge1_curr',
    'charge1_rate',
    'charge2',
    'charge2_amt',
    'charge2_curr',
    'charge2_rate',
    'charge3',
    'charge3_amt',
    'charge3_curr',
    'charge3_rate',
    'charge4',
    'charge4_amt',
    'charge4_curr',
    'charge4_rate',
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
    if re.match(r'^[A-Za-z]:', text):
        text = text[2:].strip()

    def try_parse(candidate):
        for fmt in (
            '%Y-%m-%d %H:%M:%S',
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d %H:%M',
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

    parsed = try_parse(text)
    if parsed:
        return parsed

    parts = text.split()
    if len(parts) >= 3 and parts[-1].upper() not in {'AM', 'PM'}:
        parsed = try_parse(" ".join(parts[:-1]))
        if parsed:
            return parsed

    return None


def main():
    parser = argparse.ArgumentParser(description="Export SOMAST rows to JSON.")
    parser.add_argument('--dsn', default=os.getenv('FOXPRO_DSN', 'Fox Pro ERP'))
    parser.add_argument('--limit', type=int, default=1)
    parser.add_argument('--all', action='store_true', help='Export all rows (ignore --limit)')
    parser.add_argument('--so-id', default=None, help='Export one specific SO_ID')
    parser.add_argument('--since-hours', type=int, default=None, help='Filter by adatetime in last N hours')
    parser.add_argument('--since-days', type=int, default=None, help='Filter by adatetime in last N days')
    parser.add_argument('--order-by', default='so_id')
    parser.add_argument('--output', default=os.path.join(os.getcwd(), 'foxpro_somain_export.json'))
    args = parser.parse_args()

    cutoff = None
    if args.since_hours is not None:
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=args.since_hours)
    elif args.since_days is not None:
        cutoff = datetime.datetime.now() - datetime.timedelta(days=args.since_days)

    where_clause = ''
    incremental_mode = (args.since_hours is not None) or (args.since_days is not None)

    if args.so_id:
        so_id = str(args.so_id).replace("'", "''")
        query = (
            f"SELECT {', '.join(FOXPRO_FIELDS)} "
            f"FROM SOMAST WHERE so_id = '{so_id}' ORDER BY {args.order_by}"
        )
    elif args.all or incremental_mode:
        query = (
            f"SELECT {', '.join(FOXPRO_FIELDS)} "
            f"FROM SOMAST{where_clause} ORDER BY {args.order_by}"
        )
    else:
        query = (
            f"SELECT TOP {args.limit} {', '.join(FOXPRO_FIELDS)} "
            f"FROM SOMAST{where_clause} ORDER BY {args.order_by}"
        )

    conn = pyodbc.connect(f"DSN={args.dsn};")
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
    finally:
        conn.close()

    output = []
    for row in rows:
        row_dict = dict(zip(FOXPRO_FIELDS, row))
        if cutoff:
            adatetime_dt = _parse_foxpro_datetime(row_dict.get('adatetime'))
            so_date_dt = _parse_foxpro_datetime(row_dict.get('so_date'))
            if not ((adatetime_dt and adatetime_dt >= cutoff) or (so_date_dt and so_date_dt >= cutoff)):
                continue
        serialized = {key: _serialize_value(value) for key, value in row_dict.items()}
        output.append(serialized)

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(output)} row(s) to {args.output}")


if __name__ == '__main__':
    main()
