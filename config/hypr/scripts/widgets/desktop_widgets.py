#!/usr/bin/env python3
# desktop_widgets.py — Pinned Desktop Background Widgets for Hyprland.
# Layout: Profile avatar card (Top-Left) and Weather Forecast (Top-Right).
# Pinned to GtkLayerShell Layer.BOTTOM beneath all application windows.

import os
import sys
import time
import datetime
import calendar
import threading
import urllib.request
import urllib.parse
import json
import subprocess
import signal
import math
import cairo
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
try:
    gi.require_version('GtkLayerShell', '0.1')
    from gi.repository import GtkLayerShell
    HAS_LAYER_SHELL = True
except Exception:
    HAS_LAYER_SHELL = False

from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Pango, PangoCairo

# Ensure script directory and system directory are in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_ROOT = os.path.dirname(SCRIPT_DIR)
SYSTEM_DIR = os.path.join(SCRIPTS_ROOT, "system")
HYPR_DIR = os.path.dirname(SCRIPTS_ROOT)

for p in (SCRIPT_DIR, SCRIPTS_ROOT, SYSTEM_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

def get_repo_root():
    curr = SCRIPT_DIR
    while curr and curr != "/":
        if os.path.isdir(os.path.join(curr, "config")):
            return curr
        curr = os.path.dirname(curr)
    return os.path.expanduser("~/custom")

# Import color palette tokens
try:
    from palette import (
        PALETTE, hex_to_rgba,
        C_BG_WIN, C_BG_CARD, C_BG_CARD_HOVER, C_BG_SUBTLE,
        C_ACCENT, C_ACCENT_HOVER, C_TEXT_PRI, C_TEXT_SEC, C_TEXT_MUT, C_TEXT_INV,
        C_STATUS_WARN, C_STATUS_CRIT, C_STATUS_SUCC, C_RIBBON,
        C_BG_WAYBAR, C_BORDER_3D, C_BG_CREAM,
        BG_WINDOW_RGBA, BG_CARD_RGBA, ACCENT_RGBA, ACCENT_HOVER_RGBA,
        BORDER_WINDOW_RGBA, BORDER_CARD_RGBA
    )
except ImportError:
    C_BG_WIN        = "#201011"
    C_BG_CARD       = "#2A1A1E"
    C_BG_CARD_HOVER = "#3A222A"
    C_BG_SUBTLE     = "#301F20"
    C_ACCENT        = "#DC1A36"
    C_ACCENT_HOVER  = "#F02D4C"
    C_TEXT_PRI      = "#FFF0F5"
    C_TEXT_SEC      = "#E8C2D0"
    C_TEXT_MUT      = "#A68595"
    C_TEXT_INV      = "#FFFFFF"
    C_STATUS_WARN   = "#FFB86C"
    C_STATUS_CRIT   = "#DC1A36"
    C_STATUS_SUCC   = "#8FBC8F"
    C_RIBBON        = "#50A6FF"
    C_BG_WAYBAR     = "#851733"
    C_BORDER_3D     = "#4D0A1C"
    C_BG_CREAM      = "rgba(255, 240, 245, 0.96)"
    BG_WINDOW_RGBA  = (32.0/255.0, 16.0/255.0, 18.0/255.0, 0.98)
    BG_CARD_RGBA    = (42.0/255.0, 26.0/255.0, 31.0/255.0, 0.95)
    ACCENT_RGBA     = (220.0/255.0, 26.0/255.0, 54.0/255.0, 1.0)
    ACCENT_HOVER_RGBA = (240.0/255.0, 45.0/255.0, 76.0/255.0, 1.0)
    BORDER_WINDOW_RGBA = (1.0, 1.0, 1.0, 0.12)
    BORDER_CARD_RGBA   = (1.0, 1.0, 1.0, 0.12)

    def hex_to_rgba(hex_code, alpha=1.0):
        h = hex_code.strip().lstrip('#')
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, float(alpha))

PID_FILE = "/tmp/desktop_widgets.pid"

MONTHS_EN = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]
DAYS_EN = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
DAYS_SHORT_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def get_weather_icon(desc: str, hour: int) -> str:
    """Return appropriate weather glyph according to description and time."""
    low = desc.lower()
    # Evening starts from 17:00 (5:00 PM) in Vietnam
    is_day = 6 <= hour < 17
    if "thunder" in low or "lightning" in low:
        return "󰖓"
    elif "snow" in low or "ice" in low or "sleet" in low or "blizzard" in low:
        return "󰖘"
    elif "rain" in low or "drizzle" in low or "shower" in low:
        return "󰖗"
    elif "fog" in low or "mist" in low or "haze" in low:
        return "󰖑"
    elif "partly cloudy" in low or "few clouds" in low:
        return "󰖕" if is_day else "󰼱"
    elif "cloud" in low or "overcast" in low:
        return "󰖐"
    elif "clear" in low or "sunny" in low:
        # Night condition: show moon icon
        return "󰖙" if is_day else "󰼱"
    else:
        return "󰖕" if is_day else "󰼱"

WMO_MAP = {
    0: ("Clear", "󰖙", "󰼱"),
    1: ("Mainly clear", "󰖕", "󰼱"),
    2: ("Partly cloudy", "󰖕", "󰼱"),
    3: ("Overcast", "󰖐", "󰖐"),
    45: ("Fog", "󰖑", "󰖑"),
    48: ("Rime fog", "󰖑", "󰖑"),
    51: ("Light drizzle", "󰖗", "󰖗"),
    53: ("Drizzle", "󰖗", "󰖗"),
    55: ("Dense drizzle", "󰖗", "󰖗"),
    56: ("Freezing drizzle", "󰖘", "󰖘"),
    57: ("Freezing drizzle", "󰖘", "󰖘"),
    61: ("Light rain", "󰖗", "󰖗"),
    63: ("Moderate rain", "󰖗", "󰖗"),
    65: ("Heavy rain", "󰖗", "󰖗"),
    66: ("Freezing rain", "󰖘", "󰖘"),
    67: ("Freezing rain", "󰖘", "󰖘"),
    71: ("Light snow", "󰖘", "󰖘"),
    73: ("Snow", "󰖘", "󰖘"),
    75: ("Heavy snow", "󰖘", "󰖘"),
    77: ("Snow grains", "󰖘", "󰖘"),
    80: ("Rain showers", "󰖗", "󰖗"),
    81: ("Rain showers", "󰖗", "󰖗"),
    82: ("Violent rain", "󰖗", "󰖗"),
    85: ("Snow showers", "󰖘", "󰖘"),
    86: ("Heavy snow showers", "󰖘", "󰖘"),
    95: ("Thunderstorm", "󰖓", "󰖓"),
    96: ("Thunderstorm", "󰖓", "󰖓"),
    99: ("Thunderstorm", "󰖓", "󰖓"),
}

