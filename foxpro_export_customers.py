import argparse
import datetime
import json
import os
from decimal import Decimal

import pyodbc

FOXPRO_FIELDS = [
    ('customer_id', 'customer_id'),
    ('customer_code', 'customer_code'),
    ('employee_id', 'employee_id'),
    ('company_name', 'company_name'),
    ('contact_name', 'contact_name'),
    ('address', 'address'),
    ('address2', 'address2'),
    ('address3', 'address3'),
    ('address4', 'address4'),
    ('country', 'country'),
    ('city', 'city'),
    ('region', 'region'),
    ('postal_code', 'postal_code'),
    ('phone', 'phone'),
    ('phone1', 'phone1'),
    ('phone2', 'phone2'),
    ('contact1', 'contact1'),
    ('contact2', 'contact2'),
    ('fax', 'fax'),
    ('telex', 'telex'),
    ('cable', 'cable'),
    ('cust_pay', 'cust_pay'),
    ('status', 'status'),
    ('ship_to', 'ship_to'),
    ('fob_cif', 'fob_cif'),
    ('cdate', 'cdate'),
    ('adate', 'adate'),
    ('t6', 't6'),
    ('remarks2', 'remarks2'),
]


def _serialize_value(value):
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def main():
    parser = argparse.ArgumentParser(description="Export CUSTOMER rows to JSON.")
    parser.add_argument('--dsn', default=os.getenv('FOXPRO_DSN', 'Fox Pro ERP'))
    parser.add_argument('--limit', type=int, default=1)
    parser.add_argument('--all', action='store_true', help='Export all rows (ignore --limit)')
    parser.add_argument('--since-hours', type=int, default=None, help='Filter by adate in last N hours')
    parser.add_argument('--since-days', type=int, default=None, help='Filter by adate in last N days')
    parser.add_argument('--order-by', default='customer_id')
    parser.add_argument('--output', default=os.path.join(os.getcwd(), 'foxpro_customers_export.json'))
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
            f"FROM CUSTOMER{where_clause} ORDER BY {args.order_by}"
        )
    else:
        query = (
            f"SELECT TOP {args.limit} {', '.join(select_fields)} "
            f"FROM CUSTOMER{where_clause} ORDER BY {args.order_by}"
        )

    conn = pyodbc.connect(f"DSN={args.dsn};")
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
    finally:
        conn.close()

    output = []
    export_keys = [alias for _, alias in FOXPRO_FIELDS]
    for row in rows:
        row_dict = dict(zip(export_keys, row))
        serialized = {key: _serialize_value(value) for key, value in row_dict.items()}
        output.append(serialized)

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(output)} row(s) to {args.output}")


if __name__ == '__main__':
    main()
