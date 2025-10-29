import atexit
import ctypes
import os
import random
import threading
import time
import uuid
from contextlib import suppress
from datetime import datetime
from typing import Dict, List, Literal, Optional, Tuple

import keyboard
import requests
from PIL import Image, ImageOps
from ctypes import wintypes

from cache_manager import CacheManager
from config import (
    ApiKey,
    CacheSettings,
    KeyBind,
    PexelsApiKey,
    PexelsMode,
    Provider,
    ProvidersSequence,
    SchedulerSettings,
)
from preset_manager import Preset, PresetManager
from scheduler_service import SchedulerService
from tray_app import TrayApp

SPI_SETDESKWALLPAPER = 20
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDWININICHANGE = 0x02
SINGLE_DOWNLOAD_NAME = "wallpaper_current.jpg"
SINGLE_BMP_NAME = "wallpaper_current.bmp"
DOWNLOAD_TEMPLATE = "wallpaper_monitor_{index}.jpg"
BMP_TEMPLATE = "wallpaper_monitor_{index}.bmp"
SPAN_BMP_NAME = "wallpaper_span.bmp"
REQUEST_TIMEOUT = 30
PROVIDER_WALLHAVEN = "wallhaven"
PROVIDER_PEXELS = "pexels"
SUPPORTED_PROVIDERS = {PROVIDER_WALLHAVEN, PROVIDER_PEXELS}
PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"
PEXELS_CURATED_URL = "https://api.pexels.com/v1/curated"
PEXELS_PER_PAGE = 40
PEXELS_MAX_PAGE = 20
PEXELS_MODE_SEARCH = "search"
PEXELS_MODE_CURATED = "curated"
CLSID_DESKTOP_WALLPAPER = uuid.UUID("{C2CF3110-460E-4FC1-B9D0-8A1C0C9CC4BD}")
IID_IDESKTOP_WALLPAPER = uuid.UUID("{B92B56A9-8B55-4E14-9A89-0199BBB6F93B}")
CLSCTX_ALL = 23
COINIT_APARTMENTTHREADED = 0x2
PROVIDER_SEQUENCE_STATE: Dict[Tuple[str, ...], int] = {}
WALLHAVEN_SORT_OPTIONS = {"random", "toplist", "favorites", "views"}
WALLHAVEN_TOP_RANGE_MAP = {
    "1d": "1d",
    "3d": "3d",
    "1w": "1w",
    "1m": "1M",
    "3m": "3M",
    "6m": "6M",
    "1y": "1y",
}

if not hasattr(wintypes, "HMONITOR"):
    wintypes.HMONITOR = wintypes.HANDLE

try:
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS  # type: ignore[attr-defined]
except AttributeError:  # Pillow < 9
    RESAMPLE_LANCZOS = Image.LANCZOS


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> "GUID":
        raw = value.bytes_le
        data4 = (ctypes.c_ubyte * 8).from_buffer_copy(raw[8:])
        return cls(
            ctypes.c_ulong(int.from_bytes(raw[0:4], "little")),
            ctypes.c_ushort(int.from_bytes(raw[4:6], "little")),
            ctypes.c_ushort(int.from_bytes(raw[6:8], "little")),
            data4,
        )


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


HRESULT = ctypes.c_long
LPVOID = ctypes.c_void_p
LPWSTR = ctypes.c_wchar_p
UINT = ctypes.c_uint

QueryInterfaceProto = ctypes.WINFUNCTYPE(HRESULT, LPVOID, ctypes.POINTER(GUID), ctypes.POINTER(LPVOID))
AddRefProto = ctypes.WINFUNCTYPE(ctypes.c_ulong, LPVOID)
ReleaseProto = ctypes.WINFUNCTYPE(ctypes.c_ulong, LPVOID)
SetWallpaperProto = ctypes.WINFUNCTYPE(HRESULT, LPVOID, LPWSTR, LPWSTR)
GetWallpaperProto = ctypes.WINFUNCTYPE(HRESULT, LPVOID, LPWSTR, ctypes.POINTER(LPWSTR))
GetMonitorDevicePathAtProto = ctypes.WINFUNCTYPE(HRESULT, LPVOID, UINT, ctypes.POINTER(LPWSTR))
GetMonitorDevicePathCountProto = ctypes.WINFUNCTYPE(HRESULT, LPVOID, ctypes.POINTER(UINT))
GetMonitorRectProto = ctypes.WINFUNCTYPE(HRESULT, LPVOID, LPWSTR, ctypes.POINTER(RECT))


