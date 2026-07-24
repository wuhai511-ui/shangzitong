from celery import Celery
from core.config import settings

celery_app = Celery(
    "szt_worker",
    broker=getattr(settings, "CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=getattr(settings, "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    beat_schedule={
        "evaluate-auto-swipe-every-30m": {
            "task": "app.tasks.auto_swipe_tasks.evaluate_all_merchants_task",
            "schedule": 1800.0,
        },
        "execute-scheduled-every-5m": {
            "task": "app.tasks.auto_swipe_tasks.execute_scheduled_transactions_task",
            "schedule": 300.0,
        },
        "retry-failed-every-15m": {
            "task": "app.tasks.auto_swipe_tasks.retry_failed_transactions_task",
            "schedule": 900.0,
        },
    },
)
