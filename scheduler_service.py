import random
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional


def _parse_time(value: str) -> datetime.time:
    hour, minute = (int(part) for part in value.split(":", 1))
    return datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0).time()


class SchedulerService:
    def __init__(self, controller, settings: Dict):
        self.controller = controller
        self.settings = settings or {}
        self.enabled = bool(self.settings.get("enabled", False))
        self.interval_minutes = max(int(self.settings.get("interval_minutes", 30)), 1)
        self.jitter_minutes = max(int(self.settings.get("jitter_minutes", 0)), 0)
        self.initial_delay_minutes = max(int(self.settings.get("initial_delay_minutes", 0)), 0)
        self.days = {day.lower() for day in self.settings.get("days", []) if isinstance(day, str)}
        self.quiet_hours = [
            (
                _parse_time(str(window.get("start", "00:00"))),
                _parse_time(str(window.get("end", "00:00"))),
            )
            for window in self.settings.get("quiet_hours", [])
            if isinstance(window, dict) and window.get("start") and window.get("end")
        ]
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._paused = threading.Event()
        self._paused.clear()

    def start(self) -> None:
        if not self.enabled or self._thread:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="WallpaperScheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
        self._thread = None

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        if enabled:
            self.start()
        else:
            self.stop()

    def toggle(self) -> bool:
        self.set_enabled(not self.enabled)
        return self.enabled

    def _run(self) -> None:
        if self.initial_delay_minutes:
            if self._wait_minutes(self.initial_delay_minutes):
                return

        while not self._stop_event.is_set():
            if self._within_active_window(datetime.now()):
                try:
                    self.controller.change_wallpaper("scheduler")
                except Exception as exc:  # pragma: no cover
                    print(f"[Scheduler] Wallpaper update failed: {exc}")

            interval = self.interval_minutes
            if self.jitter_minutes:
                interval += random.randint(-self.jitter_minutes, self.jitter_minutes)
                interval = max(interval, 1)

            if self._wait_minutes(interval):
                break

    def _wait_minutes(self, minutes: int) -> bool:
        seconds = minutes * 60
        end_time = time.time() + seconds
        while time.time() < end_time:
            remaining = end_time - time.time()
            if self._stop_event.wait(timeout=min(remaining, 1)):
                return True
        return False

    def _within_active_window(self, now: datetime) -> bool:
        if self.days and now.strftime("%a").lower()[:3] not in self.days:
            return False

        current_time = now.time()
        for start, end in self.quiet_hours:
            if start <= end:
                if start <= current_time <= end:
                    return False
            else:  # wraps midnight
                if current_time >= start or current_time <= end:
                    return False
        return True

