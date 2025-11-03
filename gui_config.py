import ast
import json
import os
import pprint
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, scrolledtext
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageTk

from cache_manager import CacheManager
from config import CacheSettings


class WallpaperConfigGUI:
    # Modern color scheme
    COLORS = {
        'bg_primary': '#1e1e2e',
        'bg_secondary': '#2a2a3e',
        'bg_tertiary': '#363650',
        'accent': '#89b4fa',
        'accent_hover': '#b4befe',
        'success': '#a6e3a1',
        'warning': '#f9e2af',
        'error': '#f38ba8',
        'text_primary': '#cdd6f4',
        'text_secondary': '#a6adc8',
        'text_muted': '#6c7086',
        'border': '#45475a',
        'shadow': '#11111b',
    }

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Wallpaper Changer - Configuration")
        self.root.geometry("1100x750")

        # Set window icon if available
        try:
            icon_path = Path(__file__).parent / "icon.ico"
            if icon_path.exists():
                self.root.iconbitmap(icon_path)
        except:
            pass

        # Configure modern theme
        self._setup_theme()

        base_path = Path(__file__).parent
        self.config_path = base_path / "config.py"
        self.provider_state_path = base_path / "provider_state.json"
        self.config_data: Dict[str, Any] = {}

        cache_dir = CacheSettings.get("directory") or os.path.join(
            os.path.expanduser("~"), "WallpaperChangerCache"
        )
        self.cache_manager = CacheManager(
            cache_dir,
            max_items=int(CacheSettings.get("max_items", 60)),
            enable_rotation=bool(CacheSettings.get("enable_offline_rotation", True)),
        )

        # Thumbnail cache to avoid reloading images
        self.thumbnail_cache = {}

        # Filter and sort state
        self.filter_resolution = tk.StringVar(value="All")
        self.sort_by = tk.StringVar(value="Newest First")

        self._load_config()

        self.playlists_data: List[Dict[str, Any]] = list(self.config_data.get("Playlists") or [])
        self.weather_settings: Dict[str, Any] = dict(self.config_data.get("WeatherRotationSettings") or {})

        # Check and start main app if not running
        self._ensure_main_app_running()

        self._create_widgets()

    def _setup_theme(self) -> None:
        """Setup modern theme with custom styles"""
        style = ttk.Style()

        # Use a modern theme as base
        try:
            style.theme_use('clam')
        except:
            style.theme_use('default')

        # Configure root window
        self.root.configure(bg=self.COLORS['bg_primary'])

        # Configure Notebook (tabs)
        style.configure('TNotebook',
            background=self.COLORS['bg_primary'],
            borderwidth=0,
            tabmargins=[2, 5, 2, 0])

        style.configure('TNotebook.Tab',
            background=self.COLORS['bg_secondary'],
            foreground=self.COLORS['text_secondary'],
            padding=[20, 10],
            borderwidth=0,
            font=('Segoe UI', 10, 'bold'))

        style.map('TNotebook.Tab',
            background=[('selected', self.COLORS['bg_tertiary'])],
            foreground=[('selected', self.COLORS['accent'])],
            expand=[('selected', [1, 1, 1, 0])])

        # Configure Frames
        style.configure('TFrame',
            background=self.COLORS['bg_primary'])

        style.configure('Card.TFrame',
            background=self.COLORS['bg_secondary'],
            borderwidth=1,
            relief='solid')

        # Configure LabelFrame
        style.configure('TLabelframe',
            background=self.COLORS['bg_secondary'],
            foreground=self.COLORS['text_primary'],
            bordercolor=self.COLORS['border'],
            borderwidth=2,
            relief='flat',
            font=('Segoe UI', 10, 'bold'))

        style.configure('TLabelframe.Label',
            background=self.COLORS['bg_secondary'],
            foreground=self.COLORS['accent'],
            font=('Segoe UI', 11, 'bold'))

        # Configure Labels
        style.configure('TLabel',
            background=self.COLORS['bg_secondary'],
            foreground=self.COLORS['text_primary'],
            font=('Segoe UI', 9))

        style.configure('Title.TLabel',
            font=('Segoe UI', 12, 'bold'),
            foreground=self.COLORS['accent'])

        style.configure('Subtitle.TLabel',
            font=('Segoe UI', 10),
            foreground=self.COLORS['text_secondary'])

        # Configure Buttons
        style.configure('TButton',
            background=self.COLORS['accent'],
            foreground='#1e1e2e',
            borderwidth=0,
            focuscolor='none',
            font=('Segoe UI', 9, 'bold'),
            padding=[15, 8])

        style.map('TButton',
            background=[('active', self.COLORS['accent_hover']),
                       ('pressed', self.COLORS['accent'])],
            foreground=[('active', '#1e1e2e')])

        style.configure('Accent.TButton',
            background=self.COLORS['accent'],
            font=('Segoe UI', 10, 'bold'),
            padding=[20, 10])

        style.configure('Success.TButton',
            background=self.COLORS['success'],
            foreground='#1e1e2e')

        style.configure('Danger.TButton',
            background=self.COLORS['error'],
            foreground='#1e1e2e')

        # Configure Entry
        style.configure('TEntry',
            fieldbackground=self.COLORS['bg_tertiary'],
            foreground=self.COLORS['text_primary'],
            bordercolor=self.COLORS['border'],
            lightcolor=self.COLORS['border'],
            darkcolor=self.COLORS['border'],
            insertcolor=self.COLORS['text_primary'],
            font=('Segoe UI', 9))

        # Configure Combobox
        style.configure('TCombobox',
            fieldbackground=self.COLORS['bg_tertiary'],
            background=self.COLORS['bg_tertiary'],
            foreground=self.COLORS['text_primary'],
            arrowcolor=self.COLORS['text_primary'],
            bordercolor=self.COLORS['border'],
            lightcolor=self.COLORS['border'],
            darkcolor=self.COLORS['border'],
            font=('Segoe UI', 9))

        style.map('TCombobox',
            fieldbackground=[('readonly', self.COLORS['bg_tertiary'])],
            foreground=[('readonly', self.COLORS['text_primary'])])

        # Configure Spinbox
        style.configure('TSpinbox',
            fieldbackground=self.COLORS['bg_tertiary'],
            foreground=self.COLORS['text_primary'],
            arrowcolor=self.COLORS['text_primary'],
            bordercolor=self.COLORS['border'],
            font=('Segoe UI', 9))

        # Configure Checkbutton
        style.configure('TCheckbutton',
            background=self.COLORS['bg_secondary'],
            foreground=self.COLORS['text_primary'],
            font=('Segoe UI', 9))

        style.map('TCheckbutton',
            background=[('active', self.COLORS['bg_tertiary'])],
            foreground=[('active', self.COLORS['accent'])])

        # Configure Scrollbar
        style.configure('Vertical.TScrollbar',
            background=self.COLORS['bg_tertiary'],
            troughcolor=self.COLORS['bg_secondary'],
            bordercolor=self.COLORS['border'],
            arrowcolor=self.COLORS['text_primary'])

        # Configure Canvas for gallery
        self.root.option_add('*TCombobox*Listbox.background', self.COLORS['bg_tertiary'])
        self.root.option_add('*TCombobox*Listbox.foreground', self.COLORS['text_primary'])
        self.root.option_add('*TCombobox*Listbox.selectBackground', self.COLORS['accent'])
        self.root.option_add('*TCombobox*Listbox.selectForeground', '#1e1e2e')

    def _bind_mousewheel(self, widget) -> None:
        """Bind mouse wheel scrolling to canvas"""
        def on_mousewheel(event):
            widget.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def on_enter(event):
            widget.bind_all("<MouseWheel>", on_mousewheel)

        def on_leave(event):
            widget.unbind_all("<MouseWheel>")

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def _ensure_main_app_running(self) -> None:
        """Ensure the main wallpaper app is running, start it if not"""
        import subprocess

        pid_path = Path(__file__).parent / "wallpaperchanger.pid"

        if not pid_path.exists():
            # Automatically start the service without asking
            try:
                # Start the main app in background
                main_script = Path(__file__).parent / "main.py"
                subprocess.Popen(
                    ["pythonw", str(main_script)],
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                print("Wallpaper Changer service started automatically")
                # Mark that we started the service
                self.service_started_by_gui = True
            except Exception as e:
                messagebox.showerror(
                    "Error",
                    f"Failed to start Wallpaper Changer service:\n{e}\n\n"
                    "Please start it manually using:\n"
                    "• launchers/start_wallpaper_changer.vbs\n"
                    "• or 'python main.py'"
                )
                self.service_started_by_gui = False
        else:
            # Service was already running
            self.service_started_by_gui = False

    def _check_app_status(self) -> bool:
        """Check if main app is running"""
        pid_path = Path(__file__).parent / "wallpaperchanger.pid"
        return pid_path.exists()

    def _update_status_indicator(self) -> None:
        """Update the status indicator"""
        if hasattr(self, 'status_label'):
            is_running = self._check_app_status()
            if is_running:
                self.status_label.configure(
                    text="🟢 Service Running",
                    foreground=self.COLORS['success']
                )
            else:
                self.status_label.configure(
                    text="🔴 Service Stopped",
                    foreground=self.COLORS['error']
                )

        # Schedule next update
        self.root.after(3000, self._update_status_indicator)

    def _send_signal_command(self, payload: Any) -> bool:
        """Write a command payload for the main app to consume."""
        signal_path = self.provider_state_path.with_name("wallpaperchanger.signal")
        try:
            if signal_path.exists():
                signal_path.unlink()
            with open(signal_path, "w", encoding="utf-8") as handle:
                if isinstance(payload, (dict, list)):
                    json.dump(payload, handle)
                else:
                    handle.write(str(payload))
            return True
        except Exception as exc:
            messagebox.showerror(
                "Error",
                "Failed to communicate with the Wallpaper Changer service.\n\n"
                f"Details: {exc}"
            )
            return False

    def _format_provider_info(self, state: Dict[str, Any]) -> str:
        """Build a short status string describing provider rotation."""
        if not state:
            return "Provider info unavailable."

        info_parts: List[str] = []

        sequences = state.get("sequences")
        if isinstance(sequences, list):
            sequence_entry = None
            for entry in sequences:
                if not isinstance(entry, dict):
                    continue
                sequence = entry.get("sequence")
                if isinstance(sequence, list) and sequence:
                    sequence_entry = entry
                    break
            if sequence_entry:
                sequence_list = [str(item) for item in sequence_entry.get("sequence", [])]
                next_provider = sequence_entry.get("next_provider")
                if not next_provider and sequence_list:
                    next_index = sequence_entry.get("next_index", 0)
                    if isinstance(next_index, int) and sequence_list:
                        next_provider = sequence_list[next_index % len(sequence_list)]
                if sequence_list:
                    info_parts.append(f"Sequence: {' -> '.join(sequence_list)}")
                if next_provider:
                    info_parts.append(f"Next: {next_provider}")

        providers_used = state.get("providers_used")
        if isinstance(providers_used, list) and providers_used:
            info_parts.append(f"Last used: {', '.join(str(p) for p in providers_used)}")

        timestamp = state.get("timestamp")
        if isinstance(timestamp, str) and timestamp:
            info_parts.append(f"Updated: {timestamp}")

        note = state.get("note")
        if isinstance(note, str) and note:
            info_parts.append(note)

        if not info_parts:
            return "Provider rotation not configured."
        return " | ".join(info_parts)

    def _update_provider_info(self, schedule_next: bool = True) -> None:
        """Refresh provider rotation label from shared state."""
        if not hasattr(self, "provider_info_label"):
            return

        state: Dict[str, Any] = {}
        try:
            if self.provider_state_path.exists():
                with open(self.provider_state_path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if isinstance(data, dict):
                    state = data
        except (OSError, json.JSONDecodeError):
            state = {}

        self.provider_info_label.configure(text=self._format_provider_info(state))

        if schedule_next:
            self.root.after(5000, self._update_provider_info)

    def _cycle_provider(self) -> None:
        """Advance provider rotation without triggering a change."""
        if not self._check_app_status():
            messagebox.showwarning(
                "Service Not Running",
                "Start the Wallpaper Changer service before cycling providers."
            )
            return

        if hasattr(self, "provider_info_label"):
            self.provider_info_label.configure(text="Cycling provider...")

        if self._send_signal_command({"action": "cycle_provider"}):
            self.root.after(750, lambda: self._update_provider_info(schedule_next=False))

    def _reset_provider_rotation(self) -> None:
        """Reset provider rotation to the first provider."""
        if not self._check_app_status():
            messagebox.showwarning(
                "Service Not Running",
                "Start the Wallpaper Changer service before resetting the rotation."
            )
            return

        confirm = messagebox.askyesno(
            "Reset Provider Rotation",
            "Reset the provider rotation back to the first provider?"
        )
        if not confirm:
            return

        if hasattr(self, "provider_info_label"):
            self.provider_info_label.configure(text="Resetting provider rotation...")

        if self._send_signal_command({"action": "reset_provider_rotation"}):
            self.root.after(750, lambda: self._update_provider_info(schedule_next=False))

    def _toggle_service(self) -> None:
        """Toggle the wallpaper service on/off"""
        import subprocess

        is_running = self._check_app_status()

        if is_running:
            # Stop the service
            result = messagebox.askyesno(
                "Stop Service?",
                "Are you sure you want to stop the Wallpaper Changer service?\n\n"
                "Automatic wallpaper changes will be disabled."
            )

            if result:
                try:
                    pid_path = Path(__file__).parent / "wallpaperchanger.pid"
                    if pid_path.exists():
                        with open(pid_path, 'r') as f:
                            pid = int(f.read().strip())

                        # Kill the process
                        if os.name == 'nt':
                            subprocess.run(['taskkill', '/F', '/PID', str(pid)], check=True)
                        else:
                            os.kill(pid, 9)

                        messagebox.showinfo("Service Stopped", "Wallpaper Changer service stopped successfully.")
                        self._update_status_indicator()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to stop service: {e}")
        else:
            # Start the service
            try:
                main_script = Path(__file__).parent / "main.py"
                subprocess.Popen(
                    ["pythonw", str(main_script)],
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                messagebox.showinfo("Service Started", "Wallpaper Changer service started successfully!")
                self.root.after(1000, self._update_status_indicator)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start service: {e}")

    def _on_closing(self) -> None:
        """Handle GUI closing - stop service if we started it"""
        if hasattr(self, 'service_started_by_gui') and self.service_started_by_gui:
            # We started the service, so stop it when closing
            try:
                pid_path = Path(__file__).parent / "wallpaperchanger.pid"
                if pid_path.exists():
                    with open(pid_path, 'r') as f:
                        pid = int(f.read().strip())

                    # Kill the process
                    import subprocess
                    if os.name == 'nt':
                        subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True)
                    else:
                        os.kill(pid, 9)

                    print("Wallpaper Changer service stopped")
            except Exception as e:
                print(f"Error stopping service: {e}")

        # Close the GUI
        self.root.quit()
        self.root.destroy()

    def _minimize_to_tray(self) -> None:
        """Minimize GUI to system tray"""
        try:
            import pystray
            from PIL import Image, ImageDraw

            # Hide the main window
            self.root.withdraw()

            # Create tray icon
            def create_icon():
                image = Image.new('RGB', (64, 64), color=(137, 180, 250))
                draw = ImageDraw.Draw(image)
                draw.rectangle([10, 10, 54, 54], fill=(30, 30, 46))
                draw.text((20, 20), "WC", fill=(137, 180, 250))
                return image

            def on_show(icon, item):
                icon.stop()
                self.root.deiconify()

            def on_quit(icon, item):
                icon.stop()
                self.root.deiconify()
                self._on_closing()

            icon = pystray.Icon(
                "Wallpaper Config",
                create_icon(),
                "Wallpaper Changer Config",
                menu=pystray.Menu(
                    pystray.MenuItem("Show", on_show, default=True),
                    pystray.MenuItem("Quit", on_quit)
                )
            )

            icon.run()

        except ImportError:
            messagebox.showwarning(
                "Feature Not Available",
                "Minimize to tray requires 'pystray' module.\n\n"
                "Install it with: pip install pystray"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to minimize to tray: {e}")

    def _load_config(self) -> None:
        """Load current configuration from config.py"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Import config module directly to handle os.getenv() and other dynamic values
            import importlib.util
            spec = importlib.util.spec_from_file_location("config", self.config_path)
            if spec and spec.loader:
                config_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(config_module)

                # Get WeatherRotationSettings from the loaded module
                weather_settings = getattr(config_module, "WeatherRotationSettings", {})
                playlists = getattr(config_module, "Playlists", [])
            else:
                weather_settings = {}
                playlists = []

            # Parse basic settings (simplified parsing)
            self.config_data = {
                "Provider": self._extract_value(content, "Provider"),
                "ProvidersSequence": self._extract_list(content, "ProvidersSequence"),
                "RotateProviders": self._extract_value(content, "RotateProviders") == "True",
                "Query": self._extract_value(content, "Query"),
                "PurityLevel": self._extract_value(content, "PurityLevel"),
                "ScreenResolution": self._extract_value(content, "ScreenResolution"),
                "WallhavenSorting": self._extract_value(content, "WallhavenSorting"),
                "WallhavenTopRange": self._extract_value(content, "WallhavenTopRange"),
                "PexelsMode": self._extract_value(content, "PexelsMode"),
                "KeyBind": self._extract_value(content, "KeyBind"),
                "SchedulerEnabled": self._extract_dict_value(content, "SchedulerSettings", "enabled"),
                "SchedulerInterval": self._extract_dict_value(content, "SchedulerSettings", "interval_minutes"),
                "SchedulerJitter": self._extract_dict_value(content, "SchedulerSettings", "jitter_minutes"),
                "CacheMaxItems": self._extract_dict_value(content, "CacheSettings", "max_items"),
                "CacheOfflineRotation": self._extract_dict_value(content, "CacheSettings", "enable_offline_rotation"),
                "RedditSettings": self._extract_dict_literal(content, "RedditSettings"),
                "Monitors": self._extract_monitors(content),
                "DefaultPlaylist": self._extract_value(content, "DefaultPlaylist"),
                "Playlists": playlists,
                "WeatherRotationSettings": weather_settings,
            }
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config: {e}")

    def _extract_value(self, content: str, key: str) -> str:
        """Extract simple value from config content"""
        for line in content.split("\n"):
            if line.strip().startswith(f"{key} ="):
                value = line.split("=", 1)[1].strip()
                return value.strip('"\'')
        return ""

    def _extract_list(self, content: str, key: str) -> List[str]:
        """Extract list value from config content"""
        for line in content.split("\n"):
            if line.strip().startswith(f"{key} ="):
                value = line.split("=", 1)[1].strip()
                # Simple list parsing
                value = value.strip("[]").replace('"', '').replace("'", "")
                return [item.strip() for item in value.split(",") if item.strip()]
        return []

    def _extract_dict_value(self, content: str, dict_name: str, key: str) -> Any:
        """Extract value from dictionary in config"""
        in_dict = False
        for line in content.split("\n"):
            if f"{dict_name} = {{" in line or f"{dict_name} ={{" in line:
                in_dict = True
                continue
            if in_dict:
                if "}" in line and not line.strip().startswith('"'):
                    break
                if f'"{key}":' in line or f"'{key}':" in line:
                    value = line.split(":", 1)[1].strip().rstrip(",")
                    if value in ("True", "False"):
                        return value == "True"
                    try:
                        return int(value)
                    except ValueError:
                        return value.strip('"\'')
        return None

    def _extract_monitors(self, content: str) -> List[Dict]:
        """Extract Monitors list from config"""
        try:
            import re
            # Find the Monitors section
            monitors_match = re.search(r'Monitors\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if not monitors_match:
                return []

            monitors_str = monitors_match.group(1)
            monitors = []

            # Split by dictionary entries
            dict_pattern = r'\{([^}]+)\}'
            for dict_match in re.finditer(dict_pattern, monitors_str):
                dict_content = dict_match.group(1)
                monitor = {}

                # Extract key-value pairs
                for line in dict_content.split('\n'):
                    if ':' in line:
                        key_val = line.split(':', 1)
                        if len(key_val) == 2:
                            key = key_val[0].strip().strip('"\'')
                            val = key_val[1].strip().rstrip(',').strip('"\'')
                            monitor[key] = val

                if monitor:
                    monitors.append(monitor)

            return monitors
        except Exception as e:
            print(f"Error extracting monitors: {e}")
            return []

    def _extract_literal(self, content: str, name: str, default: Optional[Any] = None) -> Optional[Any]:
        """Extract a Python literal assigned to the given name using AST parsing."""
        try:
            module = ast.parse(content)
            for node in module.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == name:
                            return ast.literal_eval(node.value)
        except Exception as error:
            print(f"Unable to extract literal for {name}: {error}")
        return default

    def _extract_dict_literal(self, content: str, key: str) -> Dict[str, Any]:
        """Extract dictionary literal assigned to key using AST parsing."""
        try:
            tree = ast.parse(content)
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == key:
                            value = ast.literal_eval(node.value)
                            if isinstance(value, dict):
                                return value
        except Exception as exc:
            print(f"Error extracting {key}: {exc}")
        return {}

    def _create_widgets(self) -> None:
        """Create GUI widgets"""
        # Status bar at the top
        status_frame = tk.Frame(self.root, bg=self.COLORS['bg_secondary'], height=40)
        status_frame.pack(fill=tk.X, padx=0, pady=0)
        status_frame.pack_propagate(False)

        # Status indicator
        status_container = tk.Frame(status_frame, bg=self.COLORS['bg_secondary'])
        status_container.pack(side=tk.RIGHT, padx=15, pady=8)

        self.status_label = tk.Label(status_container,
                                     text="🟢 Service Running",
                                     bg=self.COLORS['bg_secondary'],
                                     fg=self.COLORS['success'],
                                     font=('Segoe UI', 9, 'bold'))
        self.status_label.pack(side=tk.LEFT, padx=5)

        # Start/Stop button
        self.service_btn = tk.Button(status_container,
                                     text="⚙️ Service",
                                     bg=self.COLORS['bg_tertiary'],
                                     fg=self.COLORS['text_primary'],
                                     font=('Segoe UI', 8, 'bold'),
                                     relief=tk.FLAT,
                                     cursor='hand2',
                                     padx=10,
                                     pady=4,
                                     command=self._toggle_service)
        self.service_btn.pack(side=tk.LEFT, padx=5)

        # App title on the left
        title_label = tk.Label(status_frame,
                              text="🎨 Wallpaper Changer Configuration",
                              bg=self.COLORS['bg_secondary'],
                              fg=self.COLORS['accent'],
                              font=('Segoe UI', 11, 'bold'))
        title_label.pack(side=tk.LEFT, padx=15, pady=8)

        # Start status update loop
        self._update_status_indicator()

        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        # Tab 1: Settings
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="⚙️ Settings")
        self._create_settings_tab()

        # Tab 2: Cache/Gallery
        self.cache_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.cache_frame, text="🖼️ Wallpaper Gallery")
        self._create_cache_tab()

        # Tab 3: Advanced Parameters
        self.advanced_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.advanced_frame, text="🔧 Advanced")
        self._create_advanced_tab()

        # Tab 4: Help & Features
        self.help_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.help_frame, text="📚 Help & Features")
        self._create_help_tab()

        # Tab 5: Logs
        self.logs_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.logs_frame, text="📋 Logs")
        self._create_logs_tab()

        # Bottom buttons
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(button_frame, text="💾 Save Configuration", command=self._save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🔄 Reload Config", command=self._reload_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="📥 Minimize to Tray", command=self._minimize_to_tray).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="❌ Close", command=self._on_closing).pack(side=tk.RIGHT, padx=5)

        # Handle window close button (X)
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_settings_tab(self) -> None:
        """Create settings tab content"""
        # Create canvas with scrollbar
        canvas = tk.Canvas(self.settings_frame, bg=self.COLORS['bg_primary'],
                          highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.settings_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Enable mouse wheel scrolling
        self._bind_mousewheel(canvas)

        # Provider Settings
        provider_group = ttk.LabelFrame(scrollable_frame, text="Provider Settings", padding=10)
        provider_group.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(provider_group, text="Default Provider:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.provider_var = tk.StringVar(value=self.config_data.get("Provider", "wallhaven"))
        ttk.Combobox(provider_group, textvariable=self.provider_var,
                     values=["wallhaven", "pexels", "reddit"], width=30).grid(row=0, column=1, pady=2)

        ttk.Label(provider_group, text="Search Query:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.query_var = tk.StringVar(value=self.config_data.get("Query", "nature"))
        ttk.Entry(provider_group, textvariable=self.query_var, width=33).grid(row=1, column=1, pady=2)

        self.rotate_providers_var = tk.BooleanVar(value=self.config_data.get("RotateProviders", True))
        ttk.Checkbutton(provider_group, text="Enable Provider Rotation",

                       variable=self.rotate_providers_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)

        reddit_settings = self.config_data.get("RedditSettings", {})
        subreddits_value = reddit_settings.get("subreddits", ["wallpapers"])
        if isinstance(subreddits_value, list):
            subreddits_text = ", ".join(subreddits_value)
        else:
            subreddits_text = str(subreddits_value or "wallpapers")
        self.reddit_subreddits_var = tk.StringVar(value=subreddits_text or "wallpapers")
        self.reddit_sort_var = tk.StringVar(value=str(reddit_settings.get("sort", "hot")))
        self.reddit_time_var = tk.StringVar(value=str(reddit_settings.get("time_filter", "day")))
        self.reddit_limit_var = tk.IntVar(value=int(reddit_settings.get("limit", 60) or 60))
        self.reddit_score_var = tk.IntVar(value=int(reddit_settings.get("min_score", 0) or 0))
        allow_nsfw = reddit_settings.get("allow_nsfw", False)
        if isinstance(allow_nsfw, str):
            allow_nsfw = allow_nsfw.strip().lower() in {"1", "true", "yes", "on"}
        self.reddit_nsfw_var = tk.BooleanVar(value=bool(allow_nsfw))
        self.reddit_user_agent_var = tk.StringVar(
            value=str(reddit_settings.get("user_agent", "WallpaperChanger/1.0 (by u/yourusername)"))
        )

        # Wallhaven Settings
        wallhaven_group = ttk.LabelFrame(scrollable_frame, text="Wallhaven Settings", padding=10)
        wallhaven_group.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(wallhaven_group, text="Purity Level:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.purity_var = tk.StringVar(value=self.config_data.get("PurityLevel", "100"))
        ttk.Combobox(wallhaven_group, textvariable=self.purity_var,
                     values=["100", "110", "111", "010", "001"], width=30).grid(row=0, column=1, pady=2)
        ttk.Label(wallhaven_group, text="(100=SFW, 110=SFW+Sketchy, 111=All)").grid(row=0, column=2, sticky=tk.W, padx=5)

        ttk.Label(wallhaven_group, text="Min Resolution:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.resolution_var = tk.StringVar(value=self.config_data.get("ScreenResolution", "1920x1080"))
        ttk.Combobox(wallhaven_group, textvariable=self.resolution_var,
                     values=["1920x1080", "2560x1440", "3440x1440", "3840x2160"],
                     width=30).grid(row=1, column=1, pady=2)

        ttk.Label(wallhaven_group, text="Sorting:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.sorting_var = tk.StringVar(value=self.config_data.get("WallhavenSorting", "toplist"))
        ttk.Combobox(wallhaven_group, textvariable=self.sorting_var,
                     values=["random", "toplist", "favorites", "views"], width=30).grid(row=2, column=1, pady=2)

        ttk.Label(wallhaven_group, text="Top Range:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.toprange_var = tk.StringVar(value=self.config_data.get("WallhavenTopRange", "1M"))
        ttk.Combobox(wallhaven_group, textvariable=self.toprange_var,
                     values=["1d", "3d", "1w", "1M", "3M", "6M", "1y"], width=30).grid(row=3, column=1, pady=2)

        # Pexels Settings
        pexels_group = ttk.LabelFrame(scrollable_frame, text="Pexels Settings", padding=10)
        pexels_group.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(pexels_group, text="Mode:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.pexels_mode_var = tk.StringVar(value=self.config_data.get("PexelsMode", "curated"))
        ttk.Combobox(pexels_group, textvariable=self.pexels_mode_var,
                     values=["search", "curated"], width=30).grid(row=0, column=1, pady=2)

        # Reddit Settings
        reddit_group = ttk.LabelFrame(scrollable_frame, text="Reddit Settings", padding=10)
        reddit_group.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(reddit_group, text="Subreddits (comma separated):").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(reddit_group, textvariable=self.reddit_subreddits_var, width=33).grid(row=0, column=1, pady=2)
        ttk.Label(reddit_group, text="(e.g., wallpapers, wallpaper)").grid(row=0, column=2, sticky=tk.W, padx=5)

        ttk.Label(reddit_group, text="Sort:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Combobox(reddit_group, textvariable=self.reddit_sort_var,
                     values=["hot", "new", "rising", "top", "controversial"],
                     width=30, state="readonly").grid(row=1, column=1, pady=2)

        ttk.Label(reddit_group, text="Time Filter:").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Combobox(reddit_group, textvariable=self.reddit_time_var,
                     values=["hour", "day", "week", "month", "year", "all"],
                     width=30, state="readonly").grid(row=2, column=1, pady=2)
        ttk.Label(reddit_group, text="(Used for Top/Controversial)").grid(row=2, column=2, sticky=tk.W, padx=5)

        ttk.Label(reddit_group, text="Posts per fetch:").grid(row=3, column=0, sticky=tk.W, pady=2)
        ttk.Spinbox(reddit_group, from_=10, to=100, textvariable=self.reddit_limit_var, width=31).grid(row=3, column=1, pady=2)

        ttk.Label(reddit_group, text="Minimum upvotes:").grid(row=4, column=0, sticky=tk.W, pady=2)
        ttk.Spinbox(reddit_group, from_=0, to=100000, increment=10, textvariable=self.reddit_score_var,
                    width=31).grid(row=4, column=1, pady=2)

        ttk.Checkbutton(reddit_group, text="Include NSFW posts",
                        variable=self.reddit_nsfw_var).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=2)

        ttk.Label(reddit_group, text="User Agent:").grid(row=6, column=0, sticky=tk.W, pady=2)
        ttk.Entry(reddit_group, textvariable=self.reddit_user_agent_var, width=50).grid(row=6, column=1, columnspan=2, pady=2, sticky=tk.W)

        ttk.Label(reddit_group,
                  text="Reddit requires a descriptive user-agent; consider using your Reddit username.",
                  foreground="gray").grid(row=7, column=0, columnspan=3, sticky=tk.W, pady=(2, 0))

        # Scheduler Settings
        scheduler_group = ttk.LabelFrame(scrollable_frame, text="Scheduler Settings", padding=10)
        scheduler_group.pack(fill=tk.X, padx=10, pady=5)

        self.scheduler_enabled_var = tk.BooleanVar(value=self.config_data.get("SchedulerEnabled", True))
        ttk.Checkbutton(scheduler_group, text="Enable Scheduler",
                       variable=self.scheduler_enabled_var).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)

        ttk.Label(scheduler_group, text="Interval (minutes):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.interval_var = tk.IntVar(value=self.config_data.get("SchedulerInterval", 45))
        ttk.Spinbox(scheduler_group, from_=1, to=1440, textvariable=self.interval_var, width=31).grid(row=1, column=1, pady=2)

        ttk.Label(scheduler_group, text="Jitter (minutes):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.jitter_var = tk.IntVar(value=self.config_data.get("SchedulerJitter", 10))
        ttk.Spinbox(scheduler_group, from_=0, to=60, textvariable=self.jitter_var, width=31).grid(row=2, column=1, pady=2)

        # Cache Settings
        cache_group = ttk.LabelFrame(scrollable_frame, text="Cache Settings", padding=10)
        cache_group.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(cache_group, text="Max Cache Items:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.cache_max_var = tk.IntVar(value=self.config_data.get("CacheMaxItems", 60))
        ttk.Spinbox(cache_group, from_=10, to=500, textvariable=self.cache_max_var, width=31).grid(row=0, column=1, pady=2)

        self.cache_offline_var = tk.BooleanVar(value=self.config_data.get("CacheOfflineRotation", True))
        ttk.Checkbutton(cache_group, text="Enable Offline Rotation",
                       variable=self.cache_offline_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)

        # Monitor Resolution Settings
        monitors_group = ttk.LabelFrame(scrollable_frame, text="🖥️ Monitor Resolution Settings", padding=10)
        monitors_group.pack(fill=tk.X, padx=10, pady=5)

        # Detect active monitors
        from main import enumerate_monitors_user32, DesktopWallpaperController

        monitors = []
        try:
            manager = DesktopWallpaperController()
            monitors = manager.enumerate_monitors()
            manager.close()
        except Exception:
            try:
                monitors = enumerate_monitors_user32()
            except Exception:
                pass

        if not monitors:
            ttk.Label(monitors_group, text="No monitors detected. Connect monitors and restart the app.",
                     foreground="gray").grid(row=0, column=0, columnspan=3, pady=5)
        else:
            ttk.Label(monitors_group,
                     text="Set minimum resolution for each active monitor:",
                     font=('Segoe UI', 9, 'bold')).grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))

            self.monitor_resolution_vars = {}

            # Load monitor settings from config
            monitors_config = self.config_data.get("Monitors", [])

            for idx, monitor in enumerate(monitors):
                current_res = f"{monitor.get('width')}x{monitor.get('height')}"
                monitor_name = f"Monitor {idx + 1}"

                # Try to get saved resolution from config
                saved_res = current_res
                if idx < len(monitors_config):
                    saved_res = monitors_config[idx].get("screen_resolution", current_res)

                # Label
                ttk.Label(monitors_group,
                         text=f"{monitor_name} (Current: {current_res}):").grid(row=idx+1, column=0, sticky=tk.W, pady=3, padx=5)

                # Resolution dropdown
                res_var = tk.StringVar(value=saved_res)
                self.monitor_resolution_vars[idx] = res_var

                res_combo = ttk.Combobox(monitors_group, textvariable=res_var,
                                        values=["1920x1080", "2560x1440", "3440x1440", "3840x2160", "5120x1440", current_res],
                                        width=20)
                res_combo.grid(row=idx+1, column=1, pady=3, padx=5)

                # Info label
                ttk.Label(monitors_group,
                         text="(Min resolution for wallpapers)",
                         foreground="gray",
                         font=('Segoe UI', 8)).grid(row=idx+1, column=2, sticky=tk.W, pady=3, padx=5)

        # Hotkey Settings
        hotkey_group = ttk.LabelFrame(scrollable_frame, text="Hotkey Settings", padding=10)
        hotkey_group.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(hotkey_group, text="Hotkey:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.keybind_var = tk.StringVar(value=self.config_data.get("KeyBind", "ctrl+alt+w"))
        ttk.Entry(hotkey_group, textvariable=self.keybind_var, width=33).grid(row=0, column=1, pady=2)
        ttk.Label(hotkey_group, text="(e.g., ctrl+alt+w)").grid(row=0, column=2, sticky=tk.W, padx=5)

    def _create_cache_tab(self) -> None:
        """Create cache/gallery tab content"""
        # Prominent "Change Wallpaper Now" button with provider info
        change_wallpaper_frame = tk.Frame(self.cache_frame, bg=self.COLORS['bg_primary'])
        change_wallpaper_frame.pack(fill=tk.X, padx=15, pady=15)

        # Top row: Main change button
        change_btn = tk.Button(change_wallpaper_frame,
                              text="🎨 CHANGE WALLPAPER NOW",
                              bg=self.COLORS['accent'],
                              fg='#1e1e2e',
                              font=('Segoe UI', 12, 'bold'),
                              relief=tk.FLAT,
                              cursor='hand2',
                              padx=30,
                              pady=15,
                              command=self._change_wallpaper_now)
        change_btn.pack(fill=tk.X)

        # Provider rotation controls
        provider_frame = tk.Frame(change_wallpaper_frame, bg=self.COLORS['bg_secondary'])
        provider_frame.pack(fill=tk.X, pady=(10, 0))

        # Provider info label
        self.provider_info_label = tk.Label(provider_frame,
                                           text="Loading provider info...",
                                           bg=self.COLORS['bg_secondary'],
                                           fg=self.COLORS['text_primary'],
                                           font=('Segoe UI', 9))
        self.provider_info_label.pack(side=tk.LEFT, padx=10, pady=8)

        # Cycle provider button
        cycle_btn = tk.Button(provider_frame,
                             text="🔄 Cycle to Next Provider",
                             bg=self.COLORS['bg_tertiary'],
                             fg=self.COLORS['text_primary'],
                             font=('Segoe UI', 9),
                             relief=tk.FLAT,
                             cursor='hand2',
                             padx=15,
                             pady=5,
                             command=self._cycle_provider)
        cycle_btn.pack(side=tk.LEFT, padx=5)

        # Reset rotation button
        reset_btn = tk.Button(provider_frame,
                             text="↺ Reset Rotation",
                             bg=self.COLORS['bg_tertiary'],
                             fg=self.COLORS['warning'],
                             font=('Segoe UI', 9),
                             relief=tk.FLAT,
                             cursor='hand2',
                             padx=15,
                             pady=5,
                             command=self._reset_provider_rotation)
        reset_btn.pack(side=tk.LEFT, padx=5)

        # Update provider info after initialization
        self.root.after(500, self._update_provider_info)

        # Button hover effect
        def btn_enter(e):
            change_btn.configure(bg=self.COLORS['accent_hover'])

        def btn_leave(e):
            change_btn.configure(bg=self.COLORS['accent'])

        change_btn.bind("<Enter>", btn_enter)
        change_btn.bind("<Leave>", btn_leave)

        # Top controls - Row 1: Filters and Sort
        control_frame1 = ttk.Frame(self.cache_frame)
        control_frame1.pack(fill=tk.X, padx=10, pady=(5, 2))

        ttk.Label(control_frame1, text="🔍 Filter by Resolution:").pack(side=tk.LEFT, padx=5)
        filter_combo = ttk.Combobox(control_frame1, textvariable=self.filter_resolution,
                                    values=["All", "1920x1080+", "2560x1440+", "3440x1440+", "3840x2160+"],
                                    width=15, state="readonly")
        filter_combo.pack(side=tk.LEFT, padx=5)
        filter_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())

        ttk.Label(control_frame1, text="📊 Sort by:").pack(side=tk.LEFT, padx=(15, 5))
        sort_combo = ttk.Combobox(control_frame1, textvariable=self.sort_by,
                                  values=["Newest First", "Oldest First", "Highest Resolution", "Lowest Resolution"],
                                  width=18, state="readonly")
        sort_combo.pack(side=tk.LEFT, padx=5)
        sort_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())

        # Row 2: Actions
        control_frame2 = ttk.Frame(self.cache_frame)
        control_frame2.pack(fill=tk.X, padx=10, pady=(2, 5))

        ttk.Label(control_frame2, text="Select Monitor:").pack(side=tk.LEFT, padx=5)
        self.monitor_var = tk.StringVar(value="All Monitors")
        self.monitor_combo = ttk.Combobox(control_frame2, textvariable=self.monitor_var, width=30)
        self.monitor_combo.pack(side=tk.LEFT, padx=5)

        ttk.Button(control_frame2, text="🔄 Refresh Gallery", command=self._refresh_gallery).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame2, text="🗑️ Clear Cache", command=self._clear_cache).pack(side=tk.LEFT, padx=5)

        # Create canvas with scrollbar for gallery
        gallery_container = ttk.Frame(self.cache_frame)
        gallery_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.gallery_canvas = tk.Canvas(gallery_container, bg=self.COLORS['bg_primary'],
                                        highlightthickness=0)
        gallery_scrollbar = ttk.Scrollbar(gallery_container, orient="vertical", command=self.gallery_canvas.yview)
        self.gallery_frame = ttk.Frame(self.gallery_canvas)

        self.gallery_frame.bind(
            "<Configure>",
            lambda e: self.gallery_canvas.configure(scrollregion=self.gallery_canvas.bbox("all"))
        )

        self.gallery_canvas.create_window((0, 0), window=self.gallery_frame, anchor="nw")
        self.gallery_canvas.configure(yscrollcommand=gallery_scrollbar.set)

        self.gallery_canvas.pack(side="left", fill="both", expand=True)
        gallery_scrollbar.pack(side="right", fill="y")

        # Enable mouse wheel scrolling
        self._bind_mousewheel(self.gallery_canvas)

        # Bind window resize to re-layout thumbnails
        self.gallery_canvas.bind("<Configure>", self._on_gallery_resize)

        # Load monitors
        self._load_monitors()

        # Load gallery
        self._refresh_gallery()

    def _create_advanced_tab(self) -> None:
        """Create advanced parameters tab content"""
        # Create canvas with scrollbar
        canvas = tk.Canvas(self.advanced_frame, bg=self.COLORS['bg_primary'],
                          highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.advanced_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Enable mouse wheel scrolling
        self._bind_mousewheel(canvas)

        # API Keys Section
        api_group = ttk.LabelFrame(scrollable_frame, text="API Keys Configuration", padding=10)
        api_group.pack(fill=tk.X, padx=10, pady=5)

        # Load current API keys from .env
        env_path = Path(__file__).parent / '.env'
        current_wallhaven_key = ""
        current_pexels_key = ""
        current_openweather_key = ""

        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('WALLHAVEN_API_KEY='):
                        current_wallhaven_key = line.split('=', 1)[1].strip()
                    elif line.startswith('PEXELS_API_KEY='):
                        current_pexels_key = line.split('=', 1)[1].strip()
                    elif line.startswith('OPENWEATHER_API_KEY='):
                        current_openweather_key = line.split('=', 1)[1].strip()

        ttk.Label(api_group, text="Wallhaven API Key:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.wallhaven_key_var = tk.StringVar(value=current_wallhaven_key)
        wallhaven_entry = ttk.Entry(api_group, textvariable=self.wallhaven_key_var, width=50, show="*")
        wallhaven_entry.grid(row=0, column=1, pady=5, padx=5)
        ttk.Button(api_group, text="👁", width=3,
                  command=lambda: self._toggle_password_visibility(wallhaven_entry)).grid(row=0, column=2, padx=2)

        ttk.Label(api_group, text="Pexels API Key:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.pexels_key_var = tk.StringVar(value=current_pexels_key)
        pexels_entry = ttk.Entry(api_group, textvariable=self.pexels_key_var, width=50, show="*")
        pexels_entry.grid(row=1, column=1, pady=5, padx=5)
        ttk.Button(api_group, text="👁", width=3,
                  command=lambda: self._toggle_password_visibility(pexels_entry)).grid(row=1, column=2, padx=2)

        ttk.Label(api_group, text="OpenWeatherMap API Key:").grid(row=2, column=0, sticky=tk.W, pady=5, padx=5)
        self.weather_api_key_var = tk.StringVar(value=current_openweather_key)
        openweather_entry = ttk.Entry(api_group, textvariable=self.weather_api_key_var, width=50, show="*")
        openweather_entry.grid(row=2, column=1, pady=5, padx=5)
        ttk.Button(api_group, text="👁", width=3,
                  command=lambda: self._toggle_password_visibility(openweather_entry)).grid(row=2, column=2, padx=2)

        # Info label for OpenWeather
        ttk.Label(api_group, text="🌤️ Free tier: 1000 calls/day · Get it at: https://home.openweathermap.org/api_keys",
                 foreground=self.COLORS['text_muted'], font=('Segoe UI', 8)).grid(row=3, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(0, 5))

        ttk.Button(api_group, text="💾 Save API Keys", command=self._save_api_keys).grid(row=4, column=1, pady=10, sticky=tk.E)

        # Folders Configuration Section
        folders_group = ttk.LabelFrame(scrollable_frame, text="Folders Configuration", padding=10)
        folders_group.pack(fill=tk.X, padx=10, pady=5)

        cache_dir = CacheSettings.get("directory") or os.path.join(os.path.expanduser("~"), "WallpaperChangerCache")

        ttk.Label(folders_group, text="Cache Directory:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.cache_dir_var = tk.StringVar(value=cache_dir)
        ttk.Entry(folders_group, textvariable=self.cache_dir_var, width=50).grid(row=0, column=1, pady=5, padx=5)
        ttk.Button(folders_group, text="📁 Browse",
                  command=lambda: self._browse_directory(self.cache_dir_var)).grid(row=0, column=2, padx=2)
        ttk.Button(folders_group, text="📂 Open",
                  command=lambda: os.startfile(self.cache_dir_var.get()) if os.path.exists(self.cache_dir_var.get()) else None).grid(row=0, column=3, padx=2)

        # Advanced Scheduler Section
        scheduler_group = ttk.LabelFrame(scrollable_frame, text="Advanced Scheduler Settings", padding=10)
        scheduler_group.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(scheduler_group, text="Initial Delay (minutes):").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.initial_delay_var = tk.IntVar(value=self._extract_dict_value(self._get_config_content(),
                                                                           "SchedulerSettings", "initial_delay_minutes") or 1)
        ttk.Spinbox(scheduler_group, from_=0, to=60, textvariable=self.initial_delay_var, width=15).grid(row=0, column=1, pady=5, padx=5, sticky=tk.W)

        ttk.Label(scheduler_group, text="Quiet Hours:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        quiet_hours_frame = ttk.Frame(scheduler_group)
        quiet_hours_frame.grid(row=1, column=1, columnspan=2, pady=5, sticky=tk.W)

        ttk.Label(quiet_hours_frame, text="Start:").pack(side=tk.LEFT, padx=2)
        self.quiet_start_var = tk.StringVar(value="23:30")
        ttk.Entry(quiet_hours_frame, textvariable=self.quiet_start_var, width=8).pack(side=tk.LEFT, padx=2)

        ttk.Label(quiet_hours_frame, text="End:").pack(side=tk.LEFT, padx=5)
        self.quiet_end_var = tk.StringVar(value="07:00")
        ttk.Entry(quiet_hours_frame, textvariable=self.quiet_end_var, width=8).pack(side=tk.LEFT, padx=2)

        ttk.Label(scheduler_group, text="Active Days:").grid(row=2, column=0, sticky=tk.W, pady=5, padx=5)
        days_frame = ttk.Frame(scheduler_group)
        days_frame.grid(row=2, column=1, columnspan=2, pady=5, sticky=tk.W)

        self.days_vars = {}
        days = [("Mon", "mon"), ("Tue", "tue"), ("Wed", "wed"), ("Thu", "thu"),
                ("Fri", "fri"), ("Sat", "sat"), ("Sun", "sun")]
        for idx, (label, value) in enumerate(days):
            var = tk.BooleanVar(value=True)
            self.days_vars[value] = var
            ttk.Checkbutton(days_frame, text=label, variable=var).grid(row=0, column=idx, padx=2)

        # Default Preset Section
        preset_group = ttk.LabelFrame(scrollable_frame, text="Default Preset", padding=10)
        preset_group.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(preset_group, text="Default Preset at Startup:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)

        try:
            from preset_manager import PresetManager
            preset_mgr = PresetManager()
            preset_names = [p.name for p in preset_mgr.list_presets()]
            default_preset = self._extract_value(self._get_config_content(), "DefaultPreset") or "workspace"
        except:
            preset_names = ["workspace", "relax"]
            default_preset = "workspace"

        self.default_preset_var = tk.StringVar(value=default_preset)
        ttk.Combobox(preset_group, textvariable=self.default_preset_var,
                    values=preset_names, width=30).grid(row=0, column=1, pady=5, padx=5, sticky=tk.W)

        # Playlist & Thematic Rotation Section
        playlist_group = ttk.LabelFrame(scrollable_frame, text="Playlists & Thematic Rotation", padding=10)
        playlist_group.pack(fill=tk.X, padx=10, pady=5)

        raw_default_playlist = (self.config_data.get("DefaultPlaylist") or "").strip()
        seen_playlist_names = set()
        playlist_names: List[str] = []
        for item in self.playlists_data:
            if isinstance(item, dict):
                name = str(item.get("name", "")).strip()
                if name and name not in seen_playlist_names:
                    playlist_names.append(name)
                    seen_playlist_names.add(name)
        playlist_choices = ["(None)"] + playlist_names
        default_playlist_display = raw_default_playlist if raw_default_playlist in playlist_names else "(None)"
        self.default_playlist_display_var = tk.StringVar(value=default_playlist_display)

        ttk.Label(playlist_group, text="Default Playlist at Startup:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.default_playlist_combo = ttk.Combobox(
            playlist_group,
            textvariable=self.default_playlist_display_var,
            values=playlist_choices,
            width=30,
            state="readonly",
        )
        self.default_playlist_combo.grid(row=0, column=1, pady=5, padx=5, sticky=tk.W)

        if playlist_names:
            summary_lines = [f"- {name}" for name in playlist_names]
            summary_text = "\n".join(summary_lines)
        else:
            summary_text = "No playlists defined yet."
        self.playlist_summary_label = ttk.Label(
            playlist_group,
            text=summary_text,
            justify=tk.LEFT,
            foreground=self.COLORS['text_secondary'],
        )
        self.playlist_summary_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 5), padx=5)

        ttk.Button(
            playlist_group,
            text="Edit Playlist Definitions",
            command=self._focus_playlists_editor,
        ).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5, padx=5)

        # Weather Rotation Section
        weather_group = ttk.LabelFrame(scrollable_frame, text="Weather-Based Rotation", padding=10)
        weather_group.pack(fill=tk.X, padx=10, pady=5)

        weather_location = self.weather_settings.get("location", {}) if isinstance(self.weather_settings, dict) else {}
        weather_apply_on = self.weather_settings.get("apply_on", []) if isinstance(self.weather_settings, dict) else []

        self.weather_enabled_var = tk.BooleanVar(value=bool(self.weather_settings.get("enabled", False)))
        self.weather_provider_var = tk.StringVar(value=str(self.weather_settings.get("provider", "openweathermap") or "openweathermap"))
        # weather_api_key_var already initialized in API Keys section above - use .env value if available, otherwise config
        if not self.weather_api_key_var.get() and self.weather_settings.get("api_key"):
            self.weather_api_key_var.set(str(self.weather_settings.get("api_key", "") or ""))
        self.weather_refresh_var = tk.IntVar(value=int(self.weather_settings.get("refresh_minutes", 30) or 30))
        self.weather_units_var = tk.StringVar(value=str(self.weather_settings.get("units", "metric") or "metric"))
        self.weather_city_var = tk.StringVar(value=str(weather_location.get("city", "") or ""))
        self.weather_country_var = tk.StringVar(value=str(weather_location.get("country", "") or ""))
        self.weather_lat_var = tk.StringVar(value=str(weather_location.get("latitude", "") or ""))
        self.weather_lon_var = tk.StringVar(value=str(weather_location.get("longitude", "") or ""))

        # Info banner at top
        info_banner = tk.Frame(weather_group, bg=self.COLORS['bg_tertiary'], relief=tk.FLAT, pady=8, padx=10)
        info_banner.grid(row=0, column=0, columnspan=3, sticky=tk.EW, pady=(0, 10))

        tk.Label(info_banner,
                text="🌤️ OpenWeatherMap è GRATUITO fino a 1000 chiamate/giorno (più che sufficiente!)",
                bg=self.COLORS['bg_tertiary'],
                fg=self.COLORS['success'],
                font=('Segoe UI', 9, 'bold')).pack(anchor=tk.W)

        tk.Label(info_banner,
                text="⏰ IMPORTANTE: Le nuove API key possono impiegare fino a 2 ore per attivarsi!",
                bg=self.COLORS['bg_tertiary'],
                fg=self.COLORS['warning'],
                font=('Segoe UI', 8, 'bold')).pack(anchor=tk.W, pady=(3, 0))

        tk.Label(info_banner,
                text="Ottieni la tua API key gratuita qui:",
                bg=self.COLORS['bg_tertiary'],
                fg=self.COLORS['text_secondary'],
                font=('Segoe UI', 8)).pack(anchor=tk.W, pady=(3, 0))

        link_frame = tk.Frame(info_banner, bg=self.COLORS['bg_tertiary'])
        link_frame.pack(anchor=tk.W)

        tk.Label(link_frame,
                text="https://home.openweathermap.org/api_keys",
                bg=self.COLORS['bg_tertiary'],
                fg=self.COLORS['accent'],
                font=('Segoe UI', 8, 'underline'),
                cursor='hand2').pack(side=tk.LEFT)

        def open_weather_link(event):
            import webbrowser
            webbrowser.open("https://home.openweathermap.org/api_keys")

        link_frame.winfo_children()[0].bind("<Button-1>", open_weather_link)

        ttk.Checkbutton(
            weather_group,
            text="Enable weather-based wallpaper rotation",
            variable=self.weather_enabled_var,
        ).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5, padx=5)

        ttk.Label(weather_group, text="API Key:").grid(row=2, column=0, sticky=tk.W, pady=5, padx=5)
        api_entry = ttk.Entry(weather_group, textvariable=self.weather_api_key_var, width=32, show="*")
        api_entry.grid(row=2, column=1, pady=5, padx=5, sticky=tk.W)
        ttk.Button(weather_group, text="👁", width=3,
                  command=lambda: self._toggle_password_visibility(api_entry)).grid(row=2, column=2, padx=2)

        # Test button - prominent and colorful
        test_btn_frame = tk.Frame(weather_group, bg=self.COLORS['bg_secondary'])
        test_btn_frame.grid(row=3, column=0, columnspan=3, pady=10, padx=5, sticky=tk.EW)

        self.test_weather_btn = tk.Button(test_btn_frame,
                              text="🧪 TEST WEATHER CONNECTION",
                              bg=self.COLORS['warning'],
                              fg='#1e1e2e',
                              font=('Segoe UI', 10, 'bold'),
                              relief=tk.FLAT,
                              cursor='hand2',
                              padx=20,
                              pady=10,
                              command=self._test_weather_connection)
        self.test_weather_btn.pack(fill=tk.X)

        # Weather status label
        self.weather_status_label = tk.Label(test_btn_frame,
                                            text="",
                                            bg=self.COLORS['bg_secondary'],
                                            fg=self.COLORS['text_primary'],
                                            font=('Segoe UI', 9),
                                            wraplength=600,
                                            justify=tk.LEFT)
        self.weather_status_label.pack(pady=(5, 0))

        ttk.Label(weather_group, text="Location (City):").grid(row=4, column=0, sticky=tk.W, pady=5, padx=5)
        location_quick = ttk.Frame(weather_group)
        location_quick.grid(row=4, column=1, columnspan=2, sticky=tk.W, pady=5, padx=5)
        ttk.Entry(location_quick, textvariable=self.weather_city_var, width=18).pack(side=tk.LEFT)
        ttk.Label(location_quick, text="Country:").pack(side=tk.LEFT, padx=(10, 2))
        ttk.Entry(location_quick, textvariable=self.weather_country_var, width=8).pack(side=tk.LEFT)

        ttk.Label(weather_group, text="Refresh interval (minutes):").grid(row=5, column=0, sticky=tk.W, pady=5, padx=5)
        ttk.Spinbox(weather_group, from_=5, to=180, increment=5, textvariable=self.weather_refresh_var, width=10).grid(row=5, column=1, pady=5, padx=5, sticky=tk.W)

        ttk.Label(weather_group, text="Units:").grid(row=6, column=0, sticky=tk.W, pady=5, padx=5)
        ttk.Combobox(
            weather_group,
            textvariable=self.weather_units_var,
            values=["metric", "imperial", "standard"],
            state="readonly",
            width=15,
        ).grid(row=6, column=1, pady=5, padx=5, sticky=tk.W)

        # Advanced location (optional - latitude/longitude)
        ttk.Label(weather_group, text="Advanced location (optional):").grid(row=7, column=0, sticky=tk.W, pady=(10, 2), padx=5)
        advanced_loc = ttk.Frame(weather_group)
        advanced_loc.grid(row=7, column=1, columnspan=2, sticky=tk.W, pady=(10, 2), padx=5)
        ttk.Label(advanced_loc, text="Lat:").pack(side=tk.LEFT)
        ttk.Entry(advanced_loc, textvariable=self.weather_lat_var, width=12).pack(side=tk.LEFT, padx=(2, 8))
        ttk.Label(advanced_loc, text="Lon:").pack(side=tk.LEFT)
        ttk.Entry(advanced_loc, textvariable=self.weather_lon_var, width=12).pack(side=tk.LEFT, padx=2)

        ttk.Label(weather_group, text="Apply on triggers:").grid(row=8, column=0, sticky=tk.W, pady=5, padx=5)
        triggers_frame = ttk.Frame(weather_group)
        triggers_frame.grid(row=8, column=1, columnspan=2, sticky=tk.W, pady=5, padx=5)

        self.weather_apply_on_vars: Dict[str, tk.BooleanVar] = {}
        trigger_options = ["startup", "scheduler", "hotkey", "tray", "gui"]
        for idx, trigger in enumerate(trigger_options):
            var = tk.BooleanVar(value=trigger in weather_apply_on)
            self.weather_apply_on_vars[trigger] = var
            ttk.Checkbutton(triggers_frame, text=trigger.title(), variable=var).grid(row=0, column=idx, padx=4, sticky=tk.W)

        # Simple preset/playlist selection for weather
        ttk.Label(weather_group, text="When weather changes, use:").grid(row=9, column=0, sticky=tk.W, pady=(10, 5), padx=5)
        weather_mode_frame = ttk.Frame(weather_group)
        weather_mode_frame.grid(row=9, column=1, columnspan=2, sticky=tk.W, pady=(10, 5), padx=5)

        self.weather_simple_mode_var = tk.StringVar(value="disabled")
        ttk.Radiobutton(weather_mode_frame, text="Disabled (manual config)", variable=self.weather_simple_mode_var, value="disabled").pack(anchor=tk.W)
        ttk.Radiobutton(weather_mode_frame, text="Simple mode (coming soon)", variable=self.weather_simple_mode_var, value="simple", state=tk.DISABLED).pack(anchor=tk.W)

        ttk.Label(
            weather_group,
            text="💡 For advanced weather→preset mapping, edit the Weather Conditions section below",
            foreground=self.COLORS['text_muted'],
            justify=tk.LEFT,
            font=('Segoe UI', 8),
        ).grid(row=10, column=0, columnspan=3, sticky=tk.W, pady=(5, 0), padx=5)

        # Playlist Definitions Editor
        playlists_editor_group = ttk.LabelFrame(scrollable_frame, text="Playlist Definitions (Advanced)", padding=10)
        playlists_editor_group.pack(fill=tk.BOTH, padx=10, pady=5, expand=True)

        ttk.Label(
            playlists_editor_group,
            text="Use Python syntax (lists/dicts) to customise thematic playlists.",
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=5, pady=(0, 5))

        self.playlists_text = scrolledtext.ScrolledText(
            playlists_editor_group,
            height=12,
            wrap=tk.WORD,
            font=('Consolas', 10),
        )
        self.playlists_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.playlists_text.insert('1.0', self._format_python_literal(self.playlists_data or []))

        playlist_controls = ttk.Frame(playlists_editor_group)
        playlist_controls.pack(anchor=tk.E, padx=5, pady=(0, 5))
        ttk.Button(playlist_controls, text="Format", command=self._format_playlists_text).pack(side=tk.LEFT, padx=3)
        ttk.Button(playlist_controls, text="Reset", command=self._reset_playlists_text).pack(side=tk.LEFT, padx=3)

        # Weather Conditions Editor
        weather_editor_group = ttk.LabelFrame(scrollable_frame, text="Weather Conditions Mapping", padding=10)
        weather_editor_group.pack(fill=tk.BOTH, padx=10, pady=5, expand=True)

        ttk.Label(
            weather_editor_group,
            text="Map weather conditions to playlists or presets (Python dict).",
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=5, pady=(0, 5))

        self.weather_conditions_text = scrolledtext.ScrolledText(
            weather_editor_group,
            height=10,
            wrap=tk.WORD,
            font=('Consolas', 10),
        )
        self.weather_conditions_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.weather_conditions_text.insert('1.0', self._format_python_literal((self.weather_settings.get('conditions') if isinstance(self.weather_settings, dict) else {}) or {}))

        weather_controls = ttk.Frame(weather_editor_group)
        weather_controls.pack(anchor=tk.E, padx=5, pady=(0, 5))
        ttk.Button(weather_controls, text="Format", command=self._format_weather_conditions_text).pack(side=tk.LEFT, padx=3)
        ttk.Button(weather_controls, text="Reset", command=self._reset_weather_conditions_text).pack(side=tk.LEFT, padx=3)

        # Info Section
        info_group = ttk.LabelFrame(scrollable_frame, text="ℹ️ Information", padding=10)
        info_group.pack(fill=tk.X, padx=10, pady=5)

        info_text = (
            "• API Keys are stored securely in the .env file\n"
            "• Cache directory stores downloaded wallpapers\n"
            "• Quiet hours prevent wallpaper changes during specified times\n"
            "• Active days control which days the scheduler runs\n"
            "• All changes require clicking 'Save Configuration' at the bottom"
        )
        ttk.Label(info_group, text=info_text, font=("Arial", 9), justify=tk.LEFT).pack(anchor=tk.W, padx=5, pady=5)

    def _create_help_tab(self) -> None:
        """Create help tab with detailed explanations of features"""
        # Create canvas with scrollbar
        canvas = tk.Canvas(self.help_frame, bg=self.COLORS['bg_primary'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.help_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Enable mouse wheel scrolling
        self._bind_mousewheel(canvas)

        # Header
        header_frame = tk.Frame(scrollable_frame, bg=self.COLORS['bg_secondary'], pady=15)
        header_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(header_frame,
                text="📚 Advanced Features Guide",
                bg=self.COLORS['bg_secondary'],
                fg=self.COLORS['accent'],
                font=('Segoe UI', 16, 'bold')).pack()

        tk.Label(header_frame,
                text="Learn how to use Weather Rotation and Playlists to create dynamic wallpaper experiences",
                bg=self.COLORS['bg_secondary'],
                fg=self.COLORS['text_secondary'],
                font=('Segoe UI', 10)).pack(pady=(5, 0))

        # Weather Rotation Section
        weather_group = ttk.LabelFrame(scrollable_frame, text="🌤️ Weather-Based Rotation", padding=15)
        weather_group.pack(fill=tk.X, padx=10, pady=10)

        weather_intro = tk.Text(weather_group, wrap=tk.WORD, height=4, bg=self.COLORS['bg_tertiary'],
                               fg=self.COLORS['text_primary'], font=('Segoe UI', 9), relief=tk.FLAT, padx=10, pady=10)
        weather_intro.insert("1.0",
            "Weather Rotation permette di cambiare automaticamente il wallpaper in base alle condizioni meteo della tua posizione. "
            "Puoi mappare diverse condizioni meteo (sole, pioggia, neve, ecc.) a preset o playlist specifici, creando "
            "un'esperienza visiva che si adatta all'ambiente esterno.")
        weather_intro.config(state=tk.DISABLED)
        weather_intro.pack(fill=tk.X, pady=(0, 10))

        # How to setup
        setup_label = tk.Label(weather_group, text="⚙️ Come Configurare:",
                              bg=self.COLORS['bg_secondary'], fg=self.COLORS['accent'],
                              font=('Segoe UI', 11, 'bold'))
        setup_label.pack(anchor=tk.W, pady=(10, 5))

        setup_steps = [
            "1. Ottieni un API key gratuita da OpenWeatherMap (https://openweathermap.org/api)",
            "2. Aggiungi la key nel file .env come OPENWEATHER_API_KEY=your_key_here",
            "3. Nel tab 'Advanced', configura la sezione Weather Rotation:",
            "   • Abilita Weather Rotation",
            "   • Imposta la tua posizione (città o coordinate)",
            "   • Scegli quando applicare la rotazione (startup, scheduler, hotkey)",
            "   • Imposta l'intervallo di refresh (es. 30 minuti)",
            "4. Configura le mappature meteo → preset/playlist nella sezione 'Weather Mapping'"
        ]

        for step in setup_steps:
            step_label = tk.Label(weather_group, text=step,
                                 bg=self.COLORS['bg_secondary'], fg=self.COLORS['text_primary'],
                                 font=('Segoe UI', 9), justify=tk.LEFT)
            step_label.pack(anchor=tk.W, padx=20, pady=2)

        # Weather conditions example
        conditions_label = tk.Label(weather_group, text="☁️ Condizioni Supportate:",
                                   bg=self.COLORS['bg_secondary'], fg=self.COLORS['accent'],
                                   font=('Segoe UI', 11, 'bold'))
        conditions_label.pack(anchor=tk.W, pady=(15, 5))

        conditions_text = tk.Text(weather_group, wrap=tk.WORD, height=8, bg=self.COLORS['bg_tertiary'],
                                 fg=self.COLORS['text_primary'], font=('Consolas', 9), relief=tk.FLAT, padx=10, pady=10)
        conditions_text.insert("1.0",
            "• clear          → Cielo sereno\n"
            "• clouds         → Nuvoloso\n"
            "• rain           → Pioggia\n"
            "• drizzle        → Pioggerella\n"
            "• snow           → Neve\n"
            "• thunderstorm   → Temporale\n"
            "• mist/fog       → Nebbia\n"
            "• storm          → Tempesta\n"
            "• night_clear    → Notte serena (usa il prefisso 'night_' per condizioni notturne)\n"
            "• default        → Fallback per condizioni non mappate")
        conditions_text.config(state=tk.DISABLED)
        conditions_text.pack(fill=tk.X, pady=(0, 10))

        # Example config
        example_label = tk.Label(weather_group, text="📝 Esempio Configurazione (config.py):",
                                bg=self.COLORS['bg_secondary'], fg=self.COLORS['accent'],
                                font=('Segoe UI', 11, 'bold'))
        example_label.pack(anchor=tk.W, pady=(15, 5))

        example_text = tk.Text(weather_group, wrap=tk.NONE, height=15, bg=self.COLORS['bg_tertiary'],
                              fg=self.COLORS['text_primary'], font=('Consolas', 8), relief=tk.FLAT, padx=10, pady=10)
        example_text.insert("1.0",
            'WeatherRotationSettings = {\n'
            '    "enabled": True,\n'
            '    "provider": "openweathermap",\n'
            '    "api_key": os.getenv("OPENWEATHER_API_KEY"),\n'
            '    "refresh_minutes": 30,\n'
            '    "apply_on": ["startup", "scheduler", "hotkey"],\n'
            '    "units": "metric",\n'
            '    "location": {\n'
            '        "city": "Milan",\n'
            '        "country": "IT",\n'
            '    },\n'
            '    "conditions": {\n'
            '        "clear": {"playlist": "focus_day"},\n'
            '        "night_clear": {"playlist": "after_hours"},\n'
            '        "rain": {"preset": "relax"},\n'
            '        "snow": {"preset": "relax"},\n'
            '        "default": {"playlist": "focus_day"},\n'
            '    },\n'
            '}')
        example_text.config(state=tk.DISABLED)
        example_text.pack(fill=tk.X)

        # Playlists Section
        playlist_group = ttk.LabelFrame(scrollable_frame, text="🎵 Playlists System", padding=15)
        playlist_group.pack(fill=tk.X, padx=10, pady=10)

        playlist_intro = tk.Text(playlist_group, wrap=tk.WORD, height=4, bg=self.COLORS['bg_tertiary'],
                                fg=self.COLORS['text_primary'], font=('Segoe UI', 9), relief=tk.FLAT, padx=10, pady=10)
        playlist_intro.insert("1.0",
            "Le Playlist permettono di creare sequenze tematiche di preset che vengono applicati in rotazione. "
            "Ogni entry nella playlist può avere un 'weight' (peso) che determina quante volte appare nella sequenza, "
            "override per monitor specifici, e provider/query personalizzati. Ideali per creare esperienze contestuali "
            "(es. focus durante il giorno, relax la sera).")
        playlist_intro.config(state=tk.DISABLED)
        playlist_intro.pack(fill=tk.X, pady=(0, 10))

        # Playlist structure
        structure_label = tk.Label(playlist_group, text="🏗️ Struttura di una Playlist:",
                                  bg=self.COLORS['bg_secondary'], fg=self.COLORS['accent'],
                                  font=('Segoe UI', 11, 'bold'))
        structure_label.pack(anchor=tk.W, pady=(10, 5))

        structure_points = [
            "• name: Identificatore univoco (lowercase)",
            "• title: Nome visualizzato nell'interfaccia",
            "• description: Breve descrizione dello scopo",
            "• tags: Array di tag per categorizzare",
            "• entries: Array di step che compongono la playlist"
        ]

        for point in structure_points:
            point_label = tk.Label(playlist_group, text=point,
                                  bg=self.COLORS['bg_secondary'], fg=self.COLORS['text_primary'],
                                  font=('Segoe UI', 9), justify=tk.LEFT)
            point_label.pack(anchor=tk.W, padx=20, pady=2)

        # Entry structure
        entry_label = tk.Label(playlist_group, text="📋 Struttura di una Entry:",
                              bg=self.COLORS['bg_secondary'], fg=self.COLORS['accent'],
                              font=('Segoe UI', 11, 'bold'))
        entry_label.pack(anchor=tk.W, pady=(15, 5))

        entry_points = [
            "• preset: Nome del preset da utilizzare (richiesto)",
            "• weight: Numero di volte che appare in rotazione (default: 1)",
            "• provider: Override del provider per questo step (opzionale)",
            "• query: Query specifica per questo step (opzionale)",
            "• title: Titolo descrittivo dello step (opzionale)",
            "• monitors: Override specifici per monitor (opzionale)"
        ]

        for point in entry_points:
            point_label = tk.Label(playlist_group, text=point,
                                  bg=self.COLORS['bg_secondary'], fg=self.COLORS['text_primary'],
                                  font=('Segoe UI', 9), justify=tk.LEFT)
            point_label.pack(anchor=tk.W, padx=20, pady=2)

        # Playlist example
        playlist_example_label = tk.Label(playlist_group, text="📝 Esempio Playlist (config.py):",
                                         bg=self.COLORS['bg_secondary'], fg=self.COLORS['accent'],
                                         font=('Segoe UI', 11, 'bold'))
        playlist_example_label.pack(anchor=tk.W, pady=(15, 5))

        playlist_example_text = tk.Text(playlist_group, wrap=tk.NONE, height=25, bg=self.COLORS['bg_tertiary'],
                                       fg=self.COLORS['text_primary'], font=('Consolas', 8), relief=tk.FLAT, padx=10, pady=10)
        playlist_example_text.insert("1.0",
            'Playlists = [\n'
            '    {\n'
            '        "name": "focus_day",\n'
            '        "title": "Focus Daylight",\n'
            '        "description": "Rotazione energizzante per il giorno",\n'
            '        "tags": ["daytime", "focus"],\n'
            '        "entries": [\n'
            '            {\n'
            '                "title": "Deep Focus",\n'
            '                "preset": "workspace",\n'
            '                "weight": 3,  # Appare 3 volte su 4\n'
            '                "provider": "wallhaven",\n'
            '                "monitors": {\n'
            '                    "0": {"preset": "workspace"},  # Monitor index\n'
            '                    "Full HD": {"provider": "wallhaven"},  # Monitor name\n'
            '                    "Ultrawide": {"query": "technology"},\n'
            '                },\n'
            '            },\n'
            '            {\n'
            '                "title": "Mental Break",\n'
            '                "preset": "relax",\n'
            '                "weight": 1,  # Appare 1 volta su 4\n'
            '                "provider": "pexels",\n'
            '                "query": "nature landscape",\n'
            '            },\n'
            '        ],\n'
            '    },\n'
            ']\n\n'
            '# Imposta la playlist di default\n'
            'DefaultPlaylist = "focus_day"')
        playlist_example_text.config(state=tk.DISABLED)
        playlist_example_text.pack(fill=tk.X)

        # How to use
        usage_label = tk.Label(playlist_group, text="🚀 Come Usare le Playlist:",
                              bg=self.COLORS['bg_secondary'], fg=self.COLORS['accent'],
                              font=('Segoe UI', 11, 'bold'))
        usage_label.pack(anchor=tk.W, pady=(15, 5))

        usage_steps = [
            "1. Definisci le tue playlist nell'array 'Playlists' in config.py",
            "2. Imposta 'DefaultPlaylist' con il nome di una playlist (opzionale)",
            "3. Usa Weather Rotation per mappare condizioni meteo a playlist specifiche",
            "4. Il sistema ruoterà automaticamente tra gli step della playlist attiva",
            "5. Gli step con weight maggiore appariranno più frequentemente nella rotazione"
        ]

        for step in usage_steps:
            step_label = tk.Label(playlist_group, text=step,
                                 bg=self.COLORS['bg_secondary'], fg=self.COLORS['text_primary'],
                                 font=('Segoe UI', 9), justify=tk.LEFT)
            step_label.pack(anchor=tk.W, padx=20, pady=2)

        # Tips section
        tips_group = ttk.LabelFrame(scrollable_frame, text="💡 Tips & Best Practices", padding=15)
        tips_group.pack(fill=tk.X, padx=10, pady=10)

        tips = [
            "✓ Combina Weather Rotation e Playlist per esperienze contestuali automatiche",
            "✓ Usa weight elevati per preset preferiti che vuoi vedere più spesso",
            "✓ Gli override per monitor permettono configurazioni diverse per ogni schermo",
            "✓ Testa le configurazioni meteo usando diverse condizioni nel tab Advanced",
            "✓ Refresh meteo ogni 30-60 minuti è sufficiente per la maggior parte degli usi",
            "✓ Crea playlist tematiche (focus, relax, serale) per diverse situazioni",
            "✓ Usa il prefisso 'night_' nelle condizioni meteo per wallpaper notturni specifici",
        ]

        for tip in tips:
            tip_label = tk.Label(tips_group, text=tip,
                                bg=self.COLORS['bg_secondary'], fg=self.COLORS['text_primary'],
                                font=('Segoe UI', 9), justify=tk.LEFT)
            tip_label.pack(anchor=tk.W, padx=10, pady=3)

    def _create_logs_tab(self) -> None:
        """Create logs tab to display application logs"""
        # Main container
        container = tk.Frame(self.logs_frame, bg=self.COLORS['bg_primary'])
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Title
        title_label = tk.Label(container,
                              text="📋 Application Logs",
                              bg=self.COLORS['bg_primary'],
                              fg=self.COLORS['accent'],
                              font=('Segoe UI', 14, 'bold'))
        title_label.pack(pady=(0, 10))

        # Control buttons frame
        controls_frame = tk.Frame(container, bg=self.COLORS['bg_primary'])
        controls_frame.pack(fill=tk.X, pady=(0, 10))

        # Refresh button
        refresh_btn = tk.Button(controls_frame,
                               text="🔄 Refresh Logs",
                               bg=self.COLORS['accent'],
                               fg='#1e1e2e',
                               font=('Segoe UI', 9, 'bold'),
                               relief=tk.FLAT,
                               cursor='hand2',
                               padx=15,
                               pady=8,
                               command=self._refresh_logs)
        refresh_btn.pack(side=tk.LEFT, padx=5)

        # Auto-refresh checkbox
        self.auto_refresh_var = tk.BooleanVar(value=False)
        auto_refresh_cb = ttk.Checkbutton(controls_frame,
                                         text="Auto-refresh (3s)",
                                         variable=self.auto_refresh_var,
                                         command=self._toggle_auto_refresh)
        auto_refresh_cb.pack(side=tk.LEFT, padx=10)

        # Clear logs button
        clear_btn = tk.Button(controls_frame,
                             text="🗑️ Clear Logs",
                             bg=self.COLORS['error'],
                             fg='#1e1e2e',
                             font=('Segoe UI', 9, 'bold'),
                             relief=tk.FLAT,
                             cursor='hand2',
                             padx=15,
                             pady=8,
                             command=self._clear_logs_file)
        clear_btn.pack(side=tk.RIGHT, padx=5)

        # Log viewer with scrollbar
        log_frame = tk.Frame(container, bg=self.COLORS['bg_secondary'])
        log_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollbar
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Text widget for logs
        self.log_text = tk.Text(log_frame,
                               wrap=tk.WORD,
                               bg=self.COLORS['bg_secondary'],
                               fg=self.COLORS['text_primary'],
                               font=('Consolas', 9),
                               yscrollcommand=scrollbar.set,
                               relief=tk.FLAT,
                               padx=10,
                               pady=10)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)

        # Configure tags for different log levels
        self.log_text.tag_config('INFO', foreground=self.COLORS['success'])
        self.log_text.tag_config('WARNING', foreground=self.COLORS['warning'])
        self.log_text.tag_config('ERROR', foreground=self.COLORS['error'])
        self.log_text.tag_config('DEBUG', foreground=self.COLORS['text_muted'])

        # Load initial logs
        self._refresh_logs()

    def _refresh_logs(self) -> None:
        """Refresh the log display"""
        try:
            log_path = Path(__file__).parent / "wallpaperchanger.log"

            if not log_path.exists():
                self.log_text.delete(1.0, tk.END)
                self.log_text.insert(tk.END, "No log file found.\n\n", 'INFO')
                self.log_text.insert(tk.END, "The log file will be created when the Wallpaper Changer service starts.\n", 'INFO')
                return

            # Read log file
            with open(log_path, 'r', encoding='utf-8') as f:
                logs = f.read()

            # Clear current content
            self.log_text.delete(1.0, tk.END)

            # Parse and colorize logs
            for line in logs.splitlines():
                if ' - INFO - ' in line:
                    self.log_text.insert(tk.END, line + '\n', 'INFO')
                elif ' - WARNING - ' in line:
                    self.log_text.insert(tk.END, line + '\n', 'WARNING')
                elif ' - ERROR - ' in line:
                    self.log_text.insert(tk.END, line + '\n', 'ERROR')
                elif ' - DEBUG - ' in line:
                    self.log_text.insert(tk.END, line + '\n', 'DEBUG')
                else:
                    self.log_text.insert(tk.END, line + '\n')

            # Auto-scroll to bottom
            self.log_text.see(tk.END)

        except Exception as e:
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, f"Error reading log file: {e}\n", 'ERROR')

    def _toggle_auto_refresh(self) -> None:
        """Toggle auto-refresh of logs"""
        if self.auto_refresh_var.get():
            self._auto_refresh_logs()

    def _auto_refresh_logs(self) -> None:
        """Auto-refresh logs every 3 seconds"""
        if self.auto_refresh_var.get():
            self._refresh_logs()
            self.root.after(3000, self._auto_refresh_logs)

    def _clear_logs_file(self) -> None:
        """Clear the log file"""
        result = messagebox.askyesno("Confirm",
                                     "Are you sure you want to clear all logs?\n\n"
                                     "This action cannot be undone.")
        if result:
            try:
                log_path = Path(__file__).parent / "wallpaperchanger.log"
                if log_path.exists():
                    with open(log_path, 'w', encoding='utf-8') as f:
                        f.write('')
                    self._refresh_logs()
                    messagebox.showinfo("Success", "Logs cleared successfully!")
                else:
                    messagebox.showwarning("Warning", "No log file found.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear logs: {e}")

    def _get_config_content(self) -> str:
        """Get config.py content"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return f.read()
        except:
            return ""


    def _format_python_literal(self, value: Any) -> str:
        """Pretty format Python literals for editor areas."""
        try:
            return pprint.pformat(value, width=100, sort_dicts=False)
        except Exception:
            return repr(value)

    def _format_playlists_text(self) -> None:
        if not hasattr(self, 'playlists_text'):
            return
        raw = self.playlists_text.get('1.0', tk.END).strip() or '[]'
        try:
            data = ast.literal_eval(raw)
        except Exception as error:
            messagebox.showerror("Playlists", f"Unable to parse playlists: {error}")
            return
        self.playlists_text.delete('1.0', tk.END)
        self.playlists_text.insert('1.0', self._format_python_literal(data))

    def _reset_playlists_text(self) -> None:
        if hasattr(self, 'playlists_text'):
            self.playlists_text.delete('1.0', tk.END)
            self.playlists_text.insert('1.0', self._format_python_literal(self.playlists_data or []))

    def _format_weather_conditions_text(self) -> None:
        if not hasattr(self, 'weather_conditions_text'):
            return
        raw = self.weather_conditions_text.get('1.0', tk.END).strip() or '{}'
        try:
            data = ast.literal_eval(raw)
        except Exception as error:
            messagebox.showerror("Weather Mapping", f"Unable to parse conditions: {error}")
            return
        self.weather_conditions_text.delete('1.0', tk.END)
        self.weather_conditions_text.insert('1.0', self._format_python_literal(data))

    def _reset_weather_conditions_text(self) -> None:
        if hasattr(self, 'weather_conditions_text'):
            conditions = {}
            if isinstance(self.weather_settings, dict):
                conditions = self.weather_settings.get('conditions') or {}
            self.weather_conditions_text.delete('1.0', tk.END)
            self.weather_conditions_text.insert('1.0', self._format_python_literal(conditions))

    def _focus_playlists_editor(self) -> None:
        self.notebook.select(self.advanced_frame)
        self.root.after(150, lambda: self.playlists_text.focus_set() if hasattr(self, 'playlists_text') else None)

    def _focus_weather_editor(self) -> None:
        self.notebook.select(self.advanced_frame)
        self.root.after(150, lambda: self.weather_conditions_text.focus_set() if hasattr(self, 'weather_conditions_text') else None)

    def _test_weather_connection(self) -> None:
        """Test the weather API connection and show current weather"""
        import requests

        # Update UI
        self.weather_status_label.config(text="🔄 Testing connection...", fg=self.COLORS['warning'])
        self.test_weather_btn.config(state=tk.DISABLED)
        self.root.update()

        # Get values
        api_key = self.weather_api_key_var.get().strip()
        city = self.weather_city_var.get().strip()
        country = self.weather_country_var.get().strip()
        lat = self.weather_lat_var.get().strip()
        lon = self.weather_lon_var.get().strip()
        units = self.weather_units_var.get() or "metric"

        # Validate
        if not api_key:
            self.weather_status_label.config(
                text="❌ Error: Please enter an API key first!",
                fg=self.COLORS['error']
            )
            self.test_weather_btn.config(state=tk.NORMAL)
            return

        # Build params
        params = {
            "appid": api_key,
            "units": units
        }

        if lat and lon:
            try:
                params["lat"] = float(lat)
                params["lon"] = float(lon)
                location_str = f"coordinates ({lat}, {lon})"
            except ValueError:
                self.weather_status_label.config(
                    text="❌ Error: Latitude and Longitude must be numbers!",
                    fg=self.COLORS['error']
                )
                self.test_weather_btn.config(state=tk.NORMAL)
                return
        elif city:
            query = city if not country else f"{city},{country}"
            params["q"] = query
            location_str = query
        else:
            self.weather_status_label.config(
                text="❌ Error: Please enter either City name or Latitude/Longitude!",
                fg=self.COLORS['error']
            )
            self.test_weather_btn.config(state=tk.NORMAL)
            return

        # Make request
        try:
            response = requests.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            # Parse response
            weather_list = data.get("weather", [])
            weather = weather_list[0] if weather_list else {}
            main_condition = weather.get("main", "Unknown")
            description = weather.get("description", "")
            temp = data.get("main", {}).get("temp", "N/A")
            feels_like = data.get("main", {}).get("feels_like", "N/A")
            humidity = data.get("main", {}).get("humidity", "N/A")
            city_name = data.get("name", location_str)

            # Unit symbol
            temp_unit = "°C" if units == "metric" else ("°F" if units == "imperial" else "K")

            # Success message
            success_text = (
                f"✅ Connection successful!\n\n"
                f"📍 Location: {city_name}\n"
                f"☁️ Condition: {main_condition} ({description})\n"
                f"🌡️ Temperature: {temp}{temp_unit} (feels like {feels_like}{temp_unit})\n"
                f"💧 Humidity: {humidity}%\n\n"
                f"✨ Your weather API is working! This condition would be mapped as: '{main_condition.lower()}'"
            )

            self.weather_status_label.config(
                text=success_text,
                fg=self.COLORS['success']
            )

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                error_text = (
                    "❌ API Key Error: Invalid or unauthorized API key.\n\n"
                    "⏰ IMPORTANT: If you just created the API key, it can take up to 2 HOURS to activate!\n"
                    "OpenWeatherMap says it's active in your account, but the backend needs time to propagate.\n\n"
                    "Please check:\n"
                    "1. Did you copy the key correctly from your account?\n"
                    "2. Was it created less than 2 hours ago? → Wait and try again later\n"
                    "3. Is it showing as 'Active' at https://home.openweathermap.org/api_keys ?\n\n"
                    "💡 TIP: Try again in 15-30 minutes if you just created it."
                )
            elif e.response.status_code == 404:
                error_text = (
                    f"❌ Location Error: '{location_str}' not found.\n\n"
                    "Please check your city name or try using latitude/longitude instead."
                )
            else:
                error_text = f"❌ HTTP Error {e.response.status_code}: {str(e)}"

            self.weather_status_label.config(text=error_text, fg=self.COLORS['error'])

        except requests.exceptions.Timeout:
            self.weather_status_label.config(
                text="❌ Connection timeout. Please check your internet connection.",
                fg=self.COLORS['error']
            )

        except Exception as e:
            self.weather_status_label.config(
                text=f"❌ Error: {str(e)}",
                fg=self.COLORS['error']
            )

        finally:
            self.test_weather_btn.config(state=tk.NORMAL)

    def _toggle_password_visibility(self, entry_widget) -> None:
        """Toggle password visibility for API key fields"""
        current_show = entry_widget.cget("show")
        entry_widget.configure(show="" if current_show == "*" else "*")

    def _browse_directory(self, var: tk.StringVar) -> None:
        """Open directory browser"""
        from tkinter import filedialog
        directory = filedialog.askdirectory(initialdir=var.get(), title="Select Directory")
        if directory:
            var.set(directory)

    def _save_api_keys(self) -> None:
        """Save API keys to .env file"""
        try:
            env_path = Path(__file__).parent / '.env'
            wallhaven_key = self.wallhaven_key_var.get().strip()
            pexels_key = self.pexels_key_var.get().strip()
            openweather_key = self.weather_api_key_var.get().strip() if hasattr(self, 'weather_api_key_var') else ""

            content = f"""# Wallhaven API Key from https://wallhaven.cc/settings/account
WALLHAVEN_API_KEY={wallhaven_key}

# Pexels API Key from https://www.pexels.com/api/new/
PEXELS_API_KEY={pexels_key}

# OpenWeatherMap API Key from https://home.openweathermap.org/api_keys
# Free tier: 1000 calls/day (more than enough!)
OPENWEATHER_API_KEY={openweather_key}
"""
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(content)

            messagebox.showinfo("Success", "API Keys saved successfully to .env file!\n\nAll API keys (Wallhaven, Pexels, OpenWeatherMap) have been saved.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save API keys: {e}")

    def _load_monitors(self) -> None:
        """Load available monitors"""
        from main import enumerate_monitors_user32, DesktopWallpaperController

        monitors = []
        try:
            manager = DesktopWallpaperController()
            monitors = manager.enumerate_monitors()
            manager.close()
        except Exception:
            try:
                monitors = enumerate_monitors_user32()
            except Exception:
                pass

        monitor_options = ["All Monitors"]
        for idx, mon in enumerate(monitors):
            monitor_options.append(f"Monitor {idx + 1} ({mon.get('width')}x{mon.get('height')})")

        self.monitor_combo['values'] = monitor_options
        self.monitors_data = monitors

    def _refresh_gallery(self) -> None:
        """Refresh wallpaper gallery"""
        # Clear existing items
        for widget in self.gallery_frame.winfo_children():
            widget.destroy()

        # Clear thumbnail cache
        self.thumbnail_cache.clear()

        # Get cached items
        entries = self.cache_manager.list_entries()

        if not entries:
            info_frame = ttk.Frame(self.gallery_frame)
            info_frame.pack(pady=20, padx=20)

            ttk.Label(info_frame, text="No cached wallpapers found.",
                     font=("Arial", 12, "bold")).pack(pady=10)
            ttk.Label(info_frame, text="Wallpapers will appear here after the app downloads them.",
                     font=("Arial", 10)).pack(pady=5)
            ttk.Label(info_frame, text=f"Cache location: {self.cache_manager.cache_dir}",
                     font=("Arial", 9), foreground="gray").pack(pady=5)

            # Check if cache directory exists
            if os.path.exists(self.cache_manager.cache_dir):
                cache_files = [f for f in os.listdir(self.cache_manager.cache_dir)
                              if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
                if cache_files:
                    ttk.Label(info_frame,
                             text=f"Found {len(cache_files)} image files in cache, but index may be empty.",
                             font=("Arial", 9), foreground="orange").pack(pady=5)
            return

        # Store ALL entries for filtering/sorting
        self.all_entries = entries

        # Apply filters and sort
        self._apply_filters()

    def _apply_filters(self) -> None:
        """Apply filters and sorting to gallery"""
        if not hasattr(self, 'all_entries'):
            return

        filtered_entries = list(self.all_entries)

        # Apply resolution filter
        filter_val = self.filter_resolution.get()
        if filter_val != "All":
            min_width = int(filter_val.split('x')[0].replace('+', ''))
            min_height = int(filter_val.split('x')[1].replace('+', ''))

            filtered_entries = [
                e for e in filtered_entries
                if self._get_image_resolution(e)[0] >= min_width and
                   self._get_image_resolution(e)[1] >= min_height
            ]

        # Apply sorting
        sort_val = self.sort_by.get()
        if sort_val == "Newest First":
            pass  # Already in newest first order
        elif sort_val == "Oldest First":
            filtered_entries = list(reversed(filtered_entries))
        elif sort_val == "Highest Resolution":
            filtered_entries.sort(key=lambda e: self._get_image_resolution(e)[0] * self._get_image_resolution(e)[1], reverse=True)
        elif sort_val == "Lowest Resolution":
            filtered_entries.sort(key=lambda e: self._get_image_resolution(e)[0] * self._get_image_resolution(e)[1])

        # Limit to 50 for performance
        self.cached_entries = filtered_entries[:50]

        # Calculate responsive columns based on window width
        self._layout_thumbnails()

    def _get_image_resolution(self, entry: Dict[str, Any]) -> Tuple[int, int]:
        """Get image resolution from entry or file"""
        # Try to get from cache metadata first
        if 'width' in entry and 'height' in entry:
            return (entry['width'], entry['height'])

        # Try to read from image file
        try:
            image_path = entry.get("path", "")
            if image_path and os.path.exists(image_path):
                with Image.open(image_path) as img:
                    return img.size
        except:
            pass

        return (0, 0)  # Default if unable to determine

    def _on_gallery_resize(self, event) -> None:
        """Handle gallery canvas resize to re-layout thumbnails"""
        # Check if width actually changed significantly
        if not hasattr(self, '_last_canvas_width'):
            self._last_canvas_width = 0

        new_width = self.gallery_canvas.winfo_width()
        if abs(new_width - self._last_canvas_width) < 50:  # Ignore small changes
            return

        self._last_canvas_width = new_width

        if hasattr(self, '_resize_after_id'):
            # Cancel previous scheduled re-layout
            self.root.after_cancel(self._resize_after_id)

        # Schedule re-layout after 500ms to avoid excessive updates during drag
        self._resize_after_id = self.root.after(500, self._layout_thumbnails)

    def _layout_thumbnails(self) -> None:
        """Layout thumbnails in a responsive grid based on canvas width"""
        if not hasattr(self, 'cached_entries') or not self.cached_entries:
            return

        # Clear existing thumbnails
        for widget in self.gallery_frame.winfo_children():
            widget.destroy()

        # Calculate number of columns based on canvas width
        # Each thumbnail card is ~270px wide (250px + 20px padding)
        canvas_width = self.gallery_canvas.winfo_width()
        if canvas_width < 100:  # Canvas not yet sized
            canvas_width = 1000  # Default width

        card_width = 270
        max_cols = max(1, canvas_width // card_width)

        print(f"Gallery width: {canvas_width}px, Columns: {max_cols}")

        # Create grid of thumbnails
        row = 0
        col = 0

        for idx, entry in enumerate(self.cached_entries):
            self._create_thumbnail(entry, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def _create_thumbnail(self, entry: Dict[str, Any], row: int, col: int) -> None:
        """Create a thumbnail widget for a wallpaper"""
        # Create modern card frame
        card = tk.Frame(self.gallery_frame,
                       bg=self.COLORS['bg_secondary'],
                       highlightbackground=self.COLORS['border'],
                       highlightthickness=1)
        card.grid(row=row, column=col, padx=8, pady=8, sticky=tk.NSEW)

        # Add hover effect
        def on_enter(e):
            card.configure(highlightbackground=self.COLORS['accent'], highlightthickness=2)

        def on_leave(e):
            card.configure(highlightbackground=self.COLORS['border'], highlightthickness=1)

        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

        try:
            # Check if file exists
            image_path = entry.get("path", "")
            if not image_path or not os.path.exists(image_path):
                raise FileNotFoundError(f"Image not found: {image_path}")

            # Check thumbnail cache first
            if image_path in self.thumbnail_cache:
                photo, original_size = self.thumbnail_cache[image_path]
            else:
                # Load and resize image
                img = Image.open(image_path)
                original_size = img.size  # Store original resolution

                # Create thumbnail
                img.thumbnail((250, 150), Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)

                # Cache the thumbnail
                self.thumbnail_cache[image_path] = (photo, original_size)

            # Image container
            img_container = tk.Frame(card, bg=self.COLORS['bg_tertiary'])
            img_container.pack(padx=8, pady=8, fill=tk.BOTH, expand=True)

            # Image label
            img_label = tk.Label(img_container, image=photo, bg=self.COLORS['bg_tertiary'])
            img_label.image = photo  # Keep reference
            img_label.pack()

            # Info container
            info_container = tk.Frame(card, bg=self.COLORS['bg_secondary'])
            info_container.pack(fill=tk.X, padx=10, pady=5)

            # Resolution label with icon
            resolution_text = f"📐 {original_size[0]}x{original_size[1]}"
            resolution_label = tk.Label(info_container, text=resolution_text,
                                       bg=self.COLORS['bg_secondary'],
                                       fg=self.COLORS['accent'],
                                       font=('Segoe UI', 9, 'bold'))
            resolution_label.pack(anchor=tk.W)

            # Info label
            info_text = entry.get("source_info", "Unknown")[:45]
            info_label = tk.Label(info_container, text=info_text,
                                 bg=self.COLORS['bg_secondary'],
                                 fg=self.COLORS['text_secondary'],
                                 font=('Segoe UI', 8),
                                 wraplength=250,
                                 justify=tk.LEFT)
            info_label.pack(anchor=tk.W, pady=(2, 5))

            # Apply button with accent style - shows monitor selection menu
            apply_btn = tk.Button(card, text="✨ Apply to Monitor",
                                 bg=self.COLORS['accent'],
                                 fg='#1e1e2e',
                                 font=('Segoe UI', 9, 'bold'),
                                 relief=tk.FLAT,
                                 cursor='hand2',
                                 padx=15,
                                 pady=8,
                                 command=lambda e=entry: self._show_monitor_selection(e))
            apply_btn.pack(pady=(0, 10), padx=10, fill=tk.X)

            # Button hover effect
            def btn_enter(e):
                apply_btn.configure(bg=self.COLORS['accent_hover'])

            def btn_leave(e):
                apply_btn.configure(bg=self.COLORS['accent'])

            apply_btn.bind("<Enter>", btn_enter)
            apply_btn.bind("<Leave>", btn_leave)

        except Exception as e:
            error_label = tk.Label(card, text=f"❌ Error loading image:\n{str(e)[:50]}",
                                  bg=self.COLORS['bg_secondary'],
                                  fg=self.COLORS['error'],
                                  font=('Segoe UI', 9),
                                  wraplength=250,
                                  justify=tk.CENTER)
            error_label.pack(pady=20, padx=10)

    def _show_monitor_selection(self, entry: Dict[str, Any]) -> None:
        """Show monitor selection dialog"""
        # Create popup window
        popup = tk.Toplevel(self.root)
        popup.title("Select Monitor")
        popup.geometry("400x300")
        popup.configure(bg=self.COLORS['bg_secondary'])
        popup.transient(self.root)
        popup.grab_set()

        # Center the popup
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - (400 // 2)
        y = (popup.winfo_screenheight() // 2) - (300 // 2)
        popup.geometry(f"+{x}+{y}")

        # Title
        title_label = tk.Label(popup,
                              text="🖥️ Select Monitor",
                              bg=self.COLORS['bg_secondary'],
                              fg=self.COLORS['accent'],
                              font=('Segoe UI', 14, 'bold'))
        title_label.pack(pady=(20, 10))

        # Info
        info_label = tk.Label(popup,
                             text="Choose which monitor to apply this wallpaper to:",
                             bg=self.COLORS['bg_secondary'],
                             fg=self.COLORS['text_secondary'],
                             font=('Segoe UI', 9))
        info_label.pack(pady=(0, 20))

        # Get available monitors
        from main import enumerate_monitors_user32, DesktopWallpaperController

        monitors = []
        try:
            manager = DesktopWallpaperController()
            monitors = manager.enumerate_monitors()
            manager.close()
        except Exception:
            try:
                monitors = enumerate_monitors_user32()
            except Exception:
                pass

        # Buttons frame
        buttons_frame = tk.Frame(popup, bg=self.COLORS['bg_secondary'])
        buttons_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # All Monitors button
        all_btn = tk.Button(buttons_frame,
                           text="🖥️ All Monitors",
                           bg=self.COLORS['accent'],
                           fg='#1e1e2e',
                           font=('Segoe UI', 10, 'bold'),
                           relief=tk.FLAT,
                           cursor='hand2',
                           padx=20,
                           pady=12,
                           command=lambda: [popup.destroy(), self._apply_wallpaper(entry, "All Monitors", monitors)])
        all_btn.pack(fill=tk.X, pady=5)

        # Individual monitor buttons
        for idx, monitor in enumerate(monitors):
            monitor_name = f"Monitor {idx + 1} ({monitor.get('width')}x{monitor.get('height')})"
            mon_btn = tk.Button(buttons_frame,
                               text=f"🖥️ {monitor_name}",
                               bg=self.COLORS['bg_tertiary'],
                               fg=self.COLORS['text_primary'],
                               font=('Segoe UI', 10),
                               relief=tk.FLAT,
                               cursor='hand2',
                               padx=20,
                               pady=10,
                               command=lambda m=monitor_name, i=idx: [popup.destroy(),
                                                                       self._apply_wallpaper(entry, m, monitors, i)])
            mon_btn.pack(fill=tk.X, pady=3)

            # Hover effects
            def make_hover(btn):
                def on_enter(e):
                    btn.configure(bg=self.COLORS['accent_hover'])
                def on_leave(e):
                    btn.configure(bg=self.COLORS['bg_tertiary'])
                btn.bind("<Enter>", on_enter)
                btn.bind("<Leave>", on_leave)

            make_hover(mon_btn)

        # Cancel button
        cancel_btn = tk.Button(buttons_frame,
                              text="❌ Cancel",
                              bg=self.COLORS['error'],
                              fg='#1e1e2e',
                              font=('Segoe UI', 9, 'bold'),
                              relief=tk.FLAT,
                              cursor='hand2',
                              padx=15,
                              pady=8,
                              command=popup.destroy)
        cancel_btn.pack(fill=tk.X, pady=(10, 5))

    def _apply_wallpaper(self, entry: Dict[str, Any], monitor_selection: str = None,
                         monitors_list: List = None, monitor_idx: int = None) -> None:
        """Apply selected wallpaper to monitor"""
        if monitor_selection is None:
            monitor_selection = self.monitor_var.get()

        try:
            from main import WallpaperApp, DesktopWallpaperController, enumerate_monitors_user32
            import ctypes

            wallpaper_path = entry["path"]

            # Convert to BMP if needed
            if not wallpaper_path.lower().endswith('.bmp'):
                from pathlib import Path
                bmp_path = str(Path(wallpaper_path).with_suffix('.bmp'))
                img = Image.open(wallpaper_path)
                img.save(bmp_path, 'BMP')
                wallpaper_path = bmp_path

            if monitor_selection == "All Monitors":
                # Apply to all monitors
                ctypes.windll.user32.SystemParametersInfoW(20, 0, wallpaper_path, 3)
                messagebox.showinfo("Success", "Wallpaper applied to all monitors!")
            else:
                # Apply to specific monitor
                # If monitor_idx is passed directly, use it. Otherwise parse from selection string
                if monitor_idx is None:
                    monitor_idx = int(monitor_selection.split()[1]) - 1

                # Get monitors if not passed
                if monitors_list is None:
                    manager = DesktopWallpaperController()
                    monitors_list = manager.enumerate_monitors()
                else:
                    manager = DesktopWallpaperController()

                if monitor_idx < len(monitors_list):
                    manager.set_wallpaper(monitors_list[monitor_idx]["id"], wallpaper_path)
                    manager.close()
                    messagebox.showinfo("Success", f"Wallpaper applied to {monitor_selection}!")
                else:
                    manager.close()
                    messagebox.showerror("Error", "Invalid monitor selection")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply wallpaper: {e}")

    def _change_wallpaper_now(self) -> None:
        """Trigger immediate wallpaper change via main app"""
        try:
            # Check if main app is running by looking for PID file
            if not self._check_app_status():
                messagebox.showwarning("App Not Running",
                    "The Wallpaper Changer app is not currently running.\n\n"
                    "Please start it first using:\n"
                    "• launchers/start_wallpaper_changer.vbs\n"
                    "• or 'python main.py'")
                return

            # Show loading message
            loading_window = tk.Toplevel(self.root)
            loading_window.title("Changing Wallpaper")
            loading_window.geometry("350x120")
            loading_window.configure(bg=self.COLORS['bg_secondary'])
            loading_window.transient(self.root)
            loading_window.grab_set()

            # Center the loading window
            loading_window.update_idletasks()
            x = (loading_window.winfo_screenwidth() // 2) - (350 // 2)
            y = (loading_window.winfo_screenheight() // 2) - (120 // 2)
            loading_window.geometry(f"+{x}+{y}")

            msg_label = tk.Label(loading_window,
                                text="🎨 Changing wallpaper...\n\nPlease wait a moment.",
                                bg=self.COLORS['bg_secondary'],
                                fg=self.COLORS['text_primary'],
                                font=('Segoe UI', 11))
            msg_label.pack(expand=True)

            loading_window.update()

            if not self._send_signal_command({"action": "change_wallpaper"}):
                loading_window.destroy()
                return

            # Wait for the change to happen
            self.root.after(2000, lambda: loading_window.destroy())
            self.root.after(2500, lambda: messagebox.showinfo("Success",
                "Wallpaper change triggered!\n\n"
                "Check the Logs tab for details."))
            self.root.after(1200, lambda: self._update_provider_info(schedule_next=False))

        except Exception as e:
            messagebox.showerror("Error", f"Failed to change wallpaper: {e}")

    def _clear_cache(self) -> None:
        """Clear wallpaper cache"""
        result = messagebox.askyesno("Confirm", "Are you sure you want to clear the cache?")
        if result:
            try:
                import shutil
                if os.path.exists(self.cache_manager.cache_dir):
                    shutil.rmtree(self.cache_manager.cache_dir)
                    os.makedirs(self.cache_manager.cache_dir)
                messagebox.showinfo("Success", "Cache cleared successfully!")
                self._refresh_gallery()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear cache: {e}")

    def _save_config(self) -> None:
        """Save configuration to config.py"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Prepare advanced structures
            try:
                playlists_literal: Any = self.playlists_data or []
                if hasattr(self, 'playlists_text'):
                    raw_playlists = self.playlists_text.get('1.0', tk.END).strip()
                    if raw_playlists:
                        playlists_literal = ast.literal_eval(raw_playlists)
                    else:
                        playlists_literal = []
                if not isinstance(playlists_literal, list):
                    raise ValueError("Playlists must be a list of dictionaries")
            except Exception as error:
                messagebox.showerror("Playlists", f"Unable to parse playlists: {error}")
                return

            try:
                weather_conditions: Any = {}
                if isinstance(self.weather_settings, dict):
                    weather_conditions = self.weather_settings.get('conditions') or {}
                if hasattr(self, 'weather_conditions_text'):
                    raw_conditions = self.weather_conditions_text.get('1.0', tk.END).strip()
                    if raw_conditions:
                        weather_conditions = ast.literal_eval(raw_conditions)
                    else:
                        weather_conditions = {}
                if not isinstance(weather_conditions, dict):
                    raise ValueError("Weather conditions must be a dictionary")
            except Exception as error:
                messagebox.showerror("Weather Mapping", f"Unable to parse weather conditions: {error}")
                return

            weather_settings = dict(self.weather_settings or {}) if isinstance(self.weather_settings, dict) else {}
            weather_settings.update(
                {
                    "enabled": bool(self.weather_enabled_var.get() if hasattr(self, 'weather_enabled_var') else weather_settings.get('enabled', False)),
                    "provider": self.weather_provider_var.get().strip() if hasattr(self, 'weather_provider_var') else weather_settings.get("provider", "openweathermap"),
                    "api_key": 'os.getenv("OPENWEATHER_API_KEY", "")',  # Use os.getenv to read from .env
                    "refresh_minutes": max(1, int(self.weather_refresh_var.get() if hasattr(self, 'weather_refresh_var') else weather_settings.get("refresh_minutes", 30) or 30)),
                    "units": self.weather_units_var.get().strip() if hasattr(self, 'weather_units_var') else weather_settings.get("units", "metric"),
                }
            )

            apply_on: List[str] = []
            if hasattr(self, 'weather_apply_on_vars'):
                for trigger, var in self.weather_apply_on_vars.items():
                    if var.get():
                        apply_on.append(trigger)
            else:
                apply_on = weather_settings.get("apply_on", []) or []
            weather_settings["apply_on"] = apply_on

            location: Dict[str, Any] = {}
            if hasattr(self, 'weather_city_var') and self.weather_city_var.get().strip():
                location["city"] = self.weather_city_var.get().strip()
            if hasattr(self, 'weather_country_var') and self.weather_country_var.get().strip():
                location["country"] = self.weather_country_var.get().strip()
            if hasattr(self, 'weather_lat_var') and self.weather_lat_var.get().strip():
                try:
                    location["latitude"] = float(self.weather_lat_var.get().strip())
                except ValueError:
                    messagebox.showerror("Weather Mapping", "Latitude must be a number")
                    return
            if hasattr(self, 'weather_lon_var') and self.weather_lon_var.get().strip():
                try:
                    location["longitude"] = float(self.weather_lon_var.get().strip())
                except ValueError:
                    messagebox.showerror("Weather Mapping", "Longitude must be a number")
                    return
            weather_settings["location"] = location
            weather_settings["conditions"] = weather_conditions

            default_playlist_value = ""
            if hasattr(self, 'default_playlist_display_var'):
                selection = self.default_playlist_display_var.get().strip()
                default_playlist_value = "" if selection in {"", "(None)"} else selection

            playlists_block = "Playlists = " + self._format_python_literal(playlists_literal)
            weather_block_raw = self._format_python_literal(weather_settings)
            # Fix: os.getenv() should not be quoted - replace the quoted version with executable code
            weather_block_raw = weather_block_raw.replace('"os.getenv(\\"OPENWEATHER_API_KEY\\", \\"\\")"', 'os.getenv("OPENWEATHER_API_KEY", "")')
            weather_block_raw = weather_block_raw.replace("'os.getenv(\"OPENWEATHER_API_KEY\", \"\")'", 'os.getenv("OPENWEATHER_API_KEY", "")')
            weather_block = "WeatherRotationSettings = " + weather_block_raw

            new_lines: List[str] = []
            in_monitors_section = False
            monitor_entry_counter = -1
            in_reddit_section = False
            skip_playlists = False
            skip_weather = False
            in_weather_location = False
            found_default_playlist = False
            found_playlists = False
            found_weather = False
            found_monitors = False

            for line in lines:
                stripped = line.strip()

                if skip_playlists:
                    # Preserve original playlist lines
                    new_lines.append(line)
                    if stripped.startswith("]"):
                        skip_playlists = False
                    continue
                if skip_weather:
                    # Track if we're inside the "location" sub-dict
                    if '"location":' in line and '{' in line:
                        in_weather_location = True
                        new_lines.append(line)
                        # Continue to skip further processing of this line
                    # Update specific weather settings fields that GUI can modify
                    elif '"enabled":' in line:
                        indent = line[:len(line) - len(line.lstrip())]
                        enabled_val = self.weather_enabled_var.get() if hasattr(self, 'weather_enabled_var') else True
                        new_lines.append(f'{indent}"enabled": {enabled_val},\n')
                    elif '"refresh_minutes":' in line:
                        indent = line[:len(line) - len(line.lstrip())]
                        refresh_val = int(self.weather_refresh_var.get()) if hasattr(self, 'weather_refresh_var') else 30
                        new_lines.append(f'{indent}"refresh_minutes": {refresh_val},\n')
                    elif '"units":' in line:
                        indent = line[:len(line) - len(line.lstrip())]
                        units_val = self.weather_units_var.get() if hasattr(self, 'weather_units_var') else "metric"
                        new_lines.append(f'{indent}"units": "{units_val}",\n')
                    elif '"apply_on":' in line:
                        indent = line[:len(line) - len(line.lstrip())]
                        apply_on = []
                        if hasattr(self, 'weather_apply_on_vars'):
                            for trigger, var in self.weather_apply_on_vars.items():
                                if var.get():
                                    apply_on.append(trigger)
                        else:
                            apply_on = ["startup", "scheduler", "hotkey"]
                        new_lines.append(f'{indent}"apply_on": {apply_on},\n')
                    elif in_weather_location and '"city":' in line:
                        indent = line[:len(line) - len(line.lstrip())]
                        city_val = self.weather_city_var.get() if hasattr(self, 'weather_city_var') else "Milan"
                        new_lines.append(f'{indent}"city": "{city_val}",\n')
                    elif in_weather_location and '"country":' in line:
                        indent = line[:len(line) - len(line.lstrip())]
                        country_val = self.weather_country_var.get() if hasattr(self, 'weather_country_var') else "IT"
                        new_lines.append(f'{indent}"country": "{country_val}",\n')
                    elif in_weather_location and '"latitude":' in line:
                        indent = line[:len(line) - len(line.lstrip())]
                        lat_val = self.weather_lat_var.get() if hasattr(self, 'weather_lat_var') else "45.4642"
                        try:
                            lat_val = float(lat_val) if lat_val else 45.4642
                        except:
                            lat_val = 45.4642
                        new_lines.append(f'{indent}"latitude": {lat_val},\n')
                    elif in_weather_location and '"longitude":' in line:
                        indent = line[:len(line) - len(line.lstrip())]
                        lon_val = self.weather_lon_var.get() if hasattr(self, 'weather_lon_var') else "9.19"
                        try:
                            lon_val = float(lon_val) if lon_val else 9.19
                        except:
                            lon_val = 9.19
                        new_lines.append(f'{indent}"longitude": {lon_val},\n')
                    else:
                        # Keep other lines as-is (api_key, provider, conditions, etc.)
                        new_lines.append(line)

                    # Check if we're exiting the location block
                    if in_weather_location and stripped.startswith("},"):
                        in_weather_location = False

                    # Check if we're exiting the weather settings block
                    if stripped.startswith("}") and not in_weather_location:
                        skip_weather = False
                    continue

                if stripped.startswith("Provider ="):
                    new_lines.append(f'Provider = "{self.provider_var.get()}"\n')
                elif stripped.startswith("Query ="):
                    new_lines.append(f'Query = "{self.query_var.get()}"\n')
                elif stripped.startswith("PurityLevel ="):
                    new_lines.append(f'PurityLevel = "{self.purity_var.get()}"\n')
                elif stripped.startswith("ScreenResolution ="):
                    new_lines.append(f'ScreenResolution = "{self.resolution_var.get()}"\n')
                elif stripped.startswith("WallhavenSorting ="):
                    new_lines.append(f'WallhavenSorting = "{self.sorting_var.get()}"\n')
                elif stripped.startswith("WallhavenTopRange ="):
                    new_lines.append(f'WallhavenTopRange = "{self.toprange_var.get()}"\n')
                elif stripped.startswith("PexelsMode ="):
                    new_lines.append(f'PexelsMode = "{self.pexels_mode_var.get()}"\n')
                elif stripped.startswith("RotateProviders ="):
                    new_lines.append(f'RotateProviders = {self.rotate_providers_var.get()}\n')
                elif stripped.startswith("KeyBind ="):
                    new_lines.append(f'KeyBind = "{self.keybind_var.get()}"\n')
                elif stripped.startswith("RedditSettings = {"):
                    in_reddit_section = True
                    new_lines.append(line)
                elif in_reddit_section and '"subreddits":' in line:
                    subreddits = [s.strip() for s in self.reddit_subreddits_var.get().split(",") if s.strip()]
                    if not subreddits:
                        subreddits = ["wallpapers"]
                    new_lines.append(f'    "subreddits": {json.dumps(subreddits)},\n')
                elif in_reddit_section and '"sort":' in line:
                    new_lines.append(f'    "sort": {json.dumps(self.reddit_sort_var.get().strip().lower() or "hot")},\n')
                elif in_reddit_section and '"time_filter":' in line:
                    new_lines.append(f'    "time_filter": {json.dumps(self.reddit_time_var.get().strip().lower() or "day")},\n')
                elif in_reddit_section and '"limit":' in line:
                    limit_value = max(10, min(100, int(self.reddit_limit_var.get() or 60)))
                    new_lines.append(f'    "limit": {limit_value},\n')
                elif in_reddit_section and '"min_score":' in line:
                    min_score_value = max(0, int(self.reddit_score_var.get() or 0))
                    new_lines.append(f'    "min_score": {min_score_value},\n')
                elif in_reddit_section and '"allow_nsfw":' in line:
                    new_lines.append(f'    "allow_nsfw": {self.reddit_nsfw_var.get()},\n')
                elif in_reddit_section and '"user_agent":' in line:
                    user_agent = self.reddit_user_agent_var.get().strip() or "WallpaperChanger/1.0 (by u/yourusername)"
                    new_lines.append(f'    "user_agent": {json.dumps(user_agent)},\n')
                elif in_reddit_section and stripped.startswith("}"):
                    in_reddit_section = False
                    new_lines.append(line)
                elif '"enabled":' in line and "SchedulerSettings" in "".join(new_lines[-10:]):
                    new_lines.append(f'    "enabled": {self.scheduler_enabled_var.get()},\n')
                elif '"interval_minutes":' in line:
                    new_lines.append(f'    "interval_minutes": {self.interval_var.get()},\n')
                elif '"jitter_minutes":' in line:
                    new_lines.append(f'    "jitter_minutes": {self.jitter_var.get()},\n')
                elif '"initial_delay_minutes":' in line:
                    new_lines.append(f'    "initial_delay_minutes": {self.initial_delay_var.get()},\n')
                elif '"max_items":' in line and "CacheSettings" in "".join(new_lines[-10:]):
                    new_lines.append(f'    "max_items": {self.cache_max_var.get()},\n')
                elif '"enable_offline_rotation":' in line:
                    new_lines.append(f'    "enable_offline_rotation": {self.cache_offline_var.get()},\n')
                elif '"directory":' in line and "CacheSettings" in "".join(new_lines[-10:]):
                    cache_path = self.cache_dir_var.get() if hasattr(self, 'cache_dir_var') else ""
                    # Use raw string prefix for Windows paths
                    new_lines.append(f'    "directory": r"{cache_path}",\n')
                elif stripped.startswith("DefaultPreset ="):
                    default_preset = self.default_preset_var.get() if hasattr(self, 'default_preset_var') else "workspace"
                    new_lines.append(f'DefaultPreset = "{default_preset}"\n')
                elif stripped.startswith("DefaultPlaylist ="):
                    found_default_playlist = True
                    new_lines.append(f'DefaultPlaylist = "{default_playlist_value}"\n')
                elif stripped.startswith("Playlists ="):
                    found_playlists = True
                    # Preserve original Playlists section - don't reformat
                    new_lines.append(line)
                    skip_playlists = True
                elif stripped.startswith("WeatherRotationSettings ="):
                    found_weather = True
                    # Preserve original WeatherRotationSettings section - don't reformat
                    new_lines.append(line)
                    skip_weather = True
                elif stripped.startswith("Monitors = ["):
                    found_monitors = True
                    in_monitors_section = True
                    monitor_entry_counter = -1
                    new_lines.append(line)
                elif in_monitors_section and stripped == "{":
                    monitor_entry_counter += 1
                    new_lines.append(line)
                elif in_monitors_section and '"screen_resolution":' in line and hasattr(self, 'monitor_resolution_vars'):
                    if monitor_entry_counter in self.monitor_resolution_vars:
                        resolution = self.monitor_resolution_vars[monitor_entry_counter].get()
                        indent = line[:len(line) - len(line.lstrip())]
                        new_lines.append(f'{indent}"screen_resolution": "{resolution}",\n')
                    else:
                        new_lines.append(line)
                elif in_monitors_section and stripped == "]":
                    in_monitors_section = False
                    new_lines.append(line)
                else:
                    new_lines.append(line)

            # Append missing sections at the end if they weren't found in the original file
            if not found_default_playlist:
                new_lines.append(f'\nDefaultPlaylist = "{default_playlist_value}"\n')

            if not found_playlists:
                new_lines.append(f'\n{playlists_block}\n')

            if not found_weather:
                new_lines.append(f'\n{weather_block}\n')

            if not found_monitors:
                # Add default Monitors section
                new_lines.append('\nMonitors = [\n')
                new_lines.append('    {\n')
                new_lines.append('        "name": "Full HD",\n')
                new_lines.append('        "preset": "workspace",\n')
                new_lines.append('        "provider": "",\n')
                new_lines.append('        "query": "",\n')
                new_lines.append('        "screen_resolution": "1920x1080",\n')
                new_lines.append('        "purity": "100",\n')
                new_lines.append('        "wallhaven_sorting": "random",\n')
                new_lines.append('        "wallhaven_top_range": "1M",\n')
                new_lines.append('    },\n')
                new_lines.append(']\n')

            with open(self.config_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            self.playlists_data = playlists_literal
            self.weather_settings = weather_settings
            self.config_data["Playlists"] = playlists_literal
            self.config_data["WeatherRotationSettings"] = weather_settings
            self.config_data["DefaultPlaylist"] = default_playlist_value

            if hasattr(self, 'wallhaven_key_var') and hasattr(self, 'pexels_key_var'):
                self._save_api_keys()

            messagebox.showinfo("Success", "Configuration saved successfully!\n\nRestart the application for changes to take effect.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")

    def _reload_config(self) -> None:
        """Reload configuration"""
        self._load_config()
        self.playlists_data = list(self.config_data.get("Playlists") or [])
        self.weather_settings = dict(self.config_data.get("WeatherRotationSettings") or {})
        messagebox.showinfo("Success", "Configuration reloaded!")

        # Update basic UI elements
        self.provider_var.set(self.config_data.get("Provider", "wallhaven"))
        self.query_var.set(self.config_data.get("Query", "nature"))
        self.purity_var.set(self.config_data.get("PurityLevel", "100"))
        self.resolution_var.set(self.config_data.get("ScreenResolution", "1920x1080"))

        if hasattr(self, 'default_preset_var'):
            self.default_preset_var.set(self._extract_value(self._get_config_content(), "DefaultPreset") or "workspace")

        # Update playlist selector and summary
        if hasattr(self, 'default_playlist_display_var'):
            raw_default_playlist = (self.config_data.get("DefaultPlaylist") or "").strip()
            playlist_names: List[str] = []
            seen = set()
            for item in self.playlists_data:
                if isinstance(item, dict):
                    name = str(item.get("name", "")).strip()
                    if name and name not in seen:
                        playlist_names.append(name)
                        seen.add(name)
            display_value = raw_default_playlist if raw_default_playlist in playlist_names else "(None)"
            self.default_playlist_display_var.set(display_value)
            if hasattr(self, 'default_playlist_combo'):
                values = ["(None)"] + playlist_names
                self.default_playlist_combo['values'] = values
            if hasattr(self, 'playlist_summary_label'):
                if playlist_names:
                    summary_lines = [f"- {name}" for name in playlist_names]
                    summary_text = "\n".join(summary_lines)
                else:
                    summary_text = "No playlists defined yet."
                self.playlist_summary_label.configure(text=summary_text)
        if hasattr(self, 'playlists_text'):
            self._reset_playlists_text()

        # Update weather controls
        if isinstance(self.weather_settings, dict):
            location = self.weather_settings.get("location", {}) or {}
            apply_on = set(self.weather_settings.get("apply_on", []) or [])
            if hasattr(self, 'weather_enabled_var'):
                self.weather_enabled_var.set(bool(self.weather_settings.get("enabled", False)))
            if hasattr(self, 'weather_provider_var'):
                self.weather_provider_var.set(str(self.weather_settings.get("provider", "openweathermap") or "openweathermap"))
            if hasattr(self, 'weather_api_key_var'):
                self.weather_api_key_var.set(str(self.weather_settings.get("api_key", "") or ""))
            if hasattr(self, 'weather_refresh_var'):
                self.weather_refresh_var.set(int(self.weather_settings.get("refresh_minutes", 30) or 30))
            if hasattr(self, 'weather_units_var'):
                self.weather_units_var.set(str(self.weather_settings.get("units", "metric") or "metric"))
            if hasattr(self, 'weather_city_var'):
                self.weather_city_var.set(str(location.get("city", "") or ""))
            if hasattr(self, 'weather_country_var'):
                self.weather_country_var.set(str(location.get("country", "") or ""))
            if hasattr(self, 'weather_lat_var'):
                latitude = location.get("latitude", "")
                self.weather_lat_var.set("" if latitude in (None, "") else str(latitude))
            if hasattr(self, 'weather_lon_var'):
                longitude = location.get("longitude", "")
                self.weather_lon_var.set("" if longitude in (None, "") else str(longitude))
            if hasattr(self, 'weather_apply_on_vars'):
                for trigger, var in self.weather_apply_on_vars.items():
                    var.set(trigger in apply_on)
        if hasattr(self, 'weather_conditions_text'):
            self._reset_weather_conditions_text()



def main() -> None:
    root = tk.Tk()
    app = WallpaperConfigGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
