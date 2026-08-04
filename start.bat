@echo off
chcp 65001 >nul
title Бит.Serves — платформа (локальный запуск)
cd /d "%~dp0"
echo ============================================
echo   Бит.Serves — запуск платформы
echo   После старта открой: http://localhost:8000
echo   Остановка: закрой это окно или Ctrl+C
echo ============================================
echo.
"..\.venv-test\Scripts\python.exe" local_launcher.py
pause
