#!/usr/bin/env python3
# control_center.py — Control Center and notifications panel entrypoint.

import os
import signal
import sys
import threading

import cairo

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from control_center_pkg.constants import (  # noqa: E402
    VIVID_RED,
    LIGHT_RED,
    DEEP_WINE,
    SOFT_WINE,
    DARK_WINE,
    DARK_RUBY,
    LIGHT_CYAN,
    SOFT_PINK,
    HAS_LAYER_SHELL,
    PID_FILE,
    GtkLayerShell,
    hex_to_rgba,
)
from gi.repository import Gdk, GLib, Gtk, Pango, PangoCairo  # noqa: E402
from control_center_pkg.interaction_mixin import ControlCenterInteractionMixin  # noqa: E402
from control_center_pkg.render_mixin import ControlCenterRenderMixin  # noqa: E402
from control_center_pkg.services_mixin import ControlCenterServicesMixin  # noqa: E402
from control_center_pkg.shapes import (  # noqa: E402,F401
    create_bottom_red_casing_path,
    create_top_red_casing_path,
    draw_pokeball_dual_slider,
    format_relative_time,
    get_badge_info,
)
from ui_core import DraggablePopup, draw_curved_kerned_cached, get_cursor_pos, get_monitor_geometry  # noqa: E402


