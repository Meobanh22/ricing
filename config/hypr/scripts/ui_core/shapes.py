#!/usr/bin/env python3
# shapes.py — Common geometric path generators and Cairo shape drawing routines.

import math
import cairo
import gi

gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo

try:
    from system.palette import (
        hex_to_rgba, DARK_WINE, DARK_RUBY, VIVID_RED
    )
except Exception:
    def hex_to_rgba(h, a=1.0):
        h = h.strip().lstrip('#')
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, float(a))
    DARK_WINE = "#201011"
    DARK_RUBY = "#4D0A1C"
    VIVID_RED = "#DC1A36"


def clear_surface(cr: cairo.Context):
    """Clears a cairo surface to complete transparency without rendering artifacts."""
    cr.set_source_rgba(0, 0, 0, 0)
    cr.set_operator(cairo.OPERATOR_CLEAR)
    cr.paint()
    cr.set_operator(cairo.OPERATOR_OVER)


def draw_rounded_rect(cr: cairo.Context, x: float, y: float, w: float, h: float, r: float):
    """Generates a rounded rectangle path."""
    r = min(r, w / 2.0, h / 2.0)
    cr.new_sub_path()
    cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    cr.arc(x + w - r, y + r, r, 1.5 * math.pi, 2 * math.pi)
    cr.arc(x + w - r, y + h - r, r, 0, 0.5 * math.pi)
    cr.arc(x + r, y + h - r, r, 0.5 * math.pi, math.pi)
    cr.close_path()


def squircle(cr: cairo.Context, x: float, y: float, w: float, h: float, r: float):
    """Generates a smooth squircle/rounded rectangle path."""
    draw_rounded_rect(cr, x, y, w, h, r)


def clip_device_bounds(cr: cairo.Context, x: float, y: float, w: float, h: float, r: float):
    """Sets a rounded rectangle clipping boundary on the cairo context."""
    draw_rounded_rect(cr, x, y, w, h, r)
    cr.clip()


def draw_anime_grooves(cr: cairo.Context, cx: float, cy: float, grooves, a1: float, a2: float,
                       groove_fill=None, stroke1=None, stroke2=None):
    """Draws tech groove bands along an arc."""
    fill_rgba = groove_fill or hex_to_rgba(DARK_WINE, 0.62)
    s1_rgba = stroke1 or hex_to_rgba(DARK_WINE, 0.90)
    s2_rgba = stroke2 or hex_to_rgba(DARK_RUBY, 0.85)

    for r_inner, r_outer in grooves:
        cr.save()
        cr.new_sub_path()
        cr.arc(cx, cy, r_inner, a1, a2)
        cr.arc_negative(cx, cy, r_outer, a2, a1)
        cr.close_path()
        cr.set_source_rgba(*fill_rgba)
        cr.fill_preserve()

        cr.set_line_width(0.7)
        cr.set_source_rgba(*s1_rgba)
        cr.stroke_preserve()

        cr.set_line_width(0.35)
        cr.set_source_rgba(*s2_rgba)
        cr.stroke()
        cr.restore()


def draw_bow_mark(ctx: cairo.Context, cx: float, cy: float, size: float = 24.0, color=None):
    """Draws the solid minimal bow mark centered at (cx, cy)."""
    if color is None:
        color = hex_to_rgba(VIVID_RED)[:3]
    elif isinstance(color, str):
        color = hex_to_rgba(color)[:3]

    scale = size / 24.0
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(scale, scale)
    ctx.translate(-12.0, -12.0)
    ctx.set_source_rgb(color[0], color[1], color[2])

    # Left Wing
    ctx.new_path()
    ctx.move_to(8.9, 9.3)
    ctx.curve_to(6.4, 6.1, 3.9, 5.1, 2.6, 6.2)
    ctx.curve_to(1.4, 7.4, 1.4, 16.6, 2.6, 17.8)
    ctx.curve_to(3.9, 18.9, 6.4, 17.9, 8.9, 14.7)
    ctx.curve_to(8.5, 13.0, 8.5, 11.0, 8.9, 9.3)
    ctx.close_path()
    ctx.fill()

    # Right Wing
    ctx.new_path()
    ctx.move_to(15.1, 9.3)
    ctx.curve_to(17.6, 6.1, 20.1, 5.1, 21.4, 6.2)
    ctx.curve_to(22.6, 7.4, 22.6, 16.6, 21.4, 17.8)
    ctx.curve_to(20.1, 18.9, 17.6, 17.9, 15.1, 14.7)
    ctx.curve_to(15.5, 13.0, 15.5, 11.0, 15.1, 9.3)
    ctx.close_path()
    ctx.fill()

    # Center Knot
    draw_rounded_rect(ctx, 10.1, 8.0, 3.8, 8.0, 1.6)
    ctx.fill()
    ctx.restore()


def draw_bell_icon(ctx: cairo.Context, cx: float, cy: float, font_size: int = 20, color=None):
    """Draws notification bell icon centered at (cx, cy)."""
    if color is None:
        color = VIVID_RED
    l = PangoCairo.create_layout(ctx)
    l.set_font_description(Pango.FontDescription(f"JetBrains Mono Nerd Font Bold {font_size}"))
    l.set_markup(f"<span color='{color}'>󰂚</span>", -1)
    ink, log = l.get_pixel_extents()
    ctx.move_to(cx - ink.x - ink.width / 2.0, cy - ink.y - ink.height / 2.0)
    PangoCairo.show_layout(ctx, l)
