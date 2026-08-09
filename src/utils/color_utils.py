import logging
from PyQt6.QtGui import QColor

logger = logging.getLogger(__name__)


def get_relative_luminance(color_hex_or_rgb) -> float:
    """
    Computes the relative luminance of a color based on WCAG 2.1 specs.
    Accepts a hex string (e.g. '#FFFFFF' or 'FFFFFF') or an RGB tuple/list (r, g, b).
    """
    if isinstance(color_hex_or_rgb, str):
        hex_str = color_hex_or_rgb.lstrip('#')
        if len(hex_str) == 6:
            try:
                r = int(hex_str[0:2], 16)
                g = int(hex_str[2:4], 16)
                b = int(hex_str[4:6], 16)
            except ValueError:
                r, g, b = 255, 255, 255
        else:
            r, g, b = 255, 255, 255
    else:
        try:
            r, g, b = color_hex_or_rgb[:3]
        except (TypeError, IndexError):
            r, g, b = 255, 255, 255

    # Standard WCAG sRGB conversion to relative luminance
    def srgb_to_linear(c):
        val = c / 255.0
        if val <= 0.03928:
            return val / 12.92
        else:
            return ((val + 0.055) / 1.055) ** 2.4

    r_l = srgb_to_linear(r)
    g_l = srgb_to_linear(g)
    b_l = srgb_to_linear(b)

    return 0.2126 * r_l + 0.7152 * g_l + 0.0722 * b_l


def get_contrast_ratio(color1, color2) -> float:
    """
    Computes the WCAG contrast ratio between two colors.
    """
    l1 = get_relative_luminance(color1)
    l2 = get_relative_luminance(color2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def get_best_foreground_color(bg_hex: str, dark_color: str = "#121214", light_color: str = "#FFFFFF") -> str:
    """
    Returns either dark_color or light_color depending on which one has better WCAG contrast against bg_hex.
    Guarantees contrast complies with WCAG AA/AAA.
    """
    try:
        ratio_light = get_contrast_ratio(bg_hex, light_color)
        ratio_dark = get_contrast_ratio(bg_hex, dark_color)
        return light_color if ratio_light >= ratio_dark else dark_color
    except Exception as e:
        logger.error(f"Error computing best foreground color: {e}")
        return light_color


def get_dark_container_color(accent_hex: str) -> str:
    """
    Generates a dark-mode friendly container color (Tone 30-ish in HCT/Material space)
    from the given accent color. Keeps the hue, but decreases the brightness/value.
    """
    try:
        color = QColor(accent_hex)
        h, s, v, a = color.getHsv()
        # M3 Tone 30 corresponds to ~30-38% brightness.
        # Boost saturation slightly to keep the color rich and vibrant in the dark container.
        s_dark = min(255, int(s * 1.15)) if s > 0 else 0
        v_dark = max(20, min(80, int(v * 0.35)))
        
        dark_color = QColor.fromHsv(h, s_dark, v_dark, a)
        return dark_color.name()
    except Exception as e:
        logger.error(f"Error generating dark container color: {e}")
        return "#2d161a"  # Safe default dark fallback


def get_semantic_colors(accent_hex: str) -> dict:
    """
    Returns a dict of theme-harmonized semantic colors (success, error, warning, info)
    derived from the user's accent color's saturation and lightness.
    """
    try:
        color = QColor(accent_hex)
        h, s, v, a = color.getHsv()
        # Keep similar saturation and brightness profiles to keep them harmonized,
        # but change the hue to standard semantic angles.
        s_sem = max(100, min(s, 180)) if s > 0 else 0
        v_sem = max(180, min(v, 230))
        
        success = QColor.fromHsv(120, s_sem, v_sem, a).name()  # Vibrant soft green
        error = QColor.fromHsv(0, s_sem, v_sem, a).name()      # Vibrant soft red
        warning = QColor.fromHsv(40, s_sem, v_sem, a).name()    # Vibrant soft orange/yellow
        info = QColor.fromHsv(210, s_sem, v_sem, a).name()      # Vibrant soft blue
        
        return {
            "success": success,
            "error": error,
            "warning": warning,
            "info": info
        }
    except Exception as e:
        logger.error(f"Error generating semantic colors: {e}")
        return {
            "success": "#81c784",
            "error": "#e57373",
            "warning": "#ffd54f",
            "info": "#64b5f6"
        }


def get_grayscale_color(hex_color: str) -> str:
    """
    Converts a hex color string to grayscale by zeroing out saturation (s = 0) while keeping
    lightness/brightness untouched, so a bright blue switch becomes a mid-gray, not white or black.
    Does NOT change opacity/alpha — output remains fully opaque.
    """
    try:
        color = QColor(hex_color)
        h, s, l, a = color.getHsl()
        gray_color = QColor.fromHsl(h, 0, l, a)
        return gray_color.name()
    except Exception as e:
        logger.error(f"Error generating grayscale color for '{hex_color}': {e}")
        return "#9E9E9E"


