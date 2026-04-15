import datetime
import json
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from orders.models import Product

FIELD_MAP = {
    'product_id': 'product_id',
    'bar_code': 'barcode',
    'lookupid': 'customer_item_code',
    'class_id': 'supplier_item_code',
    'class1': 'department_no',
    'packing': 'packing',
    'attribute1': 'material',
    'attribute3': 'copy_from_product_id',
    'attribute4': 'brand',
    'attribute5': 'german_item_code',
    'supplier_id': 'supplier_id',
    'product_name': 'product_name',
    'unit_price': 'unit_price',
    'unit_price2': 'unit_price1',
    'unit_price3': 'unit_price2',
    'unit_cost': 'unit_cost',
    'ctn_qty': 'qty_per_carton',
    'ctn_unit': 'carton_unit',
    'ctn_pack': 'per_carton_unit',
    'ctn_packqty': 'per_carton_qty',
    'length': 'length',
    'hight': 'hight',
    'width': 'width',
    'measure_unit': 'measure_unit',
    'cuft': 'cuft',
    'cbm': 'cbm',
    'net_wt': 'net_wt',
    'grs_wt': 'gross_wt',
    'group1': 'main_category_id',
    'group2': 'sub_category_id',
    'quota_desc': 'french_item_code',
    'custom_code': 'hs_code',
    'discontinued': 'inactive',
    'desc': 'description',
    'desc_': 'description',
    'cdate': 'create_time',
    'adate': 'mod_time',
    'photo': 'image',
    'price_term': 'unit_price_term',
    'price_term2': 'unit_price_term1',
    'price_term3': 'unit_price_term2',
    'cost_term': 'unit_cost_term',
    'date6': 'lab_test_till_date',
    'creator': 'create_by',
}

DECIMAL_FIELDS = {
    'unit_price',
    'unit_price1',
    'unit_price2',
    'unit_cost',
    'per_carton_qty',
    'length',
    'hight',
    'width',
    'cuft',
    'cbm',
    'net_wt',
    'gross_wt',
}

DATETIME_FIELDS = {
    'create_time',
    'mod_time',
    'lab_test_till_date',
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
    if not text:
        return None
    try:
        dt = datetime.datetime.fromisoformat(text)
        return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
    except ValueError:
        pass
    for fmt in ('%Y/%m/%d %H:%M', '%Y/%m/%d %H:%M:%S', '%Y-%m-%d %H:%M:%S'):
        try:
            dt = datetime.datetime.strptime(text, fmt)
            return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
        except ValueError:
            continue
    try:
        excel_serial = float(text)
        base = datetime.datetime(1899, 12, 30)
        dt = base + datetime.timedelta(days=excel_serial)
        return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
    except ValueError:
        return None


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
    if isinstance(value, (datetime.datetime, datetime.date)):
        return _parse_datetime(value), None
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return None, None
        parts = trimmed.split()
        if len(parts) >= 3:
            user = parts[-1]
            time_str = " ".join(parts[:-1])
            parsed_time = _parse_datetime(time_str)
            if parsed_time:
                return parsed_time, user
        parsed_time = _parse_datetime(trimmed)
        return parsed_time, None
    return None, None


class Command(BaseCommand):
    help = "Import PRODUCTS JSON export into PostgreSQL PRODUCTS table."

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
            create_time, create_by = _split_user_datetime(row.get('cdate'))
            mod_time, mod_by = _split_user_datetime(row.get('adate'))
            for source_field, target_field in FIELD_MAP.items():
                value = row.get(source_field)
                if target_field == 'create_time':
                    value = create_time
                if target_field == 'mod_time':
                    value = mod_time
                if target_field == 'inactive':
                    value = _parse_bool(value)
                if target_field == 'qty_per_carton' and value not in (None, ''):
                    try:
                        value = int(value)
                    except (ValueError, TypeError):
                        value = None
                if target_field in DATETIME_FIELDS:
                    value = _parse_datetime(value)
                elif target_field in DECIMAL_FIELDS:
                    value = _parse_decimal(value)
                elif isinstance(value, str):
                    value = _sanitize_text(value)
                mapped[target_field] = value

            if not mapped.get('create_by') and create_by:
                mapped['create_by'] = _sanitize_text(create_by)
            if mod_by:
                mapped['mod_by'] = _sanitize_text(mod_by)

            product_id = _sanitize_text(mapped.pop('product_id', None))
            if not product_id:
                continue

            obj, created = Product.objects.update_or_create(
                product_id=product_id,
                defaults=mapped,
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

            self.stdout.write(self.style.SUCCESS(f"Imported PRODUCT {obj.product_id}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created: {created_count}, Updated: {updated_count}",
            ),
        )
