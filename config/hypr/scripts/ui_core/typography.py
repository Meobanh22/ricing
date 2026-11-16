#!/usr/bin/env python3
# typography.py — Text rendering helpers, curved typography, and layout caching.

import math
import cairo
import gi

gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo

try:
    from system.palette import hex_to_rgba, C_BG_WIN
except Exception:
    def hex_to_rgba(h, a=1.0):
        h = h.strip().lstrip('#')
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, float(a))
    C_BG_WIN = "#201011"


_CURVED_TEXT_SURFACES = {}


def clear_text_cache():
    """Clears cached curved text surfaces."""
    global _CURVED_TEXT_SURFACES
    _CURVED_TEXT_SURFACES.clear()


def draw_curved_kerned(cr: cairo.Context, text: str, cx: float, cy_top: float,
                       r_text: float = 62.0, font_desc: str = "DejaVu Sans Bold 8.5",
                       letter_spacing: float = 1.6, color=None):
    """
    Renders curved text along an arc with proportional kerning, avoiding letter overlap.
    """
    if color is None:
        color = hex_to_rgba(C_BG_WIN)[:3]
    elif isinstance(color, str):
        color = hex_to_rgba(color)[:3]

    widths = []
    for ch in text:
        l = PangoCairo.create_layout(cr)
        l.set_font_description(Pango.FontDescription(font_desc))
        l.set_text(ch, -1)
        ink, log = l.get_pixel_extents()
        w = log.width if ch != ' ' else 6.0
        widths.append(w + letter_spacing)

    total_arc = sum(widths)
    total_ang = total_arc / r_text
    start_ang = -math.pi / 2.0 - total_ang / 2.0

    curr_ang = start_ang
    for i, ch in enumerate(text):
        char_w = widths[i]
        ang = curr_ang + (char_w / 2.0) / r_text
        curr_ang += char_w / r_text

        x = cx + r_text * math.cos(ang)
        y = cy_top + r_text * math.sin(ang)
        cr.save()
        cr.translate(x, y)
        cr.rotate(ang + math.pi / 2.0)
        l = PangoCairo.create_layout(cr)
        l.set_font_description(Pango.FontDescription(font_desc))
        l.set_text(ch, -1)
        ink, log = l.get_pixel_extents()
        cr.move_to(-log.width / 2.0, -log.height / 2.0)
        cr.set_source_rgb(*color)
        PangoCairo.show_layout(cr, l)
        cr.restore()


def draw_curved_kerned_cached(cr: cairo.Context, text: str, cx: float, cy_top: float,
                              r_text: float = 62.0, font_desc: str = "DejaVu Sans Bold 8.5",
                              letter_spacing: float = 1.6, color=None):
    """
    Renders curved text from an internal surface cache for high-framerate redraws.
    """
    if color is None:
        color = hex_to_rgba(C_BG_WIN)[:3]
    elif isinstance(color, str):
        color = hex_to_rgba(color)[:3]

    color_tuple = tuple(color) if isinstance(color, (list, tuple)) else (0.1, 0.1, 0.1)
    key = (text, font_desc, r_text, letter_spacing, color_tuple)
    entry = _CURVED_TEXT_SURFACES.get(key)
    if entry is None:
        ref_w = int(r_text * 2 + 60)
        ref_h = int(r_text + 40)
        rel_cx = ref_w / 2.0
        rel_cy = float(ref_h - 10)
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, ref_w, ref_h)
        scr = cairo.Context(surf)
        draw_curved_kerned(scr, text, rel_cx, rel_cy, r_text, font_desc, letter_spacing, color_tuple)
        entry = (surf, ref_w, ref_h, rel_cx, rel_cy)
        _CURVED_TEXT_SURFACES[key] = entry

    surf, ref_w, ref_h, rel_cx, rel_cy = entry
    cr.save()
    cr.set_source_surface(surf, cx - rel_cx, cy_top - rel_cy)
    cr.paint()
    cr.restore()
