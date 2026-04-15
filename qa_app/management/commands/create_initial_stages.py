"""
Management command to create initial stages for existing products
"""
from django.core.management.base import BaseCommand
from qa_app.models import Product, ProductStage


class Command(BaseCommand):
    help = 'Create initial QA stages (R/A/F/M/G) for all products that don\'t have them'

    def handle(self, *args, **options):
        products = Product.objects.all()
        created_count = 0

        for product in products:
            stages_created = 0
            for stage_code, stage_name in ProductStage.STAGE_CHOICES:
                stage, created = ProductStage.objects.get_or_create(
                    product=product,
                    stage_type=stage_code,
                    defaults={'status': 'not_started'}
                )
                if created:
                    stages_created += 1

            if stages_created > 0:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created {stages_created} stages for {product.bmuk_item_no}'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted. Created stages for {created_count} products.'
            )
        )

