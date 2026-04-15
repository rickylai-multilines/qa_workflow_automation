from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0004_workflow_templates'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='WipTypeDefinition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('lead_time_min', models.IntegerField()),
                ('lead_time_max', models.IntegerField()),
                ('is_active', models.BooleanField(default=True)),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wip_types', to='orders.department')),
            ],
        ),
        migrations.CreateModel(
            name='WipCheckpointDefinition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=200)),
                ('order', models.IntegerField()),
                ('rule_type', models.CharField(choices=[('crd_offset', 'CRD Offset'), ('prev_offset', 'Previous Checkpoint Offset')], max_length=20)),
                ('offset_days', models.IntegerField()),
                ('wip_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='checkpoints', to='orders.wiptypedefinition')),
            ],
            options={
                'ordering': ['order'],
                'unique_together': {('wip_type', 'order')},
            },
        ),
        migrations.CreateModel(
            name='WipOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lead_time_days', models.IntegerField(blank=True, null=True)),
                ('status', models.CharField(choices=[('open', 'Open'), ('completed', 'Completed'), ('on_hold', 'On Hold')], default='open', max_length=20)),
                ('assigned_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('department', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='orders.department')),
                ('sodetail', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wip_orders', to='orders.sodetail')),
                ('somain', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wip_orders', to='orders.somain')),
                ('wip_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='orders.wiptypedefinition')),
            ],
            options={
                'unique_together': {('somain', 'sodetail')},
            },
        ),
        migrations.CreateModel(
            name='WipTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('planned_date', models.DateField(blank=True, null=True)),
                ('action_date', models.DateField(blank=True, null=True)),
                ('kpi_days', models.IntegerField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('completed', 'Completed'), ('overdue', 'Overdue')], default='pending', max_length=20)),
                ('checkpoint', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tasks', to='orders.wipcheckpointdefinition')),
                ('wip_order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tasks', to='orders.wiporder')),
            ],
            options={
                'unique_together': {('wip_order', 'checkpoint')},
            },
        ),
        migrations.AddIndex(
            model_name='wiptypedefinition',
            index=models.Index(fields=['department', 'is_active'], name='orders_wip_departm_1c83b9_idx'),
        ),
        migrations.AddIndex(
            model_name='wiptypedefinition',
            index=models.Index(fields=['lead_time_min', 'lead_time_max'], name='orders_wip_lead_t_f1b2c0_idx'),
        ),
        migrations.AddIndex(
            model_name='wiporder',
            index=models.Index(fields=['department', 'status'], name='orders_wip_departm_287476_idx'),
        ),
        migrations.AddIndex(
            model_name='wiporder',
            index=models.Index(fields=['assigned_user'], name='orders_wip_assigne_7e6b2a_idx'),
        ),
        migrations.AddIndex(
            model_name='wiptask',
            index=models.Index(fields=['planned_date'], name='orders_wip_planned_6d8a27_idx'),
        ),
        migrations.AddIndex(
            model_name='wiptask',
            index=models.Index(fields=['status'], name='orders_wip_status_2e9d43_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='wiptypedefinition',
            unique_together={('department', 'name')},
        ),
    ]
