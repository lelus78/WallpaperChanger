# 🖼️ Wallpaper Changer

A modern, feature-rich wallpaper manager for Windows that automatically downloads and applies beautiful wallpapers from multiple sources (Wallhaven, Pexels, Reddit).

## ✨ Key Features

### Modern GUI
- **Beautiful Interface** - Clean, dark-themed modern UI built with CustomTkinter
- **Wallpaper Gallery** - Browse, filter, and preview all cached wallpapers with responsive 3-column layout
- **Fullscreen Viewer** - Click any wallpaper to view in full resolution
- **Tag System** - Auto-extracted tags from providers for easy filtering
- **Color Filtering** - Filter wallpapers by dominant color with visual color badges
- **Duplicate Detection** - Find and manage similar wallpapers with adjustable sensitivity (Exact, Nearly Identical, Very Similar, Similar, Somewhat Similar)
- **Instant Duplicate Removal** - Delete duplicates with zero lag, no rescanning required
- **Statistics Dashboard** - Track usage, favorites, and view distribution charts
- **Rating & Favorites** - 5-star rating system and favorites management
- **Wallpaper Deletion** - Permanently remove unwanted wallpapers with confirmation dialog

### Smart Wallpaper Management
- **Multi-Monitor Support** - Different wallpapers for each monitor with cross-monitor duplicate prevention
- **Auto-Download** - Fresh wallpapers from Wallhaven, Reddit, and Pexels
- **Multi-Provider Downloads** - Instant download buttons for all three providers in search and AI features
- **Smart Caching** - Intelligent cache rotation that protects starred and favorite wallpapers
- **Advanced Duplicate Prevention** - Automatic detection using perceptual hashing with cross-monitor blocking (threshold: distance ≤ 3)
  - Prevents downloading same wallpaper for different monitors automatically
  - User can still manually apply same wallpaper via GUI if desired
  - Stricter "Nearly Identical" threshold for better duplicate detection
- **Color Extraction** - Fast color analysis (100x faster) with dominant color identification
- **Weather Overlays** - Display current temperature on wallpapers
- **Playlists** - Create themed collections for different moods/times
- **Scheduled Changes** - Automatic rotation with configurable intervals

### AI-Powered Features
- **AI Mood Detection** - Automatically analyzes your mood and suggests matching wallpapers
- **Smart Query Translation** - Automatically translates search queries from any language to English for better results
- **AI Predictive Downloads** - Get AI-suggested wallpapers with interactive preview mode
- **Interactive Preview** - Compare multiple downloads before applying, dialog stays open to try different providers
- **Local AI with Ollama** - Complete offline AI functionality with automatic Gemini → Ollama fallback
- **Privacy Mode** - Optional local-only AI processing without any cloud API calls
- **Unlimited AI Usage** - No quota limits when using local Ollama models (llama3.2, phi3, mistral, etc.)
- **Robust Downloads** - Browser-like headers and retry logic for reliable image downloads even from restrictive hosts

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
   pip install requests pillow customtkinter matplotlib keyboard pystray python-dotenv imagehash google-generativeai
   ```

3. Configure API keys (optional):
   - Copy `.env.example` to `.env` and add your API keys
   - **Wallhaven** – [Get API key](https://wallhaven.cc/help/api)
   - **Pexels** – [Get API key](https://www.pexels.com/api/new/)
   - **Reddit** - No key required
   - **Google Gemini** – [Get API key](https://makersuite.google.com/app/apikey) (for AI features, 250 requests/day free)

4. Setup Local AI (Optional but Recommended):
   - **Install Ollama**: Download from [ollama.ai](https://ollama.ai)
   - **Pull a model**: `ollama pull llama3.2:3b` (or phi3, mistral, gemma)
   - **Benefits**: Unlimited AI usage, complete privacy, works offline
   - **Docker Setup**: See [setup_ollama_docker.md](setup_ollama_docker.md) for containerized setup

5. Customize settings:
   - **GUI**: Run `python gui_config.py`
   - **Manual**: Edit `config.py`

## 🤖 AI Features Guide

### Multi-Language Smart Search
The AI automatically translates and improves your search queries:
- Type in **any language**: "un cagnolino", "美しい山", "schöner Sonnenuntergang"
- AI translates to English and improves: "Little puppy", "Beautiful mountain", "Sunset scenery"
- Works with all three providers (Pexels, Reddit, Wallhaven)

### Multi-Provider Downloads
Every search and AI feature includes instant download buttons:
- **Pexels** (blue) - High-quality curated photos
- **Reddit** (orange) - Community-voted wallpapers
- **Wallhaven** (green) - Vast wallpaper collection
- Click any button to download from that source

### AI Mood Detection
1. Open the **AI Assistant** tab
2. Click **"Detect Mood"** - AI analyzes time, weather, and your preferences
3. Get personalized wallpaper suggestions with download buttons
4. Each provider button downloads a matching wallpaper instantly

### AI Predictive Downloads with Interactive Preview
1. Go to **AI Assistant** → **AI Predictive**
2. AI suggests your next wallpaper based on usage patterns
3. Click any provider button (Pexels/Reddit/Wallhaven) to download alternatives
4. **Preview updates live** - see each download before applying
5. Compare multiple options without closing the dialog
6. Click **"Apply"** when you find the perfect one

### Local AI with Ollama (Recommended)
**Why use Ollama?**
- ✅ Unlimited AI requests (no quota limits)
- ✅ Complete privacy (no data sent to cloud)
- ✅ Works offline
- ✅ Automatic fallback when Gemini quota exceeded
- ✅ Multiple model choices (llama3.2, phi3, mistral, gemma)

**Quick Setup:**
```bash
# 1. Install Ollama
# Download from https://ollama.ai