def get_user_location():
    """
    Get user coordinates (lat, lon, city_name).
    1. Check user config file ~/.config/hypr/weather_location.json (if manually configured).
    2. Check cached geolocation in ~/.cache/user_geo_location.json (valid for 24 hours).
    3. Query IP geolocation API (http://ip-api.com/json with timeout=3s, or https://ipinfo.io/json).
    4. Fallback to Hanoi, Vietnam (lat=21.0285, lon=105.8542).
    """
    user_conf = os.path.expanduser("~/.config/hypr/weather_location.json")
    if os.path.exists(user_conf):
        try:
            with open(user_conf, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if "latitude" in cfg and "longitude" in cfg:
                    return float(cfg["latitude"]), float(cfg["longitude"]), cfg.get("city", "Custom")
        except Exception:
            pass

    geo_cache = os.path.expanduser("~/.cache/user_geo_location.json")
    if os.path.exists(geo_cache):
        try:
            mtime = os.path.getmtime(geo_cache)
            if time.time() - mtime < 86400:  # 24h cache
                with open(geo_cache, "r", encoding="utf-8") as f:
                    cdata = json.load(f)
                    if "lat" in cdata and "lon" in cdata:
                        return float(cdata["lat"]), float(cdata["lon"]), cdata.get("city", "Hanoi")
        except Exception:
            pass

    # Query IP Geolocation API
    try:
        req = urllib.request.Request("http://ip-api.com/json", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get("status") == "success" and "lat" in data and "lon" in data:
                lat = float(data["lat"])
                lon = float(data["lon"])
                city = data.get("city", "Hanoi")
                try:
                    with open(geo_cache, "w", encoding="utf-8") as f:
                        json.dump({"lat": lat, "lon": lon, "city": city}, f)
                except Exception:
                    pass
                return lat, lon, city
    except Exception:
        pass

    try:
        req = urllib.request.Request("https://ipinfo.io/json", headers={'User-Agent': 'curl/8.0'})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if "loc" in data:
                lat_str, lon_str = data["loc"].split(",")
                lat = float(lat_str)
                lon = float(lon_str)
                city = data.get("city", "Hanoi")
                try:
                    with open(geo_cache, "w", encoding="utf-8") as f:
                        json.dump({"lat": lat, "lon": lon, "city": city}, f)
                except Exception:
                    pass
                return lat, lon, city
    except Exception:
        pass

    return 21.0285, 105.8542, "Hanoi"

def parse_open_meteo_forecast(data: dict):
    curr = data.get("current", {})
    hour = datetime.datetime.now().hour
    is_day = bool(curr.get("is_day", 1 if 6 <= hour < 18 else 0))
    code = curr.get("weather_code", 0)
    desc, ico_d, ico_n = WMO_MAP.get(code, ("Clear", "󰖙", "󰼱"))
    curr_icon = ico_d if is_day else ico_n
    temp_c = str(int(round(curr.get("temperature_2m", 0))))

    daily = data.get("daily", {})
    dates = daily.get("time", [])[:3]
    codes = daily.get("weather_code", [])[:3]
    maxs = daily.get("temperature_2m_max", [])[:3]
    mins = daily.get("temperature_2m_min", [])[:3]

    forecast_list = []
    for i in range(len(dates)):
        try:
            dt = datetime.datetime.strptime(dates[i], "%Y-%m-%d")
            day_name = "Today" if i == 0 else DAYS_SHORT_EN[dt.weekday()]
        except Exception:
            day_name = f"Day {i+1}"
        d_code = codes[i] if i < len(codes) else 0
        d_desc, d_ico, _ = WMO_MAP.get(d_code, ("Clear", "󰖙", "󰼱"))
        d_max = str(int(round(maxs[i]))) if i < len(maxs) else "--"
        d_min = str(int(round(mins[i]))) if i < len(mins) else "--"
        forecast_list.append({
            "day": day_name,
            "icon": d_ico,
            "max": d_max,
            "min": d_min,
            "full_desc": d_desc
        })

    return temp_c, curr_icon, desc, forecast_list

def parse_forecast_day(day_data: dict, day_index: int) -> dict:
    """Parse wttr.in daily forecast item into day name, icon, short condition, max & min temp."""
    date_str = day_data.get('date', '')
    try:
        dt = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        day_name = "Today" if day_index == 0 else DAYS_SHORT_EN[dt.weekday()]
    except Exception:
        day_name = f"Day {day_index + 1}"

    max_c = day_data.get('maxtempC', '--')
    min_c = day_data.get('mintempC', '--')

    hourly = day_data.get('hourly', [])
    desc = hourly[4]['weatherDesc'][0]['value'] if len(hourly) > 4 else (hourly[0]['weatherDesc'][0]['value'] if hourly else 'Clear')

    low = desc.lower()
    if "thunder" in low or "lightning" in low:
        icon = "󰖓"
        short = "Thunder"
    elif "snow" in low or "ice" in low or "sleet" in low or "blizzard" in low:
        icon = "󰖘"
        short = "Snow"
    elif "rain" in low or "drizzle" in low or "shower" in low:
        icon = "󰖗"
        short = "Rain"
    elif "fog" in low or "mist" in low or "haze" in low:
        icon = "󰖑"
        short = "Fog"
    elif "partly cloudy" in low or "few clouds" in low:
        icon = "󰖕"
        short = "P.Cloud"
    elif "cloud" in low or "overcast" in low:
        icon = "󰖐"
        short = "Cloudy"
    elif "clear" in low or "sunny" in low:
        icon = "󰖙"
        short = "Sunny"
    else:
        icon = "󰖕"
        short = "Clear"

    return {
        "day": day_name,
        "icon": icon,
        "short_desc": short,
        "max": max_c,
        "min": min_c,
        "full_desc": desc
    }

def apply_global_css():
    """Load desktop_widgets.css globally for all widget windows."""
    css_provider = Gtk.CssProvider()
    repo_root = get_repo_root()
    candidate_paths = [
        os.path.join(HYPR_DIR, "styles", "desktop_widgets.css"),
        os.path.expanduser("~/.config/hypr/styles/desktop_widgets.css"),
        os.path.join(repo_root, "config", "hypr", "styles", "desktop_widgets.css"),
    ]
    for p in candidate_paths:
        abs_p = os.path.abspath(p)
        if os.path.exists(abs_p):
            try:
                css_provider.load_from_path(abs_p)
                break
            except Exception as e:
                print(f"[desktop_widgets] Warning: Error parsing CSS from {abs_p}: {e}", file=sys.stderr)

    screen = Gdk.Screen.get_default()
    if screen:
        Gtk.StyleContext.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER + 20)

def on_window_draw_clear(widget, cr):
    """Draw transparent RGBA surface without artifacts."""
    cr.set_source_rgba(0, 0, 0, 0)
    cr.set_operator(cairo.OPERATOR_CLEAR)
    cr.paint()
    cr.set_operator(cairo.OPERATOR_OVER)
    return False

def get_uptime_str() -> str:
    """Read system uptime from /proc/uptime and format cleanly."""
    try:
        with open("/proc/uptime", "r") as f:
            sec = float(f.readline().split()[0])
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        if h >= 24:
            d = h // 24
            rh = h % 24
            return f"{d}d {rh}h"
        elif h > 0:
            return f"{h}h {m}m"
        else:
            return f"{m}m"
    except Exception:
        return "--"

# ==============================================================================
# WIDGET 1: PROFILE AVATAR CARD WINDOW (TOP-LEFT)
# ==============================================================================
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
        repo_root = get_repo_root()
        paths = [
            os.path.join(repo_root, relative_path),
            os.path.expanduser(f"~/.config/hypr/{os.path.basename(relative_path)}"),
            os.path.expanduser(f"~/.config/hypr/assets/{os.path.basename(relative_path)}"),
            os.path.expanduser(f"~/custom/{relative_path}"),
        ]
        for p in paths:
            if os.path.exists(p):
                return p
        return None

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

        # 3D extrusion shadow below smoothly swept along corners
        steps = 14
        for s in range(steps + 1):
            dy = 3.5 * (s / steps)
            rounded_rect(0, dy, w, h, r)
            cr.set_source_rgb(*hex_to_rgba(C_BORDER_3D)[:3])
            cr.fill()

        # Clip and paint cover image
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
                cr.set_source_rgb(*hex_to_rgba(C_BG_WAYBAR)[:3])
                cr.paint()
                cr.restore()

        # 3D frame border: clear, solid #4D0A1C outline all around
        rounded_rect(0, 0, w, h, r)
        cr.set_source_rgba(*hex_to_rgba(C_BORDER_3D, 0.95))
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

        # 3D extrusion shadow below smoothly swept along corners
        steps = 14
        for s in range(steps + 1):
            dy = 3.5 * (s / steps)
            cr.arc(cx, cy + dy, r, 0, 6.2831853)
            cr.set_source_rgb(*hex_to_rgba(C_BORDER_3D)[:3])
            cr.fill()

        # Clip and paint avatar image
        if avatar_path and os.path.exists(avatar_path):
            try:
                src = GdkPixbuf.Pixbuf.new_from_file_at_scale(avatar_path, int(r*2), int(r*2), False)
                cr.save()
                cr.arc(cx, cy, r, 0, 6.2831853)
                cr.clip()
                Gdk.cairo_set_source_pixbuf(cr, src, cx - r, cy - r)
                cr.paint()
                cr.restore()
            except Exception:
                cr.arc(cx, cy, r, 0, 6.2831853)
                cr.set_source_rgb(*hex_to_rgba(C_BG_WAYBAR)[:3])
                cr.fill()

        # 3D frame border: solid, crisp circular contour
        cr.arc(cx, cy, r, 0, 6.2831853)
        cr.set_source_rgba(*hex_to_rgba(C_BORDER_3D, 0.95))
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

        # 3D extrusion shadow below smoothly swept along circular curve
        steps = 14
        for s in range(steps + 1):
            dy = 3.6 * (s / steps)
            cr.arc(cx, cy + dy, r, 0, 6.2831853)
            cr.set_source_rgb(*hex_to_rgba(C_BORDER_3D)[:3])
            cr.fill()

        cr.save()
        cr.arc(cx, cy, r, 0, 6.2831853)
        cr.clip()

        # Bottom half: White / cream
        cr.set_source_rgb(*hex_to_rgba(C_TEXT_PRI)[:3])
        cr.paint()

        # Top half: Serena Red gradient
        pat = cairo.LinearGradient(0, cy - r, 0, cy)
        pat.add_color_stop_rgb(0, *hex_to_rgba(C_ACCENT_HOVER)[:3])
        pat.add_color_stop_rgb(1, *hex_to_rgba(C_ACCENT)[:3])
        cr.set_source(pat)
        cr.rectangle(cx - r, cy - r, r * 2, r)
        cr.fill()

        # Subtle anime glossy sheen arc
        cr.save()
        cr.arc(cx, cy - r * 0.45, r * 0.65, 3.4, 6.0)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.35)
        cr.set_line_width(2.2)
        cr.stroke()
        cr.restore()

        # Middle belt: dark wine
        cr.set_source_rgb(*hex_to_rgba(C_BORDER_3D)[:3])
        cr.rectangle(cx - r, cy - 2.5, r * 2, 5.0)
        cr.fill()

        # Center Pokeball Button
        cr.arc(cx, cy, 9.0, 0, 6.2831853)
        cr.set_source_rgb(*hex_to_rgba(C_BORDER_3D)[:3])
        cr.fill()

        cr.arc(cx, cy, 6.5, 0, 6.2831853)
        cr.set_source_rgb(*hex_to_rgba(C_TEXT_INV)[:3])
        cr.fill()

        cr.arc(cx, cy, 3.5, 0, 6.2831853)
        cr.set_source_rgb(*hex_to_rgba(C_BORDER_3D)[:3])
        cr.fill()

        cr.arc(cx, cy, 2.5, 0, 6.2831853)
        cr.set_source_rgb(*hex_to_rgba(C_TEXT_INV)[:3])
        cr.fill()

        cr.restore()

        # Outer ring: crisp solid #4D0A1C contour
        cr.arc(cx, cy, r, 0, 6.2831853)
        cr.set_source_rgba(*hex_to_rgba(C_BORDER_3D, 0.95))
        cr.set_line_width(2.0)
        cr.stroke()

        pix = Gdk.pixbuf_get_from_surface(surface, 0, 0, size, size + extra_h)
        return Gtk.Image.new_from_pixbuf(pix)

    def update_uptime_tick(self):
        try:
            self.lbl_uptime_val.set_markup(f"<span font_family='Inter, Sans' font='13.5' weight='800' color='{C_TEXT_PRI}'>{get_uptime_str()}</span>")
        except Exception:
            pass
        return True

    def build_ui(self):
        # Master column holding Card 1 (Avatar) and Card 2 (System info)
        col_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        col_box.set_size_request(269, -1)

        # -------------------------------------------------------------
        # CARD 1: Compact Serena Avatar Card (Original Compact Height)
        # -------------------------------------------------------------
        card1_event = Gtk.EventBox()
        card1_event.set_visible_window(False)

        card1_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card1_box.get_style_context().add_class("desktop-widget-card")
        card1_box.get_style_context().add_class("widget-avatar-card")
        card1_box.set_size_request(269, -1)

        card1_event.connect("enter-notify-event", lambda w, e: card1_box.get_style_context().add_class("card-hover"))
        card1_event.connect("leave-notify-event", lambda w, e: card1_box.get_style_context().remove_class("card-hover"))

        # Profile header (Cover banner + Overlapping Avatar + Name & Subtitle)
        header_fixed = Gtk.Fixed()
        header_fixed.set_size_request(220, 108)

        banner_img = self.create_banner_image(w=220, h=72, r=12.0)
        header_fixed.put(banner_img, 0, 0)

        avatar_img = self.create_avatar_image(size=60)
        header_fixed.put(avatar_img, 6, 44)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        text_box.get_style_context().add_class("avatar-profile-text-box")

        lbl_name = Gtk.Label()
        lbl_name.get_style_context().add_class("avatar-profile-name")
        lbl_name.set_markup(f"<span font_family='Inter, Sans' font='14' weight='800' color='{C_BG_WAYBAR}'>Serena</span>")
        lbl_name.set_halign(Gtk.Align.START)

        lbl_sub = Gtk.Label()
        lbl_sub.get_style_context().add_class("avatar-profile-subtitle")
        lbl_sub.set_markup(f"<span font_family='Inter, Sans' font='8' weight='700' color='{C_TEXT_MUT}'>pokemon performer</span>")
        lbl_sub.set_halign(Gtk.Align.START)

        text_box.pack_start(lbl_name, False, False, 0)
        text_box.pack_start(lbl_sub, False, False, 0)
        header_fixed.put(text_box, 72, 74)

        card1_box.pack_start(header_fixed, False, False, 0)

        # 3 Pokemon in Pokeballs (Compact)
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
            ball_img = self.create_single_pokeball_image(size=ball_sz)
            balls_fixed.put(ball_img, bx, by)

            asset_path = self.find_asset_path(asset_rel)
            if asset_path and os.path.exists(asset_path):
                sp_pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(asset_path, sprite_sz, sprite_sz, True)
                sp_img = Gtk.Image.new_from_pixbuf(sp_pix)
                sx = bx + int((ball_sz - sprite_sz) / 2)
                sy = by + int((ball_sz - sprite_sz) / 2) - 4
                balls_fixed.put(sp_img, sx, sy)

        card1_box.pack_start(balls_fixed, False, False, 0)
        card1_event.add(card1_box)
        col_box.pack_start(card1_event, False, False, 0)

        # -------------------------------------------------------------
        # CARD 2: System Info Widget (Desktop: Hyprland, Uptime: Live)
        # -------------------------------------------------------------
        card2_event = Gtk.EventBox()
        card2_event.set_visible_window(False)

        card2_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card2_box.get_style_context().add_class("desktop-widget-card")
        card2_box.get_style_context().add_class("widget-sysinfo-card")
        card2_box.set_size_request(269, -1)

        card2_event.connect("enter-notify-event", lambda w, e: card2_box.get_style_context().add_class("card-hover"))
        card2_event.connect("leave-notify-event", lambda w, e: card2_box.get_style_context().remove_class("card-hover"))

        # 2 Sub-boxes: Box 1 (Sunset Gradient) & Box 2 (Ruby Wine with tactile white border)
        info_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        info_row.set_homogeneous(True)

        # Box 1: Desktop / Hyprland (Waybar Sunset Gradient Style)
        b1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        b1.get_style_context().add_class("sysinfo-box-gradient")
        b1.get_style_context().add_class("gradient-sunset")

        l1_title = Gtk.Label()
        l1_title.get_style_context().add_class("sysinfo-sub-label")
        l1_title.set_markup(f"<span font_family='Inter, Sans' font='8' weight='700' color='{C_BORDER_3D}'>desktop</span>")

        l1_val = Gtk.Label()
        l1_val.get_style_context().add_class("sysinfo-main-label")
        l1_val.set_markup(f"<span font_family='Inter, Sans' font='13.5' weight='800' color='{C_BORDER_3D}'>hyprland</span>")

        b1.pack_start(l1_title, False, False, 2)
        b1.pack_start(l1_val, False, False, 2)
        info_row.pack_start(b1, True, True, 0)

        # Box 2: Uptime / Live time (Waybar Ruby Wine Style with white border)
        b2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        b2.get_style_context().add_class("sysinfo-box-solid")

        l2_title = Gtk.Label()
        l2_title.get_style_context().add_class("sysinfo-sub-label")
        l2_title.set_markup(f"<span font_family='Inter, Sans' font='8' weight='700' color='{C_TEXT_SEC}'>uptime</span>")

        self.lbl_uptime_val = Gtk.Label()
        self.lbl_uptime_val.get_style_context().add_class("sysinfo-main-label")
        self.lbl_uptime_val.set_markup(f"<span font_family='Inter, Sans' font='13.5' weight='800' color='{C_TEXT_PRI}'>{get_uptime_str()}</span>")

        b2.pack_start(l2_title, False, False, 2)
        b2.pack_start(self.lbl_uptime_val, False, False, 2)
        info_row.pack_start(b2, True, True, 0)

        card2_box.pack_start(info_row, True, True, 0)
        card2_event.add(card2_box)
        col_box.pack_start(card2_event, False, False, 0)

        self.add(col_box)

        # Periodic timer for uptime: update every 60 seconds
        GLib.timeout_add_seconds(60, self.update_uptime_tick)


