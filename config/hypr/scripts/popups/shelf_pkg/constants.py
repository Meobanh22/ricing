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
        CREAM_WHITE,
        CREAM_WHITE_96,
        DARK_RUBY,
        DARK_WINE,
        DARK_WINE_RGBA,
        DEEP_WINE,
        DEEP_WINE_RGBA,
        LIGHT_RED,
        LIGHT_RED_RGBA,
        LIGHT_WINE,
        MUTED_PINK,
        PALETTE,
        PURE_WHITE,
        PURE_WHITE_12_RGBA,
        SKY_BLUE,
        SOFT_GREEN,
        SOFT_PINK,
        SOFT_WINE,
        VIVID_RED,
        VIVID_RED_RGBA,
        WARM_YELLOW,
        WIDTH_SHELF,
        WINE_RED,
        hex_to_rgba,
    )
except ImportError:
    WIDTH_SHELF = 464
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
    DARK_WINE_RGBA = (32.0 / 255.0, 16.0 / 255.0, 18.0 / 255.0, 0.98)
    DEEP_WINE_RGBA = (42.0 / 255.0, 26.0 / 255.0, 31.0 / 255.0, 0.95)
    VIVID_RED_RGBA = (220.0 / 255.0, 26.0 / 255.0, 54.0 / 255.0, 1.0)
    LIGHT_RED_RGBA = (240.0 / 255.0, 45.0 / 255.0, 76.0 / 255.0, 1.0)
    PURE_WHITE_12_RGBA = (1.0, 1.0, 1.0, 0.12)

    def hex_to_rgba(hex_code: str, alpha: float = 1.0):
        h = hex_code.strip().lstrip('#')
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, float(alpha))

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
