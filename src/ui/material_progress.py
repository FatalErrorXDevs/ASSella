import math
import logging
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath
from PyQt6.QtCore import QTimer, Qt, QRectF

logger = logging.getLogger(__name__)

class MaterialSpinner(QWidget):
    """Indeterminate Material circular progress spinner."""
    def __init__(self, parent=None, size=36, color="#6750A4", thickness=3):
        super().__init__(parent)
        self.color = QColor(color)
        self.thickness = thickness
        self.setFixedSize(size, size)
        
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._rotate)
        self.timer.start(16)  # ~60 FPS

    def set_color(self, hex_color: str):
        self.color = QColor(hex_color)
        self.update()

    def _rotate(self):
        self.angle = (self.angle + 4) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Indeterminate breathing arc span: breathes between 90 and 270 degrees
        cycle = (self.angle // 2) % 180
        span = 90 + abs(cycle - 90) * 2
        
        pen = QPen(self.color)
        pen.setWidth(self.thickness)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        rect_size = self.width() - self.thickness - 2
        rect = QRectF(
            self.thickness / 2.0 + 1,
            self.thickness / 2.0 + 1,
            rect_size,
            rect_size
        )
        painter.drawArc(rect, int(self.angle * 16), int(span * 16))


class MaterialProgressLine(QWidget):
    """A Material Design 3 Linear Progress Indicator that supports:
    - Standard flat linear progress bar
    - Wavy sine wave progress bar
    - Determinate and Indeterminate states
    """
    def __init__(self, parent=None, color="#6750A4", thickness=4, wavy=False):
        super().__init__(parent)
        self.color = QColor(color)
        self.thickness = thickness
        self.wavy = wavy
        self.progress = -1.0  # -1.0 means indeterminate
        
        self.phase = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(16)  # ~60 FPS
        
        self.setFixedHeight(12)  # Give enough height for wave amplitude

    def set_color(self, hex_color: str):
        self.color = QColor(hex_color)
        self.update()

    def set_wavy(self, wavy: bool):
        self.wavy = wavy
        self.update()

    def set_progress(self, progress: float):
        """Set progress between 0.0 and 1.0. Set to -1.0 for indeterminate."""
        self.progress = progress
        self.update()

    def _animate(self):
        if self.progress < 0.0:  # Indeterminate
            self.phase += 0.15
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        W = self.width()
        H = self.height()
        cy = H / 2.0
        
        # 1. Paint background track (muted container color)
        track_color = QColor(self.color.red(), self.color.green(), self.color.blue(), 40)
        track_pen = QPen(track_color, self.thickness)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        
        if self.wavy:
            # Draw wavy background track
            track_path = QPainterPath()
            track_path.moveTo(0, cy)
            wavelength = 24.0
            amplitude = 3.0
            for x in range(0, W, 2):
                y = cy + amplitude * math.sin((2 * math.pi * x / wavelength))
                track_path.lineTo(x, y)
            painter.drawPath(track_path)
        else:
            # Draw standard flat track
            painter.drawLine(0, int(cy), W, int(cy))
            
        # 2. Paint active progress segment
        active_pen = QPen(self.color, self.thickness)
        active_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(active_pen)
        
        if self.progress >= 0.0:
            # Determinate mode
            limit = int(W * min(1.0, max(0.0, self.progress)))
            if limit <= 0:
                return
                
            if self.wavy:
                active_path = QPainterPath()
                active_path.moveTo(0, cy)
                wavelength = 24.0
                amplitude = 3.0
                for x in range(0, limit, 2):
                    y = cy + amplitude * math.sin((2 * math.pi * x / wavelength))
                    active_path.lineTo(x, y)
                painter.drawPath(active_path)
            else:
                painter.drawLine(0, int(cy), limit, int(cy))
        else:
            # Indeterminate mode - sliding segment/wave
            if self.wavy:
                # Animate a moving sine wave segment
                active_path = QPainterPath()
                pulse_width = W * 0.4
                center = (self.phase * 5.0) % (W + pulse_width) - (pulse_width / 2)
                start_x = max(0, int(center - pulse_width / 2))
                end_x = min(W, int(center + pulse_width / 2))
                
                if end_x > start_x:
                    wavelength = 24.0
                    amplitude = 3.0
                    y_start = cy + amplitude * math.sin((2 * math.pi * start_x / wavelength) - self.phase)
                    active_path.moveTo(start_x, y_start)
                    for x in range(start_x, end_x, 2):
                        y = cy + amplitude * math.sin((2 * math.pi * x / wavelength) - self.phase)
                        active_path.lineTo(x, y)
                    painter.drawPath(active_path)
            else:
                # Standard M3 sliding indeterminate segments
                seg1_width = W * 0.3
                seg1_start = (self.phase * 6.0) % (W + seg1_width) - seg1_width
                
                seg2_width = W * 0.15
                seg2_start = (self.phase * 10.0) % (W + seg2_width) - seg2_width
                
                s1 = max(0, int(seg1_start))
                e1 = min(W, int(seg1_start + seg1_width))
                if e1 > s1:
                    painter.drawLine(s1, int(cy), e1, int(cy))
                    
                s2 = max(0, int(seg2_start))
                e2 = min(W, int(seg2_start + seg2_width))
                if e2 > s2:
                    painter.drawLine(s2, int(cy), e2, int(cy))


class Material3LoadingIndicator(QWidget):
    """
    Material 3 Loading Indicator following M3 specs (https://m3.material.io/components/loading-indicator/specs).
    Renders a morphing shape (Circle -> Squircle -> Rounded Polygon) that rotates continuously.
    """
    def __init__(self, parent=None, size=32, color="#7ab3ff", thickness=3):
        super().__init__(parent)
        self.color = QColor(color)
        self.thickness = thickness
        self.setFixedSize(size, size)
        
        self.angle = 0.0
        self.morph_phase = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(16)  # ~60 FPS

    def set_color(self, hex_color: str):
        self.color = QColor(hex_color)
        self.update()

    def _animate(self):
        self.angle = (self.angle + 4.5) % 360.0
        self.morph_phase = (self.morph_phase + 0.04) % (2 * math.pi)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0
        r = min(w, h) / 2.0 - self.thickness - 1.0

        painter.translate(cx, cy)
        painter.rotate(self.angle)

        path = QPainterPath()
        num_points = 32
        morph_factor = (math.sin(self.morph_phase) + 1.0) / 2.0  # 0.0 to 1.0

        for i in range(num_points):
            theta = (2 * math.pi * i) / num_points
            # Interpolate radius between pure circle and squircle/rounded box
            radius = r * (1.0 - 0.2 * morph_factor * math.pow(math.sin(2 * theta), 2))
            x = radius * math.cos(theta)
            y = radius * math.sin(theta)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        path.closeSubpath()

        pen = QPen(self.color, self.thickness)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
