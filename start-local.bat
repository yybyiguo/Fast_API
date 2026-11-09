@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"

set "DRY="
if /i "%~1"=="--dry-run" set "DRY=1"

echo ============================================
echo   Toutiao 本地一键启动 (Windows)
echo ============================================

rem ---------- Python 虚拟环境 ----------
set "PYDIR=%BACKEND%\.venv\Scripts"
if not exist "%PYDIR%\uvicorn.exe" set "PYDIR=%BACKEND%\venv\Scripts"
if not exist "%PYDIR%\uvicorn.exe" goto :no_venv
if not exist "%PYDIR%\celery.exe" goto :no_venv
if not exist "%PYDIR%\alembic.exe" goto :no_venv
set "UVICORN=%PYDIR%\uvicorn.exe"
set "CELERY=%PYDIR%\celery.exe"
set "ALEMBIC=%PYDIR%\alembic.exe"

if not exist "%BACKEND%\.env" (
  echo [ERROR] 缺少 backend\.env
  echo         先复制 backend\.env.example 为 backend\.env，再按本机 MySQL/Redis 修改。
  goto :fail
)

rem ---------- 从 .env 读端口 ----------
set "DB_PORT=3306"
set "REDIS_PORT=6379"
for /f "tokens=1,2 delims==" %%A in ('findstr /i /b "db_port=" "%BACKEND%\.env"') do set "DB_PORT=%%B"
for /f "tokens=1,2 delims==" %%A in ('findstr /i /b "redis_port=" "%BACKEND%\.env"') do set "REDIS_PORT=%%B"
if not defined DB_PORT set "DB_PORT=3306"
if not defined REDIS_PORT set "REDIS_PORT=6379"

echo.
echo [0/5] 检查 MySQL %DB_PORT%...
call :port_listening %DB_PORT%
if errorlevel 1 (
  echo [ERROR] MySQL %DB_PORT% 没有监听，请先启动 MySQL。
  goto :fail
)
echo        MySQL OK

echo.
echo [1/5] Redis，端口 %REDIS_PORT%...
call :port_listening %REDIS_PORT%
if not errorlevel 1 (
  echo        [SKIP] %REDIS_PORT% 已在监听
) else (
  call :find_redis
  if not defined REDIS_BIN (
    echo [ERROR] Redis 没有运行，也没找到 memurai.exe / redis-server.exe。
    echo         1. 安装 Memurai 或 Redis，并把目录加入 PATH；
    echo         2. 或设置环境变量 REDIS_EXE、REDIS_CONF 指向可执行文件和配置；
    echo         3. 或直接用 docker compose up（跨平台，推荐）。
    goto :fail
  )
  if defined DRY (
    echo        [dry-run] start "!REDIS_BIN!" --port %REDIS_PORT%
  ) else (
    echo        启动 Redis: !REDIS_BIN!
    if defined REDIS_CONF_FILE (
      start "toutiao-redis" /D "!REDIS_DIR!" "!REDIS_BIN!" "!REDIS_CONF_FILE!" --port %REDIS_PORT%
    ) else (
      start "toutiao-redis" /D "!REDIS_DIR!" "!REDIS_BIN!" --port %REDIS_PORT%
    )
  )
)
if not defined DRY (
  call :wait_port %REDIS_PORT% 10
  if errorlevel 1 (
    echo [WARN] Redis %REDIS_PORT% 未监听，Celery 会连不上 broker。
    echo        检查 Redis 配置里的 port，或手动运行 Redis 看报错。
  ) else (
    echo        Redis OK
  )
)

echo.
echo [2/5] 数据库迁移...
if defined DRY (
  echo        [dry-run] alembic upgrade head
) else (
  pushd "%BACKEND%"
  "%ALEMBIC%" upgrade head
  if errorlevel 1 (
    popd
    echo [ERROR] alembic upgrade head 失败，检查 MySQL 和 .env。
    goto :fail
  )
  popd
  echo        迁移 OK
)

echo.
echo [3/5] 后端 API...
call :port_listening 8000
if not errorlevel 1 (
  echo        [SKIP] 8000 已在监听，先运行 stop-local.bat 再重启。
) else (
  if defined DRY (
    echo        [dry-run] start toutiao-api
  ) else (
    start "toutiao-api" /D "%BACKEND%" cmd /k "%UVICORN% main:app --reload --host 0.0.0.0 --port 8000"
    echo        API 已启动
  )
)

echo.
echo [4/5] Celery worker / beat...
tasklist /FI "WINDOWTITLE eq toutiao-worker" 2>nul | find /i "cmd.exe" >nul
if not errorlevel 1 (
  echo        [SKIP] worker 窗口已存在
) else (
  if defined DRY (
    echo        [dry-run] start toutiao-worker
  ) else (
    start "toutiao-worker" /D "%BACKEND%" cmd /k "%CELERY% -A tasks.celery_app worker --pool=solo -l info"
    echo        worker 已启动
  )
)

