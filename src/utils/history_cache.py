"""
history_cache.py
────────────────
Persistent, disk-backed cache for game installation/processing history.
"""

import json
import logging
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Maximum number of history entries to keep
MAX_HISTORY_ENTRIES = 30

def _get_history_path() -> Path:
    """Return the path to the on-disk history cache JSON file."""
    data_dir = Path.home() / ".local" / "share" / "ACCELA"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "install_history.json"


class HistoryCache:
    """
    Disk-backed cache for installation history.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._history: List[dict] = []
        self._dirty = False
        self._load()

    def get_history(self) -> List[dict]:
        """Return the current history."""
        with self._lock:
            # Return a copy to avoid external mutation issues
            return list(self._history)

    def add_entry(self, entry: dict) -> None:
        """
        Add a new entry to the history and save asynchronously.
        Ensures the list doesn't exceed MAX_HISTORY_ENTRIES.
        """
        if "timestamp" not in entry:
            entry["timestamp"] = time.time()
            
        with self._lock:
            self._history.insert(0, entry)
            if len(self._history) > MAX_HISTORY_ENTRIES:
                self._history = self._history[:MAX_HISTORY_ENTRIES]
            self._dirty = True
            
        self.save_async()

    def save(self) -> None:
        """Write the in-memory cache to disk. Non-blocking; errors are logged."""
        with self._lock:
            if not self._dirty:
                return
            data_to_write = list(self._history)
            self._dirty = False

        try:
            cache_path = _get_history_path()
            tmp_path = cache_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data_to_write, f, indent=2)
            tmp_path.replace(cache_path)
            logger.debug(f"History cache saved ({len(data_to_write)} entries)")
        except Exception as e:
            logger.warning(f"Failed to save history cache: {e}")
            with self._lock:
                self._dirty = True

    def save_async(self) -> None:
        """Save cache to disk in a background daemon thread."""
        t = threading.Thread(target=self.save, daemon=True, name="HistoryCacheSave")
        t.start()

    def _load(self) -> None:
        """Load cache from disk on startup."""
        try:
            cache_path = _get_history_path()
            if not cache_path.exists():
                return

            with open(cache_path, "r", encoding="utf-8") as f:
                raw = json.load(f)

            if not isinstance(raw, list):
                logger.warning("History cache file has unexpected format; discarding")
                return

            with self._lock:
                # Ensure we only load up to MAX
                self._history = raw[:MAX_HISTORY_ENTRIES]

            logger.info(f"Loaded history cache: {len(self._history)} entries")
        except json.JSONDecodeError as e:
            logger.warning(f"History cache file is corrupt, discarding: {e}")
        except Exception as e:
            logger.warning(f"Failed to load history cache: {e}")


# Module-level singleton
_instance: Optional[HistoryCache] = None
_instance_lock = threading.Lock()

def get_history_cache() -> HistoryCache:
    """Return the application-wide HistoryCache singleton."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = HistoryCache()
    return _instance
