#!/usr/bin/env python3
# draggable_popup.py — Compatibility shim forwarding to ui_core.base_window.

import os
import sys

# Ensure ui_core is importable
_SCRIPTS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS_ROOT not in sys.path:
    sys.path.insert(0, _SCRIPTS_ROOT)

from ui_core.base_window import (
    DraggablePopup,
    get_cursor_pos,
    get_monitor_geometry,
    LayerShellPopupWindow
)

__all__ = [
    "DraggablePopup",
    "get_cursor_pos",
    "get_monitor_geometry",
    "LayerShellPopupWindow"
]
