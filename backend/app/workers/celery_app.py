from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

_redis_url = settings.redis_url
_broker_use_ssl = _redis_url.startswith("rediss://")

celery_app = Celery(
    "context_store",
    broker=_redis_url,
    backend=_redis_url,
    include=["app.workers.sync_tasks"],
)

if _broker_use_ssl:
    celery_app.conf.broker_use_ssl = {"ssl_cert_reqs": None}
    celery_app.conf.redis_backend_use_ssl = {"ssl_cert_reqs": None}

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "sync-gmail-every-30min": {
            "task": "app.workers.sync_tasks.sync_connector_by_type",
            "schedule": crontab(minute="*/30"),
            "args": ("gmail",),
        },
        "sync-outlook-every-30min": {
            "task": "app.workers.sync_tasks.sync_connector_by_type",
            "schedule": crontab(minute="*/30"),
            "args": ("outlook",),
        },
        "sync-drive-every-2hours": {
            "task": "app.workers.sync_tasks.sync_connector_by_type",
            "schedule": crontab(minute=0, hour="*/2"),
            "args": ("google_drive",),
        },
        "sync-sheets-every-hour": {
            "task": "app.workers.sync_tasks.sync_connector_by_type",
            "schedule": crontab(minute=0),
            "args": ("sheets",),
        },
        "refresh-bm25-every-hour": {
            "task": "app.workers.sync_tasks.refresh_bm25_index",
            "schedule": crontab(minute=30),
        },
    },
)
