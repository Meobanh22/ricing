#!/usr/bin/env python3
# control_center_pkg/constants.py — Shared imports, paths, and palette tokens for Control Center.

import os
import sys

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
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

for p in (POPUPS_DIR, SCRIPTS_ROOT, SYSTEM_DIR, SERVICES_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from palette import (  # noqa: E402,F401
        CREAM_WHITE,
        DARK_RUBY,
        DARK_WINE,
        DARK_WINE_RGBA,
        DEEP_WINE,
        DEEP_WINE_RGBA,
        LIGHT_CYAN,
        LIGHT_RED,
        LIGHT_RED_RGBA,
        LIGHT_WINE,
        MUTED_PINK,
        PALETTE,
        PURE_WHITE,
        SKY_BLUE,
        SOFT_GREEN,
        SOFT_PINK,
        SOFT_WINE,
        VIVID_RED,
        VIVID_RED_RGBA,
        WARM_YELLOW,
        WINE_RED,
        hex_to_rgba,
    )
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
    LIGHT_CYAN = "#87F0FF"

    def hex_to_rgba(hex_code: str, alpha: float = 1.0):
        h = hex_code.strip().lstrip('#')
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, float(alpha))

PID_FILE = "/tmp/control_center.pid"
CACHE_FILE = os.path.expanduser("~/.cache/notifications.json")