class IDesktopWallpaperVtbl(ctypes.Structure):
    _fields_ = [
        ("QueryInterface", QueryInterfaceProto),
        ("AddRef", AddRefProto),
        ("Release", ReleaseProto),
        ("SetWallpaper", SetWallpaperProto),
        ("GetWallpaper", GetWallpaperProto),
        ("GetMonitorDevicePathAt", GetMonitorDevicePathAtProto),
        ("GetMonitorDevicePathCount", GetMonitorDevicePathCountProto),
        ("GetMonitorRECT", GetMonitorRectProto),
        ("SetBackgroundColor", LPVOID),
        ("GetBackgroundColor", LPVOID),
        ("SetPosition", LPVOID),
        ("GetPosition", LPVOID),
        ("SetSlideshow", LPVOID),
        ("GetSlideshow", LPVOID),
        ("SetSlideshowOptions", LPVOID),
        ("GetSlideshowOptions", LPVOID),
        ("AdvanceSlideshow", LPVOID),
        ("GetStatus", LPVOID),
        ("Enable", LPVOID),
    ]


class IDesktopWallpaper(ctypes.Structure):
    _fields_ = [("lpVtbl", ctypes.POINTER(IDesktopWallpaperVtbl))]


class DesktopWallpaperController:
    def __init__(self) -> None:
        self._ole32 = ctypes.OleDLL("ole32")
        hr = self._ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)
        if hr not in (0, 1):
            raise ctypes.WinError(hr)

        self._ole32.CoCreateInstance.argtypes = [
            ctypes.POINTER(GUID),
            LPVOID,
            ctypes.c_ulong,
            ctypes.POINTER(GUID),
            ctypes.POINTER(LPVOID),
        ]
        self._ole32.CoCreateInstance.restype = HRESULT
        self._ole32.CoTaskMemFree.argtypes = [LPVOID]
        self._ole32.CoTaskMemFree.restype = None

        clsid_guid = GUID.from_uuid(CLSID_DESKTOP_WALLPAPER)
        iid_guid = GUID.from_uuid(IID_IDESKTOP_WALLPAPER)
        iface_ptr = LPVOID()

        hr = self._ole32.CoCreateInstance(
            ctypes.byref(clsid_guid),
            None,
            CLSCTX_ALL,
            ctypes.byref(iid_guid),
            ctypes.byref(iface_ptr),
        )
        if hr != 0:
            self._ole32.CoUninitialize()
            raise ctypes.WinError(hr)

        self._iface = ctypes.cast(iface_ptr.value, ctypes.POINTER(IDesktopWallpaper))
        self._vtable = self._iface.contents.lpVtbl.contents

    def _check(self, hr: int) -> None:
        if hr != 0:
            raise ctypes.WinError(hr)

    def enumerate_monitors(self) -> List[Dict[str, int]]:
        count = UINT()
        self._check(self._vtable.GetMonitorDevicePathCount(self._iface, ctypes.byref(count)))

        monitors: List[Dict[str, int]] = []
        for index in range(count.value):
            path_ptr = LPWSTR()
            self._check(self._vtable.GetMonitorDevicePathAt(self._iface, index, ctypes.byref(path_ptr)))

            rect = RECT()
            self._check(self._vtable.GetMonitorRECT(self._iface, path_ptr, ctypes.byref(rect)))

            monitor_id = path_ptr.value
            self._ole32.CoTaskMemFree(ctypes.cast(path_ptr, LPVOID))
            if monitor_id:
                monitors.append(
                    {
                        "id": monitor_id,
                        "width": rect.width,
                        "height": rect.height,
                        "left": rect.left,
                        "top": rect.top,
                        "right": rect.right,
                        "bottom": rect.bottom,
                    }
                )

        monitors.sort(key=lambda item: (item.get("left", 0), item.get("top", 0)))
        return monitors

    def set_wallpaper(self, monitor_id: str, image_path: str) -> None:
        self._check(self._vtable.SetWallpaper(self._iface, monitor_id, image_path))

    def close(self) -> None:
        if hasattr(self, "_vtable") and self._iface:
            self._vtable.Release(self._iface)
            self._iface = None
        self._ole32.CoUninitialize()


