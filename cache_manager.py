import json
import os
import random
import shutil
import threading
import time
from typing import Dict, List, Optional
from color_analyzer import ColorAnalyzer


class CacheManager:
    def __init__(self, directory: str, max_items: int = 50, enable_rotation: bool = True, stats_manager=None):
        self.directory = os.path.abspath(os.path.expanduser(directory))
        self.max_items = max_items
        self.enable_rotation = enable_rotation
        self.stats_manager = stats_manager  # Optional StatisticsManager for smart rotation
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

    def _smart_select_for_removal(self, items: List[Dict], num_to_remove: int) -> List[Dict]:
        """
        Intelligently select wallpapers to remove, protecting important ones.
        Priority for removal (from highest to lowest):
        1. Banned wallpapers
        2. Unrated wallpapers with low views and old timestamp
        3. Lowest rated wallpapers
        Never removes: starred (rating > 0) or favorite wallpapers
        """
        if not self.stats_manager:
            # Fallback to simple old behavior if no stats manager
            return items[:num_to_remove]

        # Categorize wallpapers
        protected = []  # Starred or favorites
        banned = []
        low_priority = []  # Unrated, low views
        normal = []

        for item in items:
            path = item.get("path")
            if not path:
                continue

            # Check stats
            rating = self.stats_manager.get_rating(path)
            is_favorite = self.stats_manager.is_favorite(path)
            is_banned = self.stats_manager.is_banned(path)
            views = self.stats_manager.data.get("wallpapers", {}).get(path, {}).get("views", 0)

            # Categorize
            if rating > 0 or is_favorite:
                protected.append(item)
            elif is_banned:
                banned.append(item)
            elif rating == 0 and views < 3:
                low_priority.append((item, views, item.get("timestamp", 0)))
            else:
                normal.append((item, views, item.get("timestamp", 0)))

        # Build removal list
        to_remove = []

        # 1. Remove banned first
        to_remove.extend(banned[:num_to_remove])

        # 2. Remove low priority (sort by views then timestamp)
        if len(to_remove) < num_to_remove:
            low_priority.sort(key=lambda x: (x[1], x[2]))  # Sort by views, then timestamp
            remaining = num_to_remove - len(to_remove)
            to_remove.extend([item for item, _, _ in low_priority[:remaining]])

        # 3. Remove from normal pool if needed (oldest with lowest views)
        if len(to_remove) < num_to_remove:
            normal.sort(key=lambda x: (x[1], x[2]))  # Sort by views, then timestamp
            remaining = num_to_remove - len(to_remove)
            to_remove.extend([item for item, _, _ in normal[:remaining]])

        print(f"[CACHE] Smart rotation: protecting {len(protected)} starred/favorites, "
              f"removing {len([i for i in to_remove if i in banned])} banned, "
              f"{len([i for i in to_remove if i not in banned])} low-priority")

        return to_remove

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

            # Smart rotation: protect important wallpapers
            items = self._index["items"]
            if len(items) > self.max_items:
                excess = len(items) - self.max_items
                to_remove = self._smart_select_for_removal(items, excess)

                # Remove files from disk
                for item in to_remove:
                    try:
                        path = item.get("path")
                        if path and os.path.exists(path):
                            os.remove(path)
                            print(f"[CACHE] Removed: {os.path.basename(path)}")
                    except OSError as e:
                        print(f"[WARNING] Failed to remove {path}: {e}")

                # Remove from index
                to_remove_paths = {item.get("path") for item in to_remove}
                self._index["items"] = [item for item in items if item.get("path") not in to_remove_paths]

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
