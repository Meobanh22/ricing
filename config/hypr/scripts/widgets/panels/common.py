#!/usr/bin/env python3
# panels/common.py — Shared paths, palette imports, and GTK helpers for desktop widgets.

import os
import sys

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
try:
    gi.require_version('GtkLayerShell', '0.1')
    from gi.repository import GtkLayerShell
    HAS_LAYER_SHELL = True
except Exception:
    GtkLayerShell = None
    HAS_LAYER_SHELL = False

from gi.repository import Gdk, Gtk

WIDGETS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_ROOT = os.path.dirname(WIDGETS_DIR)
SYSTEM_DIR = os.path.join(SCRIPTS_ROOT, "system")
HYPR_DIR = os.path.dirname(SCRIPTS_ROOT)

for p in (WIDGETS_DIR, SCRIPTS_ROOT, SYSTEM_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from ui_core import clear_surface  # noqa: E402

try:
    from palette import (  # noqa: E402,F401
        ACCENT_HOVER_RGBA,
        ACCENT_RGBA,
        BG_CARD_RGBA,
        BG_WINDOW_RGBA,
        BORDER_CARD_RGBA,
        BORDER_WINDOW_RGBA,
        C_ACCENT,
        C_ACCENT_HOVER,
        C_BG_CARD,
        C_BG_CARD_HOVER,
        C_BG_CREAM,
        C_BG_SUBTLE,
        C_BG_WAYBAR,
        C_BG_WIN,
        C_BORDER_3D,
        C_RIBBON,
        C_STATUS_CRIT,
        C_STATUS_SUCC,
        C_STATUS_WARN,
        C_TEXT_INV,
        C_TEXT_MUT,
        C_TEXT_PRI,
        C_TEXT_SEC,
        PALETTE,
        hex_to_rgba,
    )
except ImportError:
    C_BG_WIN = "#201011"
    C_BG_CARD = "#2A1A1E"
    C_BG_CARD_HOVER = "#3A222A"
    C_BG_SUBTLE = "#301F20"
    C_ACCENT = "#DC1A36"
    C_ACCENT_HOVER = "#F02D4C"
    C_TEXT_PRI = "#FFF0F5"
    C_TEXT_SEC = "#E8C2D0"
    C_TEXT_MUT = "#A68595"
    C_TEXT_INV = "#FFFFFF"
    C_STATUS_WARN = "#FFB86C"
    C_STATUS_CRIT = "#DC1A36"
    C_STATUS_SUCC = "#8FBC8F"
    C_RIBBON = "#50A6FF"
    C_BG_WAYBAR = "#851733"
    C_BORDER_3D = "#4D0A1C"
    C_BG_CREAM = "rgba(255, 240, 245, 0.96)"
    BG_WINDOW_RGBA = (32.0 / 255.0, 16.0 / 255.0, 18.0 / 255.0, 0.98)
    BG_CARD_RGBA = (42.0 / 255.0, 26.0 / 255.0, 31.0 / 255.0, 0.95)
    ACCENT_RGBA = (220.0 / 255.0, 26.0 / 255.0, 54.0 / 255.0, 1.0)
    ACCENT_HOVER_RGBA = (240.0 / 255.0, 45.0 / 255.0, 76.0 / 255.0, 1.0)
    BORDER_WINDOW_RGBA = (1.0, 1.0, 1.0, 0.12)
    BORDER_CARD_RGBA = (1.0, 1.0, 1.0, 0.12)

    def hex_to_rgba(hex_code, alpha=1.0):
        h = hex_code.strip().lstrip('#')
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, float(alpha))


def get_repo_root():
    curr = WIDGETS_DIR
    while curr and curr != "/":
        if os.path.isdir(os.path.join(curr, "config")):
            return curr
        curr = os.path.dirname(curr)
    return os.path.expanduser("~/custom")


def apply_global_css():
    """Load desktop_widgets.css globally for all widget windows."""
    css_provider = Gtk.CssProvider()
    repo_root = get_repo_root()
    candidate_paths = [
        os.path.join(HYPR_DIR, "styles", "desktop_widgets.css"),
        os.path.expanduser("~/.config/hypr/styles/desktop_widgets.css"),
        os.path.join(repo_root, "config", "hypr", "styles", "desktop_widgets.css"),
    ]
    for p in candidate_paths:
        abs_p = os.path.abspath(p)
        if os.path.exists(abs_p):
            try:
                css_provider.load_from_path(abs_p)
                break
            except Exception as e:
                print(f"[desktop_widgets] Warning: Error parsing CSS from {abs_p}: {e}", file=sys.stderr)

    screen = Gdk.Screen.get_default()
    if screen:
        Gtk.StyleContext.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER + 20)


def on_window_draw_clear(widget, cr):
    """Draw transparent RGBA surface without artifacts."""
    clear_surface(cr)
    return False


def get_uptime_str() -> str:
    """Read system uptime from /proc/uptime and format cleanly."""
    try:
        with open("/proc/uptime", "r") as f:
            sec = float(f.readline().split()[0])
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        if h >= 24:
            return f"{h // 24}d {h % 24}h"
        if h > 0:
            return f"{h}h {m}m"
        return f"{m}m"
    except Exception:
        return "--"
