#!/usr/bin/env python3
# shelf_pkg/constants.py — Shared paths, palette tokens, and DnD targets for Shelf.

import os
import sys

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk

POPUPS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_ROOT = os.path.dirname(POPUPS_DIR)
SYSTEM_DIR = os.path.join(SCRIPTS_ROOT, "system")
HYPR_DIR = os.path.dirname(SCRIPTS_ROOT)

for p in (POPUPS_DIR, SCRIPTS_ROOT, SYSTEM_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

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
        WIDTH_SHELF,
        hex_to_rgba,
    )
except ImportError:
    WIDTH_SHELF = 464
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

    def hex_to_rgba(hex_code: str, alpha: float = 1.0):
        h = hex_code.strip().lstrip('#')
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, float(alpha))

C_LIGHT_BG = C_BG_CREAM
C_RUBY_PRI = C_BG_WAYBAR
C_RUBY_MUT = C_TEXT_MUT

SHELF_DIR = os.path.expanduser("~/.cache/shelf")
if not os.path.exists(SHELF_DIR) and os.path.exists(os.path.expanduser("~/.cache/serena/shelf")):
    SHELF_DIR = os.path.expanduser("~/.cache/serena/shelf")

CLIPHIST_DB = os.path.expanduser("~/.cache/cliphist/db")
PID_FILE = "/tmp/shelf.pid"
MODE_FILE = "/tmp/shelf.mode"

PINNED_FILE = os.path.expanduser("~/.cache/shelf_pinned_clips.json")
if not os.path.exists(PINNED_FILE) and os.path.exists(os.path.expanduser("~/.cache/serena_pinned_clips.json")):
    PINNED_FILE = os.path.expanduser("~/.cache/serena_pinned_clips.json")

PINS_DIR = os.path.expanduser("~/.cache/shelf_pins")
if not os.path.exists(PINS_DIR) and os.path.exists(os.path.expanduser("~/.cache/serena_pins")):
    PINS_DIR = os.path.expanduser("~/.cache/serena_pins")

POSITION_CACHE = "/tmp/shelf_pos.json"
os.makedirs(SHELF_DIR, exist_ok=True)
os.makedirs(PINS_DIR, exist_ok=True)

TARGET_URI_LIST = 80
TARGET_TEXT = 81

DROP_TARGETS = [
    Gtk.TargetEntry.new("text/uri-list", 0, TARGET_URI_LIST),
    Gtk.TargetEntry.new("text/plain", 0, TARGET_TEXT),
]

DRAG_SOURCE_TARGETS = [
    Gtk.TargetEntry.new("text/uri-list", 0, TARGET_URI_LIST),
]

STYLESHEET_PATH = os.path.join(HYPR_DIR, "styles", "shelf.css")
