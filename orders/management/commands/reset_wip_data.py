from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from django.db import connection

from orders.models import WipOrder, WipTask


class Command(BaseCommand):
    help = (
        "Delete all WIP orders and tasks, and reset the auto-increment/sequence "
        "for the WipTask primary key."
    )

    def handle(self, *args, **options):
        self.stdout.write("Deleting WIP tasks...")
        WipTask.objects.all().delete()

        self.stdout.write("Deleting WIP orders...")
        WipOrder.objects.all().delete()

        # Reset the database sequence for WipTask (and WipOrder for convenience)
        self.stdout.write("Resetting database sequences for WipTask (and WipOrder)...")
        sql_statements = connection.ops.sequence_reset_sql(
            no_style(),
            [WipTask, WipOrder],
        )
        with connection.cursor() as cursor:
            for sql in sql_statements:
                cursor.execute(sql)

        self.stdout.write(self.style.SUCCESS("All WIP orders/tasks cleared and sequences reset."))

