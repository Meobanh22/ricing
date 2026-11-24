#!/usr/bin/env python3
# control_center_pkg/shapes.py — Pure Cairo casing paths, dual slider, and notification helpers.

import math
import time

import cairo
from gi.repository import Pango, PangoCairo

from control_center_pkg.constants import C_ACCENT, C_BG_WIN, hex_to_rgba


def create_top_red_casing_path(cr, x_left, x_right, y_dark_top, cx, cy_top, r_dark, ang_dark_top_start, ang_dark_top_end, x_dark_cut, device_r, notch_d=2.0, trans=1.8, y_top=0.0):
    y_tl1_t, y_tl1_b = 48.0, 52.0
    y_tl2_t, y_tl2_b = 96.0, 100.0

    x_orig_l = x_left - y_top
    x_orig_r = x_right + y_top
    x_t1_l, x_t1_r = x_orig_l + 48.0, x_orig_l + 52.0
    x_t2_l, x_t2_r = x_orig_l + 96.0, x_orig_l + 100.0
    x_tr2_l, x_tr2_r = x_orig_r - 100.0, x_orig_r - 96.0
    x_tr1_l, x_tr1_r = x_orig_r - 52.0, x_orig_r - 48.0

    cr.new_sub_path()
    cr.move_to(x_left, y_dark_top)
    cr.line_to(x_left, y_tl2_b + trans)
    cr.curve_to(x_left, y_tl2_b + trans * 0.5, x_left + notch_d, y_tl2_b + trans * 0.5, x_left + notch_d, y_tl2_b)
    cr.line_to(x_left + notch_d, y_tl2_t)
    cr.curve_to(x_left + notch_d, y_tl2_t - trans * 0.5, x_left, y_tl2_t - trans * 0.5, x_left, y_tl2_t - trans)

    cr.line_to(x_left, y_tl1_b + trans)
    cr.curve_to(x_left, y_tl1_b + trans * 0.5, x_left + notch_d, y_tl1_b + trans * 0.5, x_left + notch_d, y_tl1_b)
    cr.line_to(x_left + notch_d, y_tl1_t)
    cr.curve_to(x_left + notch_d, y_tl1_t - trans * 0.5, x_left, y_tl1_t - trans * 0.5, x_left, y_tl1_t - trans)

    cr.line_to(x_left, y_top + device_r)
    cr.arc(x_left + device_r, y_top + device_r, device_r, math.pi, 1.5 * math.pi)

    for nl, nr in ((x_t1_l, x_t1_r), (x_t2_l, x_t2_r), (x_tr2_l, x_tr2_r), (x_tr1_l, x_tr1_r)):
        cr.line_to(nl - trans, y_top)
        cr.curve_to(nl - trans * 0.5, y_top, nl - trans * 0.5, y_top + notch_d, nl, y_top + notch_d)
        cr.line_to(nr, y_top + notch_d)
        cr.curve_to(nr + trans * 0.5, y_top + notch_d, nr + trans * 0.5, y_top, nr + trans, y_top)

    cr.line_to(x_right - device_r, y_top)
    cr.arc(x_right - device_r, y_top + device_r, device_r, 1.5 * math.pi, 2 * math.pi)

    cr.line_to(x_right, y_tl1_t - trans)
    cr.curve_to(x_right, y_tl1_t - trans * 0.5, x_right - notch_d, y_tl1_t - trans * 0.5, x_right - notch_d, y_tl1_t)
    cr.line_to(x_right - notch_d, y_tl1_b)
    cr.curve_to(x_right - notch_d, y_tl1_b + trans * 0.5, x_right, y_tl1_b + trans * 0.5, x_right, y_tl1_b + trans)

    cr.line_to(x_right, y_tl2_t - trans)
    cr.curve_to(x_right, y_tl2_t - trans * 0.5, x_right - notch_d, y_tl2_t - trans * 0.5, x_right - notch_d, y_tl2_t)
    cr.line_to(x_right - notch_d, y_tl2_b)
    cr.curve_to(x_right - notch_d, y_tl2_b + trans * 0.5, x_right, y_tl2_b + trans * 0.5, x_right, y_tl2_b + trans)

    cr.line_to(x_right, y_dark_top)
    cr.line_to(cx + x_dark_cut, y_dark_top)
    cr.arc_negative(cx, cy_top, r_dark, ang_dark_top_start, ang_dark_top_end)
    cr.line_to(x_left, y_dark_top)
    cr.close_path()


