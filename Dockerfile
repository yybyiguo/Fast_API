# ============================================================
# 阶段一：单阶段镜像（先跑通，下一课再优化成多阶段）
# ============================================================

# 基础镜像：Python 3.13 精简 Debian（走 daocloud 镜像站，docker.io 直连不通）
FROM docker.m.daocloud.io/library/python:3.13-slim

# slim 镜像没有时区数据库，TZ=Asia/Shanghai 不生效会静默回退 UTC，
# 导致容器内 datetime.now() 和业务写入的 +08:00 差 8 小时
RUN apt-get update \
 && apt-get install -y --no-install-recommends tzdata \
 && rm -rf /var/lib/apt/lists/*

# 运行环境变量：
#   PYTHONDONTWRITEBYTECODE=1  不生成 .pyc，镜像更干净
#   PYTHONUNBUFFERED=1         日志立即输出，不被缓冲（否则 docker logs 看不到实时日志）
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 之后所有命令都在 /app 里执行
WORKDIR /app

# ---- 第 1 层：只拷依赖清单 ----
# 关键：依赖清单和代码分开拷。只要 pyproject/uv.lock 没变，
# 下面装依赖那一层就能命中缓存，改代码时不用重装几百个包。
COPY pyproject.toml uv.lock ./

# ---- 第 2 层：装依赖 ----
# --no-dev：不装 pytest/httpx 这些只有开发才用的东西
RUN pip install --no-cache-dir uv \
 && uv sync --frozen --no-dev

# ---- 第 3 层：拷代码 ----
# 这一层最常变，所以放在最后
COPY . .

# 只是文档说明，真正对外暴露要靠 docker run -p
EXPOSE 8000

# 容器启动命令。
# --host 0.0.0.0 是必须的：绑 127.0.0.1 的话，容器外面永远访问不到。
# --no-sync 表示直接用已装好的 .venv，不在启动时联网同步依赖。
CMD ["uv", "run", "--no-sync", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
