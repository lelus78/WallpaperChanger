import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Choose which provider to use: "wallhaven" or "pexels"
Provider = "reddit"

# Optional ordered list of providers to rotate through across updates
ProvidersSequence = ["wallhaven", "pexels", "reddit"]

# Enable or disable provider rotation
RotateProviders = True

# Enter your Wallhaven API Key from https://wallhaven.cc/settings/account
# Or set it in the .env file as WALLHAVEN_API_KEY
ApiKey = os.getenv("WALLHAVEN_API_KEY", "")

# Enter your Pexels API key from https://www.pexels.com/api/new/
# Or set it in the .env file as PEXELS_API_KEY
PexelsApiKey = os.getenv("PEXELS_API_KEY", "")

# Choose how to fetch wallpapers from Pexels: "search" or "curated"
PexelsMode = "curated"

# Reddit settings for public JSON API access (no authentication required)
RedditSettings = {
    "user_agent": "WallpaperChanger/1.0 (by u/lelus78)",
    "subreddits": ["wallpapers", "wallpaper"],
    "sort": "hot",
    "time_filter": "day",
    "limit": 60,
    "min_score": 50,
    "allow_nsfw": False,
}

# Enter a search query/tag here to fetch wallpapers from
Query = "nature"

# Wallhaven only: 100 / 110 / 111 (sfw/sketchy/nsfw) turn purities on(1) or off(0)
# NSFW requires a valid Wallhaven API key. Example: "100" is SFW, "010" is Sketchy, "001" is NSFW.
PurityLevel = "100"

# Wallhaven only: minimum resolution allowed for images, default is 1920x1080
ScreenResolution = "3440x1440"

# Wallhaven only: sorting strategy ("random", "toplist", "favorites", "views")
WallhavenSorting = "toplist"

# Wallhaven only: optional toplist range ("1d","3d","1w","1M","6M","1y")
WallhavenTopRange = "1M"

# Cache settings: directory (blank for default), max_items (int), enable_offline_rotation (bool)
CacheSettings = {
    "directory": r"C:\Users\EmanueleO\WallpaperChangerCache",
    "max_items": 60,
    "enable_offline_rotation": True,
}

# Scheduler settings for automatic wallpaper rotation
SchedulerSettings = {
    "enabled": True,
    "interval_minutes": 45,
    "jitter_minutes": 10,
    "initial_delay_minutes": 1,
    "quiet_hours": [
        {"start": "23:30", "end": "07:00"},
    ],
    "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
}

# Advanced preset definitions
Presets = [
    {
        "name": "workspace",
        "title": "Workspace Focus",
        "description": "Clean and minimal wallpapers for productivity.",
        "providers": ["wallhaven", "pexels", "reddit"],
        "queries": ["technology"],
        "exclude": [],
        "colors": ["2b4450"],
        "ratios": ["16x9", "21x9"],
        "purity": "100",
        "screen_resolution": "3440x1440",
        "wallhaven": {
            "sorting": "toplist",
            "top_range": "1M",
            "atleast": "2560x1440",
        },
        "pexels": {
            "orientation": "landscape",
            "size": "large2x",
        },
        "reddit": {
            "subreddits": ["wallpapers", "ultrahdwallpapers"],
            "sort": "hot",
            "time_filter": "day",
            "min_score": 80,
        },
    },
    {
        "name": "relax",
        "title": "Relaxing Nature",
        "description": "Calming landscapes for breaks.",
        "providers": ["wallhaven", "pexels", "reddit"],
        "queries": ["nature", "landscape"],
        "exclude": ["city", "crowd"],
        "colors": ["004e92", "263238"],
        "ratios": ["21x9", "16x10"],
        "purity": "100",
        "screen_resolution": "3440x1440",
        "wallhaven": {
            "sorting": "toplist",
            "top_range": "1w",
        },
        "pexels": {
            "orientation": "landscape",
        },
        "reddit": {
            "subreddits": ["EarthPorn", "wallpaper", "NatureIsFuckingLit"],
            "sort": "top",
            "time_filter": "week",
            "min_score": 200,
        },
    },
]

DefaultPreset = "workspace"

# Default is ctrl+alt+w, use https://github.com/boppreh/keyboard#api to see all different key names
KeyBind = "ctrl+alt+w"

# Optional per-monitor overrides. The list order matches your physical monitors.
# Each entry can override provider/query/preset just for that screen.
# Leave provider empty to inherit the active rotation, leave preset empty to use the default preset.
Monitors = [
    {
        "name": "Full HD",
        "preset": "workspace",
        "provider": "",
        "query": "",
        "screen_resolution": "1920x1080",
        "purity": "100",
        "wallhaven_sorting": "random",
        "wallhaven_top_range": "1M",
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
