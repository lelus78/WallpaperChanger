# Setup Instructions

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/lelus78/WallpaperChanger.git
   cd WallpaperChanger
   ```

2. **Install Python dependencies**
   ```bash
   pip install requests pillow keyboard pystray python-dotenv
   ```

3. **Configure API keys**
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Edit `.env` and add your API keys:
     - **Wallhaven API Key**: Get it from [wallhaven.cc/settings/account](https://wallhaven.cc/settings/account)
     - **Pexels API Key**: Get it from [pexels.com/api/new](https://www.pexels.com/api/new/)

4. **Customize settings** (optional)
   - Edit `config.py` to adjust presets, scheduler, cache settings, and monitors

5. **Run the application**
   - **Windows (background)**: Double-click `launchers/start_wallpaper_changer.vbs`
   - **Console**: `python main.py`
   - **Settings GUI**: Double-click `launchers/start_config_gui.vbs` or run `python gui_config.py`
   - **Stop**: Double-click `launchers/stop_wallpaper_changer.vbs` or use tray icon

## Configuration

### GUI Configuration Tool

The easiest way to configure the app is using the **Settings GUI**:

- **Launch**: Double-click `launchers/start_config_gui.vbs` or run `python gui_config.py`
- **Access from tray**: Right-click the tray icon and select "Open Settings GUI"

The GUI provides:
- **Settings Tab**: Configure all parameters (provider, queries, scheduler, cache, hotkeys)
- **Wallpaper Gallery Tab**: Browse cached wallpapers and apply them to specific monitors

### API Keys (.env file)

```env
WALLHAVEN_API_KEY=your_wallhaven_key_here
PEXELS_API_KEY=your_pexels_key_here
```

### Main Settings (config.py or GUI)

- **Provider**: Choose `"wallhaven"` or `"pexels"` as default provider
- **ProvidersSequence**: Rotate between providers on each update
- **Presets**: Define custom wallpaper collections with filters
- **Scheduler**: Auto-rotate wallpapers with interval, jitter, and quiet hours
- **Monitors**: Per-monitor overrides for multi-monitor setups
- **KeyBind**: Global hotkey (default: `ctrl+alt+w`)

### Example Preset

```python
{
    "name": "workspace",
    "title": "Workspace Focus",
    "description": "Clean and minimal wallpapers for productivity.",
    "providers": ["wallhaven", "pexels"],
    "queries": ["workspace", "minimalist desk"],
    "exclude": ["anime"],
    "colors": ["2b4450"],
    "ratios": ["16x9", "21x9"],
    "purity": "100",
    "screen_resolution": "3440x1440",
    "wallhaven": {
        "sorting": "toplist",
        "top_range": "1M",
    },
    "pexels": {
        "orientation": "landscape",
    },
}
```

## Troubleshooting

- **"Module not found" error**: Install missing packages with `pip install <package_name>`
- **Wallpaper not changing**: Check API keys in `.env` file and internet connection
- **Hotkey not working**: Ensure no other application is using the same key combination
- **Cache issues**: Clear cache folder (default: `~/WallpaperChangerCache/`)

## Security Note

**Never commit your `.env` file to Git!** It contains your private API keys.
The `.gitignore` file is configured to exclude `.env` automatically.
