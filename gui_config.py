import json
import os
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, scrolledtext
from typing import Any, Dict, List, Optional

from PIL import Image, ImageTk

from cache_manager import CacheManager
from config import CacheSettings


class WallpaperConfigGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Wallpaper Changer - Configuration")
        self.root.geometry("900x700")

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

        self._load_config()
        self._create_widgets()

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

    def _create_widgets(self) -> None:
        """Create GUI widgets"""
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab 1: Settings
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="⚙️ Settings")
        self._create_settings_tab()

        # Tab 2: Cache/Gallery
        self.cache_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.cache_frame, text="🖼️ Wallpaper Gallery")
        self._create_cache_tab()

        # Bottom buttons
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(button_frame, text="💾 Save Configuration", command=self._save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🔄 Reload Config", command=self._reload_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="❌ Close", command=self.root.quit).pack(side=tk.RIGHT, padx=5)

    def _create_settings_tab(self) -> None:
        """Create settings tab content"""
        # Create canvas with scrollbar
        canvas = tk.Canvas(self.settings_frame)
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

        # Hotkey Settings
        hotkey_group = ttk.LabelFrame(scrollable_frame, text="Hotkey Settings", padding=10)
        hotkey_group.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(hotkey_group, text="Hotkey:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.keybind_var = tk.StringVar(value=self.config_data.get("KeyBind", "ctrl+alt+w"))
        ttk.Entry(hotkey_group, textvariable=self.keybind_var, width=33).grid(row=0, column=1, pady=2)
        ttk.Label(hotkey_group, text="(e.g., ctrl+alt+w)").grid(row=0, column=2, sticky=tk.W, padx=5)

    def _create_cache_tab(self) -> None:
        """Create cache/gallery tab content"""
        # Top controls
        control_frame = ttk.Frame(self.cache_frame)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(control_frame, text="Select Monitor:").pack(side=tk.LEFT, padx=5)
        self.monitor_var = tk.StringVar(value="All Monitors")
        self.monitor_combo = ttk.Combobox(control_frame, textvariable=self.monitor_var, width=30)
        self.monitor_combo.pack(side=tk.LEFT, padx=5)

        ttk.Button(control_frame, text="🔄 Refresh Gallery", command=self._refresh_gallery).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="🗑️ Clear Cache", command=self._clear_cache).pack(side=tk.LEFT, padx=5)

        # Create canvas with scrollbar for gallery
        gallery_container = ttk.Frame(self.cache_frame)
        gallery_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.gallery_canvas = tk.Canvas(gallery_container, bg="#f0f0f0")
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

        # Load monitors
        self._load_monitors()

        # Load gallery
        self._refresh_gallery()

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

        # Create grid of thumbnails
        row = 0
        col = 0
        max_cols = 3

        print(f"Loading {len(entries)} wallpapers from cache...")
        for idx, entry in enumerate(entries[:30]):  # Show last 30
            print(f"Entry {idx}: {entry.get('path', 'NO PATH')}")
            self._create_thumbnail(entry, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def _create_thumbnail(self, entry: Dict[str, Any], row: int, col: int) -> None:
        """Create a thumbnail widget for a wallpaper"""
        frame = ttk.Frame(self.gallery_frame, relief=tk.RAISED, borderwidth=2)
        frame.grid(row=row, column=col, padx=5, pady=5, sticky=tk.NSEW)

        try:
            # Check if file exists
            image_path = entry.get("path", "")
            if not image_path or not os.path.exists(image_path):
                raise FileNotFoundError(f"Image not found: {image_path}")

            # Load and resize image
            img = Image.open(image_path)
            img.thumbnail((250, 150), Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)

            # Image label
            img_label = ttk.Label(frame, image=photo)
            img_label.image = photo  # Keep reference
            img_label.pack(padx=5, pady=5)

            # Info label
            info_text = entry.get("source_info", "Unknown")[:40]
            ttk.Label(frame, text=info_text, wraplength=230).pack()

            # Apply button
            apply_btn = ttk.Button(frame, text="Apply to Selected Monitor",
                                  command=lambda e=entry: self._apply_wallpaper(e))
            apply_btn.pack(pady=5)

        except Exception as e:
            ttk.Label(frame, text=f"Error loading image:\n{str(e)[:50]}",
                     wraplength=230, foreground="red").pack(pady=10)

    def _apply_wallpaper(self, entry: Dict[str, Any]) -> None:
        """Apply selected wallpaper to monitor"""
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
                monitor_idx = int(monitor_selection.split()[1]) - 1

                manager = DesktopWallpaperController()
                monitors = manager.enumerate_monitors()

                if monitor_idx < len(monitors):
                    manager.set_wallpaper(monitors[monitor_idx]["id"], wallpaper_path)
                    manager.close()
                    messagebox.showinfo("Success", f"Wallpaper applied to {monitor_selection}!")
                else:
                    manager.close()
                    messagebox.showerror("Error", "Invalid monitor selection")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply wallpaper: {e}")

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
                elif '"max_items":' in line and "CacheSettings" in "".join(new_lines[-10:]):
                    new_lines.append(f'    "max_items": {self.cache_max_var.get()},\n')
                elif '"enable_offline_rotation":' in line:
                    new_lines.append(f'    "enable_offline_rotation": {self.cache_offline_var.get()},\n')
                else:
                    new_lines.append(line)

            with open(self.config_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

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
