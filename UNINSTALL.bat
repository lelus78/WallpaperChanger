@echo off
cls

echo ========================================
echo   Wallpaper Changer - Uninstaller
echo ========================================
echo.
echo This will remove:
echo   - Desktop shortcuts
echo   - Start Menu shortcuts
echo   - Autostart entry
echo.
echo Your wallpaper cache and settings will be preserved.
echo.

choice /C YN /M "Continue with uninstall"

if errorlevel 2 (
    echo Uninstall cancelled
    pause
    exit /b 0
)

echo.
echo Removing shortcuts...

REM Remove desktop shortcut
del "%USERPROFILE%\Desktop\Wallpaper Changer.lnk" 2>nul

REM Remove Start Menu folder
rmdir /s /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Wallpaper Changer" 2>nul

REM Remove autostart entry
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Wallpaper Changer Service.lnk" 2>nul

REM Stop running service
echo Stopping wallpaper service...
cscript //Nologo "%~dp0launchers\stop_wallpaper_changer.vbs" 2>nul

echo.
echo [OK] Uninstall complete
echo.
echo To completely remove Wallpaper Changer:
echo   - Delete this folder: %~dp0
echo   - Delete cache folder: %USERPROFILE%\WallpaperChangerCache
echo.
pause
