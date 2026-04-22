import argparse
import datetime
import json
import os
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


def main():
    parser = argparse.ArgumentParser(description="Export SOMAST rows to JSON.")
    parser.add_argument('--dsn', default=os.getenv('FOXPRO_DSN', 'Fox Pro ERP'))
    parser.add_argument('--limit', type=int, default=1)
    parser.add_argument('--all', action='store_true', help='Export all rows (ignore --limit)')
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
    if cutoff:
        cutoff_str = cutoff.strftime('%Y-%m-%d %H:%M:%S')
        where_clause = f" WHERE adatetime >= {{^{cutoff_str}}}"

    if args.all:
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
        serialized = {key: _serialize_value(value) for key, value in row_dict.items()}
        output.append(serialized)

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(output)} row(s) to {args.output}")


if __name__ == '__main__':
    main()
