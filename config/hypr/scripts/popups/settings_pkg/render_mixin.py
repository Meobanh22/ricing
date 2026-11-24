#!/usr/bin/env python3
# settings_pkg/render_mixin.py — Clamshell casing, animation frames, and screen drawing for Settings.

import math

import cairo
from gi.repository import Pango, PangoCairo

from settings_pkg.constants import (
    COLOR_BORDER_SHADOW,
    COLOR_PINK_BOT,
    COLOR_PINK_INSIDE,
    COLOR_PINK_ROSE,
    COLOR_PINK_TOP,
    COLOR_RIBBON_BOT,
    COLOR_RIBBON_MID,
    COLOR_RIBBON_TOP,
    C_ACCENT,
    C_BG_CARD,
    C_BG_CARD_HOVER,
    C_BG_WIN,
    C_BORDER_3D,
    C_STATUS_WARN,
    C_TEXT_MUT,
    C_TEXT_PRI,
    C_TEXT_SEC,
    OPEN_H,
    OPEN_W,
    hex_to_rgba,
)
from settings_pkg.shapes import draw_ribbon_bow, front_cover_path, left_panel_path, right_panel_path
from ui_core import clear_surface, squircle


class SettingsRenderMixin:
    """Cairo surface caching, clamshell flip animation, and sub-screen rendering."""

    def on_draw(self, widget, cr):
        clear_surface(cr)
        alloc = widget.get_allocation()
        win_w, win_h = float(alloc.width), float(alloc.height)

        if self.anim_state == "closed" or self.open_progress <= 0.01:
            self.draw_closed_state(cr, win_w, win_h)
        elif self.anim_state == "open" or self.open_progress >= 0.99:
            self.draw_open_state(cr, win_w, win_h)
        else:
            self.draw_transition_state(cr, win_w, win_h)
        return False

    def draw_small_hinge(self, cr, x_center, y_pos, hw=24.0, hh=80.0, alpha=1.0):
        if alpha <= 0.001:
            return
        cr.save()
        hx = x_center - hw / 2.0
        squircle(cr, hx, y_pos, hw, hh, 5.5)
        pat_h = cairo.LinearGradient(hx, y_pos, hx + hw, y_pos)
        pat_h.add_color_stop_rgba(0.0, 0.12, 0.06, 0.08, alpha)
        pat_h.add_color_stop_rgba(0.35, 0.38, 0.26, 0.30, alpha)
        pat_h.add_color_stop_rgba(0.65, 0.58, 0.44, 0.48, alpha)
        pat_h.add_color_stop_rgba(1.0, 0.12, 0.06, 0.08, alpha)
        cr.set_source(pat_h)
        cr.fill_preserve()
        cr.set_source_rgba(COLOR_BORDER_SHADOW[0], COLOR_BORDER_SHADOW[1], COLOR_BORDER_SHADOW[2], COLOR_BORDER_SHADOW[3] * alpha)
        cr.set_line_width(1.8)
        cr.stroke()
        cr.rectangle(hx, y_pos + hh / 2.0 - 1.2, hw, 2.4)
        cr.set_source_rgba(0.06, 0.02, 0.04, 0.95 * alpha)
        cr.fill()
        cr.restore()

    def draw_small_hinges(self, cr, cx, top_y, bot_y, alpha=1.0):
        if alpha <= 0.001:
            return
        self.draw_small_hinge(cr, cx, top_y + 4.0, hw=24.0, hh=80.0, alpha=alpha)
        self.draw_small_hinge(cr, cx, bot_y - 4.0 - 80.0, hw=24.0, hh=80.0, alpha=alpha)

    def draw_front_cover(self, cr, x, y, w, h):
        r, r_inner = 22.0, 18.0
        cx_mid = x + w / 2.0
        sr, sg, sb = COLOR_PINK_ROSE[0], COLOR_PINK_ROSE[1], COLOR_PINK_ROSE[2]

        cr.save()
        front_cover_path(cr, x, y, w, h, r, r_inner)
        pat_base = cairo.LinearGradient(cx_mid, y, cx_mid, y + h)
        pat_base.add_color_stop_rgba(0.00, *COLOR_PINK_TOP)
        pat_base.add_color_stop_rgba(1.00, *COLOR_PINK_BOT)
        cr.set_source(pat_base)
        cr.fill_preserve()
        cr.clip()

        pat_x = cairo.LinearGradient(x, y, x + w, y)
        for stop, rgba in (
            (0.00, (sr, sg, sb, 0.14)),
            (0.08, (0.0, 0.0, 0.0, 0.00)),
            (0.32, (1.0, 1.0, 1.0, 0.16)),
            (0.48, (1.0, 1.0, 1.0, 0.07)),
            (0.70, (0.0, 0.0, 0.0, 0.00)),
            (0.86, (sr, sg, sb, 0.16)),
            (1.00, (sr, sg, sb, 0.32)),
        ):
            pat_x.add_color_stop_rgba(stop, *rgba)
        cr.set_source(pat_x)
        cr.paint()

        pat_streak = cairo.LinearGradient(x + w * 0.82, y, x + w * 0.95, y)
        pat_streak.add_color_stop_rgba(0.00, 1.0, 1.0, 1.0, 0.00)
        pat_streak.add_color_stop_rgba(0.50, 1.0, 1.0, 1.0, 0.38)
        pat_streak.add_color_stop_rgba(1.00, 1.0, 1.0, 1.0, 0.00)
        cr.rectangle(x + w * 0.80, y, w * 0.20, h)
        cr.set_source(pat_streak)
        cr.fill()

        cr.save()
        cr.set_line_width(2.8)
        cr.arc(x + w - r, y + h - r, r - 3.2, 0.0, 0.5 * math.pi)
        pat_corner = cairo.LinearGradient(x + w - r, y + h, x + w, y + h - r)
        pat_corner.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.00)
        pat_corner.add_color_stop_rgba(0.5, 1.0, 1.0, 1.0, 0.45)
        pat_corner.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.00)
        cr.set_source(pat_corner)
        cr.stroke()
        cr.restore()

        pat_top = cairo.LinearGradient(cx_mid, y, cx_mid, y + 32.0)
        pat_top.add_color_stop_rgba(0.00, 1.0, 1.0, 1.0, 0.22)
        pat_top.add_color_stop_rgba(0.60, 1.0, 1.0, 1.0, 0.06)
        pat_top.add_color_stop_rgba(1.00, 1.0, 1.0, 1.0, 0.00)
        cr.rectangle(x, y, w, 32.0)
        cr.set_source(pat_top)
        cr.fill()

        pat_bot = cairo.LinearGradient(cx_mid, y + h - 38.0, cx_mid, y + h)
        pat_bot.add_color_stop_rgba(0.00, 0.0, 0.0, 0.0, 0.00)
        pat_bot.add_color_stop_rgba(0.80, sr, sg, sb, 0.18)
        pat_bot.add_color_stop_rgba(1.00, 1.00, 0.90, 0.95, 0.15)
        cr.rectangle(x, y + h - 38.0, w, 38.0)
        cr.set_source(pat_bot)
        cr.fill()

        x1, y1 = x, y + h / 2.0
        x2, y2 = x + w, y
        dx, dy = x2 - x1, y2 - y1
        dist, ang = math.hypot(dx, dy), math.atan2(dy, dx)
        rh = 34.0

        cr.save()
        cr.translate(x1, y1)
        cr.rotate(ang)
        cr.rectangle(-40.0, -rh / 2.0 + 3.0, dist + 80.0, rh + 2.0)
        cr.set_source_rgba(sr, sg, sb, 0.26)
        cr.fill()
        cr.restore()

        cr.save()
        cr.translate(x1, y1)
        cr.rotate(ang)
        cr.rectangle(-40.0, -rh / 2.0, dist + 80.0, rh)
        pat_r = cairo.LinearGradient(0, -rh / 2.0, 0, rh / 2.0)
        pat_r.add_color_stop_rgba(0.0, *COLOR_RIBBON_TOP)
        pat_r.add_color_stop_rgba(0.5, *COLOR_RIBBON_MID)
        pat_r.add_color_stop_rgba(1.0, *COLOR_RIBBON_BOT)
        cr.set_source(pat_r)
        cr.fill_preserve()
        cr.set_source_rgba(*COLOR_BORDER_SHADOW)
        cr.set_line_width(2.2)
        cr.stroke()

        for ey in (-rh / 2.0, rh / 2.0):
            cr.move_to(-40.0, ey + (1.2 if ey < 0 else -1.2))
            cr.line_to(dist + 80.0, ey + (1.2 if ey < 0 else -1.2))
            cr.set_source_rgba(1.0, 0.88, 0.65, 0.50)
            cr.set_line_width(1.0)
            cr.stroke()

        pat_r_curv = cairo.LinearGradient(dist * 0.25, 0, dist * 0.65, 0)
        pat_r_curv.add_color_stop_rgba(0.00, 1.0, 1.0, 1.0, 0.00)
        pat_r_curv.add_color_stop_rgba(0.40, 1.0, 1.0, 1.0, 0.16)
        pat_r_curv.add_color_stop_rgba(0.70, 1.0, 1.0, 1.0, 0.00)
        cr.rectangle(-40.0, -rh / 2.0, dist + 80.0, rh)
        cr.set_source(pat_r_curv)
        cr.fill()
        cr.restore()

        bx, by = x1 + dx * 0.50, y1 + dy * 0.50
        cr.save()
        cr.translate(1.5, 2.5)
        draw_ribbon_bow(cr, bx, by, ribbon_ang=ang, scale=1.0)
        cr.set_source_rgba(sr, sg, sb, 0.25)
        cr.fill()
        cr.restore()
        draw_ribbon_bow(cr, bx, by, ribbon_ang=ang, scale=1.0)

        cr.rectangle(x + w - 5.0, y + 220.0, 5.0, 48.0)
        cr.set_source_rgba(0.20, 0.04, 0.08, 0.85)
        cr.fill()
        cr.restore()

        cr.save()
        cr.set_line_width(1.6)
        right_panel_path(cr, x + 1.8, y + 1.8, w - 3.6, h - 3.6, max(2.0, r - 1.8), max(2.0, r_inner - 1.8))
        pat_inner = cairo.LinearGradient(x, y, x + w, y + h)
        pat_inner.add_color_stop_rgba(0.00, 1.0, 1.0, 1.0, 0.40)
        pat_inner.add_color_stop_rgba(0.45, 1.0, 0.95, 0.98, 0.20)
        pat_inner.add_color_stop_rgba(0.75, sr, sg, sb, 0.12)
        pat_inner.add_color_stop_rgba(1.00, sr, sg, sb, 0.24)
        cr.set_source(pat_inner)
        cr.stroke()
        cr.restore()

        cr.save()
        front_cover_path(cr, x, y, w, h, r, r_inner)
        cr.set_source_rgba(*COLOR_BORDER_SHADOW)
        cr.set_line_width(2.4)
        cr.stroke()
        cr.restore()

    def _draw_panel_casing(self, cr, path_fn, px, top_y, panel_w, panel_h, corner_r, r_inner, left_wall_x, right_wall_x):
        bot_y = top_y + panel_h
        t_wall = 9.5

        cr.save()
        path_fn(cr, px, top_y, panel_w, panel_h, corner_r, r_inner)
        cr.set_source_rgba(*COLOR_PINK_INSIDE)
        cr.fill()
        cr.restore()

        cr.save()
        path_fn(cr, px, top_y, panel_w, panel_h, corner_r, r_inner)
        cr.clip()
        for wall_x, edge_x in ((left_wall_x, left_wall_x + t_wall), (right_wall_x, right_wall_x)):
            cr.rectangle(wall_x, top_y, t_wall, panel_h)
            cr.set_source_rgba(*hex_to_rgba(C_BG_CARD, 1.0))
            cr.fill()
            cr.move_to(edge_x, top_y)
            cr.line_to(edge_x, bot_y)
            cr.set_source_rgba(*hex_to_rgba(C_BG_WIN, 0.85))
            cr.set_line_width(1.0)
            cr.stroke()
        cr.restore()

        cr.save()
        path_fn(cr, px, top_y, panel_w, panel_h, corner_r, r_inner)
        cr.set_source_rgba(*COLOR_BORDER_SHADOW)
        cr.set_line_width(2.0)
        cr.stroke()
        cr.restore()

    def draw_left_panel_casing(self, cr, lx, top_y, panel_w, panel_h, corner_r=22.0, r_inner=18.0):
        t_wall = 9.5
        self._draw_panel_casing(cr, left_panel_path, lx, top_y, panel_w, panel_h, corner_r, r_inner, lx, lx + panel_w - 1.0 - t_wall)

    def draw_right_panel_casing(self, cr, rx, top_y, panel_w, panel_h, corner_r=22.0, r_inner=18.0):
        t_wall = 9.5
        self._draw_panel_casing(cr, right_panel_path, rx, top_y, panel_w, panel_h, corner_r, r_inner, rx + 1.0, rx + panel_w - t_wall)

    def _draw_panel_extrusion(self, cr, path_fn, px, top_y, panel_w, panel_h, corner_r, r_inner, extrusion_h, steps):
        cr.save()
        path_fn(cr, px, top_y + extrusion_h + 5.0, panel_w, panel_h, corner_r, r_inner)
        cr.set_source_rgba(0.08, 0.02, 0.04, 0.35)
        cr.fill()
        cr.restore()

        for s in range(steps + 1):
            dy = extrusion_h * (s / steps)
            cr.save()
            path_fn(cr, px, top_y + dy, panel_w, panel_h, corner_r, r_inner)
            cr.set_source_rgba(*hex_to_rgba(C_BORDER_3D, 0.98))
            cr.fill()
            cr.restore()

        cr.save()
        path_fn(cr, px, top_y + extrusion_h, panel_w, panel_h, corner_r, r_inner)
        cr.set_source_rgba(*hex_to_rgba(C_BORDER_3D, 0.98))
        cr.set_line_width(1.8)
        cr.stroke()
        cr.restore()

    def render_closed_cover_full(self, cr, cx, panel_w, panel_h, top_y, corner_r, r_inner, extrusion_h, steps):
        self._draw_panel_extrusion(cr, front_cover_path, cx, top_y, panel_w, panel_h, corner_r, r_inner, extrusion_h, steps)
        self.draw_front_cover(cr, cx, top_y, panel_w, panel_h)

    def render_right_panel_full(self, cr, cx, panel_w, panel_h, top_y, corner_r, r_inner, extrusion_h, steps):
        rx = cx
        self._draw_panel_extrusion(cr, right_panel_path, rx, top_y, panel_w, panel_h, corner_r, r_inner, extrusion_h, steps)
        self.draw_right_panel_casing(cr, rx, top_y, panel_w, panel_h, corner_r, r_inner)

        pad_outer, pad_inner, pad_top, pad_bot = 27.0, 27.0, 36.0, 62.0
        rsx, rsy = rx + pad_inner, top_y + pad_top
        rsw, rsh = panel_w - pad_outer - pad_inner, panel_h - pad_top - pad_bot
        self.draw_right_screen(cr, rsx, rsy, rsw, rsh)
        self.draw_heart_button(cr, rsx + rsw / 2.0 - 28.0, rsy + rsh + pad_bot * 0.50 - 23.0, 56.0, 46.0)

    def render_left_panel_full(self, cr, cx, panel_w, panel_h, top_y, corner_r, r_inner, extrusion_h, steps):
        lx = cx - panel_w
        self._draw_panel_extrusion(cr, left_panel_path, lx, top_y, panel_w, panel_h, corner_r, r_inner, extrusion_h, steps)
        self.draw_left_panel_casing(cr, lx, top_y, panel_w, panel_h, corner_r, r_inner)

        pad_outer, pad_inner, pad_top, pad_bot = 27.0, 27.0, 36.0, 62.0
        self.draw_left_screen(cr, lx + pad_outer, top_y + pad_top, panel_w - pad_outer - pad_inner, panel_h - pad_top - pad_bot)

    def _ensure_caches(self):
        if (
            getattr(self, "_cache_front_cover", None) is not None
            and getattr(self, "_cache_right_panel", None) is not None
            and getattr(self, "_cache_left_panel", None) is not None
        ):
            return

        cx = OPEN_W / 2.0
        panel_w = cx - 33.0
        panel_h, top_y, corner_r, r_inner, extrusion_h, steps = 585.0, 30.0, 22.0, 18.0, 4.2, 14

        for attr, render_fn in (
            ("_cache_front_cover", self.render_closed_cover_full),
            ("_cache_right_panel", self.render_right_panel_full),
            ("_cache_left_panel", self.render_left_panel_full),
        ):
            surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, OPEN_W, OPEN_H)
            render_fn(cairo.Context(surf), cx, panel_w, panel_h, top_y, corner_r, r_inner, extrusion_h, steps)
            setattr(self, attr, surf)

    def draw_closed_state(self, cr, win_w, win_h):
        self._ensure_caches()
        cr.save()
        cr.set_source_surface(self._cache_front_cover, 0, 0)
        cr.paint()
        cr.restore()

    def draw_open_state(self, cr, win_w, win_h):
        self._ensure_caches()
        cx = win_w / 2.0
        top_y = 30.0
        bot_y = top_y + 585.0

        cr.save()
        cr.set_source_surface(self._cache_left_panel, 0, 0)
        cr.paint()
        cr.set_source_surface(self._cache_right_panel, 0, 0)
        cr.paint()
        cr.restore()

        cr.save()
        cr.rectangle(cx - 1.0, top_y, 2.0, 585.0)
        cr.set_source_rgba(*hex_to_rgba(C_BG_WIN, 1.0))
        cr.fill()
        cr.restore()

        self.draw_small_hinges(cr, cx, top_y, bot_y, alpha=1.0)

    def draw_transition_state(self, cr, win_w, win_h):
        self._ensure_caches()
        p = max(0.0, min(1.0, self.open_progress))
        cx = win_w / 2.0
        panel_w = cx - 33.0
        panel_h, top_y, corner_r, r_inner, extrusion_h = 585.0, 30.0, 22.0, 18.0, 4.2
        bot_y = top_y + panel_h
        lx = cx - panel_w

        cr.save()
        cr.set_source_surface(self._cache_right_panel, 0, 0)
        cr.paint()
        cr.restore()

        theta = p * math.pi
        cos_t, sin_t = math.cos(theta), math.sin(theta)

        if p > 0.35:
            shadow_w = panel_w * max(0.0, -cos_t)
            if shadow_w > 2.0:
                cr.save()
                cr.rectangle(cx - shadow_w, top_y + extrusion_h + 3.0, shadow_w, panel_h + 8.0)
                pat_lsh = cairo.LinearGradient(cx - shadow_w, top_y, cx, top_y)
                pat_lsh.add_color_stop_rgba(0.0, 0.08, 0.02, 0.04, 0.28 * max(0.0, -cos_t))
                pat_lsh.add_color_stop_rgba(1.0, 0.08, 0.02, 0.04, 0.05)
                cr.set_source(pat_lsh)
                cr.fill()
                cr.restore()

        if p < 0.5:
            cr.save()
            cr.translate(cx, 0)
            cr.scale(max(0.001, cos_t), 1.0)
            cr.translate(-cx, 0)
            cr.set_source_surface(self._cache_front_cover, 0, 0)
            cr.paint()
            if sin_t > 0.04:
                cr.save()
                front_cover_path(cr, cx, top_y, panel_w, panel_h, corner_r, r_inner)
                cr.set_source_rgba(0.05, 0.01, 0.03, 0.28 * sin_t)
                cr.fill()
                cr.restore()
            cr.restore()

            rim_w = 9.5 * sin_t
            if rim_w > 1.2:
                self._draw_vertical_rim(cr, cx, top_y, rim_w, panel_h, forward=True)
        else:
            rim_w = 9.5 * sin_t
            if rim_w > 1.2:
                self._draw_vertical_rim(cr, cx - rim_w, top_y, rim_w, panel_h, forward=False)

            cr.save()
            cr.translate(cx, 0)
            cr.scale(max(0.001, -cos_t), 1.0)
            cr.translate(-cx, 0)
            cr.set_source_surface(self._cache_left_panel, 0, 0)
            cr.paint()
            if sin_t > 0.04:
                cr.save()
                left_panel_path(cr, lx, top_y, panel_w, panel_h, corner_r, r_inner)
                cr.set_source_rgba(0.05, 0.01, 0.03, 0.28 * sin_t)
                cr.fill()
                cr.restore()
            cr.restore()

        if p >= 0.92:
            seam_alpha = min(1.0, (p - 0.92) / 0.08)
            cr.save()
            cr.rectangle(cx - 1.0, top_y, 2.0, panel_h)
            cr.set_source_rgba(*hex_to_rgba(C_BG_WIN, seam_alpha))
            cr.fill()
            cr.restore()

        hinge_alpha = 0.0 if p < 0.40 else min(1.0, (p - 0.40) / 0.35)
        if hinge_alpha > 0.01:
            self.draw_small_hinges(cr, cx, top_y, bot_y, alpha=hinge_alpha)

    def _draw_vertical_rim(self, cr, x, top_y, rim_w, panel_h, forward=True):
        cr.save()
        cr.rectangle(x, top_y, rim_w, panel_h)
        pat_rim = cairo.LinearGradient(x, top_y, x + rim_w, top_y)
        if forward:
            pat_rim.add_color_stop_rgba(0.0, 0.15, 0.10, 0.12, 1.0)
            pat_rim.add_color_stop_rgba(0.5, 0.26, 0.19, 0.23, 1.0)
            pat_rim.add_color_stop_rgba(1.0, 0.12, 0.08, 0.10, 1.0)
        else:
            pat_rim.add_color_stop_rgba(0.0, 0.12, 0.08, 0.10, 1.0)
            pat_rim.add_color_stop_rgba(0.5, 0.26, 0.19, 0.23, 1.0)
            pat_rim.add_color_stop_rgba(1.0, 0.15, 0.10, 0.12, 1.0)
        cr.set_source(pat_rim)
        cr.fill()
        cr.restore()

    def _draw_screen_frame(self, cr, sx, sy, sw, sh):
        cr.save()
        squircle(cr, sx, sy, sw, sh, 14.0)
        cr.set_source_rgba(0.10, 0.04, 0.06, 0.98)
        cr.fill_preserve()
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.10)
        cr.set_line_width(1.2)
        cr.stroke()
        cr.restore()

    def draw_left_screen(self, cr, sx, sy, sw, sh):
        self._draw_screen_frame(cr, sx, sy, sw, sh)

    def draw_right_screen(self, cr, sx, sy, sw, sh):
        self._draw_screen_frame(cr, sx, sy, sw, sh)

    def draw_tile(self, cr, tx, ty, tw, th, icon, label, val, is_hover=False):
        cr.save()
        squircle(cr, tx, ty, tw, th, 8.0)
        cr.set_source_rgba(*hex_to_rgba(C_BG_CARD_HOVER if is_hover else C_BG_CARD, 0.98 if is_hover else 0.90))
        cr.fill_preserve()
        cr.set_source_rgba(*(hex_to_rgba(C_ACCENT, 0.65) if is_hover else (1.0, 1.0, 1.0, 0.12)))
        cr.set_line_width(1.0)
        cr.stroke()

        layout = PangoCairo.create_layout(cr)
        cr.set_source_rgba(*hex_to_rgba(C_ACCENT, 1.0))
        layout.set_text(icon)
        layout.set_font_description(Pango.FontDescription("Symbols Nerd Font 13"))
        cr.move_to(tx + 8.0, ty + 10.0)
        PangoCairo.show_layout(cr, layout)

        layout.set_font_description(Pango.FontDescription("Rubik Regular 8.5"))
        layout.set_text(label)
        cr.set_source_rgba(*hex_to_rgba(C_TEXT_SEC, 0.85))
        cr.move_to(tx + 28.0, ty + 10.0)
        PangoCairo.show_layout(cr, layout)

        layout.set_font_description(Pango.FontDescription("Rubik Bold 9"))
        layout.set_text(val)
        cr.set_source_rgba(*hex_to_rgba(C_TEXT_PRI, 1.0))
        cr.move_to(tx + 8.0, ty + 30.0)
        PangoCairo.show_layout(cr, layout)
        cr.restore()

    def draw_media_card(self, cr, mx, my, mw, mh):
        cr.save()
        squircle(cr, mx, my, mw, mh, 10.0)
        cr.set_source_rgba(*hex_to_rgba(C_BG_CARD, 0.70))
        cr.fill_preserve()
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.10)
        cr.set_line_width(1.0)
        cr.stroke()

        cr.set_source_rgba(*hex_to_rgba(C_ACCENT, 1.0))
        layout = PangoCairo.create_layout(cr)
        layout.set_font_description(Pango.FontDescription("Symbols Nerd Font 18"))
        layout.set_text("󰝚")
        cr.move_to(mx + 14.0, my + 14.0)
        PangoCairo.show_layout(cr, layout)

        layout.set_font_description(Pango.FontDescription("Rubik Bold 10"))
        title_str = self.media_title[:22] + ("…" if len(self.media_title) > 22 else "")
        layout.set_text(title_str if title_str else "No media playing")
        cr.set_source_rgba(*hex_to_rgba(C_TEXT_PRI, 1.0))
        cr.move_to(mx + 42.0, my + 14.0)
        PangoCairo.show_layout(cr, layout)

        layout.set_font_description(Pango.FontDescription("Rubik Regular 8.5"))
        layout.set_text(self.media_artist if self.media_artist else "Pokédex Audio")
        cr.set_source_rgba(*hex_to_rgba(C_TEXT_SEC, 0.75))
        cr.move_to(mx + 42.0, my + 32.0)
        PangoCairo.show_layout(cr, layout)

        cx = mx + mw / 2.0
        btn_y = my + 82.0
        cr.set_source_rgba(*hex_to_rgba(C_TEXT_SEC, 0.9))
        layout.set_font_description(Pango.FontDescription("Symbols Nerd Font 16"))
        layout.set_text("󰒮")
        cr.move_to(cx - 50.0, btn_y)
        PangoCairo.show_layout(cr, layout)

        cr.arc(cx, btn_y + 12.0, 16.0, 0, 2 * math.pi)
        cr.set_source_rgba(*hex_to_rgba(C_ACCENT, 1.0))
        cr.fill()

        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        layout.set_font_description(Pango.FontDescription("Symbols Nerd Font 14"))
        layout.set_text("󰏤" if self.media_status == "Playing" else "󰐊")
        cr.move_to(cx - 7.0, btn_y + 4.0)
        PangoCairo.show_layout(cr, layout)

        cr.set_source_rgba(*hex_to_rgba(C_TEXT_SEC, 0.9))
        layout.set_font_description(Pango.FontDescription("Symbols Nerd Font 16"))
        layout.set_text("󰒭")
        cr.move_to(cx + 34.0, btn_y)
        PangoCairo.show_layout(cr, layout)
        cr.restore()

    def draw_left_tabs(self, cr, bx, by, bw, bh):
        tabs = (("settings", " Settings"), ("map", "󰍦 Kalos Map"), ("guide", "󰋜 Guide"))
        tab_w = bw / 3.0
        for i, (tkey, tlabel) in enumerate(tabs):
            tx = bx + i * tab_w
            is_active = (self.left_tab == tkey)
            cr.save()
            squircle(cr, tx + 2.0, by, tab_w - 4.0, bh, 6.0)
            if is_active:
                cr.set_source_rgba(*hex_to_rgba(C_ACCENT, 0.35))
                cr.fill_preserve()
                cr.set_source_rgba(*hex_to_rgba(C_ACCENT, 0.8))
                cr.set_line_width(1.0)
                cr.stroke()
            else:
                cr.set_source_rgba(*hex_to_rgba(C_BG_CARD, 0.40))
                cr.fill()

            layout = PangoCairo.create_layout(cr)
            layout.set_font_description(Pango.FontDescription("Rubik Bold 8"))
            layout.set_text(tlabel)
            _, log = layout.get_pixel_extents()
            cr.move_to(tx + (tab_w - log.width) / 2.0, by + 5.0)
            cr.set_source_rgba(*hex_to_rgba(C_TEXT_PRI if is_active else C_TEXT_MUT, 1.0))
            PangoCairo.show_layout(cr, layout)
            cr.restore()

    def draw_controls_page(self, cr, sx, sy, sw, sh):
        layout = PangoCairo.create_layout(cr)
        layout.set_font_description(Pango.FontDescription("Rubik Bold 10"))
        layout.set_text("󰐥 CONTROLS")
        cr.move_to(sx + 14.0, sy + 14.0)
        cr.set_source_rgba(*hex_to_rgba(C_ACCENT, 1.0))
        PangoCairo.show_layout(cr, layout)

        cr.set_source_rgba(*hex_to_rgba(C_ACCENT if self.notifications else C_TEXT_MUT, 1.0))
        layout.set_font_description(Pango.FontDescription("Symbols Nerd Font 13"))
        layout.set_text("󰂚")
        cr.move_to(sx + sw - 30.0, sy + 12.0)
        PangoCairo.show_layout(cr, layout)

        if self.notifications:
            cr.arc(sx + sw - 14.0, sy + 14.0, 7.0, 0, 2 * math.pi)
            cr.set_source_rgba(*hex_to_rgba(C_ACCENT, 1.0))
            cr.fill()
            layout.set_font_description(Pango.FontDescription("Rubik Bold 7"))
            layout.set_text(str(min(9, len(self.notifications))))
            cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
            cr.move_to(sx + sw - 17.0, sy + 9.0)
            PangoCairo.show_layout(cr, layout)

        cx, cy, r_arc = sx + sw / 2.0, sy + 155.0, 68.0
        cr.set_line_cap(cairo.LINE_CAP_ROUND)

        for val, start_m, color_hex in ((self.volume, 1.15, C_ACCENT), (self.brightness, 0.15, C_STATUS_WARN)):
            cr.arc(cx, cy, r_arc, math.pi * start_m, math.pi * (start_m + 0.70))
            cr.set_source_rgba(*hex_to_rgba(C_BG_CARD_HOVER, 0.90))
            cr.set_line_width(10.0)
            cr.stroke()

            prog = min(1.0, max(0.0, val / 100.0))
            if prog > 0:
                cr.arc(cx, cy, r_arc, math.pi * start_m, math.pi * start_m + (math.pi * 0.70) * prog)
                cr.set_source_rgba(*hex_to_rgba(color_hex, 1.0))
                cr.set_line_width(10.0)
                cr.stroke()

            ang = math.pi * start_m + (math.pi * 0.70) * prog
            cr.arc(cx + r_arc * math.cos(ang), cy + r_arc * math.sin(ang), 8.0, 0, 2 * math.pi)
            cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
            cr.fill_preserve()
            cr.set_source_rgba(*hex_to_rgba(color_hex, 1.0))
            cr.set_line_width(2.0)
            cr.stroke()

        layout.set_font_description(Pango.FontDescription("Symbols Nerd Font 12"))
        layout.set_text("󰕿" if self.volume < 30 else ("󰖀" if self.volume < 70 else "󰕾"))
        cr.set_source_rgba(*hex_to_rgba(C_TEXT_SEC, 1.0))
        cr.move_to(cx - 36.0, cy - 36.0)
        PangoCairo.show_layout(cr, layout)
        layout.set_font_description(Pango.FontDescription("Rubik Bold 9"))
        layout.set_text(f"{self.volume}%")
        cr.move_to(cx - 36.0, cy - 20.0)
        PangoCairo.show_layout(cr, layout)

        layout.set_font_description(Pango.FontDescription("Symbols Nerd Font 12"))
        layout.set_text("󰃠")
        cr.set_source_rgba(*hex_to_rgba(C_TEXT_SEC, 1.0))
        cr.move_to(cx - 36.0, cy + 20.0)
        PangoCairo.show_layout(cr, layout)
        layout.set_font_description(Pango.FontDescription("Rubik Bold 9"))
        layout.set_text(f"{self.brightness}%")
        cr.move_to(cx - 36.0, cy + 34.0)
        PangoCairo.show_layout(cr, layout)

        cr.arc(cx, cy, 26.0, 0, 2 * math.pi)
        cr.set_source_rgba(*hex_to_rgba(C_BG_CARD, 1.0))
        cr.fill_preserve()
        cr.set_source_rgba(*hex_to_rgba(C_ACCENT, 0.8))
        cr.set_line_width(2.0)
        cr.stroke()

        layout.set_font_description(Pango.FontDescription("Symbols Nerd Font 16"))
        layout.set_text("󰐥")
        cr.set_source_rgba(*hex_to_rgba(C_ACCENT, 1.0))
        cr.move_to(cx - 9.0, cy - 13.0)
        PangoCairo.show_layout(cr, layout)

        pill_y = sy + sh - 48.0
        squircle(cr, sx + 14.0, pill_y, sw - 28.0, 34.0, 8.0)
        cr.set_source_rgba(*hex_to_rgba(C_BG_CARD, 0.60))
        cr.fill_preserve()
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.08)
        cr.set_line_width(1.0)
        cr.stroke()

        layout.set_font_description(Pango.FontDescription("Rubik Regular 8.5"))
        layout.set_text(f"Vol: {self.volume}%  ·  Bri: {self.brightness}%  ·  {self.power_mode.capitalize()}")
        _, log = layout.get_pixel_extents()
        cr.set_source_rgba(*hex_to_rgba(C_TEXT_SEC, 0.9))
        cr.move_to(sx + (sw - log.width) / 2.0, pill_y + 9.0)
        PangoCairo.show_layout(cr, layout)

    def draw_notifications_page(self, cr, sx, sy, sw, sh):
        layout = PangoCairo.create_layout(cr)
        layout.set_font_description(Pango.FontDescription("Rubik Bold 10"))
        layout.set_text("󰂚 NOTIFICATIONS")
        cr.move_to(sx + 14.0, sy + 14.0)
        cr.set_source_rgba(*hex_to_rgba(C_ACCENT, 1.0))
        PangoCairo.show_layout(cr, layout)

        layout.set_font_description(Pango.FontDescription("Symbols Nerd Font 12"))
        layout.set_text(" Back")
        cr.set_source_rgba(*hex_to_rgba(C_TEXT_SEC, 0.9))
        cr.move_to(sx + sw - 60.0, sy + 14.0)
        PangoCairo.show_layout(cr, layout)

        list_y, item_h, gap = sy + 44.0, 56.0, 8.0
        if not self.notifications:
            layout.set_font_description(Pango.FontDescription("Rubik Regular 10"))
            layout.set_text("No notifications")
            cr.set_source_rgba(*hex_to_rgba(C_TEXT_MUT, 0.7))
            cr.move_to(sx + (sw - 100.0) / 2.0, sy + sh / 2.0)
            PangoCairo.show_layout(cr, layout)
        else:
            for i, notif in enumerate(self.notifications[:4]):
                ny = list_y + i * (item_h + gap)
                squircle(cr, sx + 10.0, ny, sw - 20.0, item_h, 8.0)
                cr.set_source_rgba(*hex_to_rgba(C_BG_CARD, 0.85))
                cr.fill_preserve()
                cr.set_source_rgba(1.0, 1.0, 1.0, 0.10)
                cr.set_line_width(1.0)
                cr.stroke()

                for font_str, txt, col_hex, alpha, dy in (
                    ("Rubik Bold 8.5", notif.get("app_name", "System"), C_ACCENT, 1.0, 8.0),
                    ("Rubik Regular 9", notif.get("summary", "")[:24], C_TEXT_PRI, 1.0, 24.0),
                    ("Rubik Regular 8", notif.get("body", "")[:28], C_TEXT_SEC, 0.75, 38.0),
                ):
                    layout.set_font_description(Pango.FontDescription(font_str))
                    layout.set_text(txt)
                    cr.set_source_rgba(*hex_to_rgba(col_hex, alpha))
                    cr.move_to(sx + 18.0, ny + dy)
                    PangoCairo.show_layout(cr, layout)

        cy = sy + sh - 36.0
        squircle(cr, sx + 14.0, cy, sw - 28.0, 28.0, 6.0)
        cr.set_source_rgba(*hex_to_rgba(C_BG_CARD, 0.90))
        cr.fill_preserve()
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.12)
        cr.set_line_width(1.0)
        cr.stroke()

        layout.set_font_description(Pango.FontDescription("Rubik Bold 8.5"))
        layout.set_text("󰃢 Clear All Notifications")
        _, log = layout.get_pixel_extents()
        cr.set_source_rgba(*hex_to_rgba(C_TEXT_PRI, 0.9))
        cr.move_to(sx + (sw - log.width) / 2.0, cy + 6.0)
        PangoCairo.show_layout(cr, layout)

    def draw_heart_button(self, cr, hx, hy, hw=56.0, hh=46.0):
        cx, cy, scale = hx + hw / 2.0, hy + hh / 2.0, 1.30
        cr.save()
        cr.translate(cx, cy + 4.0)
        cr.scale(scale, scale)
        cr.new_sub_path()
        cr.move_to(0, 14.0)
        cr.curve_to(-19.0, 3.0, -23.0, -7.0, -17.5, -17.0)
        cr.curve_to(-12.5, -23.0, -3.0, -22.0, 0, -12.5)
        cr.curve_to(3.0, -22.0, 12.5, -23.0, 17.5, -17.0)
        cr.curve_to(23.0, -7.0, 19.0, 3.0, 0, 14.0)
        cr.close_path()
        cr.set_source_rgba(*hex_to_rgba(C_ACCENT, 1.0))
        cr.fill_preserve()
        cr.set_source_rgba(COLOR_BORDER_SHADOW[0], COLOR_BORDER_SHADOW[1], COLOR_BORDER_SHADOW[2], 0.95)
        cr.set_line_width(1.6 / scale)
        cr.stroke()
        cr.restore()
