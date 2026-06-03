from celery import Celery
from celery.schedules import crontab
from app.config import settings

# Initialize Celery App
celery_app = Celery(
    "solesentry_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Celery Configurations
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Configure auto-discovery of tasks in tasks.py
    imports=["app.tasks"]
)

# Celery Beat Schedule
celery_app.conf.beat_schedule = {
    "run-price-checks-every-5-minutes": {
        "task": "app.tasks.scheduled_scrapes_trigger_task",
        # Configurable interval from settings
        "schedule": float(settings.PRICE_CHECK_INTERVAL_SECONDS),
    }
}