def enumerate_monitors_user32() -> List[Dict[str, int]]:
    monitors: List[Dict[str, int]] = []
    user32 = ctypes.windll.user32

    with suppress(AttributeError):
        user32.SetProcessDPIAware()

    MONITORENUMPROC = ctypes.WINFUNCTYPE(
        ctypes.c_int, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(RECT), wintypes.LPARAM
    )

    def callback(hmonitor, _hdc, lprc_monitor, _lparam) -> int:
        rect = lprc_monitor.contents
        monitors.append(
            {
                "id": hex(int(hmonitor)),
                "width": rect.width,
                "height": rect.height,
                "left": rect.left,
                "top": rect.top,
                "right": rect.right,
                "bottom": rect.bottom,
            }
        )
        return 1

    enum_proc = MONITORENUMPROC(callback)
    if not user32.EnumDisplayMonitors(None, None, enum_proc, 0):
        raise ctypes.WinError()

    monitors.sort(key=lambda item: (item.get("left", 0), item.get("top", 0)))
    return monitors


def normalize_string(value: Optional[str]) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else ""


def ensure_provider(name: str) -> str:
    normalized = name.lower()
    if normalized not in SUPPORTED_PROVIDERS:
        raise RuntimeError(
            f"Unsupported provider '{name}'. Use '{PROVIDER_WALLHAVEN}' or '{PROVIDER_PEXELS}'."
        )
    return normalized


def normalize_provider(value: Optional[str], fallback: Optional[str] = None) -> str:
    for candidate in (value, fallback, Provider):
        provider = normalize_string(candidate)
        if provider:
            return ensure_provider(provider)
    return PROVIDER_WALLHAVEN


def normalize_wallhaven_sorting(value: Optional[str]) -> str:
    sorting = (normalize_string(value) or "random").lower()
    if sorting not in WALLHAVEN_SORT_OPTIONS:
        return "random"
    return sorting


def normalize_wallhaven_top_range(value: Optional[str]) -> str:
    key = normalize_string(value).lower()
    if not key:
        return ""
    return WALLHAVEN_TOP_RANGE_MAP.get(key, "")


