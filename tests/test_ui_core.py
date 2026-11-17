#!/usr/bin/env python3
# test_ui_core.py — Unit test suite for ui_core primitives.

import os
import sys
import unittest
import cairo
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Pango, PangoCairo

# Add repository scripts directory to path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "config", "hypr", "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from ui_core import (
    get_repo_root, resolve_asset,
    clear_surface, draw_rounded_rect, squircle, clip_device_bounds,
    draw_bow_mark, draw_bell_icon,
    draw_curved_kerned, draw_curved_kerned_cached, clear_text_cache,
    draw_tactile_3d_text, DraggablePopup,
    draw_pokeball_dual_slider, format_relative_time, get_badge_info
)


class TestUiCoreAssets(unittest.TestCase):
    def test_repo_root_discovery(self):
        root = get_repo_root()
        self.assertTrue(os.path.isdir(root))
        self.assertTrue(os.path.exists(os.path.join(root, "config", "theme", "tokens.json")))

    def test_resolve_existing_asset(self):
        p = resolve_asset("serena_ribbon_bow_clean.png")
        self.assertTrue(os.path.exists(p), f"Failed to resolve existing asset: {p}")

    def test_resolve_subfolder_asset(self):
        p = resolve_asset("serena_cover_banner.png")
        self.assertTrue(os.path.exists(p), f"Failed to resolve banner asset: {p}")

    def test_resolve_nonexistent_asset(self):
        p = resolve_asset("non_existent_asset_xyz.png")
        self.assertEqual(p, "")


class TestUiCoreShapes(unittest.TestCase):
    def setUp(self):
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 100, 100)
        self.cr = cairo.Context(self.surface)

    def test_clear_surface(self):
        # Draw something first
        self.cr.set_source_rgba(1, 0, 0, 1)
        self.cr.paint()
        clear_surface(self.cr)
        # Verify surface is cleared (transparent)
        data = self.surface.get_data()
        self.assertEqual(data[0], 0)

    def test_draw_rounded_rect(self):
        draw_rounded_rect(self.cr, 10, 10, 80, 80, 8)
        self.cr.set_source_rgba(0, 1, 0, 1)
        self.cr.fill()

    def test_squircle_alias(self):
        squircle(self.cr, 5, 5, 50, 50, 5)
        self.cr.fill()

    def test_clip_device_bounds(self):
        clip_device_bounds(self.cr, 0, 0, 50, 50, 4)

    def test_draw_bow_mark(self):
        draw_bow_mark(self.cr, 50, 50, size=24.0)

    def test_draw_bell_icon(self):
        draw_bell_icon(self.cr, 50, 50, font_size=16)


class TestUiCoreTypography(unittest.TestCase):
    def setUp(self):
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 200, 100)
        self.cr = cairo.Context(self.surface)

    def test_draw_curved_kerned(self):
        draw_curved_kerned(self.cr, "TEST TEXT", 100, 80, r_text=60.0)

    def test_draw_curved_kerned_cached(self):
        clear_text_cache()
        draw_curved_kerned_cached(self.cr, "CACHED", 100, 80, r_text=60.0)
        # Call again to exercise cache retrieval
        draw_curved_kerned_cached(self.cr, "CACHED", 100, 80, r_text=60.0)


class TestUiCoreTactile(unittest.TestCase):
    def setUp(self):
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 150, 60)
        self.cr = cairo.Context(self.surface)

    def test_draw_tactile_3d_text(self):
        layout = PangoCairo.create_layout(self.cr)
        layout.set_text("24°C", -1)
        draw_tactile_3d_text(self.cr, layout, 10.0, 10.0, extrusion_h=4.0)


class TestUiCoreDraggable(unittest.TestCase):
    def test_draggable_bounds_clamping(self):
        win = Gtk.Window()
        drag = DraggablePopup(win, name="test_drag", default_pos=(100, 100))
        # Test within bounds
        cx, cy = drag.clamp_bounds(50, 50)
        self.assertGreaterEqual(cx, 10)
        self.assertGreaterEqual(cy, 10)
        # Test out of bounds clamping
        cx, cy = drag.clamp_bounds(-100, -200)
        self.assertEqual(cx, 10)
        self.assertEqual(cy, 10)


class TestUiCoreComponents(unittest.TestCase):
    def setUp(self):
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 200, 200)
        self.cr = cairo.Context(self.surface)

    def test_draw_pokeball_dual_slider(self):
        draw_pokeball_dual_slider(self.cr, 100, 100, R=64.0, vol_val=0.5, bri_val=0.7)

    def test_format_relative_time(self):
        import time
        now = time.time()
        self.assertEqual(format_relative_time(now - 10), "just now")
        self.assertEqual(format_relative_time(now - 120), "2m ago")
        self.assertEqual(format_relative_time(now - 7200), "2h ago")
        self.assertEqual(format_relative_time(now - 172800), "2d ago")

    def test_get_badge_info(self):
        col, icon = get_badge_info("Discord")
        self.assertEqual(col, "#5865F2")
        self.assertEqual(icon, "󰙯")

        col, icon = get_badge_info("Kitty")
        self.assertEqual(icon, "󰆍")

        col, icon = get_badge_info("unknown_app")
        self.assertEqual(icon, "󰒓")


if __name__ == "__main__":
    unittest.main()
