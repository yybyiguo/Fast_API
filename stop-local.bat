@echo off
chcp 65001 >nul
setlocal EnableExtensions

set "ROOT=%~dp0"
set "REDIS_PORT=16379"
if exist "%ROOT%backend\.env" for /f "tokens=1,2 delims==" %%A in ('findstr /i /b "redis_port=" "%ROOT%backend\.env"') do set "REDIS_PORT=%%B"
if not defined REDIS_PORT set "REDIS_PORT=16379"

echo 停止 Toutiao 本地服务...

rem 先按窗口标题停，start-local.bat 起的就是这五个窗口
for %%T in (api worker beat web redis) do taskkill /FI "WINDOWTITLE eq toutiao-%%T" /T /F >nul 2>&1

rem 再按端口兜底：uvicorn/vite 的子进程，以及会脱离 cmd 的 Redis
rem Redis 端口从 backend\.env 读，别人用默认 6379 也能停
for %%P in (8000 5500 %REDIS_PORT%) do (
  for /f "tokens=5" %%A in ('netstat -ano ^| findstr ":%%P " ^| findstr "LISTENING"') do (
    taskkill /PID %%A /T /F >nul 2>&1
  )
)

rem Celery 没有端口，按命令行兜底；只匹配 celery.exe / python.exe，
rem 否则会把包含这段文字的 powershell / Harness 自己也算进去
powershell -NoProfile -Command "$me=$PID; Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $me -and $_.Name -match '^(celery|python)' -and $_.CommandLine -like '*tasks.celery_app*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1

echo 完成。脚本启动的 Redis 窗口已停，MySQL 保持运行。
ping -n 3 127.0.0.1 >nul
exit /b 0
