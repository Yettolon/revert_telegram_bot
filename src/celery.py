from celery import Celery
from celery.schedules import crontab
from src.config import settings

celery_app = Celery(
    "revert_bot",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.autodiscover_tasks(["src.tasks"])

celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
)


celery_app.conf.beat_schedule = {
    "check-positions-every-minute": {
        "task": "src.tasks.positions.check_all_positions",
        "schedule": crontab(minute="*"),
    },
}
