import json
import os
import random
import shutil
import threading
import time
from typing import Dict, List, Optional
from color_analyzer import ColorAnalyzer


class CacheManager:
    def __init__(self, directory: str, max_items: int = 50, enable_rotation: bool = True):
        self.directory = os.path.abspath(os.path.expanduser(directory))
        self.max_items = max_items
        self.enable_rotation = enable_rotation
        self.index_path = os.path.join(self.directory, "index.json")
        self._lock = threading.Lock()
        self._index: Dict[str, List[Dict]] = {"version": 1, "items": []}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.directory):
            os.makedirs(self.directory, exist_ok=True)
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, "r", encoding="utf-8") as handle:
                    self._index = json.load(handle)
            except (json.JSONDecodeError, OSError):
                self._index = {"version": 1, "items": []}

    def _save(self) -> None:
        tmp_path = f"{self.index_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(self._index, handle, indent=2)
        os.replace(tmp_path, self.index_path)

    def store(self, source_path: str, metadata: Dict[str, str]) -> Optional[str]:
        if not os.path.exists(source_path):
            return None

        with self._lock:
            # Check for duplicates
            source_info = metadata.get("source_info")
            if source_info:
                for item in self._index.get("items", []):
                    if item.get("source_info") == source_info:
                        return item.get("path")

            os.makedirs(self.directory, exist_ok=True)
            extension = os.path.splitext(source_path)[1] or ".jpg"
            cache_id = f"{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
            target_path = os.path.join(self.directory, f"{cache_id}{extension}")
            shutil.copy2(source_path, target_path)

            # Extract dominant colors for filtering
            try:
                color_categories = ColorAnalyzer.get_color_categories(target_path, num_colors=3)
                primary_color = ColorAnalyzer.get_primary_color_category(target_path)
            except Exception as e:
                print(f"[WARNING] Failed to extract colors from {target_path}: {e}")
                color_categories = []
                primary_color = None

            entry = dict(metadata)
            entry.update(
                {
                    "id": cache_id,
                    "path": target_path,
                    "timestamp": time.time(),
                    "color_categories": color_categories,
                    "primary_color": primary_color,
                }
            )
            self._index.setdefault("items", []).append(entry)
            self._index["items"] = self._index["items"][-self.max_items :]
            self._save()
            return target_path

    def get_random(self, preset: Optional[str] = None, monitor_label: Optional[str] = None,
                   banned_paths: Optional[List[str]] = None) -> Optional[Dict]:
        with self._lock:
            items = list(self._index.get("items", []))

        if preset:
            items = [item for item in items if item.get("preset") == preset]
        if monitor_label and items:
            filtered = [item for item in items if item.get("monitor") == monitor_label]
            if filtered:
                items = filtered

        # Exclude banned wallpapers
        if banned_paths:
            items = [item for item in items if item.get("path") not in banned_paths]

        if not items:
            return None
        return random.choice(items)

    def has_items(self) -> bool:
        with self._lock:
            return bool(self._index.get("items"))

    def list_entries(self) -> List[Dict]:
        """Return list of cached entries, most recent first"""
        with self._lock:
            items = self._index.get("items", [])
            return list(reversed(items))

    def get_all_colors(self) -> List[str]:
        """Get all unique color categories from cached wallpapers"""
        with self._lock:
            items = self._index.get("items", [])
            colors = set()
            for item in items:
                if "color_categories" in item and item["color_categories"]:
                    colors.update(item["color_categories"])
                elif "primary_color" in item and item["primary_color"]:
                    colors.add(item["primary_color"])
            return sorted(list(colors))

    def get_by_color(self, color: str) -> List[Dict]:
        """Get wallpapers that contain the specified color"""
        with self._lock:
            items = self._index.get("items", [])
            filtered = []
            for item in items:
                color_categories = item.get("color_categories", [])
                primary_color = item.get("primary_color")
                if color in color_categories or color == primary_color:
                    filtered.append(item)
            return list(reversed(filtered))

    @property
    def cache_dir(self) -> str:
        """Return cache directory path"""
        return self.directory

    def prune(self) -> None:
        with self._lock:
            items = self._index.get("items", [])
            if len(items) <= self.max_items:
                return
            excess = len(items) - self.max_items
            old_items = items[:excess]
            self._index["items"] = items[excess:]
            for entry in old_items:
                try:
                    os.remove(entry.get("path", ""))
                except OSError:
                    pass
            self._save()

    def open_folder(self) -> None:
        try:
            os.startfile(self.directory)
        except OSError:
            pass