class PokedexControlCenter(
    Gtk.Window,
    ControlCenterServicesMixin,
    ControlCenterInteractionMixin,
    ControlCenterRenderMixin,
):
    def __init__(self):
        super().__init__(title="Control Center")
        self.set_name("control-center-window")
        self.set_wmclass("control-center", "control-center")
        self.set_decorated(False)
        self.set_resizable(False)

        self.base_w = 388.0
        self.base_h = 786.0
        self.W_canvas = 380.0
        self.H_canvas = 766.0
        self.set_default_size(int(self.W_canvas), int(self.H_canvas))
        self.set_size_request(int(self.W_canvas), int(self.H_canvas))

        self.current_page = "controls"
        self.dragging_slider = None
        self.hovered_item = None

        if "--open" in sys.argv:
            self.anim_state = "open"
            self.anim_progress = 1.0
        else:
            self.anim_state = "closed"
            self.anim_progress = 0.0
        self.anim_start_time = None
        self.anim_duration = 0.30
        self._cached_top_casing = None
        self._cached_bot_casing = None
        self._cached_content_surf = None
        self._cached_content_page = None
        self._tick_id = None
        self.quit_after_close = False

        self.pango_font_tile_icon = Pango.FontDescription("JetBrains Mono Nerd Font 20")
        self.pango_font_tile_title = Pango.FontDescription("JetBrains Mono Nerd Font Bold 10")
        self.pango_font_tile_val = Pango.FontDescription("JetBrains Mono Nerd Font Bold 10")
        self._warmup_cache()

        self.vol_val = 0.35
        self.bri_val = 0.60
        self.bt_enabled = False
        self.bt_device = ""
        self.power_mode = "Performance"
        self.ime_text = "Vietnamese"
        self.wifi_text, self.wifi_ssid = "Connected", ""
        self.notifications = self.load_notifications()
        self.notif_page_idx = 0
        self.last_vol_set_time = 0.0
        self.last_bri_set_time = 0.0
        self.last_slider_drag_time = 0.0

        self.wifi_networks = []
        self.wifi_scanning = False
        self.wifi_connecting = False
        self.wifi_status_msg = ""
        self.wifi_page_idx = 0
        self.wifi_password_prompt_ssid = None
        self.wifi_password_input = ""
        self.wifi_radio_enabled = True

        threading.Thread(target=self.async_refresh_status, daemon=True).start()

        self.pad_x = 4.0
        self.x_left = self.pad_x
        self.x_right = self.pad_x + 380.0
        self.W_shell = 380.0
        self.cx = self.pad_x + self.W_shell / 2.0
        self.device_r = 24.0

        self.r_inner = 82.0
        self.r_outer = 124.0
        self.r_chassis = 129.0
        self.r_dark = 133.0
        self.chassis_thick = 5.0
        self.dark_thick = 4.0
        self.grooves = [(48.0, 52.0), (96.0, 100.0)]
        self.cut_y = 13.0
        self.cuff_ext = 2.5
        self.notch_d = 2.0
        self.trans = 1.8
        self.cy_pokeball = 468.0
        self.socket_well_y = 636.5
        self.top_mark_offset = 32.0

        self.c_casing_l = hex_to_rgba(VIVID_RED)[:3]
        self.c_casing_m = hex_to_rgba(LIGHT_RED)[:3]
        self.c_casing_r = hex_to_rgba(VIVID_RED)[:3]
        self.c_border_3d = hex_to_rgba(DARK_RUBY, 0.98)
        self.c_tactile_white = (1.0, 1.0, 1.0, 0.65)
        self.c_casing_border = self.c_border_3d

        self.c_band_stop0 = hex_to_rgba(DARK_WINE)[:3]
        self.c_band_stop1 = hex_to_rgba(DEEP_WINE)[:3]
        self.c_band_stop2 = hex_to_rgba(DARK_WINE)[:3]
        self.c_band_stroke = self.c_border_3d
        self.c_slider_dark = hex_to_rgba(SOFT_WINE)[:3]
        self.c_pwr_bg = hex_to_rgba(SOFT_WINE)[:3]
        self.c_chassis = hex_to_rgba(SOFT_PINK)[:3]
        self.c_flange = hex_to_rgba(DARK_WINE)[:3]

        self.c_accent = VIVID_RED
        self.c_accent_rgb = hex_to_rgba(VIVID_RED)[:3]
        self.c_accent_hover = LIGHT_RED
        self.c_accent_hover_rgb = hex_to_rgba(LIGHT_RED)[:3]
        self.c_holo_top = hex_to_rgba(LIGHT_CYAN)[:3]
        self.c_holo_mid = hex_to_rgba(LIGHT_CYAN)[:3]
        self.c_holo_bot = hex_to_rgba(LIGHT_CYAN)[:3]
        self.holo_alpha_top = 0.58
        self.holo_alpha_mid = 0.52
        self.holo_alpha_bot = 0.58

        def cc_bounds(x, y, mon_w, mon_h):
            min_x = 14
            max_x = mon_w - int(self.W_canvas) - 14
            if self.anim_state in ("closed", "closing"):
                min_y = 14 - 180
                max_y = mon_h - 52 - 600 - 14
            else:
                min_y = 14
                max_y = max(min_y, mon_h - 52 - int(self.H_canvas) - 14)
            if max_y < min_y:
                max_y = min_y
            return max(min_x, min(max_x, x)), max(min_y, min(max_y, y))

        self.drag_manager = DraggablePopup(
            self,
            name="control_center",
            default_pos=lambda mw, mh: (mw - int(self.W_canvas) - 14, 14),
            bounds_fn=cc_bounds,
            drag_threshold=14.0,
        )
        self.drag_manager.init_layer_shell(
            namespace="control-center",
            layer=GtkLayerShell.Layer.TOP if HAS_LAYER_SHELL else None,
            keyboard_mode=GtkLayerShell.KeyboardMode.ON_DEMAND if HAS_LAYER_SHELL else None,
        )

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.set_app_paintable(True)

        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
            | Gdk.EventMask.KEY_PRESS_MASK
            | Gdk.EventMask.SCROLL_MASK
        )

        self.connect("draw", self.on_draw)
        self.connect("button-press-event", self.on_button_press)
        self.connect("button-release-event", self.on_button_release)
        self.connect("motion-notify-event", self.on_motion_notify)
        self.connect("leave-notify-event", self.on_leave_notify)
        self.connect("key-press-event", self.on_key_press)
        self.connect("scroll-event", self.on_scroll)

        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, self.on_sigusr1)
        GLib.timeout_add(1500, self.refresh_status_tick)

        self._bake_casings()
        self._bake_content()

    def _warmup_cache(self):
        try:
            dummy_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 10, 10)
            dummy_cr = cairo.Context(dummy_surf)
            draw_curved_kerned_cached(dummy_cr, "CONTROL CENTER", 0, 0)
            draw_curved_kerned_cached(dummy_cr, "NOTIFICATIONS", 0, 0)
            draw_curved_kerned_cached(dummy_cr, "WI-FI NETWORKS", 0, 0)
            for f_desc, txt in (
                ("JetBrains Mono Nerd Font 20", "󰌌󰤨󰤮󰖪󰂯󰂱󰂲󰓅󰾅󰌪󰌾󰂚"),
                ("JetBrains Mono Nerd Font Bold 10", "Input Wi-Fi Bluetooth Power Mode Vietnamese English Connected Disconnected Disabled Balanced Performance"),
                ("DejaVu Sans Bold 8.5", "CONTROL CENTER NOTIFICATIONS WI-FI NETWORKS"),
            ):
                layout = PangoCairo.create_layout(dummy_cr)
                layout.set_font_description(Pango.FontDescription(f_desc))
                layout.set_text(txt, -1)
                layout.get_pixel_extents()
        except Exception:
            pass

    @property
    def current_win_x(self):
        return self.drag_manager.current_x

    @current_win_x.setter
    def current_win_x(self, val):
        self.drag_manager.current_x = val

    @property
    def current_win_y(self):
        return self.drag_manager.current_y

    @current_win_y.setter
    def current_win_y(self, val):
        self.drag_manager.current_y = val

    @property
    def is_dragging(self):
        return self.drag_manager.is_dragging

    def get_cursor_pos(self):
        return get_cursor_pos()

    def get_monitor_geometry(self):
        return get_monitor_geometry()

    def save_window_pos(self):
        self.drag_manager.save_position()

    def reset_window_pos(self):
        self.drag_manager.reset_to_default()

    def on_sigusr1(self, *args):
        page_file = "/tmp/control_center_page.txt"
        target_page = None
        if os.path.exists(page_file):
            try:
                with open(page_file, "r") as f:
                    target_page = f.read().strip()
                os.remove(page_file)
            except Exception:
                pass

        if self.anim_state in ("open", "opening"):
            if target_page and target_page in ("controls", "notifications", "wifi"):
                if self.current_page != target_page:
                    self.current_page = target_page
                    if target_page == "wifi":
                        self.scan_wifi_networks()
                    elif target_page == "notifications":
                        self.notifications = self.load_notifications()
                        self.notif_page_idx = 0
                    self._bake_content()
                    self.queue_draw()
                    return GLib.SOURCE_CONTINUE
            self.start_close_animation(quit_after=True)
        else:
            self.close_and_quit()
        return GLib.SOURCE_CONTINUE

    def start_open_animation(self):
        if self.anim_state in ("open", "opening"):
            return

        mon_w, mon_h = self.get_monitor_geometry()
        min_open_y = 14
        max_open_y = max(min_open_y, mon_h - 52 - int(self.H_canvas) - 14)
        target_y = max(min_open_y, min(max_open_y, self.current_win_y))
        target_x = max(14, min(mon_w - int(self.W_canvas) - 14, self.current_win_x))

        self.anim_start_x = self.current_win_x
        self.anim_start_y = self.current_win_y
        self.anim_target_x = target_x
        self.anim_target_y = target_y

        self.anim_state = "opening"
        self.anim_start_time = None
        self.anim_duration = 0.30
        self._bake_content()
        if self._tick_id is None:
            self._tick_id = self.add_tick_callback(self._on_anim_tick)

    def start_close_animation(self, quit_after=False):
        if self.anim_state in ("closed", "closing"):
            if quit_after:
                self.close_and_quit()
            return

        self.anim_state = "closing"
        self.anim_start_time = None
        self.anim_duration = 0.22
        self.quit_after_close = quit_after
        if self._tick_id is None:
            self._tick_id = self.add_tick_callback(self._on_anim_tick)

    def _on_anim_tick(self, widget, frame_clock):
        frame_time = frame_clock.get_frame_time() / 1e6
        if self.anim_start_time is None:
            self.anim_start_time = frame_time

        elapsed = frame_time - self.anim_start_time
        t = min(1.0, max(0.0, elapsed / self.anim_duration))
        e = t * t * t * (t * (t * 6.0 - 15.0) + 10.0)

        if self.anim_state == "opening":
            self.anim_progress = e
            if hasattr(self, 'anim_start_y') and hasattr(self, 'anim_target_y'):
                if self.anim_start_x != self.anim_target_x or self.anim_start_y != self.anim_target_y:
                    cur_x = self.anim_start_x + (self.anim_target_x - self.anim_start_x) * e
                    cur_y = self.anim_start_y + (self.anim_target_y - self.anim_start_y) * e
                    self.drag_manager.set_position(cur_x, cur_y, save=False, clamp=False)
            self.queue_draw()
            if t >= 1.0:
                self.anim_progress = 1.0
                self.anim_state = "open"
                self._tick_id = None
                if hasattr(self, 'anim_target_x') and hasattr(self, 'anim_target_y'):
                    self.drag_manager.set_position(self.anim_target_x, self.anim_target_y, save=True, clamp=True)
                self.queue_draw()
                return False
        elif self.anim_state == "closing":
            self.anim_progress = max(0.0, 1.0 - e)
            self.queue_draw()
            if t >= 1.0:
                self.anim_progress = 0.0
                self.anim_state = "closed"
                self._tick_id = None
                self.queue_draw()
                if getattr(self, "quit_after_close", False):
                    self.close_and_quit()
                return False

        return True

    def close_and_quit(self):
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
        Gtk.main_quit()


def main():
    signal.signal(signal.SIGTERM, lambda *_: GLib.idle_add(Gtk.main_quit))
    signal.signal(signal.SIGINT, lambda *_: GLib.idle_add(Gtk.main_quit))

    try:
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass

    app = PokedexControlCenter()
    if "--open" in sys.argv:
        app.anim_state = "open"
        app.anim_progress = 1.0
    if "--page" in sys.argv:
        try:
            target = sys.argv[sys.argv.index("--page") + 1]
            if target in ("controls", "notifications", "wifi"):
                app.current_page = target
        except Exception:
            pass
    elif "wifi" in sys.argv:
        app.current_page = "wifi"

    page_file = "/tmp/control_center_page.txt"
    if os.path.exists(page_file):
        try:
            with open(page_file, "r") as f:
                target = f.read().strip()
            os.remove(page_file)
            if target in ("controls", "notifications", "wifi"):
                app.current_page = target
        except Exception:
            pass

    if app.current_page == "wifi":
        app.scan_wifi_networks()
    elif app.current_page == "notifications":
        app.notifications = app.load_notifications()
        app.notif_page_idx = 0
    app.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
