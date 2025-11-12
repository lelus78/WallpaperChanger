"""
Dynamic Wallpaper Rules Module

Manages time-based and weather-based wallpaper selection rules.
"""

import json
import os
from datetime import datetime, time as datetime_time
from typing import List, Dict, Optional, Tuple
import threading


class DynamicRule:
    """Represents a single dynamic wallpaper rule"""

    def __init__(self, rule_data: Dict):
        self.name = rule_data.get("name", "Unnamed Rule")
        self.enabled = rule_data.get("enabled", True)
        self.priority = rule_data.get("priority", 0)  # Higher = more important
        self.conditions = rule_data.get("conditions", {})
        self.actions = rule_data.get("actions", {})

    def matches(self, current_time: datetime, current_weather: Optional[str] = None) -> bool:
        """Check if this rule's conditions are met"""
        if not self.enabled:
            return False

        # Time-based conditions
        if "time_range" in self.conditions:
            time_range = self.conditions["time_range"]
            start_str, end_str = time_range.get("start"), time_range.get("end")

            if start_str and end_str:
                start_time = datetime.strptime(start_str, "%H:%M").time()
                end_time = datetime.strptime(end_str, "%H:%M").time()
                current = current_time.time()

                # Handle ranges that cross midnight
                if start_time <= end_time:
                    if not (start_time <= current < end_time):
                        return False
                else:
                    if not (current >= start_time or current < end_time):
                        return False

        # Day of week conditions
        if "days_of_week" in self.conditions:
            allowed_days = self.conditions["days_of_week"]  # 0=Monday, 6=Sunday
            if current_time.weekday() not in allowed_days:
                return False

        # Weather-based conditions
        if "weather" in self.conditions and current_weather:
            required_weather = self.conditions["weather"]
            if isinstance(required_weather, str):
                required_weather = [required_weather]
            if current_weather.lower() not in [w.lower() for w in required_weather]:
                return False

        # Season conditions
        if "season" in self.conditions:
            required_season = self.conditions["season"]
            current_season = self._get_season(current_time)
            if current_season != required_season:
                return False

        return True

    def _get_season(self, dt: datetime) -> str:
        """Determine season based on month (Northern Hemisphere)"""
        month = dt.month
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "autumn"

    def get_actions(self) -> Dict:
        """Get the actions to perform when this rule matches"""
        return self.actions

    def to_dict(self) -> Dict:
        """Convert rule to dictionary for serialization"""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "priority": self.priority,
            "conditions": self.conditions,
            "actions": self.actions,
        }


class DynamicRulesManager:
    """Manages dynamic wallpaper selection rules"""

    def __init__(self, config_file: str = "dynamic_rules.json"):
        self.config_file = config_file
        self.rules: List[DynamicRule] = []
        self._lock = threading.Lock()
        self._load_rules()

    def _load_rules(self):
        """Load rules from JSON file"""
        if not os.path.exists(self.config_file):
            self._create_default_rules()
            return

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.rules = [DynamicRule(rule_data) for rule_data in data.get("rules", [])]
        except Exception as e:
            print(f"[ERROR] Failed to load dynamic rules: {e}")
            self._create_default_rules()

    def _create_default_rules(self):
        """Create default example rules"""
        default_rules = [
            {
                "name": "Morning - Bright Wallpapers",
                "enabled": True,
                "priority": 10,
                "conditions": {
                    "time_range": {"start": "06:00", "end": "12:00"}
                },
                "actions": {
                    "preferred_colors": ["yellow", "orange", "white"],
                    "preferred_tags": ["sunrise", "morning", "bright"]
                }
            },
            {
                "name": "Evening - Warm Wallpapers",
                "enabled": True,
                "priority": 10,
                "conditions": {
                    "time_range": {"start": "17:00", "end": "21:00"}
                },
                "actions": {
                    "preferred_colors": ["orange", "red", "purple"],
                    "preferred_tags": ["sunset", "evening", "warm"]
                }
            },
            {
                "name": "Night - Dark Wallpapers",
                "enabled": True,
                "priority": 10,
                "conditions": {
                    "time_range": {"start": "21:00", "end": "06:00"}
                },
                "actions": {
                    "preferred_colors": ["dark", "blue", "purple"],
                    "preferred_tags": ["night", "stars", "moon", "dark"]
                }
            },
            {
                "name": "Rainy Days",
                "enabled": False,  # Disabled by default (requires weather API)
                "priority": 15,
                "conditions": {
                    "weather": ["rain", "drizzle", "thunderstorm"]
                },
                "actions": {
                    "preferred_tags": ["rain", "fog", "mist", "clouds"],
                    "preferred_colors": ["gray", "blue"]
                }
            },
        ]

        self.rules = [DynamicRule(rule_data) for rule_data in default_rules]
        self.save_rules()

    def save_rules(self):
        """Save rules to JSON file"""
        with self._lock:
            data = {
                "version": 1,
                "rules": [rule.to_dict() for rule in self.rules]
            }
            try:
                with open(self.config_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                print(f"[ERROR] Failed to save dynamic rules: {e}")

    def get_active_rules(self, current_weather: Optional[str] = None) -> List[DynamicRule]:
        """Get all rules that match current conditions"""
        with self._lock:
            current_time = datetime.now()
            matching_rules = [
                rule for rule in self.rules
                if rule.matches(current_time, current_weather)
            ]
            # Sort by priority (higher first)
            return sorted(matching_rules, key=lambda r: r.priority, reverse=True)

    def get_preferred_filters(self, current_weather: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Get combined preferred tags and colors from all active rules

        Returns:
            Dict with 'tags' and 'colors' lists
        """
        active_rules = self.get_active_rules(current_weather)

        preferred_tags = []
        preferred_colors = []

        for rule in active_rules:
            actions = rule.get_actions()
            if "preferred_tags" in actions:
                preferred_tags.extend(actions["preferred_tags"])
            if "preferred_colors" in actions:
                preferred_colors.extend(actions["preferred_colors"])

        # Remove duplicates while preserving order
        seen_tags = set()
        unique_tags = []
        for tag in preferred_tags:
            if tag not in seen_tags:
                seen_tags.add(tag)
                unique_tags.append(tag)

        seen_colors = set()
        unique_colors = []
        for color in preferred_colors:
            if color not in seen_colors:
                seen_colors.add(color)
                unique_colors.append(color)

        return {
            "tags": unique_tags,
            "colors": unique_colors
        }

    def add_rule(self, rule: DynamicRule):
        """Add a new rule"""
        with self._lock:
            self.rules.append(rule)
            self.save_rules()

    def remove_rule(self, rule_name: str):
        """Remove a rule by name"""
        with self._lock:
            self.rules = [r for r in self.rules if r.name != rule_name]
            self.save_rules()

    def toggle_rule(self, rule_name: str):
        """Toggle a rule's enabled status"""
        with self._lock:
            for rule in self.rules:
                if rule.name == rule_name:
                    rule.enabled = not rule.enabled
            self.save_rules()

    def get_all_rules(self) -> List[DynamicRule]:
        """Get all rules"""
        with self._lock:
            return list(self.rules)


# Testing
if __name__ == "__main__":
    manager = DynamicRulesManager()

    print("Current active rules:")
    active = manager.get_active_rules()
    for rule in active:
        print(f"  - {rule.name} (priority: {rule.priority})")

    print("\nPreferred filters:")
    filters = manager.get_preferred_filters()
    print(f"  Tags: {filters['tags']}")
    print(f"  Colors: {filters['colors']}")
