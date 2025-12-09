@echo off
REM Intersect Engine Auto Reboot Tool Launcher (Windows)

cd /d "%~dp0"

python auto_reboot_tool.py

if errorlevel 1 (
    echo.
    echo Error: Failed to start auto reboot tool
    echo Make sure Python is installed and accessible
    pause
)


