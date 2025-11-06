"""
Statistics and Favorites Manager for WallpaperChanger
Tracks wallpaper usage, ratings, and favorites
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


class StatisticsManager:
    """Manages wallpaper usage statistics and user preferences"""

    def __init__(self, stats_file: str = "wallpaper_stats.json"):
        self.stats_file = Path(stats_file)
        self.data = self._load_data()

    def _load_data(self) -> Dict:
        """Load statistics data from file"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[ERROR] Failed to load statistics: {e}")
                return self._get_default_data()
        return self._get_default_data()

    def _get_default_data(self) -> Dict:
        """Get default data structure"""
        return {
            "wallpapers": {},  # path -> {views, last_viewed, rating, favorite, tags, banned}
            "history": [],  # [{timestamp, path, provider, action}]
            "daily_stats": {},  # date -> {changes, providers}
            "banned": [],  # List of banned wallpaper paths
            "preferences": {
                "total_changes": 0,
                "favorite_provider": None,
                "favorite_time": None
            }
        }

    def _save_data(self):
        """Save statistics data to file"""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ERROR] Failed to save statistics: {e}")

    def log_wallpaper_change(self, wallpaper_path: str, provider: str = "unknown",
                            action: str = "auto"):
        """Log a wallpaper change event"""
        timestamp = datetime.now().isoformat()
        date_key = datetime.now().strftime("%Y-%m-%d")

        # Add to history
        self.data["history"].append({
            "timestamp": timestamp,
            "path": wallpaper_path,
            "provider": provider,
            "action": action
        })

        # Keep only last 1000 entries
        if len(self.data["history"]) > 1000:
            self.data["history"] = self.data["history"][-1000:]

        # Update wallpaper stats
        if wallpaper_path not in self.data["wallpapers"]:
            self.data["wallpapers"][wallpaper_path] = {
                "views": 0,
                "last_viewed": timestamp,
                "rating": 0,
                "favorite": False,
                "tags": [],
                "provider": provider
            }

        self.data["wallpapers"][wallpaper_path]["views"] += 1
        self.data["wallpapers"][wallpaper_path]["last_viewed"] = timestamp

        # Update daily stats
        if date_key not in self.data["daily_stats"]:
            self.data["daily_stats"][date_key] = {
                "changes": 0,
                "providers": defaultdict(int)
            }

        self.data["daily_stats"][date_key]["changes"] += 1
        if date_key in self.data["daily_stats"]:
            providers = self.data["daily_stats"][date_key].get("providers", {})
            providers[provider] = providers.get(provider, 0) + 1
            self.data["daily_stats"][date_key]["providers"] = providers

        # Update total changes
        self.data["preferences"]["total_changes"] += 1

        self._save_data()

    def set_rating(self, wallpaper_path: str, rating: int):
        """Set rating for a wallpaper (1-5 stars)"""
        if wallpaper_path not in self.data["wallpapers"]:
            self.data["wallpapers"][wallpaper_path] = {
                "views": 0,
                "last_viewed": datetime.now().isoformat(),
                "rating": 0,
                "favorite": False,
                "tags": [],
                "provider": "unknown"
            }

        self.data["wallpapers"][wallpaper_path]["rating"] = max(0, min(5, rating))
        self._save_data()

    def get_rating(self, wallpaper_path: str) -> int:
        """Get rating for a wallpaper"""
        return self.data["wallpapers"].get(wallpaper_path, {}).get("rating", 0)

    def toggle_favorite(self, wallpaper_path: str) -> bool:
        """Toggle favorite status for a wallpaper"""
        if wallpaper_path not in self.data["wallpapers"]:
            self.data["wallpapers"][wallpaper_path] = {
                "views": 0,
                "last_viewed": datetime.now().isoformat(),
                "rating": 0,
                "favorite": False,
                "tags": [],
                "provider": "unknown"
            }

        current = self.data["wallpapers"][wallpaper_path]["favorite"]
        self.data["wallpapers"][wallpaper_path]["favorite"] = not current
        self._save_data()
        return not current

    def is_favorite(self, wallpaper_path: str) -> bool:
        """Check if wallpaper is marked as favorite"""
        return self.data["wallpapers"].get(wallpaper_path, {}).get("favorite", False)

    def get_favorites(self) -> List[str]:
        """Get list of favorite wallpaper paths"""
        return [path for path, data in self.data["wallpapers"].items()
                if data.get("favorite", False)]

    def get_top_rated(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get top rated wallpapers"""
        rated = [(path, data["rating"]) for path, data in self.data["wallpapers"].items()
                 if data.get("rating", 0) > 0]
        return sorted(rated, key=lambda x: x[1], reverse=True)[:limit]

    def get_most_viewed(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get most viewed wallpapers"""
        viewed = [(path, data["views"]) for path, data in self.data["wallpapers"].items()]
        return sorted(viewed, key=lambda x: x[1], reverse=True)[:limit]

    def get_daily_changes(self, days: int = 7) -> Dict[str, int]:
        """Get daily change counts for the last N days"""
        result = {}
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            result[date] = self.data["daily_stats"].get(date, {}).get("changes", 0)
        return result

    def get_provider_stats(self, days: int = 7) -> Dict[str, int]:
        """Get provider usage stats for the last N days"""
        provider_counts = defaultdict(int)
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            if date in self.data["daily_stats"]:
                providers = self.data["daily_stats"][date].get("providers", {})
                for provider, count in providers.items():
                    provider_counts[provider] += count
        return dict(provider_counts)

    def get_hourly_distribution(self) -> Dict[int, int]:
        """Get distribution of wallpaper changes by hour of day"""
        hourly = defaultdict(int)
        for entry in self.data["history"]:
            try:
                dt = datetime.fromisoformat(entry["timestamp"])
                hourly[dt.hour] += 1
            except:
                pass
        return dict(hourly)

    def get_total_changes(self) -> int:
        """Get total number of wallpaper changes"""
        return self.data["preferences"]["total_changes"]

    def get_recent_history(self, limit: int = 10) -> List[Dict]:
        """Get recent wallpaper change history"""
        return self.data["history"][-limit:][::-1]

    def add_tag(self, wallpaper_path: str, tag: str):
        """Add a tag to a wallpaper"""
        if wallpaper_path not in self.data["wallpapers"]:
            self.data["wallpapers"][wallpaper_path] = {
                "views": 0,
                "last_viewed": datetime.now().isoformat(),
                "rating": 0,
                "favorite": False,
                "tags": [],
                "provider": "unknown"
            }

        tags = self.data["wallpapers"][wallpaper_path].get("tags", [])
        if tag not in tags:
            tags.append(tag)
            self.data["wallpapers"][wallpaper_path]["tags"] = tags
            self._save_data()

    def remove_tag(self, wallpaper_path: str, tag: str):
        """Remove a tag from a wallpaper"""
        if wallpaper_path in self.data["wallpapers"]:
            tags = self.data["wallpapers"][wallpaper_path].get("tags", [])
            if tag in tags:
                tags.remove(tag)
                self.data["wallpapers"][wallpaper_path]["tags"] = tags
                self._save_data()

    def get_tags(self, wallpaper_path: str) -> List[str]:
        """Get tags for a wallpaper"""
        return self.data["wallpapers"].get(wallpaper_path, {}).get("tags", [])

    def get_all_tags(self) -> List[str]:
        """Get all unique tags across all wallpapers"""
        tags = set()
        for data in self.data["wallpapers"].values():
            tags.update(data.get("tags", []))
        return sorted(list(tags))

    def get_wallpapers_by_tag(self, tag: str) -> List[str]:
        """Get all wallpapers with a specific tag"""
        return [path for path, data in self.data["wallpapers"].items()
                if tag in data.get("tags", [])]

    def cleanup_missing_wallpapers(self, valid_paths: List[str]):
        """Remove statistics for wallpapers that no longer exist"""
        valid_set = set(valid_paths)
        to_remove = [path for path in self.data["wallpapers"].keys()
                     if path not in valid_set]

        for path in to_remove:
            del self.data["wallpapers"][path]

        if to_remove:
            self._save_data()
            print(f"[INFO] Cleaned up {len(to_remove)} missing wallpapers from statistics")

    def ban_wallpaper(self, wallpaper_path: str):
        """Ban a wallpaper from being used"""
        if "banned" not in self.data:
            self.data["banned"] = []

        if wallpaper_path not in self.data["banned"]:
            self.data["banned"].append(wallpaper_path)

            # Also mark in wallpaper data
            if wallpaper_path in self.data["wallpapers"]:
                self.data["wallpapers"][wallpaper_path]["banned"] = True

            self._save_data()
            print(f"[INFO] Banned wallpaper: {wallpaper_path}")

    def unban_wallpaper(self, wallpaper_path: str):
        """Unban a wallpaper"""
        if "banned" not in self.data:
            self.data["banned"] = []

        if wallpaper_path in self.data["banned"]:
            self.data["banned"].remove(wallpaper_path)

            # Also update wallpaper data
            if wallpaper_path in self.data["wallpapers"]:
                self.data["wallpapers"][wallpaper_path]["banned"] = False

            self._save_data()
            print(f"[INFO] Unbanned wallpaper: {wallpaper_path}")

    def is_banned(self, wallpaper_path: str) -> bool:
        """Check if a wallpaper is banned"""
        if "banned" not in self.data:
            self.data["banned"] = []
        return wallpaper_path in self.data["banned"]

    def get_banned_wallpapers(self) -> List[str]:
        """Get list of all banned wallpaper paths"""
        if "banned" not in self.data:
            self.data["banned"] = []
        return self.data["banned"].copy()

    def toggle_ban(self, wallpaper_path: str) -> bool:
        """Toggle ban status for a wallpaper. Returns True if now banned, False if unbanned"""
        if self.is_banned(wallpaper_path):
            self.unban_wallpaper(wallpaper_path)
            return False
        else:
            self.ban_wallpaper(wallpaper_path)
            return True
