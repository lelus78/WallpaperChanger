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

        # Statistics manager
        self.stats_manager = StatisticsManager()

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

        # Increase scroll speed significantly - bind to the frame itself, not globally
        def fast_scroll(event):
            try:
                self.wallpapers_scrollable_frame._parent_canvas.yview_scroll(int(-3*(event.delta/120)), "units")
            except:
                pass  # Ignore if canvas doesn't exist

        self.wallpapers_scrollable_frame.bind("<MouseWheel>", fast_scroll)

        # Setup smart resize handler for wallpapers view only
        self._setup_wallpaper_resize_handler()

        # Load wallpapers into the scrollable frame
        self._load_wallpaper_grid()

    def _setup_wallpaper_resize_handler(self):
        """Setup resize handler that only works when on Wallpapers page"""
        if not hasattr(self, '_last_window_width'):
            self._last_window_width = 0
        if not hasattr(self, '_resize_timer'):
            self._resize_timer = None

        def check_resize():
            """Check if window width changed significantly"""
            try:
                current_width = self.root.winfo_width()
                # Only reload if width changed by more than 360px (one card width)
                if abs(current_width - self._last_window_width) > 360:
                    # Check if we're still on wallpapers view
                    if hasattr(self, 'wallpapers_scrollable_frame') and self.wallpapers_scrollable_frame.winfo_exists():
                        self._last_window_width = current_width
                        self._load_wallpaper_grid()
            except:
                pass
            # Schedule next check in 1 second
            if hasattr(self, 'wallpapers_scrollable_frame') and self.wallpapers_scrollable_frame.winfo_exists():
                self._resize_timer = self.root.after(1000, check_resize)

        # Start checking
        self._last_window_width = self.root.winfo_width()
        self._resize_timer = self.root.after(1000, check_resize)

    def _load_wallpaper_grid(self):
        """Load wallpapers into the grid with current filter/sort settings"""
        if not hasattr(self, 'wallpapers_scrollable_frame'):
            return

        scrollable_frame = self.wallpapers_scrollable_frame

        # Clear existing widgets
        for widget in scrollable_frame.winfo_children():
            widget.destroy()

        # Calculate number of columns based on window width
        # Each card is ~360px wide, so we can fit multiple columns in wider windows
        try:
            window_width = self.root.winfo_width()
            card_width = 360
            # Account for padding and scrollbar
            available_width = window_width - 100
            num_columns = max(3, min(6, available_width // card_width))  # Between 3 and 6 columns
        except:
            num_columns = 3  # Fallback to 3 columns

        # Configure grid columns dynamically
        for i in range(num_columns):
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

        # Apply sorting and filtering
        sort_choice = self.sort_var.get() if hasattr(self, 'sort_var') else "Newest First"

        if sort_choice == "Banned Only":
            # Filter only banned wallpapers
            banned = self.stats_manager.get_banned_wallpapers()
            items = [item for item in items if item.get("path") in banned]
        elif sort_choice == "Favorites Only":
            # Filter only favorites (exclude banned)
            favorites = self.stats_manager.get_favorites()
            items = [item for item in items if item.get("path") in favorites and not self.stats_manager.is_banned(item.get("path"))]
        elif sort_choice == "Top Rated":
            # Sort by rating (exclude banned)
            items = [item for item in items if not self.stats_manager.is_banned(item.get("path"))]
            items = sorted(items, key=lambda x: self.stats_manager.get_rating(x.get("path", "")), reverse=True)
        elif sort_choice == "Oldest First":
            # Exclude banned wallpapers
            items = [item for item in items if not self.stats_manager.is_banned(item.get("path"))]
            items = list(reversed(items))
        elif sort_choice == "Highest Resolution":
            # Exclude banned wallpapers
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
            # Default "Newest First" - exclude banned wallpapers
            items = [item for item in items if not self.stats_manager.is_banned(item.get("path"))]

        # Show message if no items after filtering
        if not items:
            no_items_label = ctk.CTkLabel(
                scrollable_frame,
                text="No wallpapers match the selected filter.",
                font=ctk.CTkFont(size=16),
                text_color=self.COLORS['text_muted']
            )
            no_items_label.grid(row=0, column=0, columnspan=num_columns, pady=100)
            return

        # Calculate optimal number of items to show based on columns
        # Show 3-4 rows worth of cards for better performance
        items_to_show = min(len(items), num_columns * 4)

        # Create cards in grid with dynamic columns
        for idx, item in enumerate(items[:items_to_show]):
            row = idx // num_columns
            col = idx % num_columns
            self._create_wallpaper_card(item, row, col, scrollable_frame)

        # Show "Load More" button if there are more items
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
        """Load more wallpapers when Load More button is clicked"""
        # Remove the load more button
        for widget in parent.winfo_children():
            if isinstance(widget, ctk.CTkFrame) and widget.cget("fg_color") == "transparent":
                # Check if it's the load more frame (last one)
                children = widget.winfo_children()
                if len(children) == 2:  # Label + Button
                    widget.destroy()
                    break

        # Load next batch
        next_batch = min(len(items), current_count + num_columns * 4)

        # Add new cards
        for idx in range(current_count, next_batch):
            item = items[idx]
            row = idx // num_columns
            col = idx % num_columns
            self._create_wallpaper_card(item, row, col, parent)

        # Show load more button again if there are still more items
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
        """Create a modern wallpaper card with rounded corners and hover effects"""
        # Card container with hover effect
        card = ctk.CTkFrame(
            parent,
            fg_color=self.COLORS['card_bg'],
            corner_radius=15,
            border_width=2,
            border_color=self.COLORS['card_bg'],  # Same as background initially
            width=340,
            height=320
        )
        card.grid(row=row, column=col, padx=10, pady=10)
        card.grid_propagate(False)  # Prevent card from shrinking

        # Hover effect functions
        def on_enter(e):
            card.configure(border_color=self.COLORS['accent'])

        def on_leave(e):
            card.configure(border_color=self.COLORS['card_bg'])

        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

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

            # Info section - top row
            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(fill="x", padx=15, pady=(0, 5))

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

            # Ban button
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
            # Store reference for updating
            ban_btn.configure(command=lambda p=image_path, b=ban_btn: self._toggle_ban(p, b))

            # Favorite button
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
            # Store reference for updating
            fav_btn.configure(command=lambda p=image_path, b=fav_btn: self._toggle_favorite(p, b))

            # Rating section
            rating_frame = ctk.CTkFrame(card, fg_color="transparent")
            rating_frame.pack(fill="x", padx=15, pady=(0, 5))

            current_rating = self.stats_manager.get_rating(image_path)

            # Create 5 star buttons
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

            # Update command with button references
            for i, star_btn in enumerate(star_buttons, 1):
                star_btn.configure(command=lambda r=i, p=image_path, btns=star_buttons: self._set_rating(p, r, btns))

            # Apply button
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

        # Initialize cache if doesn't exist
        if not hasattr(self, '_view_cache'):
            self._view_cache = {}

        # Hide all cached views
        for cached_view in self._view_cache.values():
            cached_view.pack_forget()

        # Show or create the requested view
        if view in self._view_cache:
            # Reuse cached view - just show it
            self._view_cache[view].pack(fill="both", expand=True)

            # Refresh Home view data when navigating to it
            if view == "Home":
                self._refresh_home_data()
        else:
            # Create new view and cache it
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
        # Reload statistics from file
        self.stats_manager.data = self.stats_manager._load_data()

        # Only refresh wallpaper previews if container exists
        if hasattr(self, 'wallpaper_preview_container') and self.wallpaper_preview_container.winfo_exists():
            # Clear old previews
            for widget in self.wallpaper_preview_container.winfo_children():
                widget.destroy()

            # Reload just the wallpaper previews
            self._create_current_wallpaper_preview_fast(self.wallpaper_preview_container)

    def _update_nav_buttons(self):
        """Update navigation button styles"""
        for item in self.nav_buttons:
            btn, icon, color = item
            btn_text = btn.cget("text")
            # Extract view name from button text (remove icon and spaces)
            view_name = btn_text.replace(icon, "").strip()

            if view_name == self.active_view:
                btn.configure(fg_color=self.COLORS['sidebar_hover'])
            else:
                btn.configure(fg_color="transparent")

    def _on_sort_change(self, choice: str):
        """Handle sort change and filter"""
        # Reload only the wallpaper grid with the new sort/filter
        self._load_wallpaper_grid()

    def _show_home_view(self):
        """Show enhanced home/dashboard view with statistics and info"""
        # Reload statistics from file to get latest data
        self.stats_manager.data = self.stats_manager._load_data()

        # Create container for this view
        view_container = ctk.CTkFrame(self.content_container, fg_color="transparent")
        view_container.pack(fill="both", expand=True)

        # Cache the view
        self._view_cache["Home"] = view_container

        # Main scrollable container
        scrollable = ctk.CTkScrollableFrame(
            view_container,
            fg_color="transparent"
        )
        scrollable.pack(fill="both", expand=True, padx=20, pady=20)

        # Welcome header with refresh button
        header_frame = ctk.CTkFrame(scrollable, fg_color="transparent")
        header_frame.pack(fill="x", pady=(10, 5))

        title = ctk.CTkLabel(
            header_frame,
            text="Dashboard",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=self.COLORS['text_light']
        )
        title.pack(side="left", anchor="w")

        # Refresh button
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

        # Statistics cards row 1
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

        # Statistics cards row 2
        stats_frame2 = ctk.CTkFrame(scrollable, fg_color="transparent")
        stats_frame2.pack(fill="x", pady=10)

        # Configure grid for 3 cards
        for i in range(3):
            stats_frame2.grid_columnconfigure(i, weight=1)

        # Banned Wallpapers Card
        banned_count = len(self.stats_manager.get_banned_wallpapers())
        self._create_stat_card(stats_frame2, 0, "Banned Wallpapers",
                              f"{banned_count} banned",
                              "#ff4444")

        # Favorites Card
        favorites_count = len(self.stats_manager.get_favorites())
        self._create_stat_card(stats_frame2, 1, "Favorite Wallpapers",
                              f"{favorites_count} favorites",
                              "#ff6b81")

        # Total Changes Card
        total_changes = self.stats_manager.get_total_changes()
        self._create_stat_card(stats_frame2, 2, "Total Changes",
                              f"{total_changes} times",
                              "#00e676")

        # Current Wallpaper Preview Section
        preview_label = ctk.CTkLabel(
            scrollable,
            text="Current Wallpapers (All Monitors)",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.COLORS['text_light']
        )
        preview_label.pack(pady=(30, 15), anchor="w")

        # Container for wallpaper previews (so we can refresh it later)
        self.wallpaper_preview_container = ctk.CTkFrame(scrollable, fg_color="transparent")
        self.wallpaper_preview_container.pack(fill="x", pady=10)

        # Load wallpapers directly (optimized)
        self._create_current_wallpaper_preview_fast(self.wallpaper_preview_container)

        # Statistics Chart Section - Optional Load
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

        # Show "View Statistics" button
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
        # Create a frame container for the card
        card_frame = ctk.CTkFrame(parent, fg_color="transparent")
        card_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

        # Create the button with text inside
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
        """Create wallpaper preview with optimizations - no view tracking on load"""
        # Try to get current wallpapers for all monitors
        wallpapers = []
        try:
            from main import DesktopWallpaperController
            controller = DesktopWallpaperController()
            wallpapers = controller.get_all_wallpapers()
            controller.close()
        except Exception:
            pass

        # If we couldn't get any wallpapers, show message
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

        # Create a card for each monitor (without view tracking to speed up)
        for wallpaper_info in wallpapers:
            preview_card = ctk.CTkFrame(parent, fg_color=self.COLORS['card_bg'], corner_radius=12)
            preview_card.pack(fill="x", pady=10)

            current_path = wallpaper_info.get("path")
            monitor_idx = wallpaper_info.get("monitor_index", 0)
            monitor_width = wallpaper_info.get("width", 0)
            monitor_height = wallpaper_info.get("height", 0)

            # Try to display the wallpaper
            try:
                if current_path and os.path.exists(current_path):
                    # Create preview with image and info
                    content_frame = ctk.CTkFrame(preview_card, fg_color="transparent")
                    content_frame.pack(fill="both", padx=20, pady=20)

                    # Left side - image preview (smaller thumbnail for speed)
                    image_frame = ctk.CTkFrame(content_frame, fg_color=self.COLORS['main_bg'], corner_radius=8)
                    image_frame.pack(side="left", padx=(0, 20))

                    # Use cached thumbnail or create smaller one
                    self._create_image_preview_fast(image_frame, current_path, size=(200, 120))

                    # Right side - info
                    info_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
                    info_frame.pack(side="left", fill="both", expand=True)

                    # Monitor label
                    monitor_label = ctk.CTkLabel(
                        info_frame,
                        text=f"Monitor {monitor_idx + 1} ({monitor_width}x{monitor_height})",
                        font=ctk.CTkFont(size=16, weight="bold"),
                        text_color=self.COLORS['text_light']
                    )
                    monitor_label.pack(anchor="w", pady=(0, 10))

                    # File name
                    file_name = os.path.basename(current_path)
                    name_label = ctk.CTkLabel(
                        info_frame,
                        text=f"📄 {file_name[:50]}{'...' if len(file_name) > 50 else ''}",
                        font=ctk.CTkFont(size=13),
                        text_color=self.COLORS['text_muted'],
                        anchor="w"
                    )
                    name_label.pack(anchor="w", pady=2)

                    # Quick action buttons
                    btn_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
                    btn_frame.pack(anchor="w", pady=(10, 0))

                    # Change button
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
                # Error displaying wallpaper
                error_label = ctk.CTkLabel(
                    preview_card,
                    text=f"Error displaying wallpaper for Monitor {monitor_idx + 1}",
                    font=ctk.CTkFont(size=14),
                    text_color=self.COLORS['text_muted']
                )
                error_label.pack(pady=30)

    def _create_image_preview_fast(self, parent, image_path, size=(200, 120)):
        """Create fast image preview with aggressive caching"""
        try:
            # Check cache first
            cache_key = f"{image_path}_{size[0]}x{size[1]}"
            if cache_key in self.thumbnail_cache:
                img_label = ctk.CTkLabel(parent, image=self.thumbnail_cache[cache_key], text="")
                img_label.pack(padx=10, pady=10)
                return

            # Load and resize quickly
            from PIL import Image
            img = Image.open(image_path)

            # Use FASTEST resampling for speed
            img.thumbnail(size, Image.NEAREST)  # Fastest method

            photo = ctk.CTkImage(light_image=img, dark_image=img, size=size)

            # Cache it
            self.thumbnail_cache[cache_key] = photo

            img_label = ctk.CTkLabel(parent, image=photo, text="")
            img_label.pack(padx=10, pady=10)
        except Exception:
            # Show error placeholder
            error_label = ctk.CTkLabel(
                parent,
                text="Error\nloading",
                font=ctk.CTkFont(size=12),
                text_color=self.COLORS['text_muted']
            )
            error_label.pack(expand=True, pady=50)

    def _create_current_wallpaper_preview(self, parent):
        """Create current wallpaper preview cards showing all monitors"""
        # Try to get current wallpapers for all monitors
        wallpapers = []
        try:
            from main import DesktopWallpaperController

            controller = DesktopWallpaperController()
            wallpapers = controller.get_all_wallpapers()
            controller.close()
        except Exception as e:
            pass

        # If we couldn't get any wallpapers, show message
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

        # Track viewed wallpapers in this session to avoid double counting
        if not hasattr(self, '_viewed_wallpapers_session'):
            self._viewed_wallpapers_session = set()

        # Create a card for each monitor
        for wallpaper_info in wallpapers:
            current_path = wallpaper_info.get("path")

            # Increment view count if this is the first time seeing this wallpaper in this session
            if current_path and current_path not in self._viewed_wallpapers_session:
                # Only increment views for wallpapers that are actually tracked (in cache)
                if current_path in [item.get("path") for item in self.cache_manager.list_entries()]:
                    # Get current views
                    current_views = self.stats_manager.data.get("wallpapers", {}).get(current_path, {}).get("views", 0)

                    # Log as a view (this will increment the view count)
                    if current_path in self.stats_manager.data.get("wallpapers", {}):
                        self.stats_manager.data["wallpapers"][current_path]["views"] = current_views + 1
                    else:
                        # Create entry if doesn't exist
                        from datetime import datetime
                        self.stats_manager.data.setdefault("wallpapers", {})[current_path] = {
                            "views": 1,
                            "last_viewed": datetime.now().isoformat(),
                            "rating": 0,
                            "favorite": False,
                            "tags": [],
                            "provider": "unknown"
                        }

                    # Save the updated stats
                    self.stats_manager._save_data()

                    # Mark as viewed in this session
                    self._viewed_wallpapers_session.add(current_path)

        # Create a card for each monitor
        for wallpaper_info in wallpapers:
            preview_card = ctk.CTkFrame(parent, fg_color=self.COLORS['card_bg'], corner_radius=12)
            preview_card.pack(fill="x", pady=10)

            current_path = wallpaper_info.get("path")
            monitor_idx = wallpaper_info.get("monitor_index", 0)
            monitor_width = wallpaper_info.get("width", 0)
            monitor_height = wallpaper_info.get("height", 0)

            # Try to display the wallpaper
            try:
                if current_path and os.path.exists(current_path):
                    # Create preview with image and info
                    content_frame = ctk.CTkFrame(preview_card, fg_color="transparent")
                    content_frame.pack(fill="both", padx=20, pady=20)

                    # Left side - image preview
                    try:
                        img = Image.open(current_path)
                        img.thumbnail((400, 250), Image.Resampling.LANCZOS)
                        photo = ctk.CTkImage(light_image=img, dark_image=img, size=(400, 250))

                        img_label = ctk.CTkLabel(content_frame, image=photo, text="")
                        img_label.pack(side="left", padx=(0, 20))
                    except:
                        pass

                    # Right side - info
                    info_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
                    info_frame.pack(side="left", fill="both", expand=True)

                    # Monitor label
                    monitor_label = ctk.CTkLabel(
                        info_frame,
                        text=f"Monitor {monitor_idx + 1} ({monitor_width}x{monitor_height})",
                        font=ctk.CTkFont(size=16, weight="bold"),
                        text_color=self.COLORS['accent']
                    )
                    monitor_label.pack(anchor="w", pady=(0, 5))

                    # File name
                    filename = os.path.basename(current_path)
                    ctk.CTkLabel(
                        info_frame,
                        text=filename[:40] + "..." if len(filename) > 40 else filename,
                        font=ctk.CTkFont(size=13),
                        text_color=self.COLORS['text_light']
                    ).pack(anchor="w", pady=(0, 10))

                    # Stats
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
        # Clear the container (remove button)
        for widget in self.stats_chart_container.winfo_children():
            widget.destroy()

        # Show loading message
        loading_label = ctk.CTkLabel(
            self.stats_chart_container,
            text="Loading statistics...",
            font=ctk.CTkFont(size=14),
            text_color=self.COLORS['text_muted']
        )
        loading_label.pack(pady=20)

        # Force UI update
        self.root.update()

        # Load the chart
        self._create_statistics_chart(self.stats_chart_container)

        # Remove loading message
        loading_label.destroy()

    def _create_statistics_chart(self, parent):
        """Create statistics charts using matplotlib"""
        chart_card = ctk.CTkFrame(parent, fg_color=self.COLORS['card_bg'], corner_radius=12)
        chart_card.pack(fill="x", pady=10)

        try:
            from datetime import datetime, timedelta

            # Get statistics data
            daily_changes = self.stats_manager.get_daily_changes(14)  # 2 weeks
            provider_stats = self.stats_manager.get_provider_stats(14)
            hourly_dist = self.stats_manager.get_hourly_distribution()

            # Check if we have any data at all
            total_changes = sum(daily_changes.values())
            if total_changes == 0 and not provider_stats and not hourly_dist:
                # No data available - show helpful message
                ctk.CTkLabel(
                    chart_card,
                    text="📊 No statistics available yet!\n\n"
                         "Start using the wallpaper changer to see:\n"
                         "• Daily activity trends\n"
                         "• Provider distribution\n"
                         "• Hourly usage patterns\n"
                         "• Most viewed wallpapers\n\n"
                         "Use the hotkey (ctrl+alt+w) or Quick Actions to change wallpapers!",
                    font=ctk.CTkFont(size=14),
                    text_color=self.COLORS['text_light'],
                    justify="center"
                ).pack(pady=50)
                return

            # Create matplotlib figure with 3 subplots in a grid
            fig = Figure(figsize=(14, 9), facecolor='#3D2B3F')
            fig.subplots_adjust(left=0.08, right=0.95, top=0.95, bottom=0.08, wspace=0.3, hspace=0.5)

            # Use GridSpec for better control
            import matplotlib.gridspec as gridspec
            gs = gridspec.GridSpec(3, 2, figure=fig, height_ratios=[1, 1, 1])

            # 1. Daily changes chart (top left)
            ax1 = fig.add_subplot(gs[0, 0])

            # Sort dates chronologically
            sorted_dates = sorted(daily_changes.keys())
            values = [daily_changes[d] for d in sorted_dates]
            # Format dates nicely
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
            # Rotate x-axis labels for better readability
            ax1.tick_params(axis='x', rotation=45)

            # 2. Provider distribution chart (top right)
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

                # Add percentage labels and improve pie chart
                wedges, texts, autotexts = ax2.pie(counts, labels=providers, autopct='%1.1f%%',
                       colors=colors, textprops={'color': 'white', 'fontsize': 10},
                       startangle=90, explode=[0.05]*len(providers))

                # Make percentage text bold
                for autotext in autotexts:
                    autotext.set_color('black')
                    autotext.set_weight('bold')
                    autotext.set_fontsize(9)

                ax2.set_title('Provider Distribution (Last 14 Days)', color='white', fontsize=13, pad=10, weight='bold')

            # 3. Hourly distribution chart (middle row, spans 2 columns)
            if hourly_dist:
                ax3 = fig.add_subplot(gs[1, :])

                # Ensure all hours 0-23 are present
                hours = list(range(24))
                hourly_counts = [hourly_dist.get(h, 0) for h in hours]

                # Create bar chart with gradient effect
                bars = ax3.bar(hours, hourly_counts, color='#89b4fa', edgecolor='#5b8fd4', linewidth=1.5)

                # Color bars based on value (gradient)
                max_val = max(hourly_counts) if hourly_counts else 1
                for i, (bar, count) in enumerate(zip(bars, hourly_counts)):
                    if max_val > 0:
                        intensity = count / max_val
                        alpha = 0.4 + intensity * 0.6
                        # Use different colors for different times of day (RGB normalized to 0-1, with alpha)
                        if 6 <= i < 12:  # Morning
                            bar.set_color((255/255, 217/255, 61/255, alpha))  # Yellow
                        elif 12 <= i < 18:  # Afternoon
                            bar.set_color((233/255, 69/255, 96/255, alpha))  # Red
                        elif 18 <= i < 22:  # Evening
                            bar.set_color((137/255, 180/255, 250/255, alpha))  # Blue
                        else:  # Night
                            bar.set_color((176/255, 176/255, 176/255, alpha))  # Gray

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

            # 4. Top 10 Most Viewed Wallpapers (bottom row, spans 2 columns)
            top_viewed = self.stats_manager.get_most_viewed(10)
            if top_viewed:
                ax4 = fig.add_subplot(gs[2, :])

                # Get wallpaper names (just filename without path)
                import os
                names = []
                views = []
                for path, view_count in top_viewed:
                    filename = os.path.basename(path)
                    # Truncate long filenames
                    if len(filename) > 30:
                        filename = filename[:27] + "..."
                    names.append(filename)
                    views.append(view_count)

                # Create horizontal bar chart
                y_pos = list(range(len(names)))
                bars = ax4.barh(y_pos, views, color='#00e676', edgecolor='#00a854', linewidth=1.5)

                # Add gradient effect
                max_views = max(views) if views else 1
                for i, (bar, view_count) in enumerate(zip(bars, views)):
                    intensity = view_count / max_views
                    alpha = 0.5 + intensity * 0.5
                    bar.set_color((0/255, 230/255, 118/255, alpha))  # Green with varying alpha

                ax4.set_yticks(y_pos)
                ax4.set_yticklabels(names)
                ax4.invert_yaxis()  # Labels read top-to-bottom
                ax4.set_xlabel('Views', color='#B0B0B0', fontsize=10)
                ax4.set_title('Top 10 Most Viewed Wallpapers', color='white', fontsize=13, pad=10, weight='bold')
                ax4.tick_params(colors='#B0B0B0', labelsize=9)
                ax4.set_facecolor('#3D2B3F')
                for spine in ax4.spines.values():
                    spine.set_edgecolor('#B0B0B0')
                    spine.set_linewidth(0.5)
                ax4.grid(True, alpha=0.2, color='#B0B0B0', linestyle='--', axis='x')

            # Embed in tkinter
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
        # Create container for this view
        view_container = ctk.CTkFrame(self.content_container, fg_color="transparent")
        view_container.pack(fill="both", expand=True)

        # Cache the view
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
        """Create a settings section frame with better visual separation"""
        # Add spacing before section
        ctk.CTkLabel(parent, text="", height=10).pack()

        # Section header with colored accent
        header_frame = ctk.CTkFrame(parent, fg_color="transparent")
        header_frame.pack(fill="x", pady=(10, 5), padx=5)

        # Colored indicator bar
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

        # Section content frame with border
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
            corner_radius=6,
            border_width=1,
            border_color=self.COLORS['card_hover']
        )
        help_frame.pack(fill="x", padx=25, pady=(0, 8))

        help_label = ctk.CTkLabel(
            help_frame,
            text=f"💡 {text}",
            text_color="#89b4fa",  # Light blue for better readability
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
        # Create container for this view
        view_container = ctk.CTkFrame(self.content_container, fg_color="transparent")
        view_container.pack(fill="both", expand=True)

        # Cache the view
        self._view_cache["Logs"] = view_container

        title = ctk.CTkLabel(
            view_container,
            text="Application Logs",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.COLORS['text_light']
        )
        title.pack(pady=(20, 10), padx=20, anchor="w")

        # Buttons frame
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

        # Log text area
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

            # Get banned wallpapers list
            banned_paths = self.stats_manager.get_banned_wallpapers()

            # Get weather overlay setup if enabled
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

                # Get a random wallpaper from cache, excluding banned ones
                entry = self.cache_manager.get_random(
                    monitor_label=monitor_label,
                    banned_paths=banned_paths
                ) or self.cache_manager.get_random(banned_paths=banned_paths)

                if not entry:
                    print(f"No available wallpaper for {monitor_label}")
                    continue

                wallpaper_path = entry.get("path")

                # Apply weather overlay if enabled
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

                # Convert to BMP if needed
                if not wallpaper_path.lower().endswith('.bmp'):
                    bmp_path = str(Path(wallpaper_path).with_suffix('.bmp'))
                    img = Image.open(wallpaper_path)
                    img.save(bmp_path, 'BMP')
                    wallpaper_path = bmp_path

                # Apply to monitor
                controller.set_wallpaper(monitor_id, wallpaper_path)

                # Log the change
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
        # Update button appearance
        button.configure(
            text="♥" if is_fav else "♡",
            fg_color="#ff6b81" if is_fav else "transparent"
        )

    def _toggle_ban(self, wallpaper_path: str, button: ctk.CTkButton):
        """Toggle ban status for a wallpaper"""
        is_banned = self.stats_manager.toggle_ban(wallpaper_path)
        # Update button appearance
        button.configure(
            text="🚫" if is_banned else "⊘",
            fg_color="#ff4444" if is_banned else "transparent"
        )

        # If banned, check if this wallpaper is currently in use on any monitor
        if is_banned:
            try:
                from main import DesktopWallpaperController

                controller = DesktopWallpaperController()
                current_wallpapers = controller.get_all_wallpapers()
                controller.close()

                # Check if the banned wallpaper is currently active on any monitor
                affected_monitors = []
                for wp_info in current_wallpapers:
                    if wp_info.get("path") == wallpaper_path:
                        affected_monitors.append(wp_info)

                if affected_monitors:
                    # Change wallpaper on affected monitors
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
        # Update star buttons
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
                # Show toast notification
                self.show_toast(
                    "Wallpaper Changed",
                    "Applied to all monitors",
                    original_path,
                    duration=4000
                )
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
                    # Show toast notification
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

            # Log wallpaper change to statistics
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
        # Don't stop the service - let it run in background
        self.root.destroy()

    def show_toast(self, title: str, message: str, image_path: Optional[str] = None, duration: int = 3000):
        """Show a toast notification"""
        # Create toast window
        toast = ctk.CTkToplevel(self.root)
        toast.withdraw()  # Hide initially

        # Configure toast
        toast.overrideredirect(True)  # Remove window decorations
        toast.attributes('-topmost', True)  # Always on top

        # Position in bottom right corner
        screen_width = toast.winfo_screenwidth()
        screen_height = toast.winfo_screenheight()
        toast_width = 350
        toast_height = 120 if not image_path else 180

        x = screen_width - toast_width - 20
        y = screen_height - toast_height - 60  # Account for taskbar

        toast.geometry(f"{toast_width}x{toast_height}+{x}+{y}")

        # Toast content
        toast_frame = ctk.CTkFrame(
            toast,
            fg_color=self.COLORS['card_bg'],
            border_color=self.COLORS['accent'],
            border_width=2,
            corner_radius=12
        )
        toast_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # If image provided, show thumbnail
        if image_path and os.path.exists(image_path):
            try:
                img = Image.open(image_path)
                img.thumbnail((80, 80), Image.Resampling.LANCZOS)
                photo = ctk.CTkImage(light_image=img, dark_image=img, size=(80, 80))

                img_label = ctk.CTkLabel(toast_frame, image=photo, text="")
                img_label.pack(side="left", padx=10, pady=10)
                # Keep reference to prevent garbage collection
                toast_frame.image = photo
            except:
                pass

        # Text content
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

        # Show toast
        toast.deiconify()
        self.toast_windows.append(toast)

        # Fade in animation
        toast.attributes('-alpha', 0.0)

        def fade_in(alpha=0.0):
            if alpha < 1.0:
                alpha += 0.1
                toast.attributes('-alpha', alpha)
                toast.after(30, lambda: fade_in(alpha))

        fade_in()

        # Auto close after duration
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

    def run(self):
        """Start the GUI"""
        self.root.mainloop()


def main():
    app = ModernWallpaperGUI()
    app.run()


if __name__ == "__main__":
    main()
