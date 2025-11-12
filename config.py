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

# Enter your Google Gemini API key from https://makersuite.google.com/app/apikey
# Or set it in the .env file as GEMINI_API_KEY
GeminiApiKey = os.getenv("GEMINI_API_KEY", "")

# Choose how to fetch wallpapers from Pexels: "search" or "curated"
PexelsMode = "curated"

# Search query for Pexels when using "search" mode (e.g., "nature", "abstract", "minimal")
PexelsQuery = "nature"

# Reddit settings for public JSON API access (no authentication required)
RedditSettings = {
    "user_agent": "WallpaperChanger/1.0 (by u/lelus78)",
    "subreddits": ['wallpapers', 'wallpaper'],
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
# Use None or empty string for default location (~\WallpaperChangerCache)
CacheSettings = {
    "directory": "",  # Empty = use default location in user's home directory
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
    "subreddits": ['wallpapers', 'wallpaper'],
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
    "subreddits": ['wallpapers', 'wallpaper'],
            "sort": "top",
            "time_filter": "week",
            "min_score": 200,
        },
    },
]

DefaultPreset = "workspace"

# Default is ctrl+alt+w, use https://github.com/boppreh/keyboard#api to see all different key names
KeyBind = "ctrl+alt+w"


# Weather-based playlists - each optimized for specific weather conditions
Playlists = [
    {"name": "sunny_work", "title": "Sunny Productivity", "tags": ["sunny"],
     "entries": [
         {"title": "Bright Focus", "preset": "workspace", "weight": 3, "query": "bright technology minimal"},
         {"title": "Sunrise Energy", "preset": "relax", "weight": 1, "query": "sunrise landscape bright"}
     ]},
    {"name": "cloudy_focus", "title": "Cloudy Concentration", "tags": ["cloudy"],
     "entries": [
         {"title": "Gentle Workspace", "preset": "workspace", "weight": 2, "query": "clouds minimal peaceful"},
         {"title": "Misty Mountains", "preset": "relax", "weight": 1, "query": "foggy mountains landscape"}
     ]},
    {"name": "rain_relax", "title": "Rainy Day Comfort", "tags": ["rain"],
     "entries": [
         {"title": "Cozy Interior", "preset": "relax", "weight": 2, "query": "cozy rain window"},
         {"title": "Rain Droplets", "preset": "workspace", "weight": 1, "query": "rain water drops dark"}
     ]},
    {"name": "night_calm", "title": "Night Wind Down", "tags": ["night"],
     "entries": [
         {"title": "Blue Hour", "preset": "relax", "weight": 2, "query": "blue hour landscape night"},
         {"title": "City Lights", "preset": "workspace", "weight": 1, "query": "night city lights"}
     ]},
    {"name": "storm_power", "title": "Storm Energy", "tags": ["storm"],
     "entries": [
         {"title": "Thunder Clouds", "preset": "relax", "weight": 2, "query": "storm clouds dramatic dark"},
         {"title": "Lightning Power", "preset": "workspace", "weight": 1, "query": "lightning storm nature"}
     ]}
]

DefaultPlaylist = ""

WeatherRotationSettings = {
    "enabled": True,
    "provider": "openweathermap",
    "api_key": os.getenv("OPENWEATHER_API_KEY", ""),
    "refresh_minutes": 30,
    "apply_on": ['startup', 'scheduler', 'hotkey', 'tray', 'gui'],
    "units": "metric",
    "location": {
        "city": "cameri",
        "country": "it",
        "latitude": 45.4642,
        "longitude": 9.19,
    },
    "conditions": {
        "clear": {"playlist": "sunny_work"},
        "night_clear": {"playlist": "night_calm"},
        "clouds": {"playlist": "cloudy_focus"},
        "rain": {"playlist": "rain_relax"},
        "drizzle": {"playlist": "rain_relax"},
        "snow": {"preset": "relax"},
        "thunderstorm": {"playlist": "storm_power"},
        "mist": {"playlist": "cloudy_focus"},
        "fog": {"playlist": "cloudy_focus"},
        "storm": {"playlist": "storm_power"},
        "default": {"playlist": "sunny_work"},
    },
}

# Weather overlay settings - draws weather info on wallpaper
WeatherOverlaySettings = {
    "enabled": True,
    "position": "top-right",  # "top-left", "top-right", "bottom-left", "bottom-right"
    "opacity": 0.60,  # 0.0 to 1.0
    "font_size": 48,  # Font size for main text
    "padding": 45,  # Padding around text
    "background_blur": 20,  # Blur radius (0 = no blur, higher = more blur)
    "background_color": (20, 20, 30, 180),  # Semi-transparent dark background (R, G, B, Alpha 0-255)
    "text_color": (255, 255, 255),  # White text for better contrast
}

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
