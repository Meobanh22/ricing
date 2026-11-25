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
        CREAM_WHITE,
        CREAM_WHITE_96,
        DARK_RUBY,
        DARK_WINE,
        DEEP_WINE,
        LIGHT_RED,
        LIGHT_WINE,
        MUTED_PINK,
        PURE_WHITE,
        SKY_BLUE,
        SOFT_GREEN,
        SOFT_PINK,
        SOFT_WINE,
        SUNSET_STOPS,
        VIVID_PINK,
        VIVID_RED,
        WARM_YELLOW,
        WINE_RED,
        hex_to_rgba,
    )
    SUNSET_PINK = SUNSET_STOPS[2][1]
    SUNSET_PASTEL = SUNSET_STOPS[3][1]
    C_SUNSET_ROSE = SUNSET_STOPS[0][1]
except ImportError:
    DARK_WINE = "#201011"
    DEEP_WINE = "#2A1A1E"
    LIGHT_WINE = "#3A222A"
    SOFT_WINE = "#301F20"
    VIVID_RED = "#DC1A36"
    LIGHT_RED = "#F02D4C"
    CREAM_WHITE = "#FFF0F5"
    SOFT_PINK = "#E8C2D0"
    MUTED_PINK = "#A68595"
    PURE_WHITE = "#FFFFFF"
    WARM_YELLOW = "#FFB86C"
    SOFT_GREEN = "#8FBC8F"
    SKY_BLUE = "#50A6FF"
    WINE_RED = "#851733"
    DARK_RUBY = "#4D0A1C"
    CREAM_WHITE_96 = "rgba(255, 240, 245, 0.96)"
    VIVID_PINK = "#FF5C8A"
    SUNSET_PINK = "#FF7299"
    SUNSET_PASTEL = "#EAA2C6"
    C_SUNSET_ROSE = "#A3183D"

    def hex_to_rgba(hex_code, alpha=1.0):
        h = hex_code.strip().lstrip('#')
        if len(h) == 6:
            return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)
        return (1.0, 1.0, 1.0, alpha)

COLOR_BORDER_SHADOW = hex_to_rgba(DARK_RUBY, 0.98)
COLOR_PINK_TOP = hex_to_rgba(SUNSET_PINK, 1.0)
COLOR_PINK_BOT = hex_to_rgba(SUNSET_PASTEL, 1.0)
COLOR_PINK_INSIDE = hex_to_rgba(SOFT_PINK, 1.0)
COLOR_PINK_ROSE = hex_to_rgba(C_SUNSET_ROSE, 1.0)
COLOR_PINK_3D_DARK = hex_to_rgba(DARK_RUBY, 1.0)
COLOR_PINK_3D_BOT = hex_to_rgba(DARK_WINE, 1.0)

COLOR_RIBBON_TOP = hex_to_rgba(LIGHT_RED, 1.0)
COLOR_RIBBON_MID = hex_to_rgba(VIVID_RED, 1.0)
COLOR_RIBBON_BOT = hex_to_rgba(WINE_RED, 1.0)
