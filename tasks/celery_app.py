"""Celery 应用配置。

三个角色要分清：
    beat   调度器，只负责"到点了，扔一个任务进队列"
    worker 消费者，从队列取任务、真正执行
    broker 队列本身（这里用 Redis）

beat 必须是单实例，worker 可以有多个。

启动worker ：celery -A tasks.celery_app worker --pool=solo -l info
启动beat：celery -A tasks.celery_app beat -l info
"""

import logging

from celery import Celery

from config.db_config import settings

logger = logging.getLogger(__name__)

# 用不同的 Redis db 隔离，避免和业务缓存（db 0）的 key 打架
BROKER_URL = f"redis://{settings.redis_host}:{settings.redis_port}/1"
RESULT_URL = f"redis://{settings.redis_host}:{settings.redis_port}/2"

celery_app = Celery(
    "toutiao",
    broker=BROKER_URL,
    backend=RESULT_URL,
    # 显式列出任务模块，worker 启动时才会注册这些任务
    include=["tasks.view_tasks", "tasks.user_tasks", "tasks.rss_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
    # 保证任务不丢
    task_acks_late=True,  # 执行完才 ACK
    task_reject_on_worker_lost=True,  # worker 崩了就把任务退回队列
    worker_prefetch_multiplier=1,  # 一次只领一个，避免一个 worker 囤一堆
    # 不保存任务结果
    task_ignore_result=True,
    # 启动时 Redis 还没准备好也不要立刻崩
    broker_connection_retry_on_startup=True,
    # 任务可观测：celery-exporter 依赖这些事件计算耗时/成功率
    worker_send_task_events=True,
    task_send_sent_event=True,
    task_track_started=True,
    # 兜底超时，防止卡死的抓取任务一直占着 worker
    task_soft_time_limit=240,
    task_time_limit=300,
    beat_schedule={
        "flush-view-counts": {
            "task": "tasks.view_tasks.flush_view_counts",
            "schedule": 10.0,  # 每 10 秒一次
        },
        "clean-expired-tokens": {
            "task": "tasks.user_tasks.clean_expired_tokens",
            "schedule": 3600.0,
        },
        "fetch-rss": {
            "task": "tasks.rss_tasks.fetch_due_feeds",
            "schedule": 300.0,  # 每 5 分钟扫一次，单源间隔由 fetch_interval 控制
            # Celery 5.6.3 的 ScheduleEntry 不认顶层 expires（5.7 才支持），
            # 放进 options 交给 apply_async 处理，语义不变
            "options": {"expires": 240},
        },
        "clean-old-rss": {
            "task": "tasks.rss_tasks.clean_old_rss_news",
            "schedule": 86400.0,
        },
    },
)
