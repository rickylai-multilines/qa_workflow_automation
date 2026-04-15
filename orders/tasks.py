from datetime import timedelta

from celery import shared_task
from celery.utils.log import get_task_logger
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from .models import OrderTask, UserDashboardPreference

logger = get_task_logger(__name__)


@shared_task(name='check_and_update_task_alerts')
def check_and_update_task_alerts():
    """
    Run every minute to check task deadlines and update alert status.
    """
    try:
        five_minutes_ago = timezone.now() - timedelta(minutes=5)
        pending_tasks = OrderTask.objects.filter(
            status__in=['pending', 'in_progress'],
            updated_at__lt=five_minutes_ago,
        )

        updated_count = 0
        for task in pending_tasks:
            old_status = task.alert_status
            task.update_alert_status()

            if old_status != task.alert_status:
                updated_count += 1
                logger.info(
                    "Updated alert status for task %s: %s -> %s",
                    task.id,
                    old_status,
                    task.alert_status,
                )
                if task.assigned_to and task.should_alert():
                    send_task_alert.delay(task.id)

        logger.info("Alert check completed. Updated %s tasks.", updated_count)
        return {'updated': updated_count}
    except Exception as exc:
        logger.error("Error in check_and_update_task_alerts: %s", str(exc))
        raise


@shared_task(name='send_daily_email_summary')
def send_daily_email_summary():
    """
    Daily scheduled task to send email summary of outstanding tasks.
    """
    try:
        users_with_email = User.objects.filter(
            dashboard_preference__daily_email_enabled=True,
            is_active=True,
        ).select_related('dashboard_preference')

        email_count = 0
        for user in users_with_email:
            prefs = user.dashboard_preference
            if not prefs.send_warning_alerts and not prefs.send_critical_alerts:
                continue

            outstanding_tasks = OrderTask.objects.filter(
                assigned_to=user,
                status__in=['pending', 'in_progress'],
            ).select_related('order', 'stage').order_by('planned_date')

            if not outstanding_tasks.exists():
                logger.info("No outstanding tasks for %s", user.username)
                continue

            critical_tasks = [t for t in outstanding_tasks if t.alert_status == 'critical']
            warning_tasks = [t for t in outstanding_tasks if t.alert_status == 'warning']
            normal_tasks = [t for t in outstanding_tasks if t.alert_status == 'normal']

            if not prefs.send_critical_alerts:
                critical_tasks = []
            if not prefs.send_warning_alerts:
                warning_tasks = []

            if not critical_tasks and not warning_tasks:
                continue

            send_task_summary_email.delay(
                user_id=user.id,
                critical_tasks=[t.id for t in critical_tasks],
                warning_tasks=[t.id for t in warning_tasks],
                normal_tasks=[t.id for t in normal_tasks],
            )
            email_count += 1
            logger.info("Queued email for %s", user.username)

        logger.info("Daily email summary task completed. %s emails queued.", email_count)
        return {'emails_sent': email_count}
    except Exception as exc:
        logger.error("Error in send_daily_email_summary: %s", str(exc))
        raise


@shared_task(name='send_task_summary_email')
def send_task_summary_email(user_id, critical_tasks, warning_tasks, normal_tasks):
    """
    Send formatted HTML email with task summary to specific user.
    """
    try:
        user = User.objects.get(id=user_id)

        critical = OrderTask.objects.filter(id__in=critical_tasks).select_related('order', 'stage')
        warning = OrderTask.objects.filter(id__in=warning_tasks).select_related('order', 'stage')
        normal = OrderTask.objects.filter(id__in=normal_tasks).select_related('order', 'stage')

        context = {
            'user': user,
            'critical_tasks': list(critical),
            'warning_tasks': list(warning),
            'normal_tasks': list(normal),
            'total_critical': len(critical_tasks),
            'total_warning': len(warning_tasks),
            'total_normal': len(normal_tasks),
            'generated_at': timezone.now(),
        }

        html_message = render_to_string('emails/task_summary.html', context)
        plain_message = strip_tags(html_message)

        send_mail(
            subject=(
                f"Outstanding Tasks Summary - {len(critical_tasks)} "
                f"Critical, {len(warning_tasks)} Warning"
            ),
            message=plain_message,
            from_email=None,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info("Email sent to %s", user.email)
        return {'status': 'sent', 'recipient': user.email}
    except User.DoesNotExist:
        logger.error("User %s not found", user_id)
    except Exception as exc:
        logger.error("Error sending email: %s", str(exc))
        raise


@shared_task(name='send_task_alert')
def send_task_alert(task_id):
    """
    Send immediate alert email when task becomes critical/warning.
    """
    try:
        task = OrderTask.objects.select_related('order', 'stage', 'assigned_to').get(id=task_id)

        if not task.assigned_to or not task.should_alert():
            return

        prefs, _ = UserDashboardPreference.objects.get_or_create(user=task.assigned_to)
        if task.is_overdue() and not prefs.send_critical_alerts:
            return
        if not task.is_overdue() and not prefs.send_warning_alerts:
            return

        if task.last_alert_sent and timezone.now() - task.last_alert_sent < timedelta(hours=24):
            logger.info("Alert already sent for task %s in last 24 hours", task.id)
            return

        context = {
            'task': task,
            'order': task.order,
            'stage': task.stage,
            'days_until_due': task.days_until_due(),
            'is_overdue': task.is_overdue(),
        }

        html_message = render_to_string('emails/task_alert.html', context)
        plain_message = strip_tags(html_message)

        send_mail(
            subject=(
                f"{'OVERDUE' if task.is_overdue() else 'URGENT'} - "
                f"{task.order.order_number}: {task.stage.stage_name if task.stage else 'Task'}"
            ),
            message=plain_message,
            from_email=None,
            recipient_list=[task.assigned_to.email],
            html_message=html_message,
            fail_silently=False,
        )

        task.last_alert_sent = timezone.now()
        task.save(update_fields=['last_alert_sent'])

        logger.info("Alert sent to %s for task %s", task.assigned_to.email, task.id)
    except OrderTask.DoesNotExist:
        logger.error("Task %s not found", task_id)
    except Exception as exc:
        logger.error("Error sending task alert: %s", str(exc))
        raise
