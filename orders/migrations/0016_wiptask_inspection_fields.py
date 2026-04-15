from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0015_supplier'),
    ]

    operations = [
        migrations.AddField(
            model_name='wiptask',
            name='inspection_by',
            field=models.CharField(
                max_length=10,
                null=True,
                blank=True,
                choices=[
                    ('MTL', 'MTL'),
                    ('3RD', '3rd'),
                    ('SELF', 'Self'),
                ],
            ),
        ),
        migrations.AddField(
            model_name='wiptask',
            name='inspection_result',
            field=models.CharField(
                max_length=10,
                null=True,
                blank=True,
                choices=[
                    ('PASS', 'Pass'),
                    ('FAIL', 'Fail'),
                ],
            ),
        ),
    ]

