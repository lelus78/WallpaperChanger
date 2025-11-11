@echo off
setlocal enabledelayedexpansion
cls

echo ========================================
echo   Wallpaper Changer - Easy Installer
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed!
    echo.
    echo Please install Python from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo [OK] Python found
echo.

REM Install required packages
echo Installing required Python packages...
echo This may take a few minutes...
echo.

pip install --quiet --upgrade pip
pip install --quiet pillow requests customtkinter matplotlib

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install packages
    pause
    exit /b 1
)

echo.
echo [OK] All packages installed successfully
echo.

REM Create shortcuts
echo Creating desktop shortcuts...

set SCRIPT_DIR=%~dp0
set DESKTOP=%USERPROFILE%\Desktop

REM Create shortcut for GUI
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%DESKTOP%\Wallpaper Changer.lnk'); $s.TargetPath = 'pythonw.exe'; $s.Arguments = '\"%SCRIPT_DIR%gui_modern.py\"'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.IconLocation = 'shell32.dll,13'; $s.Description = 'Wallpaper Changer - Modern GUI'; $s.Save()"

echo [OK] Desktop shortcut created
echo.

REM Create Start Menu folder
set START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Wallpaper Changer
if not exist "%START_MENU%" mkdir "%START_MENU%"

powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%START_MENU%\Wallpaper Changer.lnk'); $s.TargetPath = 'pythonw.exe'; $s.Arguments = '\"%SCRIPT_DIR%gui_modern.py\"'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.IconLocation = 'shell32.dll,13'; $s.Description = 'Wallpaper Changer - Modern GUI'; $s.Save()"

powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%START_MENU%\Configure Settings.lnk'); $s.TargetPath = 'pythonw.exe'; $s.Arguments = '\"%SCRIPT_DIR%gui_config.py\"'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.IconLocation = 'shell32.dll,70'; $s.Description = 'Configure Wallpaper Changer Settings'; $s.Save()"

powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%START_MENU%\Uninstall.lnk'); $s.TargetPath = '%SCRIPT_DIR%UNINSTALL.bat'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.IconLocation = 'shell32.dll,131'; $s.Description = 'Uninstall Wallpaper Changer'; $s.Save()"

echo [OK] Start Menu shortcuts created
echo.

REM Ask about autostart
echo.
echo Do you want Wallpaper Changer to start automatically when Windows starts?
choice /C YN /M "Start automatically"

if errorlevel 2 (
    echo Skipping autostart setup
) else (
    echo Setting up autostart...
    set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
    powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%STARTUP%\Wallpaper Changer Service.lnk'); $s.TargetPath = 'cscript.exe'; $s.Arguments = '//Nologo \"%SCRIPT_DIR%launchers\start_wallpaper_changer.vbs\"'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.Description = 'Wallpaper Changer Background Service'; $s.WindowStyle = 7; $s.Save()"
    echo [OK] Autostart configured
)

echo.
echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo Shortcuts created:
echo   - Desktop: "Wallpaper Changer"
echo   - Start Menu: "Wallpaper Changer" folder
echo.
echo To start using:
echo   1. Double-click "Wallpaper Changer" on your desktop
echo   2. Or search for "Wallpaper Changer" in Start Menu
echo.
echo Press any key to launch Wallpaper Changer now...
pause >nul

start "" "pythonw.exe" "%SCRIPT_DIR%gui_modern.py"
