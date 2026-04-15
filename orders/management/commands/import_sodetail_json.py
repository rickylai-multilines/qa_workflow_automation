import datetime
import json
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from orders.models import SODetail

FIELD_MAP = {
    'so_id': 'sc_number',
    'po_id': 'po_number',
    'product_id': 'product_id',
    'bar_code': 'barcode',
    'custref': 'cust_item_code',
    'quantity': 'qty',
    'ctn_unit': 'carton_unit',
    'unit_price': 'unit_price',
    'supplier_id': 'supplier_id',
    'customer_id': 'customer_id',
    'product_name': 'product_name',
    'sequence': 'seq',
    'desc': 'item_description',
    'desc_': 'item_description',
    'adate': 'mod_time',
    'marks': 'marks',
    'extra_1': 'supplier_item_code',
    'extra_2': 'bmi_item_code',
    'extra_3': 'french_item_code',
    'adatetime': 'last_mod_time',
    'net_wt': 'net_wt',
    'grs_wt': 'gross_wt',
    'posted': 'posted',
    'ctn_qty': 'qty_per_carton',
    'ctn_pack': 'carton_pack_unit',
    'length': 'length',
    'hight': 'hight',
    'width': 'width',
    'measure_unit': 'measure_unit',
    'packing': 'packing',
    'cbm': 'cbm',
    'cuf': 'cuf',
    'cuft': 'cuf',
    'nb_ctns': 'no_of_carton',
    'custom_code': 'haos_code',
    'attribute4': 'brand',
}

DECIMAL_FIELDS = {
    'unit_price',
    'seq',
    'net_wt',
    'gross_wt',
    'qty_per_carton',
    'length',
    'hight',
    'width',
    'cbm',
    'cuf',
    'no_of_carton',
}

DATETIME_FIELDS = {
    'mod_time',
    'last_mod_time',
}


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
    for fmt in ('%Y/%m/%d %H:%M', '%Y/%m/%d %H:%M:%S', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.datetime.strptime(str(value), fmt)
        except ValueError:
            continue
    dt = datetime.datetime.fromisoformat(str(value))
    return timezone.make_aware(dt) if timezone.is_naive(dt) else dt


def _parse_decimal(value):
    if value is None or value == '':
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _split_adate(value):
    if value is None:
        return None, None
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
        return None, trimmed[-20:]
    return None, None


def _sanitize_text(value):
    if value is None:
        return None
    text = str(value)
    if '\x00' in text:
        text = text.replace('\x00', '')
    return text.strip() if text else text


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


def _latest_timestamp(row):
    mod_time_raw = row.get('adate')
    mod_time, _ = _split_adate(mod_time_raw)
    last_mod = row.get('adatetime')
    last_mod = _parse_datetime(last_mod)
    mod_time = _parse_datetime(mod_time) if mod_time else None
    if mod_time and last_mod:
        return max(mod_time, last_mod)
    return mod_time or last_mod


class Command(BaseCommand):
    help = "Import SODTL JSON export into PostgreSQL SODETAIL table."

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

        latest_by_key = {}
        for row in rows:
            key = (row.get('so_id'), row.get('product_id'), row.get('po_id'))
            if not key[0]:
                continue
            candidate_ts = _latest_timestamp(row)
            existing = latest_by_key.get(key)
            if not existing or (candidate_ts and candidate_ts > existing[0]):
                latest_by_key[key] = (candidate_ts, row)

        created_count = 0
        updated_count = 0

        for _, row in latest_by_key.values():
            mapped = {}
            mod_time, mod_by = _split_adate(row.get('adate'))
            for source_field, target_field in FIELD_MAP.items():
                value = row.get(source_field)
                if target_field == 'mod_time':
                    value = mod_time
                if target_field == 'posted':
                    value = _parse_bool(value)
                if target_field == 'qty' and value not in (None, ''):
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

            mapped['mod_by'] = _sanitize_text(mod_by)
            sc_number = mapped.pop('sc_number', None)
            po_number = mapped.pop('po_number', None)
            product_id = mapped.pop('product_id', None)
            if not sc_number:
                continue

            obj, created = SODetail.objects.update_or_create(
                sc_number=sc_number,
                po_number=po_number,
                product_id=product_id,
                defaults=mapped,
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

            self.stdout.write(self.style.SUCCESS(
                f"Imported SODETAIL {obj.sc_number} - {obj.product_id}",
            ))

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created: {created_count}, Updated: {updated_count}",
            ),
        )
