#!/usr/bin/env python3
# control_center.py — Kalos Pokédex Control Center & Notifications Panel

import os
import sys
import time
import json
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
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from services.audio import AudioService
from services.brightness import BrightnessService
from services.bluetooth import BluetoothService
from services.power import PowerService

PID_FILE = "/tmp/control_center.pid"
CACHE_FILE = os.path.expanduser("~/.cache/notifications.json")

# ==============================================================================
# 1. PURE CAIRO GEOMETRIC PATHS & HELPERS
# ==============================================================================
def clip_device_bounds(cr, x, y, w, h, r):
    cr.new_sub_path()
    cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    cr.arc(x + w - r, y + r, r, 1.5 * math.pi, 2 * math.pi)
    cr.arc(x + w - r, y + h - r, r, 0, 0.5 * math.pi)
    cr.arc(x + r, y + h - r, r, 0.5 * math.pi, math.pi)
    cr.close_path()

def draw_anime_grooves(cr, cx, cy, grooves, a1, a2):
    for (r_in, r_out) in grooves:
        cr.save()
        cr.new_sub_path()
        cr.arc(cx, cy, r_out, a1, a2)
        cr.arc_negative(cx, cy, r_in, a2, a1)
        cr.close_path()
        cr.set_source_rgba(0x14/255.0, 0x02/255.0, 0x06/255.0, 0.62); cr.fill()

        cr.arc(cx, cy, r_out, a1, a2)
        cr.set_source_rgba(0x10/255.0, 0x02/255.0, 0x05/255.0, 0.90)
        cr.set_line_width(1.1); cr.stroke()

        cr.arc(cx, cy, r_in, a1, a2)
        cr.set_source_rgba(0x18/255.0, 0x03/255.0, 0x07/255.0, 0.85)
        cr.set_line_width(1.0); cr.stroke()

        cr.arc(cx, cy, r_out + 0.8, a1, a2)
        cr.set_source_rgba(1.0, 0.65, 0.75, 0.25)
        cr.set_line_width(0.7); cr.stroke()
        cr.restore()

def create_top_red_casing_path(cr, x_left, x_right, y_dark_top, cx, cy_top, r_dark, ang_dark_top_start, ang_dark_top_end, x_dark_cut, device_r, notch_d=2.0, trans=1.8):
    y_tl1_t = 48.0;  y_tl1_b = 52.0
    y_tl2_t = 96.0;  y_tl2_b = 100.0
    
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
    
    cr.line_to(x_left, device_r)
    cr.arc(x_left + device_r, device_r, device_r, math.pi, 1.5 * math.pi)
    cr.line_to(x_right - device_r, 0)
    cr.arc(x_right - device_r, device_r, device_r, 1.5 * math.pi, 2 * math.pi)
    
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
# 2. PROPORTIONALLY KERNED CURVED TEXT (Fixes overlapping/colliding letters)
# ==============================================================================
def draw_curved_kerned(cr, text, cx, cy_top, r_text=60.0, font_desc="DejaVu Sans Bold 10", letter_spacing=3.2, color=(0x20/255.0, 0x10/255.0, 0x11/255.0)):
    widths = []
    for ch in text:
        l = PangoCairo.create_layout(cr)
        l.set_font_description(Pango.FontDescription(font_desc))
        l.set_text(ch, -1)
        ink, log = l.get_pixel_extents()
        w = log.width if ch != ' ' else 8.5
        widths.append(w + letter_spacing)
    
    total_arc = sum(widths)
    total_ang = total_arc / r_text
    start_ang = -math.pi / 2.0 - total_ang / 2.0
    
    curr_ang = start_ang
    for i, ch in enumerate(text):
        char_w = widths[i]
        ang = curr_ang + (char_w / 2.0) / r_text
        curr_ang += char_w / r_text
        
        x = cx + r_text * math.cos(ang)
        y = cy_top + r_text * math.sin(ang)
        cr.save()
        cr.translate(x, y)
        cr.rotate(ang + math.pi / 2.0)
        l = PangoCairo.create_layout(cr)
        l.set_font_description(Pango.FontDescription(font_desc))
        l.set_text(ch, -1)
        ink, log = l.get_pixel_extents()
        cr.move_to(-log.width / 2.0, -log.height / 2.0)
        cr.set_source_rgb(*color)
        PangoCairo.show_layout(cr, l)
        cr.restore()

def draw_serena_flower(ctx, cx, cy, r_petal=9.0, r_center=3.8, color=(1.0, 0.165, 0.333)):
    cy_opt = cy + 0.8
    for i in range(5):
        ang = i * (2 * math.pi / 5.0) - math.pi / 2.0
        px = cx + (r_petal * 0.95) * math.cos(ang)
        py = cy_opt + (r_petal * 0.95) * math.sin(ang)
        ctx.arc(px, py, r_petal * 0.65, 0, 2 * math.pi)
        ctx.set_source_rgba(color[0], color[1], color[2], 0.95); ctx.fill()
    for i in range(5):
        ang = i * (2 * math.pi / 5.0) - math.pi / 2.0
        px = cx + (r_petal * 0.95) * math.cos(ang)
        py = cy_opt + (r_petal * 0.95) * math.sin(ang)
        ctx.arc(px, py, r_petal * 0.65, 0, 2 * math.pi)
        ctx.set_source_rgba(0x20/255.0, 0x10/255.0, 0x11/255.0, 0.40); ctx.set_line_width(0.9); ctx.stroke()
    ctx.arc(cx, cy_opt, r_center, 0, 2 * math.pi)
    ctx.set_source_rgb(1.0, 0.94, 0.96); ctx.fill_preserve()
    ctx.set_source_rgba(0x20/255.0, 0x10/255.0, 0x11/255.0, 0.50); ctx.set_line_width(0.8); ctx.stroke()

