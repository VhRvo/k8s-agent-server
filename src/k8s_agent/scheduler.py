import logging

from apscheduler.schedulers.background import BackgroundScheduler

from k8s_agent.core.config import settings

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    from k8s_agent.services.inspector import run_inspection

    _scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    _scheduler.add_job(
        run_inspection,
        "interval",
        minutes=settings.inspection_interval_minutes,
        id="k8s_inspection",
        replace_existing=True,
        kwargs={"trigger": "scheduled"},
    )
    _scheduler.start()
    logger.info("定时巡检已启动，每 %d 分钟执行一次", settings.inspection_interval_minutes)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("定时巡检已停止")
