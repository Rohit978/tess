@echo off
setlocal
title Disable TESS Always-On
color 0c

set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_DIR%\TESS Wake Listener.lnk"

echo --------------------------------------------------
echo      DISABLING TESS ALWAYS-ON WAKE LISTENER
echo --------------------------------------------------

if exist "%SHORTCUT_PATH%" (
    del /f /q "%SHORTCUT_PATH%"
    echo [OK] Removed startup shortcut.
) else (
    echo [INFO] Startup shortcut not found.
)

echo [INFO] Always-on wake listener is now disabled for next login.
exit /b 0