# ==============================================================================
# WIDGET 2: WEATHER FORECAST WINDOW (TOP-RIGHT)
# ==============================================================================
class Tactile3DTemperatureWidget(Gtk.DrawingArea):
    """
    Renders 3D cel-shaded temperature digits directly onto Cairo:
    - Inner Core: #851733 (Ruby Wine)
    - Crisp Contour: 2.0px white border (#FFFFFF)
    - 3D Extrusion: #4D0A1C (1.5px outer contour + 4.0px bottom 3D base)
    """
    def __init__(self, temp_str="--", unit_str="°C"):
        super().__init__()
        self._temp = str(temp_str)
        self._unit = str(unit_str)
        self.set_halign(Gtk.Align.START)
        self.set_valign(Gtk.Align.END)
        self.set_size_request(130, 56)
        self.connect("draw", self.on_draw)

    def set_temperature(self, temp_str, unit_str="°C"):
        self._temp = str(temp_str)
        self._unit = str(unit_str)
        self.queue_draw()

    def get_text(self):
        return f"{self._temp}{self._unit}"

    def on_draw(self, widget, cr):
        cr.set_antialias(cairo.ANTIALIAS_BEST)

        layout = PangoCairo.create_layout(cr)
        if self._temp == "Offline":
            markup = "<span font_family='Inter, Sans' weight='800' size='24000'>Offline</span>"
        else:
            markup = (
                f"<span font_family='Inter, Sans' weight='900' size='44000'>{self._temp}</span>"
                f"<span font_family='Inter, Sans' weight='800' size='19000' rise='17000'> {self._unit}</span>"
            )
        layout.set_markup(markup, -1)

        ink_rect, log_rect = layout.get_pixel_extents()

        # Align with crisp top-left padding
        start_x = -ink_rect.x + 4.0
        start_y = -ink_rect.y + 4.0

        dark_color = hex_to_rgba(C_BORDER_3D)[:3]
        wine_color = hex_to_rgba(C_BG_WAYBAR)[:3]
        white_color = hex_to_rgba(C_TEXT_INV)[:3]

        extrusion_h = 4.0
        white_w = 4.6
        dark_extra = 1.6
        total_dark_w = white_w + dark_extra * 2.0

        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)

        # Layer 1: Dark 3D extrusion downward (#4D0A1C)
        steps = int(extrusion_h * 4)
        for s in range(steps + 1):
            dy = extrusion_h * (s / steps)
            cr.save()
            cr.translate(start_x, start_y + dy)
            PangoCairo.layout_path(cr, layout)
            cr.set_source_rgb(*dark_color)
            cr.set_line_width(total_dark_w)
            cr.stroke_preserve()
            cr.fill()
            cr.restore()

        # Layer 2: White contour outline (#FFFFFF)
        cr.save()
        cr.translate(start_x, start_y)
        PangoCairo.layout_path(cr, layout)
        cr.set_source_rgb(*white_color)
        cr.set_line_width(white_w)
        cr.stroke_preserve()
        cr.fill()
        cr.restore()

        # Layer 3: Wine red core fill (#851733)
        cr.save()
        cr.translate(start_x, start_y)
        PangoCairo.layout_path(cr, layout)
        cr.set_source_rgb(*wine_color)
        cr.fill()
        cr.restore()

        return False


class WeatherForecastWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Weather Forecast Widget")
        self.set_name("desktop-weather-window")
        self.set_decorated(False)
        self.set_resizable(False)

        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_namespace(self, "desktop-widgets")
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.BOTTOM)
            GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, False)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, False)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, 28)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 56)
            GtkLayerShell.set_exclusive_zone(self, 0)
        else:
            self.set_wmclass("desktop-widgets", "desktop-widgets")
            self.set_position(Gtk.WindowPosition.NONE)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        self.set_app_paintable(True)
        self.connect("draw", on_window_draw_clear)

        self._fetching_weather = False
        self._last_weather_fetch = 0

        self.build_ui()

        # Initial async weather fetch
        threading.Thread(target=self.fetch_weather_async, daemon=True).start()

        # Periodic weather refresh every 15 minutes
        GLib.timeout_add_seconds(900, self.on_periodic_weather_timer)

    def build_ui(self):
        card_event = Gtk.EventBox()
        card_event.set_visible_window(False)
        card_event.connect("button-press-event", self.on_weather_card_clicked)

        card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card_box.get_style_context().add_class("desktop-widget-card")
        card_box.get_style_context().add_class("widget-weather-card")
        card_box.set_size_request(269, 340)

        card_event.connect("enter-notify-event", lambda w, e: card_box.get_style_context().add_class("card-hover"))
        card_event.connect("leave-notify-event", lambda w, e: card_box.get_style_context().remove_class("card-hover"))

        # Row 1: Hero Temperature 3D Tactile Sub-Card (Sunset Gradient)
        hero_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        hero_box.get_style_context().add_class("tactile-hero-box")
        hero_box.get_style_context().add_class("gradient-sunset")

        # Top Row inside Hero Box:
        # Left: "WEATHER" title
        # Right: Circular 3D Badge with Weather Icon
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        top_row.get_style_context().add_class("weather-hero-top-row")

        self.lbl_title = Gtk.Label()
        self.lbl_title.get_style_context().add_class("weather-hero-title")
        self.lbl_title.set_markup(f"<span font='9.5' weight='800' color='{C_BG_WAYBAR}'>WEATHER</span>")
        self.lbl_title.set_halign(Gtk.Align.START)
        self.lbl_title.set_valign(Gtk.Align.CENTER)
        top_row.pack_start(self.lbl_title, False, False, 0)

        # Weather Icon in Top-Right
        self.lbl_hero_icon = Gtk.Label()
        self.lbl_hero_icon.get_style_context().add_class("weather-hero-icon")
        self.lbl_hero_icon.set_markup(f"<span font='50' color='{C_BG_WAYBAR}'>󰼱</span>")
        self.lbl_hero_icon.set_halign(Gtk.Align.END)
        self.lbl_hero_icon.set_valign(Gtk.Align.CENTER)
        top_row.pack_end(self.lbl_hero_icon, False, False, 0)

        hero_box.pack_start(top_row, False, False, 0)

        # Bottom Row inside Hero Box:
        # 3D Cel-shaded tactile temperature digits (Waybar aesthetic directly on digits)
        self.tactile_temp = Tactile3DTemperatureWidget("--", "°C")
        hero_box.pack_start(self.tactile_temp, False, False, 2)

        card_box.pack_start(hero_box, False, False, 2)

        # Row 3: 3-Day Forecast Section (3 mini tactile 3D columns, clean Day/Icon/Temp)
        forecast_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        forecast_box.get_style_context().add_class("weather-forecast-container")
        forecast_box.set_halign(Gtk.Align.FILL)
        forecast_box.set_homogeneous(True)

        self.forecast_items = []
        for i in range(3):
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            col.get_style_context().add_class("tactile-col-box")

            lbl_day = Gtk.Label()
            lbl_day.get_style_context().add_class("forecast-col-day")
            lbl_day.set_markup(f"<span font='9.5' weight='700' color='{C_BG_WAYBAR}'>---</span>")

            lbl_ico = Gtk.Label()
            lbl_ico.get_style_context().add_class("forecast-col-icon")
            lbl_ico.set_markup(f"<span font='16' color='{C_BG_WAYBAR}'>󰖙</span>")

            lbl_temp = Gtk.Label()
            lbl_temp.get_style_context().add_class("forecast-col-temp")
            lbl_temp.set_markup(f"<span font='9' color='{C_BG_WAYBAR}'>--° --°</span>")

            col.pack_start(lbl_day, False, False, 0)
            col.pack_start(lbl_ico, False, False, 1)
            col.pack_start(lbl_temp, False, False, 1)
            forecast_box.pack_start(col, True, True, 0)

            self.forecast_items.append((lbl_day, lbl_ico, lbl_temp))

        card_box.pack_start(forecast_box, False, False, 2)

        card_event.add(card_box)
        self.add(card_event)

        # Immediately load cached weather so widget is never blank or "Offline" on launch
        self.load_cached_weather()

    def load_cached_weather(self):
        """Immediately populate UI with cached weather data if available."""
        cache_paths = [
            os.path.expanduser("~/.cache/desktop_weather_cache.json"),
            os.path.expanduser("~/.cache/open_meteo_cache.json"),
        ]
        for cp in cache_paths:
            if os.path.exists(cp):
                try:
                    with open(cp, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    fc = data.get("forecast", data)
                    if "current" in fc and "daily" in fc:
                        temp_c, icon, desc, fl = parse_open_meteo_forecast(fc)
                        self._update_weather_ui_direct(temp_c, icon, fl)
                        return True
                except Exception as e:
                    print(f"[desktop_widgets] Cache read error for {cp}: {e}", file=sys.stderr)
        return False

    def on_weather_card_clicked(self, widget, event):
        if event.button == 1:
            threading.Thread(target=self.fetch_weather_async, daemon=True).start()
            return True
        return False

    def on_periodic_weather_timer(self):
        threading.Thread(target=self.fetch_weather_async, daemon=True).start()
        return True

    def fetch_weather_async(self):
        if self._fetching_weather:
            return
        now = time.time()
        if now - self._last_weather_fetch < 5:
            return

        self._fetching_weather = True
        self._last_weather_fetch = now

        # Resolve dynamic user location (auto-detect via IP or user config)
        lat, lon, city = get_user_location()

        success = False

        # 1. Primary: Open-Meteo API (Worldwide, robust, fast, no API key)
        try:
            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}&"
                f"current=temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code,is_day&"
                f"daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=auto"
            )
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                temp_c, icon, desc, forecast_list = parse_open_meteo_forecast(data)
                GLib.idle_add(self._update_weather_ui_direct, temp_c, icon, forecast_list, city, desc)

                # Persist cache
                try:
                    out_cache = os.path.expanduser("~/.cache/desktop_weather_cache.json")
                    with open(out_cache, "w", encoding="utf-8") as f:
                        json.dump(data, f)
                except Exception:
                    pass
                success = True
        except Exception as e:
            print(f"[desktop_widgets] Open-Meteo fetch error: {e}", file=sys.stderr)

        # 2. Secondary fallback: wttr.in
        if not success:
            try:
                target_loc = urllib.parse.quote(city) if city else ""
                url = f"https://wttr.in/{target_loc}?format=j1"
                req = urllib.request.Request(url, headers={'User-Agent': 'curl/8.0'})
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    curr = data['current_condition'][0]
                    temp_c = curr.get('temp_C', '--')
                    desc = curr['weatherDesc'][0]['value'] if curr.get('weatherDesc') else 'Clear'
                    weather_days = data.get('weather', [])[:3]
                    forecast_list = [parse_forecast_day(wd, i) for i, wd in enumerate(weather_days)]
                    hour = datetime.datetime.now().hour
                    icon = get_weather_icon(desc, hour)
                    GLib.idle_add(self._update_weather_ui_direct, temp_c, icon, forecast_list, city, desc)
                    success = True
            except Exception as e:
                print(f"[desktop_widgets] wttr.in fetch error: {e}", file=sys.stderr)

        # Only fallback to Offline if temperature was never loaded from cache or network
        if not success:
            GLib.idle_add(self._update_weather_fallback)

        self._fetching_weather = False

    def _update_weather_ui_direct(self, temp_c, icon, forecast_list=None, city=None, desc=None):
        if hasattr(self, 'lbl_hero_icon'):
            self.lbl_hero_icon.set_markup(f"<span font='50' color='{C_BG_WAYBAR}'>{icon}</span>")
        if hasattr(self, 'tactile_temp'):
            self.tactile_temp.set_temperature(temp_c, "°C")

        if forecast_list and hasattr(self, 'forecast_items'):
            for idx, item_data in enumerate(forecast_list):
                if idx < len(self.forecast_items):
                    lbl_day, lbl_ico, lbl_temp = self.forecast_items[idx]
                    lbl_day.set_markup(f"<span font='9.5' weight='700' color='{C_BG_WAYBAR}'>{item_data['day']}</span>")
                    lbl_ico.set_markup(f"<span font='16' color='{C_BG_WAYBAR}'>{item_data['icon']}</span>")
                    lbl_temp.set_markup(
                        f"<span font='9' weight='700' color='{C_BG_WAYBAR}'>{item_data['max']}°</span> "
                        f"<span font='8.5' color='{C_TEXT_MUT}'>{item_data['min']}°</span>"
                    )
        return False

    def _update_weather_fallback(self):
        if hasattr(self, 'tactile_temp'):
            current_val = self.tactile_temp.get_text()
            if "--" in current_val:
                self.tactile_temp.set_temperature("Offline", "")
        return False


