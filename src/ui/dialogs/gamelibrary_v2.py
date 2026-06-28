import os
import platform
import logging
from pathlib import Path

from PyQt6.QtCore import Qt, QSize, QRect, QPropertyAnimation, pyqtProperty, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QIcon, QPixmap, QPainter, QIntValidator, QPalette
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QLineEdit,
    QComboBox,
    QMessageBox,
    QWidget,
    QFrame,
    QStackedWidget,
    QStylePainter,
    QStyleOptionComboBox,
    QStyle,
)

from utils.helpers import get_base_path
from utils.settings import get_settings
from utils.update_status_cache import get_update_cache
from utils.yaml_config_manager import (
    get_user_config_path,
    add_fake_app_id,
    remove_fake_app_id,
    get_fake_appid,
    is_slssteam_config_management_enabled,
)
from utils.image_fetcher import ImageFetcher

logger = logging.getLogger(__name__)


class SwitchToggle(QWidget):
    stateChanged = pyqtSignal(bool)

    def __init__(self, parent=None, active_color="#4CAF50", bg_color="#33333C", circle_color="#FFFFFF"):
        super().__init__(parent)
        self.setFixedSize(40, 18)
        self._checked = False
        self._active_color = QColor(active_color)
        self._bg_color = QColor(bg_color)
        self._circle_color = QColor(circle_color)
        self._circle_pos = 2
        self._animation = QPropertyAnimation(self, b"circle_pos", self)
        self._animation.setDuration(120)

    @pyqtProperty(int)
    def circle_pos(self):
        return self._circle_pos

    @circle_pos.setter
    def circle_pos(self, pos):
        self._circle_pos = pos
        self.update()

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        if self._checked != checked:
            self._checked = checked
            target = 24 if checked else 2
            self._animation.setEndValue(target)
            self._animation.start()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self.setChecked(not self._checked)
            self.stateChanged.emit(self._checked)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background
        painter.setPen(Qt.PenStyle.NoPen)
        if not self.isEnabled():
            painter.setBrush(QColor("#222225"))
        elif self._checked:
            painter.setBrush(self._active_color)
        else:
            painter.setBrush(self._bg_color)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 9, 9)
        
        # Draw circle
        if not self.isEnabled():
            painter.setBrush(QColor("#555558"))
        else:
            painter.setBrush(self._circle_color)
        painter.drawEllipse(self._circle_pos, 2, 14, 14)


class CenteredComboBox(QComboBox):
    def paintEvent(self, event):
        painter = QStylePainter(self)
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        
        # Draw the combobox frame and arrow
        painter.drawComplexControl(QStyle.ComplexControl.CC_ComboBox, opt)
        
        # Get the edit field rectangle
        rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_ComboBox,
            opt,
            QStyle.SubControl.SC_ComboBoxEditField,
            self
        )
        
        # Draw the text centered
        painter.drawItemText(
            rect,
            Qt.AlignmentFlag.AlignCenter,
            self.palette(),
            self.isEnabled(),
            self.currentText(),
            QPalette.ColorRole.Text
        )


class HeaderWidget(QWidget):
    def __init__(self, parent_dialog, parent=None):
        super().__init__(parent)
        self.bg_label = QLabel(self)
        self.overlay = QWidget(self)
        self.original_pixmap = None
        
        # Resolve parent background color dynamically to blend gradient
        bg_hex = getattr(parent_dialog, "background_color", "#1E1E24")
        if bg_hex.startswith("#"):
            r = int(bg_hex[1:3], 16)
            g = int(bg_hex[3:5], 16)
            b = int(bg_hex[5:7], 16)
        else:
            r, g, b = 30, 30, 36
            
        self.setStyleSheet("background-color: #121214; border-radius: 6px;")
        self.bg_label.setStyleSheet("border-radius: 6px;")
        self.overlay.setStyleSheet(
            f"border-radius: 6px; "
            f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            f"stop:0.0 rgba({r}, {g}, {b}, 255), "
            f"stop:0.3 rgba({r}, {g}, {b}, 220), "
            f"stop:0.7 rgba({r}, {g}, {b}, 100), "
            f"stop:1.0 rgba({r}, {g}, {b}, 20));"
        )
        
    def set_header_pixmap(self, pixmap):
        self.original_pixmap = pixmap
        self.update_pixmap()

    def update_pixmap(self):
        if self.original_pixmap and not self.original_pixmap.isNull():
            scaled = self.original_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            self.bg_label.setPixmap(scaled)
        else:
            self.bg_label.setPixmap(QPixmap())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.bg_label.setGeometry(0, 0, self.width(), self.height())
        self.overlay.setGeometry(0, 0, self.width(), self.height())
        self.update_pixmap()


