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
        self.main_frame.grid_rowconfigure(0, weight=1)  # Changed from row 1 to row 0
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Content container that will be swapped
        self.content_container = ctk.CTkFrame(
            self.main_frame,
            corner_radius=0,
            fg_color="transparent"
        )
        self.content_container.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.content_container.grid_rowconfigure(0, weight=0)  # Header row - no expansion
        self.content_container.grid_rowconfigure(1, weight=1)  # Content row - expands
        self.content_container.grid_columnconfigure(0, weight=1)  # Make content expand horizontally

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
        """Show enhanced home/dashboard view with statistics and info"""
        # Main scrollable container
        scrollable = ctk.CTkScrollableFrame(
            self.content_container,
            fg_color="transparent"
        )
        scrollable.pack(fill="both", expand=True, padx=20, pady=20)

        # Welcome header
        title = ctk.CTkLabel(
            scrollable,
            text="Dashboard",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=self.COLORS['text_light']
        )
        title.pack(pady=(10, 5), anchor="w")

        subtitle = ctk.CTkLabel(
            scrollable,
            text="Overview of your wallpaper system",
            font=ctk.CTkFont(size=14),
            text_color=self.COLORS['text_muted']
        )
        subtitle.pack(pady=(0, 20), anchor="w")

        # Statistics cards row
        stats_frame = ctk.CTkFrame(scrollable, fg_color="transparent")
        stats_frame.pack(fill="x", pady=10)

        # Configure grid for 3 cards
        for i in range(3):
            stats_frame.grid_columnconfigure(i, weight=1)

        # Service Status Card
        self._create_stat_card(stats_frame, 0, "Service Status",
                              self._get_service_status_text(),
                              self._get_service_status_color())

        # Cache Size Card
        cache_count = len(self.cache_manager.list_entries()) if self.cache_manager else 0
        self._create_stat_card(stats_frame, 1, "Cached Wallpapers",
                              f"{cache_count} images",
                              self.COLORS['accent'])

        # Weather Card
        weather_text = self._get_current_weather_text()
        self._create_stat_card(stats_frame, 2, "Current Weather",
                              weather_text,
                              "#00b4d8")

        # Quick Actions Section
        actions_label = ctk.CTkLabel(
            scrollable,
            text="Quick Actions",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.COLORS['text_light']
        )
        actions_label.pack(pady=(30, 15), anchor="w")

        # Actions grid - 2 columns
        actions_grid = ctk.CTkFrame(scrollable, fg_color="transparent")
        actions_grid.pack(fill="x", pady=10)
        actions_grid.grid_columnconfigure(0, weight=1)
        actions_grid.grid_columnconfigure(1, weight=1)

        # Action cards
        self._create_action_card(actions_grid, 0, 0,
                                "Change Wallpaper",
                                "Get a new wallpaper now",
                                self.COLORS['accent'],
                                self._change_wallpaper_now)

        self._create_action_card(actions_grid, 0, 1,
                                "Browse Gallery",
                                "View cached wallpapers",
                                self.COLORS['card_bg'],
                                lambda: self._navigate("Wallpapers"))

        self._create_action_card(actions_grid, 1, 0,
                                "Configure Settings",
                                "Adjust preferences",
                                self.COLORS['card_bg'],
                                lambda: self._navigate("Settings"))

        self._create_action_card(actions_grid, 1, 1,
                                "View Logs",
                                "Check system activity",
                                self.COLORS['card_bg'],
                                lambda: self._navigate("Logs"))

        # Recent Activity Section
        activity_label = ctk.CTkLabel(
            scrollable,
            text="System Information",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.COLORS['text_light']
        )
        activity_label.pack(pady=(30, 15), anchor="w")

        # Info card
        info_card = ctk.CTkFrame(scrollable, fg_color=self.COLORS['card_bg'], corner_radius=12)
        info_card.pack(fill="x", pady=10)

        # Read current settings
        from config import Provider, RotateProviders, SchedulerSettings

        info_items = [
            ("Active Provider", Provider.upper()),
            ("Provider Rotation", "Enabled" if RotateProviders else "Disabled"),
            ("Auto-Change", "Enabled" if SchedulerSettings.get("enabled") else "Disabled"),
            ("Change Interval", f"{SchedulerSettings.get('interval_minutes', 45)} minutes"),
        ]

        for label, value in info_items:
            item_frame = ctk.CTkFrame(info_card, fg_color="transparent")
            item_frame.pack(fill="x", padx=20, pady=8)

            ctk.CTkLabel(
                item_frame,
                text=label + ":",
                font=ctk.CTkFont(size=13),
                text_color=self.COLORS['text_muted']
            ).pack(side="left")

            ctk.CTkLabel(
                item_frame,
                text=value,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=self.COLORS['text_light']
            ).pack(side="right")

        # Spacer at bottom
        ctk.CTkLabel(scrollable, text="").pack(pady=20)

    def _create_stat_card(self, parent, col, title, value, color):
        """Create a statistics card"""
        card = ctk.CTkFrame(parent, fg_color=self.COLORS['card_bg'], corner_radius=12)
        card.grid(row=0, column=col, padx=10, pady=10, sticky="nsew")

        # Title
        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS['text_muted']
        ).pack(pady=(15, 5))

        # Value
        ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=color
        ).pack(pady=(5, 15))

    def _create_action_card(self, parent, row, col, title, description, color, command):
        """Create an action card button"""
        card = ctk.CTkButton(
            parent,
            text="",
            fg_color=color,
            hover_color=self.COLORS['card_hover'],
            corner_radius=12,
            height=100,
            command=command
        )
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

        # Content frame
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            content,
            text=title,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.COLORS['text_light']
        ).pack()

        ctk.CTkLabel(
            content,
            text=description,
            font=ctk.CTkFont(size=11),
            text_color=self.COLORS['text_muted']
        ).pack(pady=(5, 0))

    def _get_service_status_text(self):
        """Get service status text"""
        if self.pid_file.exists():
            try:
                import psutil
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                if psutil.pid_exists(pid):
                    return "Running"
            except:
                pass
        return "Stopped"

    def _get_service_status_color(self):
        """Get service status color"""
        status = self._get_service_status_text()
        return "#00ff00" if status == "Running" else "#ff0000"

    def _get_current_weather_text(self):
        """Get current weather text"""
        try:
            from weather_rotation import WeatherRotationController
            from config import WeatherRotationSettings

            controller = WeatherRotationController(WeatherRotationSettings, None)
            decision = controller.evaluate("gui")

            if decision and decision.temperature:
                return f"{decision.temperature:.1f}°C - {decision.condition}"
            return "N/A"
        except:
            return "N/A"

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
        self._add_help_text(provider_section, "Choose which service to download wallpapers from")
        self._add_setting_row(provider_section, "Search Query:", "entry", self.query_var)
        self._add_help_text(provider_section, "Keywords to search for wallpapers (e.g., 'nature', 'technology')")
        self._add_setting_row(provider_section, "Enable Provider Rotation", "checkbox", self.rotate_providers_var)
        self._add_help_text(provider_section, "Automatically rotate between different providers")

        # Wallhaven Settings
        wallhaven_section = self._create_section(scrollable, "Wallhaven Settings")
        self._add_setting_row(wallhaven_section, "Purity Level:", "dropdown", self.purity_var,
                            ["100", "110", "111", "010", "001"])
        self._add_help_text(wallhaven_section, "100=SFW only, 110=SFW+Sketchy, 111=All content")
        self._add_setting_row(wallhaven_section, "Min Resolution:", "dropdown", self.resolution_var,
                            ["1920x1080", "2560x1440", "3440x1440", "3840x2160"])
        self._add_help_text(wallhaven_section, "Minimum resolution for downloaded wallpapers")
        self._add_setting_row(wallhaven_section, "Sorting:", "dropdown", self.sorting_var,
                            ["random", "toplist", "favorites", "views"])
        self._add_help_text(wallhaven_section, "How to sort wallpapers (toplist=most popular)")
        self._add_setting_row(wallhaven_section, "Top Range:", "dropdown", self.toprange_var,
                            ["1d", "3d", "1w", "1M", "3M", "6M", "1y"])
        self._add_help_text(wallhaven_section, "Time range for toplist (1d=1 day, 1M=1 month, etc.)")

        # Pexels Settings
        pexels_section = self._create_section(scrollable, "Pexels Settings")
        self._add_setting_row(pexels_section, "Mode:", "dropdown", self.pexels_mode_var,
                            ["search", "curated"])
        self._add_help_text(pexels_section, "search=Use search query, curated=Get curated high-quality photos")

        # Reddit Settings
        reddit_section = self._create_section(scrollable, "Reddit Settings")
        self._add_setting_row(reddit_section, "Subreddits (comma separated):", "entry", self.reddit_subreddits_var)
        self._add_help_text(reddit_section, "e.g., wallpapers, wallpaper, EarthPorn")
        self._add_setting_row(reddit_section, "Sort:", "dropdown", self.reddit_sort_var,
                            ["hot", "new", "rising", "top", "controversial"])
        self._add_help_text(reddit_section, "How to sort posts (hot=trending now, top=most upvoted)")
        self._add_setting_row(reddit_section, "Time Filter:", "dropdown", self.reddit_time_var,
                            ["hour", "day", "week", "month", "year", "all"])
        self._add_help_text(reddit_section, "Time range for 'top' and 'controversial' sorts")
        self._add_setting_row(reddit_section, "Posts per fetch:", "spinbox", self.reddit_limit_var, [10, 100])
        self._add_help_text(reddit_section, "Number of posts to fetch per request")
        self._add_setting_row(reddit_section, "Minimum upvotes:", "spinbox", self.reddit_score_var, [0, 100000])
        self._add_help_text(reddit_section, "Only download posts with at least this many upvotes")
        self._add_setting_row(reddit_section, "Include NSFW posts", "checkbox", self.reddit_nsfw_var)
        self._add_help_text(reddit_section, "Include posts marked as NSFW")

        # Scheduler Settings
        scheduler_section = self._create_section(scrollable, "Scheduler Settings")
        self._add_setting_row(scheduler_section, "Enable Scheduler", "checkbox", self.scheduler_enabled_var)
        self._add_help_text(scheduler_section, "Automatically change wallpaper at regular intervals")
        self._add_setting_row(scheduler_section, "Interval (minutes):", "spinbox", self.interval_var, [1, 1440])
        self._add_help_text(scheduler_section, "How often to change wallpaper (in minutes)")
        self._add_setting_row(scheduler_section, "Jitter (minutes):", "spinbox", self.jitter_var, [0, 60])
        self._add_help_text(scheduler_section, "Random variation to add to interval (prevents predictability)")

        # Cache Settings
        cache_section = self._create_section(scrollable, "Cache Settings")
        self._add_setting_row(cache_section, "Max Cache Items:", "spinbox", self.cache_max_var, [10, 500])
        self._add_help_text(cache_section, "Maximum number of wallpapers to store in cache")
        self._add_setting_row(cache_section, "Enable Offline Rotation", "checkbox", self.cache_offline_var)
        self._add_help_text(cache_section, "Use cached wallpapers when internet is unavailable")

        # Hotkey Settings
        hotkey_section = self._create_section(scrollable, "Hotkey Settings")
        self._add_setting_row(hotkey_section, "Hotkey:", "entry", self.keybind_var)
        self._add_help_text(hotkey_section, "Use format: ctrl+alt+w, ctrl+shift+p, etc.")

        # Advanced Settings - API Keys
        self._add_section_header(scrollable, "ADVANCED SETTINGS")

        # Load API keys from .env
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

        self.wallhaven_api_var = ctk.StringVar(value=current_wallhaven_key)
        self.pexels_api_var = ctk.StringVar(value=current_pexels_key)
        self.weather_api_var = ctk.StringVar(value=current_openweather_key)

        api_section = self._create_section(scrollable, "API Keys")
        self._add_setting_row(api_section, "Wallhaven API Key:", "entry", self.wallhaven_api_var)
        self._add_help_text(api_section, "Get your API key at: https://wallhaven.cc/settings/account")
        self._add_setting_row(api_section, "Pexels API Key:", "entry", self.pexels_api_var)
        self._add_help_text(api_section, "Get your API key at: https://www.pexels.com/api/new/")
        self._add_setting_row(api_section, "OpenWeatherMap API Key:", "entry", self.weather_api_var)
        self._add_help_text(api_section, "Free tier: 1000 calls/day - Get it at: https://home.openweathermap.org/api_keys")

        # Cache Directory
        from config import CacheSettings
        cache_dir = CacheSettings.get("directory") or os.path.join(os.path.expanduser("~"), "WallpaperChangerCache")
        self.cache_dir_var = ctk.StringVar(value=cache_dir)

        folders_section = self._create_section(scrollable, "Folders Configuration")
        self._add_setting_row(folders_section, "Cache Directory:", "entry", self.cache_dir_var)
        self._add_help_text(folders_section, "Location where wallpapers are cached. Leave empty for default.")

        # Advanced Scheduler Settings
        from config import SchedulerSettings
        self.initial_delay_var = ctk.IntVar(value=SchedulerSettings.get("initial_delay_minutes", 1))

        adv_scheduler_section = self._create_section(scrollable, "Advanced Scheduler Settings")
        self._add_setting_row(adv_scheduler_section, "Initial Delay (minutes):", "spinbox",
                            self.initial_delay_var, [0, 60])
        self._add_help_text(adv_scheduler_section, "Delay before first wallpaper change after startup")

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

    def _add_help_text(self, parent, text):
        """Add a help/description text below a setting"""
        help_frame = ctk.CTkFrame(
            parent,
            fg_color=self.COLORS['main_bg'],
            corner_radius=6
        )
        help_frame.pack(fill="x", padx=25, pady=(2, 12))

        help_label = ctk.CTkLabel(
            help_frame,
            text=f"ℹ️  {text}",
            text_color=self.COLORS['text_muted'],
            font=ctk.CTkFont(size=11),
            wraplength=680,
            justify="left",
            anchor="w"
        )
        help_label.pack(fill="x", padx=10, pady=6, anchor="w")

    def _add_section_header(self, parent, text):
        """Add a section header (e.g., ADVANCED SETTINGS)"""
        header_frame = ctk.CTkFrame(parent, fg_color="transparent")
        header_frame.pack(fill="x", pady=(30, 10), padx=5)

        header_label = ctk.CTkLabel(
            header_frame,
            text=text,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.COLORS['accent']
        )
        header_label.pack(anchor="w")

        # Separator line
        separator = ctk.CTkFrame(header_frame, height=2, fg_color=self.COLORS['accent'])
        separator.pack(fill="x", pady=(5, 0))

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
                elif '"initial_delay_minutes":' in line:
                    new_lines.append(f'    "initial_delay_minutes": {self.initial_delay_var.get()},\n')
                elif '"max_items":' in line:
                    new_lines.append(f'    "max_items": {self.cache_max_var.get()},\n')
                elif '"enable_offline_rotation":' in line:
                    new_lines.append(f'    "enable_offline_rotation": {self.cache_offline_var.get()},\n')
                elif '"directory":' in line and 'CacheSettings' in ''.join(new_lines[-3:]):
                    cache_dir_value = self.cache_dir_var.get().strip()
                    if cache_dir_value:
                        new_lines.append(f'    "directory": r"{cache_dir_value}",\n')
                    else:
                        new_lines.append(f'    "directory": "",\n')
                else:
                    new_lines.append(line)

            # Write updated config
            with open(config_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)

            # Save API keys to .env
            env_path = Path(__file__).parent / '.env'
            env_lines = []

            if env_path.exists():
                with open(env_path, 'r', encoding='utf-8') as f:
                    env_lines = f.readlines()

            # Update or add API keys
            updated_keys = {
                'WALLHAVEN_API_KEY': self.wallhaven_api_var.get(),
                'PEXELS_API_KEY': self.pexels_api_var.get(),
                'OPENWEATHER_API_KEY': self.weather_api_var.get()
            }

            new_env_lines = []
            keys_found = set()

            for line in env_lines:
                found = False
                for key, value in updated_keys.items():
                    if line.startswith(f'{key}='):
                        new_env_lines.append(f'{key}={value}\n')
                        keys_found.add(key)
                        found = True
                        break
                if not found:
                    new_env_lines.append(line)

            # Add missing keys
            for key, value in updated_keys.items():
                if key not in keys_found:
                    new_env_lines.append(f'{key}={value}\n')

            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(new_env_lines)

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
        """Show monitor selection dialog and apply wallpaper"""
        self._show_monitor_selection_dialog(item)

    def _show_monitor_selection_dialog(self, item: Dict[str, Any]):
        """Show dialog to choose monitor for wallpaper"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Select Monitor")
        dialog.geometry("450x500")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

        # Title
        title = ctk.CTkLabel(
            dialog,
            text="Choose Monitor",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.COLORS['text_light']
        )
        title.pack(pady=(20, 10))

        # Info text
        info = ctk.CTkLabel(
            dialog,
            text="Choose which monitor to apply this wallpaper to:",
            font=ctk.CTkFont(size=13),
            text_color=self.COLORS['text_muted']
        )
        info.pack(pady=(0, 20))

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

        # All Monitors button
        all_btn = ctk.CTkButton(
            dialog,
            text="All Monitors",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=self.COLORS['accent'],
            hover_color=self.COLORS['sidebar_hover'],
            corner_radius=10,
            height=50,
            command=lambda: [dialog.destroy(), self._apply_wallpaper_to_monitor(item, "All Monitors", monitors)]
        )
        all_btn.pack(fill="x", padx=30, pady=10)

        # Individual monitor buttons
        for idx, monitor in enumerate(monitors):
            monitor_name = f"Monitor {idx + 1} ({monitor.get('width')}x{monitor.get('height')})"
            mon_btn = ctk.CTkButton(
                dialog,
                text=monitor_name,
                font=ctk.CTkFont(size=13),
                fg_color=self.COLORS['card_bg'],
                hover_color=self.COLORS['card_hover'],
                corner_radius=8,
                height=45,
                command=lambda m=monitor_name, i=idx: [dialog.destroy(),
                                                        self._apply_wallpaper_to_monitor(item, m, monitors, i)]
            )
            mon_btn.pack(fill="x", padx=30, pady=5)

        # Cancel button
        cancel_btn = ctk.CTkButton(
            dialog,
            text="Cancel",
            font=ctk.CTkFont(size=12),
            fg_color=self.COLORS['main_bg'],
            hover_color=self.COLORS['card_bg'],
            corner_radius=8,
            height=40,
            command=dialog.destroy
        )
        cancel_btn.pack(fill="x", padx=30, pady=(15, 20))

    def _apply_wallpaper_to_monitor(self, item: Dict[str, Any], monitor_selection: str = "All Monitors",
                                   monitors_list: list = None, monitor_idx: int = None):
        """Apply selected wallpaper to specified monitor with weather overlay if enabled"""
        try:
            from main import DesktopWallpaperController
            from PIL import Image
            from weather_overlay import WeatherOverlay, WeatherInfo
            from weather_rotation import WeatherRotationController
            from config import WeatherOverlaySettings, WeatherRotationSettings
            import ctypes
            import tempfile
            import time

            wallpaper_path = item.get("path")
            original_path = wallpaper_path

            # Apply weather overlay if enabled
            weather_overlay = WeatherOverlay(WeatherOverlaySettings)
            if weather_overlay.enabled:
                try:
                    # Get current weather
                    weather_controller = WeatherRotationController(WeatherRotationSettings, None)
                    weather_decision = weather_controller.evaluate("gui")

                    if weather_decision:
                        # Create WeatherInfo from WeatherDecision
                        weather_info = WeatherInfo(
                            city=WeatherRotationSettings.get("location", {}).get("city", ""),
                            country=WeatherRotationSettings.get("location", {}).get("country", ""),
                            condition=weather_decision.condition,
                            temperature=weather_decision.temperature or 0.0,
                            feels_like=weather_decision.details.get('feels_like') if weather_decision.details else None,
                            humidity=weather_decision.details.get('humidity') if weather_decision.details else None,
                            pressure=weather_decision.details.get('pressure') if weather_decision.details else None,
                            wind_speed=weather_decision.details.get('wind_speed') if weather_decision.details else None,
                            clouds=weather_decision.details.get('clouds') if weather_decision.details else None,
                            description=weather_decision.details.get('description') if weather_decision.details else None
                        )

                        # Create temporary file for overlay
                        temp_dir = tempfile.gettempdir()
                        timestamp = int(time.time())
                        base_name = Path(wallpaper_path).stem
                        temp_overlay_path = os.path.join(temp_dir, f"wallpaper_overlay_gui_{timestamp}_{base_name}.jpg")

                        # Get monitor size for proper overlay positioning
                        target_size = None
                        if monitor_selection != "All Monitors" and monitors_list and monitor_idx is not None:
                            mon = monitors_list[monitor_idx]
                            target_size = (mon.get('width'), mon.get('height'))

                        # Apply overlay
                        if weather_overlay.apply_overlay(wallpaper_path, temp_overlay_path, weather_info, target_size):
                            wallpaper_path = temp_overlay_path

                except Exception as e:
                    # Continue with original wallpaper if overlay fails
                    pass

            # Convert to BMP if needed
            if not wallpaper_path.lower().endswith('.bmp'):
                bmp_path = str(Path(wallpaper_path).with_suffix('.bmp'))
                img = Image.open(wallpaper_path)
                img.save(bmp_path, 'BMP')
                wallpaper_path = bmp_path

            if monitor_selection == "All Monitors":
                # Apply to all monitors
                ctypes.windll.user32.SystemParametersInfoW(20, 0, wallpaper_path, 3)
                self._show_success_dialog("Wallpaper applied to all monitors!")
            else:
                # Apply to specific monitor
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
                    self._show_success_dialog(f"Wallpaper applied to {monitor_selection}!")
                else:
                    manager.close()
                    self._show_error_dialog("Invalid monitor selection")

        except Exception as e:
            self._show_error_dialog(f"Failed to apply wallpaper: {e}")

    def _show_success_dialog(self, message: str):
        """Show success message dialog"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Success")
        dialog.geometry("400x150")
        dialog.transient(self.root)
        dialog.grab_set()

        msg = ctk.CTkLabel(
            dialog,
            text=message,
            font=ctk.CTkFont(size=13),
            text_color=self.COLORS['text_light']
        )
        msg.pack(pady=30)

        ok_btn = ctk.CTkButton(
            dialog,
            text="OK",
            fg_color=self.COLORS['accent'],
            command=dialog.destroy
        )
        ok_btn.pack(pady=10)

    def _show_error_dialog(self, message: str):
        """Show error message dialog"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Error")
        dialog.geometry("400x150")
        dialog.transient(self.root)
        dialog.grab_set()

        msg = ctk.CTkLabel(
            dialog,
            text=message,
            font=ctk.CTkFont(size=13),
            text_color=self.COLORS['warning']
        )
        msg.pack(pady=30)

        ok_btn = ctk.CTkButton(
            dialog,
            text="OK",
            fg_color=self.COLORS['accent'],
            command=dialog.destroy
        )
        ok_btn.pack(pady=10)

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
