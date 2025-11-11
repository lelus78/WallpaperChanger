# 🖼️ Wallpaper Changer

A modern, feature-rich wallpaper manager for Windows that automatically downloads and applies beautiful wallpapers from multiple sources (Wallhaven, Pexels, Reddit).

## ✨ Key Features

### Modern GUI
- **Beautiful Interface** - Clean, dark-themed modern UI built with CustomTkinter
- **Wallpaper Gallery** - Browse, filter, and preview all cached wallpapers
- **Fullscreen Viewer** - Click any wallpaper to view in full resolution
- **Tag System** - Auto-extracted tags from providers for easy filtering
- **Statistics Dashboard** - Track usage, favorites, and view distribution charts
- **Rating & Favorites** - 5-star rating system and favorites management

### Smart Wallpaper Management
- **Multi-Monitor Support** - Different wallpapers for each monitor
- **Auto-Download** - Fresh wallpapers from Wallhaven, Reddit, and Pexels
- **Smart Caching** - Local storage with offline rotation capability
- **Weather Overlays** - Display current temperature on wallpapers
- **Playlists** - Create themed collections for different moods/times
- **Scheduled Changes** - Automatic rotation with configurable intervals

### Easy to Use
- **One-Click Installation** - Simple installer for non-technical users
- **Desktop Shortcuts** - Quick access from desktop or Start Menu
- **Global Hotkey** - `Ctrl+Alt+W` to change wallpaper instantly
- **System Tray Integration** - Quick actions from notification area

## 🚀 Quick Start (For Everyone)

### Easy Installation
1. **Install Python** from [python.org](https://www.python.org/downloads/)
   - ⚠️ **Important:** Check "Add Python to PATH" during installation
2. **Double-click `INSTALL.bat`** in this folder
3. **Wait** for installation to complete (~1-2 minutes)
4. **Done!** Find "Wallpaper Changer" on your desktop

### Alternative: Quick Start Without Installing
- Just double-click **`START.bat`** to launch the GUI

👉 **For detailed instructions, see [README_USER.md](README_USER.md)**

## 📖 For Developers

### Manual Installation
1. Install Python (3.10 or newer recommended)
2. Install dependencies:
   ```bash
   pip install requests pillow customtkinter matplotlib keyboard pystray python-dotenv
   ```

3. Configure API keys (optional):
   - Copy `.env.example` to `.env` and add your API keys
   - **Wallhaven** – [Get API key](https://wallhaven.cc/help/api)
   - **Pexels** – [Get API key](https://www.pexels.com/api/new/)
   - **Reddit** - No key required

4. Customize settings:
   - **GUI**: Run `python gui_config.py`
   - **Manual**: Edit `config.py`

## Configuration Highlights (`config.py`)

- `Provider` / `ProvidersSequence`: default provider(s) and rotation order.
- `ApiKey` / `PexelsApiKey` / `PexelsMode`: provider credentials and default mode (`search` or `curated` for Pexels).
- `RedditSettings`: global defaults for subreddit list, sort/time filters, post limit, minimum score, NSFW toggle, and the user-agent sent to Reddit.
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
- Reddit’s public JSON API is rate-limited; customise `RedditSettings.user_agent`, keep reasonable intervals, and avoid unnecessary refresh storms.
- Respect Wallhaven and Pexels API usage guidelines/quotas when configuring frequent scheduler intervals.
