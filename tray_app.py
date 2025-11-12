import os
import subprocess
import threading
from typing import List, Optional

import pystray
from PIL import Image, ImageDraw


def _create_icon(size: int = 64) -> Image.Image:
    image = Image.new("RGBA", (size, size), (30, 30, 30, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, size, size], fill=(34, 40, 49, 255))
    draw.text((size * 0.25, size * 0.2), "W", fill=(0, 173, 181, 255))
    draw.text((size * 0.25, size * 0.55), "C", fill=(238, 238, 238, 255))
    return image


class TrayApp:
    def __init__(self, controller):
        self.controller = controller
        self.icon = pystray.Icon(
            "WallpaperChanger",
            icon=_create_icon(),
            title="Wallpaper Changer",
            menu=self._build_menu(),
        )
        self._thread: Optional[threading.Thread] = None

    def _build_menu(self) -> pystray.Menu:
        playlist_definitions = self.controller.playlist_manager.list_playlists()
        if playlist_definitions:
            playlist_items: List[pystray.MenuItem] = [
                pystray.MenuItem(
                    "Disattiva playlist",
                    self._clear_playlist,
                    checked=lambda item: self.controller.active_playlist is None,
                ),
                pystray.Menu.SEPARATOR,
            ]
            playlist_items.extend(
                pystray.MenuItem(
                    playlist.title,
                    self._make_set_playlist(playlist.name),
                    checked=self._make_playlist_checked(playlist.name),
                )
                for playlist in playlist_definitions
            )
        else:
            playlist_items = [
                pystray.MenuItem("Nessuna playlist disponibile", lambda *_: None, enabled=False)
            ]

        return pystray.Menu(
            pystray.MenuItem("Change Wallpaper", self._change_now),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Presets",
                pystray.Menu(
                    *[
                        pystray.MenuItem(
                            preset.title,
                            self._make_set_preset(preset.name),
                            checked=self._make_preset_checked(preset.name),
                        )
                        for preset in self.controller.preset_manager.list_presets()
                    ]
                ),
            ),
            pystray.MenuItem(
                "Playlists",
                pystray.Menu(*playlist_items),
            ),
            pystray.MenuItem(
                "Toggle Scheduler",
                self._toggle_scheduler,
                checked=lambda item: self.controller.scheduler.enabled,
            ),
            pystray.MenuItem("Next From Cache", self._next_from_cache, enabled=self._cache_available),
            pystray.MenuItem("Open Cache Folder", self._open_cache),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Open Dashboard", self._open_settings_gui),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._quit),
        )

    def _cache_available(self, _: pystray.MenuItem) -> bool:
        return self.controller.cache_manager is not None and self.controller.cache_manager.has_items()

    def _change_now(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self.controller.change_wallpaper("tray")

    def _next_from_cache(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self.controller.apply_cached_wallpaper("tray-cache")

    def _open_cache(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        if self.controller.cache_manager:
            self.controller.cache_manager.open_folder()

    def _open_settings_gui(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """Open the modern GUI"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))

            # Use the modern GUI instead of the old config GUI
            gui_script = os.path.join(script_dir, "gui_modern.py")
            subprocess.Popen(["pythonw", gui_script], shell=False)
        except Exception as e:
            print(f"Failed to open GUI: {e}")

    def _toggle_scheduler(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self.controller.scheduler.toggle()

    def _make_set_preset(self, preset_name: str):
        def handler(icon: pystray.Icon, item: pystray.MenuItem) -> None:
            self.controller.set_active_preset(preset_name)

        return handler

    def _make_preset_checked(self, preset_name: str):
        return lambda item: self.controller.active_preset == preset_name

    def _make_set_playlist(self, playlist_name: str):
        def handler(icon: pystray.Icon, item: pystray.MenuItem) -> None:
            self.controller.set_active_playlist(playlist_name)

        return handler

    def _make_playlist_checked(self, playlist_name: str):
        return lambda item: self.controller.active_playlist == playlist_name

    def _clear_playlist(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self.controller.set_active_playlist(None)

    def _quit(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self.controller.stop()
        icon.stop()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self.icon.run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self.icon:
            try:
                self.icon.stop()
            except RuntimeError:
                # Icon loop might already be stopping; ignore race conditions
                pass
        thread = self._thread
        self._thread = None
        if thread and thread.is_alive() and threading.current_thread() != thread:
            thread.join(timeout=2)
