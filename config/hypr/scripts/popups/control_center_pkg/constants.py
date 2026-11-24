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
        ACCENT_HOVER_RGBA,
        ACCENT_RGBA,
        BG_CARD_RGBA,
        BG_WINDOW_RGBA,
        C_ACCENT,
        C_ACCENT_HOVER,
        C_BG_CARD,
        C_BG_CARD_HOVER,
        C_BG_SUBTLE,
        C_BG_WAYBAR,
        C_BG_WIN,
        C_BORDER_3D,
        C_RIBBON,
        C_SCREEN_CYAN,
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
    C_SCREEN_CYAN = "#87F0FF"

    def hex_to_rgba(hex_code: str, alpha: float = 1.0):
        h = hex_code.strip().lstrip('#')
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, float(alpha))

PID_FILE = "/tmp/control_center.pid"
CACHE_FILE = os.path.expanduser("~/.cache/notifications.json")
