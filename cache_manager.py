import json
import os
import random
import shutil
import threading
import time
from typing import Dict, List, Optional


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
            os.makedirs(self.directory, exist_ok=True)
            extension = os.path.splitext(source_path)[1] or ".jpg"
            cache_id = f"{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
            target_path = os.path.join(self.directory, f"{cache_id}{extension}")
            shutil.copy2(source_path, target_path)

            entry = dict(metadata)
            entry.update(
                {
                    "id": cache_id,
                    "path": target_path,
                    "timestamp": time.time(),
                }
            )
            self._index.setdefault("items", []).append(entry)
            self._index["items"] = self._index["items"][-self.max_items :]
            self._save()
            return target_path

    def get_random(self, preset: Optional[str] = None, monitor_label: Optional[str] = None) -> Optional[Dict]:
        with self._lock:
            items = list(self._index.get("items", []))

        if preset:
            items = [item for item in items if item.get("preset") == preset]
        if monitor_label and items:
            filtered = [item for item in items if item.get("monitor") == monitor_label]
            if filtered:
                items = filtered

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
