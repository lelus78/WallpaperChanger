import json
import os
import random
import shutil
import threading
import time
from typing import Dict, List, Optional, Tuple
from color_analyzer import ColorAnalyzer
from duplicate_detector import DuplicateDetector


class CacheManager:
    def __init__(self, directory: str, max_items: int = 50, enable_rotation: bool = True, stats_manager=None, enable_duplicate_detection: bool = True):
        self.directory = os.path.abspath(os.path.expanduser(directory))
        self.max_items = max_items
        self.enable_rotation = enable_rotation
        self.stats_manager = stats_manager  # Optional StatisticsManager for smart rotation
        self.enable_duplicate_detection = enable_duplicate_detection
        self.duplicate_detector = DuplicateDetector() if enable_duplicate_detection else None
        self.index_path = os.path.join(self.directory, "index.json")
        self._index_mtime: Optional[float] = None
        self._lock = threading.Lock()
        self._index: Dict[str, List[Dict]] = {"version": 1, "items": []}
        self._load()

    def _get_index_mtime(self) -> Optional[float]:
        """Return last modification timestamp of the index file."""
        if os.path.exists(self.index_path):
            try:
                return os.path.getmtime(self.index_path)
            except OSError:
                return None
        return None

    def _refresh_index_if_changed(self) -> None:
        """Reload the cache index if another process updated it."""
        current_mtime = self._get_index_mtime()
        if current_mtime is None:
            return
        if self._index_mtime is not None and current_mtime <= self._index_mtime:
            return

        with self._lock:
            current_mtime = self._get_index_mtime()
            if current_mtime is None:
                return
            if self._index_mtime is not None and current_mtime <= self._index_mtime:
                return
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
        self._index_mtime = self._get_index_mtime()

    def _save(self) -> None:
        tmp_path = f"{self.index_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(self._index, handle, indent=2)
        os.replace(tmp_path, self.index_path)
        self._index_mtime = self._get_index_mtime()

    def _smart_select_for_removal(self, items: List[Dict], num_to_remove: int, exclude_recent_id: Optional[str] = None) -> List[Dict]:
        """
        Intelligently select wallpapers to remove, protecting important ones.
        Priority for removal (from highest to lowest):
        1. Banned wallpapers
        2. Unrated wallpapers with low views and old timestamp
        3. Lowest rated wallpapers
        Never removes: starred (rating > 0) or favorite wallpapers, or the most recently added item

        Args:
            items: List of cache items
            num_to_remove: Number of items to remove
            exclude_recent_id: Optional ID of recently added item to protect from removal
        """
        if not self.stats_manager:
            # Fallback to simple old behavior if no stats manager
            # But still protect the recently added item
            candidates = [item for item in items if item.get("id") != exclude_recent_id]
            return candidates[:num_to_remove]

        # Categorize wallpapers
        protected = []  # Starred or favorites or recently added
        banned = []
        low_priority = []  # Unrated, low views
        normal = []

        for item in items:
            path = item.get("path")
            if not path:
                continue

            # Protect recently added item from being removed in the same operation
            if exclude_recent_id and item.get("id") == exclude_recent_id:
                protected.append(item)
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
            # Check for duplicates using unique_id (preferred) or source_info (fallback)
            # BUT: if monitor_index is specified, only match if it's the same monitor
            unique_id = metadata.get("unique_id")
            source_info = metadata.get("source_info")
            monitor_index = metadata.get("monitor_index")

            for item in self._index.get("items", []):
                # Skip if this is a different monitor - each monitor should have its own wallpaper
                if monitor_index is not None and item.get("monitor_index") != monitor_index:
                    continue

                # Check unique_id first (more reliable for same content from different sources)
                if unique_id and item.get("unique_id") == unique_id:
                    cached_path = item.get("path")
                    # Verify file still exists before returning it
                    if cached_path and os.path.exists(cached_path):
                        print(f"[CACHE] Duplicate detected (unique_id), reusing: {os.path.basename(cached_path)}")
                        return cached_path
                    else:
                        print(f"[CACHE] Duplicate found but file missing, will re-download")
                        continue
                # Fallback to source_info for backwards compatibility
                if source_info and item.get("source_info") == source_info:
                    cached_path = item.get("path")
                    # Verify file still exists before returning it
                    if cached_path and os.path.exists(cached_path):
                        print(f"[CACHE] Duplicate detected (source_info), reusing: {os.path.basename(cached_path)}")
                        return cached_path
                    else:
                        print(f"[CACHE] Duplicate found but file missing, will re-download")
                        continue

            # Check for perceptual duplicates (similar images)
            # Only check duplicates for the same monitor to prevent cross-monitor deduplication
            if self.duplicate_detector:
                existing_hashes = {item.get('path'): item.get('perceptual_hash')
                                 for item in self._index.get("items", [])
                                 if item.get('perceptual_hash') and (
                                     monitor_index is None or item.get("monitor_index") == monitor_index
                                 )}

                if existing_hashes:
                    duplicate_result = self.duplicate_detector.is_duplicate(
                        source_path,
                        existing_hashes,
                        threshold=DuplicateDetector.VERY_SIMILAR
                    )
                    if duplicate_result:
                        dup_path, distance = duplicate_result
                        # Verify file still exists before returning it
                        if os.path.exists(dup_path):
                            similarity = self.duplicate_detector.get_similarity_description(distance)
                            print(f"[CACHE] {similarity} image detected (distance={distance}), reusing: {os.path.basename(dup_path)}")
                            return dup_path
                        else:
                            print(f"[CACHE] Similar image found but file missing, will download new")

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

            # Compute perceptual hash for duplicate detection
            perceptual_hash = None
            if self.duplicate_detector:
                perceptual_hash = self.duplicate_detector.compute_hash(target_path)

            entry = dict(metadata)
            entry.update(
                {
                    "id": cache_id,
                    "path": target_path,
                    "timestamp": time.time(),
                    "color_categories": color_categories,
                    "primary_color": primary_color,
                    "perceptual_hash": perceptual_hash,
                }
            )
            self._index.setdefault("items", []).append(entry)

            # Smart rotation: protect important wallpapers
            items = self._index["items"]
            if len(items) > self.max_items:
                excess = len(items) - self.max_items
                # Protect the newly added item from being immediately removed
                to_remove = self._smart_select_for_removal(items, excess, exclude_recent_id=cache_id)

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
        self._refresh_index_if_changed()
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
        self._refresh_index_if_changed()
        with self._lock:
            return bool(self._index.get("items"))

    def list_entries(self) -> List[Dict]:
        """Return list of cached entries, most recent first"""
        self._refresh_index_if_changed()
        with self._lock:
            items = self._index.get("items", [])
            return list(reversed(items))

    def get_all_colors(self) -> List[str]:
        """Get all unique color categories from cached wallpapers"""
        self._refresh_index_if_changed()
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
        self._refresh_index_if_changed()
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
        self._refresh_index_if_changed()
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
