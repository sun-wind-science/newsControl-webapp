from celery import Celery

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery("content_digest", broker=settings.celery_broker_url, backend=settings.celery_result_backend)
celery_app.conf.timezone = "Asia/Shanghai"


@celery_app.task(name="app.workers.decay_check")
def decay_check() -> dict:
    # 后续接入数据库扫描：30 天冷存、60 天衰减清理。
    return {"checked": True, "message": "资源衰减检查任务已预留"}
