#!/usr/bin/env python3
# dual_slider.py — Pokéball dual circular slider rendering component.

import math
import cairo
import gi

gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo

try:
    from system.palette import hex_to_rgba, C_ACCENT, C_BG_WIN
except Exception:
    def hex_to_rgba(h, a=1.0):
        h = h.strip().lstrip('#')
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, float(a))
    C_ACCENT = "#DC1A36"
    C_BG_WIN = "#201011"


def draw_pokeball_dual_slider(
    cr: cairo.Context,
    cx: float,
    cy: float,
    R: float = 64.0,
    thickness: float = 12.0,
    vol_val: float = 0.35,
    bri_val: float = 0.60,
    knob_style: str = "round_knob",
    icon_color: str = None,
    accent_rgb = None,
    dark_color = None,
    pwr_bg = None
):
    """
    Renders the signature Serena Wine dual circular Pokéball control:
    - Top Arc: Volume slider (left -> top -> right)
    - Bottom Arc: Brightness slider (left -> bottom -> right)
    - Horizontal equatorial seams
    - Center tactile power button
    - Speaker and Sun icons in left cavities
    """
    if icon_color is None:
        icon_color = C_ACCENT
    if accent_rgb is None:
        accent_rgb = hex_to_rgba(C_ACCENT)[:3]
    if dark_color is None:
        dark_color = hex_to_rgba(C_BG_WIN)[:3]
    if pwr_bg is None:
        pwr_bg = hex_to_rgba(C_BG_WIN)[:3]

    gap_ang = math.radians(16.0)

    # 1. TOP ARC: VOLUME (Sweeps Left -> Top -> Right)
    ang_vol_start = math.pi + gap_ang
    ang_vol_end = 2 * math.pi - gap_ang
    ang_vol_span = ang_vol_end - ang_vol_start
    ang_vol_thumb = ang_vol_start + vol_val * ang_vol_span

    cr.save()
    cr.set_line_width(thickness)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.new_sub_path()
    cr.arc(cx, cy, R, ang_vol_start, ang_vol_end)
    cr.set_source_rgb(*dark_color)
    cr.stroke()

    if vol_val > 0.01:
        cr.new_sub_path()
        cr.arc(cx, cy, R, ang_vol_start, ang_vol_thumb)
        cr.set_source_rgb(*accent_rgb)
        cr.stroke()

    if knob_style == "round_knob":
        tx = cx + R * math.cos(ang_vol_thumb)
        ty = cy + R * math.sin(ang_vol_thumb)
        cr.new_path()
        cr.arc(tx, ty, thickness * 0.62, 0, 2 * math.pi)
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.fill_preserve()
        cr.set_source_rgb(*accent_rgb)
        cr.set_line_width(2.0)
        cr.stroke()
    cr.restore()

    # 2. BOTTOM ARC: BRIGHTNESS (Sweeps Left -> Bottom -> Right)
    ang_bri_start = math.pi - gap_ang
    ang_bri_end = gap_ang
    ang_bri_span = (math.pi - 2 * gap_ang)
    ang_bri_thumb = ang_bri_start - bri_val * ang_bri_span

    cr.save()
    cr.set_line_width(thickness)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.new_sub_path()
    cr.arc_negative(cx, cy, R, ang_bri_start, ang_bri_end)
    cr.set_source_rgb(*dark_color)
    cr.stroke()

    if bri_val > 0.01:
        cr.new_sub_path()
        cr.arc_negative(cx, cy, R, ang_bri_start, ang_bri_thumb)
        cr.set_source_rgb(*accent_rgb)
        cr.stroke()

    if knob_style == "round_knob":
        bx = cx + R * math.cos(ang_bri_thumb)
        by = cy + R * math.sin(ang_bri_thumb)
        cr.new_path()
        cr.arc(bx, by, thickness * 0.62, 0, 2 * math.pi)
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.fill_preserve()
        cr.set_source_rgb(*accent_rgb)
        cr.set_line_width(2.0)
        cr.stroke()
    cr.restore()

    # 3. HORIZONTAL EQUATORIAL SEAMS
    r_out = R + thickness / 2.0 + 3.0
    r_btn_outer = 22.0

    cr.save()
    cr.set_line_width(2.8)
    cr.set_source_rgb(*dark_color)
    cr.new_sub_path()
    cr.move_to(cx - r_out, cy)
    cr.line_to(cx - r_btn_outer, cy)
    cr.stroke()
    cr.new_sub_path()
    cr.move_to(cx + r_btn_outer, cy)
    cr.line_to(cx + r_out, cy)
    cr.stroke()
    cr.restore()

    # 4. CENTER POWER BUTTON (0.0px Offset, pure geometric vector)
    cr.save()
    cr.new_sub_path()
    cr.arc(cx, cy, r_btn_outer, 0, 2 * math.pi)
    cr.set_source_rgb(*pwr_bg)
    cr.fill_preserve()
    cr.set_source_rgba(0x3A/255.0, 0x22/255.0, 0x2A/255.0, 0.9)
    cr.set_line_width(1.5)
    cr.stroke()

    r_pwr = 7.0
    ang_gap = math.radians(35.0)
    ang_s = -math.pi / 2.0 + ang_gap
    ang_e = 1.5 * math.pi - ang_gap

    cr.set_line_width(2.0)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.new_sub_path()
    cr.arc(cx, cy, r_pwr, ang_s, ang_e)
    cr.set_source_rgb(*accent_rgb)
    cr.stroke()

    cr.new_sub_path()
    cr.move_to(cx, cy - r_pwr - 2.5)
    cr.line_to(cx, cy - 1.0)
    cr.stroke()
    cr.restore()

    # 5. ICONS NESTLED INSIDE THE LEFT CAVITY
    vx = cx - 38.0
    vy = cy - 23.0
    bx = cx - 38.0
    by = cy + 23.0

    cr.save()
    l_v = PangoCairo.create_layout(cr)
    l_v.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 13.5"))
    l_v.set_markup(f"<span color='{icon_color}'>󰕾</span>", -1)
    ink_v, log_v = l_v.get_pixel_extents()
    cr.move_to(vx - ink_v.x - ink_v.width / 2.0, vy - ink_v.y - ink_v.height / 2.0)
    PangoCairo.show_layout(cr, l_v)

    l_b = PangoCairo.create_layout(cr)
    l_b.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 13.5"))
    l_b.set_markup(f"<span color='{icon_color}'>󰃠</span>", -1)
    ink_b, log_b = l_b.get_pixel_extents()
    cr.move_to(bx - ink_b.x - ink_b.width / 2.0, by - ink_b.y - ink_b.height / 2.0)
    PangoCairo.show_layout(cr, l_b)
    cr.restore()
