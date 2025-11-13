"Modern GUI for Wallpaper Changer using CustomTkinter\nInspired by contemporary wallpaper applications with sidebar navigation\n"
import os
import sys
import subprocess
import signal
import time
from datetime import datetime
import customtkinter as ctk
from pathlib import Path
from PIL import Image, ImageTk
from typing import Dict, Any, List, Optional
import tkinter as tk

from cache_manager import CacheManager
from config import CacheSettings
from statistics_manager import StatisticsManager
from smart_recommendations import SmartRecommendations
import matplotlib
matplotlib.use('TkAgg')  # Use TkAgg backend for embedding in tkinter
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import time


# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class AILoadingDialog(ctk.CTkToplevel):
    """Non-blocking loading dialog for AI operations"""
    def __init__(self, parent, title="AI Processing", message="Please wait..."):
        super().__init__(parent)
        self.title(title)
        self.geometry("400x200")
        self.transient(parent)
        self.resizable(False, False)
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 200
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 100
        self.geometry(f"+{x}+{y}")
        self.configure(fg_color="#2D2D3A")

        ctk.CTkLabel(self, text=f"🤖 {message}", font=ctk.CTkFont(size=16), text_color="#FFFFFF").pack(pady=(40, 20))
        self.progress = ctk.CTkProgressBar(self, mode="indeterminate", width=300)
        self.progress.pack(pady=10)
        self.progress.start()
        self.status_label = ctk.CTkLabel(self, text="Analyzing...", font=ctk.CTkFont(size=12), text_color="#B0B0B0")
        self.status_label.pack(pady=10)
        self.protocol("WM_DELETE_WINDOW", lambda: None)

    def update_status(self, status: str):
        self.status_label.configure(text=status)

    def close(self):
        self.progress.stop()
        self.destroy()


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
        self.root.minsize(1100, 600)  # Minimum window size to fit 3-column layout

        # Configure grid layout
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # Initialize statistics manager first (needed by cache manager)
        self.stats_manager = StatisticsManager()

        # Initialize cache manager with stats_manager for smart rotation
        cache_dir = CacheSettings.get("directory") or os.path.join(
            os.path.expanduser("~"), "WallpaperChangerCache"
        )
        self.cache_manager = CacheManager(
            cache_dir,
            max_items=int(CacheSettings.get("max_items", 60)),
            enable_rotation=bool(CacheSettings.get("enable_offline_rotation", True)),
            stats_manager=self.stats_manager,  # Pass stats_manager for smart cache rotation
        )

        # Thumbnail cache
        self.thumbnail_cache = {}

        # Image references to prevent garbage collection
        self.image_references = []
        # Clean up placeholder paths from previous versions
        self.stats_manager.cleanup_placeholder_paths()

        # Toast notifications
        self.toast_windows = []

        # Current wallpaper tracking
        self.current_wallpaper = None

        # View caching for performance
        self._view_cache = {}

        # Smart Recommendations system (API key loaded from config)
        from config import GeminiApiKey
        self.recommendations = SmartRecommendations(
            self.stats_manager,
            self.cache_manager,
            api_key=GeminiApiKey if GeminiApiKey else None
        )

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

        # Track last known wallpaper to auto-refresh Home view
        self.last_known_wallpaper_path = None
        self._monitor_wallpaper_changes()

    def _monitor_wallpaper_changes(self):
        """Periodically check for wallpaper changes and auto-refresh Home view."""
        try:
            info_path = Path(__file__).parent / "current_wallpaper_info.json"
            if info_path.exists():
                with open(info_path, "r", encoding="utf-8") as f:
                    import json
                    data = json.load(f)
                    current_path = data.get("path")

                    if current_path and current_path != self.last_known_wallpaper_path:
                        self.last_known_wallpaper_path = current_path
                        if self.active_view == "Home":
                            # Refresh home data on the main thread
                            self.root.after(100, self._refresh_home_data)
        except (IOError, json.JSONDecodeError):
            # Ignore errors if the file is being written or is corrupted
            pass
        except Exception:
            # General exceptions
            pass

        # Schedule the next check in 3 seconds (a bit faster)
        self.root.after(3000, self._monitor_wallpaper_changes)

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

        # Navigation buttons with colored icons
        nav_items = [
            ("Home", "●", "#FFD93D"),       # Yellow home icon
            ("Wallpapers", "●", "#00e676"),  # Green wallpapers icon
            ("Duplicates", "●", "#ff9500"),  # Orange duplicates icon
            ("AI Assistant", "●", "#a78bfa"), # Purple AI icon
            ("Settings", "●", "#89b4fa"),    # Blue settings icon
            ("Logs", "●", "#ff6b81"),        # Red logs icon
        ]

        self.nav_buttons = []
        for idx, (text, icon, color) in enumerate(nav_items, start=1):
            # Create button with icon and text directly
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"{icon}  {text}",
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

            # Store reference
            self.nav_buttons.append((btn, icon, color))

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
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Content container that will be swapped
        self.content_container = ctk.CTkFrame(
            self.main_frame,
            corner_radius=0,
            fg_color="transparent"
        )
        self.content_container.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.content_container.grid_rowconfigure(0, weight=0)
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
        # Clean up orphaned statistics before showing wallpapers
        self._cleanup_orphaned_stats()

        # Create container for this view
        view_container = ctk.CTkFrame(self.content_container, fg_color="transparent")
        view_container.pack(fill="both", expand=True)

        # Cache the view
        self._view_cache["Wallpapers"] = view_container

        # Configure grid
        view_container.grid_rowconfigure(1, weight=1)
        view_container.grid_columnconfigure(0, weight=1)

        # Header with controls
        header = ctk.CTkFrame(
            view_container,
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

        # Filter frame - now with two rows for better organization
        filter_frame = ctk.CTkFrame(header, fg_color="transparent")
        filter_frame.grid(row=0, column=2, sticky="e", padx=10)

        # First row of filters
        filter_row1 = ctk.CTkFrame(filter_frame, fg_color="transparent")
        filter_row1.pack(side="top", fill="x", pady=(0, 5))

        # Provider filter
        ctk.CTkLabel(
            filter_row1,
            text="Provider:",
            text_color=self.COLORS['text_muted'],
            font=ctk.CTkFont(size=13)
        ).pack(side="left", padx=(0, 5))

        # Create or reuse provider_filter_var
        if not hasattr(self, 'provider_filter_var') or not self.provider_filter_var:
            self.provider_filter_var = ctk.StringVar(value="All Providers")

        provider_menu = ctk.CTkOptionMenu(
            filter_row1,
            variable=self.provider_filter_var,
            values=["All Providers", "pexels", "reddit", "wallhaven"],
            width=120,
            fg_color=self.COLORS['card_bg'],
            button_color=self.COLORS['accent'],
            button_hover_color=self.COLORS['sidebar_hover'],
            command=self._on_filter_change
        )
        provider_menu.pack(side="left", padx=(0, 10))

        # Second row of filters
        filter_row2 = ctk.CTkFrame(filter_frame, fg_color="transparent")
        filter_row2.pack(side="top", fill="x")

        # Color filter dropdown
        ctk.CTkLabel(
            filter_row2,
            text="Color:",
            text_color=self.COLORS['text_muted'],
            font=ctk.CTkFont(size=13)
        ).pack(side="left", padx=(0, 5))

        # Create or reuse color_filter_var to preserve selection
        if not hasattr(self, 'color_filter_var') or not self.color_filter_var:
            self.color_filter_var = ctk.StringVar(value="All Colors")

        # Get all unique colors from cache
        all_colors = self.cache_manager.get_all_colors()
        color_values = ["All Colors"] + sorted(all_colors)

        color_menu = ctk.CTkOptionMenu(
            filter_row2,
            variable=self.color_filter_var,
            values=color_values if color_values else ["All Colors"],
            width=120,
            fg_color=self.COLORS['card_bg'],
            button_color=self.COLORS['accent'],
            button_hover_color=self.COLORS['sidebar_hover'],
            command=self._on_filter_change
        )
        color_menu.pack(side="left", padx=(0, 5))

        # Dominant color only checkbox
        if not hasattr(self, 'dominant_only_var'):
            self.dominant_only_var = ctk.BooleanVar(value=False)

        dominant_checkbox = ctk.CTkCheckBox(
            filter_row2,
            text="Dominant only",
            variable=self.dominant_only_var,
            fg_color=self.COLORS['accent'],
            hover_color=self.COLORS['sidebar_hover'],
            command=self._on_filter_change,
            width=20
        )
        dominant_checkbox.pack(side="left", padx=(0, 10))

        # Sort dropdown
        ctk.CTkLabel(
            filter_row2,
            text="Sort:",
            text_color=self.COLORS['text_muted'],
            font=ctk.CTkFont(size=13)
        ).pack(side="left", padx=(0, 5))

        # Create or reuse sort_var to preserve selection
        if not hasattr(self, 'sort_var') or not self.sort_var:
            self.sort_var = ctk.StringVar(value="Newest First")

        sort_menu = ctk.CTkOptionMenu(
            filter_row2,
            variable=self.sort_var,
            values=["Newest First", "Oldest First", "Highest Resolution", "Favorites Only", "Top Rated", "Banned Only"],
            width=170,
            fg_color=self.COLORS['card_bg'],
            button_color=self.COLORS['accent'],
            button_hover_color=self.COLORS['sidebar_hover'],
            command=self._on_sort_change
        )
        sort_menu.pack(side="left", padx=(0, 10))

        # Refresh button to reload grid with current window size
        refresh_btn = ctk.CTkButton(
            filter_row2,
            text="🔄",
            font=ctk.CTkFont(size=16),
            width=35,
            height=28,
            fg_color=self.COLORS['card_bg'],
            hover_color=self.COLORS['accent'],
            corner_radius=8,
            command=self._load_wallpaper_grid
        )
        refresh_btn.pack(side="left")

        # Tags filter button - opens popup dialog
        tags_btn = ctk.CTkButton(
            filter_row2,
            text="Tags...",
            width=80,
            height=28,
            fg_color=self.COLORS['card_bg'],
            hover_color=self.COLORS['accent'],
            corner_radius=8,
            command=self._show_tags_dialog
        )
        tags_btn.pack(side="left", padx=(10, 0))

        # Initialize selected tags set
        if not hasattr(self, 'selected_tags'):
            self.selected_tags = set()

        # Scrollable frame for wallpaper grid with faster scrolling
        self.wallpapers_scrollable_frame = ctk.CTkScrollableFrame(
            view_container,
            corner_radius=0,
            fg_color="transparent",
            scrollbar_button_color=self.COLORS['accent'],
            scrollbar_button_hover_color=self.COLORS['sidebar_hover']
        )
        self.wallpapers_scrollable_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)

        def fast_scroll(event):
            try:
                self.wallpapers_scrollable_frame._parent_canvas.yview_scroll(int(-3*(event.delta/120)), "units")
            except:
                pass

        self.wallpapers_scrollable_frame.bind("<MouseWheel>", fast_scroll)
        self._setup_wallpaper_resize_handler()
        self._load_wallpaper_grid()

    def _setup_wallpaper_resize_handler(self):
        """Setup resize handler that only works when on Wallpapers page"""
        # Disabled automatic resize - cards now use fixed grid layout
        # User can manually refresh if needed using the refresh button
        pass

    def _load_wallpaper_grid(self):
        """Load wallpapers into the grid with current filter/sort settings"""
        if not hasattr(self, 'wallpapers_scrollable_frame'):
            return

        scrollable_frame = self.wallpapers_scrollable_frame
        for widget in scrollable_frame.winfo_children():
            widget.destroy()

        # Use fixed 3-column layout for consistency
        # Cards will expand/shrink naturally with window size
        num_columns = 3

        # Configure columns with weight and minimum size
        for i in range(num_columns):
            scrollable_frame.grid_columnconfigure(i, weight=1, minsize=320)

        if not self.cache_manager or not self.cache_manager.has_items():
            empty_label = ctk.CTkLabel(
                scrollable_frame,
                text="No wallpapers in cache.\nDownload some wallpapers first!",
                font=ctk.CTkFont(size=16),
                text_color=self.COLORS['text_muted']
            )
            empty_label.grid(row=0, column=0, columnspan=4, pady=100)
            return

        items = self.cache_manager.list_entries()
        sort_choice = self.sort_var.get() if hasattr(self, 'sort_var') else "Newest First"
        provider_filter = self.provider_filter_var.get() if hasattr(self, 'provider_filter_var') else "All Providers"
        color_filter = self.color_filter_var.get() if hasattr(self, 'color_filter_var') else "All Colors"

        # Apply tag filter - match wallpapers that have ALL selected tags
        if hasattr(self, 'selected_tags') and self.selected_tags:
            def item_matches_tags(item):
                item_path = item.get("path")
                stats = self.stats_manager.data.get("wallpapers", {}).get(item_path, {})
                item_tags = set(stats.get("tags", []))
                # Item must have ALL selected tags (AND logic)
                return self.selected_tags.issubset(item_tags)

            items = [item for item in items if item_matches_tags(item)]

        # Apply provider filter
        if provider_filter and provider_filter != "All Providers":
            items = [item for item in items if item.get("provider") == provider_filter]

        # Apply color filter
        if color_filter and color_filter != "All Colors":
            dominant_only = self.dominant_only_var.get() if hasattr(self, 'dominant_only_var') else False

            if dominant_only:
                # Filter only by primary/dominant color
                items = [item for item in items if color_filter == item.get("primary_color")]
            else:
                # Filter by any color in the palette
                items = [item for item in items
                        if color_filter in item.get("color_categories", []) or
                           color_filter == item.get("primary_color")]

        if sort_choice == "Banned Only":
            banned = self.stats_manager.get_banned_wallpapers()
            items = [item for item in items if item.get("path") in banned]
        elif sort_choice == "Favorites Only":
            favorites = self.stats_manager.get_favorites()
            items = [item for item in items if item.get("path") in favorites and not self.stats_manager.is_banned(item.get("path"))]
        elif sort_choice == "Top Rated":
            items = [item for item in items if not self.stats_manager.is_banned(item.get("path"))]
            items = sorted(items, key=lambda x: self.stats_manager.get_rating(x.get("path", "")), reverse=True)
        elif sort_choice == "Oldest First":
            items = [item for item in items if not self.stats_manager.is_banned(item.get("path"))]
            items = list(reversed(items))
        elif sort_choice == "Highest Resolution":
            items = [item for item in items if not self.stats_manager.is_banned(item.get("path"))]
            def get_resolution(item):
                try:
                    from PIL import Image
                    img = Image.open(item.get("path"))
                    return img.size[0] * img.size[1]
                except:
                    return 0
            items = sorted(items, key=get_resolution, reverse=True)
        else:
            items = [item for item in items if not self.stats_manager.is_banned(item.get("path"))]

        if not items:
            no_items_label = ctk.CTkLabel(
                scrollable_frame,
                text="No wallpapers match the selected filter.",
                font=ctk.CTkFont(size=16),
                text_color=self.COLORS['text_muted']
            )
            no_items_label.grid(row=0, column=0, columnspan=num_columns, pady=100)
            return

        items_to_show = min(len(items), num_columns * 4)
        for idx, item in enumerate(items[:items_to_show]):
            row = idx // num_columns
            col = idx % num_columns
            self._create_wallpaper_card(item, row, col, scrollable_frame)

        if len(items) > items_to_show:
            remaining = len(items) - items_to_show
            load_more_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
            load_more_frame.grid(row=(items_to_show // num_columns) + 1, column=0, columnspan=num_columns, pady=20)

            ctk.CTkLabel(
                load_more_frame,
                text=f"{remaining} more wallpapers available",
                font=ctk.CTkFont(size=12),
                text_color=self.COLORS['text_muted']
            ).pack(pady=(0, 10))

            ctk.CTkButton(
                load_more_frame,
                text="Load More",
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color=self.COLORS['accent'],
                hover_color=self.COLORS['sidebar_hover'],
                corner_radius=10,
                height=35,
                width=150,
                command=lambda: self._load_more_wallpapers(items, items_to_show, num_columns, scrollable_frame)
            ).pack()

    def _load_more_wallpapers(self, items: list, current_count: int, num_columns: int, parent):
        for widget in parent.winfo_children():
            if isinstance(widget, ctk.CTkFrame) and widget.cget("fg_color") == "transparent":
                children = widget.winfo_children()
                if len(children) == 2:
                    widget.destroy()
                    break

        next_batch = min(len(items), current_count + num_columns * 4)
        for idx in range(current_count, next_batch):
            item = items[idx]
            row = idx // num_columns
            col = idx % num_columns
            self._create_wallpaper_card(item, row, col, parent)

        if next_batch < len(items):
            remaining = len(items) - next_batch
            load_more_frame = ctk.CTkFrame(parent, fg_color="transparent")
            load_more_frame.grid(row=(next_batch // num_columns) + 1, column=0, columnspan=num_columns, pady=20)

            ctk.CTkLabel(
                load_more_frame,
                text=f"{remaining} more wallpapers available",
                font=ctk.CTkFont(size=12),
                text_color=self.COLORS['text_muted']
            ).pack(pady=(0, 10))

            ctk.CTkButton(
                load_more_frame,
                text="Load More",
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color=self.COLORS['accent'],
                hover_color=self.COLORS['sidebar_hover'],
                corner_radius=10,
                height=35,
                width=150,
                command=lambda: self._load_more_wallpapers(items, next_batch, num_columns, parent)
            ).pack()

    def _create_wallpaper_card(self, item: Dict[str, Any], row: int, col: int, parent):
        card = ctk.CTkFrame(
            parent,
            fg_color=self.COLORS['card_bg'],
            corner_radius=15,
            border_width=2,
            border_color=self.COLORS['card_bg'],
            height=320
        )
        card.grid(row=row, column=col, padx=10, pady=10, sticky="ew")
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)

        def on_enter(e):
            card.configure(border_color=self.COLORS['accent'])

        def on_leave(e):
            card.configure(border_color=self.COLORS['card_bg'])

        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

        try:
            image_path = item.get("path", "")
            if not os.path.exists(image_path):
                raise FileNotFoundError()

            if image_path in self.thumbnail_cache:
                photo, original_size = self.thumbnail_cache[image_path]
            else:
                img = Image.open(image_path)
                original_size = img.size
                img.thumbnail((320, 200), Image.Resampling.LANCZOS)
                photo = ctk.CTkImage(light_image=img, dark_image=img, size=(320, 200))
                self.thumbnail_cache[image_path] = (photo, original_size)

            img_label = ctk.CTkLabel(
                card,
                image=photo,
                text="",
                width=320,
                height=200,
                cursor="hand2"
            )
            img_label.pack(padx=10, pady=10, fill="both", expand=False)

            # Make image clickable to view fullscreen
            img_label.bind("<Button-1>", lambda e, path=image_path: self._show_fullscreen_viewer(path))

            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(fill="x", padx=15, pady=(0, 5))

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

            # Display tags from statistics (if available)
            tags = self.stats_manager.get_tags(image_path)
            if tags:
                # Show only first 2 tags to save space
                tags_to_show = tags[:2]
                tags_text = ", ".join(tags_to_show)
                if len(tags) > 2:
                    tags_text += f" +{len(tags) - 2}"

                tags_label = ctk.CTkLabel(
                    info_frame,
                    text=f"🏷️ {tags_text}",
                    font=ctk.CTkFont(size=9),
                    text_color=self.COLORS['text_muted'],
                )
                tags_label.pack(side="left", padx=(8, 0))

            # Display primary/dominant color with badge style
            primary_color = item.get("primary_color")
            if primary_color:
                color_emoji = "🎨"
                # Create a frame for the color badge with background
                color_badge = ctk.CTkFrame(
                    info_frame,
                    fg_color=self.COLORS['accent'],
                    corner_radius=12,
                    height=22
                )
                color_badge.pack(side="left", padx=(8, 0))

                color_label = ctk.CTkLabel(
                    color_badge,
                    text=f"{color_emoji} {primary_color.capitalize()}",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color="white",
                )
                color_label.pack(padx=8, pady=2)

            # Delete button
            delete_btn = ctk.CTkButton(
                info_frame,
                text="🗑️",
                font=ctk.CTkFont(size=16),
                width=30,
                height=30,
                fg_color="transparent",
                hover_color="#ff0000",
                corner_radius=15,
                command=lambda p=image_path, c=card, i=item: self._delete_wallpaper(p, c, i)
            )
            delete_btn.pack(side="right", padx=(5, 0))

            is_banned = self.stats_manager.is_banned(image_path)
            ban_btn = ctk.CTkButton(
                info_frame,
                text="🚫" if is_banned else "⊘",
                font=ctk.CTkFont(size=16),
                width=30,
                height=30,
                fg_color="#ff4444" if is_banned else "transparent",
                hover_color="#cc0000",
                corner_radius=15,
                command=lambda p=image_path, b=None: self._toggle_ban(p, b)
            )
            ban_btn.pack(side="right", padx=(5, 0))
            ban_btn.configure(command=lambda p=image_path, b=ban_btn: self._toggle_ban(p, b))

            is_fav = self.stats_manager.is_favorite(image_path)
            fav_btn = ctk.CTkButton(
                info_frame,
                text="♥" if is_fav else "♡",
                font=ctk.CTkFont(size=16),
                width=30,
                height=30,
                fg_color="#ff6b81" if is_fav else "transparent",
                hover_color="#ff4757",
                corner_radius=15,
                command=lambda p=image_path, b=None: self._toggle_favorite(p, b)
            )
            fav_btn.pack(side="right", padx=(5, 0))
            fav_btn.configure(command=lambda p=image_path, b=fav_btn: self._toggle_favorite(p, b))

            rating_frame = ctk.CTkFrame(card, fg_color="transparent")
            rating_frame.pack(fill="x", padx=15, pady=(0, 5))

            current_rating = self.stats_manager.get_rating(image_path)
            star_buttons = []
            for i in range(1, 6):
                star_text = "★" if i <= current_rating else "☆"
                star_btn = ctk.CTkButton(
                    rating_frame,
                    text=star_text,
                    font=ctk.CTkFont(size=16),
                    width=30,
                    height=25,
                    fg_color="transparent",
                    hover_color=self.COLORS['card_hover'],
                    text_color="#ffd700" if i <= current_rating else self.COLORS['text_muted'],
                    command=lambda r=i, p=image_path, btns=None: self._set_rating(p, r, btns)
                )
                star_btn.pack(side="left", padx=1)
                star_buttons.append(star_btn)

            for i, star_btn in enumerate(star_buttons, 1):
                star_btn.configure(command=lambda r=i, p=image_path, btns=star_buttons: self._set_rating(p, r, btns))

            apply_btn = ctk.CTkButton(
                card,
                text="SET AS WALLPAPER",
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color=self.COLORS['accent'],
                hover_color=self.COLORS['sidebar_hover'],
                corner_radius=10,
                height=35,
                command=lambda i=item: self._apply_wallpaper(i)
            )
            apply_btn.pack(fill="x", padx=15, pady=(0, 10))

        except Exception as e:
            error_label = ctk.CTkLabel(
                card,
                text=f"Error loading\nimage",
                font=ctk.CTkFont(size=12),
                text_color=self.COLORS['text_muted']
            )
            error_label.pack(expand=True, pady=50)

    def _navigate(self, view: str):
        """Handle navigation with view caching for performance"""
        self.active_view = view
        self._update_nav_buttons()

        if not hasattr(self, '_view_cache'):
            self._view_cache = {}

        for cached_view in self._view_cache.values():
            cached_view.pack_forget()

        if view in self._view_cache:
            self._view_cache[view].pack(fill="both", expand=True)
            if view == "Home":
                self._refresh_home_data()
        else:
            if view == "Home":
                self._show_home_view()
            elif view == "Wallpapers":
                self._show_wallpapers_view()
            elif view == "Duplicates":
                self._show_duplicates_view()
            elif view == "AI Assistant":
                self._show_ai_assistant_view()
            elif view == "Settings":
                self._show_settings_view()
            elif view == "Logs":
                self._show_logs_view()

    def _cleanup_orphaned_stats(self):
        """Clean up statistics and cache index for wallpapers that no longer exist"""
        import os

        # Reload cache manager index from disk
        self.cache_manager._load()

        # First, clean up cache index - remove entries for files that don't exist
        cache_items = self.cache_manager._index.get('items', [])
        valid_cache_items = []
        removed_from_cache = 0

        for item in cache_items:
            path = item.get('path')
            if path and os.path.exists(path):
                valid_cache_items.append(item)
            else:
                removed_from_cache += 1

        if removed_from_cache > 0:
            self.cache_manager._index['items'] = valid_cache_items
            self.cache_manager._save()
            print(f"[CLEANUP] Removed {removed_from_cache} missing files from cache index")

        # Reload statistics manager data
        self.stats_manager.data = self.stats_manager._load_data()

        # Clean up statistics for wallpapers that no longer exist in cache
        cached_paths = {item.get('path') for item in valid_cache_items}
        stats_wallpapers = self.stats_manager.data.get('wallpapers', {})

        # Remove stats for wallpapers not in cache anymore
        paths_to_remove = [path for path in stats_wallpapers.keys() if path not in cached_paths]
        for path in paths_to_remove:
            del stats_wallpapers[path]

        # Save cleaned statistics
        if paths_to_remove:
            self.stats_manager._save_data()
            print(f"[CLEANUP] Removed {len(paths_to_remove)} orphaned wallpaper stats and tags")

        total_removed = removed_from_cache + len(paths_to_remove)
        return total_removed

    def _refresh_home_data(self):
        """Refresh Home view wallpapers without recreating entire view"""
        # Clean up orphaned statistics
        self._cleanup_orphaned_stats()

        # Clear image references to allow new images to load
        self.image_references.clear()

        # Clear view cache to force recreation of Wallpapers view (updates tag/color filters)
        if 'Wallpapers' in self._view_cache:
            del self._view_cache['Wallpapers']

        # Refresh current wallpaper preview if on Home view
        if hasattr(self, 'wallpaper_preview_container') and self.wallpaper_preview_container.winfo_exists():
            for widget in self.wallpaper_preview_container.winfo_children():
                widget.destroy()
            self._create_current_wallpaper_preview(self.wallpaper_preview_container)

        # If currently on Wallpapers view, reload it
        if self.active_view == "Wallpapers":
            self._load_wallpapers_view()

    def _update_nav_buttons(self):
        """Update navigation button styles"""
        for item in self.nav_buttons:
            btn, icon, color = item
            btn_text = btn.cget("text")
            view_name = btn_text.replace(icon, "").strip()

            if view_name == self.active_view:
                btn.configure(fg_color=self.COLORS['sidebar_hover'])
            else:
                btn.configure(fg_color="transparent")

    def _show_tags_dialog(self):
        """Show a popup dialog to select tags for filtering"""
        # Create popup dialog
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Filter by Tags")
        dialog.geometry("500x600")
        dialog.transient(self.root)
        dialog.grab_set()

        # Header
        header = ctk.CTkLabel(
            dialog,
            text="Select tags to filter wallpapers",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.COLORS['text_light']
        )
        header.pack(pady=20, padx=20)

        # Scrollable frame for tag checkboxes
        scroll_frame = ctk.CTkScrollableFrame(
            dialog,
            fg_color=self.COLORS['card_bg'],
            corner_radius=10
        )
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Track checkbox variables and widgets
        tag_vars = {}
        tag_checkboxes = {}

        def get_available_tags():
            """Get tags that are available in currently filtered wallpapers"""
            # Get current filters
            items = self.cache_manager.list_entries()
            provider_filter = self.provider_filter_var.get() if hasattr(self, 'provider_filter_var') else "All Providers"
            color_filter = self.color_filter_var.get() if hasattr(self, 'color_filter_var') else "All Colors"

            # Apply current tag filter (excluding the tag we're potentially adding)
            if hasattr(self, 'selected_tags') and self.selected_tags:
                def item_matches_tags(item):
                    item_path = item.get("path")
                    stats = self.stats_manager.data.get("wallpapers", {}).get(item_path, {})
                    item_tags = set(stats.get("tags", []))
                    return self.selected_tags.issubset(item_tags)
                items = [item for item in items if item_matches_tags(item)]

            # Apply provider filter
            if provider_filter and provider_filter != "All Providers":
                items = [item for item in items if item.get("provider") == provider_filter]

            # Apply color filter
            if color_filter and color_filter != "All Colors":
                dominant_only = self.dominant_only_var.get() if hasattr(self, 'dominant_only_var') else False
                if dominant_only:
                    items = [item for item in items if color_filter == item.get("primary_color")]
                else:
                    items = [item for item in items
                            if color_filter in item.get("color_categories", []) or
                               color_filter == item.get("primary_color")]

            # Count tags in filtered items
            tag_counts = {}
            for item in items:
                item_path = item.get("path")
                stats = self.stats_manager.data.get("wallpapers", {}).get(item_path, {})
                for tag in stats.get("tags", []):
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

            return tag_counts

        def rebuild_tag_list():
            """Rebuild the tag checkbox list with currently available tags"""
            # Clear existing checkboxes
            for widget in scroll_frame.winfo_children():
                widget.destroy()

            # Get available tags
            tag_counts = get_available_tags()
            sorted_tags = sorted(tag_counts.items(), key=lambda x: (-x[1], x[0].lower()))

            # Recreate checkboxes
            for tag, count in sorted_tags:
                if tag not in tag_vars:
                    tag_vars[tag] = ctk.BooleanVar(value=tag in self.selected_tags)
                else:
                    # Update value if tag already exists
                    tag_vars[tag].set(tag in self.selected_tags)

                checkbox = ctk.CTkCheckBox(
                    scroll_frame,
                    text=f"{tag} ({count})",
                    variable=tag_vars[tag],
                    fg_color=self.COLORS['accent'],
                    hover_color=self.COLORS['sidebar_hover'],
                    font=ctk.CTkFont(size=13),
                    command=lambda t=tag: on_tag_toggle(t)
                )
                checkbox.pack(anchor="w", padx=10, pady=5)
                tag_checkboxes[tag] = checkbox

        # Helper function to update filters in real-time
        def on_tag_toggle(tag):
            # Update selected tags from current checkbox states
            self.selected_tags = {t for t, var in tag_vars.items() if var.get()}
            # Reload wallpaper grid immediately
            self._load_wallpaper_grid()
            # Rebuild tag list to show only available tags
            rebuild_tag_list()

        # Initial build of tag list
        rebuild_tag_list()

        # Buttons frame
        buttons_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=20, pady=(0, 20))

        # Clear all button - now with real-time update
        def clear_all():
            # Update filters immediately
            self.selected_tags = set()
            self._load_wallpaper_grid()
            # Rebuild tag list to show all available tags
            rebuild_tag_list()

        clear_btn = ctk.CTkButton(
            buttons_frame,
            text="Clear All",
            fg_color=self.COLORS['card_bg'],
            hover_color=self.COLORS['sidebar_hover'],
            command=clear_all
        )
        clear_btn.pack(side="left", padx=(0, 10))

        # Close button (no longer need Apply since changes are real-time)
        close_btn = ctk.CTkButton(
            buttons_frame,
            text="Close",
            fg_color=self.COLORS['accent'],
            hover_color=self.COLORS['sidebar_hover'],
            command=dialog.destroy
        )
        close_btn.pack(side="right")

    def _on_sort_change(self, choice: str):
        """Handle sort change and filter"""
        self._load_wallpaper_grid()

    def _on_filter_change(self, choice: str = None):
        """Handle filter change"""
        self._load_wallpaper_grid()

    def _refresh_tag_filter(self):
        """Refresh the tag filter dropdown with current tags"""
        if hasattr(self, 'tag_filter_var'):
            # This will be called when returning to Wallpapers view
            # to update the tag list
            pass

    def _show_home_view(self):
        """Show enhanced home/dashboard view with statistics and info"""
        self.stats_manager.data = self.stats_manager._load_data()
        view_container = ctk.CTkFrame(self.content_container, fg_color="transparent")
        view_container.pack(fill="both", expand=True)
        self._view_cache["Home"] = view_container

        scrollable = ctk.CTkScrollableFrame(
            view_container,
            fg_color="transparent"
        )
        scrollable.pack(fill="both", expand=True, padx=20, pady=20)

        header_frame = ctk.CTkFrame(scrollable, fg_color="transparent")
        header_frame.pack(fill="x", pady=(10, 5))

        title = ctk.CTkLabel(
            header_frame,
            text="Dashboard",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=self.COLORS['text_light']
        )
        title.pack(side="left", anchor="w")

        refresh_btn = ctk.CTkButton(
            header_frame,
            text="🔄 Refresh",
            font=ctk.CTkFont(size=13),
            width=100,
            height=32,
            fg_color=self.COLORS['accent'],
            hover_color=self.COLORS['sidebar_hover'],
            corner_radius=8,
            command=self._refresh_home_data
        )
        refresh_btn.pack(side="right", padx=10)

        subtitle = ctk.CTkLabel(
            scrollable,
            text="Overview of your wallpaper system (updates automatically when you return to Home)",
            font=ctk.CTkFont(size=14),
            text_color=self.COLORS['text_muted']
        )
        subtitle.pack(pady=(0, 20), anchor="w")

        stats_frame = ctk.CTkFrame(scrollable, fg_color="transparent")
        stats_frame.pack(fill="x", pady=10)
        for i in range(3):
            stats_frame.grid_columnconfigure(i, weight=1)

        self._create_stat_card(stats_frame, 0, "Service Status",
                              self._get_service_status_text(),
                              self._get_service_status_color())

        cache_count = len(self.cache_manager.list_entries()) if self.cache_manager else 0
        self._create_stat_card(stats_frame, 1, "Cached Wallpapers",
                              f"{cache_count} images",
                              self.COLORS['accent'])

        weather_text = self._get_current_weather_text()
        self._create_stat_card(stats_frame, 2, "Current Weather",
                              weather_text,
                              "#00b4d8")

        stats_frame2 = ctk.CTkFrame(scrollable, fg_color="transparent")
        stats_frame2.pack(fill="x", pady=10)
        for i in range(3):
            stats_frame2.grid_columnconfigure(i, weight=1)

        banned_count = len(self.stats_manager.get_banned_wallpapers())
        self._create_stat_card(stats_frame2, 0, "Banned Wallpapers",
                              f"{banned_count} banned",
                              "#ff4444")

        favorites_count = len(self.stats_manager.get_favorites())
        self._create_stat_card(stats_frame2, 1, "Favorite Wallpapers",
                              f"{favorites_count} favorites",
                              "#ff6b81")

        total_changes = self.stats_manager.get_total_changes()
        self._create_stat_card(stats_frame2, 2, "Total Changes",
                              f"{total_changes} times",
                              "#00e676")

        preview_label = ctk.CTkLabel(
            scrollable,
            text="Current Wallpapers (All Monitors)",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.COLORS['text_light']
        )
        preview_label.pack(pady=(30, 15), anchor="w")

        self.wallpaper_preview_container = ctk.CTkFrame(scrollable, fg_color="transparent")
        self.wallpaper_preview_container.pack(fill="x", pady=10)
        self._create_current_wallpaper_preview_fast(self.wallpaper_preview_container)

        chart_card = ctk.CTkFrame(scrollable, fg_color=self.COLORS['card_bg'], corner_radius=12)
        chart_card.pack(fill="x", pady=(30, 10))

        chart_inner = ctk.CTkFrame(chart_card, fg_color="transparent")
        chart_inner.pack(fill="x", padx=20, pady=20)

        chart_label = ctk.CTkLabel(
            chart_inner,
            text="Usage Statistics",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.COLORS['text_light']
        )
        chart_label.pack(anchor="w", pady=(0, 10))

        info_label = ctk.CTkLabel(
            chart_inner,
            text="Click below to view detailed charts and analytics",
            font=ctk.CTkFont(size=13),
            text_color=self.COLORS['text_muted']
        )
        info_label.pack(anchor="w", pady=(0, 15))

        self.stats_chart_container = ctk.CTkFrame(chart_inner, fg_color="transparent")
        self.stats_chart_container.pack(fill="x")

        load_stats_btn = ctk.CTkButton(
            self.stats_chart_container,
            text="📊 View Detailed Statistics",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=36,
            fg_color=self.COLORS['accent'],
            hover_color=self.COLORS['sidebar_hover'],
            command=lambda: self._load_statistics_chart_lazy()
        )
        load_stats_btn.pack()

        actions_label = ctk.CTkLabel(
            scrollable,
            text="Quick Actions",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.COLORS['text_light']
        )
        actions_label.pack(pady=(30, 15), anchor="w")

        actions_grid = ctk.CTkFrame(scrollable, fg_color="transparent")
        actions_grid.pack(fill="x", pady=10)
        actions_grid.grid_columnconfigure(0, weight=1)
        actions_grid.grid_columnconfigure(1, weight=1)

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

        activity_label = ctk.CTkLabel(
            scrollable,
            text="System Information",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.COLORS['text_light']
        )
        activity_label.pack(pady=(30, 15), anchor="w")

        info_card = ctk.CTkFrame(scrollable, fg_color=self.COLORS['card_bg'], corner_radius=12)
        info_card.pack(fill="x", pady=10)

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

        ctk.CTkLabel(scrollable, text="").pack(pady=20)

    def _create_stat_card(self, parent, col, title, value, color):
        """Create a statistics card"""
        card = ctk.CTkFrame(parent, fg_color=self.COLORS['card_bg'], corner_radius=12)
        card.grid(row=0, column=col, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS['text_muted']
        ).pack(pady=(15, 5))

        ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=color
        ).pack(pady=(5, 15))

    def _create_action_card(self, parent, row, col, title, description, color, command):
        """Create an action card button"""
        card_frame = ctk.CTkFrame(parent, fg_color="transparent")
        card_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

        card = ctk.CTkButton(
            card_frame,
            text=f"{title}\n{description}",
            fg_color=color,
            hover_color=self.COLORS['card_hover'],
            corner_radius=12,
            height=100,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=command
        )
        card.pack(fill="both", expand=True)

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

    def _create_current_wallpaper_preview_fast(self, parent):
        """Create wallpaper preview with optimizations using the info file."""
        wallpaper_path = None
        try:
            info_path = Path(__file__).parent / "current_wallpaper_info.json"
            if info_path.exists():
                with open(info_path, "r", encoding="utf-8") as f:
                    import json
                    data = json.load(f)
                    wallpaper_path = data.get("path")
        except Exception:
            pass

        if not wallpaper_path or not os.path.exists(wallpaper_path):
            preview_card = ctk.CTkFrame(parent, fg_color=self.COLORS['card_bg'], corner_radius=12)
            preview_card.pack(fill="x", pady=10)
            ctk.CTkLabel(
                preview_card,
                text="Unable to detect current wallpaper from info file.",
                font=ctk.CTkFont(size=14),
                text_color=self.COLORS['text_muted']
            ).pack(pady=30)
            return

        preview_card = ctk.CTkFrame(parent, fg_color=self.COLORS['card_bg'], corner_radius=12)
        preview_card.pack(fill="x", pady=10)

        try:
            content_frame = ctk.CTkFrame(preview_card, fg_color="transparent")
            content_frame.pack(fill="both", padx=20, pady=20)

            image_frame = ctk.CTkFrame(content_frame, fg_color=self.COLORS['main_bg'], corner_radius=8)
            image_frame.pack(side="left", padx=(0, 20))

            self._create_image_preview_fast(image_frame, wallpaper_path, size=(200, 120))

            info_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True)

            monitor_label = ctk.CTkLabel(
                info_frame,
                text="Current Wallpaper (Primary)",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=self.COLORS['text_light']
            )
            monitor_label.pack(anchor="w", pady=(0, 10))

            file_name = os.path.basename(wallpaper_path)
            name_label = ctk.CTkLabel(
                info_frame,
                text=f"📄 {file_name[:50]}{'...' if len(file_name) > 50 else ''}",
                font=ctk.CTkFont(size=13),
                text_color=self.COLORS['text_muted'],
                anchor="w"
            )
            name_label.pack(anchor="w", pady=2)

            btn_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
            btn_frame.pack(anchor="w", pady=(10, 0))

            change_btn = ctk.CTkButton(
                btn_frame,
                text="Change",
                width=80,
                height=28,
                fg_color=self.COLORS['accent'],
                hover_color=self.COLORS['sidebar_hover'],
                command=self._change_wallpaper_now
            )
            change_btn.pack(side="left", padx=(0, 10))

        except Exception:
            error_label = ctk.CTkLabel(
                preview_card,
                text="Error displaying current wallpaper",
                font=ctk.CTkFont(size=14),
                text_color=self.COLORS['text_muted']
            )
            error_label.pack(pady=30)

    def _create_image_preview_fast(self, parent, image_path, size=(200, 120)):
        """Create fast image preview with aggressive caching"""
        try:
            cache_key = f"{image_path}_{size[0]}x{size[1]}"
            if cache_key in self.thumbnail_cache:
                img_label = ctk.CTkLabel(parent, image=self.thumbnail_cache[cache_key], text="")
                img_label.pack(padx=10, pady=10)
                return

            from PIL import Image
            img = Image.open(image_path)
            img.thumbnail(size, Image.NEAREST)

            photo = ctk.CTkImage(light_image=img, dark_image=img, size=size)
            self.thumbnail_cache[cache_key] = photo

            img_label = ctk.CTkLabel(parent, image=photo, text="")
            img_label.pack(padx=10, pady=10)
        except Exception:
            error_label = ctk.CTkLabel(
                parent,
                text="Error\nloading",
                font=ctk.CTkFont(size=12),
                text_color=self.COLORS['text_muted']
            )
            error_label.pack(expand=True, pady=50)

    def _create_current_wallpaper_preview(self, parent):
        """Create current wallpaper preview cards showing all monitors"""
        wallpapers = []
        try:
            from main import DesktopWallpaperController
            controller = DesktopWallpaperController()
            wallpapers = controller.get_all_wallpapers()
            controller.close()
        except Exception as e:
            pass

        if not wallpapers:
            preview_card = ctk.CTkFrame(parent, fg_color=self.COLORS['card_bg'], corner_radius=12)
            preview_card.pack(fill="x", pady=10)
            ctk.CTkLabel(
                preview_card,
                text="Unable to detect current wallpapers",
                font=ctk.CTkFont(size=14),
                text_color=self.COLORS['text_muted']
            ).pack(pady=30)
            return

        if not hasattr(self, '_viewed_wallpapers_session'):
            self._viewed_wallpapers_session = set()

        for wallpaper_info in wallpapers:
            current_path = wallpaper_info.get("path")
            if current_path and current_path not in self._viewed_wallpapers_session:
                if current_path in [item.get("path") for item in self.cache_manager.list_entries()]:
                    current_views = self.stats_manager.data.get("wallpapers", {}).get(current_path, {}).get("views", 0)
                    if current_path in self.stats_manager.data.get("wallpapers", {}):
                        self.stats_manager.data["wallpapers"][current_path]["views"] = current_views + 1
                    else:
                        from datetime import datetime
                        self.stats_manager.data.setdefault("wallpapers", {})[current_path] = {
                            "views": 1,
                            "last_viewed": datetime.now().isoformat(),
                            "rating": 0,
                            "favorite": False,
                            "tags": [],
                            "provider": "unknown"
                        }
                    self.stats_manager._save_data()
                    self._viewed_wallpapers_session.add(current_path)

        for wallpaper_info in wallpapers:
            preview_card = ctk.CTkFrame(parent, fg_color=self.COLORS['card_bg'], corner_radius=12)
            preview_card.pack(fill="x", pady=10)
            current_path = wallpaper_info.get("path")
            monitor_idx = wallpaper_info.get("monitor_index", 0)
            monitor_width = wallpaper_info.get("width", 0)
            monitor_height = wallpaper_info.get("height", 0)

            try:
                if current_path and os.path.exists(current_path):
                    content_frame = ctk.CTkFrame(preview_card, fg_color="transparent")
                    content_frame.pack(fill="both", padx=20, pady=20)
                    try:
                        img = Image.open(current_path)
                        img.thumbnail((400, 250), Image.Resampling.LANCZOS)
                        photo = ctk.CTkImage(light_image=img, dark_image=img, size=(400, 250))
                        # Keep reference to prevent garbage collection
                        self.image_references.append(photo)
                        img_label = ctk.CTkLabel(content_frame, image=photo, text="")
                        img_label.pack(side="left", padx=(0, 20))
                    except:
                        pass

                    info_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
                    info_frame.pack(side="left", fill="both", expand=True)

                    monitor_label = ctk.CTkLabel(
                        info_frame,
                        text=f"Monitor {monitor_idx + 1} ({monitor_width}x{monitor_height})",
                        font=ctk.CTkFont(size=16, weight="bold"),
                        text_color=self.COLORS['accent']
                    )
                    monitor_label.pack(anchor="w", pady=(0, 5))

                    filename = os.path.basename(current_path)
                    ctk.CTkLabel(
                        info_frame,
                        text=filename[:40] + "..." if len(filename) > 40 else filename,
                        font=ctk.CTkFont(size=13),
                        text_color=self.COLORS['text_light']
                    ).pack(anchor="w", pady=(0, 10))

                    # Display tags if available
                    tags = self.stats_manager.get_tags(current_path)
                    if tags:
                        tags_text = ", ".join(tags[:5])  # Show up to 5 tags
                        if len(tags) > 5:
                            tags_text += f" +{len(tags) - 5} more"
                        ctk.CTkLabel(
                            info_frame,
                            text=f"🏷️ {tags_text}",
                            font=ctk.CTkFont(size=11),
                            text_color=self.COLORS['text_muted']
                        ).pack(anchor="w", pady=(0, 10))

                    rating = self.stats_manager.get_rating(current_path)
                    is_fav = self.stats_manager.is_favorite(current_path)
                    stats_info = [
                        ("Rating", "★" * rating + "☆" * (5 - rating) if rating > 0 else "Not rated"),
                        ("Favorite", "Yes ♥" if is_fav else "No"),
                        ("Views", str(self.stats_manager.data.get("wallpapers", {}).get(current_path, {}).get("views", 0)))
                    ]
                    for label, value in stats_info:
                        row = ctk.CTkFrame(info_frame, fg_color="transparent")
                        row.pack(fill="x", pady=3)
                        ctk.CTkLabel(
                            row,
                            text=label + ":",
                            font=ctk.CTkFont(size=11),
                            text_color=self.COLORS['text_muted']
                        ).pack(side="left")
                        ctk.CTkLabel(
                            row,
                            text=value,
                            font=ctk.CTkFont(size=11, weight="bold"),
                            text_color=self.COLORS['text_light']
                        ).pack(side="right")
                else:
                    ctk.CTkLabel(
                        preview_card,
                        text=f"Monitor {monitor_idx + 1}: No wallpaper set",
                        font=ctk.CTkFont(size=14),
                        text_color=self.COLORS['text_muted']
                    ).pack(pady=30)
            except Exception as e:
                ctk.CTkLabel(
                    preview_card,
                    text=f"Monitor {monitor_idx + 1}: Unable to load wallpaper",
                    font=ctk.CTkFont(size=14),
                    text_color=self.COLORS['text_muted']
                ).pack(pady=30)

    def _load_statistics_chart_lazy(self):
        """Load statistics chart on demand (lazy loading)"""
        for widget in self.stats_chart_container.winfo_children():
            widget.destroy()

        loading_label = ctk.CTkLabel(
            self.stats_chart_container,
            text="Loading statistics...",
            font=ctk.CTkFont(size=14),
            text_color=self.COLORS['text_muted']
        )
        loading_label.pack(pady=20)
        self.root.update()
        self._create_statistics_chart(self.stats_chart_container)
        loading_label.destroy()

    def _create_statistics_chart(self, parent):
        """Create statistics charts using matplotlib"""
        chart_card = ctk.CTkFrame(parent, fg_color=self.COLORS['card_bg'], corner_radius=12)
        chart_card.pack(fill="x", pady=10)

        try:
            from datetime import datetime, timedelta
            daily_changes = self.stats_manager.get_daily_changes(14)
            provider_stats = self.stats_manager.get_provider_stats(14)
            hourly_dist = self.stats_manager.get_hourly_distribution()

            total_changes = sum(daily_changes.values())
            if total_changes == 0 and not provider_stats and not hourly_dist:
                ctk.CTkLabel(
                    chart_card,
                    text="📊 No statistics available yet!\n\nStart using the wallpaper changer to see:\n• Daily activity trends\n• Provider distribution\n• Hourly usage patterns\n• Most viewed wallpapers\n\nUse the hotkey (ctrl+alt+w) or Quick Actions to change wallpapers!",
                    font=ctk.CTkFont(size=14),
                    text_color=self.COLORS['text_light'],
                    justify="center"
                ).pack(pady=50)
                return

            fig = Figure(figsize=(14, 9), facecolor='#3D2B3F')
            fig.subplots_adjust(left=0.08, right=0.95, top=0.95, bottom=0.08, wspace=0.3, hspace=0.5)
            import matplotlib.gridspec as gridspec
            gs = gridspec.GridSpec(3, 2, figure=fig, height_ratios=[1, 1, 1])

            ax1 = fig.add_subplot(gs[0, 0])
            sorted_dates = sorted(daily_changes.keys())
            values = [daily_changes[d] for d in sorted_dates]
            dates_display = []
            for d in sorted_dates:
                try:
                    dt = datetime.strptime(d, "%Y-%m-%d")
                    dates_display.append(dt.strftime("%m/%d"))
                except:
                    dates_display.append(d[-5:])

            ax1.plot(dates_display, values, color='#E94560', marker='o', linewidth=2,
                    markersize=6, markerfacecolor='#FFD93D', markeredgecolor='#E94560', markeredgewidth=2)
            ax1.fill_between(range(len(values)), values, alpha=0.3, color='#E94560')
            ax1.set_title('Daily Wallpaper Changes (Last 14 Days)', color='white', fontsize=13, pad=10, weight='bold')
            ax1.set_xlabel('Date', color='#B0B0B0', fontsize=10)
            ax1.set_ylabel('Changes', color='#B0B0B0', fontsize=10)
            ax1.tick_params(colors='#B0B0B0', labelsize=9)
            ax1.set_facecolor('#3D2B3F')
            for spine in ax1.spines.values():
                spine.set_edgecolor('#B0B0B0')
                spine.set_linewidth(0.5)
            ax1.grid(True, alpha=0.2, color='#B0B0B0', linestyle='--', axis='y')
            ax1.tick_params(axis='x', rotation=45)

            if provider_stats:
                ax2 = fig.add_subplot(gs[0, 1])
                providers = list(provider_stats.keys())
                counts = list(provider_stats.values())
                colors_map = {
                    'wallhaven': '#00e676',
                    'pexels': '#ffd93d',
                    'reddit': '#ff6b81',
                    'unsplash': '#89b4fa',
                }
                colors = [colors_map.get(p.lower(), '#808080') for p in providers]
                wedges, texts, autotexts = ax2.pie(counts, labels=providers, autopct='%1.1f%%',
                       colors=colors, textprops={'color': 'white', 'fontsize': 10},
                       startangle=90, explode=[0.05]*len(providers))
                for autotext in autotexts:
                    autotext.set_color('black')
                    autotext.set_weight('bold')
                    autotext.set_fontsize(9)
                ax2.set_title('Provider Distribution (Last 14 Days)', color='white', fontsize=13, pad=10, weight='bold')

            if hourly_dist:
                ax3 = fig.add_subplot(gs[1, :])
                hours = list(range(24))
                hourly_counts = [hourly_dist.get(h, 0) for h in hours]
                bars = ax3.bar(hours, hourly_counts, color='#89b4fa', edgecolor='#5b8fd4', linewidth=1.5)
                max_val = max(hourly_counts) if hourly_counts else 1
                for i, (bar, count) in enumerate(zip(bars, hourly_counts)):
                    if max_val > 0:
                        intensity = count / max_val
                        alpha = 0.4 + intensity * 0.6
                        if 6 <= i < 12:
                            bar.set_color((255/255, 217/255, 61/255, alpha))
                        elif 12 <= i < 18:
                            bar.set_color((233/255, 69/255, 96/255, alpha))
                        elif 18 <= i < 22:
                            bar.set_color((137/255, 180/255, 250/255, alpha))
                        else:
                            bar.set_color((176/255, 176/255, 176/255, alpha))
                ax3.set_title('Hourly Activity Distribution', color='white', fontsize=13, pad=10, weight='bold')
                ax3.set_xlabel('Hour of Day', color='#B0B0B0', fontsize=10)
                ax3.set_ylabel('Wallpaper Changes', color='#B0B0B0', fontsize=10)
                ax3.set_xticks(hours)
                ax3.set_xticklabels([f'{h:02d}:00' for h in hours], rotation=45, ha='right')
                ax3.tick_params(colors='#B0B0B0', labelsize=8)
                ax3.set_facecolor('#3D2B3F')
                for spine in ax3.spines.values():
                    spine.set_edgecolor('#B0B0B0')
                    spine.set_linewidth(0.5)
                ax3.grid(True, alpha=0.2, color='#B0B0B0', linestyle='--', axis='y')

            # Tag distribution chart
            tag_stats = self.stats_manager.get_tag_stats(10)
            if tag_stats:
                ax4 = fig.add_subplot(gs[2, :])
                tags = list(tag_stats.keys())
                counts = list(tag_stats.values())

                y_pos = list(range(len(tags)))
                bars = ax4.barh(y_pos, counts, color='#00e676', edgecolor='#00a854', linewidth=1.5)
                max_count = max(counts) if counts else 1
                for i, (bar, count) in enumerate(zip(bars, counts)):
                    intensity = count / max_count
                    alpha = 0.5 + intensity * 0.5
                    bar.set_color((0/255, 230/255, 118/255, alpha))
                ax4.set_yticks(y_pos)
                ax4.set_yticklabels(tags)
                ax4.invert_yaxis()
                ax4.set_xlabel('Wallpaper Count', color='#B0B0B0', fontsize=10)
                ax4.set_title('Top 10 Most Common Tags', color='white', fontsize=13, pad=10, weight='bold')
                ax4.tick_params(colors='#B0B0B0', labelsize=9)
                ax4.set_facecolor('#3D2B3F')
                for spine in ax4.spines.values():
                    spine.set_edgecolor('#B0B0B0')
                    spine.set_linewidth(0.5)
                ax4.grid(True, alpha=0.2, color='#B0B0B0', linestyle='--', axis='x')
            else:
                # Show message if no tags
                ax4 = fig.add_subplot(gs[2, :])
                ax4.text(0.5, 0.5, 'No tags available yet. Tags will appear as wallpapers are downloaded.',
                        ha='center', va='center', transform=ax4.transAxes,
                        color='#B0B0B0', fontsize=12)
                ax4.set_facecolor('#3D2B3F')
                ax4.set_xticks([])
                ax4.set_yticks([])
                for spine in ax4.spines.values():
                    spine.set_visible(False)

            canvas = FigureCanvasTkAgg(fig, master=chart_card)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        except Exception as e:
            import traceback
            error_text = f"Unable to generate charts: {str(e)}"
            print(f"Chart error: {traceback.format_exc()}")
            ctk.CTkLabel(
                chart_card,
                text=error_text[:80],
                font=ctk.CTkFont(size=14),
                text_color=self.COLORS['text_muted']
            ).pack(pady=30)

    def _show_duplicates_view(self):
        """Show duplicate wallpapers detection and management"""
        from duplicate_detector import DuplicateDetector

        view_container = ctk.CTkFrame(self.content_container, fg_color="transparent")
        view_container.pack(fill="both", expand=True)
        self._view_cache["Duplicates"] = view_container

        # Header
        header_frame = ctk.CTkFrame(view_container, fg_color="transparent", height=70)
        header_frame.pack(fill="x", padx=30, pady=(20, 0))
        header_frame.pack_propagate(False)

        title = ctk.CTkLabel(
            header_frame,
            text="Duplicate Detection",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=self.COLORS['text_light']
        )
        title.pack(side="left", anchor="w")

        # Right side controls
        controls_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        controls_frame.pack(side="right")

        # Sensitivity selector
        sensitivity_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        sensitivity_frame.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(
            sensitivity_frame,
            text="Sensitivity:",
            font=ctk.CTkFont(size=13),
            text_color=self.COLORS['text_muted']
        ).pack(side="left", padx=(0, 8))

        # Initialize sensitivity variable if not exists
        if not hasattr(self, 'duplicate_sensitivity'):
            self.duplicate_sensitivity = ctk.StringVar(value="Similar")

        sensitivity_menu = ctk.CTkOptionMenu(
            sensitivity_frame,
            variable=self.duplicate_sensitivity,
            values=["Exact", "Very Similar", "Similar", "Somewhat Similar"],
            width=150,
            fg_color=self.COLORS['card_bg'],
            button_color=self.COLORS['accent'],
            button_hover_color=self.COLORS['sidebar_hover']
        )
        sensitivity_menu.pack(side="left")

        # Scan button
        scan_btn = ctk.CTkButton(
            controls_frame,
            text="🔍 Scan for Duplicates",
            font=ctk.CTkFont(size=14),
            width=180,
            height=40,
            fg_color=self.COLORS['accent'],
            hover_color=self.COLORS['sidebar_hover'],
            corner_radius=8,
            command=self._scan_for_duplicates
        )
        scan_btn.pack(side="left")

        # Scrollable content
        scrollable = ctk.CTkScrollableFrame(
            view_container,
            fg_color="transparent",
            scrollbar_button_color=self.COLORS['accent'],
            scrollbar_button_hover_color=self.COLORS['sidebar_hover']
        )
        scrollable.pack(fill="both", expand=True, padx=30, pady=20)

        # Store reference for updates
        self.duplicates_content = scrollable

        # Initial message
        self._show_duplicates_placeholder()

    def _show_duplicates_placeholder(self):
        """Show placeholder message"""
        for widget in self.duplicates_content.winfo_children():
            widget.destroy()

        placeholder = ctk.CTkLabel(
            self.duplicates_content,
            text="Click 'Scan for Duplicates' to find similar wallpapers\n\nThis will compare all cached wallpapers using perceptual hashing.",
            font=ctk.CTkFont(size=16),
            text_color=self.COLORS['text_muted'],
            justify="center"
        )
        placeholder.pack(pady=100)

    def _scan_for_duplicates(self):
        """Scan for duplicates and display results"""
        from duplicate_detector import DuplicateDetector

        # Clear current content
        for widget in self.duplicates_content.winfo_children():
            widget.destroy()

        # Show scanning message
        scanning_label = ctk.CTkLabel(
            self.duplicates_content,
            text="Scanning wallpapers for duplicates...",
            font=ctk.CTkFont(size=16),
            text_color=self.COLORS['text_light']
        )
        scanning_label.pack(pady=50)
        self.root.update()

        # Get all wallpaper paths
        entries = self.cache_manager._index.get("items", [])
        image_paths = [entry.get("path") for entry in entries if entry.get("path") and os.path.exists(entry.get("path"))]

        if len(image_paths) < 2:
            scanning_label.destroy()
            ctk.CTkLabel(
                self.duplicates_content,
                text="Not enough wallpapers to compare.\nDownload at least 2 wallpapers first.",
                font=ctk.CTkFont(size=16),
                text_color=self.COLORS['text_muted']
            ).pack(pady=100)
            return

        # Get selected sensitivity
        sensitivity_map = {
            "Exact": DuplicateDetector.EXACT_MATCH,
            "Very Similar": DuplicateDetector.VERY_SIMILAR,
            "Similar": DuplicateDetector.SIMILAR,
            "Somewhat Similar": DuplicateDetector.SOMEWHAT_SIMILAR
        }
        sensitivity = self.duplicate_sensitivity.get()
        threshold = sensitivity_map.get(sensitivity, DuplicateDetector.SIMILAR)

        # Find duplicates
        detector = DuplicateDetector()
        duplicates = detector.find_duplicates(image_paths, threshold=threshold)

        scanning_label.destroy()

        if not duplicates:
            ctk.CTkLabel(
                self.duplicates_content,
                text=f"No duplicates found!\n\nScanned {len(image_paths)} wallpapers - all unique.",
                font=ctk.CTkFont(size=16),
                text_color=self.COLORS['text_light']
            ).pack(pady=100)
            return

        # Show results header
        results_header = ctk.CTkFrame(self.duplicates_content, fg_color="transparent")
        results_header.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            results_header,
            text=f"Found {len(duplicates)} similar pair(s)",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.COLORS['text_light']
        ).pack(side="left")

        # Display each duplicate pair
        for idx, (path1, path2, distance) in enumerate(duplicates, 1):
            self._create_duplicate_comparison_card(path1, path2, distance, idx)

    def _create_duplicate_comparison_card(self, path1: str, path2: str, distance: int, pair_num: int):
        """Create a card showing two duplicate wallpapers side by side"""
        from duplicate_detector import DuplicateDetector

        detector = DuplicateDetector()
        similarity = detector.get_similarity_description(distance)

        # Card container
        card = ctk.CTkFrame(
            self.duplicates_content,
            fg_color=self.COLORS['card_bg'],
            corner_radius=12
        )
        card.pack(fill="x", pady=10)

        # Header with similarity info
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=15)

        ctk.CTkLabel(
            header,
            text=f"Pair #{pair_num}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.COLORS['text_light']
        ).pack(side="left")

        similarity_label = ctk.CTkLabel(
            header,
            text=f"{similarity} (distance: {distance})",
            font=ctk.CTkFont(size=14),
            text_color=self.COLORS['accent']
        )
        similarity_label.pack(side="left", padx=20)

        # Comparison frame
        comparison = ctk.CTkFrame(card, fg_color="transparent")
        comparison.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Left wallpaper
        self._create_duplicate_item(comparison, path1, "left", pair_num, path2)

        # VS label
        ctk.CTkLabel(
            comparison,
            text="VS",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.COLORS['text_muted']
        ).pack(side="left", padx=20)

        # Right wallpaper
        self._create_duplicate_item(comparison, path2, "right", pair_num, path1)

    def _create_duplicate_item(self, parent, image_path: str, side: str, pair_num: int, other_path: str):
        """Create one side of duplicate comparison"""
        container = ctk.CTkFrame(parent, fg_color=self.COLORS['main_bg'], corner_radius=8)
        container.pack(side="left", fill="both", expand=True, padx=10)

        # Load and display image
        try:
            pil_image = Image.open(image_path)
            # Resize for preview
            pil_image.thumbnail((400, 300), Image.Resampling.LANCZOS)
            photo = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=pil_image.size)

            img_label = ctk.CTkLabel(container, image=photo, text="")
            img_label.pack(pady=15)
            self.image_references.append(photo)
        except Exception as e:
            ctk.CTkLabel(
                container,
                text=f"Error loading image\n{str(e)}",
                text_color=self.COLORS['error']
            ).pack(pady=15)

        # Info
        info_frame = ctk.CTkFrame(container, fg_color="transparent")
        info_frame.pack(fill="x", padx=15, pady=(0, 10))

        filename = os.path.basename(image_path)
        ctk.CTkLabel(
            info_frame,
            text=filename[:40] + "..." if len(filename) > 40 else filename,
            font=ctk.CTkFont(size=11),
            text_color=self.COLORS['text_muted']
        ).pack()

        # Get metadata
        entry = next((e for e in self.cache_manager._index.get("items", []) if e.get("path") == image_path), None)
        if entry:
            source = entry.get("source_info", "Unknown")[:50]
            ctk.CTkLabel(
                info_frame,
                text=source,
                font=ctk.CTkFont(size=10),
                text_color=self.COLORS['text_muted']
            ).pack()

        # Action buttons
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(5, 15))

        # Keep button
        keep_btn = ctk.CTkButton(
            btn_frame,
            text="✓ Keep",
            width=80,
            height=32,
            fg_color="#00e676",
            hover_color="#00c853",
            command=lambda: self._keep_wallpaper(image_path, other_path, pair_num)
        )
        keep_btn.pack(side="left", padx=5)

        # Delete button
        delete_btn = ctk.CTkButton(
            btn_frame,
            text="✕ Delete",
            width=80,
            height=32,
            fg_color="#ff6b81",
            hover_color="#ff4757",
            command=lambda: self._delete_duplicate(image_path, other_path, pair_num)
        )
        delete_btn.pack(side="left", padx=5)

    def _keep_wallpaper(self, keep_path: str, delete_path: str, pair_num: int):
        """Keep one wallpaper and delete the other"""
        self._delete_duplicate(delete_path, keep_path, pair_num)

    def _delete_duplicate(self, delete_path: str, keep_path: str, pair_num: int):
        """Delete a duplicate wallpaper"""
        try:
            # Remove from cache
            items = self.cache_manager._index.get("items", [])
            self.cache_manager._index["items"] = [item for item in items if item.get("path") != delete_path]
            self.cache_manager._save()

            # Delete file
            if os.path.exists(delete_path):
                os.remove(delete_path)

            # Show success message
            print(f"[DUPLICATES] Deleted: {os.path.basename(delete_path)}")

            # Rescan to update view
            self._scan_for_duplicates()

        except Exception as e:
            print(f"[ERROR] Failed to delete duplicate: {e}")
            # Show error message
            ctk.CTkMessagebox(
                title="Error",
                message=f"Failed to delete wallpaper:\n{str(e)}",
                icon="cancel"
            )

    def _show_settings_view(self):
        """Show fully editable settings"""
        view_container = ctk.CTkFrame(self.content_container, fg_color="transparent")
        view_container.pack(fill="both", expand=True)
        self._view_cache["Settings"] = view_container

        scrollable = ctk.CTkScrollableFrame(
            view_container,
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

        from config import (
            Provider, RotateProviders, Query, PurityLevel, ScreenResolution,
            WallhavenSorting, WallhavenTopRange, PexelsMode, PexelsQuery, RedditSettings,
            SchedulerSettings, CacheSettings, KeyBind
        )

        self.provider_var = ctk.StringVar(value=Provider)
        self.rotate_providers_var = ctk.BooleanVar(value=RotateProviders)
        self.query_var = ctk.StringVar(value=Query)
        self.purity_var = ctk.StringVar(value=PurityLevel)
        self.resolution_var = ctk.StringVar(value=ScreenResolution)
        self.sorting_var = ctk.StringVar(value=WallhavenSorting)
        self.toprange_var = ctk.StringVar(value=WallhavenTopRange)
        self.pexels_mode_var = ctk.StringVar(value=PexelsMode)
        self.pexels_query_var = ctk.StringVar(value=PexelsQuery)

        reddit_subreddits = ", ".join(RedditSettings.get("subreddits", ["wallpapers"]))
        self.reddit_subreddits_var = ctk.StringVar(value=reddit_subreddits)
        self.reddit_sort_var = ctk.StringVar(value=RedditSettings.get("sort", "hot"))
        self.reddit_time_var = ctk.StringVar(value=RedditSettings.get("time_filter", "day"))
        self.reddit_limit_var = ctk.IntVar(value=RedditSettings.get("limit", 60))
        self.reddit_score_var = ctk.IntVar(value=RedditSettings.get("min_score", 0))
        self.reddit_nsfw_var = ctk.BooleanVar(value=RedditSettings.get("allow_nsfw", False))

        self.scheduler_enabled_var = ctk.BooleanVar(value=SchedulerSettings.get("enabled", True))
        self.interval_var = ctk.IntVar(value=SchedulerSettings.get("interval_minutes", 45))
        self.jitter_var = ctk.IntVar(value=SchedulerSettings.get("jitter_minutes", 10))

        self.cache_max_var = ctk.IntVar(value=CacheSettings.get("max_items", 60))
        self.cache_offline_var = ctk.BooleanVar(value=CacheSettings.get("enable_offline_rotation", True))

        self.keybind_var = ctk.StringVar(value=KeyBind)

        provider_section = self._create_section(scrollable, "Provider Settings")
        self._add_setting_row(provider_section, "Default Provider:", "dropdown", self.provider_var,
                            ["wallhaven", "pexels", "reddit"])
        self._add_help_text(provider_section, "Choose which service to download wallpapers from")
        self._add_setting_row(provider_section, "Search Query:", "entry", self.query_var)
        self._add_help_text(provider_section, "Keywords to search for wallpapers (e.g., 'nature', 'technology')")
        self._add_setting_row(provider_section, "Enable Provider Rotation", "checkbox", self.rotate_providers_var)
        self._add_help_text(provider_section, "Automatically rotate between different providers")

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

        pexels_section = self._create_section(scrollable, "Pexels Settings")
        self._add_setting_row(pexels_section, "Mode:", "dropdown", self.pexels_mode_var,
                            ["search", "curated"])
        self._add_help_text(pexels_section, "search=Use search query, curated=Get curated high-quality photos")
        self._add_setting_row(pexels_section, "Search Query:", "entry", self.pexels_query_var)
        self._add_help_text(pexels_section, "Search term when using 'search' mode (e.g., nature, abstract, minimal)")

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

        scheduler_section = self._create_section(scrollable, "Scheduler Settings")
        self._add_setting_row(scheduler_section, "Enable Scheduler", "checkbox", self.scheduler_enabled_var)
        self._add_help_text(scheduler_section, "Automatically change wallpaper at regular intervals")
        self._add_setting_row(scheduler_section, "Interval (minutes):", "spinbox", self.interval_var, [1, 1440])
        self._add_help_text(scheduler_section, "How often to change wallpaper (in minutes)")
        self._add_setting_row(scheduler_section, "Jitter (minutes):", "spinbox", self.jitter_var, [0, 60])
        self._add_help_text(scheduler_section, "Random variation to add to interval (prevents predictability)")

        cache_section = self._create_section(scrollable, "Cache Settings")
        self._add_setting_row(cache_section, "Max Cache Items:", "spinbox", self.cache_max_var, [10, 500])
        self._add_help_text(cache_section, "Maximum number of wallpapers to store in cache")
        self._add_setting_row(cache_section, "Enable Offline Rotation", "checkbox", self.cache_offline_var)
        self._add_help_text(cache_section, "Use cached wallpapers when internet is unavailable")

        hotkey_section = self._create_section(scrollable, "Hotkey Settings")
        self._add_setting_row(hotkey_section, "Hotkey:", "entry", self.keybind_var)
        self._add_help_text(hotkey_section, "Use format: ctrl+alt+w, ctrl+shift+p, etc.")

        self._add_section_header(scrollable, "ADVANCED SETTINGS")

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

        from config import CacheSettings
        cache_dir = CacheSettings.get("directory") or os.path.join(os.path.expanduser("~"), "WallpaperChangerCache")
        self.cache_dir_var = ctk.StringVar(value=cache_dir)

        folders_section = self._create_section(scrollable, "Folders Configuration")
        self._add_setting_row(folders_section, "Cache Directory:", "entry", self.cache_dir_var)
        self._add_help_text(folders_section, "Location where wallpapers are cached. Leave empty for default.")

        from config import SchedulerSettings
        self.initial_delay_var = ctk.IntVar(value=SchedulerSettings.get("initial_delay_minutes", 1))

        adv_scheduler_section = self._create_section(scrollable, "Advanced Scheduler Settings")
        self._add_setting_row(adv_scheduler_section, "Initial Delay (minutes):", "spinbox",
                            self.initial_delay_var, [0, 60])
        self._add_help_text(adv_scheduler_section, "Delay before first wallpaper change after startup")

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
        """Create a settings section frame with better visual separation"""
        ctk.CTkLabel(parent, text="", height=10).pack()
        header_frame = ctk.CTkFrame(parent, fg_color="transparent")
        header_frame.pack(fill="x", pady=(10, 5), padx=5)
        indicator = ctk.CTkFrame(
            header_frame,
            fg_color=self.COLORS['accent'],
            width=4,
            height=25,
            corner_radius=2
        )
        indicator.pack(side="left", padx=(0, 10))
        section_label = ctk.CTkLabel(
            header_frame,
            text=title,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.COLORS['accent']
        )
        section_label.pack(side="left", anchor="w")
        section_frame = ctk.CTkFrame(
            parent,
            fg_color=self.COLORS['card_bg'],
            corner_radius=12,
            border_width=1,
            border_color=self.COLORS['card_hover']
        )
        section_frame.pack(fill="x", pady=(5, 15), padx=5)
        return section_frame

    def _add_setting_row(self, section_frame, label_text, widget_type, variable, options=None):
        """Add a setting row with label and widget"""
        row_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
        row_frame.pack(fill="x", padx=25, pady=10)

        if widget_type == "checkbox":
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
            label = ctk.CTkLabel(
                row_frame,
                text=label_text,
                text_color=self.COLORS['text_light'],
                font=ctk.CTkFont(size=13),
                width=250
            )
            label.pack(side="left", anchor="w")

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
            corner_radius=6,
            border_width=1,
            border_color=self.COLORS['card_hover']
        )
        help_frame.pack(fill="x", padx=25, pady=(0, 8))
        help_label = ctk.CTkLabel(
            help_frame,
            text=f"💡 {text}",
            text_color="#89b4fa",
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
        separator = ctk.CTkFrame(header_frame, height=2, fg_color=self.COLORS['accent'])
        separator.pack(fill="x", pady=(5, 0))

    def _save_settings(self):
        """Save all settings to config.py"""
        try:
            config_path = Path(__file__).parent / "config.py"
            with open(config_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
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
                elif line.startswith('PexelsQuery = '):
                    new_lines.append(f'PexelsQuery = "{self.pexels_query_var.get()}"\n')
                elif line.startswith('KeyBind = '):
                    new_lines.append(f'KeyBind = "{self.keybind_var.get()}"\n')
                elif '"subreddits":' in line:
                    subreddits = [s.strip() for s in self.reddit_subreddits_var.get().split(',')]
                    new_lines.append(f'    "subreddits": {subreddits},\n')
                elif '"sort":' in line and 'RedditSettings' in ''.join(new_lines[-5:]):
                    new_lines.append(f'    "sort": "{self.reddit_sort_var.get()}",\n')
                elif line.startswith('"time_filter":'):
                    new_lines.append(f'    "time_filter": "{self.reddit_time_var.get()}",\n')
                elif line.startswith('"limit":') and 'RedditSettings' in ''.join(new_lines[-10:]):
                    new_lines.append(f'    "limit": {self.reddit_limit_var.get()},\n')
                elif line.startswith('"min_score":'):
                    new_lines.append(f'    "min_score": {self.reddit_score_var.get()},\n')
                elif line.startswith('"allow_nsfw":'):
                    new_lines.append(f'    "allow_nsfw": {self.reddit_nsfw_var.get()},\n')
                elif line.startswith('"enabled":') and 'SchedulerSettings' in ''.join(new_lines[-5:]):
                    new_lines.append(f'    "enabled": {self.scheduler_enabled_var.get()},\n')
                elif line.startswith('"interval_minutes":'):
                    new_lines.append(f'    "interval_minutes": {self.interval_var.get()},\n')
                elif line.startswith('"jitter_minutes":'):
                    new_lines.append(f'    "jitter_minutes": {self.jitter_var.get()},\n')
                elif line.startswith('"initial_delay_minutes":'):
                    new_lines.append(f'    "initial_delay_minutes": {self.initial_delay_var.get()},\n')
                elif line.startswith('"max_items":'):
                    new_lines.append(f'    "max_items": {self.cache_max_var.get()},\n')
                elif line.startswith('"enable_offline_rotation":'):
                    new_lines.append(f'    "enable_offline_rotation": {self.cache_offline_var.get()},\n')
                elif line.startswith('"directory":') and 'CacheSettings' in ''.join(new_lines[-3:]):
                    cache_dir_value = self.cache_dir_var.get().strip()
                    if cache_dir_value:
                        new_lines.append(f'    "directory": r"{cache_dir_value}",\n')
                    else:
                        new_lines.append(f'    "directory": "",\n')
                else:
                    new_lines.append(line)

            with open(config_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)

            env_path = Path(__file__).parent / '.env'
            env_lines = []
            if env_path.exists():
                with open(env_path, 'r', encoding='utf-8') as f:
                    env_lines = f.readlines()

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
                    if line.startswith(f'{key}=') :
                        new_env_lines.append(f'{key}={value}\n')
                        keys_found.add(key)
                        found = True
                        break
                if not found:
                    new_env_lines.append(line)
            for key, value in updated_keys.items():
                if key not in keys_found:
                    new_env_lines.append(f'{key}={value}\n')
            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(new_env_lines)

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
        view_container = ctk.CTkFrame(self.content_container, fg_color="transparent")
        view_container.pack(fill="both", expand=True)
        self._view_cache["Logs"] = view_container

        title = ctk.CTkLabel(
            view_container,
            text="Application Logs",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.COLORS['text_light']
        )
        title.pack(pady=(20, 10), padx=20, anchor="w")

        btn_frame = ctk.CTkFrame(view_container, fg_color="transparent")
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

        log_frame = ctk.CTkFrame(view_container, fg_color=self.COLORS['card_bg'], corner_radius=12)
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
                    recent_lines = lines[-500:]
                    self.log_textbox.delete("1.0", "end")
                    self.log_textbox.insert("1.0", "".join(recent_lines))
                    self.log_textbox.see("end")
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
        if self.pid_file.exists():
            try:
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                import psutil
                if psutil.pid_exists(pid):
                    print(f"Service already running (PID: {pid})")
                    return
            except:
                pass

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
            with open(self.signal_file, 'w') as f:
                f.write('change')
            print("Wallpaper change requested")
        except Exception as e:
            print(f"Error requesting wallpaper change: {e}")

    def _change_wallpaper_on_monitors(self, affected_monitors: List[Dict]):
        """Change wallpaper on specific monitors"""
        try:
            from main import DesktopWallpaperController
            from PIL import Image
            from weather_overlay import WeatherOverlay, WeatherInfo
            from weather_rotation import WeatherRotationController
            from config import WeatherOverlaySettings, WeatherRotationSettings
            import tempfile
            import time

            banned_paths = self.stats_manager.get_banned_wallpapers()
            weather_overlay = WeatherOverlay(WeatherOverlaySettings)
            weather_info = None
            if weather_overlay.enabled:
                try:
                    weather_controller = WeatherRotationController(WeatherRotationSettings, None)
                    weather_decision = weather_controller.evaluate("gui_ban")
                    if weather_decision:
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
                except:
                    pass

            controller = DesktopWallpaperController()
            for monitor_info in affected_monitors:
                monitor_idx = monitor_info.get("monitor_index")
                monitor_id = monitor_info.get("monitor_id")
                monitor_label = f"Monitor {monitor_idx + 1}"
                entry = self.cache_manager.get_random(
                    monitor_label=monitor_label,
                    banned_paths=banned_paths
                ) or self.cache_manager.get_random(banned_paths=banned_paths)
                if not entry:
                    print(f"No available wallpaper for {monitor_label}")
                    continue
                wallpaper_path = entry.get("path")
                if weather_overlay.enabled and weather_info:
                    try:
                        temp_dir = tempfile.gettempdir()
                        timestamp = int(time.time())
                        base_name = Path(wallpaper_path).stem
                        temp_overlay_path = os.path.join(temp_dir, f"wallpaper_overlay_ban_{timestamp}_{base_name}.jpg")
                        target_size = (monitor_info.get('width'), monitor_info.get('height'))
                        if weather_overlay.apply_overlay(wallpaper_path, temp_overlay_path, weather_info, target_size):
                            wallpaper_path = temp_overlay_path
                    except:
                        pass
                if not wallpaper_path.lower().endswith('.bmp'):
                    bmp_path = str(Path(wallpaper_path).with_suffix('.bmp'))
                    img = Image.open(wallpaper_path)
                    img.save(bmp_path, 'BMP')
                    wallpaper_path = bmp_path
                controller.set_wallpaper(monitor_id, wallpaper_path)
                self.stats_manager.log_wallpaper_change(
                    entry.get("path"),
                    provider=entry.get("provider", "unknown"),
                    action="ban_replace"
                )
            controller.close()
        except Exception as e:
            print(f"Error changing wallpaper on monitors: {e}")

    def _apply_wallpaper(self, item: Dict[str, Any]):
        """Show monitor selection dialog and apply wallpaper"""
        self._show_monitor_selection_dialog(item)

    def _set_wallpaper_from_cache(self, wallpaper_path: str):
        """Helper method to apply wallpaper from path"""
        # Find the item in cache by path
        for item in self.cache_manager.list_entries():
            if item.get("path") == wallpaper_path:
                self._apply_wallpaper(item)
                return
        self.show_toast("Error", "Wallpaper not found in cache")

    def _toggle_favorite(self, wallpaper_path: str, button: ctk.CTkButton = None):
        """Toggle favorite status for a wallpaper"""
        is_fav = self.stats_manager.toggle_favorite(wallpaper_path)

        # Update UI button if provided
        if button:
            button.configure(
                text="♥" if is_fav else "♡",
                fg_color="#ff6b81" if is_fav else "transparent"
            )

    def _toggle_ban(self, wallpaper_path: str, button: ctk.CTkButton):
        """Toggle ban status for a wallpaper"""
        is_banned = self.stats_manager.toggle_ban(wallpaper_path)
        button.configure(
            text="🚫" if is_banned else "⊘",
            fg_color="#ff4444" if is_banned else "transparent"
        )
        if is_banned:
            try:
                from main import DesktopWallpaperController
                controller = DesktopWallpaperController()
                current_wallpapers = controller.get_all_wallpapers()
                controller.close()
                affected_monitors = []
                for wp_info in current_wallpapers:
                    if wp_info.get("path") == wallpaper_path:
                        affected_monitors.append(wp_info)
                if affected_monitors:
                    self._change_wallpaper_on_monitors(affected_monitors)
                    monitor_names = ", ".join([f"Monitor {wp['monitor_index'] + 1}" for wp in affected_monitors])
                    self.show_toast(
                        "Wallpaper Banned & Replaced",
                        f"Changed wallpaper on {monitor_names}",
                        duration=3000
                    )
                else:
                    self.show_toast("Wallpaper Banned", "This wallpaper will be excluded from rotation", duration=2000)
            except Exception as e:
                self.show_toast("Wallpaper Banned", "This wallpaper will be excluded from rotation", duration=2000)
        else:
            self.show_toast("Wallpaper Unbanned", "This wallpaper is now available again", duration=2000)

    def _delete_wallpaper(self, wallpaper_path: str, card_widget, item: Dict[str, Any]):
        """Permanently delete a wallpaper from cache"""
        import tkinter.messagebox as messagebox

        # Confirm deletion
        confirm = messagebox.askyesno(
            "Delete Wallpaper",
            f"Are you sure you want to permanently delete this wallpaper?\n\nThis action cannot be undone.",
            icon='warning'
        )

        if not confirm:
            return

        try:
            # Remove from disk
            if os.path.exists(wallpaper_path):
                os.remove(wallpaper_path)
                print(f"[DELETE] Removed file: {wallpaper_path}")

            # Remove from cache index
            self.cache_manager._index["items"] = [
                i for i in self.cache_manager._index.get("items", [])
                if i.get("path") != wallpaper_path
            ]
            self.cache_manager._save()
            print(f"[DELETE] Removed from cache index")

            # Remove from statistics
            if wallpaper_path in self.stats_manager.data.get("wallpapers", {}):
                del self.stats_manager.data["wallpapers"][wallpaper_path]
                self.stats_manager._save()
                print(f"[DELETE] Removed from statistics")

            # Remove from thumbnail cache
            if wallpaper_path in self.thumbnail_cache:
                del self.thumbnail_cache[wallpaper_path]

            # Hide the card from UI
            card_widget.destroy()

            self.show_toast("Deleted", "Wallpaper permanently deleted", duration=2000)

        except Exception as e:
            print(f"[DELETE ERROR] {e}")
            self.show_toast("Error", f"Failed to delete: {str(e)}", duration=3000)

    def _set_rating(self, wallpaper_path: str, rating: int, star_buttons: List = None):
        """Set rating for a wallpaper"""
        self.stats_manager.set_rating(wallpaper_path, rating)

        # Update UI buttons if provided
        if star_buttons:
            for i, btn in enumerate(star_buttons, 1):
                if i <= rating:
                    btn.configure(text="★", text_color="#ffd700")
                else:
                    btn.configure(text="☆", text_color=self.COLORS['text_muted'])

    def _show_monitor_selection_dialog(self, item: Dict[str, Any]):
        """Show dialog to choose monitor for wallpaper"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Select Monitor")
        dialog.geometry("450x500")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"{x}+{y}")

        title = ctk.CTkLabel(
            dialog,
            text="Choose Monitor",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.COLORS['text_light']
        )
        title.pack(pady=(20, 10))

        info = ctk.CTkLabel(
            dialog,
            text="Choose which monitor to apply this wallpaper to:",
            font=ctk.CTkFont(size=13),
            text_color=self.COLORS['text_muted']
        )
        info.pack(pady=(0, 20))

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
            weather_overlay = WeatherOverlay(WeatherOverlaySettings)
            if weather_overlay.enabled:
                try:
                    weather_controller = WeatherRotationController(WeatherRotationSettings, None)
                    weather_decision = weather_controller.evaluate("gui")
                    if weather_decision:
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
                        temp_dir = tempfile.gettempdir()
                        timestamp = int(time.time())
                        base_name = Path(wallpaper_path).stem
                        temp_overlay_path = os.path.join(temp_dir, f"wallpaper_overlay_gui_{timestamp}_{base_name}.jpg")
                        target_size = None
                        if monitor_selection != "All Monitors" and monitors_list and monitor_idx is not None:
                            mon = monitors_list[monitor_idx]
                            target_size = (mon.get('width'), mon.get('height'))
                        if weather_overlay.apply_overlay(wallpaper_path, temp_overlay_path, weather_info, target_size):
                            wallpaper_path = temp_overlay_path
                except Exception as e:
                    pass

            if not wallpaper_path.lower().endswith('.bmp'):
                bmp_path = str(Path(wallpaper_path).with_suffix('.bmp'))
                img = Image.open(wallpaper_path)
                img.save(bmp_path, 'BMP')
                wallpaper_path = bmp_path

            if monitor_selection == "All Monitors":
                ctypes.windll.user32.SystemParametersInfoW(20, 0, wallpaper_path, 3)
                self.show_toast(
                    "Wallpaper Changed",
                    "Applied to all monitors",
                    original_path,
                    duration=4000
                )
                self._show_success_dialog("Wallpaper applied to all monitors!")
            else:
                if monitor_idx is None:
                    monitor_idx = int(monitor_selection.split()[1]) - 1
                if monitors_list is None:
                    manager = DesktopWallpaperController()
                    monitors_list = manager.enumerate_monitors()
                else:
                    manager = DesktopWallpaperController()
                if monitor_idx < len(monitors_list):
                    manager.set_wallpaper(monitors_list[monitor_idx]["id"], wallpaper_path)
                    manager.close()
                    self.show_toast(
                        "Wallpaper Changed",
                        f"Applied to {monitor_selection}",
                        original_path,
                        duration=4000
                    )
                    self._show_success_dialog(f"Wallpaper applied to {monitor_selection}!")
                else:
                    manager.close()
                    self._show_error_dialog("Invalid monitor selection")

            self.stats_manager.log_wallpaper_change(
                original_path,
                provider=item.get("provider", "unknown"),
                action="manual"
            )
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
        self.root.destroy()

    def show_toast(self, title: str, message: str, image_path: Optional[str] = None, duration: int = 3000):
        """Show a toast notification"""
        toast = ctk.CTkToplevel(self.root)
        toast.withdraw()
        toast.overrideredirect(True)
        toast.attributes('-topmost', True)
        screen_width = toast.winfo_screenwidth()
        screen_height = toast.winfo_screenheight()
        toast_width = 350
        toast_height = 120 if not image_path else 180
        x = screen_width - toast_width - 20
        y = screen_height - toast_height - 60
        toast.geometry(f"{toast_width}x{toast_height}+{x}+{y}")

        toast_frame = ctk.CTkFrame(
            toast,
            fg_color=self.COLORS['card_bg'],
            border_color=self.COLORS['accent'],
            border_width=2,
            corner_radius=12
        )
        toast_frame.pack(fill="both", expand=True, padx=5, pady=5)

        if image_path and os.path.exists(image_path):
            try:
                img = Image.open(image_path)
                img.thumbnail((80, 80), Image.Resampling.LANCZOS)
                photo = ctk.CTkImage(light_image=img, dark_image=img, size=(80, 80))
                img_label = ctk.CTkLabel(toast_frame, image=photo, text="")
                img_label.pack(side="left", padx=10, pady=10)
                toast_frame.image = photo
            except:
                pass

        text_frame = ctk.CTkFrame(toast_frame, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            text_frame,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.COLORS['text_light']
        ).pack(anchor="w")

        ctk.CTkLabel(
            text_frame,
            text=message,
            font=ctk.CTkFont(size=11),
            text_color=self.COLORS['text_muted'],
            wraplength=200
        ).pack(anchor="w", pady=(5, 0))

        toast.deiconify()
        self.toast_windows.append(toast)
        toast.attributes('-alpha', 0.0)

        def fade_in(alpha=0.0):
            if alpha < 1.0:
                alpha += 0.1
                toast.attributes('-alpha', alpha)
                toast.after(30, lambda: fade_in(alpha))
        fade_in()

        def close_toast():
            def fade_out(alpha=1.0):
                if alpha > 0.0:
                    alpha -= 0.1
                    try:
                        toast.attributes('-alpha', alpha)
                        toast.after(30, lambda: fade_out(alpha))
                    except:
                        pass
                else:
                    try:
                        toast.destroy()
                        if toast in self.toast_windows:
                            self.toast_windows.remove(toast)
                    except:
                        pass
            fade_out()
        toast.after(duration, close_toast)

    def _show_fullscreen_viewer(self, image_path: str):
        """Show wallpaper in fullscreen viewer"""
        if not os.path.exists(image_path):
            self.show_toast("Error", "Image file not found")
            return

        # Create fullscreen window
        viewer = ctk.CTkToplevel(self.root)
        viewer.title("Wallpaper Viewer")
        viewer.attributes("-fullscreen", True)
        viewer.configure(fg_color="#000000")

        # Load image
        try:
            img = Image.open(image_path)

            # Get screen dimensions
            screen_width = viewer.winfo_screenwidth()
            screen_height = viewer.winfo_screenheight()

            # Calculate scaling to fit screen while maintaining aspect ratio
            img_ratio = img.width / img.height
            screen_ratio = screen_width / screen_height

            if img_ratio > screen_ratio:
                # Image is wider than screen
                new_width = screen_width
                new_height = int(screen_width / img_ratio)
            else:
                # Image is taller than screen
                new_height = screen_height
                new_width = int(screen_height * img_ratio)

            # Create CTkImage with appropriate size
            photo = ctk.CTkImage(light_image=img, dark_image=img, size=(new_width, new_height))

            # Create container frame
            container = ctk.CTkFrame(viewer, fg_color="#000000")
            container.pack(fill="both", expand=True)

            # Display image centered
            img_label = ctk.CTkLabel(
                container,
                image=photo,
                text=""
            )
            img_label.place(relx=0.5, rely=0.5, anchor="center")

            # Keep reference to prevent garbage collection
            viewer._image_ref = photo

            # Info overlay at top
            info_bar = ctk.CTkFrame(viewer, fg_color="#1a1a1a", height=60)
            info_bar.pack(side="top", fill="x")

            filename = os.path.basename(image_path)
            file_label = ctk.CTkLabel(
                info_bar,
                text=filename,
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color="#ffffff"
            )
            file_label.pack(side="left", padx=20, pady=10)

            resolution_label = ctk.CTkLabel(
                info_bar,
                text=f"{img.width}x{img.height}",
                font=ctk.CTkFont(size=14),
                text_color="#888888"
            )
            resolution_label.pack(side="left", padx=10, pady=10)

            # Get and display tags
            tags = self.stats_manager.get_tags(image_path)
            if tags:
                tags_text = ", ".join(tags[:5])
                tags_label = ctk.CTkLabel(
                    info_bar,
                    text=f"🏷️ {tags_text}",
                    font=ctk.CTkFont(size=12),
                    text_color="#888888"
                )
                tags_label.pack(side="left", padx=10, pady=10)

            # Close button
            close_btn = ctk.CTkButton(
                info_bar,
                text="✕ Close",
                font=ctk.CTkFont(size=14, weight="bold"),
                width=100,
                height=35,
                fg_color=self.COLORS['accent'],
                hover_color=self.COLORS['sidebar_hover'],
                command=viewer.destroy
            )
            close_btn.pack(side="right", padx=20, pady=10)

            # Action buttons at bottom
            action_bar = ctk.CTkFrame(viewer, fg_color="#1a1a1a", height=70)
            action_bar.pack(side="bottom", fill="x")

            # Set as wallpaper button
            set_wallpaper_btn = ctk.CTkButton(
                action_bar,
                text="SET AS WALLPAPER",
                font=ctk.CTkFont(size=14, weight="bold"),
                width=200,
                height=40,
                fg_color=self.COLORS['accent'],
                hover_color=self.COLORS['sidebar_hover'],
                command=lambda: [self._apply_wallpaper({"path": image_path}), self.show_toast("Success", "Wallpaper applied!")]
            )
            set_wallpaper_btn.pack(side="left", padx=20, pady=15)

            # Rating
            rating_frame = ctk.CTkFrame(action_bar, fg_color="transparent")
            rating_frame.pack(side="left", padx=20, pady=15)

            ctk.CTkLabel(
                rating_frame,
                text="Rating:",
                font=ctk.CTkFont(size=12),
                text_color="#888888"
            ).pack(side="left", padx=(0, 10))

            # Create star buttons list for updating
            star_buttons = []
            current_rating = self.stats_manager.get_rating(image_path)
            for i in range(1, 6):
                star_text = "★" if i <= current_rating else "☆"
                star_btn = ctk.CTkButton(
                    rating_frame,
                    text=star_text,
                    font=ctk.CTkFont(size=18),
                    width=35,
                    height=35,
                    fg_color="transparent",
                    hover_color="#333333",
                    text_color="#ffd700" if i <= current_rating else "#555555",
                    command=lambda r=i, p=image_path, btns=star_buttons: [self._set_rating(p, r, btns), self.show_toast("Rating", f"Rated {r} stars")]
                )
                star_btn.pack(side="left", padx=2)
                star_buttons.append(star_btn)

            # Favorite button
            is_fav = self.stats_manager.is_favorite(image_path)
            fav_btn = ctk.CTkButton(
                action_bar,
                text="♥ Favorite" if is_fav else "♡ Add to Favorites",
                font=ctk.CTkFont(size=14, weight="bold"),
                width=180,
                height=40,
                fg_color="#ff6b81" if is_fav else "#333333",
                hover_color="#ff4757",
                command=lambda: [self._toggle_favorite(image_path, fav_btn), self.show_toast("Favorites", "Removed from favorites" if not self.stats_manager.is_favorite(image_path) else "Added to favorites!")]
            )
            fav_btn.pack(side="left", padx=10, pady=15)

            # Tag editor with autocomplete
            tag_frame = ctk.CTkFrame(action_bar, fg_color="transparent")
            tag_frame.pack(side="left", padx=20, pady=15)

            ctk.CTkLabel(
                tag_frame,
                text="Tags:",
                font=ctk.CTkFont(size=12),
                text_color="#888888"
            ).pack(side="left", padx=(0, 10))

            # Get current tags and all available tags
            current_tags = self.stats_manager.get_tags(image_path)
            all_tags = set(self.stats_manager.get_all_tags())  # get_all_tags() returns a list

            # Tag entry with autocomplete
            tag_entry = ctk.CTkEntry(
                tag_frame,
                placeholder_text="Add tag...",
                width=150,
                height=35
            )
            tag_entry.pack(side="left", padx=5)

            # Autocomplete dropdown (initially hidden)
            autocomplete_frame = ctk.CTkFrame(
                viewer,
                fg_color=self.COLORS['sidebar_bg'],
                border_width=1,
                border_color=self.COLORS['accent']
            )

            # Store autocomplete widgets
            autocomplete_labels = []

            def update_autocomplete(event=None):
                """Update autocomplete suggestions based on input"""
                text = tag_entry.get().strip().lower()

                # Clear previous suggestions
                for label in autocomplete_labels:
                    label.destroy()
                autocomplete_labels.clear()

                if not text:
                    autocomplete_frame.place_forget()
                    return

                # Find matching tags
                matches = sorted([tag for tag in all_tags if text in tag.lower() and tag.lower() not in [t.lower() for t in current_tags]])[:5]

                if matches:
                    # Position autocomplete below entry
                    autocomplete_frame.place(
                        x=tag_entry.winfo_rootx() - viewer.winfo_rootx(),
                        y=tag_entry.winfo_rooty() - viewer.winfo_rooty() + tag_entry.winfo_height(),
                        width=tag_entry.winfo_width()
                    )

                    for match in matches:
                        match_label = ctk.CTkLabel(
                            autocomplete_frame,
                            text=match,
                            font=ctk.CTkFont(size=12),
                            text_color=self.COLORS['text_light'],
                            anchor="w",
                            padx=10,
                            pady=5
                        )
                        match_label.pack(fill="x")
                        match_label.bind("<Button-1>", lambda e, t=match: select_tag(t))
                        match_label.bind("<Enter>", lambda e, l=match_label: l.configure(text_color=self.COLORS['accent']))
                        match_label.bind("<Leave>", lambda e, l=match_label: l.configure(text_color=self.COLORS['text_light']))
                        autocomplete_labels.append(match_label)
                else:
                    autocomplete_frame.place_forget()

            def select_tag(tag_text):
                """Select a tag from autocomplete or add new one"""
                tag_text = tag_text.strip()
                if tag_text and tag_text not in current_tags:
                    # Add tag to wallpaper
                    self.stats_manager.add_tag(image_path, tag_text)
                    current_tags.append(tag_text)
                    all_tags.add(tag_text)

                    # Clear entry and hide autocomplete
                    tag_entry.delete(0, 'end')
                    autocomplete_frame.place_forget()

                    # Update tags display in viewer
                    tags_display.configure(text=f"🏷️ {', '.join(current_tags[:5])}" if current_tags else "🏷️ No tags")

                    self.show_toast("Tags", f"Tag '{tag_text}' added")

            def add_tag_from_entry(event=None):
                """Add tag from entry (Enter key or button)"""
                tag_text = tag_entry.get().strip()
                if tag_text:
                    select_tag(tag_text)

            # Bind events
            tag_entry.bind("<KeyRelease>", update_autocomplete)
            tag_entry.bind("<Return>", add_tag_from_entry)
            tag_entry.bind("<FocusOut>", lambda e: viewer.after(200, lambda: autocomplete_frame.place_forget()))

            # Add button
            add_tag_btn = ctk.CTkButton(
                tag_frame,
                text="➕",
                width=35,
                height=35,
                fg_color=self.COLORS['accent'],
                hover_color=self.COLORS['sidebar_hover'],
                command=add_tag_from_entry
            )
            add_tag_btn.pack(side="left", padx=5)

            # Tags display (update existing tags label in info bar)
            tags_display = None
            for child in info_bar.winfo_children():
                if isinstance(child, ctk.CTkLabel) and child.cget("text").startswith("🏷️"):
                    tags_display = child
                    break

            # Close on Escape or click
            viewer.bind("<Escape>", lambda e: viewer.destroy())
            viewer.bind("<Button-1>", lambda e: viewer.destroy() if e.widget == viewer or e.widget == container else None)

            viewer.focus()

        except Exception as e:
            viewer.destroy()
            self.show_toast("Error", f"Error loading image: {str(e)}")

    def _show_ai_assistant_view(self):
        """Show AI Assistant view with Smart Recommendations"""
        # Create container for this view (following same pattern as other views)
        view_container = ctk.CTkFrame(self.content_container, fg_color="transparent")
        view_container.pack(fill="both", expand=True)
        self._view_cache["AI Assistant"] = view_container

        # Create scrollable container inside view
        scroll_container = ctk.CTkScrollableFrame(
            view_container,
            fg_color="transparent"
        )
        scroll_container.pack(fill="both", expand=True, padx=30, pady=20)

        # Header
        header = ctk.CTkLabel(
            scroll_container,
            text="AI Assistant",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=self.COLORS['text_light']
        )
        header.pack(anchor="w", pady=(0, 10))

        subtitle = ctk.CTkLabel(
            scroll_container,
            text="AI-powered recommendations and suggestions",
            font=ctk.CTkFont(size=14),
            text_color=self.COLORS['text_muted']
        )
        subtitle.pack(anchor="w", pady=(0, 30))

        # API Key Section
        api_section = ctk.CTkFrame(
            scroll_container,
            fg_color=self.COLORS['card_bg'],
            corner_radius=12
        )
        api_section.pack(fill="x", pady=(0, 20))

        api_header = ctk.CTkLabel(
            api_section,
            text="Google Gemini API Key",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.COLORS['text_light']
        )
        api_header.pack(anchor="w", padx=20, pady=(20, 10))

        api_info = ctk.CTkLabel(
            api_section,
            text="Get your free API key at https://makersuite.google.com/app/apikey",
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS['text_muted']
        )
        api_info.pack(anchor="w", padx=20, pady=(0, 15))

        # API Key Entry
        api_frame = ctk.CTkFrame(api_section, fg_color="transparent")
        api_frame.pack(fill="x", padx=20, pady=(0, 15))

        current_key = self.recommendations.api_key or ""
        api_entry = ctk.CTkEntry(
            api_frame,
            placeholder_text="Enter your Gemini API key here...",
            width=400,
            height=35,
            fg_color=self.COLORS['main_bg'],
            border_color=self.COLORS['accent']
        )
        api_entry.pack(side="left", padx=(0, 10))
        if current_key:
            api_entry.insert(0, current_key)

        def save_api_key():
            key = api_entry.get().strip()
            if key:
                if self.recommendations.set_api_key(key):
                    # Save to .env file
                    try:
                        env_path = Path(__file__).parent / '.env'
                        env_lines = []
                        if env_path.exists():
                            with open(env_path, 'r', encoding='utf-8') as f:
                                env_lines = f.readlines()

                        # Update or add GEMINI_API_KEY
                        new_env_lines = []
                        key_found = False
                        for line in env_lines:
                            if line.startswith('GEMINI_API_KEY='):
                                new_env_lines.append(f'GEMINI_API_KEY={key}\n')
                                key_found = True
                            else:
                                new_env_lines.append(line)

                        if not key_found:
                            new_env_lines.append(f'GEMINI_API_KEY={key}\n')

                        with open(env_path, 'w', encoding='utf-8') as f:
                            f.writelines(new_env_lines)

                        self.show_toast("Success", "API Key saved successfully!")
                        # Refresh recommendations
                        self._navigate("AI Assistant")
                    except Exception as e:
                        self.show_toast("Error", f"Failed to save API key: {e}")
                else:
                    self.show_toast("Error", "Invalid API Key. Please check and try again.")
            else:
                self.show_toast("Error", "Please enter an API key")

        save_btn = ctk.CTkButton(
            api_frame,
            text="Save API Key",
            width=120,
            height=35,
            fg_color=self.COLORS['accent'],
            hover_color=self.COLORS['sidebar_hover'],
            command=save_api_key
        )
        save_btn.pack(side="left")

        # Status indicator
        status_text = "✓ API Key Configured" if self.recommendations.model else "⚠ API Key Required"
        status_color = self.COLORS['accent'] if self.recommendations.model else self.COLORS['warning']
        status_label = ctk.CTkLabel(
            api_section,
            text=status_text,
            font=ctk.CTkFont(size=12),
            text_color=status_color
        )
        status_label.pack(anchor="w", padx=20, pady=(0, 20))

        # Privacy Section
        privacy_section = ctk.CTkFrame(scroll_container, fg_color=self.COLORS['card_bg'], corner_radius=12)
        privacy_section.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(privacy_section, text="🔒 Privacy Settings", font=ctk.CTkFont(size=16, weight="bold"), text_color=self.COLORS['text_light']).pack(anchor="w", padx=20, pady=(20, 10))
        ctk.CTkLabel(privacy_section, text="Keep all AI processing on your local machine (requires Ollama)", font=ctk.CTkFont(size=12), text_color=self.COLORS['text_muted']).pack(anchor="w", padx=20, pady=(0, 15))

        if not hasattr(self, 'use_local_ai_var'):
            self.use_local_ai_var = ctk.BooleanVar(value=os.getenv("USE_LOCAL_AI_ONLY", "false").lower() == "true")

        ctk.CTkCheckBox(privacy_section, text="Use Local AI Only (Ollama) - No data sent to Google", variable=self.use_local_ai_var, font=ctk.CTkFont(size=13), text_color=self.COLORS['text_light'], fg_color=self.COLORS['accent'], hover_color=self.COLORS['sidebar_hover'], command=self._toggle_local_ai_mode).pack(anchor="w", padx=20, pady=(0, 10))

        ollama_models = self.recommendations._get_ollama_models()
        if ollama_models:
            ctk.CTkLabel(privacy_section, text=f"✓ Ollama available ({len(ollama_models)} models)", font=ctk.CTkFont(size=11), text_color=self.COLORS['accent']).pack(anchor="w", padx=40, pady=(0, 5))
            ctk.CTkLabel(privacy_section, text="Models: " + ", ".join(ollama_models[:3]) + (f" (+{len(ollama_models)-3})" if len(ollama_models)>3 else ""), font=ctk.CTkFont(size=10), text_color=self.COLORS['text_muted']).pack(anchor="w", padx=40, pady=(0, 20))
        else:
            ctk.CTkLabel(privacy_section, text="⚠ Ollama not found - Install from ollama.ai", font=ctk.CTkFont(size=11), text_color=self.COLORS['warning']).pack(anchor="w", padx=40, pady=(0, 20))

        # Smart Recommendations Section
        if self.recommendations.model or True:  # Show even without API (basic recommendations)
            recs_section = ctk.CTkFrame(
                scroll_container,
                fg_color=self.COLORS['card_bg'],
                corner_radius=12
            )
            recs_section.pack(fill="both", expand=True, pady=(0, 20))

            recs_header_frame = ctk.CTkFrame(recs_section, fg_color="transparent")
            recs_header_frame.pack(fill="x", padx=20, pady=(20, 15))

            recs_header = ctk.CTkLabel(
                recs_header_frame,
                text="Smart Recommendations",
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color=self.COLORS['text_light']
            )
            recs_header.pack(side="left")

            refresh_btn = ctk.CTkButton(
                recs_header_frame,
                text="↻ Refresh",
                width=100,
                height=30,
                fg_color=self.COLORS['accent'],
                hover_color=self.COLORS['sidebar_hover'],
                command=lambda: self._navigate("AI Assistant")
            )
            refresh_btn.pack(side="right")

            # Get recommendations
            recommendations = self.recommendations.get_recommendations(12)

            if recommendations:
                # Grid for recommended wallpapers
                grid_frame = ctk.CTkFrame(recs_section, fg_color="transparent")
                grid_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

                for idx, rec in enumerate(recommendations):
                    row = idx // 3
                    col = idx % 3

                    self._create_wallpaper_card_ai(
                        grid_frame,
                        rec["item"],
                        rec["score"],
                        rec["reasons"],
                        row=row,
                        column=col
                    )
            else:
                no_recs = ctk.CTkLabel(
                    recs_section,
                    text="Not enough data yet. Use the app more to get personalized recommendations!",
                    font=ctk.CTkFont(size=14),
                    text_color=self.COLORS['text_muted']
                )
                no_recs.pack(padx=20, pady=40)

            # AI Suggestions (if API is configured)
            if self.recommendations.model:
                suggestions_section = ctk.CTkFrame(
                    scroll_container,
                    fg_color=self.COLORS['card_bg'],
                    corner_radius=12
                )
                suggestions_section.pack(fill="x", pady=(0, 20))

                sugg_header = ctk.CTkLabel(
                    suggestions_section,
                    text="AI-Generated Search Suggestions",
                    font=ctk.CTkFont(size=16, weight="bold"),
                    text_color=self.COLORS['text_light']
                )
                sugg_header.pack(anchor="w", padx=20, pady=(20, 15))

                # Get AI suggestions
                queries = self.recommendations.suggest_search_queries()

                for query in queries:
                    query_frame = ctk.CTkFrame(
                        suggestions_section,
                        fg_color=self.COLORS['main_bg'],
                        corner_radius=8
                    )
                    query_frame.pack(fill="x", padx=20, pady=5)

                    query_label = ctk.CTkLabel(
                        query_frame,
                        text=f"💡 {query}",
                        font=ctk.CTkFont(size=13),
                        text_color=self.COLORS['text_light']
                    )
                    query_label.pack(side="left", padx=15, pady=10)

                suggestions_section.pack_configure(pady=(0, 20))

                # 🎭 AI MOOD DETECTION Section
                mood_section = ctk.CTkFrame(
                    scroll_container,
                    fg_color=self.COLORS['card_bg'],
                    corner_radius=12
                )
                mood_section.pack(fill="x", pady=(0, 20))

                mood_header = ctk.CTkLabel(
                    mood_section,
                    text="🎭 AI Mood Detection",
                    font=ctk.CTkFont(size=16, weight="bold"),
                    text_color=self.COLORS['text_light']
                )
                mood_header.pack(anchor="w", padx=20, pady=(20, 10))

                mood_btn = ctk.CTkButton(
                    mood_section,
                    text="Detect My Current Mood",
                    fg_color=self.COLORS['accent'],
                    hover_color=self.COLORS['sidebar_hover'],
                    command=lambda: self._detect_mood_ai()
                )
                mood_btn.pack(padx=20, pady=(0, 20))

                # 💬 AI NATURAL LANGUAGE SEARCH Section
                search_section = ctk.CTkFrame(
                    scroll_container,
                    fg_color=self.COLORS['card_bg'],
                    corner_radius=12
                )
                search_section.pack(fill="x", pady=(0, 20))

                search_header = ctk.CTkLabel(
                    search_section,
                    text="💬 AI Natural Language Search",
                    font=ctk.CTkFont(size=16, weight="bold"),
                    text_color=self.COLORS['text_light']
                )
                search_header.pack(anchor="w", padx=20, pady=(20, 10))

                search_info = ctk.CTkLabel(
                    search_section,
                    text="Search using conversational language (e.g., 'something relaxing for evening')",
                    font=ctk.CTkFont(size=12),
                    text_color=self.COLORS['text_muted']
                )
                search_info.pack(anchor="w", padx=20, pady=(0, 10))

                search_frame = ctk.CTkFrame(search_section, fg_color="transparent")
                search_frame.pack(fill="x", padx=20, pady=(0, 20))

                search_entry = ctk.CTkEntry(
                    search_frame,
                    placeholder_text="Describe what kind of wallpaper you want...",
                    width=400,
                    height=35,
                    fg_color=self.COLORS['main_bg'],
                    border_color=self.COLORS['accent']
                )
                search_entry.pack(side="left", padx=(0, 10))

                # Download buttons for different providers
                download_container = ctk.CTkFrame(search_frame, fg_color="transparent")
                download_container.pack(side="left", padx=(0, 10))

                ctk.CTkLabel(download_container, text="Download:", font=ctk.CTkFont(size=11), text_color=self.COLORS['text_muted']).pack(side="left", padx=(0, 5))

                pexels_dl_btn = ctk.CTkButton(
                    download_container,
                    text="Pexels",
                    width=70,
                    height=28,
                    fg_color=self.COLORS['accent'],
                    hover_color=self.COLORS['sidebar_hover'],
                    command=lambda: self._ai_download_and_apply(search_entry.get(), "pexels")
                )
                pexels_dl_btn.pack(side="left", padx=2)

                reddit_dl_btn = ctk.CTkButton(
                    download_container,
                    text="Reddit",
                    width=70,
                    height=28,
                    fg_color="#FF4500",
                    hover_color="#CC3700",
                    command=lambda: self._ai_download_and_apply(search_entry.get(), "reddit")
                )
                reddit_dl_btn.pack(side="left", padx=2)

                wallhaven_dl_btn = ctk.CTkButton(
                    download_container,
                    text="Wallhaven",
                    width=80,
                    height=28,
                    fg_color="#6C5CE7",
                    hover_color="#5A4BC4",
                    command=lambda: self._ai_download_and_apply(search_entry.get(), "wallhaven")
                )
                wallhaven_dl_btn.pack(side="left", padx=2)

                search_btn = ctk.CTkButton(
                    search_frame,
                    text="🔍 Search Cache",
                    width=120,
                    fg_color=self.COLORS['sidebar_hover'],
                    hover_color=self.COLORS['accent'],
                    command=lambda: self._ai_natural_search(search_entry.get())
                )
                search_btn.pack(side="left")

                # 🔮 AI PREDICTIVE SELECTION Section
                predict_section = ctk.CTkFrame(
                    scroll_container,
                    fg_color=self.COLORS['card_bg'],
                    corner_radius=12
                )
                predict_section.pack(fill="x", pady=(0, 20))

                predict_header = ctk.CTkLabel(
                    predict_section,
                    text="🔮 AI Predictive Selection",
                    font=ctk.CTkFont(size=16, weight="bold"),
                    text_color=self.COLORS['text_light']
                )
                predict_header.pack(anchor="w", padx=20, pady=(20, 10))

                predict_info = ctk.CTkLabel(
                    predict_section,
                    text="Let AI predict the perfect wallpaper for you right now",
                    font=ctk.CTkFont(size=12),
                    text_color=self.COLORS['text_muted']
                )
                predict_info.pack(anchor="w", padx=20, pady=(0, 10))

                predict_btn = ctk.CTkButton(
                    predict_section,
                    text="✨ Predict Perfect Wallpaper",
                    fg_color=self.COLORS['accent'],
                    hover_color=self.COLORS['sidebar_hover'],
                    command=lambda: self._ai_predict_wallpaper()
                )
                predict_btn.pack(padx=20, pady=(0, 20))

                # 🎨 STYLE SIMILARITY FINDER Section
                similarity_section = ctk.CTkFrame(
                    scroll_container,
                    fg_color=self.COLORS['card_bg'],
                    corner_radius=12
                )
                similarity_section.pack(fill="x", pady=(0, 20))

                similarity_header = ctk.CTkLabel(
                    similarity_section,
                    text="🎨 Style Similarity Finder",
                    font=ctk.CTkFont(size=16, weight="bold"),
                    text_color=self.COLORS['text_light']
                )
                similarity_header.pack(anchor="w", padx=20, pady=(20, 10))

                similarity_info = ctk.CTkLabel(
                    similarity_section,
                    text="Find wallpapers with similar artistic style to your favorites",
                    font=ctk.CTkFont(size=12),
                    text_color=self.COLORS['text_muted']
                )
                similarity_info.pack(anchor="w", padx=20, pady=(0, 10))

                # Reference wallpaper selection
                similarity_frame = ctk.CTkFrame(similarity_section, fg_color="transparent")
                similarity_frame.pack(fill="x", padx=20, pady=(0, 15))

                ref_label = ctk.CTkLabel(
                    similarity_frame,
                    text="Reference:",
                    font=ctk.CTkFont(size=12),
                    text_color=self.COLORS['text_muted']
                )
                ref_label.pack(side="left", padx=(0, 10))

                self.ai_similarity_ref_label = ctk.CTkLabel(
                    similarity_frame,
                    text="No wallpaper selected",
                    font=ctk.CTkFont(size=11),
                    text_color=self.COLORS['text_muted']
                )
                self.ai_similarity_ref_label.pack(side="left")

                similarity_btn_frame = ctk.CTkFrame(similarity_section, fg_color="transparent")
                similarity_btn_frame.pack(padx=20, pady=(0, 20))

                select_ref_btn = ctk.CTkButton(
                    similarity_btn_frame,
                    text="📁 Select Reference Wallpaper",
                    fg_color=self.COLORS['card_bg'],
                    hover_color=self.COLORS['card_hover'],
                    command=lambda: self._ai_select_reference_wallpaper()
                )
                select_ref_btn.pack(side="left", padx=(0, 10))

                find_similar_btn = ctk.CTkButton(
                    similarity_btn_frame,
                    text="🔍 Find Similar Wallpapers",
                    fg_color=self.COLORS['accent'],
                    hover_color=self.COLORS['sidebar_hover'],
                    command=lambda: self._ai_find_similar_wallpapers()
                )
                find_similar_btn.pack(side="left")

                # 📝 AI WALLPAPER ANALYSIS Section
                analysis_section = ctk.CTkFrame(
                    scroll_container,
                    fg_color=self.COLORS['card_bg'],
                    corner_radius=12
                )
                analysis_section.pack(fill="x", pady=(0, 20))

                analysis_header = ctk.CTkLabel(
                    analysis_section,
                    text="📝 AI Wallpaper Analysis",
                    font=ctk.CTkFont(size=16, weight="bold"),
                    text_color=self.COLORS['text_light']
                )
                analysis_header.pack(anchor="w", padx=20, pady=(20, 10))

                analysis_info = ctk.CTkLabel(
                    analysis_section,
                    text="Get creative AI-generated descriptions and tag suggestions for any wallpaper",
                    font=ctk.CTkFont(size=12),
                    text_color=self.COLORS['text_muted']
                )
                analysis_info.pack(anchor="w", padx=20, pady=(0, 10))

                # Selected wallpaper for analysis
                analysis_frame = ctk.CTkFrame(analysis_section, fg_color="transparent")
                analysis_frame.pack(fill="x", padx=20, pady=(0, 15))

                analysis_label = ctk.CTkLabel(
                    analysis_frame,
                    text="Wallpaper:",
                    font=ctk.CTkFont(size=12),
                    text_color=self.COLORS['text_muted']
                )
                analysis_label.pack(side="left", padx=(0, 10))

                self.ai_analysis_path_label = ctk.CTkLabel(
                    analysis_frame,
                    text="No wallpaper selected",
                    font=ctk.CTkFont(size=11),
                    text_color=self.COLORS['text_muted']
                )
                self.ai_analysis_path_label.pack(side="left")

                analysis_btn_frame = ctk.CTkFrame(analysis_section, fg_color="transparent")
                analysis_btn_frame.pack(padx=20, pady=(0, 20))

                select_analysis_btn = ctk.CTkButton(
                    analysis_btn_frame,
                    text="📁 Select Wallpaper",
                    fg_color=self.COLORS['card_bg'],
                    hover_color=self.COLORS['card_hover'],
                    command=lambda: self._ai_select_wallpaper_for_analysis()
                )
                select_analysis_btn.pack(side="left", padx=(0, 10))

                analyze_btn = ctk.CTkButton(
                    analysis_btn_frame,
                    text="🤖 Analyze with AI",
                    fg_color=self.COLORS['accent'],
                    hover_color=self.COLORS['sidebar_hover'],
                    command=lambda: self._ai_analyze_wallpaper()
                )
                analyze_btn.pack(side="left")

    def _create_wallpaper_card_ai(self, parent, item: Dict[str, Any], score: float, reasons: List[str], row: int, column: int):
        """Create a wallpaper card for AI recommendations with score and reasons"""
        card = ctk.CTkFrame(
            parent,
            fg_color=self.COLORS['card_bg'],
            corner_radius=12,
            cursor="hand2"
        )
        card.grid(row=row, column=column, padx=10, pady=10, sticky="nsew")
        parent.grid_columnconfigure(column, weight=1, uniform="cols")

        # Bind click event to set wallpaper
        path = item.get("path")
        card.bind("<Button-1>", lambda e, p=path: self._set_wallpaper_from_cache(p))

        try:
            # Load and display thumbnail
            img_path = Path(path)
            if img_path.exists():
                img = Image.open(img_path)
                img.thumbnail((300, 200), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)

                img_label = ctk.CTkLabel(card, image=photo, text="")
                img_label.image = photo
                img_label.pack(pady=(10, 5))
                self.image_references.append(photo)

                # Score badge
                score_label = ctk.CTkLabel(
                    card,
                    text=f"Score: {score:.0f}%",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=self.COLORS['warning'],
                    fg_color=self.COLORS['main_bg'],
                    corner_radius=6
                )
                score_label.pack(pady=5)

                # Reasons (show top 2)
                for reason in reasons[:2]:
                    reason_label = ctk.CTkLabel(
                        card,
                        text=f"• {reason}",
                        font=ctk.CTkFont(size=10),
                        text_color=self.COLORS['text_muted'],
                        wraplength=250
                    )
                    reason_label.pack(pady=2)

        except Exception as e:
            error_label = ctk.CTkLabel(
                card,
                text=f"Error loading\nimage",
                font=ctk.CTkFont(size=12),
                text_color=self.COLORS['text_muted']
            )
            error_label.pack(expand=True, pady=50)

    def _toggle_local_ai_mode(self):
        use_local = self.use_local_ai_var.get()
        try:
            env_path = Path(__file__).parent / '.env'
            env_lines = []
            if env_path.exists():
                with open(env_path, 'r', encoding='utf-8') as f:
                    env_lines = f.readlines()

            new_env_lines = []
            key_found = False
            for line in env_lines:
                if line.startswith('USE_LOCAL_AI_ONLY='):
                    new_env_lines.append(f'USE_LOCAL_AI_ONLY={"true" if use_local else "false"}\n')
                    key_found = True
                else:
                    new_env_lines.append(line)

            if not key_found:
                new_env_lines.append(f'USE_LOCAL_AI_ONLY={"true" if use_local else "false"}\n')

            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(new_env_lines)

            os.environ["USE_LOCAL_AI_ONLY"] = "true" if use_local else "false"

            if use_local:
                models = self.recommendations._get_ollama_models()
                if models:
                    self.show_toast("Privacy Mode", f"✓ Using local AI only\nModel: {models[0]}")
                else:
                    self.show_toast("Warning", "⚠ Ollama not available\nPlease install Ollama")
                    self.use_local_ai_var.set(False)
            else:
                self.show_toast("Privacy Mode", "Using cloud AI (Google Gemini)")
        except Exception as e:
            self.show_toast("Error", f"Failed to save setting: {e}")

    def _detect_mood_ai(self):
        """🎭 Detect current mood using AI"""
        if not self.recommendations.model:
            self.show_toast("Error", "Please configure Gemini API key first")
            return

        # Create loading dialog
        loading = AILoadingDialog(self.root, title="AI Mood Detection", message="Analyzing your mood...")

        def ai_task():
            try:
                loading.update_status("Analyzing context...")
                current_weather = None
                mood_data = self.recommendations.detect_mood_and_suggest(current_weather)
                self.root.after(0, lambda: self._show_mood_results(mood_data, loading))
            except Exception as e:
                self.root.after(0, lambda: self._show_mood_error(str(e), loading))

        threading.Thread(target=ai_task, daemon=True).start()

    def _show_mood_results(self, mood_data, loading_dialog):
        try:
            if loading_dialog and loading_dialog.winfo_exists():
                loading_dialog.close()
        except:
            pass

        try:
            # Create dialog to show results
            mood_dialog = ctk.CTkToplevel(self.root)
            mood_dialog.title("AI Mood Detection")
            mood_dialog.geometry("500x400")
            mood_dialog.transient(self.root)
            mood_dialog.grab_set()

            # Header
            header = ctk.CTkLabel(
                mood_dialog,
                text=f"🎭 Current Mood: {mood_data['mood'].upper()}",
                font=ctk.CTkFont(size=20, weight="bold"),
                text_color=self.COLORS['accent']
            )
            header.pack(pady=(20, 10))

            # Style
            if mood_data.get('style'):
                style_label = ctk.CTkLabel(
                    mood_dialog,
                    text=f"Recommended Style:\n{mood_data['style']}",
                    font=ctk.CTkFont(size=14),
                    text_color=self.COLORS['text_light'],
                    wraplength=450
                )
                style_label.pack(pady=10)

            # Reason
            reason_label = ctk.CTkLabel(
                mood_dialog,
                text=mood_data['reason'],
                font=ctk.CTkFont(size=12),
                text_color=self.COLORS['text_muted']
            )
            reason_label.pack(pady=10)

            # Queries with download buttons
            if mood_data.get('queries'):
                queries_label = ctk.CTkLabel(
                    mood_dialog,
                    text="AI Suggested Searches:",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color=self.COLORS['text_light']
                )
                queries_label.pack(pady=(20, 10))

                for query in mood_data['queries']:
                    q_frame = ctk.CTkFrame(mood_dialog, fg_color=self.COLORS['card_bg'])
                    q_frame.pack(fill="x", padx=40, pady=5)

                    # Query text and download button in horizontal layout
                    content_frame = ctk.CTkFrame(q_frame, fg_color="transparent")
                    content_frame.pack(fill="x", padx=10, pady=8)

                    q_label = ctk.CTkLabel(
                        content_frame,
                        text=f"💡 {query}",
                        font=ctk.CTkFont(size=12),
                        text_color=self.COLORS['text_light']
                    )
                    q_label.pack(side="left", padx=(0, 10))

                    # Button container for provider choices
                    btn_container = ctk.CTkFrame(content_frame, fg_color="transparent")
                    btn_container.pack(side="right")

                    def make_download_handler(search_query, provider, dialog):
                        def handler():
                            dialog.destroy()
                            self._ai_download_and_apply(search_query, provider)
                        return handler

                    # Pexels button
                    pexels_btn = ctk.CTkButton(
                        btn_container,
                        text="Pexels",
                        width=70,
                        height=28,
                        command=make_download_handler(query, "pexels", mood_dialog),
                        fg_color=self.COLORS['accent'],
                        hover_color=self.COLORS['sidebar_hover']
                    )
                    pexels_btn.pack(side="left", padx=2)

                    # Reddit button
                    reddit_btn = ctk.CTkButton(
                        btn_container,
                        text="Reddit",
                        width=70,
                        height=28,
                        command=make_download_handler(query, "reddit", mood_dialog),
                        fg_color="#FF4500",
                        hover_color="#CC3700"
                    )
                    reddit_btn.pack(side="left", padx=2)

                    # Wallhaven button
                    wallhaven_btn = ctk.CTkButton(
                        btn_container,
                        text="Wallhaven",
                        width=80,
                        height=28,
                        command=make_download_handler(query, "wallhaven", mood_dialog),
                        fg_color="#6C5CE7",
                        hover_color="#5A4BC4"
                    )
                    wallhaven_btn.pack(side="left", padx=2)

            # Close button
            close_btn = ctk.CTkButton(
                mood_dialog,
                text="Close",
                command=mood_dialog.destroy,
                fg_color=self.COLORS['accent']
            )
            close_btn.pack(pady=20)

        except Exception as e:
            self.show_toast("Error", f"Failed to display results: {str(e)}")

    def _show_mood_error(self, error_msg, loading_dialog):
        try:
            if loading_dialog and loading_dialog.winfo_exists():
                loading_dialog.close()
        except:
            pass
        self.show_toast("Error", f"Mood detection failed:\n{error_msg}")

    def _ai_natural_search(self, query: str):
        """💬 Search using natural language"""
        if not self.recommendations.model:
            self.show_toast("Error", "Please configure Gemini API key first")
            return

        if not query or not query.strip():
            self.show_toast("Error", "Please enter a search query")
            return

        try:
            # Show loading
            self.show_toast("AI Assistant", f"Searching for: {query}...")

            # Perform AI search
            results = self.recommendations.natural_language_search(query.strip())

            if not results:
                self.show_toast("AI Assistant", "No matching wallpapers found")
                return

            # Create dialog to show results
            search_dialog = ctk.CTkToplevel(self.root)
            search_dialog.title("AI Search Results")
            search_dialog.geometry("900x700")
            search_dialog.transient(self.root)
            search_dialog.grab_set()

            # Header
            header = ctk.CTkLabel(
                search_dialog,
                text=f"🔍 Results for: '{query}'",
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color=self.COLORS['text_light']
            )
            header.pack(pady=(20, 10))

            # Scrollable frame for results
            scroll_frame = ctk.CTkScrollableFrame(search_dialog, fg_color="transparent")
            scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

            # Display results
            for idx, result in enumerate(results):
                result_card = ctk.CTkFrame(scroll_frame, fg_color=self.COLORS['card_bg'])
                result_card.pack(fill="x", pady=10)

                # Reason
                reason_label = ctk.CTkLabel(
                    result_card,
                    text=f"#{idx+1}: {result['reason']}",
                    font=ctk.CTkFont(size=13),
                    text_color=self.COLORS['text_light'],
                    wraplength=800
                )
                reason_label.pack(anchor="w", padx=15, pady=10)

                # Apply button
                def make_search_apply_handler(path, dialog):
                    def handler():
                        self._set_wallpaper_from_cache(path)
                        dialog.destroy()
                    return handler

                apply_btn = ctk.CTkButton(
                    result_card,
                    text="Apply This Wallpaper",
                    command=make_search_apply_handler(result['item']['path'], search_dialog),
                    fg_color=self.COLORS['accent']
                )
                apply_btn.pack(padx=15, pady=(0, 10))

            # Close button
            close_btn = ctk.CTkButton(
                search_dialog,
                text="Close",
                command=search_dialog.destroy,
                fg_color=self.COLORS['sidebar_hover']
            )
            close_btn.pack(pady=10)

        except Exception as e:
            self.show_toast("Error", f"AI search failed: {str(e)}")

    def _ai_predict_wallpaper(self):
        """🔮 Predict perfect wallpaper using AI"""
        if not self.recommendations.model:
            self.show_toast("Error", "Please configure Gemini API key first")
            return

        try:
            # Show loading
            self.show_toast("AI Assistant", "Predicting perfect wallpaper...")

            # Get prediction
            prediction = self.recommendations.predict_next_wallpaper()

            if not prediction:
                self.show_toast("AI Assistant", "Not enough data for prediction")
                return

            # Create dialog to show prediction
            pred_dialog = ctk.CTkToplevel(self.root)
            pred_dialog.title("AI Prediction")
            pred_dialog.geometry("550x650")
            pred_dialog.transient(self.root)
            pred_dialog.grab_set()

            # Initialize dialog state early (before any functions that need it)
            dialog_state = {
                'img_label': None,
                'pred_text': None,
                'score_label': None,
                'reasons_label': None,
                'apply_btn': None,
                'downloaded_path': None,
                'is_alive': True
            }

            # Handle dialog close events
            def on_dialog_close():
                dialog_state['is_alive'] = False
                pred_dialog.destroy()

            pred_dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)

            # Header
            header = ctk.CTkLabel(
                pred_dialog,
                text="🔮 AI Predicted Perfect Wallpaper",
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color=self.COLORS['accent']
            )
            header.pack(pady=(20, 15))

            # Wallpaper thumbnail
            try:
                from PIL import Image, ImageTk
                img_path = Path(prediction['item']['path'])
                if img_path.exists():
                    img = Image.open(img_path)
                    img.thumbnail((400, 250), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)

                    img_label = ctk.CTkLabel(pred_dialog, image=photo, text="")
                    img_label.image = photo
                    img_label.pack(pady=10)
                    self.image_references.append(photo)
                    dialog_state['img_label'] = img_label  # Store reference
            except Exception as e:
                print(f"Error loading prediction thumbnail: {e}")

            # AI Prediction text
            if prediction.get('ai_prediction'):
                pred_text = ctk.CTkLabel(
                    pred_dialog,
                    text=f"AI thinks:\n\n\"{prediction['ai_prediction']}\"",
                    font=ctk.CTkFont(size=13),
                    text_color=self.COLORS['text_light'],
                    wraplength=450
                )
                pred_text.pack(pady=15)
                dialog_state['pred_text'] = pred_text  # Store reference

            # Score
            score_label = ctk.CTkLabel(
                pred_dialog,
                text=f"Match Score: {prediction['score']:.0f}%",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=self.COLORS['warning']
            )
            score_label.pack(pady=10)
            dialog_state['score_label'] = score_label  # Store reference

            # Reasons
            if prediction.get('reasons'):
                reasons_text = "Why this wallpaper:\n" + "\n".join([f"• {r}" for r in prediction['reasons'][:3]])
                reasons_label = ctk.CTkLabel(
                    pred_dialog,
                    text=reasons_text,
                    font=ctk.CTkFont(size=12),
                    text_color=self.COLORS['text_muted'],
                    wraplength=450
                )
                reasons_label.pack(pady=10)
                dialog_state['reasons_label'] = reasons_label  # Store reference

            # Apply button
            def apply_prediction():
                self._set_wallpaper_from_cache(prediction['item']['path'])
                dialog_state['is_alive'] = False  # Mark dialog as closed
                pred_dialog.destroy()

            apply_btn = ctk.CTkButton(
                pred_dialog,
                text="✨ Apply Predicted Wallpaper",
                command=apply_prediction,
                fg_color=self.COLORS['accent'],
                height=40
            )
            apply_btn.pack(pady=20)

            # Download similar wallpapers section
            similar_label = ctk.CTkLabel(
                pred_dialog,
                text="💡 Download similar wallpapers:",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=self.COLORS['text_light']
            )
            similar_label.pack(pady=(10, 5))

            # Extract search query from AI prediction
            search_query = prediction.get('ai_prediction', 'wallpaper')
            # Clean up the query - take first few descriptive words
            words = search_query.split()[:4]
            search_query = ' '.join(words)

            # Provider buttons
            provider_frame = ctk.CTkFrame(pred_dialog, fg_color="transparent")
            provider_frame.pack(pady=10)

            def make_download_similar(query, provider, state):
                def handler():
                    # Download in background and update preview
                    import threading

                    def download_task():
                        try:
                            self.show_toast("Downloading", f"Getting wallpaper from {provider.capitalize()}...")

                            # Download (modify to return path instead of applying)
                            downloaded_item = self._ai_download_similar(query, provider)

                            if downloaded_item and downloaded_item.get('path'):
                                # Update UI in main thread
                                self.root.after(0, lambda: update_preview(downloaded_item, provider))
                        except Exception as e:
                            self.root.after(0, lambda: self.show_toast("Error", f"Download failed: {str(e)}"))

                    threading.Thread(target=download_task, daemon=True).start()

                return handler

            def update_preview(item, provider):
                """Update dialog with new downloaded wallpaper"""
                # Check if dialog is still open
                if not dialog_state.get('is_alive', False):
                    print("[PREVIEW] Dialog closed, skipping update")
                    return

                try:
                    # Update image
                    if dialog_state['img_label']:
                        from PIL import Image, ImageTk
                        img_path = Path(item['path'])
                        if img_path.exists():
                            img = Image.open(img_path)
                            img.thumbnail((400, 250), Image.Resampling.LANCZOS)
                            photo = ImageTk.PhotoImage(img)
                            dialog_state['img_label'].configure(image=photo)
                            dialog_state['img_label'].image = photo
                            self.image_references.append(photo)

                    # Update text
                    if dialog_state['pred_text']:
                        dialog_state['pred_text'].configure(
                            text=f"Downloaded from {provider.upper()}:\n\n\"{search_query}\""
                        )

                    # Update score
                    dialog_state['score_label'].configure(
                        text=f"✅ Downloaded Successfully",
                        text_color=self.COLORS['accent']
                    )

                    # Update reasons
                    if dialog_state['reasons_label']:
                        dialog_state['reasons_label'].configure(
                            text=f"Source: {provider.capitalize()}\nQuery: {search_query}\nTags: {', '.join(item.get('tags', []))}"
                        )

                    # Store downloaded path
                    dialog_state['downloaded_path'] = item['path']

                    # Update apply button
                    if dialog_state['apply_btn']:
                        dialog_state['apply_btn'].configure(
                            text="✨ Apply Downloaded Wallpaper",
                            command=lambda: (self._set_wallpaper_from_cache(item['path']), on_dialog_close())
                        )

                    self.show_toast("Success", f"Preview updated! Click Apply to use it.")

                except Exception as e:
                    print(f"Error updating preview: {e}")
                    self.show_toast("Error", f"Failed to update preview: {str(e)}")

            pexels_btn = ctk.CTkButton(
                provider_frame,
                text="📥 Pexels",
                width=140,
                height=35,
                fg_color=self.COLORS['accent'],
                hover_color=self.COLORS['sidebar_hover'],
                command=make_download_similar(search_query, "pexels", dialog_state)
            )
            pexels_btn.pack(side="left", padx=5)

            reddit_btn = ctk.CTkButton(
                provider_frame,
                text="📥 Reddit",
                width=140,
                height=35,
                fg_color="#FF4500",
                hover_color="#CC3700",
                command=make_download_similar(search_query, "reddit", dialog_state)
            )
            reddit_btn.pack(side="left", padx=5)

            wallhaven_btn = ctk.CTkButton(
                provider_frame,
                text="📥 Wallhaven",
                width=140,
                height=35,
                fg_color="#6C5CE7",
                hover_color="#5A4BC4",
                command=make_download_similar(search_query, "wallhaven", dialog_state)
            )
            wallhaven_btn.pack(side="left", padx=5)

            # Store apply button reference
            dialog_state['apply_btn'] = apply_btn

            # Close button
            close_btn = ctk.CTkButton(
                pred_dialog,
                text="Maybe Later",
                command=on_dialog_close,  # Use handler that sets is_alive flag
                fg_color=self.COLORS['sidebar_hover']
            )
            close_btn.pack(pady=(15, 20))

        except Exception as e:
            self.show_toast("Error", f"Prediction failed: {str(e)}")

    def _ai_select_reference_wallpaper(self):
        """📁 Select a reference wallpaper for similarity search"""
        from tkinter import filedialog

        # Open file dialog
        file_path = filedialog.askopenfilename(
            title="Select Reference Wallpaper",
            initialdir=str(self.cache_manager.cache_dir),
            filetypes=[
                ("Image Files", "*.jpg *.jpeg *.png *.webp *.bmp"),
                ("All Files", "*.*")
            ]
        )

        if file_path:
            self.ai_similarity_reference = file_path
            filename = Path(file_path).name
            self.ai_similarity_ref_label.configure(text=filename)
            self.show_toast("AI Assistant", "Reference wallpaper selected")

    def _ai_find_similar_wallpapers(self):
        """🎨 Find similar wallpapers using AI style analysis"""
        if not self.recommendations.model:
            self.show_toast("Error", "Please configure Gemini API key first")
            return

        if not hasattr(self, 'ai_similarity_reference') or not self.ai_similarity_reference:
            self.show_toast("Error", "Please select a reference wallpaper first")
            return

        try:
            self.show_toast("AI Assistant", "Finding similar wallpapers...")

            # Get similar wallpapers
            similar = self.recommendations.get_similar_wallpapers(
                self.ai_similarity_reference,
                count=6
            )

            if not similar:
                self.show_toast("AI Assistant", "No similar wallpapers found")
                return

            # Create dialog to show results
            sim_dialog = ctk.CTkToplevel(self.root)
            sim_dialog.title("🎨 Similar Wallpapers - AI Style Analysis")
            sim_dialog.geometry("1000x700")
            sim_dialog.configure(fg_color=self.COLORS['main_bg'])

            # Header
            header = ctk.CTkLabel(
                sim_dialog,
                text=f"Found {len(similar)} Similar Wallpapers",
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color=self.COLORS['text_light']
            )
            header.pack(pady=(20, 5))

            # AI explanation
            if similar and 'similarity_reason' in similar[0]:
                explanation_label = ctk.CTkLabel(
                    sim_dialog,
                    text=f"AI Analysis: {similar[0]['similarity_reason']}",
                    font=ctk.CTkFont(size=12),
                    text_color=self.COLORS['text_muted'],
                    wraplength=900
                )
                explanation_label.pack(pady=(0, 10))

            # Scrollable frame for results
            scroll_frame = ctk.CTkScrollableFrame(sim_dialog, fg_color="transparent")
            scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

            # Display similar wallpapers in grid
            for idx, result in enumerate(similar):
                row = idx // 2
                col = idx % 2

                card = ctk.CTkFrame(scroll_frame, fg_color=self.COLORS['card_bg'], corner_radius=12)
                card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
                scroll_frame.grid_columnconfigure(col, weight=1)

                try:
                    # Load thumbnail
                    img_path = Path(result['item']['path'])
                    if img_path.exists():
                        img = Image.open(img_path)
                        img.thumbnail((400, 250), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(img)

                        img_label = ctk.CTkLabel(card, image=photo, text="")
                        img_label.image = photo
                        img_label.pack(pady=10)
                        self.image_references.append(photo)
                except:
                    pass

                # Score
                score_label = ctk.CTkLabel(
                    card,
                    text=f"Similarity: {result['score']:.0f}%",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=self.COLORS['warning']
                )
                score_label.pack(pady=5)

                # Matching tags
                if result.get('matching_tags'):
                    tags_text = "Similar: " + ", ".join(result['matching_tags'][:5])
                    tags_label = ctk.CTkLabel(
                        card,
                        text=tags_text,
                        font=ctk.CTkFont(size=10),
                        text_color=self.COLORS['text_muted'],
                        wraplength=380
                    )
                    tags_label.pack(pady=5)

                # Apply button
                def make_apply_handler(path, dialog):
                    def handler():
                        self._set_wallpaper_from_cache(path)
                        dialog.destroy()
                    return handler

                apply_btn = ctk.CTkButton(
                    card,
                    text="Apply Wallpaper",
                    command=make_apply_handler(result['item']['path'], sim_dialog),
                    fg_color=self.COLORS['accent']
                )
                apply_btn.pack(pady=10)

            # Close button
            close_btn = ctk.CTkButton(
                sim_dialog,
                text="Close",
                command=sim_dialog.destroy,
                fg_color=self.COLORS['sidebar_hover']
            )
            close_btn.pack(pady=10)

        except Exception as e:
            self.show_toast("Error", f"Similarity search failed: {str(e)}")

    def _ai_select_wallpaper_for_analysis(self):
        """📁 Select a wallpaper for AI analysis"""
        from tkinter import filedialog

        # Open file dialog
        file_path = filedialog.askopenfilename(
            title="Select Wallpaper to Analyze",
            initialdir=str(self.cache_manager.cache_dir),
            filetypes=[
                ("Image Files", "*.jpg *.jpeg *.png *.webp *.bmp"),
                ("All Files", "*.*")
            ]
        )

        if file_path:
            self.ai_analysis_path = file_path
            filename = Path(file_path).name
            self.ai_analysis_path_label.configure(text=filename)
            self.show_toast("AI Assistant", "Wallpaper selected for analysis")

    def _ai_analyze_wallpaper(self):
        """📝 Analyze wallpaper with AI and get creative description"""
        if not self.recommendations.model:
            self.show_toast("Error", "Please configure Gemini API key first")
            return

        if not hasattr(self, 'ai_analysis_path') or not self.ai_analysis_path:
            self.show_toast("Error", "Please select a wallpaper first")
            return

        try:
            self.show_toast("AI Assistant", "Analyzing wallpaper with AI...")

            # Get tags for this wallpaper
            wallpaper_path = Path(self.ai_analysis_path)
            wallpaper_info = None

            for item in self.cache_manager.cache_metadata:
                if Path(item['path']) == wallpaper_path:
                    wallpaper_info = item
                    break

            tags = wallpaper_info.get('tags', []) if wallpaper_info else []

            # Analyze with AI
            analysis = self.recommendations.analyze_wallpaper_with_ai(
                str(wallpaper_path),
                tags
            )

            # Create dialog to show results
            analysis_dialog = ctk.CTkToplevel(self.root)
            analysis_dialog.title("📝 AI Wallpaper Analysis")
            analysis_dialog.geometry("800x700")
            analysis_dialog.configure(fg_color=self.COLORS['main_bg'])

            # Header
            header = ctk.CTkLabel(
                analysis_dialog,
                text="🤖 AI Creative Analysis",
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color=self.COLORS['text_light']
            )
            header.pack(pady=(20, 10))

            # Scrollable content
            scroll_frame = ctk.CTkScrollableFrame(analysis_dialog, fg_color="transparent")
            scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

            # Wallpaper preview
            try:
                img = Image.open(wallpaper_path)
                img.thumbnail((700, 300), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)

                img_label = ctk.CTkLabel(scroll_frame, image=photo, text="")
                img_label.image = photo
                img_label.pack(pady=10)
                self.image_references.append(photo)
            except:
                pass

            # Description
            desc_frame = ctk.CTkFrame(scroll_frame, fg_color=self.COLORS['card_bg'])
            desc_frame.pack(fill="x", pady=10)

            desc_header = ctk.CTkLabel(
                desc_frame,
                text="✨ Creative Description:",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=self.COLORS['text_light']
            )
            desc_header.pack(anchor="w", padx=15, pady=(15, 5))

            desc_text = ctk.CTkLabel(
                desc_frame,
                text=analysis.get('description', 'No description available'),
                font=ctk.CTkFont(size=12),
                text_color=self.COLORS['text_muted'],
                wraplength=700,
                justify="left"
            )
            desc_text.pack(anchor="w", padx=15, pady=(0, 15))

            # Mood & Style
            info_frame = ctk.CTkFrame(scroll_frame, fg_color=self.COLORS['card_bg'])
            info_frame.pack(fill="x", pady=10)

            mood_label = ctk.CTkLabel(
                info_frame,
                text=f"🎭 Mood: {analysis.get('mood', 'N/A')}",
                font=ctk.CTkFont(size=13),
                text_color=self.COLORS['text_light']
            )
            mood_label.pack(anchor="w", padx=15, pady=(15, 5))

            style_label = ctk.CTkLabel(
                info_frame,
                text=f"🎨 Style: {analysis.get('style', 'N/A')}",
                font=ctk.CTkFont(size=13),
                text_color=self.COLORS['text_light']
            )
            style_label.pack(anchor="w", padx=15, pady=(0, 15))

            # Suggested tags
            if analysis.get('suggested_tags'):
                tags_frame = ctk.CTkFrame(scroll_frame, fg_color=self.COLORS['card_bg'])
                tags_frame.pack(fill="x", pady=10)

                tags_header = ctk.CTkLabel(
                    tags_frame,
                    text="🏷️ AI Suggested Tags:",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color=self.COLORS['text_light']
                )
                tags_header.pack(anchor="w", padx=15, pady=(15, 10))

                tags_container = ctk.CTkFrame(tags_frame, fg_color="transparent")
                tags_container.pack(fill="x", padx=15, pady=(0, 15))

                for tag in analysis['suggested_tags']:
                    tag_label = ctk.CTkLabel(
                        tags_container,
                        text=tag,
                        font=ctk.CTkFont(size=11),
                        text_color=self.COLORS['text_light'],
                        fg_color=self.COLORS['main_bg'],
                        corner_radius=6,
                        padx=10,
                        pady=5
                    )
                    tag_label.pack(side="left", padx=5, pady=5)

            # Apply button
            def apply_analysis():
                self._set_wallpaper_from_cache(str(wallpaper_path))
                analysis_dialog.destroy()

            apply_btn = ctk.CTkButton(
                analysis_dialog,
                text="Apply This Wallpaper",
                command=apply_analysis,
                fg_color=self.COLORS['accent']
            )
            apply_btn.pack(pady=10)

            # Close button
            close_btn = ctk.CTkButton(
                analysis_dialog,
                text="Close",
                command=analysis_dialog.destroy,
                fg_color=self.COLORS['sidebar_hover']
            )
            close_btn.pack(pady=(0, 20))

        except Exception as e:
            self.show_toast("Error", f"Analysis failed: {str(e)}")

    def _ai_download_similar(self, query: str, provider: str = "pexels"):
        """Download wallpaper WITHOUT applying - returns item dict"""
        # Call main download function but intercept before apply
        result = self._ai_download_and_apply(query, provider, apply_wallpaper=False)
        return result

    def _ai_download_and_apply(self, query: str, provider: str = "pexels", apply_wallpaper: bool = True):
        """Download and optionally apply wallpaper based on AI query suggestion"""
        try:
            import requests
            import random
            from pathlib import Path

            # Use AI to improve and translate query to English
            original_query = query
            if self.recommendations and self.recommendations.model:
                self.show_toast("AI Assistant", f"Improving search query...")
                try:
                    improve_prompt = f"""Translate and improve this wallpaper search query to English.
Keep it 2-4 words maximum. Make it specific and descriptive for image search.

User query: "{query}"

Return ONLY the improved English search terms, nothing else."""

                    improved = self.recommendations._generate_content(improve_prompt)
                    query = improved.strip().strip('"').strip("'")
                    print(f"[AI SEARCH] Original: '{original_query}' -> Improved: '{query}'")
                except Exception as e:
                    print(f"[AI SEARCH] Failed to improve query: {e}")
                    # Continue with original query

            self.show_toast("AI Assistant", f"Downloading from {provider.capitalize()}: {query}")

            # Provider-specific logic
            image_url = None
            metadata = {}

            if provider == "pexels":
                from config import PexelsApiKey
                if not PexelsApiKey:
                    self.show_toast("Error", "Pexels API key not configured")
                    return

                headers = {"Authorization": PexelsApiKey}
                search_url = f"https://api.pexels.com/v1/search?query={query}&per_page=15&orientation=landscape"
                response = requests.get(search_url, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()

                if not data.get('photos'):
                    self.show_toast("Error", "No wallpapers found on Pexels")
                    return

                photo = random.choice(data['photos'])
                image_url = photo['src']['original']
                metadata = {
                    "id": str(photo['id']),
                    "url": photo['url'],
                    "provider": "pexels",
                    "photographer": photo.get('photographer', 'Unknown')
                }

            elif provider == "reddit":
                # Reddit wallpaper scraping
                subreddits = ["wallpaper", "wallpapers", "MinimalWallpaper", "WidescreenWallpaper"]
                search_query = query.replace(' ', '+')

                for subreddit in subreddits:
                    try:
                        reddit_url = f"https://www.reddit.com/r/{subreddit}/search.json?q={search_query}&restrict_sr=1&limit=50"
                        headers = {"User-Agent": "WallpaperChanger/1.0"}
                        response = requests.get(reddit_url, headers=headers, timeout=10)
                        response.raise_for_status()
                        data = response.json()

                        # Filter for image posts
                        posts = data.get('data', {}).get('children', [])
                        image_posts = [p['data'] for p in posts if p['data'].get('url', '').endswith(('.jpg', '.jpeg', '.png'))]

                        if image_posts:
                            post = random.choice(image_posts)
                            image_url = post['url']
                            metadata = {
                                "id": post['id'],
                                "url": f"https://reddit.com{post['permalink']}",
                                "provider": "reddit",
                                "photographer": f"u/{post['author']}"
                            }
                            break
                    except:
                        continue

                if not image_url:
                    self.show_toast("Error", "No wallpapers found on Reddit")
                    return

            elif provider == "wallhaven":
                # Wallhaven API
                from config import ApiKey
                api_key_param = f"&apikey={ApiKey}" if ApiKey else ""
                search_url = f"https://wallhaven.cc/api/v1/search?q={query}&categories=111&purity=100&atleast=1920x1080{api_key_param}"

                response = requests.get(search_url, timeout=10)
                response.raise_for_status()
                data = response.json()

                if not data.get('data'):
                    self.show_toast("Error", "No wallpapers found on Wallhaven")
                    return

                wallpaper = random.choice(data['data'])
                image_url = wallpaper['path']
                metadata = {
                    "id": wallpaper['id'],
                    "url": wallpaper['url'],
                    "provider": "wallhaven",
                    "photographer": wallpaper.get('uploader', {}).get('username', 'Unknown')
                }

            if not image_url:
                self.show_toast("Error", f"Failed to get image from {provider}")
                return

            # Download the image with retry logic
            import tempfile
            from pathlib import Path

            MAX_RETRIES = 3
            MIN_IMAGE_SIZE = 5000  # 5KB minimum for valid wallpaper

            for attempt in range(MAX_RETRIES):
                try:
                    print(f"[AI DOWNLOAD] Attempt {attempt + 1}/{MAX_RETRIES}: {image_url}")

                    # Use browser-like headers to avoid blocks
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Referer': 'https://www.google.com/'
                    }

                    img_response = requests.get(image_url, timeout=30, headers=headers)
                    img_response.raise_for_status()

                    # Check if image is valid
                    image_size = len(img_response.content)

                    if image_size < MIN_IMAGE_SIZE:
                        raise Exception(f"Image too small ({image_size} bytes)")

                    print(f"[AI DOWNLOAD] Valid image: {image_size} bytes")
                    break  # Success!

                except Exception as e:
                    print(f"[AI DOWNLOAD] Attempt {attempt + 1} failed: {e}")

                    if attempt < MAX_RETRIES - 1:
                        # Try to get another image from the same search
                        print(f"[AI DOWNLOAD] Retrying with different image...")

                        if provider == "pexels":
                            photo = random.choice(data['photos'])
                            image_url = photo['src']['original']
                            metadata['id'] = str(photo['id'])
                            metadata['url'] = photo['url']
                        elif provider == "reddit":
                            if image_posts:
                                post = random.choice(image_posts)
                                image_url = post['url']
                                metadata['id'] = post['id']
                                metadata['url'] = f"https://reddit.com{post['permalink']}"
                        elif provider == "wallhaven":
                            if data.get('data'):
                                wallpaper = random.choice(data['data'])
                                image_url = wallpaper['path']
                                metadata['id'] = wallpaper['id']
                                metadata['url'] = wallpaper['url']
                    else:
                        # Last attempt failed
                        raise Exception(f"Failed to download after {MAX_RETRIES} attempts. {str(e)}")

            # Save to cache
            from pathlib import Path
            cache_dir = Path(self.cache_manager.cache_dir)
            print(f"[AI DOWNLOAD] Cache dir: {cache_dir}")

            # Ensure cache directory exists
            cache_dir.mkdir(parents=True, exist_ok=True)

            filename = f"ai_suggested_{int(time.time())}_{metadata['id']}.jpg"
            filepath = cache_dir / filename
            print(f"[AI DOWNLOAD] Saving to: {filepath}")

            with open(filepath, 'wb') as f:
                f.write(img_response.content)
            print(f"[AI DOWNLOAD] File saved successfully")

            # Add to cache index
            # Extract colors for filtering
            try:
                from color_analyzer import ColorAnalyzer
                color_categories = ColorAnalyzer.get_color_categories(str(filepath), num_colors=3)
                primary_color = ColorAnalyzer.get_primary_color_category(str(filepath))
            except Exception as e:
                print(f"[WARNING] Failed to extract colors: {e}")
                color_categories = []
                primary_color = None

            # Compute perceptual hash for duplicate detection
            perceptual_hash = None
            if self.cache_manager.duplicate_detector:
                perceptual_hash = self.cache_manager.duplicate_detector.compute_hash(str(filepath))

            # Extract tags from query (split by spaces and commas)
            tags = [tag.strip() for tag in query.replace(',', ' ').split() if tag.strip()]
            print(f"[AI DOWNLOAD] Query: '{query}' -> Tags: {tags}")

            item = {
                "id": metadata['id'],
                "path": str(filepath),
                "url": metadata['url'],
                "provider": metadata['provider'],
                "photographer": metadata['photographer'],
                "tags": tags,
                "timestamp": time.time(),
                "ai_suggested": True,
                "ai_query": query,
                "color_categories": color_categories,
                "primary_color": primary_color,
                "perceptual_hash": perceptual_hash
            }

            self.cache_manager._index.setdefault("items", []).append(item)
            self.cache_manager._save()
            print(f"[AI DOWNLOAD] Metadata saved with {len(tags)} tags: {tags}")

            # Save tags to statistics manager so they appear in the gallery
            if tags and self.stats_manager:
                for tag in tags:
                    self.stats_manager.add_tag(str(filepath), tag)
                print(f"[AI DOWNLOAD] Tags added to statistics manager")

            # Apply the wallpaper (only if requested)
            if apply_wallpaper:
                print(f"[AI DOWNLOAD] Applying wallpaper...")
                self._apply_wallpaper(item)
                print(f"[AI DOWNLOAD] All done!")
                self.show_toast("Success", f"AI wallpaper downloaded and applied!")
            else:
                print(f"[AI DOWNLOAD] Download complete (not applied)")
                return item  # Return item for preview mode

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"[AI DOWNLOAD ERROR] {error_details}")
            self.show_toast("Error", f"Download failed: {str(e)}")
            return None

    def run(self):
        """Start the GUI"""
        self.root.mainloop()


def main():
    app = ModernWallpaperGUI()
    app.run()


if __name__ == "__main__":
    main()