from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_sodetail'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('code', models.CharField(max_length=20, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='WorkflowGridTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('slug', models.SlugField(max_length=50, unique=True)),
                ('source_file', models.CharField(blank=True, max_length=255)),
                ('is_active', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_supervisor', models.BooleanField(default=False)),
                ('department', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='orders.department')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='orders_profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='WorkflowGridColumn',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=100)),
                ('label', models.CharField(max_length=200)),
                ('group_label', models.CharField(blank=True, max_length=200)),
                ('order', models.IntegerField()),
                ('data_type', models.CharField(choices=[('text', 'Text'), ('date', 'Date'), ('number', 'Number'), ('boolean', 'Boolean')], default='text', max_length=20)),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='columns', to='orders.workflowgridtemplate')),
            ],
            options={
                'ordering': ['order'],
                'unique_together': {('template', 'key')},
            },
        ),
        migrations.CreateModel(
            name='WorkflowGridEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.JSONField(blank=True, default=dict)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('assigned_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('department', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='orders.department')),
                ('order_detail', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workflow_entries', to='orders.sodetail')),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entries', to='orders.workflowgridtemplate')),
            ],
            options={
                'unique_together': {('template', 'order_detail')},
            },
        ),
        migrations.AddIndex(
            model_name='workflowgridentry',
            index=models.Index(fields=['template', 'department'], name='orders_work_templat_0f3f1e_idx'),
        ),
        migrations.AddIndex(
            model_name='workflowgridentry',
            index=models.Index(fields=['assigned_user'], name='orders_work_assigne_3a7960_idx'),
        ),
    ]