# ==============================================================================
# WIDGET 3: CALENDAR WINDOW (RIGHT COLUMN, BENEATH WEATHER)
# ==============================================================================
class Tactile3DMonthWidget(Gtk.DrawingArea):
    """
    Renders 3D cel-shaded month title directly onto Cairo:
    - Inner Core: #851733 (Ruby Wine)
    - Crisp Contour: 2.0px white border (#FFFFFF)
    - 3D Extrusion: #4D0A1C (1.5px outer contour + 3.8px bottom 3D base)
    """
    def __init__(self, month_str="NOVEMBER"):
        super().__init__()
        self._month = str(month_str).upper()
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)
        self.set_size_request(130, 38)
        self.connect("draw", self.on_draw)

    def set_month(self, month_str):
        self._month = str(month_str).upper()
        self.queue_draw()

    def on_draw(self, widget, cr):
        cr.set_antialias(cairo.ANTIALIAS_BEST)
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()

        layout = PangoCairo.create_layout(cr)
        n = len(self._month)
        if n <= 4:
            fsize = 21000
        elif n <= 6:
            fsize = 19000
        elif n <= 8:
            fsize = 17000
        else:
            fsize = 15000

        markup = f"<span font_family='Inter, Sans' weight='900' size='{fsize}'>{self._month}</span>"
        layout.set_markup(markup, -1)

        ink, log = layout.get_pixel_extents()

        start_x = (w - ink.width) / 2.0 - ink.x
        start_y = (h - ink.height) / 2.0 - ink.y - 1.0

        dark_color = hex_to_rgba(C_BORDER_3D)[:3]
        wine_color = hex_to_rgba(C_BG_WAYBAR)[:3]
        white_color = hex_to_rgba(C_TEXT_INV)[:3]

        extrusion_h = 3.8
        white_w = 4.2
        dark_extra = 1.5
        total_dark_w = white_w + dark_extra * 2.0

        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)

        # Layer 1: Dark 3D extrusion downward (#4D0A1C)
        steps = int(extrusion_h * 4)
        for s in range(steps + 1):
            dy = extrusion_h * (s / steps)
            cr.save()
            cr.translate(start_x, start_y + dy)
            PangoCairo.layout_path(cr, layout)
            cr.set_source_rgb(*dark_color)
            cr.set_line_width(total_dark_w)
            cr.stroke_preserve()
            cr.fill()
            cr.restore()

        # Layer 2: White contour outline (#FFFFFF)
        cr.save()
        cr.translate(start_x, start_y)
        PangoCairo.layout_path(cr, layout)
        cr.set_source_rgb(*white_color)
        cr.set_line_width(white_w)
        cr.stroke_preserve()
        cr.fill()
        cr.restore()

        # Layer 3: Wine red core fill (#851733)
        cr.save()
        cr.translate(start_x, start_y)
        PangoCairo.layout_path(cr, layout)
        cr.set_source_rgb(*wine_color)
        cr.fill()
        cr.restore()

        return False


class DesktopCalendarWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Calendar Widget")
        self.set_name("desktop-calendar-window")
        self.set_decorated(False)
        self.set_resizable(False)

        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_namespace(self, "desktop-widgets")
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.BOTTOM)
            GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, False)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, False)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, 28)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 408)
            GtkLayerShell.set_exclusive_zone(self, 0)
        else:
            self.set_wmclass("desktop-widgets", "desktop-widgets")
            self.set_position(Gtk.WindowPosition.NONE)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        self.set_app_paintable(True)
        self.connect("draw", on_window_draw_clear)

        today = datetime.date.today()
        self._cached_today = today
        self._view_year = today.year
        self._view_month = today.month

        self.build_ui()

        # Periodic check for midnight date rollover every 30 seconds
        GLib.timeout_add_seconds(30, self.on_check_date_tick)

    def build_ui(self):
        card_event = Gtk.EventBox()
        card_event.set_visible_window(False)

        card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card_box.get_style_context().add_class("desktop-widget-card")
        card_box.get_style_context().add_class("widget-calendar-card")
        card_box.set_size_request(269, -1)

        card_event.connect("enter-notify-event", lambda w, e: card_box.get_style_context().add_class("card-hover"))
        card_event.connect("leave-notify-event", lambda w, e: card_box.get_style_context().remove_class("card-hover"))

        # Row 1: Hero Month/Year Header (Sunset Gradient with 3D Month & Prev/Next buttons)
        hero_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        hero_box.get_style_context().add_class("tactile-hero-box")

        # Top row: CALENDAR on left, Year on right
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        title_event = Gtk.EventBox()
        title_event.set_visible_window(False)
        title_event.connect("button-press-event", self.on_reset_today)
        lbl_title = Gtk.Label()
        lbl_title.get_style_context().add_class("calendar-hero-title")
        lbl_title.set_markup(f"<span font='9.5' weight='800' color='{C_BG_WAYBAR}'>CALENDAR</span>")
        lbl_title.set_halign(Gtk.Align.START)
        lbl_title.set_valign(Gtk.Align.CENTER)
        title_event.add(lbl_title)
        top_row.pack_start(title_event, False, False, 0)

        self.lbl_year = Gtk.Label()
        self.lbl_year.get_style_context().add_class("calendar-hero-title")
        self.lbl_year.set_markup(f"<span font='10' weight='800' color='{C_BG_WAYBAR}'>{self._view_year}</span>")
        self.lbl_year.set_halign(Gtk.Align.END)
        self.lbl_year.set_valign(Gtk.Align.CENTER)
        top_row.pack_end(self.lbl_year, False, False, 0)

        hero_box.pack_start(top_row, False, False, 0)

        # Main row: [ ❮ ]   [ Tactile 3D Month ]   [ ❯ ]
        month_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)

        btn_prev = Gtk.EventBox()
        btn_prev.set_visible_window(False)
        btn_prev.get_style_context().add_class("calendar-nav-btn")
        lbl_prev = Gtk.Label()
        lbl_prev.set_markup(f"<span font='13' weight='900' color='{C_BG_WAYBAR}'>❮</span>")
        btn_prev.add(lbl_prev)
        btn_prev.connect("button-press-event", self.on_prev_month)

        month_event = Gtk.EventBox()
        month_event.set_visible_window(False)
        month_event.set_size_request(130, 38)
        month_event.connect("button-press-event", self.on_reset_today)

        self.tactile_month = Tactile3DMonthWidget(MONTHS_EN[self._view_month - 1])
        month_event.add(self.tactile_month)

        btn_next = Gtk.EventBox()
        btn_next.set_visible_window(False)
        btn_next.get_style_context().add_class("calendar-nav-btn")
        lbl_next = Gtk.Label()
        lbl_next.set_markup(f"<span font='13' weight='900' color='{C_BG_WAYBAR}'>❯</span>")
        btn_next.add(lbl_next)
        btn_next.connect("button-press-event", self.on_next_month)

        month_row.pack_start(btn_prev, False, False, 0)
        month_row.pack_start(month_event, True, True, 0)
        month_row.pack_end(btn_next, False, False, 0)

        hero_box.pack_start(month_row, False, False, 1)

        card_box.pack_start(hero_box, False, False, 2)

        # Row 2: Monthly Calendar Grid Container
        grid_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        grid_container.get_style_context().add_class("tactile-calendar-box")

        # 7-Column Day Grid
        self.cal_grid = Gtk.Grid()
        self.cal_grid.set_column_homogeneous(True)
        self.cal_grid.set_row_homogeneous(True)
        self.cal_grid.set_column_spacing(2)
        self.cal_grid.set_row_spacing(2)

        self.rebuild_calendar_grid()
        grid_container.pack_start(self.cal_grid, True, True, 0)

        card_box.pack_start(grid_container, False, False, 2)
        card_event.add(card_box)
        self.add(card_event)

    def update_month_title(self):
        month_str = MONTHS_EN[self._view_month - 1]
        self.tactile_month.set_month(month_str)
        self.lbl_year.set_markup(f"<span font='10' weight='800' color='{C_BG_WAYBAR}'>{self._view_year}</span>")

    def rebuild_calendar_grid(self):
        for child in self.cal_grid.get_children():
            self.cal_grid.remove(child)

        days_headers = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']
        for col_idx, d_name in enumerate(days_headers):
            lbl = Gtk.Label()
            lbl.get_style_context().add_class("calendar-day-header")
            if col_idx >= 5:
                lbl.set_markup(f"<span font='8.5' weight='800' color='{C_ACCENT}'>{d_name}</span>")
            else:
                lbl.set_markup(f"<span font='8.5' weight='800' color='{C_BG_WAYBAR}'>{d_name}</span>")
            self.cal_grid.attach(lbl, col_idx, 0, 1, 1)

        cal = calendar.Calendar(firstweekday=0)
        weeks = cal.monthdatescalendar(self._view_year, self._view_month)
        today = datetime.date.today()

        for row_idx, week in enumerate(weeks):
            for col_idx, d in enumerate(week):
                cell_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                cell_lbl = Gtk.Label()

                is_today = (d == today)
                is_curr_month = (d.month == self._view_month)

                if is_today:
                    cell_box.get_style_context().add_class("calendar-cell-today")
                    cell_lbl.set_markup(f"<span font='9' weight='800' color='{C_TEXT_INV}'>{d.day}</span>")
                elif is_curr_month:
                    cell_box.get_style_context().add_class("calendar-cell-current")
                    if col_idx >= 5:
                        cell_lbl.set_markup(f"<span font='9' weight='700' color='{C_ACCENT}'>{d.day}</span>")
                    else:
                        cell_lbl.set_markup(f"<span font='9' weight='700' color='{C_BORDER_3D}'>{d.day}</span>")
                else:
                    cell_box.get_style_context().add_class("calendar-cell-other")
                    cell_lbl.set_markup(f"<span font='9' weight='500' color='{C_TEXT_MUT}'>{d.day}</span>")

                cell_box.set_size_request(28, 20)
                cell_lbl.set_halign(Gtk.Align.CENTER)
                cell_lbl.set_valign(Gtk.Align.CENTER)
                cell_box.pack_start(cell_lbl, True, True, 0)
                self.cal_grid.attach(cell_box, col_idx, row_idx + 1, 1, 1)

        self.cal_grid.show_all()

    def on_prev_month(self, widget, event):
        if event.button == 1:
            if self._view_month == 1:
                self._view_month = 12
                self._view_year -= 1
            else:
                self._view_month -= 1
            self.update_month_title()
            self.rebuild_calendar_grid()
            return True
        return False

    def on_next_month(self, widget, event):
        if event.button == 1:
            if self._view_month == 12:
                self._view_month = 1
                self._view_year += 1
            else:
                self._view_month += 1
            self.update_month_title()
            self.rebuild_calendar_grid()
            return True
        return False

    def on_reset_today(self, widget, event):
        if event.button == 1:
            today = datetime.date.today()
            self._view_year = today.year
            self._view_month = today.month
            self.update_month_title()
            self.rebuild_calendar_grid()
            return True
        return False

    def on_check_date_tick(self):
        today = datetime.date.today()
        if today != self._cached_today:
            self._cached_today = today
            self._view_year = today.year
            self._view_month = today.month
            self.update_month_title()
            self.rebuild_calendar_grid()
        return True


def setup_lifecycle():
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception as e:
        print(f"[desktop_widgets] Warning: Failed to write PID file: {e}", file=sys.stderr)

    def sig_handler(sig, frame):
        try:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
        except Exception:
            pass
        GLib.idle_add(Gtk.main_quit)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)
    try:
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
    except Exception:
        pass

def main():
    setup_lifecycle()
    apply_global_css()

    avatar_win = ProfileCardWindow()
    weather_win = WeatherForecastWindow()
    calendar_win = DesktopCalendarWindow()

    avatar_win.show_all()
    weather_win.show_all()
    calendar_win.show_all()

    Gtk.main()

if __name__ == "__main__":
    main()
