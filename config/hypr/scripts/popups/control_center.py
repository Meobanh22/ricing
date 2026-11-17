#!/usr/bin/env python3
# control_center.py — Control Center and notifications panel.

import os
import sys
import time
import json
import re
import signal
import subprocess
import shutil
import math
import threading
import cairo
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
try:
    gi.require_version('GtkLayerShell', '0.1')
    from gi.repository import GtkLayerShell
    HAS_LAYER_SHELL = True
except Exception:
    HAS_LAYER_SHELL = False

from gi.repository import Gtk, Gdk, GLib, Pango, PangoCairo

# Resolve script & service paths
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_ROOT = os.path.dirname(SCRIPTS_DIR)
SYSTEM_DIR = os.path.join(SCRIPTS_ROOT, "system")
SERVICES_DIR = os.path.join(SCRIPTS_ROOT, "services")

for p in (SCRIPTS_DIR, SCRIPTS_ROOT, SYSTEM_DIR, SERVICES_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from services.audio import AudioService
from services.brightness import BrightnessService
from services.bluetooth import BluetoothService
from services.power import PowerService
from services.wifi import WifiService
from ui_core import (
    DraggablePopup, get_cursor_pos, get_monitor_geometry,
    draw_rounded_rect, clip_device_bounds, draw_anime_grooves,
    draw_bow_mark, draw_bell_icon,
    draw_curved_kerned, draw_curved_kerned_cached,
    clear_surface
)

try:
    from palette import (
        PALETTE, hex_to_rgba,
        C_BG_WIN, C_BG_CARD, C_BG_CARD_HOVER, C_BG_SUBTLE,
        C_ACCENT, C_ACCENT_HOVER, C_TEXT_PRI, C_TEXT_SEC, C_TEXT_MUT, C_TEXT_INV,
        C_STATUS_WARN, C_STATUS_CRIT, C_STATUS_SUCC, C_RIBBON,
        C_BG_WAYBAR, C_BORDER_3D, C_SCREEN_CYAN,
        BG_WINDOW_RGBA, BG_CARD_RGBA, ACCENT_RGBA, ACCENT_HOVER_RGBA
    )
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
    C_SCREEN_CYAN = "#87F0FF"

PID_FILE = "/tmp/control_center.pid"
CACHE_FILE = os.path.expanduser("~/.cache/notifications.json")

# ==============================================================================
# 1. PURE CAIRO GEOMETRIC PATHS & HELPERS (ui_core imported)
# ==============================================================================

def create_top_red_casing_path(cr, x_left, x_right, y_dark_top, cx, cy_top, r_dark, ang_dark_top_start, ang_dark_top_end, x_dark_cut, device_r, notch_d=2.0, trans=1.8, y_top=0.0):
    y_tl1_t = 48.0;  y_tl1_b = 52.0
    y_tl2_t = 96.0;  y_tl2_b = 100.0

    # Top edge notch coordinates (aligned with concentric grooves centered at corners)
    x_orig_l = x_left - y_top
    x_orig_r = x_right + y_top
    x_t1_l = x_orig_l + 48.0; x_t1_r = x_orig_l + 52.0
    x_t2_l = x_orig_l + 96.0; x_t2_r = x_orig_l + 100.0
    x_tr2_l = x_orig_r - 100.0; x_tr2_r = x_orig_r - 96.0
    x_tr1_l = x_orig_r - 52.0; x_tr1_r = x_orig_r - 48.0
    
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

    # Top edge notches (inward dipping: +notch_d in y)
    cr.line_to(x_t1_l - trans, y_top)
    cr.curve_to(x_t1_l - trans * 0.5, y_top, x_t1_l - trans * 0.5, y_top + notch_d, x_t1_l, y_top + notch_d)
    cr.line_to(x_t1_r, y_top + notch_d)
    cr.curve_to(x_t1_r + trans * 0.5, y_top + notch_d, x_t1_r + trans * 0.5, y_top, x_t1_r + trans, y_top)

    cr.line_to(x_t2_l - trans, y_top)
    cr.curve_to(x_t2_l - trans * 0.5, y_top, x_t2_l - trans * 0.5, y_top + notch_d, x_t2_l, y_top + notch_d)
    cr.line_to(x_t2_r, y_top + notch_d)
    cr.curve_to(x_t2_r + trans * 0.5, y_top + notch_d, x_t2_r + trans * 0.5, y_top, x_t2_r + trans, y_top)

    cr.line_to(x_tr2_l - trans, y_top)
    cr.curve_to(x_tr2_l - trans * 0.5, y_top, x_tr2_l - trans * 0.5, y_top + notch_d, x_tr2_l, y_top + notch_d)
    cr.line_to(x_tr2_r, y_top + notch_d)
    cr.curve_to(x_tr2_r + trans * 0.5, y_top + notch_d, x_tr2_r + trans * 0.5, y_top, x_tr2_r + trans, y_top)

    cr.line_to(x_tr1_l - trans, y_top)
    cr.curve_to(x_tr1_l - trans * 0.5, y_top, x_tr1_l - trans * 0.5, y_top + notch_d, x_tr1_l, y_top + notch_d)
    cr.line_to(x_tr1_r, y_top + notch_d)
    cr.curve_to(x_tr1_r + trans * 0.5, y_top + notch_d, x_tr1_r + trans * 0.5, y_top, x_tr1_r + trans, y_top)

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
    y_bl1_b = H_canvas - 48.0; y_bl1_t = H_canvas - 52.0
    y_bl2_b = H_canvas - 96.0; y_bl2_t = H_canvas - 100.0
    
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

# ==============================================================================
# 2. POKÉBALL DUAL SLIDER & NOTIFICATION HELPERS (Control Center Specific)
# ==============================================================================
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
        cr.set_source_rgb(1.0, 1.0, 1.0); cr.fill_preserve()
        cr.set_source_rgb(*accent_rgb); cr.set_line_width(2.0); cr.stroke()
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
        cr.set_source_rgb(1.0, 1.0, 1.0); cr.fill_preserve()
        cr.set_source_rgb(*accent_rgb); cr.set_line_width(2.0); cr.stroke()
    cr.restore()

    # 3. HORIZONTAL EQUATORIAL SEAMS
    r_out = R + thickness / 2.0 + 3.0
    r_btn_outer = 22.0

    cr.save()
    cr.set_line_width(2.8)
    cr.set_source_rgb(*dark_color)
    cr.new_sub_path()
    cr.move_to(cx - r_out, cy); cr.line_to(cx - r_btn_outer, cy); cr.stroke()
    cr.new_sub_path()
    cr.move_to(cx + r_btn_outer, cy); cr.line_to(cx + r_out, cy); cr.stroke()
    cr.restore()

    # 4. CENTER POWER BUTTON
    cr.save()
    cr.new_sub_path()
    cr.arc(cx, cy, r_btn_outer, 0, 2 * math.pi)
    cr.set_source_rgb(*pwr_bg); cr.fill_preserve()
    cr.set_source_rgba(0x3A/255.0, 0x22/255.0, 0x2A/255.0, 0.9); cr.set_line_width(1.5); cr.stroke()

    r_pwr = 7.0
    ang_gap = math.radians(35.0)
    ang_s = -math.pi / 2.0 + ang_gap
    ang_e = 1.5 * math.pi - ang_gap

    cr.set_line_width(2.0)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.new_sub_path()
    cr.arc(cx, cy, r_pwr, ang_s, ang_e)
    cr.set_source_rgb(*accent_rgb); cr.stroke()

    cr.new_sub_path()
    cr.move_to(cx, cy - r_pwr - 2.5)
    cr.line_to(cx, cy - 1.0)
    cr.stroke()
    cr.restore()

    # 5. ICONS
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

def format_relative_time(timestamp):
    if not timestamp:
        return "just now"
    now = time.time()
    diff = max(0, int(now - timestamp))
    if diff < 60:
        return "just now"
    elif diff < 3600:
        mins = diff // 60
        return f"{mins}m ago"
    elif diff < 86400:
        hours = diff // 3600
        return f"{hours}h ago"
    else:
        days = diff // 86400
        return f"{days}d ago"

def get_badge_info(app_name):
    app_lower = app_name.lower()
    if "discord" in app_lower:
        return "#5865F2", "󰙯"
    elif "firefox" in app_lower or "browser" in app_lower:
        return "#FF7139", "󰈹"
    elif "spotify" in app_lower or "music" in app_lower:
        return "#1ED760", "󰓇"
    elif "steam" in app_lower:
        return "#1b2838", "󰓓"
    elif "terminal" in app_lower or "alacritty" in app_lower or "kitty" in app_lower:
        return C_ACCENT, "󰆍"
    return C_ACCENT, "󰒓"

# ==============================================================================
# 3. POKÉDEX GTK APPLICATION WITH SLIDING ANIMATION & CLOSED STATE
# ==============================================================================
class PokedexControlCenter(Gtk.Window):
    def __init__(self):
        super().__init__(title="Control Center")
        self.set_name("control-center-window")
        self.set_wmclass("control-center", "control-center")
        self.set_decorated(False)
        self.set_resizable(False)

        # Logical canvas dimensions (scaled by 4px each side, 10px top & bottom)
        self.base_w = 388.0
        self.base_h = 786.0
        self.W_canvas = 380.0   # 388 - 8px (4px on each side)
        self.H_canvas = 766.0   # 786 - 20px (10px on top and bottom)
        self.set_default_size(int(self.W_canvas), int(self.H_canvas))
        self.set_size_request(int(self.W_canvas), int(self.H_canvas))

        self.current_page = "controls"
        self.dragging_slider = None
        self.hovered_item = None

        # ANIMATION & STATE:
        # Starts in CLOSED state per user requirement (or open if --open passed)
        if "--open" in sys.argv:
            self.anim_state = "open"
            self.anim_progress = 1.0
        else:
            self.anim_state = "closed"
            self.anim_progress = 0.0
        self.anim_start_time = None
        self.anim_duration = 0.30    # 300ms smooth anime sliding (+40ms)
        self._cached_top_casing = None
        self._cached_bot_casing = None
        self._cached_content_surf = None
        self._cached_content_page = None
        self._tick_id = None
        self.quit_after_close = False

        # Cached Pango font descriptions for quick tiles (avoids string parsing overhead on every frame)
        self.pango_font_tile_icon = Pango.FontDescription("JetBrains Mono Nerd Font 20")
        self.pango_font_tile_title = Pango.FontDescription("JetBrains Mono Nerd Font Bold 10")
        self.pango_font_tile_val = Pango.FontDescription("JetBrains Mono Nerd Font Bold 10")

        # Warm up Fontconfig, Pango glyph caches, and curved header surfaces to prevent mid-animation hitch
        self._warmup_cache()

        # State cache (Instant non-blocking defaults for 0.01s launch)
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

        # Wi-Fi Selection View State
        self.wifi_networks = []
        self.wifi_scanning = False
        self.wifi_connecting = False
        self.wifi_status_msg = ""
        self.wifi_page_idx = 0
        self.wifi_password_prompt_ssid = None
        self.wifi_password_input = ""
        self.wifi_radio_enabled = True

        # Non-blocking async status fetch immediately in background
        threading.Thread(target=self.async_refresh_status, daemon=True).start()

        # Geometry dimensions
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

        # Layout anchors for geometric balance:
        self.cy_pokeball = 468.0
        self.socket_well_y = 636.5
        self.top_mark_offset = 32.0

        # Unified Anime Palette (derived from design tokens)
        self.c_casing_l = hex_to_rgba(C_ACCENT)[:3]
        self.c_casing_m = hex_to_rgba(C_ACCENT_HOVER)[:3]
        self.c_casing_r = hex_to_rgba(C_ACCENT)[:3]
        self.c_border_3d = hex_to_rgba(C_BORDER_3D, 0.98)
        self.c_tactile_white = (1.0, 1.0, 1.0, 0.65)
        self.c_casing_border = self.c_border_3d

        # Pokéball Band & Chassis (using wine base and subtle tokens)
        self.c_band_stop0 = hex_to_rgba(C_BG_WIN)[:3]
        self.c_band_stop1 = hex_to_rgba(C_BG_CARD)[:3]
        self.c_band_stop2 = hex_to_rgba(C_BG_WIN)[:3]
        self.c_band_stroke = self.c_border_3d
        self.c_slider_dark = hex_to_rgba(C_BG_SUBTLE)[:3]
        self.c_pwr_bg = hex_to_rgba(C_BG_SUBTLE)[:3]
        self.c_chassis = hex_to_rgba(C_TEXT_SEC)[:3]
        self.c_flange = hex_to_rgba(C_BG_WIN)[:3]

        # Accent & Screen Cyan roles
        self.c_accent = C_ACCENT
        self.c_accent_rgb = hex_to_rgba(C_ACCENT)[:3]
        self.c_accent_hover = C_ACCENT_HOVER
        self.c_accent_hover_rgb = hex_to_rgba(C_ACCENT_HOVER)[:3]
        self.c_holo_top = hex_to_rgba(C_SCREEN_CYAN)[:3]
        self.c_holo_mid = hex_to_rgba(C_SCREEN_CYAN)[:3]
        self.c_holo_bot = hex_to_rgba(C_SCREEN_CYAN)[:3]
        self.holo_alpha_top = 0.58
        self.holo_alpha_mid = 0.52
        self.holo_alpha_bot = 0.58

        # LayerShell setup via shared DraggablePopup manager
        def cc_bounds(x, y, mon_w, mon_h):
            min_x = 14
            max_x = mon_w - int(self.W_canvas) - 14
            if self.anim_state in ("closed", "closing"):
                # When closed, physical shell is local y in [180.0, 600.0]
                min_y = 14 - 180  # Top of closed casing can reach Y = 66 (aligned with VS Code)
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
            drag_threshold=14.0
        )
        self.drag_manager.init_layer_shell(
            namespace="control-center",
            layer=GtkLayerShell.Layer.TOP if HAS_LAYER_SHELL else None,
            keyboard_mode=GtkLayerShell.KeyboardMode.ON_DEMAND if HAS_LAYER_SHELL else None
        )

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        self.set_app_paintable(True)

        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.LEAVE_NOTIFY_MASK |
            Gdk.EventMask.KEY_PRESS_MASK |
            Gdk.EventMask.SCROLL_MASK
        )

        self.connect("draw", self.on_draw)
        self.connect("button-press-event", self.on_button_press)
        self.connect("button-release-event", self.on_button_release)
        self.connect("motion-notify-event", self.on_motion_notify)
        self.connect("leave-notify-event", self.on_leave_notify)
        self.connect("key-press-event", self.on_key_press)
        self.connect("scroll-event", self.on_scroll)

        # Signal handling for Super+N toggling
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, self.on_sigusr1)

        GLib.timeout_add(1500, self.refresh_status_tick)

        # Bake initial surface caches
        self._bake_casings()
        self._bake_content()

    def _warmup_cache(self):
        try:
            dummy_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 10, 10)
            dummy_cr = cairo.Context(dummy_surf)
            # Pre-render curved header surfaces to memory
            draw_curved_kerned_cached(dummy_cr, "CONTROL CENTER", 0, 0)
            draw_curved_kerned_cached(dummy_cr, "NOTIFICATIONS", 0, 0)
            draw_curved_kerned_cached(dummy_cr, "WI-FI NETWORKS", 0, 0)
            # Pre-rasterize fonts and icon glyphs into Fontconfig/Pango cache
            for f_desc, txt in [
                ("JetBrains Mono Nerd Font 20", "󰌌󰤨󰤮󰖪󰂯󰂱󰂲󰓅󰾅󰌪󰌾󰂚"),
                ("JetBrains Mono Nerd Font Bold 10", "Input Wi-Fi Bluetooth Power Mode Vietnamese English Connected Disconnected Disabled Balanced Performance"),
                ("DejaVu Sans Bold 8.5", "CONTROL CENTER NOTIFICATIONS WI-FI NETWORKS")
            ]:
                l = PangoCairo.create_layout(dummy_cr)
                l.set_font_description(Pango.FontDescription(f_desc))
                l.set_text(txt, -1)
                l.get_pixel_extents()
        except Exception:
            pass

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

        # Ensure open Pokédex fits completely on screen vertically
        mon_w, mon_h = self.get_monitor_geometry()
        min_open_y = 14
        max_open_y = max(min_open_y, mon_h - 52 - int(self.H_canvas) - 14)
        target_y = max(min_open_y, min(max_open_y, self.current_win_y))

        min_open_x = 14
        max_open_x = mon_w - int(self.W_canvas) - 14
        target_x = max(min_open_x, min(max_open_x, self.current_win_x))

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

        if self.anim_state == "opening":
            # Perlin Smootherstep: zero 1st & 2nd derivatives for liquid-smooth mechanical glide
            e = t * t * t * (t * (t * 6.0 - 15.0) + 10.0)
            self.anim_progress = e

            # Smooth window margin translation in lockstep with easing
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
            # Perlin Smootherstep for closing
            e = t * t * t * (t * (t * 6.0 - 15.0) + 10.0)
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

    def on_scroll(self, widget, event):
        if self.current_page == "wifi" and not self.wifi_password_prompt_ssid:
            max_page = max(0, (len(self.wifi_networks) - 1) // 5)
            if event.direction in (Gdk.ScrollDirection.UP, Gdk.ScrollDirection.SMOOTH):
                if event.direction == Gdk.ScrollDirection.SMOOTH and hasattr(event, 'delta_y') and event.delta_y > 0:
                    if self.wifi_page_idx < max_page:
                        self.wifi_page_idx += 1
                        self._bake_content()
                    self.queue_draw()
                elif self.wifi_page_idx > 0:
                    self.wifi_page_idx -= 1
                    self._bake_content()
                    self.queue_draw()
                return True
            elif event.direction == Gdk.ScrollDirection.DOWN:
                if self.wifi_page_idx < max_page:
                    self.wifi_page_idx += 1
                    self._bake_content()
                    self.queue_draw()
                return True
        elif self.current_page == "notifications":
            max_page = max(0, (len(self.notifications) - 1) // 5)
            if event.direction in (Gdk.ScrollDirection.UP, Gdk.ScrollDirection.SMOOTH):
                if event.direction == Gdk.ScrollDirection.SMOOTH and hasattr(event, 'delta_y') and event.delta_y > 0:
                    if self.notif_page_idx < max_page:
                        self.notif_page_idx += 1
                        self._bake_content()
                    self.queue_draw()
                elif self.notif_page_idx > 0:
                    self.notif_page_idx -= 1
                    self._bake_content()
                    self.queue_draw()
                return True
            elif event.direction == Gdk.ScrollDirection.DOWN:
                if self.notif_page_idx < max_page:
                    self.notif_page_idx += 1
                    self._bake_content()
                    self.queue_draw()
                return True
        return False

    def on_key_press(self, widget, event):
        if self.current_page == "wifi" and self.wifi_password_prompt_ssid:
            if event.keyval == Gdk.KEY_Escape:
                self.wifi_password_prompt_ssid = None
                self.wifi_password_input = ""
                self.wifi_status_msg = ""
                if HAS_LAYER_SHELL:
                    try:
                        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)
                    except Exception:
                        pass
                self.queue_draw()
                return True
            elif event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
                self.submit_wifi_password()
                return True
            elif event.keyval == Gdk.KEY_BackSpace:
                self.wifi_password_input = self.wifi_password_input[:-1]
                self.queue_draw()
                return True
            else:
                char = Gdk.keyval_to_unicode(event.keyval)
                if char >= 32:
                    self.wifi_password_input += chr(char)
                    self._bake_content()
                    self.queue_draw()
                    return True

        if event.keyval == Gdk.KEY_Escape:
            if self.current_page == "wifi":
                self.current_page = "controls"
                self.queue_draw()
                return True
            elif self.anim_state == "open":
                self.start_close_animation(quit_after=True)
            else:
                self.close_and_quit()
            return True
        elif event.keyval == Gdk.KEY_Tab:
            if self.anim_state == "open":
                self.toggle_page()
            return True
        return False

    def toggle_page(self):
        if self.current_page == "wifi":
            self.current_page = "controls"
        else:
            self.current_page = "notifications" if self.current_page == "controls" else "controls"
            if self.current_page == "notifications":
                self.notifications = self.load_notifications()
                self.notif_page_idx = 0
        self.queue_draw()

    def scan_wifi_networks(self, fast=True):
        if not self.wifi_radio_enabled or self.wifi_scanning:
            return
        self.wifi_scanning = True
        if not self.wifi_networks:
            self.wifi_status_msg = "Scanning networks..."
            self.queue_draw()

        def on_initial(nets, radio_on):
            def apply_initial():
                self.wifi_networks = nets
                self.wifi_radio_enabled = radio_on
                self._bake_content()
                self.queue_draw()
            GLib.idle_add(apply_initial)

        def on_complete(nets, radio_on):
            def apply_final():
                self.wifi_networks = nets
                self.wifi_scanning = False
                self.wifi_status_msg = ""
                self.wifi_radio_enabled = radio_on
                txt, wifi_ssid = WifiService.get_status()
                self.wifi_ssid = wifi_ssid
                self.wifi_text = txt
                self._bake_content()
                self.queue_draw()
            GLib.idle_add(apply_final)

        WifiService.scan_networks_async(fast=fast, on_initial=on_initial, on_complete=on_complete)

    def connect_to_network(self, ssid, password=None):
        if self.wifi_connecting:
            return
        self.wifi_connecting = True
        self.wifi_status_msg = f"Connecting to {ssid}..."
        self.queue_draw()

        def on_complete(success, err_msg):
            def apply_result():
                self.wifi_connecting = False
                if success:
                    self.wifi_password_prompt_ssid = None
                    self.wifi_password_input = ""
                    self.wifi_status_msg = f"Connected to {ssid}!"
                    self.wifi_ssid = ssid
                    self.wifi_text = "Connected"
                    GLib.timeout_add(1500, self.scan_wifi_networks)
                else:
                    self.wifi_status_msg = f"Failed: {err_msg[:20]}"
                self.queue_draw()
            GLib.idle_add(apply_result)

        WifiService.connect_async(ssid, password=password, on_complete=on_complete)

    def disconnect_wifi(self):
        self.wifi_status_msg = "Disconnecting..."
        self.queue_draw()

        def on_complete(success):
            def apply_disc():
                self.wifi_status_msg = "Disconnected"
                self.wifi_ssid = ""
                self.wifi_text = "Disconnected"
                GLib.timeout_add(1000, self.scan_wifi_networks)
                self.queue_draw()
            GLib.idle_add(apply_disc)

        WifiService.disconnect_async(on_complete=on_complete)

    def toggle_wifi_radio(self):
        curr = self.wifi_radio_enabled
        new_state = not curr
        self.wifi_radio_enabled = new_state
        if not new_state:
            self.wifi_networks = []
            self.wifi_ssid = ""
            self.wifi_text = "Disabled"
            self.wifi_status_msg = ""
        else:
            self.wifi_text = "Disconnected"
            self.wifi_status_msg = "Enabling Wi-Fi..."
        self._bake_content()
        self.queue_draw()

        def worker():
            WifiService.set_radio(new_state)
            if new_state:
                time.sleep(1.0)
                self.scan_wifi_networks(fast=False)
            else:
                def apply_off():
                    self.wifi_radio_enabled = False
                    self.wifi_networks = []
                    self.wifi_ssid = ""
                    self.wifi_text = "Disabled"
                    self.wifi_status_msg = ""
                    self._bake_content()
                    self.queue_draw()
                GLib.idle_add(apply_off)

        threading.Thread(target=worker, daemon=True).start()

    def submit_wifi_password(self):
        ssid = self.wifi_password_prompt_ssid
        pwd = self.wifi_password_input
        if not ssid:
            return
        if HAS_LAYER_SHELL:
            try:
                GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)
            except Exception:
                pass
        self.connect_to_network(ssid, password=pwd)

    def get_ime_status(self):
        try:
            out = subprocess.check_output(["fcitx5-remote", "-n"], stderr=subprocess.DEVNULL).decode().strip()
            if "unikey" in out.lower() or "bamboo" in out.lower() or "ngosen" in out.lower():
                return "Vietnamese"
            return "English"
        except Exception:
            return "English"

    def get_wifi_status(self):
        txt, ssid = WifiService.get_status()
        self.wifi_radio_enabled = (txt != "Disabled")
        return txt, ssid

    def async_refresh_status(self):
        try:
            vol = AudioService.get_volume() / 100.0
            bri = BrightnessService.get_brightness() / 100.0
            bt_on = BluetoothService.is_enabled()
            bt_dev = BluetoothService.get_connected_device_name() if bt_on else ""
            pwr = PowerService.get_power_mode()
            ime = self.get_ime_status()
            wifi_txt, wifi_ssid = self.get_wifi_status()

            if self.current_page == "wifi" and self.wifi_radio_enabled and not self.wifi_networks and not self.wifi_scanning:
                self.scan_wifi_networks(fast=True)

            def apply():
                now = time.time()
                if not self.dragging_slider and (now - self.last_slider_drag_time) > 2.0:
                    self.vol_val = vol
                    self.bri_val = bri
                changed = (
                    self.bt_enabled != bt_on or
                    self.bt_device != bt_dev or
                    self.power_mode != pwr or
                    self.ime_text != ime or
                    self.wifi_text != wifi_txt or
                    self.wifi_ssid != wifi_ssid
                )
                self.bt_enabled = bt_on
                self.bt_device = bt_dev
                self.power_mode = pwr
                self.ime_text = ime
                self.wifi_text = wifi_txt
                self.wifi_ssid = wifi_ssid
                if changed and self.anim_state == "open":
                    self._bake_content()
                    self.queue_draw()
                return False

            GLib.idle_add(apply)
        except Exception:
            pass

    def load_notifications(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def refresh_status_tick(self):
        if self.anim_state == "open":
            threading.Thread(target=self.async_refresh_status, daemon=True).start()
        return True

    # ---------------- INTERACTION ----------------
    def on_button_press(self, widget, event):
        sx = self.W_canvas / self.base_w
        sy = self.H_canvas / self.base_h
        x, y = event.x / sx, event.y / sy

        if event.button == 1:
            if self.anim_state in ("opening", "closing"):
                return True

            # 1. Closed state interaction
            if self.anim_state == "closed":
                if 180.0 <= y <= 600.0 and self.x_left <= x <= self.x_right:
                    return self.drag_manager.handle_press(event, is_inside=True)
                else:
                    self.close_and_quit()
                    return True

            # 2. Open state interaction:
            # Clicking outside the device body dismisses
            if y < 10.0 or y > self.base_h - 10.0:
                self.start_close_animation(quit_after=True)
                return True

            # If user presses on the circular slider arc, let the slider take the interaction
            if self.current_page == "controls":
                cy_poke = self.cy_pokeball
                dx = x - self.cx
                dy = y - cy_poke
                dist_poke = math.sqrt(dx**2 + dy**2)
                if 46.0 <= dist_poke <= 82.0:
                    if dy < 0:
                        self.dragging_slider = "volume"
                        self.update_slider_from_coords(x, y, "volume")
                    else:
                        self.dragging_slider = "brightness"
                        self.update_slider_from_coords(x, y, "brightness")
                    return True

            # Everywhere else on the device, arm dragging via shared drag manager
            return self.drag_manager.handle_press(event, is_inside=True)

        return False

    def on_button_release(self, widget, event):
        if event.button == 1:
            if self.dragging_slider:
                slider = self.dragging_slider
                self.dragging_slider = None
                self.last_slider_drag_time = time.time()
                if slider == "volume":
                    AudioService.set_volume(int(self.vol_val * 100.0))
                elif slider == "brightness":
                    BrightnessService.set_brightness(int(self.bri_val * 100.0))
                return True
            return self.drag_manager.handle_release(event, on_click=self.handle_click)
        return False

    def handle_click(self, px, py):
        sx = self.W_canvas / self.base_w
        sy = self.H_canvas / self.base_h
        x, y = px / sx, py / sy

        # 1. Closed state interaction
        if self.anim_state == "closed":
            if 180.0 <= y <= 600.0 and self.x_left <= x <= self.x_right:
                self.start_open_animation()
            else:
                self.close_and_quit()
            return

        if self.anim_state in ("opening", "closing"):
            return

        # 2. Open state interaction
        if y < 10.0 or y > self.base_h - 10.0:
            self.start_close_animation(quit_after=True)
            return

        # Bottom Navigation Button (Floating Bell/Bow at cx, socket_well_y)
        dist_nav = math.sqrt((x - self.cx)**2 + (y - self.socket_well_y)**2)
        if dist_nav <= 28.0:
            self.toggle_page()
            return

        # Top Mark (Bow / Bell at cx, cy_top - top_mark_offset)
        dist_top = math.sqrt((x - self.cx)**2 + (y - (190.0 - self.top_mark_offset))**2)
        if dist_top <= 24.0:
            self.toggle_page()
            return

        # Clicking on top red casing header or bottom casing footer triggers slide-closed
        y_casing_top_limit = 190.0 - (self.cut_y + self.chassis_thick + self.dark_thick)
        y_casing_bot_limit = 590.0 + (self.cut_y + self.chassis_thick + self.dark_thick)
        if y < y_casing_top_limit and abs(x - self.cx) > 40.0:
            self.start_close_animation()
            return
        if y > y_casing_bot_limit and dist_nav > 30.0:
            self.start_close_animation()
            return

        if self.current_page == "controls":
            grid_x = self.x_left + 36.0
            grid_y = 224.0
            col_w = (self.W_shell - 72.0 - 20.0) / 2.0
            row_h = 44.0
            gap_y = 24.0

            # Tile (0,0) - Input
            if grid_x <= x <= grid_x + col_w and grid_y <= y <= grid_y + row_h:
                toggle_sh = os.path.join(SYSTEM_DIR, "toggle_vietnamese.sh")
                if not os.path.exists(toggle_sh):
                    toggle_sh = os.path.expanduser("~/.config/hypr/scripts/system/toggle_vietnamese.sh")
                if os.path.exists(toggle_sh):
                    subprocess.Popen([toggle_sh])
                self.ime_text = "Vietnamese" if self.ime_text == "English" else "English"
                self._bake_content()
                self.queue_draw()
                return

            # Tile (1,0) - Wi-Fi
            c1_x = grid_x + col_w + 20.0
            if c1_x - 10.0 <= x <= c1_x + col_w + 15.0 and grid_y - 8.0 <= y <= grid_y + row_h + 8.0:
                self.current_page = "wifi"
                self.wifi_password_prompt_ssid = None
                self.wifi_password_input = ""
                self.wifi_status_msg = ""
                self.wifi_page_idx = 0
                self.scan_wifi_networks()
                self._bake_content()
                self.queue_draw()
                return

            # Tile (0,1) - Bluetooth
            r1_y = grid_y + row_h + gap_y
            if grid_x <= x <= grid_x + col_w and r1_y <= y <= r1_y + row_h:
                self.bt_enabled = BluetoothService.toggle_power()
                if not self.bt_enabled:
                    self.bt_device = ""
                self._bake_content()
                self.queue_draw()
                return

            # Tile (1,1) - Power Mode
            if c1_x <= x <= c1_x + col_w and r1_y <= y <= r1_y + row_h:
                order = ["powersave", "balanced", "performance"]
                raw = (self.power_mode or "balanced").lower()
                if raw in ("powersave", "power-saver", "power saver"):
                    curr = "powersave"
                elif raw == "performance":
                    curr = "performance"
                else:
                    curr = "balanced"
                next_idx = (order.index(curr) + 1) % len(order)
                next_mode = order[next_idx]
                PowerService.set_power_mode(next_mode)
                self.power_mode = next_mode
                self._bake_content()
                self.queue_draw()
                return

            # Center Power Button
            dist_poke = math.sqrt((x - self.cx)**2 + (y - self.cy_pokeball)**2)
            if dist_poke <= 22.0:
                wlogout_sh = os.path.join(SYSTEM_DIR, "Wlogout.sh")
                if not os.path.exists(wlogout_sh):
                    wlogout_sh = os.path.expanduser("~/.config/hypr/scripts/system/Wlogout.sh")
                if os.path.exists(wlogout_sh):
                    subprocess.Popen([wlogout_sh])
                elif shutil.which("wlogout"):
                    subprocess.Popen(["wlogout"])
                self.close_and_quit()
                return

        elif self.current_page == "notifications":
            content_x = self.x_left + 36.0
            content_w = self.W_shell - 72.0

            # 1. "Clear all notifications" button
            if len(self.notifications) > 0 and 468.0 <= y <= 496.0 and abs(x - self.cx) <= 120.0:
                if os.path.exists(CACHE_FILE):
                    try:
                        with open(CACHE_FILE, "w", encoding="utf-8") as f:
                            json.dump([], f)
                    except Exception:
                        pass
                self.notifications = []
                self.notif_page_idx = 0
                self.queue_draw()
                return

            # 2. Pagination Prev / Next if > 5 notifications
            if len(self.notifications) > 5 and 498.0 <= y <= 524.0:
                total_pages = max(1, (len(self.notifications) + 4) // 5)
                if content_x <= x <= content_x + 65.0:
                    if self.notif_page_idx > 0:
                        self.notif_page_idx -= 1
                        self._bake_content()
                    self.queue_draw()
                    return
                elif content_x + content_w - 65.0 <= x <= content_x + content_w:
                    if self.notif_page_idx < total_pages - 1:
                        self.notif_page_idx += 1
                        self._bake_content()
                    self.queue_draw()
                    return

            # 3. Click individual notification row to dismiss it
            start_idx = self.notif_page_idx * 5
            page_notifs = self.notifications[start_idx : start_idx + 5]
            for idx in range(len(page_notifs)):
                item_y = 214.0 + idx * 49.0
                if content_x <= x <= content_x + content_w and item_y <= y <= item_y + 46.0:
                    real_idx = start_idx + idx
                    if real_idx < len(self.notifications):
                        del self.notifications[real_idx]
                        if os.path.exists(CACHE_FILE):
                            try:
                                with open(CACHE_FILE, "w", encoding="utf-8") as f:
                                    json.dump(self.notifications, f, ensure_ascii=False, indent=2)
                            except Exception:
                                pass
                        max_page = max(0, (len(self.notifications) - 1) // 5)
                        if self.notif_page_idx > max_page:
                            self.notif_page_idx = max_page
                        self._bake_content()
                    self.queue_draw()
                    return

        elif self.current_page == "wifi":
            content_x = self.x_left + 36.0
            content_w = self.W_shell - 72.0

            # 1. Wi-Fi toggle: [content_x + content_w - 110.0, content_x + content_w - 55.0], y in [210.0, 236.0]
            if content_x + content_w - 110.0 <= x <= content_x + content_w - 55.0 and 210.0 <= y <= 236.0:
                self.toggle_wifi_radio()
                return

            # 2. Rescan button: [content_x + content_w - 52.0, content_x + content_w + 5.0], y in [210.0, 236.0]
            if content_x + content_w - 52.0 <= x <= content_x + content_w + 5.0 and 210.0 <= y <= 236.0:
                self.scan_wifi_networks(fast=False)
                return

            # 3. Disconnect if connected: [content_x + content_w - 110.0, content_x + content_w + 5.0], y in [236.0, 258.0]
            if self.wifi_ssid and content_x + content_w - 110.0 <= x <= content_x + content_w + 5.0 and 236.0 <= y <= 258.0:
                self.disconnect_wifi()
                return

            # 4. Password prompt mode
            if self.wifi_password_prompt_ssid:
                if content_x <= x <= content_x + 115.0 and 368.0 <= y <= 408.0:
                    self.submit_wifi_password()
                    return
                if content_x + 125.0 <= x <= content_x + 210.0 and 368.0 <= y <= 408.0:
                    self.wifi_password_prompt_ssid = None
                    self.wifi_password_input = ""
                    self.wifi_status_msg = ""
                    if HAS_LAYER_SHELL:
                        try:
                            GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)
                        except Exception:
                            pass
                    self._bake_content()
                    self.queue_draw()
                    return
                return

            # 5. Network items mode (5 clean floating rows)
            start_idx = self.wifi_page_idx * 5
            page_nets = self.wifi_networks[start_idx : start_idx + 5]
            curr_y = 262.0
            for idx, net in enumerate(page_nets):
                if content_x - 6.0 <= x <= content_x + content_w + 6.0 and curr_y - 4.0 <= y <= curr_y + 44.0:
                    if net.get("in_use"):
                        self.wifi_status_msg = f"Connected to {net.get('ssid')}"
                        self._bake_content()
                        self.queue_draw()
                        return
                    elif net.get("saved") or not (net.get("security") and net.get("security") != "--"):
                        self.connect_to_network(net["ssid"])
                        return
                    else:
                        self.wifi_password_prompt_ssid = net["ssid"]
                        self.wifi_password_input = ""
                        self.wifi_status_msg = ""
                        if HAS_LAYER_SHELL:
                            try:
                                GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
                            except Exception:
                                pass
                        self.grab_focus()
                        self._bake_content()
                        self.queue_draw()
                        return
                curr_y += 48.0

            # 6. Pagination buttons
            if len(self.wifi_networks) > 5:
                py_y = 514.0
                total_pages = max(1, (len(self.wifi_networks) + 4) // 5)
                if content_x <= x <= content_x + 70.0 and py_y - 6.0 <= y <= py_y + 24.0:
                    if self.wifi_page_idx > 0:
                        self.wifi_page_idx -= 1
                        self._bake_content()
                    self.queue_draw()
                    return
                if content_x + content_w - 70.0 <= x <= content_x + content_w and py_y - 6.0 <= y <= py_y + 24.0:
                    if self.wifi_page_idx < total_pages - 1:
                        self.wifi_page_idx += 1
                        self._bake_content()
                    self.queue_draw()
                    return

    def on_leave_notify(self, widget, event):
        if self.hovered_item is not None:
            self.hovered_item = None
            self.queue_draw()
        win = self.get_window()
        if win and not self.is_dragging:
            win.set_cursor(None)
        return False

    def on_motion_notify(self, widget, event):
        sx = self.W_canvas / self.base_w
        sy = self.H_canvas / self.base_h
        x, y = event.x / sx, event.y / sy

        # 1. Slider dragging
        if self.anim_state == "open" and self.dragging_slider:
            self.update_slider_from_coords(x, y, self.dragging_slider)
            return True

        # 2. Window dragging delegation
        if self.drag_manager.handle_motion(event):
            return True

        # 3. Hover feedback & cursor updates
        win = self.get_window()
        if self.anim_state == "closed":
            if win and not self.is_dragging:
                if 180.0 <= y <= 600.0 and self.x_left <= x <= self.x_right:
                    win.set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "grab"))
                else:
                    win.set_cursor(None)
            return False

        if self.anim_state == "open":
            new_hover = None

            if self.current_page == "controls":
                grid_x = self.x_left + 36.0
                grid_y = 224.0
                col_w = (self.W_shell - 72.0 - 20.0) / 2.0
                row_h = 44.0
                gap_y = 24.0
                c1_x = grid_x + col_w + 20.0
                r1_y = grid_y + row_h + gap_y

                if grid_x <= x <= grid_x + col_w and grid_y <= y <= grid_y + row_h:
                    new_hover = "ime"
                elif c1_x - 10.0 <= x <= c1_x + col_w + 15.0 and grid_y - 8.0 <= y <= grid_y + row_h + 8.0:
                    new_hover = "wifi"
                elif grid_x <= x <= grid_x + col_w and r1_y <= y <= r1_y + row_h:
                    new_hover = "bt"
                elif c1_x <= x <= c1_x + col_w and r1_y <= y <= r1_y + row_h:
                    new_hover = "power"
                else:
                    dist_pwr = math.sqrt((x - self.cx)**2 + (y - self.cy_pokeball)**2)
                    if dist_pwr <= 22.0:
                        new_hover = "pokeball_pwr"
                    else:
                        dist_nav = math.sqrt((x - self.cx)**2 + (y - self.socket_well_y)**2)
                        if dist_nav <= 24.0:
                            new_hover = "nav"

            elif self.current_page == "wifi":
                content_x = self.x_left + 36.0
                content_w = self.W_shell - 72.0

                if content_x + content_w - 110.0 <= x <= content_x + content_w - 55.0 and 210.0 <= y <= 236.0:
                    new_hover = "wifi_toggle"
                elif content_x + content_w - 52.0 <= x <= content_x + content_w + 5.0 and 210.0 <= y <= 236.0:
                    new_hover = "wifi_rescan"
                elif self.wifi_ssid and content_x + content_w - 110.0 <= x <= content_x + content_w + 5.0 and 236.0 <= y <= 258.0:
                    new_hover = "wifi_disconnect"
                elif self.wifi_password_prompt_ssid:
                    if content_x <= x <= content_x + 115.0 and 368.0 <= y <= 408.0:
                        new_hover = "wifi_pass_connect"
                    elif content_x + 125.0 <= x <= content_x + 210.0 and 368.0 <= y <= 408.0:
                        new_hover = "wifi_pass_cancel"
                else:
                    start_idx = self.wifi_page_idx * 5
                    page_nets = self.wifi_networks[start_idx : start_idx + 5]
                    curr_y = 262.0
                    for idx in range(len(page_nets)):
                        if content_x - 6.0 <= x <= content_x + content_w + 6.0 and curr_y - 4.0 <= y <= curr_y + 44.0:
                            new_hover = f"wifi_item_{idx}"
                            break
                        curr_y += 48.0
                    if not new_hover and len(self.wifi_networks) > 5:
                        py_y = 514.0
                        if content_x <= x <= content_x + 70.0 and py_y - 6.0 <= y <= py_y + 24.0:
                            new_hover = "wifi_prev"
                        elif content_x + content_w - 70.0 <= x <= content_x + content_w and py_y - 6.0 <= y <= py_y + 24.0:
                            new_hover = "wifi_next"
                    if not new_hover:
                        dist_nav = math.sqrt((x - self.cx)**2 + (y - self.socket_well_y)**2)
                        if dist_nav <= 28.0:
                            new_hover = "nav"

            elif self.current_page == "notifications":
                grid_x = self.x_left + 36.0
                grid_y = 214.0
                row_w = self.W_shell - 72.0
                card_h = 46.0
                card_pitch = 49.0

                start_idx = self.notif_page_idx * 5
                page_notifs = self.notifications[start_idx : start_idx + 5]
                for idx in range(len(page_notifs)):
                    item_y = grid_y + idx * card_pitch
                    if grid_x - 6.0 <= x <= grid_x + row_w + 6.0 and item_y - 2.0 <= y <= item_y + card_h:
                        new_hover = f"notif_{idx}"
                        break

                if not new_hover and len(self.notifications) > 0:
                    if 468.0 <= y <= 496.0 and abs(x - self.cx) <= 120.0:
                        new_hover = "clear_all"
                    elif len(self.notifications) > 5 and 498.0 <= y <= 524.0:
                        if grid_x <= x <= grid_x + 65.0:
                            new_hover = "notif_prev"
                        elif grid_x + row_w - 65.0 <= x <= grid_x + row_w:
                            new_hover = "notif_next"

                if not new_hover:
                    dist_nav = math.sqrt((x - self.cx)**2 + (y - self.socket_well_y)**2)
                    if dist_nav <= 24.0:
                        new_hover = "nav"

            if new_hover != self.hovered_item:
                self.hovered_item = new_hover
                self.queue_draw()

            if win and not self.is_dragging:
                if new_hover:
                    win.set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "pointer"))
                elif 46.0 <= math.sqrt((x - self.cx)**2 + (y - self.cy_pokeball)**2) <= 82.0 and self.current_page == "controls":
                    win.set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "pointer"))
                elif 10.0 <= y <= self.base_h - 10.0:
                    win.set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "grab"))
                else:
                    win.set_cursor(None)

        return False

    def update_slider_from_coords(self, x, y, slider_type):
        cy_poke = self.cy_pokeball
        dx = x - self.cx
        dy = y - cy_poke
        self.last_slider_drag_time = time.time()
        now = time.time()

        gap_deg = 16.0

        if slider_type == "volume":
            # Volume: top arc (left=-164 deg -> right=-16 deg)
            start_deg = -180.0 + gap_deg  # -164.0 deg (0%)
            end_deg = -gap_deg            # -16.0 deg (100%)
            span_deg = end_deg - start_deg # 148.0 deg

            if dy > 0:
                # Below equator: clamp to 0% if on left, 100% if on right
                val = 1.0 if dx > 0 else 0.0
            else:
                a_deg = math.degrees(math.atan2(dy, dx)) # [-180, 0]
                if a_deg <= start_deg:
                    val = 0.0
                elif a_deg >= end_deg:
                    val = 1.0
                else:
                    val = (a_deg - start_deg) / span_deg

            self.vol_val = max(0.0, min(1.0, val))
            self.queue_draw()
            if (now - self.last_vol_set_time) >= 0.04:
                self.last_vol_set_time = now
                AudioService.set_volume(int(self.vol_val * 100.0))

        elif slider_type == "brightness":
            # Brightness: bottom arc (left=164 deg -> right=16 deg)
            start_deg = 180.0 - gap_deg   # 164.0 deg (0%)
            end_deg = gap_deg             # 16.0 deg (100%)
            span_deg = start_deg - end_deg # 148.0 deg

            if dy < 0:
                # Above equator: clamp to 0% if on left, 100% if on right (PREVENTS 100% -> 0% WRAP)
                val = 1.0 if dx > 0 else 0.0
            else:
                a_deg = math.degrees(math.atan2(dy, dx)) # [0, 180]
                if a_deg >= start_deg:
                    val = 0.0
                elif a_deg <= end_deg:
                    val = 1.0
                else:
                    val = (start_deg - a_deg) / span_deg

            self.bri_val = max(0.0, min(1.0, val))
            self.queue_draw()
            if (now - self.last_bri_set_time) >= 0.04:
                self.last_bri_set_time = now
                BrightnessService.set_brightness(int(self.bri_val * 100.0))

    # ---------------- DYNAMIC COORDINATES ----------------
    def get_dynamic_coords(self, p):
        # p=0.0: closed, p=1.0: fully open
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

        ang_dark_bot_start = math.asin(dy_dark / self.r_dark)
        ang_dark_bot_end = math.pi - math.asin(dy_dark / self.r_dark)
        ang_chassis_bot_start = math.asin(dy_chassis / self.r_chassis)
        ang_chassis_bot_end = math.pi - math.asin(dy_chassis / self.r_chassis)
        ang_outer_bot_start = math.asin(self.cut_y / self.r_outer)
        ang_outer_bot_end = math.pi - math.asin(self.cut_y / self.r_outer)
        ang_inner_bot_start = math.asin(self.cut_y / self.r_inner)
        ang_inner_bot_end = math.pi - math.asin(self.cut_y / self.r_inner)

        top_casing_y = cy_top - 190.0
        bot_casing_y = cy_bot - 590.0

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
            "ang_dark_bot_start": ang_dark_bot_start,
            "ang_dark_bot_end": ang_dark_bot_end,
            "ang_chassis_bot_start": ang_chassis_bot_start,
            "ang_chassis_bot_end": ang_chassis_bot_end,
            "ang_outer_bot_start": ang_outer_bot_start,
            "ang_outer_bot_end": ang_outer_bot_end,
            "ang_inner_bot_start": ang_inner_bot_start,
            "ang_inner_bot_end": ang_inner_bot_end,
            "top_casing_y": top_casing_y,
            "bot_casing_y": bot_casing_y,
        }

    # ---------------- MASTER DRAW PIPELINE ----------------
    def _bake_casings(self):
        W, H = int(self.base_w), int(self.base_h)
        geo0 = self.get_dynamic_coords(1.0)
        c_dark_r, c_dark_g, c_dark_b = self.c_flange
        prot = 2.5; r_cuff = 2.5

        # 1. Top Casing Assembly
        top_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        tcr = cairo.Context(top_surf)
        tcr.set_antialias(cairo.ANTIALIAS_DEFAULT)
        y_dark_top_base = 190.0 - (self.cut_y + self.chassis_thick + self.dark_thick)

        create_top_red_casing_path(tcr, self.x_left, self.x_right, y_dark_top_base, self.cx, 190.0, self.r_dark, geo0["ang_dark_top_start"], geo0["ang_dark_top_end"], geo0["x_dark_cut"], self.device_r, notch_d=self.notch_d, trans=self.trans)
        red_pat = cairo.LinearGradient(self.x_left, 0, self.x_right, 0)
        red_pat.add_color_stop_rgb(0, *self.c_casing_l); red_pat.add_color_stop_rgb(0.5, *self.c_casing_m); red_pat.add_color_stop_rgb(1, *self.c_casing_r)
        tcr.set_source(red_pat); tcr.fill()

        draw_anime_grooves(tcr, self.x_left, 0, self.grooves, 0, 0.5 * math.pi)
        draw_anime_grooves(tcr, self.x_right, 0, self.grooves, 0.5 * math.pi, math.pi)

        create_top_red_casing_path(tcr, self.x_left, self.x_right, y_dark_top_base, self.cx, 190.0, self.r_dark, geo0["ang_dark_top_start"], geo0["ang_dark_top_end"], geo0["x_dark_cut"], self.device_r, notch_d=self.notch_d, trans=self.trans)
        tcr.set_source_rgba(*self.c_border_3d); tcr.set_line_width(2.0); tcr.stroke()

        create_top_red_casing_path(tcr, self.x_left + 1.6, self.x_right - 1.6, y_dark_top_base - 0.8, self.cx, 190.0, self.r_dark - 1.2, geo0["ang_dark_top_start"], geo0["ang_dark_top_end"], geo0["x_dark_cut"], max(4.0, self.device_r - 1.6), notch_d=self.notch_d, trans=self.trans, y_top=1.6)
        tcr.set_source_rgba(*self.c_tactile_white); tcr.set_line_width(1.3); tcr.stroke()

        tcr.new_sub_path()
        tcr.move_to(self.x_left, geo0["y_silver_top"]); tcr.line_to(self.x_left, geo0["y_dark_top"]); tcr.line_to(self.cx - geo0["x_dark_cut"], geo0["y_dark_top"])
        tcr.arc(self.cx, 190.0, self.r_dark, geo0["ang_dark_top_end"], geo0["ang_dark_top_start"])
        tcr.line_to(self.x_right, geo0["y_dark_top"]); tcr.line_to(self.x_right, geo0["y_silver_top"]); tcr.line_to(self.cx + geo0["x_chassis_cut"], geo0["y_silver_top"])
        tcr.arc_negative(self.cx, 190.0, self.r_chassis, geo0["ang_chassis_top_start"], geo0["ang_chassis_top_end"]); tcr.close_path()
        tcr.set_source_rgba(c_dark_r, c_dark_g, c_dark_b, 0.85); tcr.fill()
        tcr.move_to(self.x_left, geo0["y_dark_top"]); tcr.line_to(self.cx - geo0["x_dark_cut"], geo0["y_dark_top"])
        tcr.arc(self.cx, 190.0, self.r_dark, geo0["ang_dark_top_end"], geo0["ang_dark_top_start"]); tcr.line_to(self.x_right, geo0["y_dark_top"])
        tcr.set_source_rgba(*self.c_border_3d); tcr.set_line_width(1.4); tcr.stroke()

        tcr.new_sub_path()
        tcr.move_to(self.x_left, geo0["y_edge_top"]); tcr.arc(self.x_left, geo0["y_edge_top"] - r_cuff, r_cuff, 0.5 * math.pi, math.pi)
        tcr.line_to(self.x_left - prot, geo0["y_dark_top"] + r_cuff); tcr.arc(self.x_left, geo0["y_dark_top"] + r_cuff, r_cuff, math.pi, 1.5 * math.pi)
        tcr.line_to(self.x_left, geo0["y_silver_top"]); tcr.line_to(self.cx - geo0["x_chassis_cut"], geo0["y_silver_top"])
        tcr.arc(self.cx, 190.0, self.r_chassis, geo0["ang_chassis_top_end"], geo0["ang_chassis_top_start"]); tcr.line_to(self.x_right, geo0["y_silver_top"])
        tcr.line_to(self.x_right, geo0["y_dark_top"]); tcr.arc(self.x_right, geo0["y_dark_top"] + r_cuff, r_cuff, 1.5 * math.pi, 2 * math.pi)
        tcr.line_to(self.x_right + prot, geo0["y_edge_top"] - r_cuff); tcr.arc(self.x_right, geo0["y_edge_top"] - r_cuff, r_cuff, 0, 0.5 * math.pi)
        tcr.line_to(self.cx + geo0["x_outer_cut"], geo0["y_edge_top"]); tcr.arc_negative(self.cx, 190.0, self.r_outer, geo0["ang_outer_top_start"], geo0["ang_outer_top_end"]); tcr.close_path()
        silver_pat_top = cairo.LinearGradient(self.x_left, geo0["y_dark_top"], self.x_left, geo0["y_edge_top"])
        silver_pat_top.add_color_stop_rgb(0.0, *hex_to_rgba(C_TEXT_PRI)[:3]); silver_pat_top.add_color_stop_rgb(1.0, *hex_to_rgba(C_TEXT_SEC)[:3])
        tcr.set_source(silver_pat_top); tcr.fill_preserve(); tcr.set_source_rgba(*self.c_border_3d); tcr.set_line_width(1.4); tcr.stroke()

        band_pat_top = cairo.LinearGradient(self.cx - self.r_outer, 190.0, self.cx + self.r_outer, 190.0)
        band_pat_top.add_color_stop_rgb(0, *self.c_band_stop0); band_pat_top.add_color_stop_rgb(0.5, *self.c_band_stop1); band_pat_top.add_color_stop_rgb(1, *self.c_band_stop2)
        tcr.new_sub_path()
        tcr.arc_negative(self.cx, 190.0, self.r_outer, geo0["ang_outer_top_start"], geo0["ang_outer_top_end"]); tcr.line_to(self.cx - geo0["x_inner_cut"], geo0["y_edge_top"])
        tcr.arc(self.cx, 190.0, self.r_inner, geo0["ang_inner_top_end"], geo0["ang_inner_top_start"]); tcr.close_path()
        tcr.set_source(band_pat_top); tcr.fill_preserve(); tcr.set_source_rgba(*self.c_border_3d); tcr.set_line_width(1.6); tcr.stroke()
        tcr.arc(self.cx, 190.0, self.r_inner, geo0["ang_inner_top_end"], geo0["ang_inner_top_start"])
        tcr.set_source_rgba(0, 0, 0, 0.35); tcr.set_line_width(2.2); tcr.stroke()
        self._cached_top_casing = top_surf

        # 2. Bottom Casing Assembly
        bot_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        bcr = cairo.Context(bot_surf)
        bcr.set_antialias(cairo.ANTIALIAS_DEFAULT)
        y_dark_bot_base = 590.0 + (self.cut_y + self.chassis_thick + self.dark_thick)
        for s in range(4):
            dy = 5.0 * (s / 3.0)
            bcr.save(); bcr.translate(0, dy)
            create_bottom_red_casing_path(bcr, self.x_left, self.x_right, y_dark_bot_base, 780.0, self.cx, 590.0, self.r_dark, geo0["ang_dark_bot_start"], geo0["ang_dark_bot_end"], geo0["x_dark_cut"], self.device_r, notch_d=self.notch_d, trans=self.trans)
            bcr.set_source_rgba(*self.c_border_3d); bcr.fill(); bcr.restore()
        create_bottom_red_casing_path(bcr, self.x_left, self.x_right, y_dark_bot_base, 780.0, self.cx, 590.0, self.r_dark, geo0["ang_dark_bot_start"], geo0["ang_dark_bot_end"], geo0["x_dark_cut"], self.device_r, notch_d=self.notch_d, trans=self.trans)
        red_pat_b = cairo.LinearGradient(self.x_left, 0, self.x_right, 0)
        red_pat_b.add_color_stop_rgb(0, *self.c_casing_l); red_pat_b.add_color_stop_rgb(0.5, *self.c_casing_m); red_pat_b.add_color_stop_rgb(1, *self.c_casing_r)
        bcr.set_source(red_pat_b); bcr.fill()
        draw_anime_grooves(bcr, self.x_left, 780.0, self.grooves, 1.5 * math.pi, 2 * math.pi)
        draw_anime_grooves(bcr, self.x_right, 780.0, self.grooves, math.pi, 1.5 * math.pi)
        create_bottom_red_casing_path(bcr, self.x_left, self.x_right, y_dark_bot_base, 780.0, self.cx, 590.0, self.r_dark, geo0["ang_dark_bot_start"], geo0["ang_dark_bot_end"], geo0["x_dark_cut"], self.device_r, notch_d=self.notch_d, trans=self.trans)
        bcr.set_source_rgba(*self.c_border_3d); bcr.set_line_width(2.0); bcr.stroke()
        create_bottom_red_casing_path(bcr, self.x_left + 1.6, self.x_right - 1.6, y_dark_bot_base + 0.8, 778.4, self.cx, 590.0, self.r_dark - 1.2, geo0["ang_dark_bot_start"], geo0["ang_dark_bot_end"], geo0["x_dark_cut"], max(4.0, self.device_r - 1.6), notch_d=self.notch_d, trans=self.trans)
        bcr.set_source_rgba(*self.c_tactile_white); bcr.set_line_width(1.3); bcr.stroke()
        bcr.new_sub_path()
        bcr.move_to(self.x_left, geo0["y_silver_bot"]); bcr.line_to(self.x_left, geo0["y_dark_bot"]); bcr.line_to(self.cx - geo0["x_dark_cut"], geo0["y_dark_bot"])
        bcr.arc_negative(self.cx, 590.0, self.r_dark, geo0["ang_dark_bot_end"], geo0["ang_dark_bot_start"])
        bcr.line_to(self.x_right, geo0["y_dark_bot"]); bcr.line_to(self.x_right, geo0["y_silver_bot"]); bcr.line_to(self.cx + geo0["x_chassis_cut"], geo0["y_silver_bot"])
        bcr.arc(self.cx, 590.0, self.r_chassis, geo0["ang_chassis_bot_start"], geo0["ang_chassis_bot_end"]); bcr.close_path()
        bcr.set_source_rgba(c_dark_r, c_dark_g, c_dark_b, 0.85); bcr.fill()
        bcr.move_to(self.x_left, geo0["y_dark_bot"]); bcr.line_to(self.cx - geo0["x_dark_cut"], geo0["y_dark_bot"])
        bcr.arc_negative(self.cx, 590.0, self.r_dark, geo0["ang_dark_bot_end"], geo0["ang_dark_bot_start"]); bcr.line_to(self.x_right, geo0["y_dark_bot"])
        bcr.set_source_rgba(*self.c_border_3d); bcr.set_line_width(1.4); bcr.stroke()
        y_up_top = geo0["y_edge_bot"] - self.cuff_ext
        bcr.new_sub_path()
        bcr.move_to(self.x_left, geo0["y_edge_bot"]); bcr.line_to(self.x_left, y_up_top)
        bcr.arc_negative(self.x_left, y_up_top + r_cuff, r_cuff, 1.5 * math.pi, math.pi)
        bcr.line_to(self.x_left - prot, geo0["y_silver_bot"] - r_cuff)
        bcr.arc_negative(self.x_left, geo0["y_silver_bot"] - r_cuff, r_cuff, math.pi, 0.5 * math.pi)
        bcr.line_to(self.cx - geo0["x_chassis_cut"], geo0["y_silver_bot"])
        bcr.arc_negative(self.cx, 590.0, self.r_chassis, geo0["ang_chassis_bot_end"], geo0["ang_chassis_bot_start"])
        bcr.line_to(self.x_right, geo0["y_silver_bot"])
        bcr.arc_negative(self.x_right, geo0["y_silver_bot"] - r_cuff, r_cuff, 0.5 * math.pi, 0)
        bcr.line_to(self.x_right + prot, y_up_top + r_cuff)
        bcr.arc_negative(self.x_right, y_up_top + r_cuff, r_cuff, 0, 1.5 * math.pi)
        bcr.line_to(self.x_right, geo0["y_edge_bot"]); bcr.line_to(self.cx + geo0["x_outer_cut"], geo0["y_edge_bot"])
        bcr.arc(self.cx, 590.0, self.r_outer, geo0["ang_outer_bot_start"], geo0["ang_outer_bot_end"])
        bcr.close_path()
        silver_pat_bot = cairo.LinearGradient(self.x_left, geo0["y_edge_bot"], self.x_left, geo0["y_silver_bot"])
        silver_pat_bot.add_color_stop_rgb(0.0, *hex_to_rgba(C_TEXT_SEC)[:3]); silver_pat_bot.add_color_stop_rgb(1.0, *hex_to_rgba(C_TEXT_PRI)[:3])
        bcr.set_source(silver_pat_bot); bcr.fill_preserve(); bcr.set_source_rgba(*self.c_border_3d); bcr.set_line_width(1.4); bcr.stroke()
        band_pat_bot = cairo.LinearGradient(self.cx - self.r_outer, 590.0, self.cx + self.r_outer, 590.0)
        band_pat_bot.add_color_stop_rgb(0, *self.c_band_stop0); band_pat_bot.add_color_stop_rgb(0.5, *self.c_band_stop1); band_pat_bot.add_color_stop_rgb(1, *self.c_band_stop2)
        bcr.new_sub_path()
        bcr.arc(self.cx, 590.0, self.r_outer, geo0["ang_outer_bot_start"], geo0["ang_outer_bot_end"])
        bcr.line_to(self.cx - geo0["x_inner_cut"], geo0["y_edge_bot"])
        bcr.arc_negative(self.cx, 590.0, self.r_inner, geo0["ang_inner_bot_end"], geo0["ang_inner_bot_start"])
        bcr.close_path()
        bcr.set_source(band_pat_bot); bcr.fill_preserve(); bcr.set_source_rgba(*self.c_border_3d); bcr.set_line_width(1.6); bcr.stroke()
        bcr.arc(self.cx, 590.0, self.r_inner, geo0["ang_inner_bot_start"], geo0["ang_inner_bot_end"])
        bcr.set_source_rgba(0, 0, 0, 0.35); bcr.set_line_width(2.2); bcr.stroke()
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
        socket_well_y = self.socket_well_y

        if self.current_page == "controls":
            # KERNED CURVED HEADER: Perfectly contained within the arc band
            draw_curved_kerned_cached(cr, "CONTROL CENTER", self.cx, cy_top, r_text=62.0, font_desc="DejaVu Sans Bold 8.5", letter_spacing=1.6)

            # Bow icon at the top
            cr.save()
            draw_bow_mark(cr, self.cx, cy_top - self.top_mark_offset, size=22.0, color=self.c_accent_rgb)
            cr.restore()

            # Floating Quick Tiles
            grid_x = self.x_left + 36.0
            grid_y = 224.0
            col_w = (self.W_shell - 72.0 - 20.0) / 2.0
            row_h = 44.0
            gap_y = 24.0

            # Dynamic Tile Resolution: Bluetooth, Power Mode, Wi-Fi, Input (Always Red)
            if self.bt_enabled:
                bt_icon = "󰂱" if self.bt_device else "󰂯"
                bt_val = self.bt_device if self.bt_device else "Enabled"
            else:
                bt_icon = "󰂲"
                bt_val = "Disabled"

            pwr_lower = (self.power_mode or "balanced").lower()
            if pwr_lower == "performance":
                pwr_icon = "󰓅"
                pwr_val = "Performance"
            elif pwr_lower in ("powersave", "power-saver", "power saver"):
                pwr_icon = "󰌪"
                pwr_val = "Power Saver"
            else:
                pwr_icon = "󰾅"
                pwr_val = "Balanced"

            if not self.wifi_radio_enabled or self.wifi_text == "Disabled":
                wifi_icon = "󰤮"
                wifi_val = "Disabled"
            elif self.wifi_text == "Connected" or self.wifi_ssid:
                wifi_icon = "󰤨"
                wifi_val = self.wifi_ssid if self.wifi_ssid else "Connected"
            else:
                wifi_icon = "󰖪"
                wifi_val = "Disconnected"

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
                # Perfectly center icon horizontally in box_w
                ic_x = c_x + (box_w - ink.width) / 2.0 - ink.x
                cr.move_to(ic_x, c_y + 4.0)
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

            # Pokéball Dual Slider + Power Button (Option B)
            cy_pokeball = self.cy_pokeball
            draw_pokeball_dual_slider(
                cr, self.cx, cy_pokeball, 
                R=64.0, thickness=12.0, 
                vol_val=self.vol_val, bri_val=self.bri_val, 
                knob_style="round_knob",
                icon_color=self.c_accent,
                accent_rgb=self.c_accent_rgb,
                dark_color=self.c_slider_dark,
                pwr_bg=self.c_pwr_bg
            )

            # Bottom Navigation: Pure Floating Bell
            btn_y = socket_well_y
            cr.save()
            draw_bell_icon(cr, self.cx, btn_y, font_size=20, color=self.c_accent)
            cr.restore()

        elif self.current_page == "notifications":
            # KERNED CURVED HEADER: Perfectly contained within the arc band
            draw_curved_kerned_cached(cr, "NOTIFICATIONS", self.cx, cy_top, r_text=62.0, font_desc="DejaVu Sans Bold 8.5", letter_spacing=1.6)

            # Bell icon at top of Notifications
            cr.save()
            draw_bell_icon(cr, self.cx, cy_top - self.top_mark_offset, font_size=11, color=self.c_accent)
            cr.restore()

            # Notification stream (5 items per page)
            grid_x = self.x_left + 36.0
            grid_y = 214.0
            row_w = self.W_shell - 72.0

            notifs = self.notifications
            if not notifs:
                # Minimalist empty state in accent red (pops clearly on holographic cyan screen)
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
                page_notifs = notifs[start_idx : start_idx + 5]

                for idx, item in enumerate(page_notifs):
                    item_y = grid_y + idx * 49.0
                    is_hover = (self.hovered_item == f"notif_{idx}")

                    cr.save()
                    # Subtle wash on hover
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

                    # Icon
                    l_ic = PangoCairo.create_layout(cr)
                    l_ic.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font 16"))
                    l_ic.set_markup(f"<span color='{icon_col}'>{icon}</span>", -1)
                    cr.move_to(grid_x, item_y + 2.0)
                    PangoCairo.show_layout(cr, l_ic)

                    txt_x = grid_x + 28.0
                    max_text_w = row_w - (50.0 if is_hover else 32.0)

                    # Line 1: App name + relative time
                    l_app = PangoCairo.create_layout(cr)
                    l_app.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 10"))
                    l_app.set_width(int(max_text_w * Pango.SCALE))
                    l_app.set_ellipsize(Pango.EllipsizeMode.END)
                    l_app.set_markup(f"<span color='{C_BG_WIN}'>{app}</span>  <span color='{C_BG_WIN}' alpha='50%'>• {time_str}</span>", -1)
                    cr.move_to(txt_x, item_y)
                    PangoCairo.show_layout(cr, l_app)

                    # Line 2: Title / Summary
                    l_tit = PangoCairo.create_layout(cr)
                    l_tit.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 9.5"))
                    l_tit.set_width(int(max_text_w * Pango.SCALE))
                    l_tit.set_ellipsize(Pango.EllipsizeMode.END)
                    l_tit.set_markup(f"<span color='{self.c_accent}'>{title}</span>", -1)
                    cr.move_to(txt_x, item_y + 15.0)
                    PangoCairo.show_layout(cr, l_tit)

                    # Line 3: Body text
                    l_bod = PangoCairo.create_layout(cr)
                    l_bod.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font 8.5"))
                    l_bod.set_width(int(max_text_w * Pango.SCALE))
                    l_bod.set_ellipsize(Pango.EllipsizeMode.END)
                    l_bod.set_markup(f"<span color='{C_BG_WIN}' alpha='75%'>{body}</span>", -1)
                    cr.move_to(txt_x, item_y + 29.0)
                    PangoCairo.show_layout(cr, l_bod)

                    # Hover dismiss '󰅖' indicator on right
                    if is_hover:
                        l_del = PangoCairo.create_layout(cr)
                        l_del.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 11"))
                        l_del.set_markup(f"<span color='{self.c_accent}'>󰅖</span>", -1)
                        cr.move_to(grid_x + row_w - 14.0, item_y + 14.0)
                        PangoCairo.show_layout(cr, l_del)

                    cr.restore()

                # "Clear all notifications" button
                cr.save()
                is_clr_hover = (self.hovered_item == "clear_all")
                clr_col = self.c_accent_hover if is_clr_hover else self.c_accent
                l_clr = PangoCairo.create_layout(cr)
                l_clr.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 10.5"))
                l_clr.set_markup(f"<span color='{clr_col}'>󰆴 Clear all notifications</span>", -1)
                ink, log = l_clr.get_pixel_extents()
                cr.move_to(self.cx - ink.width / 2.0, 478.0)
                PangoCairo.show_layout(cr, l_clr)
                cr.restore()

                # Floating Pagination Row (if > 5 notifications)
                if len(notifs) > 5:
                    cr.save()
                    total_pages = max(1, (len(notifs) + 4) // 5)
                    py_y = 504.0

                    # Prev
                    is_pv_hover = (self.hovered_item == "notif_prev")
                    pv_col = self.c_accent if is_pv_hover else (C_BG_WIN if self.notif_page_idx > 0 else C_TEXT_MUT)
                    l_prv = PangoCairo.create_layout(cr)
                    l_prv.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 10"))
                    l_prv.set_markup(f"<span color='{pv_col}'><b>◀ Prev</b></span>", -1)
                    cr.move_to(grid_x + 4.0, py_y)
                    PangoCairo.show_layout(cr, l_prv)

                    # Page indicator
                    l_pg = PangoCairo.create_layout(cr)
                    l_pg.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 9.5"))
                    l_pg.set_markup(f"<span color='{C_BG_WIN}' alpha='75%'><b>{self.notif_page_idx + 1} / {total_pages}</b></span>", -1)
                    ink, _ = l_pg.get_pixel_extents()
                    cr.move_to(self.cx - ink.width / 2.0, py_y)
                    PangoCairo.show_layout(cr, l_pg)

                    # Next
                    is_nx_hover = (self.hovered_item == "notif_next")
                    nx_col = self.c_accent if is_nx_hover else (C_BG_WIN if self.notif_page_idx < total_pages - 1 else C_TEXT_MUT)
                    l_nxt = PangoCairo.create_layout(cr)
                    l_nxt.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 10"))
                    l_nxt.set_markup(f"<span color='{nx_col}'><b>Next ▶</b></span>", -1)
                    cr.move_to(grid_x + row_w - 52.0, py_y)
                    PangoCairo.show_layout(cr, l_nxt)
                    cr.restore()

            # Bottom Navigation: Bow on Notifications
            btn_y = socket_well_y
            cr.save()
            draw_bow_mark(cr, self.cx, btn_y, size=34.0, color=self.c_accent_rgb)
            cr.restore()

        elif self.current_page == "wifi":
            # KERNED CURVED HEADER: Perfectly contained within the arc band
            draw_curved_kerned_cached(cr, "WI-FI NETWORKS", self.cx, cy_top, r_text=62.0, font_desc="DejaVu Sans Bold 8.5", letter_spacing=1.6)

            # Wi-Fi icon at top
            cr.save()
            l_top = PangoCairo.create_layout(cr)
            l_top.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font 13"))
            l_top.set_markup(f"<span color='{self.c_accent}'>󰖩</span>", -1)
            ink, log = l_top.get_pixel_extents()
            cr.move_to(self.cx - ink.width / 2.0, cy_top - self.top_mark_offset - ink.height / 2.0)
            PangoCairo.show_layout(cr, l_top)
            cr.restore()

            content_x = self.x_left + 36.0
            content_w = self.W_shell - 72.0

            # 1. TOP HEADER & ACTION ROW (y = 214.0) - Pure floating, NO boxes
            cr.save()
            l_htit = PangoCairo.create_layout(cr)
            l_htit.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 12"))
            l_htit.set_markup(f"<span color='{C_BG_WIN}'>Wi-Fi Networks</span>", -1)
            cr.move_to(content_x, 212.0)
            PangoCairo.show_layout(cr, l_htit)

            # Action: Toggle Radio (ON / OFF)
            is_tg_hover = (self.hovered_item == "wifi_toggle")
            tg_text = "󰖩 ON" if self.wifi_radio_enabled else "󰖪 OFF"
            tg_col = (self.c_accent if is_tg_hover else self.c_accent) if self.wifi_radio_enabled else (self.c_accent if is_tg_hover else C_TEXT_MUT)
            l_tg = PangoCairo.create_layout(cr)
            l_tg.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 10.5"))
            l_tg.set_markup(f"<span color='{tg_col}'><b>{tg_text}</b></span>", -1)
            cr.move_to(content_x + content_w - 105.0, 213.0)
            PangoCairo.show_layout(cr, l_tg)

            # Action: Rescan
            is_sc_hover = (self.hovered_item == "wifi_rescan")
            sc_col = self.c_accent if is_sc_hover else C_BG_WIN
            l_sc = PangoCairo.create_layout(cr)
            l_sc.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 10.5"))
            l_sc.set_markup(f"<span color='{sc_col}'><b>󰑐 Scan</b></span>", -1)
            cr.move_to(content_x + content_w - 48.0, 213.0)
            PangoCairo.show_layout(cr, l_sc)
            cr.restore()

            # 2. STATUS / ACTIVE ROW (y = 238.0) - Pure floating, NO boxes
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

                # Disconnect pure text link
                is_dc_hover = (self.hovered_item == "wifi_disconnect")
                dc_col = self.c_accent if is_dc_hover else C_BG_WAYBAR
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

            # 3. CONTENT: PASSWORD PROMPT OR NETWORK LIST
            if self.wifi_password_prompt_ssid:
                # Clean Floating Password Entry Mode (NO white boxes)
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

                # Subtle Input underline / slot
                input_y = 326.0
                input_h = 34.0
                draw_rounded_rect(cr, content_x, input_y, content_w, input_h, 6.0)
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

                # Floating Action Buttons
                btn_y = 374.0

                # Connect pill button
                draw_rounded_rect(cr, content_x, btn_y, 110.0, 30.0, 6.0)
                if self.hovered_item == "wifi_pass_connect":
                    cr.set_source_rgba(*hex_to_rgba(C_ACCENT_HOVER, 1.0))
                else:
                    cr.set_source_rgba(*hex_to_rgba(self.c_accent, 0.90))
                cr.fill()
                l_btnc = PangoCairo.create_layout(cr)
                l_btnc.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 10"))
                l_btnc.set_markup(f"<span color='{C_TEXT_INV}'>Connect ↵</span>", -1)
                cr.move_to(content_x + 16.0, btn_y + 6.0)
                PangoCairo.show_layout(cr, l_btnc)

                # Cancel floating text
                is_cxl_hover = (self.hovered_item == "wifi_pass_cancel")
                cxl_col = self.c_accent if is_cxl_hover else C_BG_WIN
                l_btnx = PangoCairo.create_layout(cr)
                l_btnx.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 10"))
                l_btnx.set_markup(f"<span color='{cxl_col}'>Cancel</span>", -1)
                cr.move_to(content_x + 135.0, btn_y + 6.0)
                PangoCairo.show_layout(cr, l_btnx)

                # Helper note
                l_hint = PangoCairo.create_layout(cr)
                l_hint.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font 9"))
                l_hint.set_markup(f"<span color='{C_BG_WIN}' alpha='60%'>Press Enter to connect, Esc to return</span>", -1)
                cr.move_to(content_x, 420.0)
                PangoCairo.show_layout(cr, l_hint)
                cr.restore()

            else:
                # Network List (5 items per page) - Pure floating rows, NO white card boxes
                start_idx = self.wifi_page_idx * 5
                page_nets = self.wifi_networks[start_idx : start_idx + 5]

                if not page_nets:
                    cr.save()
                    l_empty = PangoCairo.create_layout(cr)
                    l_empty.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 11"))
                    if self.wifi_scanning:
                        msg = "󰑐 Scanning nearby networks..."
                        col = self.c_accent
                    elif not self.wifi_radio_enabled:
                        msg = "󰖪 Wi-Fi is disabled"
                        col = self.c_accent
                    else:
                        msg = "󰤯 No networks found"
                        col = self.c_accent
                    l_empty.set_markup(f"<span color='{col}'>{msg}</span>", -1)
                    ink, log = l_empty.get_pixel_extents()
                    cr.move_to(self.cx - ink.width / 2.0, 340.0)
                    PangoCairo.show_layout(cr, l_empty)
                    cr.restore()
                else:
                    for idx, net in enumerate(page_nets):
                        cr.save()
                        item_y = 262.0 + idx * 48.0
                        is_active = net.get("in_use") or (net.get("ssid") == self.wifi_ssid)
                        is_hover = (self.hovered_item == f"wifi_item_{idx}")

                        # Subtle translucent wash on hover or active (NO borders, NO boxes)
                        if is_active:
                            draw_rounded_rect(cr, content_x - 6.0, item_y - 2.0, content_w + 12.0, 44.0, 8.0)
                            cr.set_source_rgba(*hex_to_rgba(self.c_accent, 0.12))
                            cr.fill()
                        elif is_hover:
                            draw_rounded_rect(cr, content_x - 6.0, item_y - 2.0, content_w + 12.0, 44.0, 8.0)
                            cr.set_source_rgba(*hex_to_rgba(self.c_accent, 0.08))
                            cr.fill()

                        # Signal icon (Size 20, matches main page icon scale)
                        sig = net.get("signal", 0)
                        sig_icon = "󰤨" if sig >= 80 else "󰤥" if sig >= 60 else "󰤢" if sig >= 40 else "󰤟" if sig >= 20 else "󰤯"
                        ic_col = self.c_accent if (is_active or is_hover) else C_BORDER_3D
                        l_sig = PangoCairo.create_layout(cr)
                        l_sig.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font 20"))
                        l_sig.set_markup(f"<span color='{ic_col}'>{sig_icon}</span>", -1)
                        cr.move_to(content_x, item_y + 2.0)
                        PangoCairo.show_layout(cr, l_sig)

                        # SSID (Size 11.5 Bold)
                        ssid_str = net.get("ssid", "Unknown")
                        ssid_disp = (ssid_str[:17] + "…") if len(ssid_str) > 18 else ssid_str
                        l_nm = PangoCairo.create_layout(cr)
                        l_nm.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 11.5"))
                        nm_col = self.c_accent if is_active else (C_BORDER_3D if is_hover else C_BG_WIN)
                        l_nm.set_markup(f"<span color='{nm_col}'>{ssid_disp}</span>", -1)
                        cr.move_to(content_x + 36.0, item_y)
                        PangoCairo.show_layout(cr, l_nm)

                        # Sub info: signal % and security (Size 9.5)
                        sec_str = net.get("security", "")
                        sec_disp = sec_str.replace("WPA1", "").replace("WPA2", "WPA2").strip() if sec_str and sec_str != "--" else "Open"
                        l_inf = PangoCairo.create_layout(cr)
                        l_inf.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font 9.5"))
                        l_inf.set_markup(f"<span color='{C_BG_WIN}' alpha='70%'>{sig}%  •  {sec_disp}</span>", -1)
                        cr.move_to(content_x + 36.0, item_y + 21.0)
                        PangoCairo.show_layout(cr, l_inf)

                        # Badges on right side
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

                        # Lock icon (Security) - only show for unsaved, non-active secured networks
                        if not is_active and not net.get("saved") and sec_str and sec_str != "--":
                            l_lk = PangoCairo.create_layout(cr)
                            l_lk.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font 12"))
                            l_lk.set_markup(f"<span color='{self.c_accent}' alpha='85%'>󰌾</span>", -1)
                            cr.move_to(content_x + content_w - 18.0, item_y + 19.0)
                            PangoCairo.show_layout(cr, l_lk)

                        cr.restore()

                # Floating Pagination Row (NO boxes)
                if len(self.wifi_networks) > 5:
                    cr.save()
                    total_pages = max(1, (len(self.wifi_networks) + 4) // 5)
                    py_y = 514.0

                    # Prev
                    is_pv_hover = (self.hovered_item == "wifi_prev")
                    pv_col = self.c_accent if is_pv_hover else (C_BG_WIN if self.wifi_page_idx > 0 else C_TEXT_MUT)
                    l_prv = PangoCairo.create_layout(cr)
                    l_prv.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 10.5"))
                    l_prv.set_markup(f"<span color='{pv_col}'><b>◀ Prev</b></span>", -1)
                    cr.move_to(content_x + 4.0, py_y)
                    PangoCairo.show_layout(cr, l_prv)

                    # Page indicator
                    l_pg = PangoCairo.create_layout(cr)
                    l_pg.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 10"))
                    l_pg.set_markup(f"<span color='{C_BG_WIN}' alpha='75%'><b>{self.wifi_page_idx + 1} / {total_pages}</b></span>", -1)
                    ink, log = l_pg.get_pixel_extents()
                    cr.move_to(self.cx - ink.width / 2.0, py_y)
                    PangoCairo.show_layout(cr, l_pg)

                    # Next
                    is_nx_hover = (self.hovered_item == "wifi_next")
                    nx_col = self.c_accent if is_nx_hover else (C_BG_WIN if self.wifi_page_idx < total_pages - 1 else C_TEXT_MUT)
                    l_nxt = PangoCairo.create_layout(cr)
                    l_nxt.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 10.5"))
                    l_nxt.set_markup(f"<span color='{nx_col}'><b>Next ▶</b></span>", -1)
                    cr.move_to(content_x + content_w - 56.0, py_y)
                    PangoCairo.show_layout(cr, l_nxt)
                    cr.restore()

            # Bottom Navigation: Bow mark to return to Controls
            btn_y = socket_well_y
            cr.save()
            draw_bow_mark(cr, self.cx, btn_y, size=34.0, color=self.c_accent_rgb)
            cr.restore()


    def on_draw(self, widget, cr):
        # 0. Clear canvas surface to transparent
        clear_surface(cr)
        cr.set_antialias(cairo.ANTIALIAS_DEFAULT)

        cr.save()
        sx = self.W_canvas / self.base_w
        sy = self.H_canvas / self.base_h
        cr.scale(sx, sy)

        geo = self.get_dynamic_coords(self.anim_progress)

        if self.anim_state in ("opening", "closing", "closed"):
            # 1. Screen aperture (always drawn so center eye has cyan hologram glass when closed)
            cr.save()
            cr.new_sub_path()
            cr.rectangle(self.x_left, geo["y_edge_top"], self.W_shell, geo["y_edge_bot"] - geo["y_edge_top"])
            cr.arc(self.cx, geo["cy_top"], self.r_inner, geo["ang_inner_top_end"], geo["ang_inner_top_start"])
            cr.close_path()
            cr.arc(self.cx, geo["cy_bot"], self.r_inner, geo["ang_inner_bot_start"], geo["ang_inner_bot_end"])
            cr.close_path()
            cr.clip()

            y_grad_top = geo["cy_top"] - self.r_inner
            y_grad_bot = geo["cy_bot"] + self.r_inner
            scr_pat = cairo.LinearGradient(0, y_grad_top, 0, y_grad_bot)
            scr_pat.add_color_stop_rgba(0.0, self.c_holo_top[0], self.c_holo_top[1], self.c_holo_top[2], self.holo_alpha_top)
            scr_pat.add_color_stop_rgba(0.5, self.c_holo_mid[0], self.c_holo_mid[1], self.c_holo_mid[2], self.holo_alpha_mid)
            scr_pat.add_color_stop_rgba(1.0, self.c_holo_bot[0], self.c_holo_bot[1], self.c_holo_bot[2], self.holo_alpha_bot)
            cr.set_source(scr_pat)
            cr.paint()

            # Content revealed
            if self.anim_progress > 0.25:
                if not self._cached_content_surf or self._cached_content_page != self.current_page:
                    self._bake_content()
                alpha = min(1.0, max(0.0, (self.anim_progress - 0.25) / 0.75))
                cr.set_source_surface(self._cached_content_surf, 0, 0)
                cr.paint_with_alpha(alpha)
            cr.restore()

            # 2. Baked top casing
            if not self._cached_top_casing:
                self._bake_casings()
            cr.save()
            cr.set_source_surface(self._cached_top_casing, 0, geo["top_casing_y"])
            cr.paint()
            cr.restore()

            # 3. Baked bottom casing
            if not self._cached_bot_casing:
                self._bake_casings()
            cr.save()
            cr.set_source_surface(self._cached_bot_casing, 0, geo["bot_casing_y"])
            cr.paint()
            cr.restore()

            cr.restore()
            return False

        # --- LIVE INTERACTIVE OPEN STATE (anim_state == "open", p == 1.0) ---
        cr.save()
        cr.new_sub_path()
        cr.rectangle(self.x_left, geo["y_edge_top"], self.W_shell, geo["y_edge_bot"] - geo["y_edge_top"])
        cr.arc(self.cx, geo["cy_top"], self.r_inner, geo["ang_inner_top_end"], geo["ang_inner_top_start"])
        cr.close_path()
        cr.arc(self.cx, geo["cy_bot"], self.r_inner, geo["ang_inner_bot_start"], geo["ang_inner_bot_end"])
        cr.close_path()
        cr.clip()

        y_grad_top = geo["cy_top"] - self.r_inner
        y_grad_bot = geo["cy_bot"] + self.r_inner
        scr_pat = cairo.LinearGradient(0, y_grad_top, 0, y_grad_bot)
        scr_pat.add_color_stop_rgba(0.0, self.c_holo_top[0], self.c_holo_top[1], self.c_holo_top[2], self.holo_alpha_top)
        scr_pat.add_color_stop_rgba(0.5, self.c_holo_mid[0], self.c_holo_mid[1], self.c_holo_mid[2], self.holo_alpha_mid)
        scr_pat.add_color_stop_rgba(1.0, self.c_holo_bot[0], self.c_holo_bot[1], self.c_holo_bot[2], self.holo_alpha_bot)
        cr.set_source(scr_pat)
        cr.paint()

        self._draw_content_elements(cr, cy_top=geo["cy_top"])
        cr.restore()

        # Baked Casings at p=1.0 (top_casing_y=0, bot_casing_y=0)
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

def main():
    def sig_handler(signum, frame):
        GLib.idle_add(Gtk.main_quit)

    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    my_pid = os.getpid()
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(my_pid))
    except Exception:
        pass

    app = PokedexControlCenter()
    if "--open" in sys.argv:
        app.anim_state = "open"
        app.anim_progress = 1.0
    if "--page" in sys.argv:
        try:
            p_idx = sys.argv.index("--page")
            target = sys.argv[p_idx + 1]
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