def draw_bell_icon(ctx, cx, cy, font_size=20, color="#FF2A55"):
    l = PangoCairo.create_layout(ctx)
    l.set_font_description(Pango.FontDescription(f"JetBrains Mono Nerd Font Bold {font_size}"))
    l.set_markup(f"<span color='{color}'>󰂚</span>", -1)
    ink, log = l.get_pixel_extents()
    ctx.move_to(cx - ink.x - ink.width / 2.0, cy - ink.y - ink.height / 2.0)
    PangoCairo.show_layout(ctx, l)

def draw_pokeball_dual_slider(cr, cx, cy, R=64.0, thickness=12.0, vol_val=0.35, bri_val=0.60, knob_style="round_knob", icon_color="#FF2A55", accent_rgb=(0xFF/255.0, 0x2A/255.0, 0x55/255.0), dark_color=(0x20/255.0, 0x10/255.0, 0x11/255.0), pwr_bg=(0x20/255.0, 0x10/255.0, 0x11/255.0)):
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
    cr.set_source_rgb(*dark_color) # Token bg_window
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
    cr.set_source_rgb(*dark_color) # Token bg_window
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

    # 4. CENTER POWER BUTTON (0.0px Offset, pure geometric vector)
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

    # 5. ICONS NESTLED INSIDE THE LEFT CAVITY - PHƯƠNG ÁN B
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
        return "#FF2A55", "󰆍"
    return "#FF2A55", "󰒓"

