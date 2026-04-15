from datetime import date

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from orders.models import UserProfile, WipTask


class Command(BaseCommand):
    help = "Send daily WIP reminder emails to users and department supervisors."

    def handle(self, *args, **options):
        today = date.today()

        due_today = WipTask.objects.filter(
            planned_date=today,
            status__in=['pending', 'overdue'],
        ).select_related(
            'wip_order', 'wip_order__sodetail', 'wip_order__somain',
            'wip_order__department', 'wip_order__assigned_user', 'checkpoint',
        )

        overdue = WipTask.objects.filter(
            planned_date__lt=today,
            status__in=['pending', 'overdue'],
        ).select_related(
            'wip_order', 'wip_order__sodetail', 'wip_order__somain',
            'wip_order__department', 'wip_order__assigned_user', 'checkpoint',
        )

        tasks_by_user = {}

        for task in list(due_today) + list(overdue):
            order = task.wip_order
            recipients = set()
            if order.assigned_user and order.assigned_user.email:
                recipients.add(order.assigned_user.email)

            if order.department:
                supervisors = UserProfile.objects.filter(
                    department=order.department,
                    is_supervisor=True,
                ).select_related('user')
                for sup in supervisors:
                    if sup.user.email:
                        recipients.add(sup.user.email)

            for email in recipients:
                tasks_by_user.setdefault(email, {'due_today': [], 'overdue': []})
                if task.planned_date == today:
                    tasks_by_user[email]['due_today'].append(task)
                else:
                    tasks_by_user[email]['overdue'].append(task)

        sent_count = 0
        for email, data in tasks_by_user.items():
            context = {
                'email': email,
                'due_today': data['due_today'],
                'overdue': data['overdue'],
                'date': today,
            }
            html_message = render_to_string('emails/wip_reminder.html', context)
            plain_message = strip_tags(html_message)
            send_mail(
                subject=f"WIP Reminder - {today.isoformat()}",
                message=plain_message,
                from_email=None,
                recipient_list=[email],
                html_message=html_message,
                fail_silently=False,
            )
            sent_count += 1

        self.stdout.write(self.style.SUCCESS(f"Sent {sent_count} reminder emails."))
