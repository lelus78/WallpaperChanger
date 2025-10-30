import json
import os
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

        self.config_path = Path(__file__).parent / "config.py"
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

            # Parse basic settings (simplified parsing)
            self.config_data = {
                "Provider": self._extract_value(content, "Provider"),
                "ProvidersSequence": self._extract_list(content, "ProvidersSequence"),
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
                "Monitors": self._extract_monitors(content),
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

        # Tab 4: Logs
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
                     values=["wallhaven", "pexels"], width=30).grid(row=0, column=1, pady=2)

        ttk.Label(provider_group, text="Search Query:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.query_var = tk.StringVar(value=self.config_data.get("Query", "nature"))
        ttk.Entry(provider_group, textvariable=self.query_var, width=33).grid(row=1, column=1, pady=2)

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
        # Prominent "Change Wallpaper Now" button
        change_wallpaper_frame = tk.Frame(self.cache_frame, bg=self.COLORS['bg_primary'])
        change_wallpaper_frame.pack(fill=tk.X, padx=15, pady=15)

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

        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('WALLHAVEN_API_KEY='):
                        current_wallhaven_key = line.split('=', 1)[1].strip()
                    elif line.startswith('PEXELS_API_KEY='):
                        current_pexels_key = line.split('=', 1)[1].strip()

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

        ttk.Button(api_group, text="💾 Save API Keys", command=self._save_api_keys).grid(row=2, column=1, pady=10, sticky=tk.E)

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

            content = f"""# Wallhaven API Key from https://wallhaven.cc/settings/account
WALLHAVEN_API_KEY={wallhaven_key}

# Pexels API Key from https://www.pexels.com/api/new/
PEXELS_API_KEY={pexels_key}
"""
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(content)

            messagebox.showinfo("Success", "API Keys saved successfully to .env file!")
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
            pid_path = Path(__file__).parent / "wallpaperchanger.pid"

            if not pid_path.exists():
                messagebox.showwarning("App Not Running",
                    "The Wallpaper Changer app is not currently running.\n\n"
                    "Please start it first using:\n"
                    "• launchers/start_wallpaper_changer.vbs\n"
                    "• or 'python main.py'")
                return

            # Create signal file to trigger wallpaper change
            signal_path = Path(__file__).parent / "wallpaperchanger.signal"

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

            # Create signal file
            with open(signal_path, 'w') as f:
                f.write('change')

            # Wait for the change to happen
            self.root.after(2000, lambda: loading_window.destroy())
            self.root.after(2500, lambda: messagebox.showinfo("Success",
                "Wallpaper change triggered!\n\n"
                "Check the Logs tab for details."))

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

            # Update values
            new_lines = []
            in_monitors_section = False
            monitor_entry_counter = -1

            for line in lines:
                # Simple replacements
                if line.strip().startswith("Provider ="):
                    new_lines.append(f'Provider = "{self.provider_var.get()}"\n')
                elif line.strip().startswith("Query ="):
                    new_lines.append(f'Query = "{self.query_var.get()}"\n')
                elif line.strip().startswith("PurityLevel ="):
                    new_lines.append(f'PurityLevel = "{self.purity_var.get()}"\n')
                elif line.strip().startswith("ScreenResolution ="):
                    new_lines.append(f'ScreenResolution = "{self.resolution_var.get()}"\n')
                elif line.strip().startswith("WallhavenSorting ="):
                    new_lines.append(f'WallhavenSorting = "{self.sorting_var.get()}"\n')
                elif line.strip().startswith("WallhavenTopRange ="):
                    new_lines.append(f'WallhavenTopRange = "{self.toprange_var.get()}"\n')
                elif line.strip().startswith("PexelsMode ="):
                    new_lines.append(f'PexelsMode = "{self.pexels_mode_var.get()}"\n')
                elif line.strip().startswith("KeyBind ="):
                    new_lines.append(f'KeyBind = "{self.keybind_var.get()}"\n')
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
                    new_lines.append(f'    "directory": "{cache_path}",\n')
                elif line.strip().startswith("DefaultPreset ="):
                    default_preset = self.default_preset_var.get() if hasattr(self, 'default_preset_var') else "workspace"
                    new_lines.append(f'DefaultPreset = "{default_preset}"\n')
                # Monitor resolution updates
                elif line.strip().startswith("Monitors = ["):
                    in_monitors_section = True
                    monitor_entry_counter = -1
                    new_lines.append(line)
                elif in_monitors_section and line.strip() == "{":
                    monitor_entry_counter += 1
                    new_lines.append(line)
                elif in_monitors_section and '"screen_resolution":' in line and hasattr(self, 'monitor_resolution_vars'):
                    # Update resolution for this monitor
                    if monitor_entry_counter in self.monitor_resolution_vars:
                        resolution = self.monitor_resolution_vars[monitor_entry_counter].get()
                        indent = line[:len(line) - len(line.lstrip())]
                        new_lines.append(f'{indent}"screen_resolution": "{resolution}",\n')
                    else:
                        new_lines.append(line)
                elif in_monitors_section and line.strip() == "]":
                    in_monitors_section = False
                    new_lines.append(line)
                else:
                    new_lines.append(line)

            with open(self.config_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            # Save API keys separately
            if hasattr(self, 'wallhaven_key_var') and hasattr(self, 'pexels_key_var'):
                self._save_api_keys()

            messagebox.showinfo("Success", "Configuration saved successfully!\n\nRestart the application for changes to take effect.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")

    def _reload_config(self) -> None:
        """Reload configuration"""
        self._load_config()
        messagebox.showinfo("Success", "Configuration reloaded!")
        # Update UI elements
        self.provider_var.set(self.config_data.get("Provider", "wallhaven"))
        self.query_var.set(self.config_data.get("Query", "nature"))
        self.purity_var.set(self.config_data.get("PurityLevel", "100"))
        self.resolution_var.set(self.config_data.get("ScreenResolution", "1920x1080"))


def main() -> None:
    root = tk.Tk()
    app = WallpaperConfigGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