class WallpaperApp:
    def __init__(self) -> None:
        self.preset_manager = PresetManager()
        self.active_preset = self.preset_manager.default_name

        cache_dir = CacheSettings.get("directory") or os.path.join(
            os.path.expanduser("~"), "WallpaperChangerCache"
        )
        self.cache_manager = CacheManager(
            cache_dir,
            max_items=int(CacheSettings.get("max_items", 60)),
            enable_rotation=bool(CacheSettings.get("enable_offline_rotation", True)),
        )

        self.scheduler = SchedulerService(self, SchedulerSettings)
        self.tray_app = TrayApp(self)
        self._stop_event = threading.Event()
        self.pid_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wallpaperchanger.pid")
        self._pid_registered = False

    def start(self) -> None:
        print(f"Initial wallpaper update in progress (hotkey: {KeyBind})...")
        self._write_pid()
        self.change_wallpaper("startup")
        self._register_hotkey()
        self.scheduler.start()
        self.tray_app.start()
        self._run_loop()

    def stop(self) -> None:
        self._stop_event.set()
        keyboard.unhook_all_hotkeys()
        self.scheduler.stop()
        self.tray_app.stop()
        self._remove_pid()

    def _run_loop(self) -> None:
        try:
            while not self._stop_event.is_set():
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def _write_pid(self) -> None:
        try:
            with open(self.pid_path, "w", encoding="utf-8") as handle:
                handle.write(str(os.getpid()))
            if not self._pid_registered:
                atexit.register(self._remove_pid)
                self._pid_registered = True
        except OSError as error:
            print(f"Unable to write PID file: {error}")

    def _remove_pid(self) -> None:
        if os.path.exists(self.pid_path):
            try:
                os.remove(self.pid_path)
            except OSError:
                pass

    def _register_hotkey(self) -> None:
        keyboard.add_hotkey(KeyBind, lambda: self.change_wallpaper("hotkey"))

    def set_active_preset(self, preset_name: str) -> None:
        if preset_name == self.active_preset:
            return
        self.active_preset = preset_name
        print(f"Preset switched to '{preset_name}'")
        self.change_wallpaper("preset-switch", preset_name=preset_name)

    def pick_active_provider(self, preset: Preset, fallback_provider: Optional[str] = None) -> str:
        sequence = []
        if preset.providers:
            sequence = [ensure_provider(provider) for provider in preset.providers]
        elif ProvidersSequence:
            sequence = [ensure_provider(provider) for provider in ProvidersSequence]

        if not sequence:
            sequence = [normalize_provider(fallback_provider)]

        key = tuple(sequence)
        current_index = PROVIDER_SEQUENCE_STATE.get(key, 0)
        provider = sequence[current_index % len(sequence)]
        PROVIDER_SEQUENCE_STATE[key] = (current_index + 1) % len(sequence)
        return provider

    def change_wallpaper(
        self,
        trigger: Literal["startup", "hotkey", "scheduler", "tray", "tray-cache", "preset-switch"],
        preset_name: Optional[str] = None,
        provider_override: Optional[str] = None,
        use_cache: bool = False,
    ) -> None:
        preset = self.preset_manager.get_preset(preset_name or self.active_preset)
        provider = (
            ensure_provider(provider_override)
            if provider_override
            else self.pick_active_provider(preset, fallback_provider=Provider)
        )

        manager = self._create_desktop_controller()
        monitors = []
        if manager:
            try:
                monitors = manager.enumerate_monitors()
            except OSError as error:
                print(f"Per-monitor wallpaper initialization failed: {error}")
                monitors = []

        if not monitors:
            try:
                monitors = enumerate_monitors_user32()
            except OSError as error:
                print(f"Monitor enumeration via user32 failed: {error}")
                monitors = []

        tasks = self._build_tasks(monitors, preset, provider)

        if use_cache and self.apply_cached_wallpaper(trigger):
            return

        results: List[Tuple[str, str]] = []
        try:
            if manager and len(tasks) > 1:
                for index, task in enumerate(tasks):
                    line, used_provider = self._process_task(task, index, manager)
                    results.append((line, used_provider))
            elif len(tasks) > 1:
                print("Per-monitor API unavailable; composing a span wallpaper instead.")
                results.extend(self._apply_span(tasks))
            else:
                line, used_provider = self._process_single(tasks[0])
                results.append((line, used_provider))
        finally:
            if manager:
                manager.close()
            self.cache_manager.prune()

        providers_used = sorted({prov for _, prov in results}) or [provider]
        print(
            f"Wallpaper updated ({trigger}) using providers {', '.join(providers_used)} "
            f"and preset '{preset.name}'."
        )
        for line, _ in results:
            print(f" - {line}")

    def apply_cached_wallpaper(self, trigger: str) -> bool:
        if not self.cache_manager.enable_rotation:
            return False
        monitors = []
        manager = self._create_desktop_controller()
        if manager:
            try:
                monitors = manager.enumerate_monitors()
            except OSError:
                monitors = []

        if not monitors:
            try:
                monitors = enumerate_monitors_user32()
            except OSError:
                monitors = []

        if not monitors:
            if manager:
                manager.close()
            entry = self.cache_manager.get_random()
            if not entry:
                return False
            bmp_path = self._convert_to_bmp(entry["path"], SINGLE_BMP_NAME, None)
            self._apply_legacy_wallpaper(bmp_path)
            print(f"Wallpaper updated ({trigger}) from cache | {entry.get('source_info')}")
            return True

        if not manager:
            entries = [
                self.cache_manager.get_random(monitor_label=f"Monitor {idx + 1}")
                or self.cache_manager.get_random()
                for idx in range(len(monitors))
            ]
            results = self._apply_span_cached(monitors, entries)
            if results:
                print(f"Wallpaper updated ({trigger}) from cache.")
                for line in results:
                    print(f" - {line}")
                return True
            return False

        results = []
        try:
            for index, monitor in enumerate(monitors):
                label = f"Monitor {index + 1}"
                entry = self.cache_manager.get_random(monitor_label=label) or self.cache_manager.get_random()
                if not entry:
                    continue
                bmp_name = BMP_TEMPLATE.format(index=index)
                bmp_path = self._convert_to_bmp(entry["path"], bmp_name, (monitor["width"], monitor["height"]))
                try:
                    manager.set_wallpaper(monitor["id"], bmp_path)
                except OSError as error:
                    print(f"Failed to set cached wallpaper on {label}: {error}")
                    continue
                results.append(f"{label}: {entry.get('source_info')}")
        finally:
            manager.close()

        if results:
            print(f"Wallpaper updated ({trigger}) from cache.")
            for line in results:
                print(f" - {line}")
            return True
        return False

    def _create_desktop_controller(self) -> Optional[DesktopWallpaperController]:
        try:
            return DesktopWallpaperController()
        except OSError as error:
            print(f"Per-monitor wallpaper initialization failed: {error}")
            return None

    def _build_tasks(self, monitors: List[Dict[str, int]], preset: Preset, provider: str) -> List[Dict]:
        tasks: List[Dict] = []
        multi_monitor = len(monitors) > 1

        for index, monitor in enumerate(monitors or [{}]):
            override = self.preset_manager.get_monitor_override(index)
            monitor_preset = self.preset_manager.get_preset(override.get("preset") or preset.name)
            monitor_provider = normalize_provider(override.get("provider"), fallback=provider)

            query_override = override.get("query") or None
            query = self.preset_manager.pick_query(monitor_preset, query_override)

            wallhaven_settings = monitor_preset.get_wallhaven_settings()
            if override.get("wallhaven_sorting"):
                wallhaven_settings["sorting"] = normalize_wallhaven_sorting(override["wallhaven_sorting"])
            if override.get("wallhaven_top_range"):
                wallhaven_settings["top_range"] = normalize_wallhaven_top_range(override["wallhaven_top_range"])
            if override.get("purity"):
                wallhaven_settings["purity"] = override["purity"]
            if override.get("screen_resolution"):
                wallhaven_settings["atleast"] = override["screen_resolution"]

            provider_candidates = [monitor_provider]
            if not override.get("provider"):
                for candidate in monitor_preset.providers:
                    normalized = ensure_provider(candidate)
                    if normalized not in provider_candidates:
                        provider_candidates.append(normalized)
                for candidate in ProvidersSequence or []:
                    normalized = ensure_provider(candidate)
                    if normalized not in provider_candidates:
                        provider_candidates.append(normalized)

            task = {
                "preset": monitor_preset.name,
                "provider": monitor_provider,
                "provider_candidates": provider_candidates,
                "monitor": monitor,
                "label": override.get("name") or f"Monitor {index + 1}",
                "query": query,
                "wallhaven": wallhaven_settings,
                "pexels": monitor_preset.get_pexels_settings(),
                "target_size": (monitor.get("width"), monitor.get("height"))
                if monitor
                else self._get_primary_size(),
            }
            tasks.append(task)

            if not multi_monitor:
                break

        if not tasks:
            fallback_candidates = [provider]
            for candidate in preset.providers:
                normalized = ensure_provider(candidate)
                if normalized not in fallback_candidates:
                    fallback_candidates.append(normalized)
            for candidate in ProvidersSequence or []:
                normalized = ensure_provider(candidate)
                if normalized not in fallback_candidates:
                    fallback_candidates.append(normalized)
            tasks.append(
                {
                    "preset": preset.name,
                    "provider": provider,
                    "provider_candidates": fallback_candidates,
                    "monitor": None,
                    "label": "All monitors",
                    "query": preset.build_query(None),
                    "wallhaven": preset.get_wallhaven_settings(),
                    "pexels": preset.get_pexels_settings(),
                    "target_size": self._get_primary_size(),
                }
            )

        return tasks

    def _process_task(self, task: Dict, index: int, manager: DesktopWallpaperController) -> Tuple[str, str]:
        url, source_info, metadata = self._resolve_wallpaper(task)
        download_path = os.path.join(os.path.expanduser("~"), DOWNLOAD_TEMPLATE.format(index=index))
        self._download_wallpaper(url, download_path)
        cached_path = self.cache_manager.store(download_path, metadata) or download_path
        if cached_path != download_path:
            with suppress(OSError):
                os.remove(download_path)
        bmp_path = os.path.join(os.path.expanduser("~"), BMP_TEMPLATE.format(index=index))
        self._convert_to_bmp(cached_path, bmp_path, task["target_size"])
        manager.set_wallpaper(task["monitor"]["id"], bmp_path)
        return f"{task['label']}: {source_info}", metadata["provider"]

    def _process_single(self, task: Dict) -> Tuple[str, str]:
        url, source_info, metadata = self._resolve_wallpaper(task)
        download_path = os.path.join(os.path.expanduser("~"), SINGLE_DOWNLOAD_NAME)
        self._download_wallpaper(url, download_path)
        cached_path = self.cache_manager.store(download_path, metadata) or download_path
        if cached_path != download_path:
            with suppress(OSError):
                os.remove(download_path)
        bmp_path = os.path.join(os.path.expanduser("~"), SINGLE_BMP_NAME)
        self._convert_to_bmp(cached_path, bmp_path, task["target_size"])
        self._apply_legacy_wallpaper(bmp_path)
        return f"{task['label']}: {source_info}", metadata["provider"]

    def _apply_span(self, tasks: List[Dict]) -> List[Tuple[str, str]]:
        home_dir = os.path.expanduser("~")
        composite = None
        results: List[Tuple[str, str]] = []

        monitors = [task["monitor"] for task in tasks if task.get("monitor")]
        if not monitors:
            return []

        min_left = min(m.get("left", 0) for m in monitors)
        min_top = min(m.get("top", 0) for m in monitors)
        max_right = max(m.get("right", m.get("left", 0) + m.get("width", 0)) for m in monitors)
        max_bottom = max(m.get("bottom", m.get("top", 0) + m.get("height", 0)) for m in monitors)

        total_width = max_right - min_left
        total_height = max_bottom - min_top
        composite = Image.new("RGB", (total_width, total_height), color=(0, 0, 0))

        for index, task in enumerate(tasks):
            url, source_info, metadata = self._resolve_wallpaper(task)
            download_path = os.path.join(home_dir, DOWNLOAD_TEMPLATE.format(index=index))
            self._download_wallpaper(url, download_path)
            cached_path = self.cache_manager.store(download_path, metadata) or download_path
            if cached_path != download_path:
                with suppress(OSError):
                    os.remove(download_path)
            image = self._render_image(cached_path, task["target_size"])
            monitor = task["monitor"]
            offset_x = monitor.get("left", 0) - min_left
            offset_y = monitor.get("top", 0) - min_top
            composite.paste(image, (offset_x, offset_y))
            results.append((f"{task['label']}: {source_info}", metadata["provider"]))

        span_path = os.path.join(home_dir, SPAN_BMP_NAME)
        composite.save(span_path, "BMP")
        composite.close()
        self._apply_legacy_wallpaper(span_path)
        return results

    def _apply_span_cached(self, monitors: List[Dict[str, int]], entries: List[Optional[Dict]]) -> List[str]:
        min_left = min(m.get("left", 0) for m in monitors)
        min_top = min(m.get("top", 0) for m in monitors)
        max_right = max(m.get("right", m.get("left", 0) + m.get("width", 0)) for m in monitors)
        max_bottom = max(m.get("bottom", m.get("top", 0) + m.get("height", 0)) for m in monitors)

        total_width = max_right - min_left
        total_height = max_bottom - min_top

        composite = Image.new("RGB", (total_width, total_height), color=(0, 0, 0))
        results: List[str] = []

        for monitor, entry in zip(monitors, entries):
            if not entry:
                continue
            image = self._render_image(entry["path"], (monitor["width"], monitor["height"]))
            offset_x = monitor.get("left", 0) - min_left
            offset_y = monitor.get("top", 0) - min_top
            composite.paste(image, (offset_x, offset_y))
            results.append(f"{entry.get('monitor', 'Monitor')} (cache): {entry.get('source_info')}")

        if not results:
            composite.close()
            return results

        span_path = os.path.join(os.path.expanduser("~"), SPAN_BMP_NAME)
        composite.save(span_path, "BMP")
        composite.close()
        self._apply_legacy_wallpaper(span_path)
        return results

    def _fetch_wallpaper(self, task: Dict) -> Tuple[str, str, Dict]:
        provider = task["provider"]
        query = task["query"]
        if provider == PROVIDER_WALLHAVEN:
            url, source_info = self._fetch_wallhaven(task)
        elif provider == PROVIDER_PEXELS:
            url, source_info = self._fetch_pexels(task)
        else:
            raise RuntimeError(f"Unsupported provider '{provider}'")

        metadata = {
            "preset": task["preset"],
            "provider": provider,
            "query": query,
            "monitor": task["label"],
            "source_info": source_info,
        }
        return url, source_info, metadata

    def _fetch_wallhaven(self, task: Dict) -> Tuple[str, str]:
        settings = task["wallhaven"]
        sorting = normalize_wallhaven_sorting(settings.get("sorting"))
        params = {
            "sorting": sorting,
            "apikey": normalize_string(ApiKey),
            "purity": normalize_string(settings.get("purity")),
            "q": task["query"],
            "resolutions": normalize_string(settings.get("resolutions")),
            "atleast": normalize_string(settings.get("atleast")),
            "colors": normalize_string(settings.get("colors")),
            "ratios": normalize_string(settings.get("ratios")),
            "categories": normalize_string(settings.get("categories")),
        }
        top_range = normalize_wallhaven_top_range(settings.get("top_range"))
        if sorting == "toplist" and top_range:
            params["topRange"] = top_range

        params = {key: value for key, value in params.items() if value}
        params["order"] = "desc"

        response = requests.get("https://wallhaven.cc/api/v1/search", params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        wallpapers = data.get("data", [])

        fallback_triggered = False
        if not wallpapers and sorting != "random":
            fallback_params = dict(params)
            fallback_params["sorting"] = "random"
            fallback_params.pop("topRange", None)
            fallback_response = requests.get(
                "https://wallhaven.cc/api/v1/search", params=fallback_params, timeout=REQUEST_TIMEOUT
            )
            fallback_response.raise_for_status()
            data = fallback_response.json()
            wallpapers = data.get("data", [])
            if wallpapers:
                fallback_triggered = True
                sorting = "random"
                params = fallback_params

        if not wallpapers:
            raise RuntimeError(
                f"Failed to retrieve a wallpaper from Wallhaven (sorting={settings.get('sorting')}, "
                f"topRange={settings.get('top_range')}, query={task['query']})."
            )

        choice = random.choice(wallpapers)
        meta = [sorting]
        if params.get("topRange"):
            meta.append(f"topRange={params['topRange']}")
        if fallback_triggered:
            meta.append(f"fallback from {settings.get('sorting')}")

        source_info = f"Wallhaven ({', '.join(meta)}) | {choice.get('id', 'unknown')} ({choice.get('url', 'n/a')})"
        return choice["path"], source_info

    def _fetch_pexels(self, task: Dict) -> Tuple[str, str]:
        if not normalize_string(PexelsApiKey):
            raise RuntimeError("Pexels provider selected but PexelsApiKey is empty.")

        mode = normalize_string(PexelsMode) or PEXELS_MODE_SEARCH
        headers = {"Authorization": normalize_string(PexelsApiKey)}
        page = random.randint(1, PEXELS_MAX_PAGE)
        params = {"per_page": PEXELS_PER_PAGE, "page": page}
        filters = task["pexels"]

        if mode == PEXELS_MODE_CURATED:
            url = PEXELS_CURATED_URL
        else:
            url = PEXELS_SEARCH_URL
            params.update(
                {
                    "query": task["query"],
                    "orientation": filters.get("orientation", "landscape"),
                    "size": filters.get("size", "large"),
                }
            )
            color = filters.get("color")
            if color:
                params["color"] = color

        response = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        photos = data.get("photos", [])
        if not photos:
            raise RuntimeError("No photos returned from Pexels with the current configuration.")

        choice = random.choice(photos)
        src = choice.get("src", {})
        image_url = src.get("original") or src.get("large2x") or src.get("large")
        if not image_url:
            raise RuntimeError("Selected Pexels photo does not include a downloadable URL.")

        photographer = choice.get("photographer") or "Unknown photographer"
        photographer_url = choice.get("photographer_url")
        mode_info = "curated" if mode == PEXELS_MODE_CURATED else "search"
        source_info = f"Pexels ({mode_info}) | {photographer}"
        if photographer_url:
            source_info += f" ({photographer_url})"

        return image_url, source_info

    def _resolve_wallpaper(self, task: Dict) -> Tuple[str, str, Dict]:
        candidates = task.get("provider_candidates") or [task.get("provider")]
        last_error: Optional[Exception] = None
        for candidate in candidates:
            if not candidate:
                continue
            task["provider"] = candidate
            try:
                url, source_info, metadata = self._fetch_wallpaper(task)
                metadata["provider"] = candidate
                return url, source_info, metadata
            except Exception as exc:
                last_error = exc
        if last_error:
            raise last_error
        raise RuntimeError("No providers available for wallpaper download.")

    def _download_wallpaper(self, url: str, target_path: str) -> None:
        response = requests.get(url, stream=True, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        with open(target_path, "wb") as handle:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    handle.write(chunk)

    def _render_image(self, source_path: str, size: Optional[Tuple[int, int]]) -> Image.Image:
        with Image.open(source_path) as image:
            rgb_image = image.convert("RGB")
            if size and all(size):
                rgb_image = ImageOps.fit(rgb_image, size, method=RESAMPLE_LANCZOS)
            return rgb_image.copy()

    def _convert_to_bmp(self, source_path: str, target_name: str, size: Optional[Tuple[int, int]]) -> str:
        target_path = os.path.join(os.path.expanduser("~"), target_name)
        image = self._render_image(source_path, size)
        try:
            image.save(target_path, "BMP")
        finally:
            image.close()
        return target_path

    def _apply_legacy_wallpaper(self, image_path: str) -> None:
        result = ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER, 0, image_path, SPIF_UPDATEINIFILE | SPIF_SENDWININICHANGE
        )
        if not result:
            raise ctypes.WinError()

    def _get_primary_size(self) -> Optional[Tuple[int, int]]:
        user32 = ctypes.windll.user32
        with suppress(AttributeError):
            user32.SetProcessDPIAware()
        width = user32.GetSystemMetrics(0)
        height = user32.GetSystemMetrics(1)
        if width and height:
            return int(width), int(height)
        return None


if __name__ == "__main__":
    app = WallpaperApp()
    app.start()
