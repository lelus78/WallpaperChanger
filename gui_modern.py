"""
Modern GUI for Wallpaper Changer using CustomTkinter
Inspired by contemporary wallpaper applications with sidebar navigation
"""
import os
import sys
import subprocess
import signal
import customtkinter as ctk
from pathlib import Path
from PIL import Image, ImageTk
from typing import Dict, Any, List, Optional
import tkinter as tk

from cache_manager import CacheManager
from config import CacheSettings


# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ModernWallpaperGUI:
    """Modern CustomTkinter-based GUI for Wallpaper Changer"""

    # Modern color palette matching the reference image
    COLORS = {
        'sidebar_bg': '#C41E3A',  # Red sidebar like reference
        'sidebar_hover': '#A01828',
        'main_bg': '#2B1B2D',  # Dark purple/burgundy background
        'card_bg': '#3D2B3F',
        'card_hover': '#4D3B4F',
        'accent': '#E94560',
        'text_light': '#FFFFFF',
        'text_muted': '#B0B0B0',
        'warning': '#FFD93D',
    }

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Wallpaper Changer")
        self.root.geometry("1400x900")

        # Configure grid layout
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # Initialize cache manager
        cache_dir = CacheSettings.get("directory") or os.path.join(
            os.path.expanduser("~"), "WallpaperChangerCache"
        )
        self.cache_manager = CacheManager(
            cache_dir,
            max_items=int(CacheSettings.get("max_items", 60)),
            enable_rotation=bool(CacheSettings.get("enable_offline_rotation", True)),
        )

        # Thumbnail cache
        self.thumbnail_cache = {}

        # Main app process
        self.main_process = None
        self.pid_file = Path(__file__).parent / "wallpaperchanger.pid"
        self.signal_file = Path(__file__).parent / "wallpaperchanger.signal"

        # Start main wallpaper service
        self._ensure_service_running()

        # Create UI
        self._create_sidebar()
        self._create_main_content()

        # Setup cleanup on close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_sidebar(self):
        """Create modern sidebar with navigation"""
        self.sidebar = ctk.CTkFrame(
            self.root,
            width=200,
            corner_radius=0,
            fg_color=self.COLORS['sidebar_bg']
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)

        # Logo/Title
        title_label = ctk.CTkLabel(
            self.sidebar,
            text="WALLPAPER\nCHANGER",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.COLORS['text_light']
        )
        title_label.grid(row=0, column=0, padx=20, pady=(30, 40))

        # Navigation buttons with icons (text-based for now)
        nav_items = [
            ("Home", "🏠"),
            ("Wallpapers", "🖼️"),
            ("Settings", "⚙️"),
            ("Logs", "📋"),
        ]

        self.nav_buttons = []
        for idx, (text, icon) in enumerate(nav_items, start=1):
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"  {text}",
                font=ctk.CTkFont(size=14),
                fg_color="transparent",
                text_color=self.COLORS['text_light'],
                hover_color=self.COLORS['sidebar_hover'],
                anchor="w",
                height=45,
                corner_radius=8,
                command=lambda t=text: self._navigate(t)
            )
            btn.grid(row=idx, column=0, padx=15, pady=5, sticky="ew")
            self.nav_buttons.append(btn)

        # Set "Wallpapers" as active by default
        self.active_view = "Wallpapers"
        self._update_nav_buttons()

    def _create_main_content(self):
        """Create main content area"""
        # Main container
        self.main_frame = ctk.CTkFrame(
            self.root,
            corner_radius=0,
            fg_color=self.COLORS['main_bg']
        )
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Content container that will be swapped
        self.content_container = ctk.CTkFrame(
            self.main_frame,
            corner_radius=0,
            fg_color="transparent"
        )
        self.content_container.grid(row=0, column=0, sticky="nsew")
        self.content_container.grid_rowconfigure(1, weight=1)
        self.content_container.grid_columnconfigure(0, weight=1)

        # Show wallpapers view by default
        self._show_wallpapers_view()

    def _create_header(self):
        """Create header with search and filters"""
        header = ctk.CTkFrame(
            self.main_frame,
            height=80,
            corner_radius=0,
            fg_color="transparent"
        )
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 0))
        header.grid_columnconfigure(1, weight=1)

        # Title
        title = ctk.CTkLabel(
            header,
            text="Wallpaper Gallery",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.COLORS['text_light']
        )
        title.grid(row=0, column=0, sticky="w", padx=10)

        # Filter dropdown
        filter_frame = ctk.CTkFrame(header, fg_color="transparent")
        filter_frame.grid(row=0, column=2, sticky="e", padx=10)

        ctk.CTkLabel(
            filter_frame,
            text="Sort:",
            text_color=self.COLORS['text_muted'],
            font=ctk.CTkFont(size=13)
        ).pack(side="left", padx=(0, 10))

        self.sort_var = ctk.StringVar(value="Newest First")
        sort_menu = ctk.CTkOptionMenu(
            filter_frame,
            variable=self.sort_var,
            values=["Newest First", "Oldest First", "Highest Resolution"],
            width=150,
            fg_color=self.COLORS['card_bg'],
            button_color=self.COLORS['accent'],
            button_hover_color=self.COLORS['sidebar_hover'],
            command=self._on_sort_change
        )
        sort_menu.pack(side="left")

    def _show_wallpapers_view(self):
        """Show wallpapers gallery view"""
        # Header with controls
        header = ctk.CTkFrame(
            self.content_container,
            height=80,
            corner_radius=0,
            fg_color="transparent"
        )
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 0))
        header.grid_columnconfigure(1, weight=1)

        # Title
        title = ctk.CTkLabel(
            header,
            text="Wallpaper Gallery",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.COLORS['text_light']
        )
        title.grid(row=0, column=0, sticky="w", padx=10)

        # Filter dropdown
        filter_frame = ctk.CTkFrame(header, fg_color="transparent")
        filter_frame.grid(row=0, column=2, sticky="e", padx=10)

        ctk.CTkLabel(
            filter_frame,
            text="Sort:",
            text_color=self.COLORS['text_muted'],
            font=ctk.CTkFont(size=13)
        ).pack(side="left", padx=(0, 10))

        self.sort_var = ctk.StringVar(value="Newest First")
        sort_menu = ctk.CTkOptionMenu(
            filter_frame,
            variable=self.sort_var,
            values=["Newest First", "Oldest First", "Highest Resolution"],
            width=150,
            fg_color=self.COLORS['card_bg'],
            button_color=self.COLORS['accent'],
            button_hover_color=self.COLORS['sidebar_hover'],
            command=self._on_sort_change
        )
        sort_menu.pack(side="left")

        # Scrollable frame for wallpaper grid
        scrollable_frame = ctk.CTkScrollableFrame(
            self.content_container,
            corner_radius=0,
            fg_color="transparent"
        )
        scrollable_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)

        # Configure grid for wallpaper cards (3 columns, fixed width to prevent stretching)
        for i in range(3):
            scrollable_frame.grid_columnconfigure(i, weight=0, minsize=360)

        # Load wallpapers from cache
        if not self.cache_manager or not self.cache_manager.has_items():
            # Show empty state
            empty_label = ctk.CTkLabel(
                scrollable_frame,
                text="No wallpapers in cache.\nDownload some wallpapers first!",
                font=ctk.CTkFont(size=16),
                text_color=self.COLORS['text_muted']
            )
            empty_label.grid(row=0, column=0, columnspan=4, pady=100)
            return

        # Get cached items
        items = self.cache_manager.list_entries()

        # Create cards in grid (3 columns)
        for idx, item in enumerate(items[:30]):  # Show up to 30 wallpapers
            row = idx // 3
            col = idx % 3
            self._create_wallpaper_card(item, row, col, scrollable_frame)

    def _create_wallpaper_card(self, item: Dict[str, Any], row: int, col: int, parent):
        """Create a modern wallpaper card with rounded corners"""
        # Card container - FIXED: removed sticky to prevent horizontal stretching
        card = ctk.CTkFrame(
            parent,
            fg_color=self.COLORS['card_bg'],
            corner_radius=15,
            border_width=0,
            width=340,
            height=320
        )
        card.grid(row=row, column=col, padx=10, pady=10)
        card.grid_propagate(False)  # Prevent card from shrinking

        try:
            # Load image
            image_path = item.get("path", "")
            if not os.path.exists(image_path):
                raise FileNotFoundError()

            # Check cache
            if image_path in self.thumbnail_cache:
                photo, original_size = self.thumbnail_cache[image_path]
            else:
                img = Image.open(image_path)
                original_size = img.size
                # Create larger thumbnail
                img.thumbnail((320, 200), Image.Resampling.LANCZOS)
                photo = ctk.CTkImage(light_image=img, dark_image=img, size=(320, 200))
                self.thumbnail_cache[image_path] = (photo, original_size)

            # Image label with rounded appearance
            img_label = ctk.CTkLabel(
                card,
                image=photo,
                text="",
                width=320,
                height=200
            )
            img_label.pack(padx=10, pady=10, fill="both", expand=False)

            # Info section
            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(fill="x", padx=15, pady=(0, 10))

            # Resolution badge
            resolution_text = f"{original_size[0]}x{original_size[1]}"
            resolution_badge = ctk.CTkLabel(
                info_frame,
                text=resolution_text,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=self.COLORS['text_light'],
                fg_color=self.COLORS['accent'],
                corner_radius=6,
                padx=10,
                pady=4
            )
            resolution_badge.pack(side="left", padx=(0, 5))

            # Provider badge
            provider = item.get("provider", "Unknown").upper()
            provider_colors = {
                'WALLHAVEN': '#00e676',
                'PEXELS': '#ffd93d',
                'REDDIT': '#ff6b81',
                'UNSPLASH': '#89b4fa',
            }
            provider_color = provider_colors.get(provider, '#808080')

            provider_badge = ctk.CTkLabel(
                info_frame,
                text=provider,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color='#000000',
                fg_color=provider_color,
                corner_radius=6,
                padx=10,
                pady=4
            )
            provider_badge.pack(side="left")

            # Apply button
            apply_btn = ctk.CTkButton(
                card,
                text="SET AS WALLPAPER",
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color=self.COLORS['accent'],
                hover_color=self.COLORS['sidebar_hover'],
                corner_radius=10,
                height=40,
                command=lambda i=item: self._apply_wallpaper(i)
            )
            apply_btn.pack(fill="x", padx=15, pady=(0, 15))

        except Exception as e:
            error_label = ctk.CTkLabel(
                card,
                text=f"Error loading\nimage",
                font=ctk.CTkFont(size=12),
                text_color=self.COLORS['text_muted']
            )
            error_label.pack(expand=True, pady=50)

    def _navigate(self, view: str):
        """Handle navigation"""
        self.active_view = view
        self._update_nav_buttons()

        # Clear current content
        for widget in self.content_container.winfo_children():
            widget.destroy()

        # Show appropriate view
        if view == "Home":
            self._show_home_view()
        elif view == "Wallpapers":
            self._show_wallpapers_view()
        elif view == "Settings":
            self._show_settings_view()
        elif view == "Logs":
            self._show_logs_view()

    def _update_nav_buttons(self):
        """Update navigation button styles"""
        for btn in self.nav_buttons:
            if btn.cget("text").strip() == self.active_view:
                btn.configure(fg_color=self.COLORS['sidebar_hover'])
            else:
                btn.configure(fg_color="transparent")

    def _on_sort_change(self, choice: str):
        """Handle sort change"""
        print(f"Sort changed to: {choice}")
        # TODO: Re-sort and reload wallpapers

    def _show_home_view(self):
        """Show home/dashboard view"""
        title = ctk.CTkLabel(
            self.content_container,
            text="Welcome to Wallpaper Changer",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color=self.COLORS['text_light']
        )
        title.pack(pady=(50, 20))

        subtitle = ctk.CTkLabel(
            self.content_container,
            text="Manage and customize your desktop wallpapers",
            font=ctk.CTkFont(size=16),
            text_color=self.COLORS['text_muted']
        )
        subtitle.pack(pady=(0, 40))

        # Quick action buttons
        btn_frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
        btn_frame.pack(pady=20)

        change_btn = ctk.CTkButton(
            btn_frame,
            text="CHANGE WALLPAPER NOW",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=self.COLORS['accent'],
            hover_color=self.COLORS['sidebar_hover'],
            corner_radius=12,
            height=50,
            width=300,
            command=self._change_wallpaper_now
        )
        change_btn.pack(pady=10)

        gallery_btn = ctk.CTkButton(
            btn_frame,
            text="Browse Gallery",
            font=ctk.CTkFont(size=14),
            fg_color=self.COLORS['card_bg'],
            hover_color=self.COLORS['card_hover'],
            corner_radius=12,
            height=45,
            width=300,
            command=lambda: self._navigate("Wallpapers")
        )
        gallery_btn.pack(pady=10)

    def _show_settings_view(self):
        """Show fully editable settings"""
        scrollable = ctk.CTkScrollableFrame(
            self.content_container,
            fg_color="transparent"
        )
        scrollable.pack(fill="both", expand=True, padx=20, pady=20)

        title = ctk.CTkLabel(
            scrollable,
            text="Settings",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.COLORS['text_light']
        )
        title.pack(pady=(10, 20), anchor="w")

        # Load current config
        from config import (Provider, RotateProviders, Query, PurityLevel, ScreenResolution,
                           WallhavenSorting, WallhavenTopRange, PexelsMode, RedditSettings,
                           SchedulerSettings, CacheSettings, KeyBind)

        # Initialize setting variables
        self.provider_var = ctk.StringVar(value=Provider)
        self.rotate_providers_var = ctk.BooleanVar(value=RotateProviders)
        self.query_var = ctk.StringVar(value=Query)
        self.purity_var = ctk.StringVar(value=PurityLevel)
        self.resolution_var = ctk.StringVar(value=ScreenResolution)
        self.sorting_var = ctk.StringVar(value=WallhavenSorting)
        self.toprange_var = ctk.StringVar(value=WallhavenTopRange)
        self.pexels_mode_var = ctk.StringVar(value=PexelsMode)

        # Reddit settings
        reddit_subreddits = ", ".join(RedditSettings.get("subreddits", ["wallpapers"]))
        self.reddit_subreddits_var = ctk.StringVar(value=reddit_subreddits)
        self.reddit_sort_var = ctk.StringVar(value=RedditSettings.get("sort", "hot"))
        self.reddit_time_var = ctk.StringVar(value=RedditSettings.get("time_filter", "day"))
        self.reddit_limit_var = ctk.IntVar(value=RedditSettings.get("limit", 60))
        self.reddit_score_var = ctk.IntVar(value=RedditSettings.get("min_score", 0))
        self.reddit_nsfw_var = ctk.BooleanVar(value=RedditSettings.get("allow_nsfw", False))

        # Scheduler settings
        self.scheduler_enabled_var = ctk.BooleanVar(value=SchedulerSettings.get("enabled", True))
        self.interval_var = ctk.IntVar(value=SchedulerSettings.get("interval_minutes", 45))
        self.jitter_var = ctk.IntVar(value=SchedulerSettings.get("jitter_minutes", 10))

        # Cache settings
        self.cache_max_var = ctk.IntVar(value=CacheSettings.get("max_items", 60))
        self.cache_offline_var = ctk.BooleanVar(value=CacheSettings.get("enable_offline_rotation", True))

        # Hotkey
        self.keybind_var = ctk.StringVar(value=KeyBind)

        # Provider Settings
        provider_section = self._create_section(scrollable, "Provider Settings")
        self._add_setting_row(provider_section, "Default Provider:", "dropdown", self.provider_var,
                            ["wallhaven", "pexels", "reddit"])
        self._add_setting_row(provider_section, "Search Query:", "entry", self.query_var)
        self._add_setting_row(provider_section, "Enable Provider Rotation", "checkbox", self.rotate_providers_var)

        # Wallhaven Settings
        wallhaven_section = self._create_section(scrollable, "Wallhaven Settings")
        self._add_setting_row(wallhaven_section, "Purity Level:", "dropdown", self.purity_var,
                            ["100", "110", "111", "010", "001"])
        self._add_setting_row(wallhaven_section, "Min Resolution:", "dropdown", self.resolution_var,
                            ["1920x1080", "2560x1440", "3440x1440", "3840x2160"])
        self._add_setting_row(wallhaven_section, "Sorting:", "dropdown", self.sorting_var,
                            ["random", "toplist", "favorites", "views"])
        self._add_setting_row(wallhaven_section, "Top Range:", "dropdown", self.toprange_var,
                            ["1d", "3d", "1w", "1M", "3M", "6M", "1y"])

        # Pexels Settings
        pexels_section = self._create_section(scrollable, "Pexels Settings")
        self._add_setting_row(pexels_section, "Mode:", "dropdown", self.pexels_mode_var,
                            ["search", "curated"])

        # Reddit Settings
        reddit_section = self._create_section(scrollable, "Reddit Settings")
        self._add_setting_row(reddit_section, "Subreddits (comma separated):", "entry", self.reddit_subreddits_var)
        self._add_setting_row(reddit_section, "Sort:", "dropdown", self.reddit_sort_var,
                            ["hot", "new", "rising", "top", "controversial"])
        self._add_setting_row(reddit_section, "Time Filter:", "dropdown", self.reddit_time_var,
                            ["hour", "day", "week", "month", "year", "all"])
        self._add_setting_row(reddit_section, "Posts per fetch:", "spinbox", self.reddit_limit_var, [10, 100])
        self._add_setting_row(reddit_section, "Minimum upvotes:", "spinbox", self.reddit_score_var, [0, 100000])
        self._add_setting_row(reddit_section, "Include NSFW posts", "checkbox", self.reddit_nsfw_var)

        # Scheduler Settings
        scheduler_section = self._create_section(scrollable, "Scheduler Settings")
        self._add_setting_row(scheduler_section, "Enable Scheduler", "checkbox", self.scheduler_enabled_var)
        self._add_setting_row(scheduler_section, "Interval (minutes):", "spinbox", self.interval_var, [1, 1440])
        self._add_setting_row(scheduler_section, "Jitter (minutes):", "spinbox", self.jitter_var, [0, 60])

        # Cache Settings
        cache_section = self._create_section(scrollable, "Cache Settings")
        self._add_setting_row(cache_section, "Max Cache Items:", "spinbox", self.cache_max_var, [10, 500])
        self._add_setting_row(cache_section, "Enable Offline Rotation", "checkbox", self.cache_offline_var)

        # Hotkey Settings
        hotkey_section = self._create_section(scrollable, "Hotkey Settings")
        self._add_setting_row(hotkey_section, "Hotkey:", "entry", self.keybind_var)

        # Save button
        save_btn = ctk.CTkButton(
            scrollable,
            text="SAVE SETTINGS",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=self.COLORS['accent'],
            hover_color=self.COLORS['sidebar_hover'],
            corner_radius=10,
            height=45,
            command=self._save_settings
        )
        save_btn.pack(fill="x", pady=(20, 10))

    def _create_section(self, parent, title):
        """Create a settings section frame"""
        section_frame = ctk.CTkFrame(parent, fg_color=self.COLORS['card_bg'], corner_radius=12)
        section_frame.pack(fill="x", pady=10, padx=5)

        section_label = ctk.CTkLabel(
            section_frame,
            text=title,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.COLORS['text_light']
        )
        section_label.pack(pady=15, padx=20, anchor="w")

        return section_frame

    def _add_setting_row(self, section_frame, label_text, widget_type, variable, options=None):
        """Add a setting row with label and widget"""
        row_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
        row_frame.pack(fill="x", padx=20, pady=8)

        if widget_type == "checkbox":
            # Checkbox with label inside
            checkbox = ctk.CTkCheckBox(
                row_frame,
                text=label_text,
                variable=variable,
                fg_color=self.COLORS['accent'],
                hover_color=self.COLORS['sidebar_hover'],
                checkmark_color=self.COLORS['text_light'],
                text_color=self.COLORS['text_light'],
                font=ctk.CTkFont(size=13)
            )
            checkbox.pack(side="left", anchor="w")
        else:
            # Label on left
            label = ctk.CTkLabel(
                row_frame,
                text=label_text,
                text_color=self.COLORS['text_light'],
                font=ctk.CTkFont(size=13),
                width=250
            )
            label.pack(side="left", anchor="w")

            # Widget on right
            if widget_type == "entry":
                widget = ctk.CTkEntry(
                    row_frame,
                    textvariable=variable,
                    width=300,
                    fg_color=self.COLORS['card_hover'],
                    border_color=self.COLORS['accent'],
                    text_color=self.COLORS['text_light']
                )
                widget.pack(side="right", anchor="e")

            elif widget_type == "dropdown":
                widget = ctk.CTkComboBox(
                    row_frame,
                    variable=variable,
                    values=options,
                    width=300,
                    fg_color=self.COLORS['card_hover'],
                    border_color=self.COLORS['accent'],
                    button_color=self.COLORS['accent'],
                    text_color=self.COLORS['text_light'],
                    dropdown_fg_color=self.COLORS['card_bg']
                )
                widget.pack(side="right", anchor="e")

            elif widget_type == "spinbox":
                from_, to = options
                spinbox_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
                spinbox_frame.pack(side="right", anchor="e")

                entry = ctk.CTkEntry(
                    spinbox_frame,
                    textvariable=variable,
                    width=200,
                    fg_color=self.COLORS['card_hover'],
                    border_color=self.COLORS['accent'],
                    text_color=self.COLORS['text_light']
                )
                entry.pack(side="left", padx=(0, 5))

                btn_frame = ctk.CTkFrame(spinbox_frame, fg_color="transparent")
                btn_frame.pack(side="left")

                def increment():
                    try:
                        val = variable.get()
                        if val < to:
                            variable.set(val + 1)
                    except:
                        variable.set(from_)

                def decrement():
                    try:
                        val = variable.get()
                        if val > from_:
                            variable.set(val - 1)
                    except:
                        variable.set(from_)

                up_btn = ctk.CTkButton(
                    btn_frame,
                    text="▲",
                    width=40,
                    height=25,
                    fg_color=self.COLORS['accent'],
                    hover_color=self.COLORS['sidebar_hover'],
                    command=increment
                )
                up_btn.pack(side="left", padx=2)

                down_btn = ctk.CTkButton(
                    btn_frame,
                    text="▼",
                    width=40,
                    height=25,
                    fg_color=self.COLORS['accent'],
                    hover_color=self.COLORS['sidebar_hover'],
                    command=decrement
                )
                down_btn.pack(side="left", padx=2)

    def _save_settings(self):
        """Save all settings to config.py"""
        try:
            config_path = Path(__file__).parent / "config.py"

            # Read current config
            with open(config_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Update values in config
            new_lines = []
            for line in lines:
                if line.startswith('Provider = '):
                    new_lines.append(f'Provider = "{self.provider_var.get()}"\n')
                elif line.startswith('RotateProviders = '):
                    new_lines.append(f'RotateProviders = {self.rotate_providers_var.get()}\n')
                elif line.startswith('Query = '):
                    new_lines.append(f'Query = "{self.query_var.get()}"\n')
                elif line.startswith('PurityLevel = '):
                    new_lines.append(f'PurityLevel = "{self.purity_var.get()}"\n')
                elif line.startswith('ScreenResolution = '):
                    new_lines.append(f'ScreenResolution = "{self.resolution_var.get()}"\n')
                elif line.startswith('WallhavenSorting = '):
                    new_lines.append(f'WallhavenSorting = "{self.sorting_var.get()}"\n')
                elif line.startswith('WallhavenTopRange = '):
                    new_lines.append(f'WallhavenTopRange = "{self.toprange_var.get()}"\n')
                elif line.startswith('PexelsMode = '):
                    new_lines.append(f'PexelsMode = "{self.pexels_mode_var.get()}"\n')
                elif line.startswith('KeyBind = '):
                    new_lines.append(f'KeyBind = "{self.keybind_var.get()}"\n')
                elif '"subreddits":' in line:
                    subreddits = [s.strip() for s in self.reddit_subreddits_var.get().split(',')]
                    new_lines.append(f'    "subreddits": {subreddits},\n')
                elif '"sort":' in line and 'RedditSettings' in ''.join(new_lines[-5:]):
                    new_lines.append(f'    "sort": "{self.reddit_sort_var.get()}",\n')
                elif '"time_filter":' in line:
                    new_lines.append(f'    "time_filter": "{self.reddit_time_var.get()}",\n')
                elif '"limit":' in line and 'RedditSettings' in ''.join(new_lines[-10:]):
                    new_lines.append(f'    "limit": {self.reddit_limit_var.get()},\n')
                elif '"min_score":' in line:
                    new_lines.append(f'    "min_score": {self.reddit_score_var.get()},\n')
                elif '"allow_nsfw":' in line:
                    new_lines.append(f'    "allow_nsfw": {self.reddit_nsfw_var.get()},\n')
                elif '"enabled":' in line and 'SchedulerSettings' in ''.join(new_lines[-5:]):
                    new_lines.append(f'    "enabled": {self.scheduler_enabled_var.get()},\n')
                elif '"interval_minutes":' in line:
                    new_lines.append(f'    "interval_minutes": {self.interval_var.get()},\n')
                elif '"jitter_minutes":' in line:
                    new_lines.append(f'    "jitter_minutes": {self.jitter_var.get()},\n')
                elif '"max_items":' in line:
                    new_lines.append(f'    "max_items": {self.cache_max_var.get()},\n')
                elif '"enable_offline_rotation":' in line:
                    new_lines.append(f'    "enable_offline_rotation": {self.cache_offline_var.get()},\n')
                else:
                    new_lines.append(line)

            # Write updated config
            with open(config_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)

            # Show success message
            success_dialog = ctk.CTkToplevel(self.root)
            success_dialog.title("Settings Saved")
            success_dialog.geometry("400x150")
            success_dialog.transient(self.root)
            success_dialog.grab_set()

            msg = ctk.CTkLabel(
                success_dialog,
                text="Settings saved successfully!\nRestart the wallpaper service for changes to take effect.",
                font=ctk.CTkFont(size=13),
                text_color=self.COLORS['text_light']
            )
            msg.pack(pady=30)

            ok_btn = ctk.CTkButton(
                success_dialog,
                text="OK",
                fg_color=self.COLORS['accent'],
                command=success_dialog.destroy
            )
            ok_btn.pack(pady=10)

        except Exception as e:
            error_dialog = ctk.CTkToplevel(self.root)
            error_dialog.title("Error")
            error_dialog.geometry("400x150")
            error_dialog.transient(self.root)
            error_dialog.grab_set()

            msg = ctk.CTkLabel(
                error_dialog,
                text=f"Failed to save settings:\n{str(e)}",
                font=ctk.CTkFont(size=13),
                text_color=self.COLORS['warning']
            )
            msg.pack(pady=30)

            ok_btn = ctk.CTkButton(
                error_dialog,
                text="OK",
                fg_color=self.COLORS['accent'],
                command=error_dialog.destroy
            )
            ok_btn.pack(pady=10)

    def _show_logs_view(self):
        """Show logs view"""
        title = ctk.CTkLabel(
            self.content_container,
            text="Application Logs",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.COLORS['text_light']
        )
        title.pack(pady=(20, 10), padx=20, anchor="w")

        # Buttons frame
        btn_frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 10))

        refresh_btn = ctk.CTkButton(
            btn_frame,
            text="Refresh Logs",
            width=120,
            height=32,
            fg_color=self.COLORS['accent'],
            hover_color=self.COLORS['sidebar_hover'],
            corner_radius=8,
            command=self._refresh_logs
        )
        refresh_btn.pack(side="left", padx=(0, 10))

        clear_btn = ctk.CTkButton(
            btn_frame,
            text="Clear Display",
            width=120,
            height=32,
            fg_color=self.COLORS['card_bg'],
            hover_color=self.COLORS['card_hover'],
            corner_radius=8,
            command=self._clear_log_display
        )
        clear_btn.pack(side="left")

        # Log text area
        log_frame = ctk.CTkFrame(self.content_container, fg_color=self.COLORS['card_bg'], corner_radius=12)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.log_textbox = ctk.CTkTextbox(
            log_frame,
            fg_color=self.COLORS['main_bg'],
            text_color=self.COLORS['text_light'],
            border_width=0,
            corner_radius=8,
            font=ctk.CTkFont(family="Consolas", size=11)
        )
        self.log_textbox.pack(fill="both", expand=True, padx=15, pady=15)

        # Load logs
        self._load_logs()

    def _open_full_settings(self):
        """Open the full settings GUI"""
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        gui_script = os.path.join(script_dir, "gui_config.py")
        try:
            subprocess.Popen(["pythonw", gui_script], shell=False)
        except Exception as e:
            print(f"Failed to open settings GUI: {e}")

    def _load_logs(self):
        """Load logs from wallpaperchanger.log"""
        log_file = Path(__file__).parent / "wallpaperchanger.log"
        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    # Show last 500 lines
                    recent_lines = lines[-500:]
                    self.log_textbox.delete("1.0", "end")
                    self.log_textbox.insert("1.0", "".join(recent_lines))
                    self.log_textbox.see("end")  # Scroll to bottom
            except Exception as e:
                self.log_textbox.delete("1.0", "end")
                self.log_textbox.insert("1.0", f"Error loading logs: {e}")
        else:
            self.log_textbox.delete("1.0", "end")
            self.log_textbox.insert("1.0", "No log file found.\n\nLogs will appear here when the wallpaper service is running.")

    def _refresh_logs(self):
        """Refresh the log display"""
        self._load_logs()

    def _clear_log_display(self):
        """Clear the log display"""
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.insert("1.0", "Log display cleared. Click 'Refresh Logs' to reload.")

    def _ensure_service_running(self):
        """Ensure main wallpaper service is running"""
        # Check if already running
        if self.pid_file.exists():
            try:
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                # Check if process is still alive
                import psutil
                if psutil.pid_exists(pid):
                    print(f"Service already running (PID: {pid})")
                    return
            except:
                pass

        # Start the service
        try:
            main_script = Path(__file__).parent / "main.py"
            self.main_process = subprocess.Popen(
                [sys.executable, str(main_script)],
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            print(f"Started wallpaper service (PID: {self.main_process.pid})")
        except Exception as e:
            print(f"Error starting service: {e}")

    def _change_wallpaper_now(self):
        """Trigger wallpaper change via signal file"""
        try:
            # Create signal file to trigger change
            with open(self.signal_file, 'w') as f:
                f.write('change')
            print("Wallpaper change requested")
        except Exception as e:
            print(f"Error requesting wallpaper change: {e}")

    def _apply_wallpaper(self, item: Dict[str, Any]):
        """Apply selected wallpaper - simplified version"""
        print(f"Applying wallpaper: {item.get('path')}")
        # For now, just trigger a change - could be enhanced to apply specific wallpaper
        self._change_wallpaper_now()

    def _on_closing(self):
        """Handle window closing"""
        # Don't stop the service - let it run in background
        self.root.destroy()

    def run(self):
        """Start the GUI"""
        self.root.mainloop()


def main():
    app = ModernWallpaperGUI()
    app.run()


if __name__ == "__main__":
    main()
