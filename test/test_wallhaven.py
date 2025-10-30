import os
import sys
import logging
from typing import Dict, Tuple

# Add the current directory to the Python path to allow importing from main
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from main import WallpaperApp, normalize_wallhaven_sorting, normalize_wallhaven_top_range
from config import ApiKey, PurityLevel, ScreenResolution, WallhavenSorting, WallhavenTopRange

# Configure basic logging to see output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_wallhaven_fetch():
    logger.info("Starting Wallhaven fetch test...")

    # Create a dummy WallpaperApp instance.
    # We'll mock out the parts that interact with the desktop or GUI.
    class MockWallpaperApp(WallpaperApp):
        def __init__(self):
            # Initialize only the parts needed for _fetch_wallhaven
            self.app_dir = os.path.dirname(os.path.abspath(__file__))
            self.logger = logger # Use the logger defined above
            self.preset_manager = None # Not needed for _fetch_wallhaven directly
            self.cache_manager = None # Not needed for _fetch_wallhaven directly
            self.scheduler = None # Not needed for _fetch_wallhaven directly
            self.tray_app = None # Not needed for _fetch_wallhaven directly
            self._stop_event = None # Not needed for _fetch_wallhaven directly
            self.pid_path = None # Not needed for _fetch_wallhaven directly
            self._pid_registered = False # Not needed for _fetch_wallhaven directly
            self.provider_state_path = None # Not needed for _fetch_wallhaven directly

        # Mock methods that would be called but are not relevant for fetching
        def _create_desktop_controller(self):
            return None
        def _apply_legacy_wallpaper(self, image_path: str) -> None:
            pass
        def _download_wallpaper(self, url: str, target_path: str) -> None:
            logger.info(f"Mock download: {url} to {target_path}")
            # In a real test, you might download a small dummy file
            pass
        def _render_image(self, source_path: str, size: Tuple[int, int]) -> object:
            # Return a mock image object or None
            return None
        def _convert_to_bmp(self, source_path: str, target_name: str, size: Tuple[int, int]) -> str:
            return "mock_bmp_path.bmp"
        def _get_primary_size(self) -> Tuple[int, int]:
            return (1920, 1080) # Dummy size

    mock_app = MockWallpaperApp()

    # Construct a dummy task dictionary
    # These values are taken from config.py defaults or common settings
    task = {
        "preset": "test_preset",
        "provider": "wallhaven",
        "monitor": {"width": 1920, "height": 1080}, # Dummy monitor info
        "label": "Test Monitor",
        "query": "nature", # Example query
        "wallhaven": {
            "sorting": normalize_wallhaven_sorting(WallhavenSorting),
            "top_range": normalize_wallhaven_top_range(WallhavenTopRange),
            "purity": PurityLevel,
            "atleast": ScreenResolution,
            "resolutions": ScreenResolution, # Add resolutions for completeness
            "colors": "",
            "ratios": "",
            "categories": "",
        },
        "pexels": {}, # Not used for Wallhaven
        "target_size": (1920, 1080),
    }

    try:
        url, source_info = mock_app._fetch_wallhaven(task)
        logger.info(f"Successfully fetched from Wallhaven:")
        logger.info(f"  URL: {url}")
        logger.info(f"  Source Info: {source_info}")
        return True
    except Exception as e:
        logger.error(f"Failed to fetch from Wallhaven: {e}")
        return False

if __name__ == "__main__":
    if test_wallhaven_fetch():
        logger.info("Wallhaven fetch test completed successfully.")
    else:
        logger.error("Wallhaven fetch test failed.")
