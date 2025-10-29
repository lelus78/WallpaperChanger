# Wallpaper Changer

The **Wallpaper Changer** is a Python program that automatically refreshes your desktop wallpaper using random images from configurable providers (Wallhaven or Pexels). It now bundles a Windows tray companion, scheduling, caching, presets, and one-click launchers so you can tailor wallpaper rotation to your workflow.

## Features

- **GUI Configuration Tool** with Settings tab and Wallpaper Gallery to easily configure the app and manage cached wallpapers.
- System tray companion with quick actions (change now, rotate presets, toggle scheduler, play next cached wallpaper, open settings GUI, exit).
- Configurable presets with include/exclude keywords, colour cues, aspect-ratio filters, and provider-specific options (sorting/toplist on Wallhaven, orientation on Pexels).
- Flexible scheduler with interval, jitter, day filters, and quiet hours to avoid changes while you work or sleep.
- Local cache with metadata and offline rotation, letting you replay favourite wallpapers even without a connection.
- **Wallpaper Gallery** in the GUI to browse cached wallpapers and apply them to specific monitors with one click.
- One-click launcher scripts (`launchers/start_wallpaper_changer.vbs`, `launchers/stop_wallpaper_changer.vbs`, `launchers/start_config_gui.vbs`) to start or stop the app without opening a console.
- Provider rotation and per-monitor overrides (provider, preset, resolution) including automatic panorama fallback when the Windows per-monitor API is unavailable.
- Global hotkey (default `ctrl+alt+w`) to trigger an instant refresh.
- Automatic BMP conversion so Windows reliably applies the wallpaper across multiple monitors.

## Installation

1. Install Python (3.10 or newer recommended). Download it from [python.org](https://www.python.org/downloads/).
2. Install dependencies inside your terminal from the project directory:

   ```bash
   pip install requests pillow keyboard pystray python-dotenv
   ```

3. Configure API keys:
   - Copy `.env.example` to `.env` and add your API keys
   - **Wallhaven** – visit the [Wallhaven API settings](https://wallhaven.cc/help/api) page and generate a key.
   - **Pexels** – create an account and request a key at [pexels.com/api/new](https://www.pexels.com/api/new/).

4. Customize settings:
   - **Easy way**: Launch the GUI (`launchers/start_config_gui.vbs` or `python gui_config.py`)
   - **Manual way**: Edit `config.py` to adjust presets/scheduler/cache and per-monitor overrides.

## Configuration Highlights (`config.py`)

- `Provider` / `ProvidersSequence`: default provider(s) and rotation order.
- `ApiKey` / `PexelsApiKey` / `PexelsMode`: provider credentials and default mode (`search` or `curated` for Pexels).
- `CacheSettings`: cache directory, size cap, and offline rotation toggle.
- `SchedulerSettings`: enable/disable scheduler, interval, jitter, initial delay, quiet hours, and active days.
- `Presets`: named preset list defining providers, include/exclude keywords, colours, ratios, and provider-specific options (`wallhaven.sorting`, `wallhaven.top_range`, `pexels.orientation`, etc.).
- `DefaultPreset`: preset activated at startup.
- `Monitors`: per-monitor overrides (physical order) allowing preset/provider/query/resolution customisation.
- `KeyBind`: global hotkey for manual refresh.

Example monitor override:

```python
Monitors = [
    {
        "name": "Full HD",
        "preset": "workspace",
        "provider": "",
        "query": "",
        "screen_resolution": "1920x1080",
        "purity": "100",
        "wallhaven_sorting": "toplist",
        "wallhaven_top_range": "1w",
    },
    {
        "name": "Ultrawide",
        "preset": "relax",
        "provider": "",
        "query": "",
        "screen_resolution": "3440x1440",
        "purity": "100",
        "wallhaven_sorting": "toplist",
        "wallhaven_top_range": "3d",
    },
]
```

## Usage

1. Launch the application by double-clicking `launchers/start_wallpaper_changer.vbs`. The script runs `main.py` in the background without opening a console window.
   - Prefer the terminal? You can still run `python main.py`.
   - On startup the first wallpaper change happens immediately and the **Wallpaper Changer** tray icon appears in the notification area.

2. Interact via the tray menu:
   - **Change Wallpaper** – refresh instantly using the active preset/provider sequence.
   - **Presets** – switch preset on the fly; the change applies right away.
   - **Toggle Scheduler** – enable or disable automatic rotation without editing `config.py`.
   - **Next From Cache** – apply a cached wallpaper (handy when offline).
   - **Open Cache Folder** – open the cache directory in Explorer.
   - **Exit** – stop the scheduler, unhook the hotkey, and close the tray icon.

3. Hotkey trigger: press `ctrl+alt+w` (or your custom `KeyBind`) to refresh immediately from anywhere.

4. Scheduler: if enabled, wallpapers change automatically at the configured interval outside quiet hours/days. You can pause/resume via the tray menu.

5. Shutdown: double-click `launchers/stop_wallpaper_changer.vbs`, or use the tray’s **Exit** command. (If you started from the terminal, `Ctrl+C` still works.)

## Notes

- Keep a stable internet connection for new wallpapers; cached mode lets you replay previous ones offline.
- Per-monitor wallpapers rely on the Windows 8+ `IDesktopWallpaper` API. If unavailable, the app assembles a panorama across monitors instead.
- The cache stores original downloads (JPEG/PNG) and converts them on the fly, so you can reuse high-quality images later.
- Respect Wallhaven and Pexels API usage guidelines/quotas when configuring frequent scheduler intervals.
