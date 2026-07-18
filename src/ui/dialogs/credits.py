import logging
import urllib.request
import threading
import re

from PyQt6.QtWidgets import (
    QDialog,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QWidget,
    QFrame,
)
from PyQt6.QtCore import Qt, QMetaObject, Q_ARG, pyqtSlot

from utils.settings import get_settings
from utils.version import app_version

logger = logging.getLogger(__name__)


class CreditsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Credits & Updates")
        self.setMinimumWidth(430)
        self.setMinimumHeight(440)
        self.resize(430, 440)
        self.settings = get_settings()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(12)
        self.main_window = parent
        self.accent_color = self.settings.value("accent_color", "#C06C84")

        logger.debug("Opening CreditsDialog.")

        # Global stylesheet matching rest of settings app
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: #1a1a1a;
            }}
            QGroupBox {{
                font-weight: bold;
                border: 1px solid #333333;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                color: {self.accent_color};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 3px;
            }}
            QLabel {{
                color: #e0e0e0;
            }}
            QPushButton {{
                background-color: #2b2b2b;
                border: 1px solid #444444;
                border-radius: 4px;
                color: #ffffff;
                padding: 6px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #3b3b3b;
                border-color: {self.accent_color};
            }}
            QPushButton:disabled {{
                background-color: #1b1b1b;
                color: #666666;
                border-color: #222222;
            }}
            """
        )

        # 1. Header Section
        self._create_header()

        # 2. Content Section
        self._create_credits_content()

        # 3. Update Section
        self._create_update_section()

        # 4. Close button row
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        self.main_layout.addWidget(close_btn)

    def _create_header(self):
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        # App title and version
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        title_label = QLabel("ASSELA")
        title_label.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {self.accent_color}; letter-spacing: 2px;"
        )

        version_label = QLabel(f"Version {app_version}")
        version_label.setStyleSheet("font-size: 11px; color: #888888;")

        text_layout.addWidget(title_label)
        text_layout.addWidget(version_label)

        header_layout.addLayout(text_layout)
        header_layout.addStretch()

        self.main_layout.addWidget(header_widget)

        # Divider line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #333333; max-height: 1px; border: none;")
        self.main_layout.addWidget(line)

    def _create_credits_content(self):
        # Developer Section
        dev_group = QGroupBox("Core Development")
        dev_layout = QVBoxLayout(dev_group)
        dev_layout.setContentsMargins(12, 12, 12, 12)

        dev_label = QLabel("Developed by:  bakabakabaka")
        dev_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #e0e0e0;")
        dev_layout.addWidget(dev_label)
        self.main_layout.addWidget(dev_group)

        # Third Party Section
        third_party_group = QGroupBox("Third-Party Tools & Integration")
        third_party_layout = QVBoxLayout(third_party_group)
        third_party_layout.setContentsMargins(12, 12, 12, 12)
        third_party_layout.setSpacing(6)

        items = [
            ("GreenLuma", "Steam integration & offline helper"),
            ("SLSsteam", "Steam API interface wrapper"),
            ("Steamless", "DRM remover & unpacker (by Morrenus for AIO)"),
            ("DepotDownloaderMod", "High-speed manifest downloading"),
            ("SLScheevo", "Steam achievements unlocker & manager"),
            ("GogoVang", "Steam Workshop downloader extension"),
        ]

        for title, desc in items:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)

            t_lbl = QLabel(f"• {title}")
            t_lbl.setStyleSheet("font-weight: bold; color: #d0d0d0; min-width: 140px;")

            d_lbl = QLabel(desc)
            d_lbl.setStyleSheet("color: #888888; font-size: 11px;")

            row_layout.addWidget(t_lbl)
            row_layout.addWidget(d_lbl)
            row_layout.addStretch()
            third_party_layout.addWidget(row)

        self.main_layout.addWidget(third_party_group)

    def _create_update_section(self):
        self.update_group = QGroupBox("Application Updates")
        update_layout = QHBoxLayout(self.update_group)
        update_layout.setContentsMargins(12, 12, 12, 12)
        update_layout.setSpacing(10)

        # Status text label
        self.status_label = QLabel("Click 'Check' to look for updates.")
        self.status_label.setStyleSheet("font-size: 12px; color: #aaaaaa;")
        update_layout.addWidget(self.status_label, 1)

        # Check button
        self.check_btn = QPushButton("Check")
        self.check_btn.clicked.connect(self.check_updates)
        update_layout.addWidget(self.check_btn)

        self.main_layout.addWidget(self.update_group)

    def check_updates(self):
        self.check_btn.setEnabled(False)
        self.status_label.setText("Checking for updates...")
        self.status_label.setStyleSheet("color: #aaaaaa; font-size: 12px;")

        def _extract_semver(raw: str) -> str:
            if "+ASSella-" in raw:
                return raw.split("+ASSella-", 1)[1].strip()
            return raw.strip()

        def _parse_version(v_str: str) -> tuple:
            v_str = v_str.lstrip("v").strip()
            parts = v_str.split("-")
            main_part = parts[0]
            main_numbers = []
            for num in main_part.split("."):
                try:
                    main_numbers.append(int(num))
                except ValueError:
                    main_numbers.append(0)

            while len(main_numbers) < 3:
                main_numbers.append(0)

            pre_release_val = 0
            pre_release_num = 0

            if len(parts) > 1:
                pre_tag = parts[1].lower()
                pre_release_val = -1
                match = re.search(r"\d+$", pre_tag)
                if match:
                    try:
                        pre_release_num = int(match.group(0))
                    except ValueError:
                        pre_release_num = 0

            return tuple(main_numbers) + (pre_release_val, pre_release_num)

        def _check_sync():
            try:
                local_clean = _extract_semver(app_version)
                branch = (
                    "beta"
                    if any(x in local_clean.lower() for x in ("beta", "rc"))
                    else "main"
                )
                url = f"https://raw.githubusercontent.com/niwia/ASSella/{branch}/src/res/version"

                req = urllib.request.Request(
                    url, headers={"User-Agent": "ASSella-Updater"}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    remote_raw = response.read().decode("utf-8").strip()
                    remote_clean = _extract_semver(remote_raw)

                    if remote_clean:
                        if _parse_version(remote_clean) > _parse_version(
                            local_clean
                        ):
                            QMetaObject.invokeMethod(
                                self,
                                "_on_check_available",
                                Qt.ConnectionType.QueuedConnection,
                                Q_ARG(str, remote_clean),
                            )
                        else:
                            QMetaObject.invokeMethod(
                                self,
                                "_on_check_up_to_date",
                                Qt.ConnectionType.QueuedConnection,
                            )
            except Exception as e:
                logger.warning(f"Credits check updates failed: {e}")
                QMetaObject.invokeMethod(
                    self,
                    "_on_check_failed",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, str(e)),
                )

        t = threading.Thread(target=_check_sync, daemon=True)
        t.start()

    @pyqtSlot(str)
    def _on_check_available(self, remote_version: str) -> None:
        self.status_label.setText(f"New update available: v{remote_version}")
        self.status_label.setStyleSheet(
            "color: #E05A47; font-weight: bold; font-size: 12px;"
        )

        self.check_btn.setText("Update")
        self.check_btn.setEnabled(True)

        try:
            self.check_btn.clicked.disconnect()
        except TypeError:
            pass
        self.check_btn.clicked.connect(self.trigger_self_update)

    @pyqtSlot()
    def _on_check_up_to_date(self) -> None:
        self.status_label.setText("ASSella is up to date!")
        self.status_label.setStyleSheet(
            "color: #2ECC71; font-weight: bold; font-size: 12px;"
        )
        self.check_btn.setText("Check")
        self.check_btn.setEnabled(True)

    @pyqtSlot(str)
    def _on_check_failed(self, error: str) -> None:
        self.status_label.setText("Failed to check for updates.")
        self.status_label.setStyleSheet("color: #E74C3C; font-size: 12px;")
        self.check_btn.setText("Retry")
        self.check_btn.setEnabled(True)

    def trigger_self_update(self) -> None:
        self.reject()
        if self.main_window and hasattr(self.main_window, "run_self_update"):
            self.main_window.run_self_update()
