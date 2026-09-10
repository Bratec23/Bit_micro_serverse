@echo off
chcp 65001 >nul
title Бит.Serves — перезапуск платформы
call "%~dp0stop.bat"
call "%~dp0start.bat"
