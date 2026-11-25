#!/usr/bin/env python3
# panels/weather_widget.py — Top-right tactile 3D weather forecast widget.

import datetime
import json
import os
import sys
import threading
import time
import urllib.parse
import urllib.request

import cairo
from gi.repository import GLib, Gtk, PangoCairo

from panels.common import (
    WINE_RED,
    DARK_RUBY,
    PURE_WHITE,
    MUTED_PINK,
    HAS_LAYER_SHELL,
    GtkLayerShell,
    on_window_draw_clear,
)
from panels.weather_service import (
    get_user_location,
    get_weather_icon,
    parse_forecast_day,
    parse_open_meteo_forecast,
)
from ui_core import draw_tactile_3d_text


class Tactile3DTemperatureWidget(Gtk.DrawingArea):
    """Renders 3D cel-shaded temperature digits directly onto Cairo."""

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

        ink_rect, _ = layout.get_pixel_extents()
        start_x = -ink_rect.x + 4.0
        start_y = -ink_rect.y + 4.0

        draw_tactile_3d_text(
            cr,
            layout,
            start_x,
            start_y,
            core_color=WINE_RED,
            dark_color=DARK_RUBY,
            white_color=PURE_WHITE,
            extrusion_h=4.0,
            white_w=4.6,
            dark_extra=1.6,
        )
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
        threading.Thread(target=self.fetch_weather_async, daemon=True).start()
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

        hero_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        hero_box.get_style_context().add_class("tactile-hero-box")
        hero_box.get_style_context().add_class("gradient-sunset")

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        top_row.get_style_context().add_class("weather-hero-top-row")

        self.lbl_title = Gtk.Label()
        self.lbl_title.get_style_context().add_class("weather-hero-title")
        self.lbl_title.set_markup(f"<span font='9.5' weight='800' color='{WINE_RED}'>WEATHER</span>")
        self.lbl_title.set_halign(Gtk.Align.START)
        self.lbl_title.set_valign(Gtk.Align.CENTER)
        top_row.pack_start(self.lbl_title, False, False, 0)

        self.lbl_hero_icon = Gtk.Label()
        self.lbl_hero_icon.get_style_context().add_class("weather-hero-icon")
        self.lbl_hero_icon.set_markup(f"<span font='50' color='{WINE_RED}'>󰼱</span>")
        self.lbl_hero_icon.set_halign(Gtk.Align.END)
        self.lbl_hero_icon.set_valign(Gtk.Align.CENTER)
        top_row.pack_end(self.lbl_hero_icon, False, False, 0)

        hero_box.pack_start(top_row, False, False, 0)
        self.tactile_temp = Tactile3DTemperatureWidget("--", "°C")
        hero_box.pack_start(self.tactile_temp, False, False, 2)
        card_box.pack_start(hero_box, False, False, 2)

        forecast_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        forecast_box.get_style_context().add_class("weather-forecast-container")
        forecast_box.set_halign(Gtk.Align.FILL)
        forecast_box.set_homogeneous(True)

        self.forecast_items = []
        for _ in range(3):
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            col.get_style_context().add_class("tactile-col-box")

            lbl_day = Gtk.Label()
            lbl_day.get_style_context().add_class("forecast-col-day")
            lbl_day.set_markup(f"<span font='9.5' weight='700' color='{WINE_RED}'>---</span>")

            lbl_ico = Gtk.Label()
            lbl_ico.get_style_context().add_class("forecast-col-icon")
            lbl_ico.set_markup(f"<span font='16' color='{WINE_RED}'>󰖙</span>")

            lbl_temp = Gtk.Label()
            lbl_temp.get_style_context().add_class("forecast-col-temp")
            lbl_temp.set_markup(f"<span font='9' color='{WINE_RED}'>--° --°</span>")

            col.pack_start(lbl_day, False, False, 0)
            col.pack_start(lbl_ico, False, False, 1)
            col.pack_start(lbl_temp, False, False, 1)
            forecast_box.pack_start(col, True, True, 0)
            self.forecast_items.append((lbl_day, lbl_ico, lbl_temp))

        card_box.pack_start(forecast_box, False, False, 2)
        card_event.add(card_box)
        self.add(card_event)
        self.load_cached_weather()

    def load_cached_weather(self):
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
                        temp_c, icon, _, fl = parse_open_meteo_forecast(fc)
                        self._update_weather_ui_direct(temp_c, icon, fl)
                        return True
                except Exception as e:
                    print(f"[desktop_widgets] Cache read error for {cp}: {e}", file=sys.stderr)
        return False

    def on_weather_card_clicked(self, widget, event):
        if event.button == 1:
            threading.Thread(target=self.fetch_weather_async, args=(True,), daemon=True).start()
            return True
        return False

    def on_periodic_weather_timer(self):
        threading.Thread(target=self.fetch_weather_async, daemon=True).start()
        return True

    def fetch_weather_async(self, force_refresh=False):
        if self._fetching_weather:
            return
        now = time.time()
        if now - self._last_weather_fetch < 5 and not force_refresh:
            return

        self._fetching_weather = True
        self._last_weather_fetch = now
        lat, lon, city = get_user_location(force_refresh=force_refresh)
        success = False

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
                try:
                    out_cache = os.path.expanduser("~/.cache/desktop_weather_cache.json")
                    with open(out_cache, "w", encoding="utf-8") as f:
                        json.dump(data, f)
                except Exception:
                    pass
                success = True
        except Exception as e:
            print(f"[desktop_widgets] Open-Meteo fetch error: {e}", file=sys.stderr)

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
                    icon = get_weather_icon(desc, datetime.datetime.now().hour)
                    GLib.idle_add(self._update_weather_ui_direct, temp_c, icon, forecast_list, city, desc)
                    success = True
            except Exception as e:
                print(f"[desktop_widgets] wttr.in fetch error: {e}", file=sys.stderr)

        if not success:
            GLib.idle_add(self._update_weather_fallback)

        self._fetching_weather = False

    def _update_weather_ui_direct(self, temp_c, icon, forecast_list=None, city=None, desc=None):
        if hasattr(self, 'lbl_hero_icon'):
            self.lbl_hero_icon.set_markup(f"<span font='50' color='{WINE_RED}'>{icon}</span>")
        if hasattr(self, 'tactile_temp'):
            self.tactile_temp.set_temperature(temp_c, "°C")

        if forecast_list and hasattr(self, 'forecast_items'):
            for idx, item_data in enumerate(forecast_list):
                if idx < len(self.forecast_items):
                    lbl_day, lbl_ico, lbl_temp = self.forecast_items[idx]
                    lbl_day.set_markup(f"<span font='9.5' weight='700' color='{WINE_RED}'>{item_data['day']}</span>")
                    lbl_ico.set_markup(f"<span font='16' color='{WINE_RED}'>{item_data['icon']}</span>")
                    lbl_temp.set_markup(
                        f"<span font='9' weight='700' color='{WINE_RED}'>{item_data['max']}°</span> "
                        f"<span font='8.5' color='{MUTED_PINK}'>{item_data['min']}°</span>"
                    )
        return False

    def _update_weather_fallback(self):
        if hasattr(self, 'tactile_temp') and "--" in self.tactile_temp.get_text():
            self.tactile_temp.set_temperature("Offline", "")
        return False
