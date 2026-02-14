@echo off
title Installing TESS AI...
color 0b

echo --------------------------------------------------
echo       TESS TERMINAL PRO - INSTALLATION
echo --------------------------------------------------
echo.
echo [INSTALLER] Launching Setup Wizard...
echo.

:: Run PowerShell setup with Bypass policy to avoid permission errors
PowerShell -NoProfile -ExecutionPolicy Bypass -Command "& '%~dp0setup.ps1'"

echo.
echo [INSTALLER] Setup process finished.
pause
