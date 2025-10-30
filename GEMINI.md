# Project Overview

The Wallpaper Changer is a Python application designed to automatically refresh desktop wallpapers using images from configurable providers like Wallhaven and Pexels. It features a graphical user interface (GUI) for configuration, a system tray companion for quick actions, a flexible scheduler, and a local caching mechanism for offline wallpaper rotation. The application supports per-monitor wallpaper overrides and global hotkeys for manual refreshes.

**Key Technologies:**
*   Python (3.10+)
*   `requests` for API interactions
*   `Pillow` for image processing
*   `keyboard` for global hotkey detection
*   `pystray` for system tray integration
*   `python-dotenv` for environment variable management

# Building and Running

## Installation

1.  **Install Python:** Ensure Python 3.10 or newer is installed. Download from [python.org](https://www.python.org/downloads/).
2.  **Install Dependencies:** From the project directory, run:
    ```bash
    pip install requests pillow keyboard pystray python-dotenv
    ```
3.  **Configure API Keys:**
    *   Copy `.env.example` to `.env`.
    *   Obtain API keys from Wallhaven ([wallhaven.cc/help/api](https://wallhaven.cc/help/api)) and Pexels ([pexels.com/api/new](https://www.pexels.com/api/new/)) and add them to the `.env` file.
4.  **Customize Settings:**
    *   **GUI:** Launch the GUI using `launchers/start_config_gui.vbs` or `python gui_config.py`.
    *   **Manual:** Edit `config.py` directly.

## Running the Application

*   **Start Wallpaper Changer:** Double-click `launchers/start_wallpaper_changer.vbs` to run in the background. Alternatively, run `python main.py` from the terminal.
*   **Start Configuration GUI:** Double-click `launchers/start_config_gui.vbs` or run `python gui_config.py`.
*   **Stop Wallpaper Changer:** Double-click `launchers/stop_wallpaper_changer.vbs` or use the "Exit" option from the system tray icon.

## Testing

The project includes test files such as `test_cache.py` and `test_wallhaven.py`. To run tests, you would typically use a command like `pytest` if it's installed, or run the test files directly.

# Development Conventions

*   **Language:** Python is the primary development language.
*   **Configuration:** API keys and sensitive information are managed via `.env` files.
*   **Launchers:** `.vbs` scripts are used for convenient launching and stopping of the application components on Windows.
*   **Modularity:** The project is structured into several Python modules (e.g., `cache_manager.py`, `config.py`, `scheduler_service.py`, `tray_app.py`) to manage different functionalities.