# 2. Pull a model (choose one)
ollama pull llama3.2:3b    # Recommended - fast & small (2GB)
ollama pull phi3:mini      # Alternative - Microsoft model
ollama pull mistral:latest # Larger but more capable

# 3. Start using AI features - automatic fallback works!
```

**Docker Setup** (for advanced users):
```bash
# 1. Create Ollama container
docker run -d --name ollama -p 11434:11434 ollama/ollama

# 2. Download model inside container
docker exec -it ollama ollama pull llama3.2:3b

# 3. Set environment variable (optional)
export OLLAMA_HOST=http://localhost:11434  # Linux/Mac
$env:OLLAMA_HOST = "http://localhost:11434" # Windows PowerShell
```

See [setup_ollama_docker.md](setup_ollama_docker.md) for detailed Docker instructions.

### Privacy Mode
Enable **"Use Local AI Only"** checkbox in the AI Assistant tab:
- ✅ All AI processing stays on your machine
- ✅ No data sent to Google Gemini
- ✅ Requires Ollama installed
- ❌ Disabled if no Ollama models found

### AI Fallback Behavior
The application intelligently manages AI providers:
1. **Try Gemini first** (if API key configured and not in privacy mode)
2. **Auto-fallback to Ollama** on quota exceeded (429 errors)
3. **Seamless experience** - you won't see errors, just logs
4. **All features covered**: Mood detection, prediction, search, wallpaper analysis

### Testing AI Features
Run the test script to verify your setup:
```bash
python test_ollama_fallback.py
```

Expected output:
- ✅ Detects Ollama installation
- ✅ Lists available models
- ✅ Tests generation with sample prompt
- ✅ Simulates quota exceeded scenario

### Gallery Features

**Wallpaper Deletion:**
- Each wallpaper card has a **🗑️ delete button**
- Click to permanently remove unwanted wallpapers
- Confirmation dialog prevents accidental deletion
- Cleanup includes: file, cache index, statistics, thumbnails

**Tag System:**
- Tags auto-extracted from provider metadata
- Display in gallery with 🏷️ emoji
- Filter wallpapers by clicking tags
- Works with AI-downloaded wallpapers

### Duplicate Detection & Management

**Automatic Prevention During Download:**
- Cross-monitor duplicate detection prevents downloading the same wallpaper for different monitors
- Uses perceptual hashing with "Nearly Identical" threshold (distance ≤ 3)
- Works automatically in the background - no user intervention needed
- User can still manually apply same wallpaper to multiple monitors via GUI

**Manual Duplicate Scanning:**
1. Go to **Duplicates** tab in the GUI
2. Select sensitivity level:
   - **Exact** (distance = 0) - Only identical files
   - **Nearly Identical** (distance ≤ 3) - Extremely similar (default for auto-prevention)
   - **Very Similar** (distance ≤ 5) - Minor edits, compression differences
   - **Similar** (distance ≤ 10) - Similar composition/content
   - **Somewhat Similar** (distance ≤ 15) - Some visual similarities
3. Click **"Scan for Duplicates"**
4. Review side-by-side comparisons
5. Click **"Delete"** on duplicates - instant removal with zero lag!

**Performance:**
- Instant deletion (no rescanning after each removal)
- Perceptual hashing cached for fast comparisons
- Test with `python test_duplicate_prevention.py` to verify cross-monitor blocking

**Command-Line Tools:**
```bash
# Find and list all duplicates
python find_duplicates.py

# Populate perceptual hashes for existing wallpapers
python populate_colors.py  # Also includes hash computation
```

## Configuration Highlights (`config.py`)

- `Provider` / `ProvidersSequence`: default provider(s) and rotation order.
- `ApiKey` / `PexelsApiKey` / `PexelsMode`: provider credentials and default mode (`search` or `curated` for Pexels).
- `GeminiApiKey`: Google Gemini API key for AI features (250 requests/day free tier).
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
