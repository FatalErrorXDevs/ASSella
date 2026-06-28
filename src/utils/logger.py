import logging
import os
import platform
import subprocess
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from utils.helpers import get_base_path

# Constants
APP_NAME = "accela"
MAX_PREVIOUS_LOGS = 3

logger = logging.getLogger(__name__)


class QtLogHandler(QObject, logging.Handler):
    """Custom logging handler that emits signals to Qt widgets."""

    new_record = pyqtSignal(str)
    flushOnClose = False

    def __init__(self):
        super().__init__()
        # Initialize QObject part of the mixin
        QObject.__init__(self)
        logging.Handler.__init__(self)

        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        self.setFormatter(formatter)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.new_record.emit(msg)
        except RuntimeError:
            # Qt object has been deleted
            pass

    def flush(self) -> None:
        # No-op to avoid issues with deleted Qt objects
        pass

class QtLogFormatter(logging.Formatter):
    """Custom formatter for GUI logs to keep it clean and minimal."""

    def format(self, record: logging.LogRecord) -> str:
        if record.levelno >= logging.WARNING:
            return f"[{record.levelname}] {record.getMessage()}"
        return record.getMessage()


# Global handler instance
qt_log_handler = QtLogHandler()
_current_log_name: Optional[str] = None
_log_dir = get_base_path() / "logs"


class LineRotatingFileHandler(logging.FileHandler):
    """
    Handler that rotates logs based on maximum line count.
    Keeps at most max_lines in the file, dropping older lines.
    """
    def __init__(self, filename, mode='a', encoding=None, delay=False, max_lines=10000):
        super().__init__(filename, mode, encoding, delay)
        self.max_lines = max_lines
        self._emit_count = 0

    def emit(self, record):
        super().emit(record)
        self.flush()
        self._emit_count += 1
        # Truncate every 20 log records to keep disk I/O low
        if self._emit_count >= 20:
            self._emit_count = 0
            try:
                self.rotate_by_lines()
            except Exception:
                pass

    def rotate_by_lines(self):
        if not os.path.exists(self.baseFilename):
            return
        try:
            with open(self.baseFilename, 'r', encoding=self.encoding or 'utf-8', errors='ignore') as f:
                lines = f.readlines()
            if len(lines) > self.max_lines:
                keep_lines = lines[-self.max_lines:]
                with open(self.baseFilename, 'w', encoding=self.encoding or 'utf-8') as f:
                    f.writelines(keep_lines)
        except Exception:
            pass

    def close(self):
        try:
            self.rotate_by_lines()
        except Exception:
            pass
        super().close()


class LogCategoryFilter(logging.Filter):
    def __init__(self, level_str="DEBUG", category_str="All Modules"):
        super().__init__()
        self.level = getattr(logging, level_str.upper(), logging.DEBUG)
        self.category = category_str

    def filter(self, record):
        # 1. Filter by level
        if record.levelno < self.level:
            return False

        # 2. Filter by category
        if self.category == "All Modules":
            return True
        elif self.category == "Only Steam Client & API":
            name = record.name.lower()
            return "steam" in name or "client" in name or "scheevo" in name
        elif self.category == "Only Downloads & Manifests":
            name = record.name.lower()
            return "download" in name or "manifest" in name or "task" in name or "job" in name
        elif self.category == "Only Database & Library":
            name = record.name.lower()
            return "db_manager" in name or "database" in name or "game_manager" in name or "library" in name

        return True


def update_log_filters():
    """Update active log filters from current settings."""
    try:
        from utils.settings import get_settings
        settings = get_settings()
        if not settings:
            return
        
        level_str = settings.value("log_filter_level", "DEBUG", type=str)
        category_str = settings.value("log_filter_category", "All Modules", type=str)
        
        # Find and update our filter
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            # Remove any existing LogCategoryFilters
            for filt in handler.filters[:]:
                if isinstance(filt, LogCategoryFilter):
                    handler.removeFilter(filt)
            # Add updated filter
            handler.addFilter(LogCategoryFilter(level_str, category_str))
            
            # Update the level of the handler
            level_num = getattr(logging, level_str.upper(), logging.DEBUG)
            handler.setLevel(level_num)
            
    except Exception as e:
        print(f"Error updating log filters: {e}", file=sys.stderr)


