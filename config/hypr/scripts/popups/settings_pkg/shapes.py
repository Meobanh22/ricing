#!/usr/bin/env python3
# settings_pkg/shapes.py — Clamshell panel paths and decorative ribbon bow renderer.

import math

import cairo

from settings_pkg.constants import (
    COLOR_BORDER_SHADOW,
    COLOR_RIBBON_BOT,
    COLOR_RIBBON_MID,
    COLOR_RIBBON_TOP,
)


def left_panel_path(cr, x, y, w, h, r=22.0, r_inner=18.0):
    """Left wing with outer corners rounded (r) and inner corners near hinges rounded (r_inner)."""
    cr.new_sub_path()
    cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    cr.line_to(x + w - r_inner, y)
    cr.arc(x + w - r_inner, y + r_inner, r_inner, 1.5 * math.pi, 2.0 * math.pi)
    cr.line_to(x + w, y + h - r_inner)
    cr.arc(x + w - r_inner, y + h - r_inner, r_inner, 0.0, 0.5 * math.pi)
    cr.line_to(x + r, y + h)
    cr.arc(x + r, y + h - r, r, 0.5 * math.pi, math.pi)
    cr.close_path()


def right_panel_path(cr, x, y, w, h, r=22.0, r_inner=18.0):
    """Right wing with inner corners near hinges rounded (r_inner) and outer corners rounded (r)."""
    cr.new_sub_path()
    cr.arc(x + r_inner, y + r_inner, r_inner, math.pi, 1.5 * math.pi)
    cr.line_to(x + w - r, y)
    cr.arc(x + w - r, y + r, r, 1.5 * math.pi, 2.0 * math.pi)
    cr.line_to(x + w, y + h - r)
    cr.arc(x + w - r, y + h - r, r, 0.0, 0.5 * math.pi)
    cr.line_to(x + r_inner, y + h)
    cr.arc(x + r_inner, y + h - r_inner, r_inner, 0.5 * math.pi, math.pi)
    cr.line_to(x, y + r_inner)
    cr.close_path()


def front_cover_path(cr, x, y, w, h, r=22.0, r_inner=18.0):
    """Front cover shell matching right_panel_path contour."""
    right_panel_path(cr, x, y, w, h, r, r_inner)


def ellipse_path(cr, cx, cy, rx, ry):
    k = 0.55228475
    kx, ky = k * rx, k * ry
    cr.new_sub_path()
    cr.move_to(cx + rx, cy)
    cr.curve_to(cx + rx, cy + ky, cx + kx, cy + ry, cx, cy + ry)
    cr.curve_to(cx - kx, cy + ry, cx - rx, cy + ky, cx - rx, cy)
    cr.curve_to(cx - rx, cy - ky, cx - kx, cy - ry, cx, cy - ry)
    cr.curve_to(cx + kx, cy - ry, cx + rx, cy - ky, cx + rx, cy)
    cr.close_path()


def draw_ribbon_bow(cr, bx, by, ribbon_ang=0.0, scale=1.0):
    """Render decorative ribbon bow symmetrically aligned with the ribbon axis."""
    cr.save()
    cr.translate(bx, by)
    if ribbon_ang != 0.0:
        cr.rotate(ribbon_ang)
    if scale != 1.0:
        cr.scale(scale, scale)

    wing_w, wing_h = 70.0, 35.0
    rx, ry = 18.0, 11.5

    # Left and right wings (mirrored across x=0)
    for sign in (-1.0, 1.0):
        cr.new_sub_path()
        cr.move_to(sign * rx * 0.65, -7.0)
        cr.curve_to(sign * 35.0, -wing_h * 0.95, sign * 55.0, -wing_h * 0.95, sign * (wing_w - 3.0), -wing_h * 0.72)
        cr.curve_to(sign * (wing_w + 1.5), -wing_h * 0.35, sign * (wing_w + 1.5), wing_h * 0.35, sign * (wing_w - 3.0), wing_h * 0.72)
        cr.curve_to(sign * 55.0, wing_h * 0.95, sign * 35.0, wing_h * 0.95, sign * rx * 0.65, 7.0)
        cr.close_path()

        pat = cairo.LinearGradient(sign * wing_w, -wing_h, sign * rx, wing_h)
        pat.add_color_stop_rgba(0.0, *COLOR_RIBBON_TOP)
        pat.add_color_stop_rgba(0.5, *COLOR_RIBBON_MID)
        pat.add_color_stop_rgba(1.0, *COLOR_RIBBON_BOT)
        cr.set_source(pat)
        cr.fill_preserve()
        cr.set_source_rgba(*COLOR_BORDER_SHADOW)
        cr.set_line_width(2.0)
        cr.stroke()

        cr.move_to(sign * rx * 0.65, 0)
        cr.curve_to(sign * 35.0, -wing_h * 0.25, sign * 55.0, -wing_h * 0.15, sign * wing_w * 0.70, 0)
        cr.set_source_rgba(*COLOR_BORDER_SHADOW)
        cr.set_line_width(1.3)
        cr.stroke()

    ellipse_path(cr, 0, 0, rx, ry)
    pat_knot = cairo.RadialGradient(-rx * 0.25, -ry * 0.35, 2.0, 0, 0, max(rx, ry))
    pat_knot.add_color_stop_rgb(0.0, 1.0, 0.45, 0.55)
    pat_knot.add_color_stop_rgba(0.35, *COLOR_RIBBON_TOP)
    pat_knot.add_color_stop_rgba(1.0, *COLOR_RIBBON_BOT)
    cr.set_source(pat_knot)
    cr.fill_preserve()
    cr.set_source_rgba(*COLOR_BORDER_SHADOW)
    cr.set_line_width(2.0)
    cr.stroke()

    for sign in (-1.0, 1.0):
        cr.move_to(sign * rx * 0.35, -ry * 0.70)
        cr.curve_to(sign * rx * 0.15, 0, sign * rx * 0.15, 0, sign * rx * 0.35, ry * 0.70)
        cr.set_source_rgba(*COLOR_BORDER_SHADOW)
        cr.set_line_width(1.1)
        cr.stroke()

    cr.restore()
