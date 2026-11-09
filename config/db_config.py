from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# .env 的位置相对于本文件是固定的：backend/.env
# 不能写相对路径 ".env" —— 那是相对【当前工作目录】找的，
# 换一个目录启动（VS Code 发现测试、计划任务、别的服务）就读不到，报 Field required。
BASE_DIR = Path(__file__).resolve().parent.parent

# 配置类：定义所有环境变量


class Settings(BaseSettings):
    # 数据库配置
    db_host: str
    db_port: int = 3306
    db_user: str
    db_password: str
    db_name: str

    redis_host: str
    redis_port: int = 6379
    redis_db: int = 0
    redis_decode_responses: bool = True

    # 运行环境：dev 走本机、开 SQL echo 和详细报错；prod 全部关掉
    # 字段名用 app_env 而不是 env：很多 CI/容器里已经有 ENV 环境变量，会撞车导致启动即失败
    app_env: Literal["dev", "prod"] = "dev"

    @property
    def debug(self) -> bool:
        """唯一事实来源：只有 prod 才关调试。

        不把 debug 也做成字段，否则会出现 app_env=prod 但 debug=True 的矛盾状态，
        而且没人说得清哪个说了算。
        """
        return self.app_env != "prod"

    # RSS
    rsshub_base: str = "http://127.0.0.1:1200"
    # 逗号分隔的用户名白名单；为空表示所有登录用户都能管理（仅适合本地）
    rss_admin_users: str = ""
    # 允许订阅的内网主机（本地 RSSHub 用），生产环境别放开
    rss_private_hosts: str = "127.0.0.1,localhost"
    # RSS 文章保留天数；0 表示不自动清理
    rss_retention_days: int = 0

    @property
    def rss_admins(self) -> set[str]:
        return {name.strip() for name in self.rss_admin_users.split(",") if name.strip()}

    @property
    def rss_private_host_set(self) -> set[str]:
        return {host.strip() for host in self.rss_private_hosts.split(",") if host.strip()}

    # 读取 .env 文件
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8")


# lru_cache 缓存，全局只实例化一次，性能更好
@lru_cache
def get_settings():
    return Settings()


settings = get_settings()

DB_URL = (
    f"mysql+aiomysql://{settings.db_user}:{settings.db_password}"
    f"@{settings.db_host}:{settings.db_port}/{settings.db_name}?charset=utf8mb4"
)

# 创建连接池
async_engine = create_async_engine(DB_URL, echo=settings.debug, pool_size=10, max_overflow=20)
# 会话工厂，被使用时会自动向连接池请求一条连接，session是在数据库连接之上的一层
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
