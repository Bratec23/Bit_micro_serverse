@echo off
chcp 65001 >nul
title Бит.Serves — остановка платформы
echo Останавливаю все процессы платформы...

REM Имя папки проекта — маркер для поиска процессов
for %%I in ("%~dp0.") do set "PRJ=%%~nxI"

REM 1) Все python-процессы этого проекта (включая «сирот», которые не слушают порты)
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name like 'python%%'\" | Where-Object { $_.ExecutablePath -like '*%PRJ%*' -or $_.CommandLine -like '*%PRJ%*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

REM 2) Страховка: добиваем всё, что ещё слушает порты 8000-8007
for /f "tokens=5" %%p in ('netstat -ano ^| findstr LISTENING ^| findstr /R ":8000 :8001 :8002 :8003 :8004 :8005 :8006 :8007"') do (
    taskkill /PID %%p /F >nul 2>&1
)
echo Готово. Все сервисы остановлены.
pause
