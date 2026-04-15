from django.core.management.base import BaseCommand

from orders.models import WorkflowGridTemplate, WorkflowGridEntry, SODetail


class Command(BaseCommand):
    help = "Create workflow entries for all SODetail rows."

    def add_arguments(self, parser):
        parser.add_argument('--template', required=True, help='Template slug (repeat/new)')

    def handle(self, *args, **options):
        template = WorkflowGridTemplate.objects.get(slug=options['template'])

        created = 0
        for detail in SODetail.objects.all().iterator():
            obj, was_created = WorkflowGridEntry.objects.get_or_create(
                template=template,
                order_detail=detail,
                defaults={
                    'department': None,
                    'assigned_user': None,
                    'data': {},
                },
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Created {created} entries for {template.slug}"))
