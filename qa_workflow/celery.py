import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qa_workflow.settings')

app = Celery('qa_workflow')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'check-task-alerts-every-minute': {
        'task': 'orders.tasks.check_and_update_task_alerts',
        'schedule': crontab(),
    },
    'send-daily-email-summary': {
        'task': 'orders.tasks.send_daily_email_summary',
        'schedule': crontab(hour=9, minute=0),
    },
}

app.conf.timezone = 'UTC'


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
