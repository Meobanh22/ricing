#!/usr/bin/env python3
# panels/profile_card.py — Top-left Serena avatar & system info card widget.

import os
import cairo
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

from panels.common import (
    VIVID_RED,
    LIGHT_RED,
    WINE_RED,
    DARK_RUBY,
    PURE_WHITE,
    MUTED_PINK,
    CREAM_WHITE,
    SOFT_PINK,
    HAS_LAYER_SHELL,
    GtkLayerShell,
    get_uptime_str,
    hex_to_rgba,
    on_window_draw_clear,
)
from ui_core import resolve_asset


class ProfileCardWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Profile Card Widget")
        self.set_name("desktop-avatar-window")
        self.set_decorated(False)
        self.set_resizable(False)

        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_namespace(self, "desktop-widgets")
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.BOTTOM)
            GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, False)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, False)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.LEFT, 28)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 56)
            GtkLayerShell.set_exclusive_zone(self, 0)
        else:
            self.set_wmclass("desktop-widgets", "desktop-widgets")
            self.set_position(Gtk.WindowPosition.NONE)
            self.move(28, 56)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        self.set_app_paintable(True)
        self.connect("draw", on_window_draw_clear)
        self.build_ui()

    def find_asset_path(self, relative_path: str):
        p = resolve_asset(relative_path)
        return p if p else None

    def create_banner_image(self, w=220, h=72, r=12.0):
        banner_path = self.find_asset_path("assets/banners/serena_cover_banner.png")
        if not banner_path:
            banner_path = self.find_asset_path("assets/wallpapers/serena_fennekin_wallpaper_hd.jpg")

        extra_h = 5
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h + extra_h)
        cr = cairo.Context(surface)
        cr.set_antialias(cairo.ANTIALIAS_BEST)

        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        def rounded_rect(x, y, rw, rh, rad):
            cr.new_sub_path()
            cr.arc(x + rw - rad, y + rad, rad, -1.57079632679, 0)
            cr.arc(x + rw - rad, y + rh - rad, rad, 0, 1.57079632679)
            cr.arc(x + rad, y + rh - rad, rad, 1.57079632679, 3.14159265359)
            cr.arc(x + rad, y + rad, rad, 3.14159265359, 4.71238898038)
            cr.close_path()

        steps = 14
        for s in range(steps + 1):
            dy = 3.5 * (s / steps)
            rounded_rect(0, dy, w, h, r)
            cr.set_source_rgb(*hex_to_rgba(DARK_RUBY)[:3])
            cr.fill()

        if banner_path and os.path.exists(banner_path):
            try:
                src = GdkPixbuf.Pixbuf.new_from_file_at_scale(banner_path, w, h, False)
                cr.save()
                rounded_rect(0, 0, w, h, r)
                cr.clip()
                Gdk.cairo_set_source_pixbuf(cr, src, 0, 0)
                cr.paint()
                cr.restore()
            except Exception:
                cr.save()
                rounded_rect(0, 0, w, h, r)
                cr.clip()
                cr.set_source_rgb(*hex_to_rgba(WINE_RED)[:3])
                cr.paint()
                cr.restore()

        rounded_rect(0, 0, w, h, r)
        cr.set_source_rgba(*hex_to_rgba(DARK_RUBY, 0.95))
        cr.set_line_width(2.0)
        cr.stroke()

        pix = Gdk.pixbuf_get_from_surface(surface, 0, 0, w, h + extra_h)
        return Gtk.Image.new_from_pixbuf(pix)

    def create_avatar_image(self, size=60):
        avatar_path = self.find_asset_path("assets/avatars/serena_profile_avatar.png")
        extra_h = 5
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size + extra_h)
        cr = cairo.Context(surface)
        cr.set_antialias(cairo.ANTIALIAS_BEST)

        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        r = size / 2.0 - 1.5
        cx = size / 2.0
        cy = size / 2.0

        steps = 14
        for s in range(steps + 1):
            dy = 3.5 * (s / steps)
            cr.arc(cx, cy + dy, r, 0, 6.2831853)
            cr.set_source_rgb(*hex_to_rgba(DARK_RUBY)[:3])
            cr.fill()

        if avatar_path and os.path.exists(avatar_path):
            try:
                src = GdkPixbuf.Pixbuf.new_from_file_at_scale(avatar_path, int(r * 2), int(r * 2), False)
                cr.save()
                cr.arc(cx, cy, r, 0, 6.2831853)
                cr.clip()
                Gdk.cairo_set_source_pixbuf(cr, src, cx - r, cy - r)
                cr.paint()
                cr.restore()
            except Exception:
                cr.arc(cx, cy, r, 0, 6.2831853)
                cr.set_source_rgb(*hex_to_rgba(WINE_RED)[:3])
                cr.fill()

        cr.arc(cx, cy, r, 0, 6.2831853)
        cr.set_source_rgba(*hex_to_rgba(DARK_RUBY, 0.95))
        cr.set_line_width(2.2)
        cr.stroke()

        pix = Gdk.pixbuf_get_from_surface(surface, 0, 0, size, size + extra_h)
        return Gtk.Image.new_from_pixbuf(pix)

    def create_single_pokeball_image(self, size=60):
        extra_h = 5
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size + extra_h)
        cr = cairo.Context(surface)
        cr.set_antialias(cairo.ANTIALIAS_BEST)

        r = size / 2.0 - 2.0
        cx = size / 2.0
        cy = size / 2.0

        steps = 14
        for s in range(steps + 1):
            dy = 3.6 * (s / steps)
            cr.arc(cx, cy + dy, r, 0, 6.2831853)
            cr.set_source_rgb(*hex_to_rgba(DARK_RUBY)[:3])
            cr.fill()

        cr.save()
        cr.arc(cx, cy, r, 0, 6.2831853)
        cr.clip()

        cr.set_source_rgb(*hex_to_rgba(CREAM_WHITE)[:3])
        cr.paint()

        pat = cairo.LinearGradient(0, cy - r, 0, cy)
        pat.add_color_stop_rgb(0, *hex_to_rgba(LIGHT_RED)[:3])
        pat.add_color_stop_rgb(1, *hex_to_rgba(VIVID_RED)[:3])
        cr.set_source(pat)
        cr.rectangle(cx - r, cy - r, r * 2, r)
        cr.fill()

        cr.save()
        cr.arc(cx, cy - r * 0.45, r * 0.65, 3.4, 6.0)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.35)
        cr.set_line_width(2.2)
        cr.stroke()
        cr.restore()

        cr.set_source_rgb(*hex_to_rgba(DARK_RUBY)[:3])
        cr.rectangle(cx - r, cy - 2.5, r * 2, 5.0)
        cr.fill()

        for rad, col in ((9.0, DARK_RUBY), (6.5, PURE_WHITE), (3.5, DARK_RUBY), (2.5, PURE_WHITE)):
            cr.arc(cx, cy, rad, 0, 6.2831853)
            cr.set_source_rgb(*hex_to_rgba(col)[:3])
            cr.fill()

        cr.restore()

        cr.arc(cx, cy, r, 0, 6.2831853)
        cr.set_source_rgba(*hex_to_rgba(DARK_RUBY, 0.95))
        cr.set_line_width(2.0)
        cr.stroke()

        pix = Gdk.pixbuf_get_from_surface(surface, 0, 0, size, size + extra_h)
        return Gtk.Image.new_from_pixbuf(pix)

    def update_uptime_tick(self):
        try:
            self.lbl_uptime_val.set_markup(
                f"<span font_family='Inter, Sans' font='13.5' weight='800' color='{CREAM_WHITE}'>{get_uptime_str()}</span>"
            )
        except Exception:
            pass
        return True

    def build_ui(self):
        col_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        col_box.set_size_request(269, -1)

        card1_event = Gtk.EventBox()
        card1_event.set_visible_window(False)

        card1_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card1_box.get_style_context().add_class("desktop-widget-card")
        card1_box.get_style_context().add_class("widget-avatar-card")
        card1_box.set_size_request(269, -1)

        card1_event.connect("enter-notify-event", lambda w, e: card1_box.get_style_context().add_class("card-hover"))
        card1_event.connect("leave-notify-event", lambda w, e: card1_box.get_style_context().remove_class("card-hover"))

        header_fixed = Gtk.Fixed()
        header_fixed.set_size_request(220, 108)

        header_fixed.put(self.create_banner_image(w=220, h=72, r=12.0), 0, 0)
        header_fixed.put(self.create_avatar_image(size=60), 6, 44)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        text_box.get_style_context().add_class("avatar-profile-text-box")

        lbl_name = Gtk.Label()
        lbl_name.get_style_context().add_class("avatar-profile-name")
        lbl_name.set_markup(f"<span font_family='Inter, Sans' font='14' weight='800' color='{WINE_RED}'>Serena</span>")
        lbl_name.set_halign(Gtk.Align.START)

        lbl_sub = Gtk.Label()
        lbl_sub.get_style_context().add_class("avatar-profile-subtitle")
        lbl_sub.set_markup(f"<span font_family='Inter, Sans' font='8' weight='700' color='{MUTED_PINK}'>pokemon performer</span>")
        lbl_sub.set_halign(Gtk.Align.START)

        text_box.pack_start(lbl_name, False, False, 0)
        text_box.pack_start(lbl_sub, False, False, 0)
        header_fixed.put(text_box, 72, 74)
        card1_box.pack_start(header_fixed, False, False, 0)

        balls_fixed = Gtk.Fixed()
        balls_fixed.set_size_request(220, 78)

        ball_sz = 60
        pokemon_specs = [
            ("assets/pokemon/pancham.png", 46, 6),
            ("assets/pokemon/sylveon.png", 52, 78),
            ("assets/pokemon/braixen.png", 48, 150),
        ]

        for asset_rel, sprite_sz, bx in pokemon_specs:
            by = 10
            balls_fixed.put(self.create_single_pokeball_image(size=ball_sz), bx, by)
            asset_path = self.find_asset_path(asset_rel)
            if asset_path and os.path.exists(asset_path):
                sp_pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(asset_path, sprite_sz, sprite_sz, True)
                sx = bx + int((ball_sz - sprite_sz) / 2)
                sy = by + int((ball_sz - sprite_sz) / 2) - 4
                balls_fixed.put(Gtk.Image.new_from_pixbuf(sp_pix), sx, sy)

        card1_box.pack_start(balls_fixed, False, False, 0)
        card1_event.add(card1_box)
        col_box.pack_start(card1_event, False, False, 0)

        card2_event = Gtk.EventBox()
        card2_event.set_visible_window(False)

        card2_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card2_box.get_style_context().add_class("desktop-widget-card")
        card2_box.get_style_context().add_class("widget-sysinfo-card")
        card2_box.set_size_request(269, -1)

        card2_event.connect("enter-notify-event", lambda w, e: card2_box.get_style_context().add_class("card-hover"))
        card2_event.connect("leave-notify-event", lambda w, e: card2_box.get_style_context().remove_class("card-hover"))

        info_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        info_row.set_homogeneous(True)

        b1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        b1.get_style_context().add_class("sysinfo-box-gradient")
        b1.get_style_context().add_class("gradient-sunset")
        l1_title = Gtk.Label()
        l1_title.get_style_context().add_class("sysinfo-sub-label")
        l1_title.set_markup(f"<span font_family='Inter, Sans' font='8' weight='700' color='{DARK_RUBY}'>desktop</span>")
        l1_val = Gtk.Label()
        l1_val.get_style_context().add_class("sysinfo-main-label")
        l1_val.set_markup(f"<span font_family='Inter, Sans' font='13.5' weight='800' color='{DARK_RUBY}'>hyprland</span>")
        b1.pack_start(l1_title, False, False, 2)
        b1.pack_start(l1_val, False, False, 2)
        info_row.pack_start(b1, True, True, 0)

        b2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        b2.get_style_context().add_class("sysinfo-box-solid")
        l2_title = Gtk.Label()
        l2_title.get_style_context().add_class("sysinfo-sub-label")
        l2_title.set_markup(f"<span font_family='Inter, Sans' font='8' weight='700' color='{SOFT_PINK}'>uptime</span>")
        self.lbl_uptime_val = Gtk.Label()
        self.lbl_uptime_val.get_style_context().add_class("sysinfo-main-label")
        self.lbl_uptime_val.set_markup(f"<span font_family='Inter, Sans' font='13.5' weight='800' color='{CREAM_WHITE}'>{get_uptime_str()}</span>")
        b2.pack_start(l2_title, False, False, 2)
        b2.pack_start(self.lbl_uptime_val, False, False, 2)
        info_row.pack_start(b2, True, True, 0)

        card2_box.pack_start(info_row, True, True, 0)
        card2_event.add(card2_box)
        col_box.pack_start(card2_event, False, False, 0)

        self.add(col_box)
        GLib.timeout_add_seconds(60, self.update_uptime_tick)
