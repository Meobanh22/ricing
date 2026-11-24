#!/usr/bin/env python3
# settings_pkg/constants.py — Shared imports, paths, dimensions, and palette tokens for Settings.

import os
import sys

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
gi.require_version('GdkPixbuf', '2.0')
try:
    gi.require_version('GtkLayerShell', '0.1')
    from gi.repository import GtkLayerShell
    HAS_LAYER_SHELL = True
except Exception:
    GtkLayerShell = None
    HAS_LAYER_SHELL = False

POPUPS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_ROOT = os.path.dirname(POPUPS_DIR)
SYSTEM_DIR = os.path.join(SCRIPTS_ROOT, "system")
SERVICES_DIR = os.path.join(SCRIPTS_ROOT, "services")
HYPR_DIR = os.path.dirname(SCRIPTS_ROOT)

for p in (POPUPS_DIR, SCRIPTS_ROOT, SYSTEM_DIR, SERVICES_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

PID_FILE = "/tmp/settings.pid"
POSITION_CACHE = "/tmp/settings_pos.json"
CACHE_FILE = os.path.expanduser("~/.cache/notifications.json")
ASSETS_DIR = os.path.join(HYPR_DIR, "assets")
FALLBACK_ASSETS_DIR = os.path.expanduser("~/.config/hypr/assets")

CLOSED_W = 420
CLOSED_H = 675
OPEN_W = 930
OPEN_H = 690
ANIM_DURATION = 0.38

try:
    from palette import (  # noqa: E402,F401
        C_ACCENT,
        C_ACCENT_HOVER,
        C_BG_CARD,
        C_BG_CARD_HOVER,
        C_BG_CREAM,
        C_BG_SUBTLE,
        C_BG_WAYBAR,
        C_BG_WIN,
        C_BORDER_3D,
        C_POKEPUFF_PINK,
        C_RIBBON,
        C_STATUS_CRIT,
        C_STATUS_SUCC,
        C_STATUS_WARN,
        C_TEXT_INV,
        C_TEXT_MUT,
        C_TEXT_PRI,
        C_TEXT_SEC,
        SUNSET_STOPS,
        hex_to_rgba,
    )
    C_SUNSET_PINK = SUNSET_STOPS[2][1]
    C_SUNSET_PASTEL = SUNSET_STOPS[3][1]
    C_SUNSET_ROSE = SUNSET_STOPS[0][1]
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
    C_POKEPUFF_PINK = "#FF5C8A"
    C_SUNSET_PINK = "#FF7299"
    C_SUNSET_PASTEL = "#EAA2C6"
    C_SUNSET_ROSE = "#A3183D"

    def hex_to_rgba(hex_code, alpha=1.0):
        h = hex_code.strip().lstrip('#')
        if len(h) == 6:
            return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)
        return (1.0, 1.0, 1.0, alpha)

COLOR_BORDER_SHADOW = hex_to_rgba(C_BORDER_3D, 0.98)
COLOR_PINK_TOP = hex_to_rgba(C_SUNSET_PINK, 1.0)
COLOR_PINK_BOT = hex_to_rgba(C_SUNSET_PASTEL, 1.0)
COLOR_PINK_INSIDE = hex_to_rgba(C_TEXT_SEC, 1.0)
COLOR_PINK_ROSE = hex_to_rgba(C_SUNSET_ROSE, 1.0)
COLOR_PINK_3D_DARK = hex_to_rgba(C_BORDER_3D, 1.0)
COLOR_PINK_3D_BOT = hex_to_rgba(C_BG_WIN, 1.0)

COLOR_RIBBON_TOP = hex_to_rgba(C_ACCENT_HOVER, 1.0)
COLOR_RIBBON_MID = hex_to_rgba(C_ACCENT, 1.0)
COLOR_RIBBON_BOT = hex_to_rgba(C_BG_WAYBAR, 1.0)
