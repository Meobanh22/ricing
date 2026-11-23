#!/usr/bin/env python3
# settings.py — Settings and device status popup widget.

import os
import sys
import time
import json
import signal
import subprocess
import shutil
import math
import threading
import socket
import glob
import cairo
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
gi.require_version('GdkPixbuf', '2.0')
try:
    gi.require_version('GtkLayerShell', '0.1')
    from gi.repository import GtkLayerShell
    HAS_LAYER_SHELL = True
except Exception:
    HAS_LAYER_SHELL = False

from gi.repository import Gtk, Gdk, GLib, Pango, PangoCairo, GdkPixbuf

# Resolve script & service paths
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_ROOT = os.path.dirname(SCRIPTS_DIR)
SYSTEM_DIR = os.path.join(SCRIPTS_ROOT, "system")
SERVICES_DIR = os.path.join(SCRIPTS_ROOT, "services")
HYPR_DIR = os.path.dirname(SCRIPTS_ROOT)

for p in (SCRIPTS_DIR, SCRIPTS_ROOT, SYSTEM_DIR, SERVICES_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from services.audio import AudioService
from services.brightness import BrightnessService
from services.bluetooth import BluetoothService
from services.power import PowerService
from ui_core import (
    DraggablePopup, get_cursor_pos, get_monitor_geometry,
    squircle, resolve_asset, clear_surface
)

PID_FILE = "/tmp/settings.pid"
POSITION_CACHE = "/tmp/settings_pos.json"
CACHE_FILE = os.path.expanduser("~/.cache/notifications.json")
ASSETS_DIR = os.path.join(HYPR_DIR, "assets")
FALLBACK_ASSETS_DIR = os.path.expanduser("~/.config/hypr/assets")

# Dimensions
CLOSED_W = 420
CLOSED_H = 675
OPEN_W = 930
OPEN_H = 690

# Animation Timings
ANIM_DURATION = 0.38                     # Clamshell flip transition duration in seconds

# Palette tokens & colors
try:
    from palette import (
        hex_to_rgba,
        C_BG_WIN, C_BG_CARD, C_BG_CARD_HOVER, C_BG_SUBTLE,
        C_ACCENT, C_ACCENT_HOVER, C_TEXT_PRI, C_TEXT_SEC, C_TEXT_MUT, C_TEXT_INV,
        C_STATUS_WARN, C_STATUS_CRIT, C_STATUS_SUCC, C_RIBBON,
        C_BG_WAYBAR, C_BORDER_3D, C_BG_CREAM,
        C_POKEPUFF_PINK, SUNSET_STOPS
    )
    C_SUNSET_PINK = SUNSET_STOPS[2][1]    # #FF7299 (sunset gradient 50% anime pink)
    C_SUNSET_PASTEL = SUNSET_STOPS[3][1]  # #EAA2C6 (sunset gradient 75% pastel pink)
    C_SUNSET_ROSE = SUNSET_STOPS[0][1]    # #A3183D (sunset gradient 0% anime rose)
except ImportError:
    C_BG_WIN = "#201011"
    C_BG_CARD = "#2A1A1E"
    C_BG_CARD_HOVER = "#3A222A"
    C_BG_SUBTLE = "#301F20"
    C_ACCENT = "#DC1A36"
    C_ACCENT_HOVER = "#F02D4C"
    C_TEXT_PRI = "#FFF0F5"
    C_TEXT_SEC = "#E8C2D0"
    C_TEXT_MUT = "#A68595"
    C_TEXT_INV = "#FFFFFF"
    C_STATUS_WARN = "#FFB86C"
    C_STATUS_CRIT = "#DC1A36"
    C_STATUS_SUCC = "#8FBC8F"
    C_RIBBON = "#50A6FF"
    C_BG_WAYBAR = "#851733"
    C_BORDER_3D = "#4D0A1C"
    C_BG_CREAM = "rgba(255, 240, 245, 0.96)"
    C_POKEPUFF_PINK = "#FF5C8A"
    C_SUNSET_PINK = "#FF7299"
    C_SUNSET_PASTEL = "#EAA2C6"
    C_SUNSET_ROSE = "#A3183D"
    def hex_to_rgba(hex_code, alpha=1.0):
        h = hex_code.strip().lstrip('#')
        if len(h) == 6:
            return (int(h[0:2], 16)/255.0, int(h[2:4], 16)/255.0, int(h[4:6], 16)/255.0, alpha)
        return (1.0, 1.0, 1.0, alpha)

# Tactile Anime Shadow & Shell Colors
COLOR_BORDER_SHADOW = hex_to_rgba(C_BORDER_3D, 0.98)   # #4D0A1C tactile border
COLOR_PINK_TOP = hex_to_rgba(C_SUNSET_PINK, 1.0)       # #FF7299 vibrant anime pink from sunset gradient
COLOR_PINK_BOT = hex_to_rgba(C_SUNSET_PASTEL, 1.0)     # #EAA2C6 soft pastel pink from sunset gradient
COLOR_PINK_INSIDE = hex_to_rgba(C_TEXT_SEC, 1.0)       # #E8C2D0 soft anime pink from tokens.json (soft_pink)
COLOR_PINK_ROSE = hex_to_rgba(C_SUNSET_ROSE, 1.0)       # #A3183D clean anime rose shadow
COLOR_PINK_3D_DARK = hex_to_rgba(C_BORDER_3D, 1.0)      # #4D0A1C darker 3D depth
COLOR_PINK_3D_BOT  = hex_to_rgba(C_BG_WIN, 1.0)         # #201011 bottom 3D shade

# Pokédex Red Colors (matches control_center.py casing red)
COLOR_RIBBON_TOP = hex_to_rgba(C_ACCENT_HOVER, 1.0)    # #F02D4C
COLOR_RIBBON_MID = hex_to_rgba(C_ACCENT, 1.0)          # #DC1A36
COLOR_RIBBON_BOT = hex_to_rgba(C_BG_WAYBAR, 1.0)        # #851733


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
    """Front cover shell: matches right_panel_path contour exactly so they stack perfectly."""
    right_panel_path(cr, x, y, w, h, r, r_inner)

def ellipse_path(cr, cx, cy, rx, ry):
    k = 0.55228475
    kx = k * rx
    ky = k * ry
    cr.new_sub_path()
    cr.move_to(cx + rx, cy)
    cr.curve_to(cx + rx, cy + ky, cx + kx, cy + ry, cx, cy + ry)
    cr.curve_to(cx - kx, cy + ry, cx - rx, cy + ky, cx - rx, cy)
    cr.curve_to(cx - rx, cy - ky, cx - kx, cy - ry, cx, cy - ry)
    cr.curve_to(cx + kx, cy - ry, cx + rx, cy - ky, cx + rx, cy)
    cr.close_path()



def draw_ribbon_bow(cr, bx, by, ribbon_ang=0.0, scale=1.0):
    """
    Renders decorative ribbon bow.
    Symmetrically aligned with the ribbon axis.
    Tapered outer wing edges with creases.
    """
    cr.save()
    cr.translate(bx, by)
    if ribbon_ang != 0.0:
        cr.rotate(ribbon_ang)
    if scale != 1.0:
        cr.scale(scale, scale)

    # 1. Loops / Wings (symmetric folded butterfly wings along the ribbon)
    # Wing spreads: tip at x = ±70, y from -35 to +35 (height = 70px, exceeds ribbon width 34px)
    wing_w = 70.0
    wing_h = 35.0

    # Center knot dimensions: HORIZONTAL ellipse (rx > ry)
    rx = 18.0
    ry = 11.5

    # Left Wing (flatter outer fold edge with softly rounded corners, eliminating bulbous roundness)
    cr.new_sub_path()
    cr.move_to(-rx * 0.65, -7.0)
    cr.curve_to(-35.0, -wing_h * 0.95, -55.0, -wing_h * 0.95, -wing_w + 3.0, -wing_h * 0.72)
    cr.curve_to(-wing_w - 1.5, -wing_h * 0.35, -wing_w - 1.5, wing_h * 0.35, -wing_w + 3.0, wing_h * 0.72)
    cr.curve_to(-55.0, wing_h * 0.95, -35.0, wing_h * 0.95, -rx * 0.65, 7.0)
    cr.close_path()

    pat_l = cairo.LinearGradient(-wing_w, -wing_h, -rx, wing_h)
    pat_l.add_color_stop_rgba(0.0, *COLOR_RIBBON_TOP)
    pat_l.add_color_stop_rgba(0.5, *COLOR_RIBBON_MID)
    pat_l.add_color_stop_rgba(1.0, *COLOR_RIBBON_BOT)
    cr.set_source(pat_l)
    cr.fill_preserve()
    cr.set_source_rgba(*COLOR_BORDER_SHADOW)
    cr.set_line_width(2.0)
    cr.stroke()

    # Left inner fold line
    cr.move_to(-rx * 0.65, 0)
    cr.curve_to(-35.0, -wing_h * 0.25, -55.0, -wing_h * 0.15, -wing_w * 0.70, 0)
    cr.set_source_rgba(*COLOR_BORDER_SHADOW)
    cr.set_line_width(1.3)
    cr.stroke()

    # Right Wing (exact mirror image across x=0)
    cr.new_sub_path()
    cr.move_to(rx * 0.65, -7.0)
    cr.curve_to(35.0, -wing_h * 0.95, 55.0, -wing_h * 0.95, wing_w - 3.0, -wing_h * 0.72)
    cr.curve_to(wing_w + 1.5, -wing_h * 0.35, wing_w + 1.5, wing_h * 0.35, wing_w - 3.0, wing_h * 0.72)
    cr.curve_to(55.0, wing_h * 0.95, 35.0, wing_h * 0.95, rx * 0.65, 7.0)
    cr.close_path()

    pat_r = cairo.LinearGradient(wing_w, -wing_h, rx, wing_h)
    pat_r.add_color_stop_rgba(0.0, *COLOR_RIBBON_TOP)
    pat_r.add_color_stop_rgba(0.5, *COLOR_RIBBON_MID)
    pat_r.add_color_stop_rgba(1.0, *COLOR_RIBBON_BOT)
    cr.set_source(pat_r)
    cr.fill_preserve()
    cr.set_source_rgba(*COLOR_BORDER_SHADOW)
    cr.set_line_width(2.0)
    cr.stroke()

    # Right inner fold line
    cr.move_to(rx * 0.65, 0)
    cr.curve_to(35.0, -wing_h * 0.25, 55.0, -wing_h * 0.15, wing_w * 0.70, 0)
    cr.set_source_rgba(*COLOR_BORDER_SHADOW)
    cr.set_line_width(1.3)
    cr.stroke()

    # 2. Center Knot Ellipse (elongated horizontally along the ribbon/wings)
    ellipse_path(cr, 0, 0, rx, ry)
    pat_knot = cairo.RadialGradient(-rx * 0.25, -ry * 0.35, 2.0, 0, 0, max(rx, ry))
    pat_knot.add_color_stop_rgb(0.0, 1.0, 0.45, 0.55)  # specular highlight
    pat_knot.add_color_stop_rgba(0.35, *COLOR_RIBBON_TOP)
    pat_knot.add_color_stop_rgba(1.0, *COLOR_RIBBON_BOT)
    cr.set_source(pat_knot)
    cr.fill_preserve()
    cr.set_source_rgba(*COLOR_BORDER_SHADOW)
    cr.set_line_width(2.0)
    cr.stroke()

    # Vertical creases across the horizontal knot
    cr.move_to(-rx * 0.35, -ry * 0.70)
    cr.curve_to(-rx * 0.15, 0, -rx * 0.15, 0, -rx * 0.35, ry * 0.70)
    cr.set_source_rgba(*COLOR_BORDER_SHADOW)
    cr.set_line_width(1.1)
    cr.stroke()

    cr.move_to(rx * 0.35, -ry * 0.70)
    cr.curve_to(rx * 0.15, 0, rx * 0.15, 0, rx * 0.35, ry * 0.70)
    cr.stroke()

    cr.restore()


class SettingsWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Settings")
        self.set_name("settings-window")
        self.set_wmclass("settings", "settings")
        self.set_role("settings")
        self.set_decorated(False)
        self.set_resizable(False)

        # Starts in closed state
        self.anim_state = "closed"   # "closed", "opening", "open", "closing"
        self.open_progress = 0.0     # 0.0 = closed, 1.0 = open
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

        # Draggable Popup Setup via shared DraggablePopup manager
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
            drag_threshold=5.0
        )
        self.drag_manager.init_layer_shell(
            namespace="settings",
            keyboard_mode=GtkLayerShell.KeyboardMode.ON_DEMAND if HAS_LAYER_SHELL else None
        )

        # Transparent RGBA surface
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        self.set_app_paintable(True)
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.SCROLL_MASK |
            Gdk.EventMask.LEAVE_NOTIFY_MASK
        )

        self.connect("draw", self.on_draw)
        self.connect("button-press-event", self.on_button_press)
        self.connect("button-release-event", self.on_button_release)
        self.connect("motion-notify-event", self.on_motion_notify)
        self.connect("scroll-event", self.on_scroll)
        self.connect("key-press-event", self.on_key_press)
        self.connect("destroy", self.on_destroy)
        self.connect("realize", self.on_realize)

        # Pages and Tabs
        self.left_tab = "settings"     # "settings", "map", "guide"
        self.right_page = "controls"    # "controls", "notifications"
        self.hover_element = None
        self.active_slider = None       # "volume", "brightness"

        # Services & State Data
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

        # Load Anime Assets
        self.load_assets()

        # Write PID file
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))

        # Register USR1 signal to close / dismiss on toggle
        signal.signal(signal.SIGUSR1, self.handle_sigusr1)

        # Initial data fetch & periodic pollers
        self.refresh_all_services()
        GLib.timeout_add(1500, self.periodic_poll)

    def on_realize(self, widget):
        self.update_input_shape()

    def update_input_shape(self):
        if not self.get_window():
            return
        if self.anim_state == "closed":
            cx = OPEN_W / 2.0
            margin_x = 33.0
            panel_w = cx - margin_x
            panel_h = 585.0
            top_y = 30.0
            region = cairo.Region(cairo.RectangleInt(
                int(cx),
                int(top_y),
                int(panel_w + 10),
                int(panel_h + 15)
            ))
            self.input_shape_combine_region(region)
        else:
            self.input_shape_combine_region(None)

    # --- Draggable Properties & Wrappers ---
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

    def load_assets(self):
        def find_asset(name):
            p = resolve_asset(name)
            return p if p else None

        self.asset_bow = None
        self.asset_heart = None
        self.asset_hinge = None
        self.asset_map = None
        self.asset_guide = None

        p_bow = find_asset("serena_ribbon_bow_clean.png") or find_asset("serena_ribbon_bow.png")
        if p_bow:
            try:
                self.asset_bow = cairo.ImageSurface.create_from_png(p_bow)
            except Exception:
                pass

        p_heart = find_asset("serena_heart_button_clean.png") or find_asset("serena_heart_button.png")
        if p_heart:
            try:
                self.asset_heart = cairo.ImageSurface.create_from_png(p_heart)
            except Exception:
                pass

        p_hinge = find_asset("serena_hinge.png")
        if p_hinge:
            try:
                self.asset_hinge = cairo.ImageSurface.create_from_png(p_hinge)
            except Exception:
                pass

        p_map = find_asset("serena_kalos_map.png")
        if p_map:
            try:
                self.asset_map = cairo.ImageSurface.create_from_png(p_map)
            except Exception:
                pass

        p_guide = find_asset("serena_dendemille_guide.png")
        if p_guide:
            try:
                self.asset_guide = cairo.ImageSurface.create_from_png(p_guide)
            except Exception:
                pass

    # ---------------- SERVICES & DATA ----------------
    def refresh_all_services(self):
        try:
            self.volume = AudioService.get_volume()
            self.is_muted = AudioService.is_muted()
        except Exception:
            pass
        try:
            self.brightness = BrightnessService.get_brightness()
        except Exception:
            pass
        try:
            self.bt_enabled = BluetoothService.is_enabled()
        except Exception:
            pass
        try:
            self.power_mode = PowerService.get_power_mode()
        except Exception:
            pass
        self.update_ime()
        self.update_wifi()
        self.update_media()
        self.load_notifications()

    def update_ime(self):
        ime_sh = os.path.join(SCRIPTS_DIR, "get_ime.sh")
        if os.path.exists(ime_sh):
            try:
                out = subprocess.check_output([ime_sh], text=True, timeout=1).strip()
                if "VIE" in out or "Tiếng Việt" in out:
                    self.ime_text = "Vietnamese"
                elif "ENG" in out:
                    self.ime_text = "English"
            except Exception:
                pass

    def update_wifi(self):
        try:
            res = subprocess.run(["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"],
                                 capture_output=True, text=True, timeout=1)
            lines = res.stdout.strip().split("\n")
            active_ssid = None
            for line in lines:
                if line.startswith("yes:"):
                    active_ssid = line.split(":", 1)[1]
                    break
            self.wifi_ssid = active_ssid if active_ssid else "Offline"
        except Exception:
            self.wifi_ssid = "Offline"

    def update_media(self):
        try:
            stat = subprocess.check_output(["playerctl", "status"], text=True, timeout=1).strip()
            self.media_status = stat if stat else "Stopped"
            if self.media_status in ("Playing", "Paused"):
                t = subprocess.check_output(["playerctl", "metadata", "--format", "{{title}}"], text=True, timeout=1).strip()
                a = subprocess.check_output(["playerctl", "metadata", "--format", "{{artist}}"], text=True, timeout=1).strip()
                self.media_title = t if t else "Playing"
                self.media_artist = a if a else "Unknown Artist"
            else:
                self.media_title = "No music playing"
                self.media_artist = ""
        except Exception:
            self.media_status = "Stopped"
            self.media_title = "No music playing"
            self.media_artist = ""

    def load_notifications(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r") as f:
                    self.notifications = json.load(f)
            except Exception:
                self.notifications = []
        else:
            self.notifications = []

    def periodic_poll(self):
        if self.anim_state != "closed":
            self.refresh_all_services()
            self.queue_draw()
        return True

    # ---------------- ANIMATION & STATE ----------------
    def start_open_animation(self):
        if self.anim_state in ("opening", "open"):
            return
        # Ensure open phone fits completely on screen horizontally
        mon_w, mon_h = self.get_monitor_geometry()
        cx = OPEN_W / 2.0
        margin_x = 33.0
        panel_w = cx - margin_x
        min_x = 10 - int(margin_x)
        max_x = mon_w - int(cx + panel_w) - 10
        target_x = max(min_x, min(max_x, self.current_win_x))
        self.anim_start_x = self.current_win_x
        self.anim_target_x = target_x

        current_p = self.open_progress if self.anim_state == "closing" else 0.0
        self.anim_state = "opening"
        self.anim_start_p = current_p
        self.anim_start_time = None
        self.update_input_shape()  # enables full window interactivity
        self._ensure_caches()
        if self._tick_id is None:
            self._tick_id = self.add_tick_callback(self._on_anim_tick)

    def start_close_animation(self, quit_after=False):
        if self.anim_state in ("closing", "closed"):
            return
        current_p = self.open_progress if self.anim_state == "opening" else 1.0
        self.anim_state = "closing"
        self.anim_start_p = current_p
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

            # Smoothly glide window to nearest valid position if needed
            if hasattr(self, 'anim_start_x') and hasattr(self, 'anim_target_x'):
                if self.anim_start_x != self.anim_target_x:
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
        if getattr(self, "_tick_id", None):
            try:
                self.remove_tick_callback(self._tick_id)
            except Exception:
                pass
            self._tick_id = None
        self.close_and_quit()

    # ---------------- DRAWING ----------------
    def on_draw(self, widget, cr):
        clear_surface(cr)

        alloc = widget.get_allocation()
        win_w = float(alloc.width)
        win_h = float(alloc.height)

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
        hw = 24.0
        hh = 80.0
        self.draw_small_hinge(cr, cx, top_y + 4.0, hw=hw, hh=hh, alpha=alpha)
        self.draw_small_hinge(cr, cx, bot_y - 4.0 - hh, hw=hw, hh=hh, alpha=alpha)

    def draw_front_cover(self, cr, x, y, w, h):
        r = 22.0
        r_inner = 18.0
        cx_mid = x + w / 2.0
        sr, sg, sb = COLOR_PINK_ROSE[0], COLOR_PINK_ROSE[1], COLOR_PINK_ROSE[2]

        # 1. Base vertical gradient (Serena Sunset Pink: #FF7299 -> #EAA2C6)
        cr.save()
        front_cover_path(cr, x, y, w, h, r, r_inner)
        pat_base = cairo.LinearGradient(cx_mid, y, cx_mid, y + h)
        pat_base.add_color_stop_rgba(0.00, *COLOR_PINK_TOP)
        pat_base.add_color_stop_rgba(1.00, *COLOR_PINK_BOT)
        cr.set_source(pat_base)
        cr.fill_preserve()
        cr.clip()

        # 2. Horizontal Cylindrical Curvature (Pure anime rose shading & smooth cylinder sheen)
        pat_x = cairo.LinearGradient(x, y, x + w, y)
        pat_x.add_color_stop_rgba(0.00, sr, sg, sb, 0.14)
        pat_x.add_color_stop_rgba(0.08, 0.0, 0.0, 0.0, 0.00)
        pat_x.add_color_stop_rgba(0.32, 1.0, 1.0, 1.0, 0.16)
        pat_x.add_color_stop_rgba(0.48, 1.0, 1.0, 1.0, 0.07)
        pat_x.add_color_stop_rgba(0.70, 0.0, 0.0, 0.0, 0.00)
        pat_x.add_color_stop_rgba(0.86, sr, sg, sb, 0.16)
        pat_x.add_color_stop_rgba(1.00, sr, sg, sb, 0.32)
        cr.set_source(pat_x)
        cr.paint()

        # 3. Specular Highlight Streak along right curved shoulder (Anime reflection from Image 1)
        pat_streak = cairo.LinearGradient(x + w * 0.82, y, x + w * 0.95, y)
        pat_streak.add_color_stop_rgba(0.00, 1.0, 1.0, 1.0, 0.00)
        pat_streak.add_color_stop_rgba(0.50, 1.0, 1.0, 1.0, 0.38)
        pat_streak.add_color_stop_rgba(1.00, 1.0, 1.0, 1.0, 0.00)
        cr.rectangle(x + w * 0.80, y, w * 0.20, h)
        cr.set_source(pat_streak)
        cr.fill()

        # Specular corner arc at bottom-right (matching Image 1 corner reflection)
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

        # 4. Top shoulder curvature roll-over (Soft rim)
        pat_top = cairo.LinearGradient(cx_mid, y, cx_mid, y + 32.0)
        pat_top.add_color_stop_rgba(0.00, 1.0, 1.0, 1.0, 0.22)
        pat_top.add_color_stop_rgba(0.60, 1.0, 1.0, 1.0, 0.06)
        pat_top.add_color_stop_rgba(1.00, 1.0, 1.0, 1.0, 0.00)
        cr.rectangle(x, y, w, 32.0)
        cr.set_source(pat_top)
        cr.fill()

        # 5. Bottom lip ambient occlusion (Rich rose shade + soft ground lift)
        pat_bot = cairo.LinearGradient(cx_mid, y + h - 38.0, cx_mid, y + h)
        pat_bot.add_color_stop_rgba(0.00, 0.0, 0.0, 0.0, 0.00)
        pat_bot.add_color_stop_rgba(0.80, sr, sg, sb, 0.18)
        pat_bot.add_color_stop_rgba(1.00, 1.00, 0.90, 0.95, 0.15)
        cr.rectangle(x, y + h - 38.0, w, 38.0)
        cr.set_source(pat_bot)
        cr.fill()

        # 6. Diagonal Ribbon following 3D curvature
        x1, y1 = x, y + h / 2.0
        x2, y2 = x + w, y
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)
        ang = math.atan2(dy, dx)
        rh = 34.0

        # Drop shadow under ribbon (anime rose shadow)
        cr.save()
        cr.translate(x1, y1)
        cr.rotate(ang)
        cr.rectangle(-40.0, -rh / 2.0 + 3.0, dist + 80.0, rh + 2.0)
        cr.set_source_rgba(sr, sg, sb, 0.26)
        cr.fill()
        cr.restore()

        # Diagonal ribbon band in Pokédex Red
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

        # Ribbon border lines with gold sheen
        for ey in [-rh / 2.0, rh / 2.0]:
            cr.move_to(-40.0, ey + (1.2 if ey < 0 else -1.2))
            cr.line_to(dist + 80.0, ey + (1.2 if ey < 0 else -1.2))
            cr.set_source_rgba(1.0, 0.88, 0.65, 0.50)
            cr.set_line_width(1.0)
            cr.stroke()

        # Ribbon curvature highlight where it crosses the cylinder
        pat_r_curv = cairo.LinearGradient(dist * 0.25, 0, dist * 0.65, 0)
        pat_r_curv.add_color_stop_rgba(0.00, 1.0, 1.0, 1.0, 0.00)
        pat_r_curv.add_color_stop_rgba(0.40, 1.0, 1.0, 1.0, 0.16)
        pat_r_curv.add_color_stop_rgba(0.70, 1.0, 1.0, 1.0, 0.00)
        cr.rectangle(-40.0, -rh / 2.0, dist + 80.0, rh)
        cr.set_source(pat_r_curv)
        cr.fill()

        cr.restore()  # unclip ribbon

        # 7. Vector Ribbon Bow with soft shadow underneath
        bx = x1 + dx * 0.50
        by = y1 + dy * 0.50
        cr.save()
        cr.translate(1.5, 2.5)
        draw_ribbon_bow(cr, bx, by, ribbon_ang=ang, scale=1.0)
        cr.set_source_rgba(sr, sg, sb, 0.25)
        cr.fill()
        cr.restore()
        draw_ribbon_bow(cr, bx, by, ribbon_ang=ang, scale=1.0)

        # Right clasp notch
        cr.rectangle(x + w - 5.0, y + 220.0, 5.0, 48.0)
        cr.set_source_rgba(0.20, 0.04, 0.08, 0.85)
        cr.fill()

        cr.restore()  # Unclip

        # 8. Molded 3D Inset Chamfer / Bevel Highlight
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

        # 9. Outer Tactile Border following the flat contour
        cr.save()
        front_cover_path(cr, x, y, w, h, r, r_inner)
        cr.set_source_rgba(*COLOR_BORDER_SHADOW)
        cr.set_line_width(2.4)
        cr.stroke()
        cr.restore()

    def draw_left_panel_casing(self, cr, lx, top_y, panel_w, panel_h, corner_r=22.0, r_inner=18.0):
        bot_y = top_y + panel_h
        cx_mid = lx + panel_w / 2.0
        t_wall = 9.5

        # 1. Solid anime pink casing base
        cr.save()
        left_panel_path(cr, lx, top_y, panel_w, panel_h, corner_r, r_inner)
        cr.set_source_rgba(*COLOR_PINK_INSIDE)
        cr.fill()
        cr.restore()

        # 2. Dark gray chassis walls on both sides (outer left and inner right)
        cr.save()
        left_panel_path(cr, lx, top_y, panel_w, panel_h, corner_r, r_inner)
        cr.clip()
        # Outer left wall
        cr.rectangle(lx, top_y, t_wall, panel_h)
        cr.set_source_rgba(*hex_to_rgba(C_BG_CARD, 1.0))
        cr.fill()
        cr.move_to(lx + t_wall, top_y)
        cr.line_to(lx + t_wall, bot_y)
        cr.set_source_rgba(*hex_to_rgba(C_BG_WIN, 0.85))
        cr.set_line_width(1.0)
        cr.stroke()
        # Inner right wall (along central hinge seam, offset by 1.0px for groove)
        cr.rectangle(lx + panel_w - 1.0 - t_wall, top_y, t_wall, panel_h)
        cr.set_source_rgba(*hex_to_rgba(C_BG_CARD, 1.0))
        cr.fill()
        cr.move_to(lx + panel_w - 1.0 - t_wall, top_y)
        cr.line_to(lx + panel_w - 1.0 - t_wall, bot_y)
        cr.set_source_rgba(*hex_to_rgba(C_BG_WIN, 0.85))
        cr.set_line_width(1.0)
        cr.stroke()
        cr.restore()

        # 3. Outer border
        cr.save()
        left_panel_path(cr, lx, top_y, panel_w, panel_h, corner_r, r_inner)
        cr.set_source_rgba(*COLOR_BORDER_SHADOW)
        cr.set_line_width(2.0)
        cr.stroke()
        cr.restore()

    def draw_right_panel_casing(self, cr, rx, top_y, panel_w, panel_h, corner_r=22.0, r_inner=18.0):
        bot_y = top_y + panel_h
        cx_mid = rx + panel_w / 2.0
        t_wall = 9.5

        # 1. Solid anime pink casing base
        cr.save()
        right_panel_path(cr, rx, top_y, panel_w, panel_h, corner_r, r_inner)
        cr.set_source_rgba(*COLOR_PINK_INSIDE)
        cr.fill()
        cr.restore()

        # 2. Dark gray chassis walls on both sides (inner left and outer right)
        cr.save()
        right_panel_path(cr, rx, top_y, panel_w, panel_h, corner_r, r_inner)
        cr.clip()
        # Inner left wall (along central hinge seam, offset by 1.0px for groove)
        cr.rectangle(rx + 1.0, top_y, t_wall, panel_h)
        cr.set_source_rgba(*hex_to_rgba(C_BG_CARD, 1.0))
        cr.fill()
        cr.move_to(rx + 1.0 + t_wall, top_y)
        cr.line_to(rx + 1.0 + t_wall, bot_y)
        cr.set_source_rgba(*hex_to_rgba(C_BG_WIN, 0.85))
        cr.set_line_width(1.0)
        cr.stroke()
        # Outer right wall
        cr.rectangle(rx + panel_w - t_wall, top_y, t_wall, panel_h)
        cr.set_source_rgba(*hex_to_rgba(C_BG_CARD, 1.0))
        cr.fill()
        cr.move_to(rx + panel_w - t_wall, top_y)
        cr.line_to(rx + panel_w - t_wall, bot_y)
        cr.set_source_rgba(*hex_to_rgba(C_BG_WIN, 0.85))
        cr.set_line_width(1.0)
        cr.stroke()
        cr.restore()

        # 3. Outer border
        cr.save()
        right_panel_path(cr, rx, top_y, panel_w, panel_h, corner_r, r_inner)
        cr.set_source_rgba(*COLOR_BORDER_SHADOW)
        cr.set_line_width(2.0)
        cr.stroke()
        cr.restore()

    def render_closed_cover_full(self, cr, cx, panel_w, panel_h, top_y, corner_r, r_inner, extrusion_h, steps):
        # 1. Ambient Drop Shadow under 3D extrusion base
        cr.save()
        front_cover_path(cr, cx, top_y + extrusion_h + 5.0, panel_w, panel_h, corner_r, r_inner)
        cr.set_source_rgba(0.08, 0.02, 0.04, 0.35)
        cr.fill()
        cr.restore()

        # 2. 3D Extrusion base downward in #4D0A1C (matches desktop widgets & control center)
        for s in range(steps + 1):
            dy = extrusion_h * (s / steps)
            cr.save()
            front_cover_path(cr, cx, top_y + dy, panel_w, panel_h, corner_r, r_inner)
            cr.set_source_rgba(*hex_to_rgba(C_BORDER_3D, 0.98))
            cr.fill()
            cr.restore()

        # Bottom edge definition contour on lowest slice
        cr.save()
        front_cover_path(cr, cx, top_y + extrusion_h, panel_w, panel_h, corner_r, r_inner)
        cr.set_source_rgba(*hex_to_rgba(C_BORDER_3D, 0.98))
        cr.set_line_width(1.8)
        cr.stroke()
        cr.restore()

        # 3. Front Cover Shell
        self.draw_front_cover(cr, cx, top_y, panel_w, panel_h)

    def render_right_panel_full(self, cr, cx, panel_w, panel_h, top_y, corner_r, r_inner, extrusion_h, steps):
        rx = cx
        # 1. Ambient Drop Shadow
        cr.save()
        right_panel_path(cr, rx, top_y + extrusion_h + 5.0, panel_w, panel_h, corner_r, r_inner)
        cr.set_source_rgba(0.08, 0.02, 0.04, 0.35)
        cr.fill()
        cr.restore()

        # 2. 3D Extrusion base
        for s in range(steps + 1):
            dy = extrusion_h * (s / steps)
            cr.save()
            right_panel_path(cr, rx, top_y + dy, panel_w, panel_h, corner_r, r_inner)
            cr.set_source_rgba(*hex_to_rgba(C_BORDER_3D, 0.98))
            cr.fill()
            cr.restore()

        cr.save()
        right_panel_path(cr, rx, top_y + extrusion_h, panel_w, panel_h, corner_r, r_inner)
        cr.set_source_rgba(*hex_to_rgba(C_BORDER_3D, 0.98))
        cr.set_line_width(1.8)
        cr.stroke()
        cr.restore()

        # 3. Right panel casing
        self.draw_right_panel_casing(cr, rx, top_y, panel_w, panel_h, corner_r, r_inner)

        # 4. Right Screen (Clean empty dark anime glass)
        pad_outer = 27.0
        pad_inner = 27.0
        pad_top = 36.0
        pad_bot = 62.0
        rsx = rx + pad_inner
        rsy = top_y + pad_top
        rsw = panel_w - pad_outer - pad_inner
        rsh = panel_h - pad_top - pad_bot
        self.draw_right_screen(cr, rsx, rsy, rsw, rsh)

        # 5. Chubby Heart Button (Centered under right screen)
        hcx = rsx + rsw / 2.0
        hcy = rsy + rsh + pad_bot * 0.50
        self.draw_heart_button(cr, hcx - 28.0, hcy - 23.0, 56.0, 46.0)

    def render_left_panel_full(self, cr, cx, panel_w, panel_h, top_y, corner_r, r_inner, extrusion_h, steps):
        lx = cx - panel_w
        # 1. Ambient Drop Shadow
        cr.save()
        left_panel_path(cr, lx, top_y + extrusion_h + 5.0, panel_w, panel_h, corner_r, r_inner)
        cr.set_source_rgba(0.08, 0.02, 0.04, 0.35)
        cr.fill()
        cr.restore()

        # 2. 3D Extrusion base
        for s in range(steps + 1):
            dy = extrusion_h * (s / steps)
            cr.save()
            left_panel_path(cr, lx, top_y + dy, panel_w, panel_h, corner_r, r_inner)
            cr.set_source_rgba(*hex_to_rgba(C_BORDER_3D, 0.98))
            cr.fill()
            cr.restore()

        cr.save()
        left_panel_path(cr, lx, top_y + extrusion_h, panel_w, panel_h, corner_r, r_inner)
        cr.set_source_rgba(*hex_to_rgba(C_BORDER_3D, 0.98))
        cr.set_line_width(1.8)
        cr.stroke()
        cr.restore()

        # 3. Left panel casing
        self.draw_left_panel_casing(cr, lx, top_y, panel_w, panel_h, corner_r, r_inner)

        # 4. Left Screen (Clean empty dark anime glass)
        pad_outer = 27.0
        pad_inner = 27.0
        pad_top = 36.0
        pad_bot = 62.0
        lsx = lx + pad_outer
        lsy = top_y + pad_top
        lsw = panel_w - pad_outer - pad_inner
        lsh = panel_h - pad_top - pad_bot
        self.draw_left_screen(cr, lsx, lsy, lsw, lsh)

    def _ensure_caches(self):
        if (getattr(self, "_cache_front_cover", None) is not None and
            getattr(self, "_cache_right_panel", None) is not None and
            getattr(self, "_cache_left_panel", None) is not None):
            return

        cx = OPEN_W / 2.0
        margin_x = 33.0
        panel_w = cx - margin_x
        panel_h = 585.0
        top_y = 30.0
        corner_r = 22.0
        r_inner = 18.0
        extrusion_h = 4.2
        steps = 14

        # 1. Front Cover (Closed)
        surf_fc = cairo.ImageSurface(cairo.FORMAT_ARGB32, OPEN_W, OPEN_H)
        cr_fc = cairo.Context(surf_fc)
        self.render_closed_cover_full(cr_fc, cx, panel_w, panel_h, top_y, corner_r, r_inner, extrusion_h, steps)
        self._cache_front_cover = surf_fc

        # 2. Right Panel (Stationary inside)
        surf_rp = cairo.ImageSurface(cairo.FORMAT_ARGB32, OPEN_W, OPEN_H)
        cr_rp = cairo.Context(surf_rp)
        self.render_right_panel_full(cr_rp, cx, panel_w, panel_h, top_y, corner_r, r_inner, extrusion_h, steps)
        self._cache_right_panel = surf_rp

        # 3. Left Panel (Moving inside)
        surf_lp = cairo.ImageSurface(cairo.FORMAT_ARGB32, OPEN_W, OPEN_H)
        cr_lp = cairo.Context(surf_lp)
        self.render_left_panel_full(cr_lp, cx, panel_w, panel_h, top_y, corner_r, r_inner, extrusion_h, steps)
        self._cache_left_panel = surf_lp

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

        # 1. Left & Right Panels
        cr.save()
        cr.set_source_surface(self._cache_left_panel, 0, 0)
        cr.paint()
        cr.set_source_surface(self._cache_right_panel, 0, 0)
        cr.paint()
        cr.restore()

        # 2. Center black recessed groove down the middle
        cr.save()
        cr.rectangle(cx - 1.0, top_y, 2.0, 585.0)
        cr.set_source_rgba(*hex_to_rgba(C_BG_WIN, 1.0))
        cr.fill()
        cr.restore()

        # 3. Two Small Hinges nestled inside the top & bottom notches
        self.draw_small_hinges(cr, cx, top_y, bot_y, alpha=1.0)

    def draw_transition_state(self, cr, win_w, win_h):
        self._ensure_caches()
        p = max(0.0, min(1.0, self.open_progress))

        cx = win_w / 2.0
        margin_x = 33.0
        panel_w = cx - margin_x
        panel_h = 585.0
        top_y = 30.0
        bot_y = top_y + panel_h
        corner_r = 22.0
        r_inner = 18.0
        extrusion_h = 4.2
        lx = cx - panel_w
        rx = cx

        # 1. Stationary Right Side (Pre-cached inside panel)
        cr.save()
        cr.set_source_surface(self._cache_right_panel, 0, 0)
        cr.paint()
        cr.restore()

        # 2. Moving Wing Physics
        theta = p * math.pi
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        # Dynamic shadow on table under left wing as it unfolds
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
            # Phase 1: Front cover flipping up from right to vertical
            cr.save()
            cr.translate(cx, 0)
            cr.scale(max(0.001, cos_t), 1.0)
            cr.translate(-cx, 0)
            cr.set_source_surface(self._cache_front_cover, 0, 0)
            cr.paint()
            # Dynamic tilt shading
            if sin_t > 0.04:
                cr.save()
                front_cover_path(cr, cx, top_y, panel_w, panel_h, corner_r, r_inner)
                cr.set_source_rgba(0.05, 0.01, 0.03, 0.28 * sin_t)
                cr.fill()
                cr.restore()
            cr.restore()

            # 3D physical chassis rim thickness when near vertical
            rim_w = 9.5 * sin_t
            if rim_w > 1.2:
                cr.save()
                cr.rectangle(cx, top_y, rim_w, panel_h)
                pat_rim = cairo.LinearGradient(cx, top_y, cx + rim_w, top_y)
                pat_rim.add_color_stop_rgba(0.0, 0.15, 0.10, 0.12, 1.0)
                pat_rim.add_color_stop_rgba(0.5, 0.26, 0.19, 0.23, 1.0)
                pat_rim.add_color_stop_rgba(1.0, 0.12, 0.08, 0.10, 1.0)
                cr.set_source(pat_rim)
                cr.fill()
                cr.restore()
        else:
            # Phase 2: Left panel unfolding from vertical to flat left
            cos_left = -cos_t

            # 3D physical chassis rim thickness when near vertical
            rim_w = 9.5 * sin_t
            if rim_w > 1.2:
                cr.save()
                cr.rectangle(cx - rim_w, top_y, rim_w, panel_h)
                pat_rim = cairo.LinearGradient(cx - rim_w, top_y, cx, top_y)
                pat_rim.add_color_stop_rgba(0.0, 0.12, 0.08, 0.10, 1.0)
                pat_rim.add_color_stop_rgba(0.5, 0.26, 0.19, 0.23, 1.0)
                pat_rim.add_color_stop_rgba(1.0, 0.15, 0.10, 0.12, 1.0)
                cr.set_source(pat_rim)
                cr.fill()
                cr.restore()

            cr.save()
            cr.translate(cx, 0)
            cr.scale(max(0.001, cos_left), 1.0)
            cr.translate(-cx, 0)
            cr.set_source_surface(self._cache_left_panel, 0, 0)
            cr.paint()
            # Dynamic tilt shading
            if sin_t > 0.04:
                cr.save()
                left_panel_path(cr, lx, top_y, panel_w, panel_h, corner_r, r_inner)
                cr.set_source_rgba(0.05, 0.01, 0.03, 0.28 * sin_t)
                cr.fill()
                cr.restore()
            cr.restore()

        # 3. Center black recessed groove down the middle (fade in as panels touch)
        if p >= 0.92:
            seam_alpha = min(1.0, (p - 0.92) / 0.08)
            cr.save()
            cr.rectangle(cx - 1.0, top_y, 2.0, panel_h)
            cr.set_source_rgba(*hex_to_rgba(C_BG_WIN, seam_alpha))
            cr.fill()
            cr.restore()

        # 4. Hinges with physical occlusion (smooth emergence as wings unfold)
        hinge_alpha = 0.0 if p < 0.40 else min(1.0, (p - 0.40) / 0.35)
        if hinge_alpha > 0.01:
            self.draw_small_hinges(cr, cx, top_y, bot_y, alpha=hinge_alpha)

    def draw_left_screen(self, cr, sx, sy, sw, sh):
        cr.save()
        squircle(cr, sx, sy, sw, sh, 14.0)
        # Completely flat clean anime dark screen
        cr.set_source_rgba(0.10, 0.04, 0.06, 0.98)
        cr.fill_preserve()
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.10)
        cr.set_line_width(1.2)
        cr.stroke()
        cr.restore()

    def draw_tile(self, cr, tx, ty, tw, th, icon, label, val, is_hover=False):
        cr.save()
        squircle(cr, tx, ty, tw, th, 8.0)
        if is_hover:
            cr.set_source_rgba(*hex_to_rgba(C_BG_CARD_HOVER, 0.98))
        else:
            cr.set_source_rgba(*hex_to_rgba(C_BG_CARD, 0.90))
        cr.fill_preserve()
        if is_hover:
            cr.set_source_rgba(*hex_to_rgba(C_ACCENT, 0.65))
        else:
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.12)
        cr.set_line_width(1.0)
        cr.stroke()

        cr.set_source_rgba(*hex_to_rgba(C_ACCENT, 1.0))
        layout = PangoCairo.create_layout(cr)
        layout.set_text(icon)
        desc = Pango.FontDescription("Symbols Nerd Font 13")
        layout.set_font_description(desc)
        cr.move_to(tx + 8.0, ty + 10.0)
        PangoCairo.show_layout(cr, layout)

        desc = Pango.FontDescription("Rubik Regular 8.5")
        layout.set_font_description(desc)
        layout.set_text(label)
        cr.set_source_rgba(*hex_to_rgba(C_TEXT_SEC, 0.85))
        cr.move_to(tx + 28.0, ty + 10.0)
        PangoCairo.show_layout(cr, layout)

        desc = Pango.FontDescription("Rubik Bold 9")
        layout.set_font_description(desc)
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
        desc = Pango.FontDescription("Symbols Nerd Font 18")
        layout.set_font_description(desc)
        layout.set_text("󰝚")
        cr.move_to(mx + 14.0, my + 14.0)
        PangoCairo.show_layout(cr, layout)

        desc = Pango.FontDescription("Rubik Bold 10")
        layout.set_font_description(desc)
        title_str = self.media_title[:22] + ("…" if len(self.media_title) > 22 else "")
        layout.set_text(title_str if title_str else "No media playing")
        cr.set_source_rgba(*hex_to_rgba(C_TEXT_PRI, 1.0))
        cr.move_to(mx + 42.0, my + 14.0)
        PangoCairo.show_layout(cr, layout)

        desc = Pango.FontDescription("Rubik Regular 8.5")
        layout.set_font_description(desc)
        layout.set_text(self.media_artist if self.media_artist else "Pokédex Audio")
        cr.set_source_rgba(*hex_to_rgba(C_TEXT_SEC, 0.75))
        cr.move_to(mx + 42.0, my + 32.0)
        PangoCairo.show_layout(cr, layout)

        cx = mx + mw / 2.0
        btn_y = my + 82.0

        cr.set_source_rgba(*hex_to_rgba(C_TEXT_SEC, 0.9))
        desc = Pango.FontDescription("Symbols Nerd Font 16")
        layout.set_font_description(desc)
        layout.set_text("󰒮")
        cr.move_to(cx - 50.0, btn_y)
        PangoCairo.show_layout(cr, layout)

        cr.arc(cx, btn_y + 12.0, 16.0, 0, 2 * math.pi)
        cr.set_source_rgba(*hex_to_rgba(C_ACCENT, 1.0))
        cr.fill()

        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        desc = Pango.FontDescription("Symbols Nerd Font 14")
        layout.set_font_description(desc)
        layout.set_text("󰏤" if self.media_status == "Playing" else "󰐊")
        cr.move_to(cx - 7.0, btn_y + 4.0)
        PangoCairo.show_layout(cr, layout)

        cr.set_source_rgba(*hex_to_rgba(C_TEXT_SEC, 0.9))
        desc = Pango.FontDescription("Symbols Nerd Font 16")
        layout.set_font_description(desc)
        layout.set_text("󰒭")
        cr.move_to(cx + 34.0, btn_y)
        PangoCairo.show_layout(cr, layout)
        cr.restore()

    def draw_left_tabs(self, cr, bx, by, bw, bh):
        tabs = [
            ("settings", " Settings"),
            ("map", "󰍦 Kalos Map"),
            ("guide", "󰋜 Guide")
        ]
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
            desc = Pango.FontDescription("Rubik Bold 8")
            layout.set_font_description(desc)
            layout.set_text(tlabel)
            ink, log = layout.get_pixel_extents()
            cr.move_to(tx + (tab_w - log.width) / 2.0, by + 5.0)
            cr.set_source_rgba(*hex_to_rgba(C_TEXT_PRI if is_active else C_TEXT_MUT, 1.0))
            PangoCairo.show_layout(cr, layout)
            cr.restore()

    def draw_right_screen(self, cr, sx, sy, sw, sh):
        cr.save()
        squircle(cr, sx, sy, sw, sh, 14.0)
        # Completely flat clean anime dark screen
        cr.set_source_rgba(0.10, 0.04, 0.06, 0.98)
        cr.fill_preserve()
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.10)
        cr.set_line_width(1.2)
        cr.stroke()
        cr.restore()

    def draw_controls_page(self, cr, sx, sy, sw, sh):
        layout = PangoCairo.create_layout(cr)
        desc = Pango.FontDescription("Rubik Bold 10")
        layout.set_font_description(desc)
        layout.set_text("󰐥 CONTROLS")
        cr.move_to(sx + 14.0, sy + 14.0)
        cr.set_source_rgba(*hex_to_rgba(C_ACCENT, 1.0))
        PangoCairo.show_layout(cr, layout)

        cr.set_source_rgba(*hex_to_rgba(C_ACCENT if len(self.notifications) > 0 else C_TEXT_MUT, 1.0))
        desc = Pango.FontDescription("Symbols Nerd Font 13")
        layout.set_font_description(desc)
        layout.set_text("󰂚")
        cr.move_to(sx + sw - 30.0, sy + 12.0)
        PangoCairo.show_layout(cr, layout)

        if len(self.notifications) > 0:
            cr.arc(sx + sw - 14.0, sy + 14.0, 7.0, 0, 2 * math.pi)
            cr.set_source_rgba(*hex_to_rgba(C_ACCENT, 1.0))
            cr.fill()
            desc = Pango.FontDescription("Rubik Bold 7")
            layout.set_font_description(desc)
            layout.set_text(str(min(9, len(self.notifications))))
            cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
            cr.move_to(sx + sw - 17.0, sy + 9.0)
            PangoCairo.show_layout(cr, layout)

        cx = sx + sw / 2.0
        cy = sy + 155.0
        r_arc = 68.0

        cr.set_line_cap(cairo.LINE_CAP_ROUND)

        # Volume track
        cr.arc(cx, cy, r_arc, math.pi * 1.15, math.pi * 1.85)
        cr.set_source_rgba(*hex_to_rgba(C_BG_CARD_HOVER, 0.90))
        cr.set_line_width(10.0)
        cr.stroke()

        v_prog = min(1.0, max(0.0, self.volume / 100.0))
        if v_prog > 0:
            cr.arc(cx, cy, r_arc, math.pi * 1.15, math.pi * 1.15 + (math.pi * 0.70) * v_prog)
            cr.set_source_rgba(*hex_to_rgba(C_ACCENT, 1.0))
            cr.set_line_width(10.0)
            cr.stroke()

        hand_ang_v = math.pi * 1.15 + (math.pi * 0.70) * v_prog
        hx_v = cx + r_arc * math.cos(hand_ang_v)
        hy_v = cy + r_arc * math.sin(hand_ang_v)
        cr.arc(hx_v, hy_v, 8.0, 0, 2 * math.pi)
        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        cr.fill_preserve()
        cr.set_source_rgba(*hex_to_rgba(C_ACCENT, 1.0))
        cr.set_line_width(2.0)
        cr.stroke()

        desc = Pango.FontDescription("Symbols Nerd Font 12")
        layout.set_font_description(desc)
        layout.set_text("󰕿" if self.volume < 30 else ("󰖀" if self.volume < 70 else "󰕾"))
        cr.set_source_rgba(*hex_to_rgba(C_TEXT_SEC, 1.0))
        cr.move_to(cx - 36.0, cy - 36.0)
        PangoCairo.show_layout(cr, layout)

        desc = Pango.FontDescription("Rubik Bold 9")
        layout.set_font_description(desc)
        layout.set_text(f"{self.volume}%")
        cr.move_to(cx - 36.0, cy - 20.0)
        PangoCairo.show_layout(cr, layout)

        # Brightness track
        cr.arc(cx, cy, r_arc, math.pi * 0.15, math.pi * 0.85)
        cr.set_source_rgba(*hex_to_rgba(C_BG_CARD_HOVER, 0.90))
        cr.set_line_width(10.0)
        cr.stroke()

        b_prog = min(1.0, max(0.0, self.brightness / 100.0))
        if b_prog > 0:
            cr.arc(cx, cy, r_arc, math.pi * 0.15, math.pi * 0.15 + (math.pi * 0.70) * b_prog)
            cr.set_source_rgba(*hex_to_rgba(C_STATUS_WARN, 1.0))
            cr.set_line_width(10.0)
            cr.stroke()

        hand_ang_b = math.pi * 0.15 + (math.pi * 0.70) * b_prog
        hx_b = cx + r_arc * math.cos(hand_ang_b)
        hy_b = cy + r_arc * math.sin(hand_ang_b)
        cr.arc(hx_b, hy_b, 8.0, 0, 2 * math.pi)
        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        cr.fill_preserve()
        cr.set_source_rgba(*hex_to_rgba(C_STATUS_WARN, 1.0))
        cr.set_line_width(2.0)
        cr.stroke()

        desc = Pango.FontDescription("Symbols Nerd Font 12")
        layout.set_font_description(desc)
        layout.set_text("󰃠")
        cr.set_source_rgba(*hex_to_rgba(C_TEXT_SEC, 1.0))
        cr.move_to(cx - 36.0, cy + 20.0)
        PangoCairo.show_layout(cr, layout)

        desc = Pango.FontDescription("Rubik Bold 9")
        layout.set_font_description(desc)
        layout.set_text(f"{self.brightness}%")
        cr.move_to(cx - 36.0, cy + 34.0)
        PangoCairo.show_layout(cr, layout)

        # Center Power Button
        cr.arc(cx, cy, 26.0, 0, 2 * math.pi)
        cr.set_source_rgba(*hex_to_rgba(C_BG_CARD, 1.0))
        cr.fill_preserve()
        cr.set_source_rgba(*hex_to_rgba(C_ACCENT, 0.8))
        cr.set_line_width(2.0)
        cr.stroke()

        desc = Pango.FontDescription("Symbols Nerd Font 16")
        layout.set_font_description(desc)
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

        desc = Pango.FontDescription("Rubik Regular 8.5")
        layout.set_font_description(desc)
        layout.set_text(f"Vol: {self.volume}%  ·  Bri: {self.brightness}%  ·  {self.power_mode.capitalize()}")
        ink, log = layout.get_pixel_extents()
        cr.set_source_rgba(*hex_to_rgba(C_TEXT_SEC, 0.9))
        cr.move_to(sx + (sw - log.width) / 2.0, pill_y + 9.0)
        PangoCairo.show_layout(cr, layout)

    def draw_notifications_page(self, cr, sx, sy, sw, sh):
        layout = PangoCairo.create_layout(cr)
        desc = Pango.FontDescription("Rubik Bold 10")
        layout.set_font_description(desc)
        layout.set_text("󰂚 NOTIFICATIONS")
        cr.move_to(sx + 14.0, sy + 14.0)
        cr.set_source_rgba(*hex_to_rgba(C_ACCENT, 1.0))
        PangoCairo.show_layout(cr, layout)

        desc = Pango.FontDescription("Symbols Nerd Font 12")
        layout.set_font_description(desc)
        layout.set_text(" Back")
        cr.set_source_rgba(*hex_to_rgba(C_TEXT_SEC, 0.9))
        cr.move_to(sx + sw - 60.0, sy + 14.0)
        PangoCairo.show_layout(cr, layout)

        list_y = sy + 44.0
        item_h = 56.0
        gap = 8.0

        if not self.notifications:
            desc = Pango.FontDescription("Rubik Regular 10")
            layout.set_font_description(desc)
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

                app_name = notif.get("app_name", "System")
                desc = Pango.FontDescription("Rubik Bold 8.5")
                layout.set_font_description(desc)
                layout.set_text(app_name)
                cr.set_source_rgba(*hex_to_rgba(C_ACCENT, 1.0))
                cr.move_to(sx + 18.0, ny + 8.0)
                PangoCairo.show_layout(cr, layout)

                summary = notif.get("summary", "")[:24]
                desc = Pango.FontDescription("Rubik Regular 9")
                layout.set_font_description(desc)
                layout.set_text(summary)
                cr.set_source_rgba(*hex_to_rgba(C_TEXT_PRI, 1.0))
                cr.move_to(sx + 18.0, ny + 24.0)
                PangoCairo.show_layout(cr, layout)

                body = notif.get("body", "")[:28]
                desc = Pango.FontDescription("Rubik Regular 8")
                layout.set_font_description(desc)
                layout.set_text(body)
                cr.set_source_rgba(*hex_to_rgba(C_TEXT_SEC, 0.75))
                cr.move_to(sx + 18.0, ny + 38.0)
                PangoCairo.show_layout(cr, layout)

        cy = sy + sh - 36.0
        squircle(cr, sx + 14.0, cy, sw - 28.0, 28.0, 6.0)
        cr.set_source_rgba(*hex_to_rgba(C_BG_CARD, 0.90))
        cr.fill_preserve()
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.12)
        cr.set_line_width(1.0)
        cr.stroke()

        desc = Pango.FontDescription("Rubik Bold 8.5")
        layout.set_font_description(desc)
        layout.set_text("󰃢 Clear All Notifications")
        ink, log = layout.get_pixel_extents()
        cr.set_source_rgba(*hex_to_rgba(C_TEXT_PRI, 0.9))
        cr.move_to(sx + (sw - log.width) / 2.0, cy + 6.0)
        PangoCairo.show_layout(cr, layout)

    def draw_heart_button(self, cr, hx, hy, hw=56.0, hh=46.0):
        cx = hx + hw / 2.0
        cy = hy + hh / 2.0
        scale = 1.30
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

        # Pure clean Pokédex red (flat anime style, no drop shadow, no specular dot)
        cr.set_source_rgba(*hex_to_rgba(C_ACCENT, 1.0))
        cr.fill_preserve()
        cr.set_source_rgba(COLOR_BORDER_SHADOW[0], COLOR_BORDER_SHADOW[1], COLOR_BORDER_SHADOW[2], 0.95)
        cr.set_line_width(1.6 / scale)
        cr.stroke()
        cr.restore()

    # ---------------- INTERACTION & EVENTS ----------------
    def on_button_press(self, widget, event):
        x, y = event.x, event.y

        cx = OPEN_W / 2.0
        margin_x = 33.0
        panel_w = cx - margin_x
        panel_h = 585.0
        top_y = 30.0
        bot_y = top_y + panel_h
        extrusion_h = 4.2
        lx = cx - panel_w
        rx = cx

        if event.button == 1:
            if self.anim_state in ("opening", "closing"):
                return True

            # Determine whether click started inside the physical device
            if self.anim_state == "closed":
                is_inside = (rx <= x <= rx + panel_w and top_y <= y <= bot_y + extrusion_h)
            else:
                is_inside = (lx - 10.0 <= x <= rx + panel_w + 10.0 and top_y - 10.0 <= y <= bot_y + extrusion_h + 10.0)

            if not is_inside:
                # Outside click: close/dismiss
                if self.anim_state == "closed":
                    self.close_and_quit()
                else:
                    self.start_close_animation(quit_after=True)
                return True

            return self.drag_manager.handle_press(event, is_inside=True)

        return False

    def on_button_release(self, widget, event):
        if event.button == 1:
            return self.drag_manager.handle_release(event, on_click=self.handle_click)
        return False

    def handle_click(self, x, y):
        cx = OPEN_W / 2.0
        margin_x = 33.0
        panel_w = cx - margin_x
        panel_h = 585.0
        top_y = 30.0
        bot_y = top_y + panel_h
        extrusion_h = 4.2
        lx = cx - panel_w
        rx = cx

        if self.anim_state == "closed":
            if rx <= x <= rx + panel_w and top_y <= y <= bot_y + extrusion_h:
                self.start_open_animation()
            else:
                self.close_and_quit()
            return

        if self.anim_state in ("opening", "closing"):
            return

        # Open state: Heart button (Centered under right screen)
        pad_outer = 27.0
        pad_inner = 27.0
        pad_top = 36.0
        pad_bot = 62.0
        rsx = rx + pad_inner
        rsy = top_y + pad_top
        rsw = panel_w - pad_outer - pad_inner
        rsh = panel_h - pad_top - pad_bot
        hcx = rsx + rsw / 2.0
        hcy = rsy + rsh + pad_bot * 0.50
        if math.hypot(x - hcx, y - hcy) <= 28.0:
            self.start_close_animation()
            return

    def on_motion_notify(self, widget, event):
        x, y = event.x, event.y

        # Delegate dragging to shared drag manager
        if self.drag_manager.handle_motion(event):
            return True

        # Cursor feedback when hovering (not dragging)
        win = self.get_window()
        if win and not self.is_dragging:
            cx = OPEN_W / 2.0
            margin_x = 33.0
            panel_w = cx - margin_x
            panel_h = 585.0
            top_y = 30.0
            bot_y = top_y + panel_h
            extrusion_h = 4.2
            lx = cx - panel_w
            rx = cx

            if self.anim_state == "closed":
                if rx <= x <= rx + panel_w and top_y <= y <= bot_y + extrusion_h:
                    win.set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "grab"))
                else:
                    win.set_cursor(None)
            elif self.anim_state == "open":
                pad_outer, pad_inner, pad_top, pad_bot = 27.0, 27.0, 36.0, 62.0
                rsx = rx + pad_inner
                rsw = panel_w - pad_outer - pad_inner
                rsh = panel_h - pad_top - pad_bot
                hcx = rsx + rsw / 2.0
                hcy = top_y + pad_top + rsh + pad_bot * 0.50
                if math.hypot(x - hcx, y - hcy) <= 28.0:
                    win.set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "pointer"))
                elif lx <= x <= rx + panel_w and top_y <= y <= bot_y + extrusion_h:
                    win.set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "grab"))
                else:
                    win.set_cursor(None)

        return True

    def on_scroll(self, widget, event):
        if self.anim_state == "open":
            if event.direction == Gdk.ScrollDirection.UP:
                new_v = min(100, self.volume + 5)
                AudioService.set_volume(new_v)
                self.volume = new_v
                self.queue_draw()
            elif event.direction == Gdk.ScrollDirection.DOWN:
                new_v = max(0, self.volume - 5)
                AudioService.set_volume(new_v)
                self.volume = new_v
                self.queue_draw()
        return True

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            if self.anim_state == "open":
                self.start_close_animation()
            else:
                self.close_and_quit()
            return True
        return False

    def update_volume_from_mouse(self, mx, my, cx, cy):
        dx = mx - cx
        dy = my - cy
        ang = math.atan2(dy, dx)
        start_ang = -0.85 * math.pi
        end_ang = -0.15 * math.pi
        if ang < 0:
            prog = (ang - start_ang) / (end_ang - start_ang)
            prog = max(0.0, min(1.0, prog))
            vol = int(prog * 100)
            AudioService.set_volume(vol)
            self.volume = vol
            self.queue_draw()

    def update_brightness_from_mouse(self, mx, my, cx, cy):
        dx = mx - cx
        dy = my - cy
        ang = math.atan2(dy, dx)
        start_ang = 0.15 * math.pi
        end_ang = 0.85 * math.pi
        if ang > 0:
            prog = (ang - start_ang) / (end_ang - start_ang)
            prog = max(0.0, min(1.0, prog))
            bri = int(prog * 100)
            BrightnessService.set_brightness(bri)
            self.brightness = bri
            self.queue_draw()


def main():
    app = SettingsWindow()
    app.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()

