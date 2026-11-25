#!/usr/bin/env python3
# tactile.py — 3D cel-shaded tactile rendering for anime aesthetic widgets.

import cairo
import gi

gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo

try:
    from system.palette import (
        hex_to_rgba, WINE_RED, DARK_RUBY, PURE_WHITE
    )
except Exception:
    def hex_to_rgba(h, a=1.0):
        h = h.strip().lstrip('#')
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, float(a))
    WINE_RED = "#851733"
    DARK_RUBY = "#4D0A1C"
    PURE_WHITE  = "#FFFFFF"


def draw_tactile_3d_text(cr: cairo.Context, layout: Pango.Layout, start_x: float, start_y: float,
                         core_color=None, dark_color=None, white_color=None,
                         extrusion_h: float = 4.0, white_w: float = 4.6, dark_extra: float = 1.6):
    """
    Renders 3-layer cel-shaded 3D tactile text:
    1. Dark 3D extrusion downward (stepped shadow)
    2. Crisp white contour outline
    3. Core fill color
    """
    if core_color is None:
        core_color = hex_to_rgba(WINE_RED)[:3]
    elif isinstance(core_color, str):
        core_color = hex_to_rgba(core_color)[:3]

    if dark_color is None:
        dark_color = hex_to_rgba(DARK_RUBY)[:3]
    elif isinstance(dark_color, str):
        dark_color = hex_to_rgba(dark_color)[:3]

    if white_color is None:
        white_color = hex_to_rgba(PURE_WHITE)[:3]
    elif isinstance(white_color, str):
        white_color = hex_to_rgba(white_color)[:3]

    total_dark_w = white_w + dark_extra * 2.0

    cr.save()
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)

    # Layer 1: Dark 3D extrusion downward
    steps = max(1, int(extrusion_h * 4))
    for s in range(steps + 1):
        dy = extrusion_h * (s / steps)
        cr.save()
        cr.translate(start_x, start_y + dy)
        PangoCairo.layout_path(cr, layout)
        cr.set_source_rgb(*dark_color)
        cr.set_line_width(total_dark_w)
        cr.stroke_preserve()
        cr.fill()
        cr.restore()

    # Layer 2: White contour outline
    cr.save()
    cr.translate(start_x, start_y)
    PangoCairo.layout_path(cr, layout)
    cr.set_source_rgb(*white_color)
    cr.set_line_width(white_w)
    cr.stroke_preserve()
    cr.fill()
    cr.restore()

    # Layer 3: Core fill
    cr.save()
    cr.translate(start_x, start_y)
    PangoCairo.layout_path(cr, layout)
    cr.set_source_rgb(*core_color)
    cr.fill()
    cr.restore()

    cr.restore()
