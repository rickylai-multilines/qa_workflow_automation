from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SOMain',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sc_number', models.CharField(db_column='SCNumber', max_length=20, unique=True)),
                ('sc_status', models.CharField(blank=True, db_column='SCStatus', max_length=20, null=True)),
                ('created_by', models.CharField(blank=True, db_column='CreatedBy', max_length=20, null=True)),
                ('sc_date', models.DateTimeField(blank=True, db_column='SCDate', null=True)),
                ('salesman', models.CharField(blank=True, db_column='Salesman', max_length=50, null=True)),
                ('cu_code', models.CharField(blank=True, db_column='CuCode', max_length=20, null=True)),
                ('ship_via', models.CharField(blank=True, db_column='ShipVia', max_length=60, null=True)),
                ('crd', models.DateTimeField(blank=True, db_column='CRD', null=True)),
                ('port_of_load', models.CharField(blank=True, db_column='PortofLoad', max_length=20, null=True)),
                ('origin', models.CharField(blank=True, db_column='Origin', max_length=20, null=True)),
                ('ship_to', models.CharField(blank=True, db_column='ShipTo', max_length=20, null=True)),
                ('port_of_disch', models.CharField(blank=True, db_column='PortofDisch', max_length=60, null=True)),
                ('cust_order', models.CharField(blank=True, db_column='CustOrder', max_length=60, null=True)),
                ('order_date', models.DateTimeField(blank=True, db_column='OrderDate', null=True)),
                ('payment_term_code', models.CharField(blank=True, db_column='PaymrntTermCode', max_length=20, null=True)),
                ('net_total_amt', models.DecimalField(blank=True, db_column='NetTotalAmt', decimal_places=4, max_digits=12, null=True)),
                ('doc_net_total_amt', models.DecimalField(blank=True, db_column='DocNetTotalAmt', decimal_places=4, max_digits=12, null=True)),
                ('gross_total_amt', models.DecimalField(blank=True, db_column='GrossTotalAmt', decimal_places=4, max_digits=12, null=True)),
                ('remark', models.TextField(blank=True, db_column='Remark', null=True)),
                ('last_po_no', models.CharField(blank=True, db_column='LastPONo', max_length=20, null=True)),
                ('container_qty', models.CharField(blank=True, db_column='ContainerQty', max_length=40, null=True)),
                ('container_size', models.CharField(blank=True, db_column='ContainerSize', max_length=40, null=True)),
                ('mod_time', models.DateTimeField(blank=True, db_column='ModTime', null=True)),
                ('posted', models.BooleanField(blank=True, db_column='Posted', null=True)),
                ('department_no', models.CharField(blank=True, db_column='DepartmentNo', max_length=10, null=True)),
                ('trade_term', models.CharField(blank=True, db_column='TradeTerm', max_length=20, null=True)),
                ('company', models.CharField(blank=True, db_column='Company', max_length=20, null=True)),
                ('total_qty', models.DecimalField(blank=True, db_column='TotalQty', decimal_places=4, max_digits=12, null=True)),
                ('total_cbm', models.DecimalField(blank=True, db_column='TotalCBM', decimal_places=4, max_digits=12, null=True)),
                ('total_gross_wt', models.DecimalField(blank=True, db_column='TotalGrossWt', decimal_places=4, max_digits=12, null=True)),
                ('user_id', models.CharField(blank=True, db_column='UserID', max_length=20, null=True)),
            ],
            options={
                'db_table': 'SOMAIN',
            },
        ),
        migrations.AddIndex(
            model_name='somain',
            index=models.Index(fields=['sc_number'], name='orders_som_sc_numb_155e09_idx'),
        ),
        migrations.AddIndex(
            model_name='somain',
            index=models.Index(fields=['sc_date'], name='orders_som_sc_date_f0fce0_idx'),
        ),
        migrations.AddIndex(
            model_name='somain',
            index=models.Index(fields=['crd'], name='orders_som_crd_4d0f8c_idx'),
        ),
    ]
