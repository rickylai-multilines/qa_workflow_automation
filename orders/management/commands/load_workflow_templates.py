import os

import openpyxl
from django.core.management.base import BaseCommand, CommandError

from orders.models import WorkflowGridTemplate, WorkflowGridColumn


def _find_header_row(rows):
    for idx, row in enumerate(rows):
        if any(cell.strip().lower() == 'merchandiser' for cell in row):
            return idx
    return None


class Command(BaseCommand):
    help = "Load workflow templates and columns from Excel files."

    def add_arguments(self, parser):
        parser.add_argument('--repeat', required=True, help='Path to Repeat Product Order check.xlsx')
        parser.add_argument('--new', required=True, help='Path to New Product Order check.xlsx')

    def handle(self, *args, **options):
        files = {
            'repeat': options['repeat'],
            'new': options['new'],
        }

        for slug, path in files.items():
            if not os.path.exists(path):
                raise CommandError(f"File not found: {path}")

            wb = openpyxl.load_workbook(path, data_only=True)
            ws = wb.active
            rows = [
                [str(c).strip() if c is not None else '' for c in r]
                for r in ws.iter_rows(min_row=1, max_row=10, values_only=True)
            ]
            header_idx = _find_header_row(rows)
            if header_idx is None:
                raise CommandError(f"Could not find header row in {path}")

            group_row = rows[header_idx - 1] if header_idx > 0 else [''] * len(rows[header_idx])
            header_row = rows[header_idx]

            template, _ = WorkflowGridTemplate.objects.update_or_create(
                slug=slug,
                defaults={
                    'name': f"{slug.title()} Product Order Workflow",
                    'source_file': path,
                    'is_active': True,
                },
            )

            WorkflowGridColumn.objects.filter(template=template).delete()

            last_group = ''
            order = 0
            for col_idx, label in enumerate(header_row):
                label = label.strip()
                if not label:
                    continue
                group = group_row[col_idx].strip() if col_idx < len(group_row) else ''
                if group:
                    last_group = group
                group = group or last_group

                data_type = 'text'
                if 'date' in label.lower():
                    data_type = 'date'
                if label.lower() in {'ok?', 'result'}:
                    data_type = 'text'

                WorkflowGridColumn.objects.create(
                    template=template,
                    key=f"c{col_idx}",
                    label=label,
                    group_label=group,
                    order=order,
                    data_type=data_type,
                )
                order += 1

            self.stdout.write(self.style.SUCCESS(f"Loaded template: {template.slug} ({order} columns)"))
