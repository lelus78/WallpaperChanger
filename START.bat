@echo off
REM Quick launcher for Wallpaper Changer GUI
REM No installation required - just double-click this file!

cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    echo.
    echo Please run INSTALL.bat first, or install Python from:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

REM Start the GUI
start "" pythonw.exe gui_modern.py
