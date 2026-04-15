from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_somain'),
    ]

    operations = [
        migrations.CreateModel(
            name='SODetail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sc_number', models.CharField(db_column='SCNumber', max_length=20)),
                ('po_number', models.CharField(blank=True, db_column='PONumber', max_length=20, null=True)),
                ('product_id', models.CharField(blank=True, db_column='ProductId', max_length=50, null=True)),
                ('barcode', models.CharField(blank=True, db_column='Barcode', max_length=50, null=True)),
                ('cust_item_code', models.CharField(blank=True, db_column='CustItemCode', max_length=50, null=True)),
                ('qty', models.IntegerField(blank=True, db_column='Qty', null=True)),
                ('carton_unit', models.CharField(blank=True, db_column='CartonUnit', max_length=20, null=True)),
                ('unit_price', models.DecimalField(blank=True, db_column='UnitPrice', decimal_places=4, max_digits=12, null=True)),
                ('supplier_id', models.CharField(blank=True, db_column='SupplierId', max_length=20, null=True)),
                ('customer_id', models.CharField(blank=True, db_column='CustomerId', max_length=20, null=True)),
                ('product_name', models.CharField(blank=True, db_column='ProductName', max_length=100, null=True)),
                ('seq', models.DecimalField(blank=True, db_column='Seq', decimal_places=5, max_digits=10, null=True)),
                ('item_description', models.TextField(blank=True, db_column='ItemDescription', null=True)),
                ('mod_time', models.DateTimeField(blank=True, db_column='ModTime', null=True)),
                ('mod_by', models.CharField(blank=True, db_column='ModBy', max_length=20, null=True)),
                ('marks', models.TextField(blank=True, db_column='Marks', null=True)),
                ('supplier_item_code', models.CharField(blank=True, db_column='SupplierItemCode', max_length=30, null=True)),
                ('bmi_item_code', models.CharField(blank=True, db_column='BMIItemCode', max_length=30, null=True)),
                ('french_item_code', models.CharField(blank=True, db_column='FrenchItemCode', max_length=30, null=True)),
                ('last_mod_time', models.DateTimeField(blank=True, db_column='LastModTime', null=True)),
                ('net_wt', models.DecimalField(blank=True, db_column='NetWt', decimal_places=4, max_digits=12, null=True)),
                ('gross_wt', models.DecimalField(blank=True, db_column='GrossWt', decimal_places=4, max_digits=12, null=True)),
                ('posted', models.BooleanField(blank=True, db_column='Posted', null=True)),
                ('qty_per_carton', models.DecimalField(blank=True, db_column='QtyPerCarton', decimal_places=4, max_digits=12, null=True)),
                ('carton_pack_unit', models.CharField(blank=True, db_column='CartonPackUnit', max_length=20, null=True)),
                ('length', models.DecimalField(blank=True, db_column='Length', decimal_places=4, max_digits=12, null=True)),
                ('hight', models.DecimalField(blank=True, db_column='Hight', decimal_places=4, max_digits=12, null=True)),
                ('width', models.DecimalField(blank=True, db_column='Width', decimal_places=4, max_digits=12, null=True)),
                ('measure_unit', models.CharField(blank=True, db_column='MeasureUnit', max_length=20, null=True)),
                ('packing', models.CharField(blank=True, db_column='Packing', max_length=120, null=True)),
                ('cbm', models.DecimalField(blank=True, db_column='Cbm', decimal_places=4, max_digits=12, null=True)),
                ('cuf', models.DecimalField(blank=True, db_column='Cuf', decimal_places=4, max_digits=12, null=True)),
                ('no_of_carton', models.DecimalField(blank=True, db_column='NoOfCarton', decimal_places=4, max_digits=12, null=True)),
                ('haos_code', models.CharField(blank=True, db_column='HAOSCode', max_length=20, null=True)),
                ('brand', models.CharField(blank=True, db_column='Brand', max_length=50, null=True)),
            ],
            options={
                'db_table': 'SODETAIL',
                'unique_together': {('sc_number', 'po_number', 'product_id')},
            },
        ),
        migrations.AddIndex(
            model_name='sodetail',
            index=models.Index(fields=['sc_number'], name='orders_sod_sc_numb_1b7f97_idx'),
        ),
        migrations.AddIndex(
            model_name='sodetail',
            index=models.Index(fields=['po_number'], name='orders_sod_po_numb_6b0fa7_idx'),
        ),
        migrations.AddIndex(
            model_name='sodetail',
            index=models.Index(fields=['product_id'], name='orders_sod_product_6f8f84_idx'),
        ),
    ]
