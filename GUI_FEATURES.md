# GUI Configuration Tool

## Overview

The **GUI Configuration Tool** (`gui_config.py`) provides an easy-to-use graphical interface for managing all aspects of the Wallpaper Changer application.

## How to Launch

1. **Via Launcher Script** (Recommended):
   - Double-click `launchers/start_config_gui.vbs`

2. **Via System Tray**:
   - Right-click the Wallpaper Changer tray icon
   - Select "Open Settings GUI"

3. **Via Command Line**:
   ```bash
   python gui_config.py
   ```

## Features

### Settings Tab

Configure all application parameters without editing `config.py`:

#### Provider Settings
- **Default Provider**: Choose between Wallhaven or Pexels
- **Search Query**: Set your preferred search terms

#### Wallhaven Settings
- **Purity Level**: SFW (100), SFW+Sketchy (110), All (111)
- **Min Resolution**: 1920x1080, 2560x1440, 3440x1440, 3840x2160
- **Sorting**: Random, Toplist, Favorites, Views
- **Top Range**: 1d, 3d, 1w, 1M, 3M, 6M, 1y

#### Pexels Settings
- **Mode**: Search or Curated

#### Scheduler Settings
- **Enable/Disable Scheduler**: Toggle automatic wallpaper rotation
- **Interval**: Set rotation interval in minutes (1-1440)
- **Jitter**: Add randomness to interval (0-60 minutes)

#### Cache Settings
- **Max Cache Items**: Control cache size (10-500 items)
- **Enable Offline Rotation**: Use cached wallpapers when offline

#### Hotkey Settings
- **Hotkey**: Set global keyboard shortcut (e.g., ctrl+alt+w)

### Wallpaper Gallery Tab

Browse and manage your cached wallpapers:

#### Features
- **Visual Thumbnail Gallery**: See all cached wallpapers at a glance
- **Monitor Selection**:
  - Apply to all monitors
  - Apply to specific monitor (Monitor 1, Monitor 2, etc.)
- **Wallpaper Information**: View source and metadata for each wallpaper
- **Quick Actions**:
  - **Apply to Selected Monitor**: One-click wallpaper application
  - **Refresh Gallery**: Reload cached wallpapers
  - **Clear Cache**: Remove all cached wallpapers

#### Monitor Detection
The GUI automatically detects your monitor configuration and displays:
- Number of monitors
- Resolution for each monitor
- Physical layout

#### Usage
1. Select target monitor from dropdown (or "All Monitors")
2. Click "Apply to Selected Monitor" button on any wallpaper thumbnail
3. Wallpaper is immediately applied to the selected monitor(s)

## Saving Configuration

1. Make your changes in the Settings tab
2. Click "💾 Save Configuration" button
3. Restart the main application for changes to take effect

## Tips

- **Real-time Preview**: Changes in the GUI are saved to `config.py`
- **No Manual Editing**: All settings can be managed through the GUI
- **Safe Configuration**: The GUI validates input values
- **Reload Anytime**: Use "🔄 Reload Config" to discard unsaved changes

## System Requirements

- Python 3.10 or newer
- tkinter (included with Python)
- PIL/Pillow (for image thumbnails)
- All other Wallpaper Changer dependencies

## Troubleshooting

### GUI Won't Launch
- Ensure all dependencies are installed: `pip install pillow`
- Check that tkinter is available (usually included with Python)
- Verify `config.py` is properly formatted

### Images Not Displaying in Gallery
- Check that cache directory exists
- Verify wallpapers have been downloaded (run the main app first)
- Ensure PIL/Pillow is installed correctly

### Changes Not Saving
- Check file permissions on `config.py`
- Ensure the main application is not running (may lock the file)
- Use "Reload Config" to verify current values

### Monitor Selection Issues
- Restart the GUI to refresh monitor detection
- Check Windows display settings
- Some monitors may require administrator privileges
