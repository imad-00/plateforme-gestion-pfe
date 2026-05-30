import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "phase-closing-soon-reminders": {
        "task": "apps.campaigns.tasks.send_phase_closing_soon_reminders",
        "schedule": crontab(minute="*/15"),  # every 15 minutes
    },
}


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
