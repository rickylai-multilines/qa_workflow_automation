import os
import re

import openpyxl
from django.core.management.base import BaseCommand, CommandError

from orders.models import Department, WipTypeDefinition, WipCheckpointDefinition


LEAD_TIME_PATTERN = re.compile(r'lead time\s*=\s*(\d+)\s*-\s*(\d+)', re.IGNORECASE)
CRD_OFFSET_PATTERN = re.compile(r'crd\s*[-+]\s*\d+', re.IGNORECASE)
OFFSET_PATTERN = re.compile(r'([+-])\s*(\d+)\s*days', re.IGNORECASE)


def _find_header_row(rows):
    for idx, row in enumerate(rows):
        if any(cell.strip().lower() == 'merchandiser' for cell in row):
            return idx
    return None


def _parse_lead_time(def_text):
    match = LEAD_TIME_PATTERN.search(def_text)
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))


def _parse_rule(rule_text):
    text = rule_text.strip()
    if not text or text.upper() == 'NA':
        return None, None
    if 'CRD' in text.upper():
        offset_match = OFFSET_PATTERN.search(text)
        if offset_match:
            sign = -1 if offset_match.group(1) == '-' else 1
            return 'crd_offset', sign * int(offset_match.group(2))
    if '+' in text:
        offset_match = OFFSET_PATTERN.search(text)
        if offset_match:
            return 'prev_offset', int(offset_match.group(2))
    return None, None


class Command(BaseCommand):
    help = "Load WIP type definitions from WIP type definition.xlsx."

    def add_arguments(self, parser):
        parser.add_argument('--file', required=True, help='Path to WIP type definition.xlsx')
        parser.add_argument('--department-code', required=True, help='Department code to apply definitions')

    def handle(self, *args, **options):
        path = options['file']
        dept_code = options['department_code']

        if not os.path.exists(path):
            raise CommandError(f"File not found: {path}")

        department, _ = Department.objects.get_or_create(
            code=dept_code,
            defaults={'name': dept_code},
        )

        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb.active
        rows = [
            [str(c).strip() if c is not None else '' for c in r]
            for r in ws.iter_rows(min_row=1, max_row=60, values_only=True)
        ]

        header_idx = _find_header_row(rows)
        if header_idx is None:
            raise CommandError("Header row not found.")

        header_row = rows[header_idx]
        wip_type_idx = header_row.index('WIP TYPE') if 'WIP TYPE' in header_row else None
        wip_def_idx = None
        for idx, col in enumerate(header_row):
            if 'WIP TYPE DEFINITION' in col:
                wip_def_idx = idx
                break
        if wip_type_idx is None or wip_def_idx is None:
            raise CommandError("WIP TYPE or definition columns not found.")

        checkpoint_labels = []
        for idx, label in enumerate(header_row):
            if idx <= wip_def_idx:
                continue
            if label:
                checkpoint_labels.append((idx, label))

        WipTypeDefinition.objects.filter(department=department).delete()

        created_types = 0
        created_checkpoints = 0

        for row in rows[header_idx + 1:]:
            wip_type = row[wip_type_idx].strip()
            wip_def = row[wip_def_idx].strip()
            if not wip_type or 'lead time' not in wip_def.lower():
                continue

            lead_min, lead_max = _parse_lead_time(wip_def)
            if lead_min is None:
                continue

            wip_obj = WipTypeDefinition.objects.create(
                department=department,
                name=wip_type,
                lead_time_min=lead_min,
                lead_time_max=lead_max,
                is_active=True,
            )
            created_types += 1

            order = 0
            for idx, label in checkpoint_labels:
                rule_text = row[idx].strip() if idx < len(row) else ''
                rule_type, offset = _parse_rule(rule_text)
                if rule_type is None:
                    continue
                WipCheckpointDefinition.objects.create(
                    wip_type=wip_obj,
                    label=label,
                    order=order,
                    rule_type=rule_type,
                    offset_days=offset,
                )
                order += 1
                created_checkpoints += 1

        self.stdout.write(self.style.SUCCESS(
            f"Loaded {created_types} WIP types and {created_checkpoints} checkpoints for {department.code}"
        ))