def create_bottom_red_casing_path(cr, x_left, x_right, y_dark_bot, H_canvas, cx, cy_bot, r_dark, ang_dark_bot_start, ang_dark_bot_end, x_dark_cut, device_r, notch_d=2.0, trans=1.8):
    y_bl1_b, y_bl1_t = H_canvas - 48.0, H_canvas - 52.0
    y_bl2_b, y_bl2_t = H_canvas - 96.0, H_canvas - 100.0

    cr.new_sub_path()
    cr.move_to(x_left, y_dark_bot)
    cr.line_to(x_left, y_bl2_t - trans)
    cr.curve_to(x_left, y_bl2_t - trans * 0.5, x_left + notch_d, y_bl2_t - trans * 0.5, x_left + notch_d, y_bl2_t)
    cr.line_to(x_left + notch_d, y_bl2_b)
    cr.curve_to(x_left + notch_d, y_bl2_b + trans * 0.5, x_left, y_bl2_b + trans * 0.5, x_left, y_bl2_b + trans)

    cr.line_to(x_left, y_bl1_t - trans)
    cr.curve_to(x_left, y_bl1_t - trans * 0.5, x_left + notch_d, y_bl1_t - trans * 0.5, x_left + notch_d, y_bl1_t)
    cr.line_to(x_left + notch_d, y_bl1_b)
    cr.curve_to(x_left + notch_d, y_bl1_b + trans * 0.5, x_left, y_bl1_b + trans * 0.5, x_left, y_bl1_b + trans)

    cr.line_to(x_left, H_canvas - device_r)
    cr.arc_negative(x_left + device_r, H_canvas - device_r, device_r, math.pi, 0.5 * math.pi)
    cr.line_to(x_right - device_r, H_canvas)
    cr.arc_negative(x_right - device_r, H_canvas - device_r, device_r, 0.5 * math.pi, 0)

    cr.line_to(x_right, y_bl1_b + trans)
    cr.curve_to(x_right, y_bl1_b + trans * 0.5, x_right - notch_d, y_bl1_b + trans * 0.5, x_right - notch_d, y_bl1_b)
    cr.line_to(x_right - notch_d, y_bl1_t)
    cr.curve_to(x_right - notch_d, y_bl1_t - trans * 0.5, x_right, y_bl1_t - trans * 0.5, x_right, y_bl1_t - trans)

    cr.line_to(x_right, y_bl2_b + trans)
    cr.curve_to(x_right, y_bl2_b + trans * 0.5, x_right - notch_d, y_bl2_b + trans * 0.5, x_right - notch_d, y_bl2_b)
    cr.line_to(x_right - notch_d, y_bl2_t)
    cr.curve_to(x_right - notch_d, y_bl2_t - trans * 0.5, x_right, y_bl2_t - trans * 0.5, x_right, y_bl2_t - trans)

    cr.line_to(x_right, y_dark_bot)
    cr.line_to(cx + x_dark_cut, y_dark_bot)
    cr.arc(cx, cy_bot, r_dark, ang_dark_bot_start, ang_dark_bot_end)
    cr.line_to(x_left, y_dark_bot)
    cr.close_path()


def draw_pokeball_dual_slider(cr, cx, cy, R=64.0, thickness=12.0, vol_val=0.35, bri_val=0.60, knob_style="round_knob", icon_color=None, accent_rgb=None, dark_color=None, pwr_bg=None):
    if icon_color is None:
        icon_color = C_ACCENT
    if accent_rgb is None:
        accent_rgb = hex_to_rgba(C_ACCENT)[:3]
    if dark_color is None:
        dark_color = hex_to_rgba(C_BG_WIN)[:3]
    if pwr_bg is None:
        pwr_bg = hex_to_rgba(C_BG_WIN)[:3]
    gap_ang = math.radians(16.0)

    ang_vol_start = math.pi + gap_ang
    ang_vol_end = 2 * math.pi - gap_ang
    ang_vol_thumb = ang_vol_start + vol_val * (ang_vol_end - ang_vol_start)

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

    ang_bri_start = math.pi - gap_ang
    ang_bri_end = gap_ang
    ang_bri_thumb = ang_bri_start - bri_val * (math.pi - 2 * gap_ang)

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

    cr.save()
    cr.new_sub_path()
    cr.arc(cx, cy, r_btn_outer, 0, 2 * math.pi)
    cr.set_source_rgb(*pwr_bg)
    cr.fill_preserve()
    cr.set_source_rgba(0x3A / 255.0, 0x22 / 255.0, 0x2A / 255.0, 0.9)
    cr.set_line_width(1.5)
    cr.stroke()

    r_pwr = 7.0
    ang_gap = math.radians(35.0)
    cr.set_line_width(2.0)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.new_sub_path()
    cr.arc(cx, cy, r_pwr, -math.pi / 2.0 + ang_gap, 1.5 * math.pi - ang_gap)
    cr.set_source_rgb(*accent_rgb)
    cr.stroke()

    cr.new_sub_path()
    cr.move_to(cx, cy - r_pwr - 2.5)
    cr.line_to(cx, cy - 1.0)
    cr.stroke()
    cr.restore()

    cr.save()
    for glyph, x_pos, y_pos in (("󰕾", cx - 38.0, cy - 23.0), ("󰃠", cx - 38.0, cy + 23.0)):
        layout = PangoCairo.create_layout(cr)
        layout.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 13.5"))
        layout.set_markup(f"<span color='{icon_color}'>{glyph}</span>", -1)
        ink, _ = layout.get_pixel_extents()
        cr.move_to(x_pos - ink.x - ink.width / 2.0, y_pos - ink.y - ink.height / 2.0)
        PangoCairo.show_layout(cr, layout)
    cr.restore()


def format_relative_time(timestamp):
    if not timestamp:
        return "just now"
    diff = max(0, int(time.time() - timestamp))
    if diff < 60:
        return "just now"
    if diff < 3600:
        return f"{diff // 60}m ago"
    if diff < 86400:
        return f"{diff // 3600}h ago"
    return f"{diff // 86400}d ago"


def get_badge_info(app_name):
    app_lower = app_name.lower()
    if "discord" in app_lower:
        return "#5865F2", "󰙯"
    if "firefox" in app_lower or "browser" in app_lower:
        return "#FF7139", "󰈹"
    if "spotify" in app_lower or "music" in app_lower:
        return "#1ED760", "󰓇"
    if "steam" in app_lower:
        return "#1b2838", "󰓓"
    if "terminal" in app_lower or "alacritty" in app_lower or "kitty" in app_lower:
        return C_ACCENT, "󰆍"
    return C_ACCENT, "󰒓"
