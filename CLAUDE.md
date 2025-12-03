# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WallpaperChanger is a Windows wallpaper manager that automatically downloads and applies wallpapers from multiple providers (Wallhaven, Pexels, Reddit). It features multi-monitor support, AI-powered features, weather overlays, playlists, and a modern GUI built with CustomTkinter.

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Launch the GUI (recommended for development)
python gui_config.py

# Or launch the main service (background wallpaper rotation)
python main.py

# Or use the launchers
launchers/start_wallpaper_changer.vbs  # Starts background service
launchers/stop_wallpaper_changer.vbs   # Stops background service
```

## Testing

```bash
# Test duplicate detection
python test_duplicate_detection.py

# Test Ollama AI fallback
python test_ollama_fallback.py

# Test span mode wallpaper logic (multi-monitor)
python test_span_logic.py

# Analyze existing wallpapers for color data
python populate_colors.py

# Find duplicate wallpapers
python find_duplicates.py
```

## Architecture

### Core Components

**main.py** (`WallpaperApp` class)
- Central service that orchestrates wallpaper changes
- Manages multi-monitor detection and wallpaper application
- Handles provider rotation (Wallhaven, Pexels, Reddit)
- Integrates weather overlays, playlists, and AI features
- Runs as background service with system tray integration

**gui_modern.py** (`WallpaperGUI` class)
- Modern UI built with CustomTkinter
- Tabs: Home (dashboard), Wallpapers (gallery), Duplicates, AI Assistant, Settings
- Handles wallpaper preview, filtering, rating, favorites, deletion
- AI features: mood detection, smart search, predictive downloads

**cache_manager.py** (`CacheManager` class)
- Manages wallpaper cache with intelligent rotation
- Protects starred/favorite wallpapers from deletion
- Handles duplicate detection using perceptual hashing
- Stores metadata: colors, tags, ratings, provider info, monitor assignment

**config.py**
- All configuration settings (providers, API keys, monitors, presets, schedules)
- Per-monitor overrides for different wallpapers on each screen
- Environment variables loaded from `.env` file

### Key Subsystems

**Multi-Monitor Support**
- Uses Windows `IDesktopWallpaper` API for per-monitor wallpaper setting
- Falls back to "span mode" (composite image) when API unavailable
- Span mode creates a single BMP that spans all monitors at their physical positions
- Files: `wallpaper_span.bmp`, `wallpaper_monitor_{index}.bmp`
- Monitor info stored in `monitors_status.json` and `current_wallpaper_info.json`

**Provider System**
- Each provider (Wallhaven, Pexels, Reddit) has its own API integration
- Provider rotation managed by `ProvidersSequence` in config
- State persisted in `provider_state.json`
- Methods: `_fetch_from_{provider}()`, `_parse_{provider}_response()`

**Preset & Playlist System**
- **Presets** (`preset_manager.py`): Named configurations (workspace, relax, etc.) with provider preferences, search queries, color/ratio filters
- **Playlists** (`playlist_manager.py`): Themed collections that change based on weather/time (e.g., "cloudy_focus" → "Misty Mountains")
- Weather integration via `weather_rotation.py` selects appropriate playlist based on current conditions

**AI Features**
- **Dual AI Backend**: Google Gemini API (cloud) + Ollama (local)
- Auto-fallback: Tries Gemini first, falls back to Ollama on quota exceeded (429 errors)
- Features: mood detection, smart query translation, predictive downloads, wallpaper analysis
- Files: `smart_recommendations.py` contains AI logic
- Ollama config: `OLLAMA_HOST` environment variable (default: `http://localhost:11434`)

**Statistics & Ratings**
- `statistics_manager.py`: Tracks views, ratings, favorites, change history
- Persisted in `wallpaper_stats.json`
- Used for smart cache rotation and AI recommendations

**Weather Overlay**
- `weather_overlay.py`: Applies temperature/weather info overlay to wallpapers
- `weather_rotation.py`: Selects wallpapers/playlists based on weather conditions
- OpenWeatherMap API integration

### Important Data Files

```
current_wallpaper_info.json     # Current wallpaper for each monitor
monitors_status.json            # Monitor status (newly added for multi-monitor tracking)
provider_state.json             # Provider rotation state
wallpaper_stats.json            # User ratings, views, favorites
dynamic_rules.json              # Time/weather-based wallpaper rules
WallpaperChangerCache/          # Downloaded wallpapers
  index.json                    # Cache metadata (colors, tags, hashes)
```

## Multi-Monitor Implementation Details

