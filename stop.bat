@echo off
chcp 65001 >nul
title Бит.Serves — остановка платформы
echo Останавливаю все процессы платформы (порты 8000-8004)...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr LISTENING ^| findstr /R ":8000 :8001 :8002 :8003 :8004"') do (
    taskkill /PID %%p /F >nul 2>&1
)
echo Готово. Все сервисы остановлены.
pause
