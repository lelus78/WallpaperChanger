"Modern GUI for Wallpaper Changer using CustomTkinter\nInspired by contemporary wallpaper applications with sidebar navigation\n"
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
from statistics_manager import StatisticsManager
import matplotlib
matplotlib.use('TkAgg')  # Use TkAgg backend for embedding in tkinter
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import time


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

        # Image references to prevent garbage collection
        self.image_references = []

        # Statistics manager
        self.stats_manager = StatisticsManager()
        # Clean up placeholder paths from previous versions
        self.stats_manager.cleanup_placeholder_paths()

        # Toast notifications
        self.toast_windows = []

        # Current wallpaper tracking
        self.current_wallpaper = None

        # View caching for performance
        self._view_cache = {}

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
            ("Home", "●", "#FFD93D"),      # Yellow home icon
            ("Wallpapers", "●", "#00e676"), # Green wallpapers icon
            ("Settings", "●", "#89b4fa"),   # Blue settings icon
            ("Logs", "●", "#ff6b81"),       # Red logs icon
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

        # Filter dropdown
        filter_frame = ctk.CTkFrame(header, fg_color="transparent")
        filter_frame.grid(row=0, column=2, sticky="e", padx=10)

        # Tag filter
        ctk.CTkLabel(
            filter_frame,
            text="Tag:",
            text_color=self.COLORS['text_muted'],
            font=ctk.CTkFont(size=13)
        ).pack(side="left", padx=(0, 10))

        # Create or reuse tag_filter_var to preserve selection
        if not hasattr(self, 'tag_filter_var') or not self.tag_filter_var:
            self.tag_filter_var = ctk.StringVar(value="All Tags")

        # Get all unique tags
        all_tags = self.stats_manager.get_all_tags()
        tag_values = ["All Tags"] + sorted(all_tags)

        tag_menu = ctk.CTkOptionMenu(
            filter_frame,
            variable=self.tag_filter_var,
            values=tag_values if tag_values else ["All Tags"],
            width=150,
            fg_color=self.COLORS['card_bg'],
            button_color=self.COLORS['accent'],
            button_hover_color=self.COLORS['sidebar_hover'],
            command=self._on_filter_change
        )
        tag_menu.pack(side="left", padx=(0, 10))

        # Sort dropdown
        ctk.CTkLabel(
            filter_frame,
            text="Sort:",
            text_color=self.COLORS['text_muted'],
            font=ctk.CTkFont(size=13)
        ).pack(side="left", padx=(0, 10))

        # Create or reuse sort_var to preserve selection
        if not hasattr(self, 'sort_var') or not self.sort_var:
            self.sort_var = ctk.StringVar(value="Newest First")

        sort_menu = ctk.CTkOptionMenu(
            filter_frame,
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
            filter_frame,
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
        if not hasattr(self, '_last_window_width'):
            self._last_window_width = 0
        if not hasattr(self, '_resize_timer'):
            self._resize_timer = None

        def check_resize():
            try:
                current_width = self.root.winfo_width()
                if abs(current_width - self._last_window_width) > 360:
                    if hasattr(self, 'wallpapers_scrollable_frame') and self.wallpapers_scrollable_frame.winfo_exists():
                        self._last_window_width = current_width
                        self._load_wallpaper_grid()
            except:
                pass
            if hasattr(self, 'wallpapers_scrollable_frame') and self.wallpapers_scrollable_frame.winfo_exists():
                self._resize_timer = self.root.after(1000, check_resize)

        self._last_window_width = self.root.winfo_width()
        self._resize_timer = self.root.after(1000, check_resize)

    def _load_wallpaper_grid(self):
        """Load wallpapers into the grid with current filter/sort settings"""
        if not hasattr(self, 'wallpapers_scrollable_frame'):
            return

        scrollable_frame = self.wallpapers_scrollable_frame
        for widget in scrollable_frame.winfo_children():
            widget.destroy()

        try:
            window_width = self.root.winfo_width()
            card_width = 360
            available_width = window_width - 100
            num_columns = max(3, min(6, available_width // card_width))
        except:
            num_columns = 3

        for i in range(num_columns):
            scrollable_frame.grid_columnconfigure(i, weight=0, minsize=360)

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
        tag_filter = self.tag_filter_var.get() if hasattr(self, 'tag_filter_var') else "All Tags"

        # Apply tag filter first
        if tag_filter and tag_filter != "All Tags":
            wallpapers_with_tag = self.stats_manager.get_wallpapers_by_tag(tag_filter)
            items = [item for item in items if item.get("path") in wallpapers_with_tag]

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
            width=340,
            height=320
        )
        card.grid(row=row, column=col, padx=10, pady=10)
        card.grid_propagate(False)

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
            elif view == "Settings":
                self._show_settings_view()
            elif view == "Logs":
                self._show_logs_view()

    def _refresh_home_data(self):
        """Refresh Home view wallpapers without recreating entire view"""
        self.stats_manager.data = self.stats_manager._load_data()
        # Clear image references to allow new images to load
        self.image_references.clear()
        if hasattr(self, 'wallpaper_preview_container') and self.wallpaper_preview_container.winfo_exists():
            for widget in self.wallpaper_preview_container.winfo_children():
                widget.destroy()
            self._create_current_wallpaper_preview(self.wallpaper_preview_container)

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

    def _on_sort_change(self, choice: str):
        """Handle sort change and filter"""
        self._load_wallpaper_grid()

    def _on_filter_change(self, choice: str):
        """Handle tag filter change"""
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

    def _toggle_favorite(self, wallpaper_path: str, button: ctk.CTkButton):
        """Toggle favorite status for a wallpaper"""
        is_fav = self.stats_manager.toggle_favorite(wallpaper_path)
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

    def _set_rating(self, wallpaper_path: str, rating: int, star_buttons: List):
        """Set rating for a wallpaper"""
        self.stats_manager.set_rating(wallpaper_path, rating)
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
            self._show_toast("Error: Image file not found", error=True)
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
                command=lambda: [self._apply_wallpaper({"path": image_path}), self._show_toast("Wallpaper applied!")]
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
                    command=lambda r=i, p=image_path: [self._set_rating(p, r, None), self._show_toast(f"Rated {r} stars")]
                )
                star_btn.pack(side="left", padx=2)

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
                command=lambda: [self._toggle_favorite(image_path, None), viewer.destroy(), self._show_toast("Added to favorites!" if not is_fav else "Removed from favorites")]
            )
            fav_btn.pack(side="left", padx=10, pady=15)

            # Close on Escape or click
            viewer.bind("<Escape>", lambda e: viewer.destroy())
            viewer.bind("<Button-1>", lambda e: viewer.destroy() if e.widget == viewer or e.widget == container else None)

            viewer.focus()

        except Exception as e:
            viewer.destroy()
            self._show_toast(f"Error loading image: {str(e)}", error=True)

    def run(self):
        """Start the GUI"""
        self.root.mainloop()


def main():
    app = ModernWallpaperGUI()
    app.run()


if __name__ == "__main__":
    main()