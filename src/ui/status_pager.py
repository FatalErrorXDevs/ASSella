import logging
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSlot
from utils.logger import qt_log_handler
from utils.settings import get_settings

logger = logging.getLogger(__name__)


class StatusPagerWidget(QFrame):
    """A full-width, persistent pager-style status display with a retro LCD/calculator aesthetic.

    Displays smart, human-readable status updates by filtering the live log stream.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self.last_msg = "SYSTEM READY · DRAG AND DROP ZIP TO INSTALL"

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(15, 0, 15, 0)
        self.layout.setSpacing(0)

        self.label = QLabel(self.last_msg)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.label)

        self.update_style()

        # Connect to the live log stream handler
        qt_log_handler.new_record.connect(self.on_new_log)

    def set_status(self, message: str) -> None:
        """Programmatically set the status message on the pager."""
        self.last_msg = message.upper()
        self.label.setText(self.last_msg)

    @pyqtSlot(str)
    def on_new_log(self, raw_msg: str) -> None:
        """Filter log stream and show human-readable status changes."""
        msg = raw_msg.strip()
        if not msg:
            return

        msg_lower = msg.lower()

        # Clean/exclude traces and verbose library logs
        exclusions = [
            "debug",
            "traceback",
            "file \"",
            "line ",
            "connection pool",
            "urllib3",
            "http/1.1",
            "get_user_stats",
            "heartbeat",
        ]
        if any(exc in msg_lower for exc in exclusions):
            return

        # Check for interesting user-facing keywords
        interesting_keywords = [
            "download",
            "depot",
            "manifest",
            "fetch",
            "drm",
            "steamless",
            "achievement",
            "scheevo",
            "zip",
            "extract",
            "install",
            "finaliz",
            "success",
            "fail",
            "error",
            "warn",
            "start",
            "complet",
            "run",
            "pause",
            "resum",
            "stop",
            "block",
            "optimal",
        ]

        if any(kw in msg_lower for kw in interesting_keywords):
            # Clean up prefix like "[INFO] " or "[WARNING] "
            cleaned = msg
            if cleaned.startswith("[") and "]" in cleaned:
                idx = cleaned.find("]")
                cleaned = cleaned[idx + 1 :].strip()

            # Limit length to keep it single-line
            if len(cleaned) > 90:
                cleaned = cleaned[:87] + "..."

            self.set_status(cleaned)

    def update_style(self) -> None:
        """Apply theme color choices to the LCD container and text."""
        settings = get_settings()
        accent = settings.value("accent_color", "#C06C84")
        bg_color = settings.value("background_color", "#000000")

        # Register bundled typewriter/calculator fonts if not already registered
        from PyQt6.QtGui import QFontDatabase
        from utils.helpers import get_base_path
        
        trixie_path = get_base_path() / "src" / "res" / "TrixieCyrG-Plain Regular.otf"
        if trixie_path.exists():
            QFontDatabase.addApplicationFont(str(trixie_path))
            
        sonic_path = get_base_path() / "src" / "res" / "sonic" / "sonic-1-hud-font.otf"
        if sonic_path.exists():
            QFontDatabase.addApplicationFont(str(sonic_path))

        # Prioritize typewriter (TrixieCyrG-Plain) and calculator (Sonic 1 HUD Font)
        font_family = "TrixieCyrG-Plain, Sonic 1 HUD Font, Courier New, Consolas, monospace"

        # Retro LCD styling: dark recessed container, monospace text
        self.setStyleSheet(
            f"""
            StatusPagerWidget {{
                background-color: rgba(10, 10, 10, 220);
                border: 1px solid rgba(255, 255, 255, 12);
                border-radius: 6px;
                margin: 4px 15px;
            }}
            QLabel {{
                color: {accent};
                font-family: {font_family};
                font-size: 12px;
                font-weight: bold;
                border: none;
                background: transparent;
            }}
        """
        )