### Span Mode (Fallback)
When per-monitor API fails (common on some Windows configurations):
1. Detects all monitors and their physical positions using `enumerate_monitors_user32()`
2. Creates composite image (`wallpaper_span.bmp`) with dimensions matching total desktop space
3. Pastes each monitor's wallpaper at correct offset based on physical position
4. Sets Windows registry `WallpaperStyle=22` for span mode
5. Applies via `SystemParametersInfoW()` legacy API

### GUI Manual Wallpaper Application
When user selects wallpaper from gallery and applies to specific monitor:
1. Attempts per-monitor API (`DesktopWallpaperController.set_wallpaper()`)
2. On failure, calls `_apply_wallpaper_span_mode()`:
   - Extracts current wallpaper of other monitors from existing span image
   - Creates new span with selected wallpaper for target monitor
   - Updates cache metadata for ALL monitors (not just target)
   - This ensures dashboard shows correct current wallpapers

### Cache Updates for Multi-Monitor
Critical: When applying wallpaper in span mode, must update cache for ALL monitors:
- `applied_wallpapers` dict tracks original paths for each monitor index
- Cache stores using monitor name ("Full HD", "Ultrawide") from `config.Monitors`
- Dashboard reads cache using monitor name mapping to show current wallpapers

## Common Issues & Solutions

### Multi-Monitor Wallpapers Not Working
- Check if `IDesktopWallpaper` API is available (requires Windows 8+)
- Verify `monitors_status.json` exists and is updated
- Ensure span mode sets registry correctly (`WallpaperStyle=22`)
- Cache must be updated for ALL monitors when applying wallpaper

### GUI Dashboard Shows Wrong/Old Wallpapers
- Dashboard reads from cache using monitor name mapping
- Ensure `_apply_wallpaper_span_mode()` updates cache for all monitors
- Check that monitor names in `config.Monitors` match cache entries
- Don't save temporary files to cache (extract from span for rendering only)

### AI Features Not Working
1. Check Gemini API key in `.env` or `config.GeminiApiKey`
2. Verify Ollama is running: `curl http://localhost:11434/api/tags`
3. Check logs for quota exceeded (429) errors - should auto-fallback to Ollama
4. Ensure at least one AI model installed in Ollama: `ollama list`

### Cache Deduplication Issues
- `monitor_index` in metadata prevents cross-monitor deduplication
- Perceptual hashing threshold: `DuplicateDetector.VERY_SIMILAR`
- Duplicates only checked within same monitor to allow same wallpaper on different monitors

## Configuration Best Practices

### Per-Monitor Setup
```python
Monitors = [
    {
        "name": "Full HD",        # Used for cache mapping
        "preset": "workspace",     # Different preset per monitor
        "screen_resolution": "1920x1080",
        # ... other settings
    },
    {
        "name": "Ultrawide",
        "preset": "relax",
        "screen_resolution": "3440x1440",
        # ... other settings
    },
]
```

### Provider Rotation
```python
ProvidersSequence = ["wallhaven", "pexels", "reddit"]
RotateProviders = True  # Cycles through providers on each change
```

### API Keys (.env file)
```
WALLHAVEN_API_KEY=your_key_here
PEXELS_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
OLLAMA_HOST=http://localhost:11434
```

## Git Commit Guidelines

This project uses conventional commits with the following format:
```
type(scope): description

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
Scopes: `wallpaper`, `gui`, `cache`, `ai`, `multi-monitor`, `config`, etc.

## Development Notes

- **Windows-only**: Uses Windows-specific APIs (`IDesktopWallpaper`, registry, `SystemParametersInfoW`)
- **Thread-safe cache**: Uses locks in `CacheManager` for concurrent access
- **Provider state persistence**: Prevents same provider being used consecutively in rotation
- **Smart cache rotation**: Protects starred/favorite wallpapers, removes low-rated/unviewed first
- **Weather overlays**: Applied before BMP conversion, stored as temporary files
- **Playlist weather integration**: OpenWeatherMap API determines playlist selection

## File Structure (Key Directories)

```
launchers/          # VBS scripts for background startup
icons/              # Tray icons, weather icons
marketing/          # Promotional materials
WallpaperChangerCache/  # Downloaded wallpapers (configurable location)
```

## External Dependencies

- **Pillow**: Image processing (resizing, cropping, color conversion)
- **CustomTkinter**: Modern UI framework
- **keyboard**: Global hotkey support
- **pystray**: System tray integration
- **imagehash**: Perceptual hashing for duplicate detection
- **google-generativeai**: Gemini API client
- **requests**: HTTP client for API calls
- **matplotlib**: Statistics charts in GUI
