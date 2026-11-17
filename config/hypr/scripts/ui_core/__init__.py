#!/usr/bin/env python3
# __init__.py — UI Core package for Serena Wine Hyprland desktop environment.
# Exports foundational window, drawing, tactile, typography, and asset primitives.

from .base_window import (
    LayerShellPopupWindow,
    DraggablePopup,
    get_cursor_pos,
    get_monitor_geometry
)

from .shapes import (
    clear_surface,
    draw_rounded_rect,
    squircle,
    clip_device_bounds,
    draw_anime_grooves,
    draw_bow_mark,
    draw_bell_icon
)

from .typography import (
    draw_curved_kerned,
    draw_curved_kerned_cached,
    clear_text_cache
)

from .tactile import (
    draw_tactile_3d_text
)

from .assets import (
    resolve_asset,
    get_repo_root
)

__all__ = [
    "LayerShellPopupWindow",
    "DraggablePopup",
    "get_cursor_pos",
    "get_monitor_geometry",
    "clear_surface",
    "draw_rounded_rect",
    "squircle",
    "clip_device_bounds",
    "draw_anime_grooves",
    "draw_bow_mark",
    "draw_bell_icon",
    "draw_curved_kerned",
    "draw_curved_kerned_cached",
    "clear_text_cache",
    "draw_tactile_3d_text",
    "resolve_asset",
    "get_repo_root"
]
