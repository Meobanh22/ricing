#!/usr/bin/env python3
# settings.py — Settings and device status popup widget entrypoint.

import os
import signal
import sys

import cairo

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from settings_pkg.constants import (  # noqa: E402
    ANIM_DURATION,
    HAS_LAYER_SHELL,
    OPEN_H,
    OPEN_W,
    PID_FILE,
    GtkLayerShell,
)
from gi.repository import Gdk, GLib, Gtk  # noqa: E402
from settings_pkg.interaction_mixin import SettingsInteractionMixin  # noqa: E402
from settings_pkg.render_mixin import SettingsRenderMixin  # noqa: E402
from settings_pkg.services_mixin import SettingsServicesMixin  # noqa: E402
from settings_pkg.shapes import (  # noqa: E402,F401
    draw_ribbon_bow,
    ellipse_path,
    front_cover_path,
    left_panel_path,
    right_panel_path,
)
from ui_core import DraggablePopup, get_cursor_pos, get_monitor_geometry  # noqa: E402


class SettingsWindow(
    Gtk.Window,
    SettingsServicesMixin,
    SettingsRenderMixin,
    SettingsInteractionMixin,
):
    def __init__(self):
        super().__init__(title="Settings")
        self.set_name("settings-window")
        self.set_wmclass("settings", "settings")
        self.set_role("settings")
        self.set_decorated(False)
        self.set_resizable(False)

        self.anim_state = "closed"
        self.open_progress = 0.0
        self.anim_start_time = None
        self.anim_duration = ANIM_DURATION
        self.anim_start_p = 0.0
        self._tick_id = None
        self._cache_front_cover = None
        self._cache_right_panel = None
        self._cache_left_panel = None

        self.current_w = OPEN_W
        self.current_h = OPEN_H
        self.set_size_request(OPEN_W, OPEN_H)
        self.set_default_size(OPEN_W, OPEN_H)

        cx = OPEN_W / 2.0
        margin_x = 33.0
        panel_w = cx - margin_x
        top_y = 30.0
        bot_y = top_y + 585.0
        extrusion_h = 4.2

        def settings_bounds(x, y, mon_w, mon_h):
            if self.anim_state in ("closed", "opening"):
                min_x = 10 - int(cx)
                max_x = mon_w - int(cx + panel_w) - 10
            else:
                min_x = 10 - int(margin_x)
                max_x = mon_w - int(cx + panel_w) - 10
            min_y = 10 - int(top_y)
            max_y = mon_h - int(bot_y + extrusion_h) - 10
            return max(min_x, min(max_x, x)), max(min_y, min(max_y, y))

        self.drag_manager = DraggablePopup(
            self,
            name="settings",
            default_pos=lambda mw, mh: (mw - OPEN_W - 20, 50),
            bounds_fn=settings_bounds,
            drag_threshold=5.0,
        )
        self.drag_manager.init_layer_shell(
            namespace="settings",
            keyboard_mode=GtkLayerShell.KeyboardMode.ON_DEMAND if HAS_LAYER_SHELL else None,
        )

        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)

        self.set_app_paintable(True)
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.SCROLL_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
        )

        self.connect("draw", self.on_draw)
        self.connect("button-press-event", self.on_button_press)
        self.connect("button-release-event", self.on_button_release)
        self.connect("motion-notify-event", self.on_motion_notify)
        self.connect("scroll-event", self.on_scroll)
        self.connect("key-press-event", self.on_key_press)
        self.connect("destroy", self.on_destroy)
        self.connect("realize", self.on_realize)

        self.left_tab = "settings"
        self.right_page = "controls"
        self.hover_element = None
        self.active_slider = None

        self.volume = 50
        self.is_muted = False
        self.brightness = 50
        self.bt_enabled = True
        self.power_mode = "balanced"
        self.ime_text = "Vietnamese"
        self.wifi_ssid = "Connecting..."
        self.media_title = ""
        self.media_artist = ""
        self.media_status = "Stopped"
        self.notifications = []

        self.load_assets()
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))

        signal.signal(signal.SIGUSR1, self.handle_sigusr1)
        self.refresh_all_services()
        GLib.timeout_add(1500, self.periodic_poll)

    def on_realize(self, widget):
        self.update_input_shape()

    def update_input_shape(self):
        if not self.get_window():
            return
        if self.anim_state == "closed":
            cx = OPEN_W / 2.0
            panel_w = cx - 33.0
            region = cairo.Region(cairo.RectangleInt(int(cx), 30, int(panel_w + 10), 600))
            self.input_shape_combine_region(region)
        else:
            self.input_shape_combine_region(None)

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

    def start_open_animation(self):
        if self.anim_state in ("opening", "open"):
            return
        mon_w, _ = self.get_monitor_geometry()
        cx = OPEN_W / 2.0
        panel_w = cx - 33.0
        target_x = max(10 - 33, min(mon_w - int(cx + panel_w) - 10, self.current_win_x))
        self.anim_start_x = self.current_win_x
        self.anim_target_x = target_x

        self.anim_start_p = self.open_progress if self.anim_state == "closing" else 0.0
        self.anim_state = "opening"
        self.anim_start_time = None
        self.update_input_shape()
        self._ensure_caches()
        if self._tick_id is None:
            self._tick_id = self.add_tick_callback(self._on_anim_tick)

    def start_close_animation(self, quit_after=False):
        if self.anim_state in ("closing", "closed"):
            return
        self.anim_start_p = self.open_progress if self.anim_state == "opening" else 1.0
        self.anim_state = "closing"
        self.anim_start_time = None
        self.quit_after_close = quit_after
        self._ensure_caches()
        if self._tick_id is None:
            self._tick_id = self.add_tick_callback(self._on_anim_tick)

    def _on_anim_tick(self, widget, frame_clock):
        frame_time = frame_clock.get_frame_time() / 1e6
        if self.anim_start_time is None:
            self.anim_start_time = frame_time

        elapsed = frame_time - self.anim_start_time
        start_p = getattr(self, "anim_start_p", 0.0 if self.anim_state == "opening" else 1.0)
        target_p = 1.0 if self.anim_state == "opening" else 0.0
        dist = abs(target_p - start_p)
        effective_duration = max(0.05, self.anim_duration * (dist if dist > 0.05 else 1.0))
        linear_t = min(1.0, max(0.0, elapsed / effective_duration))

        if self.anim_state == "opening":
            self.open_progress = start_p + (1.0 - start_p) * linear_t
            if hasattr(self, 'anim_start_x') and hasattr(self, 'anim_target_x') and self.anim_start_x != self.anim_target_x:
                e = linear_t * linear_t * (3.0 - 2.0 * linear_t)
                cur_x = self.anim_start_x + (self.anim_target_x - self.anim_start_x) * e
                self.drag_manager.set_position(cur_x, self.current_win_y, save=False, clamp=False)
            self.queue_draw()
            if linear_t >= 1.0:
                self.anim_state = "open"
                self.open_progress = 1.0
                self._tick_id = None
                if hasattr(self, 'anim_target_x'):
                    self.drag_manager.set_position(self.anim_target_x, self.current_win_y, save=True, clamp=True)
                self.queue_draw()
                return False
        elif self.anim_state == "closing":
            self.open_progress = start_p - start_p * linear_t
            self.queue_draw()
            if linear_t >= 1.0:
                self.anim_state = "closed"
                self.open_progress = 0.0
                self._tick_id = None
                self.queue_draw()
                if getattr(self, "quit_after_close", False):
                    self.close_and_quit()
                else:
                    self.update_input_shape()
                return False
        return True

    def handle_sigusr1(self, signum, frame):
        GLib.idle_add(self._sigusr1_action)

    def _sigusr1_action(self):
        self.close_and_quit()
        return False

    def close_and_quit(self):
        if getattr(self, "_tick_id", None):
            try:
                self.remove_tick_callback(self._tick_id)
            except Exception:
                pass
            self._tick_id = None
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
        Gtk.main_quit()

    def on_destroy(self, widget):
        self.close_and_quit()


def main():
    app = SettingsWindow()
    app.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