class GameDetailsDialogV2(QDialog):
    def __init__(self, parent, game_data):
        super().__init__(parent)
        self.parent_window = parent
        self.game_data = game_data
        self.appid = str(game_data.get("appid", "0"))
        self.settings = get_settings()
        self._active_fetchers = {}

        self.accent_color = getattr(parent, "accent_color", "#C06C84")
        self.background_color = getattr(parent, "background_color", "#1E1E24")

        self.setWindowTitle("Game Details")
        
        # Make the dialog resizable with scaling elements, starting a bit wider and taller
        self.setMinimumSize(600, 420)
        self.resize(720, 500)
        self.setModal(True)

        self._apply_theme_stylesheet()
        self._setup_ui()

    def _apply_theme_stylesheet(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.background_color};
            }}
            QFrame {{
                border: none;
                background: transparent;
            }}
            QLabel {{
                color: #e2e2e9;
                font-size: 11px;
                border: none;
                background: transparent;
            }}
            QPushButton {{
                background-color: transparent;
                color: #e2e2e9;
                border: 1px solid #2d2d34;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: #242428;
                border-color: {self.accent_color};
            }}
            QLineEdit {{
                background-color: #151518;
                color: #ffffff;
                border: 1px solid #2d2d34;
                border-radius: 4px;
                padding: 3px 6px;
                font-size: 11px;
            }}
            QLineEdit:disabled {{
                background-color: #111113;
                color: #555558;
                border-color: #1a1a1e;
            }}
            QLineEdit:focus {{
                border-color: {self.accent_color};
            }}
            QComboBox {{
                background-color: transparent;
                color: #e2e2e9;
                border: 1px solid #2d2d34;
                border-radius: 4px;
                padding: 3px 6px;
                font-size: 11px;
                height: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #1a1a1f;
                color: #e2e2e9;
                border: 1px solid #2d2d34;
                selection-background-color: {self.accent_color};
                font-size: 11px;
            }}
            QCheckBox {{
                color: #e2e2e9;
                font-size: 11px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border: 1px solid #282830;
                border-radius: 3px;
                background-color: #18181b;
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.accent_color};
                border-color: {self.accent_color};
            }}
            
            /* Specific Card Styling */
            QFrame#card1, QFrame#card2, QFrame#card3, QFrame#card4, QFrame#uninstall_card,
            QFrame#drm_card, QFrame#gb_card, QFrame#depot_card, QFrame#fix_card, QFrame#log_card {{
                background-color: #151518;
                border: 1px solid #242428;
                border-radius: 6px;
            }}
        """)

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Left Sidebar Navigation (Centered Text ASCII Buttons)
        sidebar = QFrame()
        sidebar.setStyleSheet("background-color: #151518; border-right: 1px solid #242428;")
        sidebar.setFixedWidth(85)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(4, 15, 4, 15)
        sidebar_layout.setSpacing(8)

        self.nav_buttons = []
        self.pages_info = [
            ("Overview", 0),
            ("Uninstall", 1),
            ("Tools", 2)
        ]

        for name, index in self.pages_info:
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setFlat(True)
            btn.setFixedWidth(77)
            btn.setFixedHeight(30)
            btn.clicked.connect(lambda checked, idx=index: self._switch_page(idx))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sidebar_layout.addStretch()
        main_layout.addWidget(sidebar)

        # 2. Right Content Panel
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(8)

        # Create Persistent Header Widget
        self.header_widget = HeaderWidget(self)
        self.header_widget.setFixedHeight(90)
        
        # Header Content Layout (Overlay Text)
        header_content = QVBoxLayout(self.header_widget)
        header_content.setContentsMargins(12, 10, 12, 10)
        header_content.setSpacing(2)

        self.name_lbl = QLabel(self.game_data.get("game_name", "Unknown"))
        self.name_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF; background: transparent; border: none;")
        self.name_lbl.setWordWrap(True)
        header_content.addWidget(self.name_lbl)

        self.appid_lbl = QLabel(f"App ID: {self.appid}")
        self.appid_lbl.setStyleSheet("color: #a0a0ab; font-size: 10px; background: transparent; border: none;")
        header_content.addWidget(self.appid_lbl)
        header_content.addStretch()

        # Load/Fetch Background Image for Persistent Header
        cached_image = self.parent_window._image_cache.get(self.appid)
        if cached_image:
            pixmap = QPixmap()
            pixmap.loadFromData(cached_image)
            if not pixmap.isNull():
                self.header_widget.set_header_pixmap(pixmap)
        else:
            if self.appid not in ("0", "N/A", "unknown"):
                if ImageFetcher:
                    url = ImageFetcher.get_header_image_url(self.appid)
                    fetcher = ImageFetcher(url)
                    fetcher.setProperty("app_id", self.appid)
                    
                    def _on_img_ready(data):
                        if data:
                            px = QPixmap()
                            px.loadFromData(data)
                            if not px.isNull():
                                self.header_widget.set_header_pixmap(px)
                    
                    fetcher.finished.connect(_on_img_ready)
                    fetcher.start()
                    self._active_fetchers[f"details_{self.appid}"] = fetcher
                    fetcher.finished.connect(lambda _, aid=self.appid: self._cleanup_fetcher(f"details_{aid}"))

        right_layout.addWidget(self.header_widget)

        # Stacked Widget (for different tabs)
        self.stacked_widget = QStackedWidget()
        
        # Create tabs
        self._init_overview_tab()
        self._init_uninstall_tab()
        self._init_tools_tab()

        right_layout.addWidget(self.stacked_widget)

        # Footer Actions (Just a Close Button)
        footer_layout = QHBoxLayout()
        self.close_btn = QPushButton("✕ Close")
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #18181b;
                border: 1px solid #282830;
                font-weight: bold;
                padding: 6px 16px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: #242428;
                border-color: {self.accent_color};
            }}
        """)
        self.close_btn.clicked.connect(self.accept)
        footer_layout.addWidget(self.close_btn, 1)
        right_layout.addLayout(footer_layout)

        main_layout.addWidget(right_container, 1)
        self._switch_page(0)

    def _switch_page(self, index):
        self.stacked_widget.setCurrentIndex(index)
        for idx, btn in enumerate(self.nav_buttons):
            btn.setChecked(idx == index)
            name = self.pages_info[idx][0]
            if idx == index:
                btn.setText(f"[ {name} ]")
                btn.setStyleSheet(f"background: transparent; color: {self.accent_color}; font-size: 11px; font-weight: bold; border: none;")
            else:
                btn.setText(name)
                btn.setStyleSheet("background: transparent; color: #8a8a93; font-size: 11px; font-weight: bold; border: none;")

    # ----------------------------------------------------
    # Overview Tab (Compact)
    # ----------------------------------------------------
    def _init_overview_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # --- 2. Compact Grid Layout ---
        grid_layout = QGridLayout()
        grid_layout.setSpacing(8)

        # Card 1: Stats Info
        card1 = QFrame()
        card1.setObjectName("card1")
        c1_layout = QVBoxLayout(card1)
        c1_layout.setContentsMargins(10, 10, 10, 10)
        c1_layout.setSpacing(5)

        c1_layout.addStretch(1)

        # Size
        size_layout = QHBoxLayout()
        size_lbl = QLabel("Size:")
        size_lbl.setStyleSheet("color: #8a8a93; font-weight: bold; font-size: 11px;")
        size_val = QLabel(self.parent_window._format_size(self.game_data.get("size_on_disk", 0)))
        size_val.setStyleSheet("color: #ffffff; font-size: 11px;")
        size_layout.addWidget(size_lbl)
        size_layout.addStretch()
        size_layout.addWidget(size_val)
        c1_layout.addLayout(size_layout)

        c1_layout.addSpacing(10)

        # Path Row (Only a Browse button)
        path_layout = QHBoxLayout()
        path_lbl = QLabel("Installation Path:")
        path_lbl.setStyleSheet("color: #8a8a93; font-weight: bold; font-size: 11px;")
        browse_btn = QPushButton("Browse")
        browse_btn.setFixedSize(70, 24)
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: 11px;
                padding: 2px 8px;
                background-color: #1c1c21;
            }}
            QPushButton:hover {{
                border-color: {self.accent_color};
            }}
        """)
        browse_btn.clicked.connect(
            lambda: self.parent_window._open_folder(self.game_data.get("install_path"))
        )
        path_layout.addWidget(path_lbl)
        path_layout.addStretch()
        path_layout.addWidget(browse_btn)
        c1_layout.addLayout(path_layout)

        c1_layout.addSpacing(10)

        # Manifest Age
        age_layout = QHBoxLayout()
        age_lbl = QLabel("Manifest Age:")
        age_lbl.setStyleSheet("color: #8a8a93; font-weight: bold; font-size: 11px;")
        manifest_age_value = self._get_manifest_age()
        age_val = QLabel(manifest_age_value)
        age_val.setStyleSheet("color: #ffffff; font-size: 11px;")
        age_layout.addWidget(age_lbl)
        age_layout.addStretch()
        age_layout.addWidget(age_val)
        c1_layout.addLayout(age_layout)

        c1_layout.addSpacing(10)

        # Last Checked
        check_layout = QHBoxLayout()
        check_lbl = QLabel("Last Checked:")
        check_lbl.setStyleSheet("color: #8a8a93; font-weight: bold; font-size: 11px;")
        last_check_value = self._get_last_checked()
        check_val = QLabel(last_check_value)
        check_val.setStyleSheet("color: #ffffff; font-size: 11px;")
        check_layout.addWidget(check_lbl)
        check_layout.addStretch()
        check_val.setAlignment(Qt.AlignmentFlag.AlignRight)
        check_layout.addWidget(check_val)
        c1_layout.addLayout(check_layout)

        c1_layout.addStretch(1)

        grid_layout.addWidget(card1, 0, 0)

        # Card 2: Update Actions
        card2 = QFrame()
        card2.setObjectName("card2")
        c2_layout = QVBoxLayout(card2)
        c2_layout.setContentsMargins(10, 10, 10, 10)
        c2_layout.setSpacing(5)

        c2_layout.addStretch(1)

        # Status badge pill
        self.status_badge = QLabel()
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_badge.setFixedHeight(22)
        c2_layout.addWidget(self.status_badge)

        c2_layout.addSpacing(8)

        # Rollback Combo using CenteredComboBox
        self.rollback_combo = CenteredComboBox()
        self.rollback_combo.addItem("Latest Build", None)
        
        manifests_dir = get_base_path() / "hubcap_manifests"
        backups = sorted(manifests_dir.glob(f"accela_fetch_{self.appid}_*.zip"), reverse=True)
        for b in backups:
            try:
                parts = b.stem.split("_")
                ts1, ts2 = parts[-2], parts[-1]
                if len(ts1) == 8 and len(ts2) == 6:
                    date_str = f"{ts1[:4]}-{ts1[4:6]}-{ts1[6:]}"
                    self.rollback_combo.addItem(f"Backup: {date_str}", str(b))
                else:
                    self.rollback_combo.addItem(f"Backup: {b.name}", str(b))
            except Exception:
                self.rollback_combo.addItem(f"Backup: {b.name}", str(b))

        self.rollback_combo.setFixedHeight(28)
        c2_layout.addWidget(self.rollback_combo)

        c2_layout.addSpacing(8)

        # Main validate/download button
        self.validate_btn = QPushButton()
        self.validate_btn.setFixedHeight(28)
        self.validate_btn.setStyleSheet("font-weight: bold; font-size: 11px;")
        c2_layout.addWidget(self.validate_btn)

        c2_layout.addSpacing(8)

        # Check for Updates button
        self.check_btn = QPushButton("Check for Updates")
        self.check_btn.setFixedHeight(28)
        self.check_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid #2d2d34;
            }}
            QPushButton:hover {{
                border-color: {self.accent_color};
                color: {self.accent_color};
            }}
        """)
        c2_layout.addWidget(self.check_btn)

        c2_layout.addStretch(1)

        # Connect actions
        self.validate_btn.clicked.connect(
            lambda: self.parent_window._fetch_game_manifest(
                self.game_data,
                self,
                local_path_override=self.rollback_combo.currentData() if backups else None
            )
        )

        def _on_check_clicked():
            if self.parent_window.game_manager:
                self.check_btn.setEnabled(False)
                self.check_btn.setText("Checking...")
                self.parent_window.game_manager.check_single_game_update(self.appid)

        self.check_btn.clicked.connect(_on_check_clicked)

        def _on_combo_changed():
            if self.rollback_combo.currentData() is not None:
                self.validate_btn.setText("Install Selected Build")
            else:
                is_update_now = self.game_data.get("update_status") == "update_available"
                self.validate_btn.setText("Download Update" if is_update_now else "Validate Files")

        if backups:
            self.rollback_combo.currentIndexChanged.connect(_on_combo_changed)

        self._update_status_ui(self.game_data.get("update_status"))
        
        if self.parent_window.game_manager:
            self.parent_window.game_manager.game_update_status_changed.connect(self._on_status_changed)
            self.finished.connect(
                lambda: self.parent_window.game_manager.game_update_status_changed.disconnect(self._on_status_changed)
                if self.parent_window.game_manager else None
            )

        grid_layout.addWidget(card2, 0, 1)

        # Card 3: Game Preferences
        card3 = QFrame()
        card3.setObjectName("card3")
        c3_layout = QVBoxLayout(card3)
        c3_layout.setContentsMargins(10, 10, 10, 10)
        c3_layout.setSpacing(6)

        c3_layout.addStretch(1)

        pref_title = QLabel("Game Preferences")
        pref_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #ffffff;")
        c3_layout.addWidget(pref_title)

        c3_layout.addSpacing(10)

        pref1_layout = QHBoxLayout()
        pref1_lbl = QLabel("Auto-update manifest")
        pref1_lbl.setStyleSheet("color: #a0a0ab; font-size: 11px;")
        self.pref1_toggle = SwitchToggle(active_color=self.accent_color)
        self.pref1_toggle.setChecked(
            self.settings.value(f"auto_update_manifest/{self.appid}", True, type=bool) if self.settings else True
        )
        self.pref1_toggle.stateChanged.connect(
            lambda state: self.settings.setValue(f"auto_update_manifest/{self.appid}", state) if self.settings else None
        )
        pref1_layout.addWidget(pref1_lbl)
        pref1_layout.addStretch()
        pref1_layout.addWidget(self.pref1_toggle)
        c3_layout.addLayout(pref1_layout)

        c3_layout.addSpacing(10)

        pref2_layout = QHBoxLayout()
        pref2_lbl = QLabel("Exclude from update all")
        pref2_lbl.setStyleSheet("color: #a0a0ab; font-size: 11px;")
        self.pref2_toggle = SwitchToggle(active_color="#e05a47")
        self.pref2_toggle.setChecked(
            self.settings.value(f"exclude_from_update_all/{self.appid}", False, type=bool) if self.settings else False
        )
        self.pref2_toggle.stateChanged.connect(
            lambda state: self.settings.setValue(f"exclude_from_update_all/{self.appid}", state) if self.settings else None
        )
        pref2_layout.addWidget(pref2_lbl)
        pref2_layout.addStretch()
        pref2_layout.addWidget(self.pref2_toggle)
        c3_layout.addLayout(pref2_layout)
        
        c3_layout.addStretch(1)

        grid_layout.addWidget(card3, 1, 0)

        # Card 4: SLSonline (Seamless Auto-Save)
        card4 = QFrame()
        card4.setObjectName("card4")
        c4_layout = QVBoxLayout(card4)
        c4_layout.setContentsMargins(10, 10, 10, 10)
        c4_layout.setSpacing(6)

        c4_layout.addStretch(1)

        sls_title = QLabel("SLSonline")
        sls_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #ffffff;")
        c4_layout.addWidget(sls_title)

        c4_layout.addSpacing(12)

        sls_row = QHBoxLayout()
        sls_row.setSpacing(8)

        self.sls_toggle = SwitchToggle(active_color=self.accent_color)
        sls_row.addWidget(self.sls_toggle)

        self.sls_input = QLineEdit()
        self.sls_input.setPlaceholderText("480")
        self.sls_input.setValidator(QIntValidator())
        self.sls_input.setFixedHeight(24)
        sls_row.addWidget(self.sls_input, 1)
        c4_layout.addLayout(sls_row)
        
        c4_layout.addStretch(1)

        # Connect SLSonline logic
        if is_slssteam_config_management_enabled() and self.appid not in ("0", "N/A", "unknown", "480"):
            config = get_user_config_path()
            if config.exists():
                existing_fake_id = get_fake_appid(config, self.appid)
                if existing_fake_id:
                    self.sls_toggle.setChecked(True)
                    self.sls_input.setText(existing_fake_id)
                    self.sls_input.setEnabled(True)
                else:
                    self.sls_toggle.setChecked(False)
                    self.sls_input.setText("480")
                    self.sls_input.setEnabled(False)

            def _on_sls_toggle_changed(checked):
                self.sls_input.setEnabled(checked)
                fake_id = self.sls_input.text().strip() or "480"
                name = self.game_data.get("game_name", "Unknown")
                if checked:
                    # Sync to config
                    current_in_config = get_fake_appid(config, self.appid)
                    if current_in_config:
                        remove_fake_app_id(config, self.appid, current_in_config)
                    add_fake_app_id(config, self.appid, name, fake_id)
                else:
                    current_in_config = get_fake_appid(config, self.appid)
                    if current_in_config:
                        remove_fake_app_id(config, self.appid, current_in_config)

            def _on_sls_input_finished():
                if self.sls_toggle.isChecked():
                    fake_id = self.sls_input.text().strip() or "480"
                    name = self.game_data.get("game_name", "Unknown")
                    current_fake_id = get_fake_appid(config, self.appid)
                    if current_fake_id != fake_id:
                        if current_fake_id:
                            remove_fake_app_id(config, self.appid, current_fake_id)
                        add_fake_app_id(config, self.appid, name, fake_id)

            self.sls_toggle.stateChanged.connect(_on_sls_toggle_changed)
            self.sls_input.editingFinished.connect(_on_sls_input_finished)
        else:
            self.sls_toggle.setEnabled(False)
            self.sls_input.setEnabled(False)

        grid_layout.addWidget(card4, 1, 1)

        layout.addLayout(grid_layout)
        self.stacked_widget.addWidget(page)

    def _update_status_ui(self, status):
        """Update status badge indicator design & text (Download Button is Green)."""
        if status == "update_available":
            self.status_badge.setText("★  NEW VERSION AVAILABLE")
            self.status_badge.setStyleSheet(
                "background-color: #1a301d; color: #7be09d; border: 1px solid #1a422b; border-radius: 4px; font-weight: bold; font-size: 9px;"
            )
            self.validate_btn.setText("Download Update")
            # Green button styling when update is available
            self.validate_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: #ffffff;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #66bb6a;
                }
            """)
        elif status == "up_to_date":
            self.status_badge.setText("✓  UP TO DATE")
            self.status_badge.setStyleSheet(
                "background-color: #16161a; color: #a0a0ab; border: 1px solid #282830; border-radius: 4px; font-weight: bold; font-size: 9px;"
            )
            self.validate_btn.setText("Validate Files")
            self.validate_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: #ffffff;
                    border: 1px solid #2d2d34;
                }}
                QPushButton:hover {{
                    border-color: {self.accent_color};
                }}
            """)
        elif status == "checking":
            self.status_badge.setText("⟳  CHECKING FOR UPDATES...")
            self.status_badge.setStyleSheet(
                "background-color: #1a223a; color: #7ab3ff; border: 1px solid #22355e; border-radius: 4px; font-weight: bold; font-size: 9px;"
            )
            self.validate_btn.setText("Validate Files")
        else:
            self.status_badge.setText("?  STATUS UNKNOWN")
            self.status_badge.setStyleSheet(
                "background-color: #16161a; color: #a0a0ab; border: 1px solid #282830; border-radius: 4px; font-weight: bold; font-size: 9px;"
            )
            self.validate_btn.setText("Validate Files")

    def _on_status_changed(self, changed_appid, new_status):
        if changed_appid != self.appid:
            return
        self.game_data["update_status"] = new_status
        self._update_status_ui(new_status)
        self.check_btn.setEnabled(True)
        self.check_btn.setText("Check for Updates")
        
        # Check if auto-update is enabled
        if self.pref1_toggle.isChecked() and new_status == "update_available":
            self.parent_window._fetch_game_manifest(self.game_data, self, download_only=True)

    def _get_manifest_age(self):
        if self.appid in ("0", "N/A", "unknown"):
            return "N/A"
        fpath = get_base_path() / "hubcap_manifests" / f"accela_fetch_{self.appid}.zip"
        if fpath.exists():
            try:
                return self._format_time_diff(fpath.stat().st_mtime)
            except Exception:
                pass
        return "Not Cached"

    def _get_last_checked(self):
        if self.appid in ("0", "N/A", "unknown"):
            return "Never"
        cache = get_update_cache()
        if cache:
            entry = cache._cache.get(str(self.appid))
            if entry and entry.get("updated_at"):
                try:
                    return self._format_time_diff(entry.get("updated_at"))
                except Exception:
                    pass
        return "Never"

    def _format_time_diff(self, ts):
        import time
        diff = int(time.time() - ts)
        if diff < 0:
            diff = 0
        if diff < 60:
            return "just now"
        elif diff < 3600:
            return f"{diff // 60}min ago"
        elif diff < 86400:
            return f"{diff // 3600}hr ago"
        elif diff < 2592000:
            return f"{diff // 86400}day ago"
        elif diff < 31536000:
            return f"{diff // 2592000}mo ago"
        else:
            return f"{diff // 31536000}yr ago"

    def _cleanup_fetcher(self, key):
        self._active_fetchers.pop(key, None)

    # ----------------------------------------------------
    # Uninstall Tab
    # ----------------------------------------------------
    def _init_uninstall_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        layout.addStretch(1)

        card = QFrame()
        card.setObjectName("uninstall_card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(15, 15, 15, 15)
        card_layout.setSpacing(10)

        title = QLabel("Remove Game")
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #e05a47; border: none; background: transparent;")
        card_layout.addWidget(title)

        desc = QLabel("Are you sure you want to remove this game and its downloaded files?")
        desc.setStyleSheet("color: #a0a0ab; border: none; background: transparent;")
        desc.setWordWrap(True)
        card_layout.addWidget(desc)

        self.uninstall_opts = {}
        if platform.system() == "Linux":
            self.uninstall_opts["compat"] = QCheckBox("Remove Proton/Wine prefix data")
            self.uninstall_opts["saves"] = QCheckBox("Remove local cloud saves")
            card_layout.addWidget(self.uninstall_opts["compat"])
            card_layout.addWidget(self.uninstall_opts["saves"])

        uninstall_btn = QPushButton("Uninstall Game")
        uninstall_btn.setFixedHeight(28)
        uninstall_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a1614;
                color: #ff8a7a;
                border: 1px solid #54221d;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #54221d;
            }
        """)
        uninstall_btn.clicked.connect(
            lambda: self.parent_window._uninstall_game(self.game_data, self, self.uninstall_opts)
        )
        card_layout.addWidget(uninstall_btn)

        layout.addWidget(card)
        layout.addStretch(1)
        self.stacked_widget.addWidget(page)

    # ----------------------------------------------------
    # Tools Tab (Redesigned Alignment and Spacing)
    # ----------------------------------------------------
    def _init_tools_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        path = self.game_data.get("install_path")
        name = self.game_data.get("game_name")

        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(10)

        # Card: DRM Removal
        drm_card = QFrame()
        drm_card.setObjectName("drm_card")
        drm_layout = QVBoxLayout(drm_card)
        drm_layout.setContentsMargins(10, 10, 10, 10)
        drm_layout.setSpacing(6)

        drm_title = QLabel("DRM Removal")
        drm_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #ffffff;")
        drm_layout.addWidget(drm_title)
        
        drm_layout.addStretch(1)

        sl_btn = QPushButton("Remove DRM (Steamless)")
        sl_btn.setFixedHeight(28)
        sl_btn.clicked.connect(
            lambda: self.parent_window.main_window.task_manager.run_steamless_for_game(path, name)
        )
        drm_layout.addWidget(sl_btn)

        sl_aio_btn = QPushButton("Remove DRM (Steamless-AIO)")
        sl_aio_btn.setFixedHeight(28)
        sl_aio_btn.clicked.connect(
            lambda: self.parent_window.main_window.task_manager.run_steamless_aio_for_game(path, name)
        )
        drm_layout.addWidget(sl_aio_btn)
        
        drm_layout.addStretch(1)
        row1_layout.addWidget(drm_card, 1)

        # Card: Goldberg Emulator
        gb_card = QFrame()
        gb_card.setObjectName("gb_card")
        gb_layout = QVBoxLayout(gb_card)
        gb_layout.setContentsMargins(10, 10, 10, 10)
        gb_layout.setSpacing(6)

        gb_title = QLabel("Goldberg Emulator")
        gb_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #ffffff;")
        gb_layout.addWidget(gb_title)
        
        gb_layout.addStretch(1)

        self.gb_btn = QPushButton("Checking Goldberg status...")
        self.gb_btn.setFixedHeight(28)
        self.gb_btn.setEnabled(False)
        gb_layout.addWidget(self.gb_btn)
        
        # Connect signal to update gb_btn
        self.parent_window.goldberg_check_complete.connect(self._on_goldberg_check_complete)
        self.finished.connect(
            lambda: self.parent_window.goldberg_check_complete.disconnect(self._on_goldberg_check_complete)
            if hasattr(self.parent_window, "goldberg_check_complete") else None
        )
        
        # Start background check
        self.parent_window.executor.submit(self.parent_window._check_goldberg_async, path)
        
        # Connect Goldberg click action
        def _on_gb_click():
            if not self.parent_window.main_window or not self.parent_window.main_window.task_manager:
                return
            is_applied = "Remove" in self.gb_btn.text()
            if is_applied:
                self.parent_window.main_window.task_manager.remove_goldberg_from_game(
                    path, self.appid, name, show_dialog=True
                )
            else:
                self.parent_window.main_window.task_manager.apply_goldberg_to_game(
                    path, self.appid, name, show_dialog=True
                )
            self.gb_btn.setText("Updating status...")
            self.gb_btn.setEnabled(False)
            self.parent_window.executor.submit(self.parent_window._check_goldberg_async, path)

        self.gb_btn.clicked.connect(_on_gb_click)
        
        gb_layout.addStretch(1)
        row1_layout.addWidget(gb_card, 1)

        layout.addLayout(row1_layout)

        # Row 2 Grid: Depot Card & Fix Install Card
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(10)

        # Card: Depot Config
        depot_card = QFrame()
        depot_card.setObjectName("depot_card")
        depot_layout = QVBoxLayout(depot_card)
        depot_layout.setContentsMargins(10, 10, 10, 10)
        depot_layout.setSpacing(6)

        depot_title = QLabel("Depot Configuration")
        depot_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #ffffff;")
        depot_layout.addWidget(depot_title)
        
        depot_layout.addStretch(1)

        self.depot_status_lbl = QLabel()
        self.depot_status_lbl.setStyleSheet("color: #a0a0ab; font-style: italic; font-size: 10px;")
        self._update_depot_label()
        depot_layout.addWidget(self.depot_status_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        configure_btn = QPushButton("Choose...")
        configure_btn.setFixedHeight(28)
        configure_btn.clicked.connect(lambda: self._configure_depots_wrapper())
        btn_row.addWidget(configure_btn, 1)

        reset_btn = QPushButton("Reset")
        reset_btn.setFixedHeight(28)
        reset_btn.clicked.connect(lambda: self._reset_depots_wrapper())
        btn_row.addWidget(reset_btn, 1)
        
        depot_layout.addLayout(btn_row)
        
        depot_layout.addStretch(1)
        row2_layout.addWidget(depot_card, 1)

        # Card: Fix Install
        fix_card = QFrame()
        fix_card.setObjectName("fix_card")
        fix_layout = QVBoxLayout(fix_card)
        fix_layout.setContentsMargins(10, 10, 10, 10)
        fix_layout.setSpacing(6)

        fix_title = QLabel("Fix Install")
        fix_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #ffffff;")
        fix_layout.addWidget(fix_title)
        
        fix_layout.addStretch(1)

        fix_desc = QLabel("Removes local .acf file.")
        fix_desc.setStyleSheet("color: #888890; font-size: 10px;")
        fix_desc.setWordWrap(True)
        fix_layout.addWidget(fix_desc)

        fix_btn = QPushButton("Fix Install (Remove .acf)")
        fix_btn.setFixedHeight(28)
        fix_btn.clicked.connect(lambda: self.parent_window._fix_game_install(self.game_data))
        fix_layout.addWidget(fix_btn)
        
        fix_layout.addStretch(1)
        row2_layout.addWidget(fix_card, 1)

        layout.addLayout(row2_layout)

        # Row 3: Log Configuration Card
        row3_layout = QHBoxLayout()
        log_card = QFrame()
        log_card.setObjectName("log_card")
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(10, 10, 10, 10)
        log_layout.setSpacing(6)

        log_title = QLabel("Log Configuration")
        log_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #ffffff;")
        log_layout.addWidget(log_title)
        
        log_layout.addStretch(1)

        combos_layout = QHBoxLayout()
        combos_layout.setSpacing(10)

        level_lbl = QLabel("Level:")
        level_lbl.setStyleSheet("color: #a0a0ab;")
        self.log_level_combo = CenteredComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.setFixedHeight(28)
        self.log_level_combo.setCurrentText(
            self.settings.value("log_filter_level", "DEBUG", type=str) if self.settings else "DEBUG"
        )

        category_lbl = QLabel("Filter:")
        category_lbl.setStyleSheet("color: #a0a0ab;")
        self.log_category_combo = CenteredComboBox()
        self.log_category_combo.addItems([
            "All Modules",
            "Only Steam Client & API",
            "Only Downloads & Manifests",
            "Only Database & Library"
        ])
        self.log_category_combo.setFixedHeight(28)
        self.log_category_combo.setCurrentText(
            self.settings.value("log_filter_category", "All Modules", type=str) if self.settings else "All Modules"
        )

        combos_layout.addWidget(level_lbl)
        combos_layout.addWidget(self.log_level_combo, 1)
        combos_layout.addWidget(category_lbl)
        combos_layout.addWidget(self.log_category_combo, 1)

        log_layout.addLayout(combos_layout)
        log_layout.addStretch(1)

        row3_layout.addWidget(log_card, 1)
        layout.addLayout(row3_layout)

        def _on_log_settings_changed():
            if self.settings:
                self.settings.setValue("log_filter_level", self.log_level_combo.currentText())
                self.settings.setValue("log_filter_category", self.log_category_combo.currentText())
            try:
                from utils.logger import update_log_filters
                update_log_filters()
            except Exception as e:
                logger.error(f"Failed to update log filters: {e}")

        self.log_level_combo.currentIndexChanged.connect(_on_log_settings_changed)
        self.log_category_combo.currentIndexChanged.connect(_on_log_settings_changed)

        self.stacked_widget.addWidget(page)

    def _on_goldberg_check_complete(self, is_applied):
        if hasattr(self, "gb_btn"):
            self.gb_btn.setText("Remove Goldberg" if is_applied else "Apply Goldberg")
            self.gb_btn.setEnabled(True)
            if is_applied:
                self.gb_btn.setStyleSheet(f"border: 1px solid {self.accent_color}; color: {self.accent_color};")
            else:
                self.gb_btn.setStyleSheet("")

    def _update_depot_label(self):
        if self.settings:
            val = self.settings.value(f"depot_selection/{self.appid}", "", type=str)
            if val:
                try:
                    import json
                    data = json.loads(val)
                    selected = data.get("selected", [])
                    total = len(data.get("all_available", []))
                    self.depot_status_lbl.setText(f"{len(selected)} of {total} depots")
                    return
                except Exception:
                    pass
        self.depot_status_lbl.setText("All depots selected")

    def _configure_depots_wrapper(self):
        self.parent_window._configure_depots(self.game_data)
        self._update_depot_label()

    def _reset_depots_wrapper(self):
        self.parent_window._reset_depot_selection(self.game_data)
        self._update_depot_label()
