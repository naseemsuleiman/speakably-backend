# myapp/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from myapp.tasks import run_send_reminders
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def start():
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")

    logger.info(f"📬 Scheduler started at {timezone.now()}")

    scheduler.add_job(
        run_send_reminders,                   # <-- now a top-level function
        trigger="interval",
        minutes=1,
        id="send_reminders",
        replace_existing=True,
    )

    scheduler.start()
