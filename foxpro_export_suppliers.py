import argparse
import datetime
import json
import os
from decimal import Decimal

import pyodbc

FOXPRO_FIELDS = [
    ('supplier_id', 'supplier_id'),
    ('company_name', 'company_name'),
    ('contact_name', 'contact_name'),
    ('address', 'address'),
    ('address2', 'address2'),
    ('address3', 'address3'),
    ('address4', 'address4'),
    ('city', 'city'),
    ('region', 'region'),
    ('postal_code', 'postal_code'),
    ('country', 'country'),
    ('phone', 'phone'),
    ('fax', 'fax'),
    ('telex', 'telex'),
    ('cable', 'cable'),
    ('phone1', 'phone1'),
    ('phone2', 'phone2'),
    ('phone3', 'phone3'),
    ('contact1', 'contact1'),
    ('contact2', 'contact2'),
    ('contact3', 'contact3'),
    ('supp_pay', 'supp_pay'),
    ('status', 'status'),
    ('ship_from', 'ship_from'),
    ('remarks', 'remarks'),
    ('cdate', 'cdate'),
    ('adate', 'adate'),
    ('extradate1', 'extradate1'),
    ('extradate2', 'extradate2'),
    ('extradate3', 'extradate3'),
    ('homepage', 'homepage'),
    ('email1', 'email1'),
    ('email2', 'email2'),
    ('email3', 'email3'),
    ('audit', 'audit'),
]


def _serialize_value(value):
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def main():
    parser = argparse.ArgumentParser(description="Export SUPPLIER rows to JSON.")
    parser.add_argument('--dsn', default=os.getenv('FOXPRO_DSN', 'Fox Pro ERP'))
    parser.add_argument('--limit', type=int, default=1)
    parser.add_argument('--all', action='store_true', help='Export all rows (ignore --limit)')
    parser.add_argument('--since-hours', type=int, default=None, help='Filter by adate in last N hours')
    parser.add_argument('--since-days', type=int, default=None, help='Filter by adate in last N days')
    parser.add_argument('--order-by', default='supplier_id')
    parser.add_argument('--output', default=os.path.join(os.getcwd(), 'foxpro_suppliers_export.json'))
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
            f"FROM SUPPLIER{where_clause} ORDER BY {args.order_by}"
        )
    else:
        query = (
            f"SELECT TOP {args.limit} {', '.join(select_fields)} "
            f"FROM SUPPLIER{where_clause} ORDER BY {args.order_by}"
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