def _create_file_handler(log_path: Path) -> Optional[LineRotatingFileHandler]:
    """Attempt to create a line rotating file handler at the specified path."""
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    try:
        handler = LineRotatingFileHandler(
            log_path,
            mode="w",  # Start fresh for each session
            encoding="utf-8",
            max_lines=10000,
            delay=False,
        )
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(formatter)
        print(f"Log file created: {log_path}", file=sys.stderr)
        return handler
    except (PermissionError, OSError) as e:
        print(f"Error: Could not create log file at {log_path}: {e}", file=sys.stderr)
        return None


def setup_logging() -> logging.Logger:
    """Setup logging with timestamped log files."""
    # Clean up old logs on launch
    cleanup_old_logs()

    # Get the timestamped log path
    log_path = get_log_path()
    system_platform = platform.system()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    handlers: List[logging.Handler] = []

    # 1. File Handler (Main Path)
    file_handler = _create_file_handler(log_path)

    # 2. File Handler (Fallback to TEMP if main fails)
    if not file_handler:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = Path(os.environ.get("TEMP", os.getcwd()))
        fallback_path = temp_dir / f"{APP_NAME}_{timestamp}.log"
        print(f"Attempting fallback log: {fallback_path}", file=sys.stderr)
        file_handler = _create_file_handler(fallback_path)

    if file_handler:
        handlers.append(file_handler)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)

    # Qt Handler
    qt_log_handler.setLevel(logging.INFO)
    qt_log_handler.setFormatter(QtLogFormatter())
    handlers.append(qt_log_handler)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Reduce noise from third-party libraries when offline
    logging.getLogger("CMServerList").setLevel(logging.CRITICAL)

    # Clear existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add new handlers
    for handler in handlers:
        root_logger.addHandler(handler)

    # Apply log filters
    update_log_filters()

    # Re-acquire logger after config
    local_logger = logging.getLogger(__name__)

    # Log configuration details
    local_logger.info("Logging Initialized")
    local_logger.info("Platform: %s", system_platform)
    local_logger.info("Python: %s", sys.version)
    local_logger.info("Log file: %s", log_path)
    local_logger.info("File level: DEBUG")
    local_logger.info("Console level: INFO")
    local_logger.info("Qt GUI level: INFO")

    return local_logger


def open_log_directory() -> bool:
    """Open the log directory in the system file manager."""
    global _log_dir

    try:
        system = platform.system().lower()
        cmd = ["xdg-open"]  # Default for Linux/Unix

        if system == "windows":
            cmd = ["explorer"]

        subprocess.run(cmd + [str(_log_dir)], check=False)
        return True
    except Exception as e:
        local_logger = logging.getLogger(__name__)
        local_logger.error("Failed to open log directory: %s", e)
        return False


def get_log_path() -> Path:
    """Return path to a timestamped log file with counter if needed."""
    global _current_log_name, _log_dir

    try:
        _log_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Fallback to temp directory
        temp_dir = Path(os.environ.get("TEMP", os.getcwd())) / "logs" / APP_NAME
        temp_dir.mkdir(parents=True, exist_ok=True)
        _log_dir = temp_dir

    # Base name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{APP_NAME}_{timestamp}"

    # Find next available filename
    counter = 1
    while True:
        if counter == 1:
            log_name = f"{base_name}.log"
        else:
            log_name = f"{base_name}_{counter}.log"

        log_path = _log_dir / log_name
        if not log_path.exists():
            break
        counter += 1

    _current_log_name = log_name
    return log_path


def cleanup_old_logs() -> None:
    """Clean up old log files on startup."""
    global MAX_PREVIOUS_LOGS

    base_path = get_base_path()
    log_dir = base_path / "logs"

    if not log_dir.exists():
        return

    # Get all app specific .log files
    log_files = [f for f in log_dir.glob(f"{APP_NAME}*.log") if f.is_file()]

    if not log_files:
        return

    # Sort by modification time (newest first)
    log_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    # Keep only the N most recent files
    for old_log in log_files[MAX_PREVIOUS_LOGS:]:
        try:
            old_log.unlink()
            print(f"Removed old log file: {old_log.name}", file=sys.stderr)
        except OSError as e:
            print(f"Could not remove {old_log.name}: {e}", file=sys.stderr)
