"""Celery 任务层：退避、token 清理、浏览量落库、调度配置。"""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select, update

from models.user import UserToken
from tasks import rss_tasks, user_tasks, view_tasks

NOW = datetime(2026, 1, 1, 12, 0, 0)


def _row(**overrides):
    data = {
        "fetch_interval": 900,
        "error_count": 0,
        "last_fetch_at": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_next_delay_grows_with_errors_and_caps():
    assert rss_tasks._next_delay(900, 0) == 900
    assert rss_tasks._next_delay(900, 2) == 3600
    assert rss_tasks._next_delay(900, 10) == 14400  # 2 ** 4 封顶
    assert rss_tasks._next_delay(3600, 4) == 6 * 3600  # 6 小时上限


def test_is_due_when_never_fetched():
    assert rss_tasks._is_due(_row(), NOW) is True


def test_is_due_respects_interval():
    assert rss_tasks._is_due(_row(last_fetch_at=NOW - timedelta(minutes=5)), NOW) is False
    assert rss_tasks._is_due(_row(last_fetch_at=NOW - timedelta(minutes=16)), NOW) is True


def test_is_due_backs_off_after_errors():
    recent = NOW - timedelta(minutes=30)
    # 失败 2 次：900 * 4 = 3600s，30 分钟还没到
    assert rss_tasks._is_due(_row(last_fetch_at=recent, error_count=2), NOW) is False


def test_is_due_force_ignores_interval():
    assert rss_tasks._is_due(_row(last_fetch_at=NOW), NOW, force=True) is True


async def test_clean_expired_tokens_keeps_valid(db, auth):
    assert await user_tasks._clean_once() == 0


async def test_clean_expired_tokens_deletes_expired(db, auth):
    await db.execute(
        update(UserToken)
        .where(UserToken.token == auth["token"])
        .values(expires_at=datetime.now() - timedelta(seconds=1))
    )
    await db.commit()

    assert await user_tasks._clean_once() == 1

    count = await db.scalar(select(func.count(UserToken.id)))
    assert count == 0


class FakeRedis:
    def __init__(self, dirty=(), values=None, fail=False):
        self.dirty = set(dirty)
        self.values = dict(values or {})
        self.fail = fail
        self.evals = []
        self.removed = []
        self.closed = False

    async def smembers(self, key):
        if self.fail:
            raise RuntimeError("redis down")
        return set(self.dirty)

    async def mget(self, keys):
        if self.fail:
            raise RuntimeError("redis down")
        return [self.values.get(key) for key in keys]

    async def srem(self, key, *members):
        self.removed.extend(members)
        for member in members:
            self.dirty.discard(member)
            self.dirty.discard(str(member))
        return len(members)

    async def eval(self, script, numkeys, *args):
        # args = (counter_key, dirty_key, value, member)
        counter_key, _dirty_key, value, member = args
        self.evals.append(args)
        if self.values.get(counter_key) == value:
            self.dirty.discard(member)
            return 1
        return 0

    async def aclose(self):
        self.closed = True


async def test_flush_once_writes_absolute_views(db, make_news, monkeypatch):
    news = await make_news()
    fake = FakeRedis(
        dirty={str(news.id)},
        values={f"news:views:total:{news.id}": "3"},
    )
    monkeypatch.setattr(view_tasks, "new_client", lambda: fake)

    flushed = await view_tasks._flush_once()

    assert flushed == 1
    assert fake.removed == []
    assert fake.closed is True
    # 落库的是绝对值，不是"views + delta"
    assert fake.evals[0][2] == "3"

    # make_news 里的 refresh 已经开了事务，先结束它才能看到另一个连接提交的值
    await db.rollback()
    await db.refresh(news)
    assert news.views == 3


async def test_flush_never_lowers_views(db, make_news, monkeypatch):
    """两个 flush 重叠时，旧快照后写不能把数据库的数字盖回去。"""
    news = await make_news(views=105)
    fake = FakeRedis(
        dirty={str(news.id)},
        # 另一个（更慢的）flush 读到的是旧值 100，晚于 105 落库
        values={f"news:views:total:{news.id}": "100"},
    )
    monkeypatch.setattr(view_tasks, "new_client", lambda: fake)

    assert await view_tasks._flush_once() == 1

    await db.rollback()
    await db.refresh(news)
    assert news.views == 105


async def test_flush_once_without_dirty_returns_zero(db, monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(view_tasks, "new_client", lambda: fake)

    assert await view_tasks._flush_once() == 0
    assert fake.closed is True


async def test_flush_once_clears_dirty_when_counter_is_gone(db, monkeypatch):
    fake = FakeRedis(dirty={"7"}, values={})
    monkeypatch.setattr(view_tasks, "new_client", lambda: fake)

    assert await view_tasks._flush_once() == 0
    assert 7 in fake.removed
    assert fake.dirty == set()


async def test_flush_once_propagates_redis_failure(db, monkeypatch):
    fake = FakeRedis(fail=True)
    monkeypatch.setattr(view_tasks, "new_client", lambda: fake)

    with pytest.raises(RuntimeError):
        await view_tasks._flush_once()
    assert fake.closed is True


def test_beat_schedule_registers_rss_and_view_tasks():
    from tasks.celery_app import celery_app

    schedule = celery_app.conf.beat_schedule
    assert schedule["fetch-rss"]["task"] == "tasks.rss_tasks.fetch_due_feeds"
    assert schedule["flush-view-counts"]["task"] == "tasks.view_tasks.flush_view_counts"
    assert "tasks.rss_tasks" in celery_app.conf.include
