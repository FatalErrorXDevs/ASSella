from typing import Any
from PyQt6.QtCore import QSettings

APP_NAME = "ACCELA"
ORG_NAME = "Tachibana Labs"


class RobustQSettings(QSettings):
    """Subclass of QSettings that robustly handles boolean values stored as string literals on Linux."""

    def value(self, key: str, defaultValue: Any = None, type: Any = None) -> Any:
        if type is bool or (type is None and isinstance(defaultValue, bool)):
            val = super().value(key, defaultValue)
            if val is None:
                return defaultValue
            if isinstance(val, str):
                return val.lower() in ("true", "1", "yes")
            return bool(val)

        if type is not None:
            return super().value(key, defaultValue, type)
        return super().value(key, defaultValue)


def get_settings() -> QSettings:
    """Get the application settings object."""
    return RobustQSettings(ORG_NAME, APP_NAME)
