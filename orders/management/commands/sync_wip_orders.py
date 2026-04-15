from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from orders.models import (
    Department,
    SOMain,
    SODetail,
    WipOrder,
    WipTask,
    WipTypeDefinition,
)

User = get_user_model()


def _lead_time_days(sc_date, crd):
    if not sc_date or not crd:
        return None
    return (crd.date() - sc_date.date()).days


def _select_wip_type(department, lead_time):
    if not department or lead_time is None:
        return None
    return (
        WipTypeDefinition.objects.filter(
            department=department,
            is_active=True,
            lead_time_min__lte=lead_time,
            lead_time_max__gte=lead_time,
        )
        .order_by('lead_time_min')
        .first()
    )


def _compute_planned_dates(crd_date, checkpoints):
    planned = {}
    last_date = None
    for cp in checkpoints:
        if cp.rule_type == 'crd_offset':
            planned_date = crd_date + timedelta(days=cp.offset_days)
        else:
            if last_date is None:
                continue
            planned_date = last_date + timedelta(days=cp.offset_days)
        planned[cp.id] = planned_date
        last_date = planned_date
    return planned


class Command(BaseCommand):
    help = "Sync WIP orders and tasks from SOMAIN/SODETAIL (SC Date within 30 days of today)."

    def handle(self, *args, **options):
        # Auto-sync is now disabled by default. To re-enable, set
        # ENABLE_WIP_AUTO_SYNC = True in Django settings.
        if not getattr(settings, "ENABLE_WIP_AUTO_SYNC", False):
            self.stdout.write(
                self.style.WARNING(
                    "WIP auto-sync is disabled (ENABLE_WIP_AUTO_SYNC is False). "
                    "Skipping sync_wip_orders."
                )
            )
            return

        created_orders = 0
        updated_orders = 0
        created_tasks = 0
        updated_tasks = 0

        today = date.today()
        sc_date_from = today - timedelta(days=30)
        sc_date_to = today + timedelta(days=30)

        somain_qs = SOMain.objects.filter(
            sc_date__date__gte=sc_date_from,
            sc_date__date__lte=sc_date_to,
        )
        somain_map = {o.sc_number: o for o in somain_qs}
        sc_numbers = set(somain_map.keys())
        user_ids = {o.user_id for o in somain_map.values() if o.user_id}
        user_map = {u.username: u for u in User.objects.filter(username__in=user_ids)}
        if not sc_numbers:
            self.stdout.write(self.style.WARNING(
                "No SOMain orders with SC Date within 30 days of today. Nothing to sync."
            ))
            return

        for detail in SODetail.objects.filter(sc_number__in=sc_numbers).iterator():
            somain = somain_map.get(detail.sc_number)
            if not somain:
                continue

            department = None
            if somain.department_no:
                department, _ = Department.objects.get_or_create(
                    code=somain.department_no,
                    defaults={'name': somain.department_no},
                )

            lead_time = _lead_time_days(somain.sc_date, somain.crd)
            wip_type = _select_wip_type(department, lead_time)
            assigned_user = user_map.get(somain.user_id) if somain.user_id else None

            wip_order, created = WipOrder.objects.update_or_create(
                somain=somain,
                sodetail=detail,
                defaults={
                    'department': department,
                    'assigned_user': assigned_user,
                    'wip_type': wip_type,
                    'lead_time_days': lead_time,
                },
            )
            if created:
                created_orders += 1
            else:
                updated_orders += 1

            if not wip_type or not somain.crd:
                continue

            checkpoints = list(wip_type.checkpoints.all())
            planned_dates = _compute_planned_dates(somain.crd.date(), checkpoints)

            for cp in checkpoints:
                planned_date = planned_dates.get(cp.id)
                status = 'pending'
                task, task_created = WipTask.objects.get_or_create(
                    wip_order=wip_order,
                    checkpoint=cp,
                    defaults={
                        'planned_date': planned_date,
                        'status': status,
                    },
                )
                if task_created:
                    created_tasks += 1
                else:
                    task.planned_date = planned_date
                    if task.action_date:
                        task.status = 'completed'
                    elif planned_date and planned_date < date.today():
                        task.status = 'overdue'
                    else:
                        task.status = 'pending'
                    task.save(update_fields=['planned_date', 'status', 'kpi_days'])
                    updated_tasks += 1

        self.stdout.write(self.style.SUCCESS(
            f"WIP Orders created: {created_orders}, updated: {updated_orders}. "
            f"Tasks created: {created_tasks}, updated: {updated_tasks}."
        ))
