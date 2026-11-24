#!/usr/bin/env python3
# control_center_pkg/render_mixin.py — Cairo baking and rendering pipeline for Control Center.

import math

import cairo
from gi.repository import Pango, PangoCairo

from control_center_pkg.constants import (
    C_ACCENT_HOVER,
    C_BG_WAYBAR,
    C_BG_WIN,
    C_BORDER_3D,
    C_STATUS_SUCC,
    C_TEXT_INV,
    C_TEXT_MUT,
    C_TEXT_PRI,
    C_TEXT_SEC,
    hex_to_rgba,
)
from control_center_pkg.shapes import (
    create_bottom_red_casing_path,
    create_top_red_casing_path,
    draw_pokeball_dual_slider,
    format_relative_time,
    get_badge_info,
)
from ui_core import (
    clear_surface,
    draw_anime_grooves,
    draw_bell_icon,
    draw_bow_mark,
    draw_curved_kerned_cached,
    draw_rounded_rect,
)


class ControlCenterRenderMixin:
    """Casing surface caching, page drawing, and GTK draw handler."""

    def get_dynamic_coords(self, p):
        cy_top = 390.0 - 200.0 * p
        cy_bot = 390.0 + 200.0 * p
        y_edge_top = cy_top - self.cut_y
        y_edge_bot = cy_bot + self.cut_y
        y_silver_top = y_edge_top - self.chassis_thick
        y_dark_top = y_silver_top - self.dark_thick
        y_silver_bot = y_edge_bot + self.chassis_thick
        y_dark_bot = y_silver_bot + self.dark_thick

        x_outer_cut = math.sqrt(self.r_outer**2 - self.cut_y**2)
        ang_outer_top_start = 2 * math.pi - math.asin(self.cut_y / self.r_outer)
        ang_outer_top_end = math.pi + math.asin(self.cut_y / self.r_outer)

        x_inner_cut = math.sqrt(self.r_inner**2 - self.cut_y**2)
        ang_inner_top_start = 2 * math.pi - math.asin(self.cut_y / self.r_inner)
        ang_inner_top_end = math.pi + math.asin(self.cut_y / self.r_inner)

        dy_chassis = abs(cy_top - y_silver_top)
        x_chassis_cut = math.sqrt(self.r_chassis**2 - dy_chassis**2)
        ang_chassis_top_start = 2 * math.pi - math.asin(dy_chassis / self.r_chassis)
        ang_chassis_top_end = math.pi + math.asin(dy_chassis / self.r_chassis)

        dy_dark = abs(cy_top - y_dark_top)
        x_dark_cut = math.sqrt(self.r_dark**2 - dy_dark**2)
        ang_dark_top_start = 2 * math.pi - math.asin(dy_dark / self.r_dark)
        ang_dark_top_end = math.pi + math.asin(dy_dark / self.r_dark)

        return {
            "cy_top": cy_top,
            "cy_bot": cy_bot,
            "y_edge_top": y_edge_top,
            "y_edge_bot": y_edge_bot,
            "y_silver_top": y_silver_top,
            "y_dark_top": y_dark_top,
            "y_silver_bot": y_silver_bot,
            "y_dark_bot": y_dark_bot,
            "x_outer_cut": x_outer_cut,
            "ang_outer_top_start": ang_outer_top_start,
            "ang_outer_top_end": ang_outer_top_end,
            "x_inner_cut": x_inner_cut,
            "ang_inner_top_start": ang_inner_top_start,
            "ang_inner_top_end": ang_inner_top_end,
            "x_chassis_cut": x_chassis_cut,
            "ang_chassis_top_start": ang_chassis_top_start,
            "ang_chassis_top_end": ang_chassis_top_end,
            "x_dark_cut": x_dark_cut,
            "ang_dark_top_start": ang_dark_top_start,
            "ang_dark_top_end": ang_dark_top_end,
            "ang_dark_bot_start": math.asin(dy_dark / self.r_dark),
            "ang_dark_bot_end": math.pi - math.asin(dy_dark / self.r_dark),
            "ang_chassis_bot_start": math.asin(dy_chassis / self.r_chassis),
            "ang_chassis_bot_end": math.pi - math.asin(dy_chassis / self.r_chassis),
            "ang_outer_bot_start": math.asin(self.cut_y / self.r_outer),
            "ang_outer_bot_end": math.pi - math.asin(self.cut_y / self.r_outer),
            "ang_inner_bot_start": math.asin(self.cut_y / self.r_inner),
            "ang_inner_bot_end": math.pi - math.asin(self.cut_y / self.r_inner),
            "top_casing_y": cy_top - 190.0,
            "bot_casing_y": cy_bot - 590.0,
        }

    def _bake_casings(self):
        W, H = int(self.base_w), int(self.base_h)
        geo0 = self.get_dynamic_coords(1.0)
        c_dark_r, c_dark_g, c_dark_b = self.c_flange
        prot, r_cuff = 2.5, 2.5

        top_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        tcr = cairo.Context(top_surf)
        tcr.set_antialias(cairo.ANTIALIAS_DEFAULT)
        y_dark_top_base = 190.0 - (self.cut_y + self.chassis_thick + self.dark_thick)

        create_top_red_casing_path(tcr, self.x_left, self.x_right, y_dark_top_base, self.cx, 190.0, self.r_dark, geo0["ang_dark_top_start"], geo0["ang_dark_top_end"], geo0["x_dark_cut"], self.device_r, notch_d=self.notch_d, trans=self.trans)
        red_pat = cairo.LinearGradient(self.x_left, 0, self.x_right, 0)
        red_pat.add_color_stop_rgb(0, *self.c_casing_l)
        red_pat.add_color_stop_rgb(0.5, *self.c_casing_m)
        red_pat.add_color_stop_rgb(1, *self.c_casing_r)
        tcr.set_source(red_pat)
        tcr.fill()

        draw_anime_grooves(tcr, self.x_left, 0, self.grooves, 0, 0.5 * math.pi)
        draw_anime_grooves(tcr, self.x_right, 0, self.grooves, 0.5 * math.pi, math.pi)

        create_top_red_casing_path(tcr, self.x_left, self.x_right, y_dark_top_base, self.cx, 190.0, self.r_dark, geo0["ang_dark_top_start"], geo0["ang_dark_top_end"], geo0["x_dark_cut"], self.device_r, notch_d=self.notch_d, trans=self.trans)
        tcr.set_source_rgba(*self.c_border_3d)
        tcr.set_line_width(2.0)
        tcr.stroke()

        create_top_red_casing_path(tcr, self.x_left + 1.6, self.x_right - 1.6, y_dark_top_base - 0.8, self.cx, 190.0, self.r_dark - 1.2, geo0["ang_dark_top_start"], geo0["ang_dark_top_end"], geo0["x_dark_cut"], max(4.0, self.device_r - 1.6), notch_d=self.notch_d, trans=self.trans, y_top=1.6)
        tcr.set_source_rgba(*self.c_tactile_white)
        tcr.set_line_width(1.3)
        tcr.stroke()

        tcr.new_sub_path()
        tcr.move_to(self.x_left, geo0["y_silver_top"])
        tcr.line_to(self.x_left, geo0["y_dark_top"])
        tcr.line_to(self.cx - geo0["x_dark_cut"], geo0["y_dark_top"])
        tcr.arc(self.cx, 190.0, self.r_dark, geo0["ang_dark_top_end"], geo0["ang_dark_top_start"])
        tcr.line_to(self.x_right, geo0["y_dark_top"])
        tcr.line_to(self.x_right, geo0["y_silver_top"])
        tcr.line_to(self.cx + geo0["x_chassis_cut"], geo0["y_silver_top"])
        tcr.arc_negative(self.cx, 190.0, self.r_chassis, geo0["ang_chassis_top_start"], geo0["ang_chassis_top_end"])
        tcr.close_path()
        tcr.set_source_rgba(c_dark_r, c_dark_g, c_dark_b, 0.85)
        tcr.fill()
        tcr.move_to(self.x_left, geo0["y_dark_top"])
        tcr.line_to(self.cx - geo0["x_dark_cut"], geo0["y_dark_top"])
        tcr.arc(self.cx, 190.0, self.r_dark, geo0["ang_dark_top_end"], geo0["ang_dark_top_start"])
        tcr.line_to(self.x_right, geo0["y_dark_top"])
        tcr.set_source_rgba(*self.c_border_3d)
        tcr.set_line_width(1.4)
        tcr.stroke()

        tcr.new_sub_path()
        tcr.move_to(self.x_left, geo0["y_edge_top"])
        tcr.arc(self.x_left, geo0["y_edge_top"] - r_cuff, r_cuff, 0.5 * math.pi, math.pi)
        tcr.line_to(self.x_left - prot, geo0["y_dark_top"] + r_cuff)
        tcr.arc(self.x_left, geo0["y_dark_top"] + r_cuff, r_cuff, math.pi, 1.5 * math.pi)
        tcr.line_to(self.x_left, geo0["y_silver_top"])
        tcr.line_to(self.cx - geo0["x_chassis_cut"], geo0["y_silver_top"])
        tcr.arc(self.cx, 190.0, self.r_chassis, geo0["ang_chassis_top_end"], geo0["ang_chassis_top_start"])
        tcr.line_to(self.x_right, geo0["y_silver_top"])
        tcr.line_to(self.x_right, geo0["y_dark_top"])
        tcr.arc(self.x_right, geo0["y_dark_top"] + r_cuff, r_cuff, 1.5 * math.pi, 2 * math.pi)
        tcr.line_to(self.x_right + prot, geo0["y_edge_top"] - r_cuff)
        tcr.arc(self.x_right, geo0["y_edge_top"] - r_cuff, r_cuff, 0, 0.5 * math.pi)
        tcr.line_to(self.cx + geo0["x_outer_cut"], geo0["y_edge_top"])
        tcr.arc_negative(self.cx, 190.0, self.r_outer, geo0["ang_outer_top_start"], geo0["ang_outer_top_end"])
        tcr.close_path()
        silver_pat_top = cairo.LinearGradient(self.x_left, geo0["y_dark_top"], self.x_left, geo0["y_edge_top"])
        silver_pat_top.add_color_stop_rgb(0.0, *hex_to_rgba(C_TEXT_PRI)[:3])
        silver_pat_top.add_color_stop_rgb(1.0, *hex_to_rgba(C_TEXT_SEC)[:3])
        tcr.set_source(silver_pat_top)
        tcr.fill_preserve()
        tcr.set_source_rgba(*self.c_border_3d)
        tcr.set_line_width(1.4)
        tcr.stroke()

        band_pat_top = cairo.LinearGradient(self.cx - self.r_outer, 190.0, self.cx + self.r_outer, 190.0)
        band_pat_top.add_color_stop_rgb(0, *self.c_band_stop0)
        band_pat_top.add_color_stop_rgb(0.5, *self.c_band_stop1)
        band_pat_top.add_color_stop_rgb(1, *self.c_band_stop2)
        tcr.new_sub_path()
        tcr.arc_negative(self.cx, 190.0, self.r_outer, geo0["ang_outer_top_start"], geo0["ang_outer_top_end"])
        tcr.line_to(self.cx - geo0["x_inner_cut"], geo0["y_edge_top"])
        tcr.arc(self.cx, 190.0, self.r_inner, geo0["ang_inner_top_end"], geo0["ang_inner_top_start"])
        tcr.close_path()
        tcr.set_source(band_pat_top)
        tcr.fill_preserve()
        tcr.set_source_rgba(*self.c_border_3d)
        tcr.set_line_width(1.6)
        tcr.stroke()
        tcr.arc(self.cx, 190.0, self.r_inner, geo0["ang_inner_top_end"], geo0["ang_inner_top_start"])
        tcr.set_source_rgba(0, 0, 0, 0.35)
        tcr.set_line_width(2.2)
        tcr.stroke()
        self._cached_top_casing = top_surf

        bot_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        bcr = cairo.Context(bot_surf)
        bcr.set_antialias(cairo.ANTIALIAS_DEFAULT)
        y_dark_bot_base = 590.0 + (self.cut_y + self.chassis_thick + self.dark_thick)
        for s in range(4):
            dy = 5.0 * (s / 3.0)
            bcr.save()
            bcr.translate(0, dy)
            create_bottom_red_casing_path(bcr, self.x_left, self.x_right, y_dark_bot_base, 780.0, self.cx, 590.0, self.r_dark, geo0["ang_dark_bot_start"], geo0["ang_dark_bot_end"], geo0["x_dark_cut"], self.device_r, notch_d=self.notch_d, trans=self.trans)
            bcr.set_source_rgba(*self.c_border_3d)
            bcr.fill()
            bcr.restore()
        create_bottom_red_casing_path(bcr, self.x_left, self.x_right, y_dark_bot_base, 780.0, self.cx, 590.0, self.r_dark, geo0["ang_dark_bot_start"], geo0["ang_dark_bot_end"], geo0["x_dark_cut"], self.device_r, notch_d=self.notch_d, trans=self.trans)
        red_pat_b = cairo.LinearGradient(self.x_left, 0, self.x_right, 0)
        red_pat_b.add_color_stop_rgb(0, *self.c_casing_l)
        red_pat_b.add_color_stop_rgb(0.5, *self.c_casing_m)
        red_pat_b.add_color_stop_rgb(1, *self.c_casing_r)
        bcr.set_source(red_pat_b)
        bcr.fill()
        draw_anime_grooves(bcr, self.x_left, 780.0, self.grooves, 1.5 * math.pi, 2 * math.pi)
        draw_anime_grooves(bcr, self.x_right, 780.0, self.grooves, math.pi, 1.5 * math.pi)
        create_bottom_red_casing_path(bcr, self.x_left, self.x_right, y_dark_bot_base, 780.0, self.cx, 590.0, self.r_dark, geo0["ang_dark_bot_start"], geo0["ang_dark_bot_end"], geo0["x_dark_cut"], self.device_r, notch_d=self.notch_d, trans=self.trans)
        bcr.set_source_rgba(*self.c_border_3d)
        bcr.set_line_width(2.0)
        bcr.stroke()
        create_bottom_red_casing_path(bcr, self.x_left + 1.6, self.x_right - 1.6, y_dark_bot_base + 0.8, 778.4, self.cx, 590.0, self.r_dark - 1.2, geo0["ang_dark_bot_start"], geo0["ang_dark_bot_end"], geo0["x_dark_cut"], max(4.0, self.device_r - 1.6), notch_d=self.notch_d, trans=self.trans)
        bcr.set_source_rgba(*self.c_tactile_white)
        bcr.set_line_width(1.3)
        bcr.stroke()
        bcr.new_sub_path()
        bcr.move_to(self.x_left, geo0["y_silver_bot"])
        bcr.line_to(self.x_left, geo0["y_dark_bot"])
        bcr.line_to(self.cx - geo0["x_dark_cut"], geo0["y_dark_bot"])
        bcr.arc_negative(self.cx, 590.0, self.r_dark, geo0["ang_dark_bot_end"], geo0["ang_dark_bot_start"])
        bcr.line_to(self.x_right, geo0["y_dark_bot"])
        bcr.line_to(self.x_right, geo0["y_silver_bot"])
        bcr.line_to(self.cx + geo0["x_chassis_cut"], geo0["y_silver_bot"])
        bcr.arc(self.cx, 590.0, self.r_chassis, geo0["ang_chassis_bot_start"], geo0["ang_chassis_bot_end"])
        bcr.close_path()
        bcr.set_source_rgba(c_dark_r, c_dark_g, c_dark_b, 0.85)
        bcr.fill()
        bcr.move_to(self.x_left, geo0["y_dark_bot"])
        bcr.line_to(self.cx - geo0["x_dark_cut"], geo0["y_dark_bot"])
        bcr.arc_negative(self.cx, 590.0, self.r_dark, geo0["ang_dark_bot_end"], geo0["ang_dark_bot_start"])
        bcr.line_to(self.x_right, geo0["y_dark_bot"])
        bcr.set_source_rgba(*self.c_border_3d)
        bcr.set_line_width(1.4)
        bcr.stroke()
        y_up_top = geo0["y_edge_bot"] - self.cuff_ext
        bcr.new_sub_path()
        bcr.move_to(self.x_left, geo0["y_edge_bot"])
        bcr.line_to(self.x_left, y_up_top)
        bcr.arc_negative(self.x_left, y_up_top + r_cuff, r_cuff, 1.5 * math.pi, math.pi)
        bcr.line_to(self.x_left - prot, geo0["y_silver_bot"] - r_cuff)
        bcr.arc_negative(self.x_left, geo0["y_silver_bot"] - r_cuff, r_cuff, math.pi, 0.5 * math.pi)
        bcr.line_to(self.cx - geo0["x_chassis_cut"], geo0["y_silver_bot"])
        bcr.arc_negative(self.cx, 590.0, self.r_chassis, geo0["ang_chassis_bot_end"], geo0["ang_chassis_bot_start"])
        bcr.line_to(self.x_right, geo0["y_silver_bot"])
        bcr.arc_negative(self.x_right, geo0["y_silver_bot"] - r_cuff, r_cuff, 0.5 * math.pi, 0)
        bcr.line_to(self.x_right + prot, y_up_top + r_cuff)
        bcr.arc_negative(self.x_right, y_up_top + r_cuff, r_cuff, 0, 1.5 * math.pi)
        bcr.line_to(self.x_right, geo0["y_edge_bot"])
        bcr.line_to(self.cx + geo0["x_outer_cut"], geo0["y_edge_bot"])
        bcr.arc(self.cx, 590.0, self.r_outer, geo0["ang_outer_bot_start"], geo0["ang_outer_bot_end"])
        bcr.close_path()
        silver_pat_bot = cairo.LinearGradient(self.x_left, geo0["y_edge_bot"], self.x_left, geo0["y_silver_bot"])
        silver_pat_bot.add_color_stop_rgb(0.0, *hex_to_rgba(C_TEXT_SEC)[:3])
        silver_pat_bot.add_color_stop_rgb(1.0, *hex_to_rgba(C_TEXT_PRI)[:3])
        bcr.set_source(silver_pat_bot)
        bcr.fill_preserve()
        bcr.set_source_rgba(*self.c_border_3d)
        bcr.set_line_width(1.4)
        bcr.stroke()
        band_pat_bot = cairo.LinearGradient(self.cx - self.r_outer, 590.0, self.cx + self.r_outer, 590.0)
        band_pat_bot.add_color_stop_rgb(0, *self.c_band_stop0)
        band_pat_bot.add_color_stop_rgb(0.5, *self.c_band_stop1)
        band_pat_bot.add_color_stop_rgb(1, *self.c_band_stop2)
        bcr.new_sub_path()
        bcr.arc(self.cx, 590.0, self.r_outer, geo0["ang_outer_bot_start"], geo0["ang_outer_bot_end"])
        bcr.line_to(self.cx - geo0["x_inner_cut"], geo0["y_edge_bot"])
        bcr.arc_negative(self.cx, 590.0, self.r_inner, geo0["ang_inner_bot_end"], geo0["ang_inner_bot_start"])
        bcr.close_path()
        bcr.set_source(band_pat_bot)
        bcr.fill_preserve()
        bcr.set_source_rgba(*self.c_border_3d)
        bcr.set_line_width(1.6)
        bcr.stroke()
        bcr.arc(self.cx, 590.0, self.r_inner, geo0["ang_inner_bot_start"], geo0["ang_inner_bot_end"])
        bcr.set_source_rgba(0, 0, 0, 0.35)
        bcr.set_line_width(2.2)
        bcr.stroke()
        self._cached_bot_casing = bot_surf

    def _bake_content(self):
        W, H = int(self.base_w), int(self.base_h)
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        cr = cairo.Context(surf)
        cr.set_antialias(cairo.ANTIALIAS_DEFAULT)
        self._draw_content_elements(cr, cy_top=190.0)
        self._cached_content_surf = surf
        self._cached_content_page = self.current_page

    def _draw_content_elements(self, cr, cy_top=190.0):
        if self.current_page == "controls":
            self._draw_controls_content(cr, cy_top)
        elif self.current_page == "notifications":
            self._draw_notifications_content(cr, cy_top)
        elif self.current_page == "wifi":
            self._draw_wifi_content(cr, cy_top)

    def _draw_controls_content(self, cr, cy_top):
        draw_curved_kerned_cached(cr, "CONTROL CENTER", self.cx, cy_top, r_text=62.0, font_desc="DejaVu Sans Bold 8.5", letter_spacing=1.6)
        cr.save()
        draw_bow_mark(cr, self.cx, cy_top - self.top_mark_offset, size=22.0, color=self.c_accent_rgb)
        cr.restore()

        grid_x = self.x_left + 36.0
        grid_y = 224.0
        col_w = (self.W_shell - 72.0 - 20.0) / 2.0
        row_h = 44.0
        gap_y = 24.0

        bt_icon, bt_val = (("󰂱" if self.bt_device else "󰂯"), (self.bt_device or "Enabled")) if self.bt_enabled else ("󰂲", "Disabled")
        pwr_lower = (self.power_mode or "balanced").lower()
        if pwr_lower == "performance":
            pwr_icon, pwr_val = "󰓅", "Performance"
        elif pwr_lower in ("powersave", "power-saver", "power saver"):
            pwr_icon, pwr_val = "󰌪", "Power Saver"
        else:
            pwr_icon, pwr_val = "󰾅", "Balanced"

        if not self.wifi_radio_enabled or self.wifi_text == "Disabled":
            wifi_icon, wifi_val = "󰤮", "Disabled"
        elif self.wifi_text == "Connected" or self.wifi_ssid:
            wifi_icon, wifi_val = "󰤨", (self.wifi_ssid or "Connected")
        else:
            wifi_icon, wifi_val = "󰖪", "Disconnected"

        tiles = [
            ("󰌌", "Input", self.ime_text, grid_x, grid_y),
            (wifi_icon, "Wi-Fi", wifi_val, grid_x + col_w + 20.0, grid_y),
            (bt_icon, "Bluetooth", bt_val, grid_x, grid_y + row_h + gap_y),
            (pwr_icon, "Power Mode", pwr_val, grid_x + col_w + 20.0, grid_y + row_h + gap_y),
        ]

        box_w = 26.0
        for icon, name, val, c_x, c_y in tiles:
            cr.save()
            l_ic = PangoCairo.create_layout(cr)
            l_ic.set_font_description(self.pango_font_tile_icon)
            l_ic.set_markup(f"<span color='{self.c_accent}'>{icon}</span>", -1)
            ink, _ = l_ic.get_pixel_extents()
            cr.move_to(c_x + (box_w - ink.width) / 2.0 - ink.x, c_y + 4.0)
            PangoCairo.show_layout(cr, l_ic)

            txt_x = c_x + 32.0
            l_txt = PangoCairo.create_layout(cr)
            l_txt.set_font_description(self.pango_font_tile_title)
            l_txt.set_markup(f"<span color='{C_BORDER_3D}'>{name}</span>", -1)
            cr.move_to(txt_x, c_y + 2.0)
            PangoCairo.show_layout(cr, l_txt)

            l_txt.set_width(int((col_w - 34.0) * Pango.SCALE))
            l_txt.set_ellipsize(Pango.EllipsizeMode.END)
            l_txt.set_markup(f"<span color='{self.c_accent}'>{val}</span>", -1)
            cr.move_to(txt_x, c_y + 20.0)
            PangoCairo.show_layout(cr, l_txt)
            cr.restore()

        draw_pokeball_dual_slider(
            cr, self.cx, self.cy_pokeball,
            R=64.0, thickness=12.0,
            vol_val=self.vol_val, bri_val=self.bri_val,
            knob_style="round_knob",
            icon_color=self.c_accent,
            accent_rgb=self.c_accent_rgb,
            dark_color=self.c_slider_dark,
            pwr_bg=self.c_pwr_bg,
        )

        cr.save()
        draw_bell_icon(cr, self.cx, self.socket_well_y, font_size=20, color=self.c_accent)
        cr.restore()

    def _draw_notifications_content(self, cr, cy_top):
        draw_curved_kerned_cached(cr, "NOTIFICATIONS", self.cx, cy_top, r_text=62.0, font_desc="DejaVu Sans Bold 8.5", letter_spacing=1.6)
        cr.save()
        draw_bell_icon(cr, self.cx, cy_top - self.top_mark_offset, font_size=11, color=self.c_accent)
        cr.restore()

        grid_x = self.x_left + 36.0
        grid_y = 214.0
        row_w = self.W_shell - 72.0
        notifs = self.notifications

        if not notifs:
            cr.save()
            l_ic = PangoCairo.create_layout(cr)
            l_ic.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font 30"))
            l_ic.set_markup(f"<span color='{self.c_accent}'>󰂛</span>", -1)
            ink_i, _ = l_ic.get_pixel_extents()
            cr.move_to(self.cx - ink_i.width / 2.0, 308.0)
            PangoCairo.show_layout(cr, l_ic)

            l_msg = PangoCairo.create_layout(cr)
            l_msg.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 11.5"))
            l_msg.set_markup(f"<span color='{self.c_accent}'>No notifications</span>", -1)
            ink_m, _ = l_msg.get_pixel_extents()
            cr.move_to(self.cx - ink_m.width / 2.0, 350.0)
            PangoCairo.show_layout(cr, l_msg)
            cr.restore()
        else:
            start_idx = self.notif_page_idx * 5
            for idx, item in enumerate(notifs[start_idx : start_idx + 5]):
                item_y = grid_y + idx * 49.0
                is_hover = (self.hovered_item == f"notif_{idx}")

                cr.save()
                if is_hover:
                    draw_rounded_rect(cr, grid_x - 6.0, item_y - 2.0, row_w + 12.0, 45.0, 8.0)
                    cr.set_source_rgba(*hex_to_rgba(self.c_accent, 0.08))
                    cr.fill()

                if isinstance(item, tuple):
                    icon, icon_col, app, time_str, title, body = item
                else:
                    app = item.get("app_name", "System")
                    time_str = format_relative_time(item.get("timestamp"))
                    title = item.get("summary", "")
                    body = item.get("body", "")
                    icon_col, icon = get_badge_info(app)

                l_ic = PangoCairo.create_layout(cr)
                l_ic.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font 16"))
                l_ic.set_markup(f"<span color='{icon_col}'>{icon}</span>", -1)
                cr.move_to(grid_x, item_y + 2.0)
                PangoCairo.show_layout(cr, l_ic)

                txt_x = grid_x + 28.0
                max_text_w = row_w - (50.0 if is_hover else 32.0)

                for font_str, markup, dy in (
                    ("JetBrains Mono Nerd Font Bold 10", f"<span color='{C_BG_WIN}'>{app}</span>  <span color='{C_BG_WIN}' alpha='50%'>• {time_str}</span>", 0.0),
                    ("JetBrains Mono Nerd Font Bold 9.5", f"<span color='{self.c_accent}'>{title}</span>", 15.0),
                    ("JetBrains Mono Nerd Font 8.5", f"<span color='{C_BG_WIN}' alpha='75%'>{body}</span>", 29.0),
                ):
                    layout = PangoCairo.create_layout(cr)
                    layout.set_font_description(Pango.FontDescription(font_str))
                    layout.set_width(int(max_text_w * Pango.SCALE))
                    layout.set_ellipsize(Pango.EllipsizeMode.END)
                    layout.set_markup(markup, -1)
                    cr.move_to(txt_x, item_y + dy)
                    PangoCairo.show_layout(cr, layout)

                if is_hover:
                    l_del = PangoCairo.create_layout(cr)
                    l_del.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 11"))
                    l_del.set_markup(f"<span color='{self.c_accent}'>󰅖</span>", -1)
                    cr.move_to(grid_x + row_w - 14.0, item_y + 14.0)
                    PangoCairo.show_layout(cr, l_del)
                cr.restore()

            cr.save()
            clr_col = self.c_accent_hover if self.hovered_item == "clear_all" else self.c_accent
            l_clr = PangoCairo.create_layout(cr)
            l_clr.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 10.5"))
            l_clr.set_markup(f"<span color='{clr_col}'>󰆴 Clear all notifications</span>", -1)
            ink, _ = l_clr.get_pixel_extents()
            cr.move_to(self.cx - ink.width / 2.0, 478.0)
            PangoCairo.show_layout(cr, l_clr)
            cr.restore()

            if len(notifs) > 5:
                self._draw_pagination_row(cr, grid_x, row_w, 504.0, self.notif_page_idx, len(notifs), "notif_prev", "notif_next", "10", "9.5")

        cr.save()
        draw_bow_mark(cr, self.cx, self.socket_well_y, size=34.0, color=self.c_accent_rgb)
        cr.restore()

    def _draw_wifi_content(self, cr, cy_top):
        draw_curved_kerned_cached(cr, "WI-FI NETWORKS", self.cx, cy_top, r_text=62.0, font_desc="DejaVu Sans Bold 8.5", letter_spacing=1.6)
        cr.save()
        l_top = PangoCairo.create_layout(cr)
        l_top.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font 13"))
        l_top.set_markup(f"<span color='{self.c_accent}'>󰖩</span>", -1)
        ink, _ = l_top.get_pixel_extents()
        cr.move_to(self.cx - ink.width / 2.0, cy_top - self.top_mark_offset - ink.height / 2.0)
        PangoCairo.show_layout(cr, l_top)
        cr.restore()

        content_x = self.x_left + 36.0
        content_w = self.W_shell - 72.0

        cr.save()
        l_htit = PangoCairo.create_layout(cr)
        l_htit.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 12"))
        l_htit.set_markup(f"<span color='{C_BG_WIN}'>Wi-Fi Networks</span>", -1)
        cr.move_to(content_x, 212.0)
        PangoCairo.show_layout(cr, l_htit)

        is_tg_hover = (self.hovered_item == "wifi_toggle")
        tg_text = "󰖩 ON" if self.wifi_radio_enabled else "󰖪 OFF"
        tg_col = self.c_accent if (self.wifi_radio_enabled or is_tg_hover) else C_TEXT_MUT
        l_tg = PangoCairo.create_layout(cr)
        l_tg.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 10.5"))
        l_tg.set_markup(f"<span color='{tg_col}'><b>{tg_text}</b></span>", -1)
        cr.move_to(content_x + content_w - 105.0, 213.0)
        PangoCairo.show_layout(cr, l_tg)

        sc_col = self.c_accent if self.hovered_item == "wifi_rescan" else C_BG_WIN
        l_sc = PangoCairo.create_layout(cr)
        l_sc.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 10.5"))
        l_sc.set_markup(f"<span color='{sc_col}'><b>󰑐 Scan</b></span>", -1)
        cr.move_to(content_x + content_w - 48.0, 213.0)
        PangoCairo.show_layout(cr, l_sc)
        cr.restore()

        cr.save()
        l_st = PangoCairo.create_layout(cr)
        l_st.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 10"))
        if self.wifi_status_msg:
            l_st.set_markup(f"<span color='{self.c_accent}'><b>{self.wifi_status_msg}</b></span>", -1)
            cr.move_to(content_x, 238.0)
            PangoCairo.show_layout(cr, l_st)
        elif self.wifi_ssid:
            l_st.set_markup(f"<span color='{C_BG_WIN}' alpha='80%'>Connected: </span><span color='{self.c_accent}'><b>{self.wifi_ssid}</b></span>", -1)
            cr.move_to(content_x, 238.0)
            PangoCairo.show_layout(cr, l_st)

            dc_col = self.c_accent if self.hovered_item == "wifi_disconnect" else C_BG_WAYBAR
            l_dc = PangoCairo.create_layout(cr)
            l_dc.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 9.5"))
            l_dc.set_markup(f"<span color='{dc_col}'><b><u>󰖪 Disconnect</u></b></span>", -1)
            cr.move_to(content_x + content_w - 95.0, 238.0)
            PangoCairo.show_layout(cr, l_dc)
        elif not self.wifi_radio_enabled:
            l_st.set_markup(f"<span color='{C_TEXT_MUT}'>Wi-Fi is currently disabled</span>", -1)
            cr.move_to(content_x, 238.0)
            PangoCairo.show_layout(cr, l_st)
        else:
            l_st.set_markup(f"<span color='{C_BG_WIN}' alpha='75%'>{len(self.wifi_networks)} networks found</span>", -1)
            cr.move_to(content_x, 238.0)
            PangoCairo.show_layout(cr, l_st)
        cr.restore()

        if self.wifi_password_prompt_ssid:
            self._draw_wifi_password_prompt(cr, content_x, content_w)
        else:
            self._draw_wifi_list(cr, content_x, content_w)

        cr.save()
        draw_bow_mark(cr, self.cx, self.socket_well_y, size=34.0, color=self.c_accent_rgb)
        cr.restore()

    def _draw_wifi_password_prompt(self, cr, content_x, content_w):
        cr.save()
        l_ptit = PangoCairo.create_layout(cr)
        l_ptit.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 12"))
        l_ptit.set_markup(f"<span color='{C_BG_WIN}'>Password Required</span>", -1)
        cr.move_to(content_x, 275.0)
        PangoCairo.show_layout(cr, l_ptit)

        l_pssid = PangoCairo.create_layout(cr)
        l_pssid.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 11"))
        l_pssid.set_markup(f"<span color='{C_BG_WIN}' alpha='75%'>Network: </span><span color='{self.c_accent}'><b>{self.wifi_password_prompt_ssid}</b></span>", -1)
        cr.move_to(content_x, 298.0)
        PangoCairo.show_layout(cr, l_pssid)

        input_y = 326.0
        draw_rounded_rect(cr, content_x, input_y, content_w, 34.0, 6.0)
        cr.set_source_rgba(0.13, 0.06, 0.07, 0.06)
        cr.fill_preserve()
        cr.set_source_rgba(*hex_to_rgba(C_BORDER_3D, 0.35))
        cr.set_line_width(1.0)
        cr.stroke()

        l_inp = PangoCairo.create_layout(cr)
        l_inp.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font 11"))
        if self.wifi_password_input:
            masked = "•" * len(self.wifi_password_input)
            l_inp.set_markup(f"<span color='{C_BG_WIN}'>{masked}</span><span color='{self.c_accent}'>|</span>", -1)
        else:
            l_inp.set_markup(f"<span color='{C_TEXT_MUT}'>Enter password...|</span>", -1)
        cr.move_to(content_x + 10.0, input_y + 7.0)
        PangoCairo.show_layout(cr, l_inp)

        btn_y = 374.0
        draw_rounded_rect(cr, content_x, btn_y, 110.0, 30.0, 6.0)
        alpha = 1.0 if self.hovered_item == "wifi_pass_connect" else 0.90
        col = C_ACCENT_HOVER if self.hovered_item == "wifi_pass_connect" else self.c_accent
        cr.set_source_rgba(*hex_to_rgba(col, alpha))
        cr.fill()
        l_btnc = PangoCairo.create_layout(cr)
        l_btnc.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 10"))
        l_btnc.set_markup(f"<span color='{C_TEXT_INV}'>Connect ↵</span>", -1)
        cr.move_to(content_x + 16.0, btn_y + 6.0)
        PangoCairo.show_layout(cr, l_btnc)

        cxl_col = self.c_accent if self.hovered_item == "wifi_pass_cancel" else C_BG_WIN
        l_btnx = PangoCairo.create_layout(cr)
        l_btnx.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 10"))
        l_btnx.set_markup(f"<span color='{cxl_col}'>Cancel</span>", -1)
        cr.move_to(content_x + 135.0, btn_y + 6.0)
        PangoCairo.show_layout(cr, l_btnx)

        l_hint = PangoCairo.create_layout(cr)
        l_hint.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font 9"))
        l_hint.set_markup(f"<span color='{C_BG_WIN}' alpha='60%'>Press Enter to connect, Esc to return</span>", -1)
        cr.move_to(content_x, 420.0)
        PangoCairo.show_layout(cr, l_hint)
        cr.restore()

    def _draw_wifi_list(self, cr, content_x, content_w):
        start_idx = self.wifi_page_idx * 5
        page_nets = self.wifi_networks[start_idx : start_idx + 5]

        if not page_nets:
            cr.save()
            l_empty = PangoCairo.create_layout(cr)
            l_empty.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 11"))
            msg = "󰑐 Scanning nearby networks..." if self.wifi_scanning else ("󰖪 Wi-Fi is disabled" if not self.wifi_radio_enabled else "󰤯 No networks found")
            l_empty.set_markup(f"<span color='{self.c_accent}'>{msg}</span>", -1)
            ink, _ = l_empty.get_pixel_extents()
            cr.move_to(self.cx - ink.width / 2.0, 340.0)
            PangoCairo.show_layout(cr, l_empty)
            cr.restore()
            return

        for idx, net in enumerate(page_nets):
            cr.save()
            item_y = 262.0 + idx * 48.0
            is_active = net.get("in_use") or (net.get("ssid") == self.wifi_ssid)
            is_hover = (self.hovered_item == f"wifi_item_{idx}")

            if is_active or is_hover:
                draw_rounded_rect(cr, content_x - 6.0, item_y - 2.0, content_w + 12.0, 44.0, 8.0)
                cr.set_source_rgba(*hex_to_rgba(self.c_accent, 0.12 if is_active else 0.08))
                cr.fill()

            sig = net.get("signal", 0)
            sig_icon = "󰤨" if sig >= 80 else "󰤥" if sig >= 60 else "󰤢" if sig >= 40 else "󰤟" if sig >= 20 else "󰤯"
            ic_col = self.c_accent if (is_active or is_hover) else C_BORDER_3D
            l_sig = PangoCairo.create_layout(cr)
            l_sig.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font 20"))
            l_sig.set_markup(f"<span color='{ic_col}'>{sig_icon}</span>", -1)
            cr.move_to(content_x, item_y + 2.0)
            PangoCairo.show_layout(cr, l_sig)

            ssid_str = net.get("ssid", "Unknown")
            ssid_disp = (ssid_str[:17] + "…") if len(ssid_str) > 18 else ssid_str
            l_nm = PangoCairo.create_layout(cr)
            l_nm.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 11.5"))
            nm_col = self.c_accent if is_active else (C_BORDER_3D if is_hover else C_BG_WIN)
            l_nm.set_markup(f"<span color='{nm_col}'>{ssid_disp}</span>", -1)
            cr.move_to(content_x + 36.0, item_y)
            PangoCairo.show_layout(cr, l_nm)

            sec_str = net.get("security", "")
            sec_disp = sec_str.replace("WPA1", "").replace("WPA2", "WPA2").strip() if sec_str and sec_str != "--" else "Open"
            l_inf = PangoCairo.create_layout(cr)
            l_inf.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font 9.5"))
            l_inf.set_markup(f"<span color='{C_BG_WIN}' alpha='70%'>{sig}%  •  {sec_disp}</span>", -1)
            cr.move_to(content_x + 36.0, item_y + 21.0)
            PangoCairo.show_layout(cr, l_inf)

            badge_x = content_x + content_w - 78.0
            if is_active:
                l_bg = PangoCairo.create_layout(cr)
                l_bg.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 9.5"))
                l_bg.set_markup(f"<span color='{C_STATUS_SUCC}'>✔ Active</span>", -1)
                cr.move_to(badge_x, item_y + 2.0)
                PangoCairo.show_layout(cr, l_bg)
            elif net.get("saved"):
                l_bg = PangoCairo.create_layout(cr)
                l_bg.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 9"))
                l_bg.set_markup(f"<span color='{C_BG_WIN}' alpha='55%'>Saved</span>", -1)
                cr.move_to(badge_x + 10.0, item_y + 2.0)
                PangoCairo.show_layout(cr, l_bg)

            if not is_active and not net.get("saved") and sec_str and sec_str != "--":
                l_lk = PangoCairo.create_layout(cr)
                l_lk.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font 12"))
                l_lk.set_markup(f"<span color='{self.c_accent}' alpha='85%'>󰌾</span>", -1)
                cr.move_to(content_x + content_w - 18.0, item_y + 19.0)
                PangoCairo.show_layout(cr, l_lk)

            cr.restore()

        if len(self.wifi_networks) > 5:
            self._draw_pagination_row(cr, content_x, content_w, 514.0, self.wifi_page_idx, len(self.wifi_networks), "wifi_prev", "wifi_next", "10.5", "10")

    def _draw_pagination_row(self, cr, x, w, py_y, page_idx, total_items, prev_key, next_key, btn_font_sz, page_font_sz):
        cr.save()
        total_pages = max(1, (total_items + 4) // 5)

        pv_col = self.c_accent if self.hovered_item == prev_key else (C_BG_WIN if page_idx > 0 else C_TEXT_MUT)
        l_prv = PangoCairo.create_layout(cr)
        l_prv.set_font_description(Pango.FontDescription(f"JetBrains Mono Nerd Font Bold {btn_font_sz}"))
        l_prv.set_markup(f"<span color='{pv_col}'><b>◀ Prev</b></span>", -1)
        cr.move_to(x + 4.0, py_y)
        PangoCairo.show_layout(cr, l_prv)

        l_pg = PangoCairo.create_layout(cr)
        l_pg.set_font_description(Pango.FontDescription(f"JetBrains Mono Nerd Font Bold {page_font_sz}"))
        l_pg.set_markup(f"<span color='{C_BG_WIN}' alpha='75%'><b>{page_idx + 1} / {total_pages}</b></span>", -1)
        ink, _ = l_pg.get_pixel_extents()
        cr.move_to(self.cx - ink.width / 2.0, py_y)
        PangoCairo.show_layout(cr, l_pg)

        nx_col = self.c_accent if self.hovered_item == next_key else (C_BG_WIN if page_idx < total_pages - 1 else C_TEXT_MUT)
        l_nxt = PangoCairo.create_layout(cr)
        l_nxt.set_font_description(Pango.FontDescription(f"JetBrains Mono Nerd Font Bold {btn_font_sz}"))
        l_nxt.set_markup(f"<span color='{nx_col}'><b>Next ▶</b></span>", -1)
        cr.move_to(x + w - (56.0 if btn_font_sz == "10.5" else 52.0), py_y)
        PangoCairo.show_layout(cr, l_nxt)
        cr.restore()

    def on_draw(self, widget, cr):
        clear_surface(cr)
        cr.set_antialias(cairo.ANTIALIAS_DEFAULT)

        cr.save()
        sx = self.W_canvas / self.base_w
        sy = self.H_canvas / self.base_h
        cr.scale(sx, sy)

        geo = self.get_dynamic_coords(self.anim_progress)

        cr.save()
        cr.new_sub_path()
        cr.rectangle(self.x_left, geo["y_edge_top"], self.W_shell, geo["y_edge_bot"] - geo["y_edge_top"])
        cr.arc(self.cx, geo["cy_top"], self.r_inner, geo["ang_inner_top_end"], geo["ang_inner_top_start"])
        cr.close_path()
        cr.arc(self.cx, geo["cy_bot"], self.r_inner, geo["ang_inner_bot_start"], geo["ang_inner_bot_end"])
        cr.close_path()
        cr.clip()

        scr_pat = cairo.LinearGradient(0, geo["cy_top"] - self.r_inner, 0, geo["cy_bot"] + self.r_inner)
        scr_pat.add_color_stop_rgba(0.0, self.c_holo_top[0], self.c_holo_top[1], self.c_holo_top[2], self.holo_alpha_top)
        scr_pat.add_color_stop_rgba(0.5, self.c_holo_mid[0], self.c_holo_mid[1], self.c_holo_mid[2], self.holo_alpha_mid)
        scr_pat.add_color_stop_rgba(1.0, self.c_holo_bot[0], self.c_holo_bot[1], self.c_holo_bot[2], self.holo_alpha_bot)
        cr.set_source(scr_pat)
        cr.paint()

        if self.anim_state in ("opening", "closing", "closed"):
            if self.anim_progress > 0.25:
                if not self._cached_content_surf or self._cached_content_page != self.current_page:
                    self._bake_content()
                alpha = min(1.0, max(0.0, (self.anim_progress - 0.25) / 0.75))
                cr.set_source_surface(self._cached_content_surf, 0, 0)
                cr.paint_with_alpha(alpha)
            cr.restore()

            if not self._cached_top_casing or not self._cached_bot_casing:
                self._bake_casings()
            cr.save()
            cr.set_source_surface(self._cached_top_casing, 0, geo["top_casing_y"])
            cr.paint()
            cr.restore()

            cr.save()
            cr.set_source_surface(self._cached_bot_casing, 0, geo["bot_casing_y"])
            cr.paint()
            cr.restore()

            cr.restore()
            return False

        self._draw_content_elements(cr, cy_top=geo["cy_top"])
        cr.restore()

        if not self._cached_top_casing or not self._cached_bot_casing:
            self._bake_casings()
        cr.save()
        cr.set_source_surface(self._cached_top_casing, 0, 0)
        cr.paint()
        cr.restore()

        cr.save()
        cr.set_source_surface(self._cached_bot_casing, 0, 0)
        cr.paint()
        cr.restore()

        cr.restore()
        return False