tasklist /FI "WINDOWTITLE eq toutiao-beat" 2>nul | find /i "cmd.exe" >nul
if not errorlevel 1 (
  echo        [SKIP] beat 窗口已存在
) else (
  if defined DRY (
    echo        [dry-run] start toutiao-beat
  ) else (
    start "toutiao-beat" /D "%BACKEND%" cmd /k "%CELERY% -A tasks.celery_app beat -l info"
    echo        beat 已启动
  )
)

echo.
echo [5/5] 前端...
where npm >nul 2>&1
if errorlevel 1 (
  echo [ERROR] 没找到 npm，请安装 Node.js 20+。
  goto :fail
)

if not exist "%FRONTEND%\node_modules" (
  if defined DRY (
    echo        [dry-run] npm install
  ) else (
    echo        安装前端依赖...
    pushd "%FRONTEND%"
    call npm install
    if errorlevel 1 (
      popd
      echo [ERROR] npm install 失败。
      goto :fail
    )
    popd
  )
)

call :port_listening 5500
if not errorlevel 1 (
  echo        [SKIP] 5500 已在监听，先运行 stop-local.bat 再重启。
) else (
  if defined DRY (
    echo        [dry-run] start toutiao-web
  ) else (
    start "toutiao-web" /D "%FRONTEND%" cmd /k "npm run dev"
    echo        前端已启动
  )
)

echo.
if defined DRY (
  echo [dry-run] 浏览器会打开 http://127.0.0.1:5500
  echo 预检完成，没有启动任何服务。
  exit /b 0
)

echo 等待服务就绪...
call :wait_port 8000 20
call :wait_port 5500 20
start "" "http://127.0.0.1:5500"

echo.
echo 启动完成：API http://127.0.0.1:8000  前端 http://127.0.0.1:5500
echo 停止服务请运行 stop-local.bat
ping -n 6 127.0.0.1 >nul
exit /b 0

:no_venv
echo [ERROR] 没找到可用的 Python 虚拟环境（uvicorn / celery / alembic）。
echo         在 backend 目录执行 uv sync，或手动 python -m venv .venv 后装依赖。
goto :fail

:fail
echo.
echo 启动失败，按任意键关闭...
pause >nul
exit /b 1

:find_redis
set "REDIS_BIN="
if defined REDIS_EXE if exist "%REDIS_EXE%" set "REDIS_BIN=%REDIS_EXE%"
if not defined REDIS_BIN for /f "delims=" %%I in ('where memurai.exe 2^>nul') do set "REDIS_BIN=%%I"
if not defined REDIS_BIN for /f "delims=" %%I in ('where redis-server.exe 2^>nul') do set "REDIS_BIN=%%I"
if not defined REDIS_BIN if exist "%ProgramFiles%\Memurai\memurai.exe" set "REDIS_BIN=%ProgramFiles%\Memurai\memurai.exe"
if not defined REDIS_BIN if exist "%ProgramFiles%\Redis\redis-server.exe" set "REDIS_BIN=%ProgramFiles%\Redis\redis-server.exe"
rem 作者本机的兜底路径；别人机器没有会自动跳过
if not defined REDIS_BIN if exist "D:\redis\memurai.exe" set "REDIS_BIN=D:\redis\memurai.exe"
if not defined REDIS_BIN exit /b 0

for %%I in ("%REDIS_BIN%") do set "REDIS_DIR=%%~dpI"
if "%REDIS_DIR:~-1%"=="\" set "REDIS_DIR=%REDIS_DIR:~0,-1%"

set "REDIS_CONF_FILE="
if defined REDIS_CONF if exist "%REDIS_CONF%" set "REDIS_CONF_FILE=%REDIS_CONF%"
if not defined REDIS_CONF_FILE if exist "%REDIS_DIR%\memurai.conf" set "REDIS_CONF_FILE=%REDIS_DIR%\memurai.conf"
if not defined REDIS_CONF_FILE if exist "%REDIS_DIR%\redis.conf" set "REDIS_CONF_FILE=%REDIS_DIR%\redis.conf"
exit /b 0

:port_listening
netstat -ano | findstr ":%~1 " | findstr "LISTENING" >nul
exit /b %errorlevel%

:wait_port
setlocal EnableExtensions
set "WPORT=%~1"
set "WTRIES=%~2"
for /l %%i in (1,1,%WTRIES%) do (
  netstat -ano | findstr ":%WPORT% " | findstr "LISTENING" >nul
  if not errorlevel 1 (
    endlocal
    exit /b 0
  )
  ping -n 2 127.0.0.1 >nul
)
endlocal
exit /b 1
