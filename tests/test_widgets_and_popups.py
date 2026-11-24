#!/usr/bin/env python3
# test_widgets_and_popups.py — Unit test suite for extracted panels, control_center_pkg, shelf_pkg, and settings_pkg modules.

import os
import sys
import unittest
from unittest.mock import patch

import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "config", "hypr", "scripts")
WIDGETS_DIR = os.path.join(SCRIPTS_DIR, "widgets")
POPUPS_DIR = os.path.join(SCRIPTS_DIR, "popups")

for path in (SCRIPTS_DIR, WIDGETS_DIR, POPUPS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from control_center_pkg.shapes import (  # noqa: E402
    create_bottom_red_casing_path,
    create_top_red_casing_path,
    draw_pokeball_dual_slider,
    format_relative_time,
    get_badge_info,
)
from panels.weather_service import (  # noqa: E402
    get_weather_icon,
    parse_forecast_day,
    parse_open_meteo_forecast,
)
from settings_pkg.shapes import (  # noqa: E402
    draw_ribbon_bow,
    ellipse_path,
    front_cover_path,
    left_panel_path,
    right_panel_path,
)
from shelf_pkg.storage import ShelfStorageMixin  # noqa: E402


class TestWeatherService(unittest.TestCase):
    def test_get_weather_icon_day_vs_night(self):
        self.assertEqual(get_weather_icon("Clear sky", 12), "󰖙")
        self.assertEqual(get_weather_icon("Clear sky", 22), "󰼱")
        self.assertEqual(get_weather_icon("Thunderstorm", 14), "󰖓")
        self.assertEqual(get_weather_icon("Light rain", 14), "󰖗")
        self.assertEqual(get_weather_icon("Heavy snow", 14), "󰖘")
        self.assertEqual(get_weather_icon("Dense fog", 14), "󰖑")
        self.assertEqual(get_weather_icon("Overcast", 14), "󰖐")

    def test_parse_open_meteo_forecast(self):
        sample = {
            "current": {"is_day": 1, "weather_code": 61, "temperature_2m": 24.6},
            "daily": {
                "time": ["2026-11-25", "2026-11-26"],
                "weather_code": [0, 3],
                "temperature_2m_max": [27.2, 22.8],
                "temperature_2m_min": [19.4, 17.9],
            },
        }
        temp_c, icon, desc, forecast = parse_open_meteo_forecast(sample)
        self.assertEqual(temp_c, "25")
        self.assertEqual(icon, "󰖗")
        self.assertEqual(desc, "Light rain")
        self.assertEqual(len(forecast), 2)
        self.assertEqual(forecast[0]["day"], "Today")
        self.assertEqual(forecast[0]["max"], "27")
        self.assertEqual(forecast[1]["day"], "Thu")
        self.assertEqual(forecast[1]["full_desc"], "Overcast")

    def test_parse_forecast_day(self):
        day = {
            "date": "2026-11-26",
            "maxtempC": "26",
            "mintempC": "18",
            "hourly": [{"weatherDesc": [{"value": "Partly cloudy"}]}] * 5,
        }
        parsed = parse_forecast_day(day, 1)
        self.assertEqual(parsed["day"], "Thu")
        self.assertEqual(parsed["short_desc"], "P.Cloud")
        self.assertEqual(parsed["max"], "26")
        self.assertEqual(parsed["min"], "18")


class TestControlCenterShapes(unittest.TestCase):
    def test_format_relative_time(self):
        self.assertEqual(format_relative_time(0), "just now")
        with patch("time.time", return_value=10000.0):
            self.assertEqual(format_relative_time(9970.0), "just now")
            self.assertEqual(format_relative_time(9700.0), "5m ago")
            self.assertEqual(format_relative_time(2800.0), "2h ago")
        with patch("time.time", return_value=200000.0):
            self.assertEqual(format_relative_time(10000.0), "2d ago")

    def test_get_badge_info(self):
        self.assertEqual(get_badge_info("Discord")[1], "󰙯")
        self.assertEqual(get_badge_info("Mozilla Firefox")[1], "󰈹")
        self.assertEqual(get_badge_info("Spotify")[1], "󰓇")
        self.assertEqual(get_badge_info("kitty")[1], "󰆍")
        self.assertEqual(get_badge_info("UnknownApp")[1], "󰒓")

    def test_cairo_casing_and_slider_draw(self):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 420, 420)
        cr = cairo.Context(surface)
        create_top_red_casing_path(cr, 10.0, 410.0, 180.0, 210.0, 180.0, 60.0, 0.2, 2.9, 55.0, 18.0)
        cr.set_source_rgba(0.86, 0.1, 0.21, 1.0)
        cr.fill()
        create_bottom_red_casing_path(cr, 10.0, 410.0, 240.0, 420.0, 210.0, 240.0, 60.0, 0.2, 2.9, 55.0, 18.0)
        cr.fill()
        draw_pokeball_dual_slider(cr, 210.0, 210.0, vol_val=0.65, bri_val=0.80)
        self.assertTrue(any(surface.get_data()))


class TestShelfStorageHelpers(unittest.TestCase):
    def test_format_file_size(self):
        self.assertEqual(ShelfStorageMixin.format_file_size(512), "512B")
        self.assertEqual(ShelfStorageMixin.format_file_size(2048), "2KB")
        self.assertEqual(ShelfStorageMixin.format_file_size(5 * 1024 * 1024), "5.0MB")

    def test_clip_matches(self):
        mixin = ShelfStorageMixin()
        t1 = {"is_image": False, "full_text": "hello world"}
        t2 = {"is_image": False, "preview": "hello world"}
        t3 = {"is_image": False, "full_text": "different"}
        img1 = {"is_image": True, "id": "42", "raw": "42\t[[ binary ]]"}
        img2 = {"is_image": True, "id": "99", "raw": "42\t[[ binary ]]"}

        self.assertTrue(mixin._clip_matches(t1, t2))
        self.assertFalse(mixin._clip_matches(t1, t3))
        self.assertFalse(mixin._clip_matches(t1, img1))
        self.assertTrue(mixin._clip_matches(img1, img2))


class TestSettingsShapes(unittest.TestCase):
    def test_panel_paths_and_bow_render(self):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 480, 320)
        cr = cairo.Context(surface)
        left_panel_path(cr, 20.0, 20.0, 200.0, 280.0)
        cr.set_source_rgba(0.12, 0.06, 0.07, 1.0)
        cr.fill()
        right_panel_path(cr, 240.0, 20.0, 200.0, 280.0)
        cr.fill()
        front_cover_path(cr, 240.0, 20.0, 200.0, 280.0)
        cr.stroke()
        ellipse_path(cr, 240.0, 160.0, 18.0, 12.0)
        cr.fill()
        draw_ribbon_bow(cr, 240.0, 160.0, ribbon_ang=0.25, scale=0.9)
        self.assertTrue(any(surface.get_data()))


if __name__ == "__main__":
    unittest.main()
