@echo off
title TESS Autostart
color 0a

echo Waiting for system to stabilize (10s)...
timeout /t 10 /nobreak >nul

cd /d "%~dp0"
call Start_TESS.bat