# ==============================================================================
# 3. POKÉDEX GTK APPLICATION WITH SLIDING ANIMATION & CLOSED STATE
# ==============================================================================
class PokedexControlCenter(Gtk.Window):
    def __init__(self):
        super().__init__(title="Pokédex Control Center")
        self.set_name("control-center-window")
        self.set_decorated(False)
        self.set_resizable(False)

        # Logical canvas dimensions
        self.W_canvas = 388.0
        self.H_canvas = 780.0
        self.set_default_size(int(self.W_canvas), int(self.H_canvas))
        self.set_size_request(int(self.W_canvas), int(self.H_canvas))

        self.current_page = "controls"
        self.dragging_slider = None

        # ANIMATION & STATE:
        # Starts in CLOSED state per user requirement (or open if --open passed)
        if "--open" in sys.argv:
            self.anim_state = "open"
            self.anim_progress = 1.0
        else:
            self.anim_state = "closed"
            self.anim_progress = 0.0
        self.anim_start_time = 0.0
        self.anim_duration = 0.32    # 320ms snappy anime sliding
        self.anim_timer_id = None
        self.quit_after_close = False

        # State cache (Instant non-blocking defaults for 0.01s launch)
        self.vol_val = 0.35
        self.bri_val = 0.60
        self.bt_enabled = False
        self.bt_device = ""
        self.power_mode = "Performance"
        self.ime_text = "Vietnamese"
        self.wifi_text, self.wifi_ssid = "Connected", ""
        self.notifications = self.load_notifications()

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
        self.cut_y = 11.0
        self.cuff_ext = 2.5
        self.notch_d = 2.0
        self.trans = 1.8

        # Layout anchors for perfect geometric balance:
        self.cy_pokeball = 468.0
        self.socket_well_y = 636.5
        self.top_mark_offset = 32.0

        # Anime Pokémon Palette (Vibrant, high-tech, authentic to anime)
        self.c_casing_l = (0xDC/255.0, 0x1A/255.0, 0x36/255.0)
        self.c_casing_m = (0xF0/255.0, 0x2D/255.0, 0x4C/255.0)
        self.c_casing_r = (0xDC/255.0, 0x1A/255.0, 0x36/255.0)
        self.c_casing_border = (0x68/255.0, 0x0A/255.0, 0x16/255.0, 0.95)

        # Pokéball Band & Chassis
        self.c_band_stop0 = (0x1C/255.0, 0x1E/255.0, 0x22/255.0)
        self.c_band_stop1 = (0x28/255.0, 0x2B/255.0, 0x32/255.0)
        self.c_band_stop2 = (0x1C/255.0, 0x1E/255.0, 0x22/255.0)
        self.c_band_stroke = (0x0E/255.0, 0x10/255.0, 0x13/255.0, 0.95)
        self.c_slider_dark = (0x20/255.0, 0x21/255.0, 0x26/255.0)
        self.c_pwr_bg = (0x20/255.0, 0x21/255.0, 0x26/255.0)
        self.c_chassis = (0xD6/255.0, 0xDC/255.0, 0xE6/255.0)
        self.c_flange = (0x18/255.0, 0x1A/255.0, 0x1E/255.0)

        # Accent & Kalos Cyan Hologram roles (Vibrant Luminous Cyan - 100% Solid & Completely Uniform!)
        self.c_accent = "#E5223E"
        self.c_accent_rgb = (0xE5/255.0, 0x22/255.0, 0x3E/255.0)
        self.c_holo_top = (0xC8/255.0, 0xF4/255.0, 0xFD/255.0)
        self.c_holo_mid = (0xBA/255.0, 0xEE/255.0, 0xFC/255.0)
        self.c_holo_bot = (0xAA/255.0, 0xE7/255.0, 0xFA/255.0)

        # LayerShell setup
        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_namespace(self, "control-center")
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, False)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, False)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 44)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, 14)
            GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)
        else:
            self.set_position(Gtk.WindowPosition.NONE)
            self.move(1600 - int(self.W_canvas) - 14, 44)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        self.set_app_paintable(True)

        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.KEY_PRESS_MASK
        )

        self.connect("draw", self.on_draw)
        self.connect("button-press-event", self.on_button_press)
        self.connect("button-release-event", self.on_button_release)
        self.connect("motion-notify-event", self.on_motion_notify)
        self.connect("key-press-event", self.on_key_press)

        # Signal handling for Super+N toggling
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, self.on_sigusr1)

        GLib.timeout_add(1500, self.refresh_status_tick)

    def on_sigusr1(self, *args):
        if self.anim_state in ("open", "opening"):
            self.start_close_animation(quit_after=True)
        else:
            self.close_and_quit()
        return GLib.SOURCE_CONTINUE

    def start_open_animation(self):
        if self.anim_state in ("open", "opening"):
            return
        self.anim_state = "opening"
        self.anim_start_time = time.time()
        self.anim_duration = 0.32
        if not self.anim_timer_id:
            self.anim_timer_id = GLib.timeout_add(16, self.on_anim_step)

    def start_close_animation(self, quit_after=False):
        if self.anim_state in ("closed", "closing"):
            if quit_after:
                self.close_and_quit()
            return
        self.anim_state = "closing"
        self.anim_start_time = time.time()
        self.anim_duration = 0.28
        self.quit_after_close = quit_after
        if not self.anim_timer_id:
            self.anim_timer_id = GLib.timeout_add(16, self.on_anim_step)

    def on_anim_step(self):
        now = time.time()
        elapsed = now - self.anim_start_time
        t = min(1.0, elapsed / self.anim_duration)

        if self.anim_state == "opening":
            # Cubic ease-out: snappy opening bursting out then locking smoothly
            e = 1.0 - math.pow(1.0 - t, 3)
            self.anim_progress = e
            if t >= 1.0:
                self.anim_progress = 1.0
                self.anim_state = "open"
                self.anim_timer_id = None
                self.queue_draw()
                return False
        elif self.anim_state == "closing":
            # Smoothstep ease-in-out
            e = t * t * (3.0 - 2.0 * t)
            self.anim_progress = max(0.0, 1.0 - e)
            if t >= 1.0:
                self.anim_progress = 0.0
                self.anim_state = "closed"
                self.anim_timer_id = None
                if getattr(self, "quit_after_close", False):
                    self.close_and_quit()
                    return False
                self.queue_draw()
                return False

        self.queue_draw()
        return True

    def close_and_quit(self):
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
        Gtk.main_quit()

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            if self.anim_state == "open":
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
        self.current_page = "notifications" if self.current_page == "controls" else "controls"
        self.queue_draw()

    def get_ime_status(self):
        try:
            out = subprocess.check_output(["fcitx5-remote", "-n"], stderr=subprocess.DEVNULL).decode().strip()
            if "unikey" in out.lower() or "bamboo" in out.lower():
                return "Vietnamese"
            return "English"
        except Exception:
            return "English"

    def get_wifi_status(self):
        try:
            out = subprocess.check_output(
                ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "dev"], 
                stderr=subprocess.DEVNULL,
                timeout=0.3
            ).decode()
            for line in out.splitlines():
                parts = line.split(":")
                if len(parts) >= 4 and parts[1] == "wifi" and parts[2] == "connected":
                    ssid = parts[3].strip()
                    return ("Connected", ssid if ssid else "Connected")
            return ("Disconnected", "")
        except Exception:
            return ("Disconnected", "")

    def async_refresh_status(self):
        try:
            vol = AudioService.get_volume() / 100.0
            bri = BrightnessService.get_brightness() / 100.0
            bt_on = BluetoothService.is_enabled()
            bt_dev = BluetoothService.get_connected_device_name()
            pwr = PowerService.get_power_mode()
            ime = self.get_ime_status()
            wifi_txt, wifi_ssid = self.get_wifi_status()

            def apply():
                self.vol_val = vol
                self.bri_val = bri
                self.bt_enabled = bt_on
                self.bt_device = bt_dev
                self.power_mode = pwr
                self.ime_text = ime
                self.wifi_text = wifi_txt
                self.wifi_ssid = wifi_ssid
                if self.anim_state == "open":
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
        x, y = event.x, event.y

        # 1. Closed state interaction:
        if self.anim_state == "closed":
            # The closed device occupies y in [190, 590], x in [x_left, x_right]
            if 180.0 <= y <= 600.0 and self.x_left <= x <= self.x_right:
                # Clicking the closed Pokédex shell triggers the opening slide!
                self.start_open_animation()
                return True
            else:
                # Clicking outside closed Pokédex dismisses it
                self.close_and_quit()
                return True

        # 2. While in motion, absorb events to avoid glitching
        if self.anim_state in ("opening", "closing"):
            return True

        # 3. Open state interaction:
        # Close if clicking outside the device body entirely
        if y < 10.0 or y > self.H_canvas - 10.0:
            self.start_close_animation(quit_after=True)
            return True

        # Bottom Navigation Button (Floating Bell/Flower at cx, socket_well_y)
        dist_nav = math.sqrt((x - self.cx)**2 + (y - self.socket_well_y)**2)
        if dist_nav <= 28.0:
            self.toggle_page()
            return True

        # Top Mark (Flower / Bell at cx, cy_top - top_mark_offset)
        dist_top = math.sqrt((x - self.cx)**2 + (y - (190.0 - self.top_mark_offset))**2)
        if dist_top <= 24.0:
            self.toggle_page()
            return True

        # Clicking on top red casing header or bottom casing footer triggers slide-closed
        if y < 170.0 and abs(x - self.cx) > 40.0:
            self.start_close_animation()
            return True
        if y > 610.0 and dist_nav > 30.0:
            self.start_close_animation()
            return True

        if self.current_page == "controls":
            grid_x = self.x_left + 36.0
            grid_y = 224.0
            col_w = (self.W_shell - 72.0 - 20.0) / 2.0
            row_h = 44.0
            gap_y = 24.0

            # Tile (0,0) - Input
            if grid_x <= x <= grid_x + col_w and grid_y <= y <= grid_y + row_h:
                toggle_sh = os.path.join(SCRIPTS_DIR, "toggle_vietnamese.sh")
                if os.path.exists(toggle_sh):
                    subprocess.Popen([toggle_sh])
                self.ime_text = "Vietnamese" if self.ime_text == "English" else "English"
                self.queue_draw()
                return True

            # Tile (1,0) - Wi-Fi
            c1_x = grid_x + col_w + 20.0
            if c1_x <= x <= c1_x + col_w and grid_y <= y <= grid_y + row_h:
                wifi_sh = os.path.join(SCRIPTS_DIR, "rofi-wifi-menu.sh")
                if os.path.exists(wifi_sh):
                    subprocess.Popen([wifi_sh])
                elif shutil.which("nm-connection-editor"):
                    subprocess.Popen(["nm-connection-editor"])
                return True

            # Tile (0,1) - Bluetooth
            r1_y = grid_y + row_h + gap_y
            if grid_x <= x <= grid_x + col_w and r1_y <= y <= r1_y + row_h:
                self.bt_enabled = BluetoothService.toggle_power()
                self.queue_draw()
                return True

            # Tile (1,1) - Power Mode
            if c1_x <= x <= c1_x + col_w and r1_y <= y <= r1_y + row_h:
                order = ["powersave", "balanced", "performance"]
                curr = self.power_mode.lower() if self.power_mode else "balanced"
                next_idx = (order.index(curr) + 1) % len(order) if curr in order else 0
                next_mode = order[next_idx]
                PowerService.set_power_mode(next_mode)
                self.power_mode = next_mode
                self.queue_draw()
                return True

            # Pokéball Dual Slider
            cy_poke = self.cy_pokeball
            dx = x - self.cx
            dy = y - cy_poke
            dist_poke = math.sqrt(dx**2 + dy**2)

            # Center Power Button
            if dist_poke <= 22.0:
                wlogout_sh = os.path.join(SCRIPTS_DIR, "Wlogout.sh")
                if os.path.exists(wlogout_sh):
                    subprocess.Popen([wlogout_sh])
                elif shutil.which("wlogout"):
                    subprocess.Popen(["wlogout"])
                self.close_and_quit()
                return True

            # Circular Arcs (Radius ~ 64px, thickness 12px -> zone 46px to 82px)
            if 46.0 <= dist_poke <= 82.0:
                if dy < 0:
                    self.dragging_slider = "volume"
                    self.update_slider_from_coords(x, y, "volume")
                else:
                    self.dragging_slider = "brightness"
                    self.update_slider_from_coords(x, y, "brightness")
                return True

        elif self.current_page == "notifications":
            # "Clear all notifications" button at y = 490..530
            if 480.0 <= y <= 530.0 and abs(x - self.cx) <= 100.0:
                if os.path.exists(CACHE_FILE):
                    try:
                        with open(CACHE_FILE, "w", encoding="utf-8") as f:
                            json.dump([], f)
                    except Exception:
                        pass
                self.notifications = []
                self.queue_draw()
                return True

        return False

    def on_button_release(self, widget, event):
        self.dragging_slider = None
        return False

    def on_motion_notify(self, widget, event):
        if self.anim_state == "open" and self.dragging_slider:
            self.update_slider_from_coords(event.x, event.y, self.dragging_slider)
            return True
        return False

    def update_slider_from_coords(self, x, y, slider_type):
        cy_poke = self.cy_pokeball
        dx = x - self.cx
        dy = y - cy_poke
        ang = math.atan2(dy, dx)
        if ang < 0:
            ang += 2 * math.pi

        gap_ang = math.radians(16.0)

        if slider_type == "volume":
            ang_vol_start = math.pi + gap_ang
            ang_vol_end = 2 * math.pi - gap_ang
            ang_vol_span = ang_vol_end - ang_vol_start

            if ang < ang_vol_start:
                if ang < math.pi * 0.5:
                    val = 1.0
                else:
                    val = 0.0
            elif ang > ang_vol_end:
                val = 1.0
            else:
                val = (ang - ang_vol_start) / ang_vol_span

            self.vol_val = max(0.0, min(1.0, val))
            AudioService.set_volume(int(self.vol_val * 100.0))
            self.queue_draw()

        elif slider_type == "brightness":
            ang_bri_start = math.pi - gap_ang
            ang_bri_end = gap_ang
            ang_bri_span = (math.pi - 2 * gap_ang)

            if ang > ang_bri_start:
                val = 0.0
            elif ang < ang_bri_end:
                val = 1.0
            else:
                val = (ang_bri_start - ang) / ang_bri_span

            self.bri_val = max(0.0, min(1.0, val))
            BrightnessService.set_brightness(int(self.bri_val * 100.0))
            self.queue_draw()

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
    def on_draw(self, widget, cr):
        # 0. Clear canvas surface to 100% transparent
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        cr.set_antialias(cairo.ANTIALIAS_BEST)

        geo = self.get_dynamic_coords(self.anim_progress)

        # 1. CYAN HOLOGRAM SCREEN: 100% SOLID MATTE
        cr.save()
        cr.new_sub_path()
        cr.rectangle(self.x_left, geo["y_edge_top"], self.W_shell, geo["y_edge_bot"] - geo["y_edge_top"])
        cr.arc(self.cx, geo["cy_top"], self.r_inner, geo["ang_inner_top_end"], geo["ang_inner_top_start"])
        cr.close_path()
        cr.arc(self.cx, geo["cy_bot"], self.r_inner, geo["ang_inner_bot_start"], geo["ang_inner_bot_end"])
        cr.close_path()
        cr.clip()

        # 1. CYAN HOLOGRAM SCREEN: Luminous Vibrant Cyan (100% Solid - Bright, crystal clear!)
        y_grad_top = geo["cy_top"] - self.r_inner
        y_grad_bot = geo["cy_bot"] + self.r_inner
        scr_pat = cairo.LinearGradient(0, y_grad_top, 0, y_grad_bot)
        scr_pat.add_color_stop_rgb(0.0, *self.c_holo_top)
        scr_pat.add_color_stop_rgb(0.5, *self.c_holo_mid)
        scr_pat.add_color_stop_rgb(1.0, *self.c_holo_bot)
        cr.set_source(scr_pat)
        cr.paint()
        cr.restore()

        # 1B. CONTENT REVEALED INSIDE SCREEN (Fades in smoothly during opening)
        if self.anim_progress > 0.05:
            alpha = min(1.0, max(0.0, (self.anim_progress - 0.25) / 0.75))
            cr.save()
            # Clip strictly inside expanding screen area
            cr.new_sub_path()
            cr.rectangle(self.x_left, geo["y_edge_top"], self.W_shell, geo["y_edge_bot"] - geo["y_edge_top"])
            cr.arc(self.cx, geo["cy_top"], self.r_inner, geo["ang_inner_top_end"], geo["ang_inner_top_start"])
            cr.close_path()
            cr.arc(self.cx, geo["cy_bot"], self.r_inner, geo["ang_inner_bot_start"], geo["ang_inner_bot_end"])
            cr.close_path()
            cr.clip()

            cr.push_group()

            socket_well_y = self.socket_well_y

            if self.current_page == "controls":
                # KERNED CURVED HEADER: No overlapping letters!
                draw_curved_kerned(cr, "CONTROL CENTER", self.cx, geo["cy_top"], r_text=60.0, font_desc="DejaVu Sans Bold 10", letter_spacing=3.2)

                # Flower icon at the top
                cr.save()
                draw_serena_flower(cr, self.cx, geo["cy_top"] - self.top_mark_offset, r_petal=5.5, r_center=2.4, color=self.c_accent_rgb)
                cr.restore()

                # Floating Quick Tiles
                grid_x = self.x_left + 36.0
                grid_y = 224.0
                col_w = (self.W_shell - 72.0 - 20.0) / 2.0
                row_h = 44.0
                gap_y = 24.0

                bt_val = self.bt_device if (self.bt_enabled and self.bt_device) else ("Enabled" if self.bt_enabled else "Disabled")
                tiles = [
                    ("󰌌", self.c_accent, "Input", self.ime_text, grid_x, grid_y),
                    ("󰤨", self.c_accent, "Wi-Fi", self.wifi_text, grid_x + col_w + 20.0, grid_y),
                    ("󰂯", self.c_accent, "Bluetooth", bt_val, grid_x, grid_y + row_h + gap_y),
                    ("󰓅", self.c_accent, "Power Mode", self.power_mode.capitalize() if self.power_mode else "Balanced", grid_x + col_w + 20.0, grid_y + row_h + gap_y),
                ]

                for icon, ic_col, name, val, c_x, c_y in tiles:
                    cr.save()
                    l_ic = PangoCairo.create_layout(cr)
                    l_ic.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font 20"))
                    l_ic.set_markup(f"<span color='{ic_col}'>{icon}</span>", -1)
                    cr.move_to(c_x, c_y + 4.0)
                    PangoCairo.show_layout(cr, l_ic)

                    txt_x = c_x + 32.0
                    l_txt = PangoCairo.create_layout(cr)
                    l_txt.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 10"))
                    l_txt.set_markup(f"<span color='#223344'>{name}</span>", -1)
                    cr.move_to(txt_x, c_y + 2.0)
                    PangoCairo.show_layout(cr, l_txt)

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
                # KERNED CURVED HEADER: No overlapping letters!
                draw_curved_kerned(cr, "NOTIFICATIONS", self.cx, geo["cy_top"], r_text=60.0, font_desc="DejaVu Sans Bold 10", letter_spacing=3.2)

                # Bell icon at top of Notifications
                cr.save()
                draw_bell_icon(cr, self.cx, geo["cy_top"] - self.top_mark_offset, font_size=11, color=self.c_accent)
                cr.restore()

                # Notification stream
                grid_x = self.x_left + 36.0
                grid_y = 216.0
                row_w = self.W_shell - 72.0

                notifs = self.notifications
                if not notifs:
                    notifs = [
                        ("󰙯", "#5865F2", "Discord", "5m ago", "Serena", "Hey! The anime showcase is starting in..."),
                        ("󰈹", "#FF7139", "Firefox", "24m ago", "Download Completed", "hyprland-kalos-assets-v2.tar.gz (14.2 MB)"),
                        ("󰓇", "#1ED760", "Spotify", "1h ago", "Now Playing", "Aim to Be a Pokémon Master - 2024 Remaster"),
                        ("󰒓", self.c_accent, "System", "2h ago", "Package Updates", "3 packages ready to upgrade (pacman -Syu)"),
                    ]

                curr_y = grid_y
                for item in notifs[:4]:
                    if isinstance(item, tuple):
                        icon, icon_col, app, time_str, title, body = item
                    else:
                        app = item.get("app_name", "System")
                        time_str = format_relative_time(item.get("timestamp"))
                        title = item.get("summary", "")
                        body = item.get("body", "")
                        icon_col, icon = get_badge_info(app)

                    cr.save()
                    l_ic = PangoCairo.create_layout(cr)
                    l_ic.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font 16"))
                    l_ic.set_markup(f"<span color='{icon_col}'>{icon}</span>", -1)
                    cr.move_to(grid_x, curr_y + 2.0)
                    PangoCairo.show_layout(cr, l_ic)

                    txt_x = grid_x + 28.0
                    l_app = PangoCairo.create_layout(cr)
                    l_app.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 10"))
                    l_app.set_markup(f"<span color='#201011'>{app}</span>  <span color='#201011' alpha='50%'>• {time_str}</span>", -1)
                    cr.move_to(txt_x, curr_y)
                    PangoCairo.show_layout(cr, l_app)

                    l_tit = PangoCairo.create_layout(cr)
                    l_tit.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 9.5"))
                    l_tit.set_markup(f"<span color='{self.c_accent}'>{title}</span>", -1)
                    cr.move_to(txt_x, curr_y + 16.0)
                    PangoCairo.show_layout(cr, l_tit)

                    l_bod = PangoCairo.create_layout(cr)
                    l_bod.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font 8.5"))
                    l_bod.set_markup(f"<span color='#201011' alpha='75%'>{body}</span>", -1)
                    cr.move_to(txt_x, curr_y + 30.0)
                    PangoCairo.show_layout(cr, l_bod)
                    cr.restore()

                    curr_y += 50.0

                # "Clear all notifications" button
                cr.save()
                l_clr = PangoCairo.create_layout(cr)
                l_clr.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font Bold 10.5"))
                l_clr.set_markup(f"<span color='{self.c_accent}'>󰆴 Clear all notifications</span>", -1)
                ink, log = l_clr.get_pixel_extents()
                cr.move_to(self.cx - ink.x - ink.width / 2.0, 508.0)
                PangoCairo.show_layout(cr, l_clr)
                cr.restore()

                # Bottom Navigation: Flower on Notifications
                btn_y = socket_well_y
                cr.save()
                draw_serena_flower(cr, self.cx, btn_y, r_petal=9.0, r_center=3.8)
                cr.restore()

            cr.pop_group_to_source()
            cr.paint_with_alpha(alpha)
            cr.restore()

        # 2. TOP RED CASING (Translates smoothly with expansion)
        cr.save()
        cr.translate(0, geo["top_casing_y"])

        # 2A. Red anime satin fill
        create_top_red_casing_path(cr, self.x_left, self.x_right, 170.0, self.cx, 190.0, self.r_dark, geo["ang_dark_top_start"], geo["ang_dark_top_end"], geo["x_dark_cut"], self.device_r, notch_d=self.notch_d, trans=self.trans)
        red_pat = cairo.LinearGradient(self.x_left, 0, self.x_right, 0)
        red_pat.add_color_stop_rgb(0, *self.c_casing_l)
        red_pat.add_color_stop_rgb(0.5, *self.c_casing_m)
        red_pat.add_color_stop_rgb(1, *self.c_casing_r)
        cr.set_source(red_pat); cr.fill()

        # 2B. Anime concentric grooves
        draw_anime_grooves(cr, self.x_left, 0, self.grooves, 0, 0.5 * math.pi)
        draw_anime_grooves(cr, self.x_right, 0, self.grooves, 0.5 * math.pi, math.pi)

        # 2C. Stroke casing outline
        create_top_red_casing_path(cr, self.x_left, self.x_right, 170.0, self.cx, 190.0, self.r_dark, geo["ang_dark_top_start"], geo["ang_dark_top_end"], geo["x_dark_cut"], self.device_r, notch_d=self.notch_d, trans=self.trans)
        cr.set_source_rgba(*self.c_casing_border); cr.set_line_width(1.3); cr.stroke()
        cr.restore()

        # 3. BOTTOM RED CASING (Translates smoothly with expansion)
        cr.save()
        cr.translate(0, geo["bot_casing_y"])

        # 3A. Red anime satin fill
        create_bottom_red_casing_path(cr, self.x_left, self.x_right, 610.0, 780.0, self.cx, 590.0, self.r_dark, geo["ang_dark_bot_start"], geo["ang_dark_bot_end"], geo["x_dark_cut"], self.device_r, notch_d=self.notch_d, trans=self.trans)
        red_pat_bot = cairo.LinearGradient(self.x_left, 590.0, self.x_right, 590.0)
        red_pat_bot.add_color_stop_rgb(0, *self.c_casing_l)
        red_pat_bot.add_color_stop_rgb(0.5, *self.c_casing_m)
        red_pat_bot.add_color_stop_rgb(1, *self.c_casing_r)
        cr.set_source(red_pat_bot); cr.fill()

        # 3B. Anime concentric grooves
        draw_anime_grooves(cr, self.x_left, 780.0, self.grooves, 1.5 * math.pi, 2 * math.pi)
        draw_anime_grooves(cr, self.x_right, 780.0, self.grooves, math.pi, 1.5 * math.pi)

        # 3C. Stroke casing outline
        create_bottom_red_casing_path(cr, self.x_left, self.x_right, 610.0, 780.0, self.cx, 590.0, self.r_dark, geo["ang_dark_bot_start"], geo["ang_dark_bot_end"], geo["x_dark_cut"], self.device_r, notch_d=self.notch_d, trans=self.trans)
        cr.set_source_rgba(*self.c_casing_border); cr.set_line_width(1.3); cr.stroke()
        cr.restore()

        # 4. DARK FLANGES
        c_dark_r, c_dark_g, c_dark_b = self.c_flange
        r_s, g_s, b_s = self.c_chassis

        cr.save()
        cr.new_sub_path()
        cr.move_to(self.x_left, geo["y_silver_top"]); cr.line_to(self.x_left, geo["y_dark_top"]); cr.line_to(self.cx - geo["x_dark_cut"], geo["y_dark_top"])
        cr.arc(self.cx, geo["cy_top"], self.r_dark, geo["ang_dark_top_end"], geo["ang_dark_top_start"])
        cr.line_to(self.x_right, geo["y_dark_top"]); cr.line_to(self.x_right, geo["y_silver_top"]); cr.line_to(self.cx + geo["x_chassis_cut"], geo["y_silver_top"])
        cr.arc_negative(self.cx, geo["cy_top"], self.r_chassis, geo["ang_chassis_top_start"], geo["ang_chassis_top_end"])
        cr.close_path()
        cr.set_source_rgba(c_dark_r, c_dark_g, c_dark_b, 0.85); cr.fill()
        cr.move_to(self.x_left, geo["y_dark_top"]); cr.line_to(self.cx - geo["x_dark_cut"], geo["y_dark_top"])
        cr.arc(self.cx, geo["cy_top"], self.r_dark, geo["ang_dark_top_end"], geo["ang_dark_top_start"]); cr.line_to(self.x_right, geo["y_dark_top"])
        cr.set_source_rgba(0x10/255.0, 0x02/255.0, 0x05/255.0, 0.95); cr.set_line_width(1.0); cr.stroke()
        cr.restore()

        cr.save()
        cr.new_sub_path()
        cr.move_to(self.x_left, geo["y_silver_bot"]); cr.line_to(self.x_left, geo["y_dark_bot"]); cr.line_to(self.cx - geo["x_dark_cut"], geo["y_dark_bot"])
        cr.arc_negative(self.cx, geo["cy_bot"], self.r_dark, geo["ang_dark_bot_end"], geo["ang_dark_bot_start"])
        cr.line_to(self.x_right, geo["y_dark_bot"]); cr.line_to(self.x_right, geo["y_silver_bot"]); cr.line_to(self.cx + geo["x_chassis_cut"], geo["y_silver_bot"])
        cr.arc(self.cx, geo["cy_bot"], self.r_chassis, geo["ang_chassis_bot_start"], geo["ang_chassis_bot_end"])
        cr.close_path()
        cr.set_source_rgba(c_dark_r, c_dark_g, c_dark_b, 0.85); cr.fill()
        cr.move_to(self.x_left, geo["y_dark_bot"]); cr.line_to(self.cx - geo["x_dark_cut"], geo["y_dark_bot"])
        cr.arc_negative(self.cx, geo["cy_bot"], self.r_dark, geo["ang_dark_bot_end"], geo["ang_dark_bot_start"]); cr.line_to(self.x_right, geo["y_dark_bot"])
        cr.set_source_rgba(0x10/255.0, 0x02/255.0, 0x05/255.0, 0.95); cr.set_line_width(1.0); cr.stroke()
        cr.restore()

        # 5. TOP SILVER CHASSIS: VÒNG LÊN (Upward cuff)
        prot = 2.5
        r_cuff = 2.5
        cr.save()
        cr.new_sub_path()
        cr.move_to(self.x_left, geo["y_edge_top"])
        cr.arc(self.x_left, geo["y_edge_top"] - r_cuff, r_cuff, 0.5 * math.pi, math.pi)
        cr.line_to(self.x_left - prot, geo["y_dark_top"] + r_cuff)
        cr.arc(self.x_left, geo["y_dark_top"] + r_cuff, r_cuff, math.pi, 1.5 * math.pi)
        cr.line_to(self.x_left, geo["y_silver_top"])
        cr.line_to(self.cx - geo["x_chassis_cut"], geo["y_silver_top"])
        cr.arc(self.cx, geo["cy_top"], self.r_chassis, geo["ang_chassis_top_end"], geo["ang_chassis_top_start"])
        cr.line_to(self.x_right, geo["y_silver_top"])
        cr.line_to(self.x_right, geo["y_dark_top"])
        cr.arc(self.x_right, geo["y_dark_top"] + r_cuff, r_cuff, 1.5 * math.pi, 2 * math.pi)
        cr.line_to(self.x_right + prot, geo["y_edge_top"] - r_cuff)
        cr.arc(self.x_right, geo["y_edge_top"] - r_cuff, r_cuff, 0, 0.5 * math.pi)
        cr.line_to(self.cx + geo["x_outer_cut"], geo["y_edge_top"])
        cr.arc_negative(self.cx, geo["cy_top"], self.r_outer, geo["ang_outer_top_start"], geo["ang_outer_top_end"])
        cr.close_path()
        silver_pat_top = cairo.LinearGradient(self.x_left, geo["y_dark_top"], self.x_left, geo["y_edge_top"])
        silver_pat_top.add_color_stop_rgb(0.0, 0xDE/255.0, 0xE4/255.0, 0xEE/255.0)
        silver_pat_top.add_color_stop_rgb(1.0, 0xC6/255.0, 0xCE/255.0, 0xD8/255.0)
        cr.set_source(silver_pat_top); cr.fill_preserve()
        cr.set_source_rgba(*self.c_band_stroke); cr.set_line_width(1.0); cr.stroke()
        cr.restore()

        # 5B. BOTTOM SILVER CHASSIS: QUAY LÊN TRÊN ĐỒNG BỘ 100%!
        y_up_top = geo["y_edge_bot"] - self.cuff_ext
        cr.save()
        cr.new_sub_path()
        cr.move_to(self.x_left, geo["y_edge_bot"])
        cr.line_to(self.x_left, y_up_top)
        cr.arc_negative(self.x_left, y_up_top + r_cuff, r_cuff, 1.5 * math.pi, math.pi)
        cr.line_to(self.x_left - prot, geo["y_silver_bot"] - r_cuff)
        cr.arc_negative(self.x_left, geo["y_silver_bot"] - r_cuff, r_cuff, math.pi, 0.5 * math.pi)
        cr.line_to(self.cx - geo["x_chassis_cut"], geo["y_silver_bot"])
        cr.arc_negative(self.cx, geo["cy_bot"], self.r_chassis, geo["ang_chassis_bot_end"], geo["ang_chassis_bot_start"])
        cr.line_to(self.x_right, geo["y_silver_bot"])
        cr.arc_negative(self.x_right, geo["y_silver_bot"] - r_cuff, r_cuff, 0.5 * math.pi, 0)
        cr.line_to(self.x_right + prot, y_up_top + r_cuff)
        cr.arc_negative(self.x_right, y_up_top + r_cuff, r_cuff, 0, 1.5 * math.pi)
        cr.line_to(self.x_right, geo["y_edge_bot"])
        cr.line_to(self.cx + geo["x_outer_cut"], geo["y_edge_bot"])
        cr.arc(self.cx, geo["cy_bot"], self.r_outer, geo["ang_outer_bot_start"], geo["ang_outer_bot_end"])
        cr.close_path()
        silver_pat_bot = cairo.LinearGradient(self.x_left, geo["y_edge_bot"], self.x_left, geo["y_silver_bot"])
        silver_pat_bot.add_color_stop_rgb(0.0, 0xC6/255.0, 0xCE/255.0, 0xD8/255.0)
        silver_pat_bot.add_color_stop_rgb(1.0, 0xDE/255.0, 0xE4/255.0, 0xEE/255.0)
        cr.set_source(silver_pat_bot); cr.fill_preserve()
        cr.set_source_rgba(*self.c_band_stroke); cr.set_line_width(1.0); cr.stroke()
        cr.restore()

        # 6. POKÉBALL BANDS
        band_pat_top = cairo.LinearGradient(self.cx - self.r_outer, geo["cy_top"], self.cx + self.r_outer, geo["cy_top"])
        band_pat_top.add_color_stop_rgb(0, *self.c_band_stop0)
        band_pat_top.add_color_stop_rgb(0.5, *self.c_band_stop1)
        band_pat_top.add_color_stop_rgb(1, *self.c_band_stop2)

        cr.save()
        cr.new_sub_path()
        cr.arc_negative(self.cx, geo["cy_top"], self.r_outer, geo["ang_outer_top_start"], geo["ang_outer_top_end"])
        cr.line_to(self.cx - geo["x_inner_cut"], geo["y_edge_top"])
        cr.arc(self.cx, geo["cy_top"], self.r_inner, geo["ang_inner_top_end"], geo["ang_inner_top_start"])
        cr.close_path()
        cr.set_source(band_pat_top); cr.fill_preserve()
        cr.set_source_rgba(*self.c_band_stroke); cr.set_line_width(1.3); cr.stroke()
        cr.arc(self.cx, geo["cy_top"], self.r_inner, geo["ang_inner_top_end"], geo["ang_inner_top_start"])
        cr.set_source_rgba(0, 0, 0, 0.30); cr.set_line_width(2.0); cr.stroke()
        cr.restore()

        band_pat_bot = cairo.LinearGradient(self.cx - self.r_outer, geo["cy_bot"], self.cx + self.r_outer, geo["cy_bot"])
        band_pat_bot.add_color_stop_rgb(0, *self.c_band_stop0)
        band_pat_bot.add_color_stop_rgb(0.5, *self.c_band_stop1)
        band_pat_bot.add_color_stop_rgb(1, *self.c_band_stop2)

        cr.save()
        cr.new_sub_path()
        cr.arc(self.cx, geo["cy_bot"], self.r_outer, geo["ang_outer_bot_start"], geo["ang_outer_bot_end"])
        cr.line_to(self.cx - geo["x_inner_cut"], geo["y_edge_bot"])
        cr.arc_negative(self.cx, geo["cy_bot"], self.r_inner, geo["ang_inner_bot_end"], geo["ang_inner_bot_start"])
        cr.close_path()
        cr.set_source(band_pat_bot); cr.fill_preserve()
        cr.set_source_rgba(*self.c_band_stroke); cr.set_line_width(1.3); cr.stroke()
        cr.arc(self.cx, geo["cy_bot"], self.r_inner, geo["ang_inner_bot_start"], geo["ang_inner_bot_end"])
        cr.set_source_rgba(0, 0, 0, 0.30); cr.set_line_width(2.0); cr.stroke()
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
    app.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
