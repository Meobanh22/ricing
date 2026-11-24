#!/usr/bin/env python3
# test_tracker.py — Unit test suite for the modularized app_tracker package.

import os
import struct
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVICES_DIR = os.path.join(REPO_ROOT, "config", "hypr", "scripts", "services")
if SERVICES_DIR not in sys.path:
    sys.path.insert(0, SERVICES_DIR)

import app_tracker  # noqa: E402
from tracker.browser import FirefoxTabResolver  # noqa: E402
from tracker.cli_report import aggregate_apps, draw_stacked_distribution  # noqa: E402
from tracker.db import TrackerDB  # noqa: E402
from tracker.utils import (  # noqa: E402
    clean_app_name,
    clean_window_title,
    format_duration,
    get_domain,
    is_browser_app,
    make_hyperlink,
)


class TestTrackerUtils(unittest.TestCase):
    def test_format_duration(self):
        self.assertEqual(format_duration(9), "09s")
        self.assertEqual(format_duration(125), "02m 05s")
        self.assertEqual(format_duration(3661), "1h 01m 01s")

    def test_clean_app_name(self):
        self.assertEqual(clean_app_name("com.microsoft.VSCode"), "VS Code")
        self.assertEqual(clean_app_name("org.mozilla.firefox"), "Firefox")
        self.assertEqual(clean_app_name("custom-app"), "custom-app")
        self.assertEqual(clean_app_name(""), "Unknown")

    def test_clean_window_title(self):
        self.assertEqual(clean_window_title("Docs — Mozilla Firefox"), "Docs")
        self.assertEqual(clean_window_title("main.py - Visual Studio Code"), "main.py")
        self.assertEqual(clean_window_title("Plain Title"), "Plain Title")
        self.assertEqual(clean_window_title(""), "")

    def test_is_browser_app(self):
        self.assertTrue(is_browser_app("firefox"))
        self.assertTrue(is_browser_app("Brave-browser"))
        self.assertFalse(is_browser_app("kitty"))

    def test_get_domain_and_hyperlink(self):
        self.assertEqual(get_domain("https://github.com/user/repo"), "github.com")
        self.assertEqual(get_domain("about:addons"), "about:addons")
        self.assertEqual(get_domain(""), "")
        self.assertEqual(make_hyperlink("", "GitHub"), "GitHub")
        self.assertIn("\x1b]8;;https://github.com\x1b\\", make_hyperlink("https://github.com", "GitHub"))


class TestTrackerBrowser(unittest.TestCase):
    def test_decompress_mozlz4_invalid(self):
        self.assertEqual(FirefoxTabResolver.decompress_mozlz4(b"badheader"), b"")

    def test_decompress_mozlz4_literals(self):
        payload = b"hello world!"
        # Token: upper nibble = literal length (12 < 15), lower nibble = 0 (no match follows at end)
        token = len(payload) << 4
        raw = b"mozLz40\0" + struct.pack("<I", len(payload)) + bytes([token]) + payload
        self.assertEqual(FirefoxTabResolver.decompress_mozlz4(raw), payload)

    def test_guess_url_from_title(self):
        self.assertEqual(FirefoxTabResolver.guess_url_from_title("Open Pull Requests · GitHub"), "https://github.com")
        self.assertEqual(FirefoxTabResolver.guess_url_from_title("Unknown Local File"), "")


class TestTrackerDBAndReport(unittest.TestCase):
    def test_db_record_and_queries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "usage.db")
            db = TrackerDB(db_path=db_path)
            try:
                db.record_usage("boot-1", "2026-11-25", "firefox", "GitHub — Mozilla Firefox", 120.0, "https://github.com")
                db.record_usage("boot-1", "2026-11-25", "code", "app.py", 60.0)
                db.record_usage("boot-1", "2026-11-25", "kitty", "ignored", 0.0)

                session = db.get_session_stats("boot-1")
                self.assertEqual(session, [("firefox", 120.0), ("code", 60.0)])

                today = db.get_today_stats("2026-11-25")
                self.assertEqual(len(today), 2)

                web = db.get_top_web_titles(boot_id="boot-1")
                self.assertEqual(len(web), 1)
                self.assertEqual(web[0][3], "https://github.com")

                details = db.get_app_details("firefox", boot_id="boot-1")
                self.assertEqual(details, [("GitHub — Mozilla Firefox", 120.0, "https://github.com")])
            finally:
                db.close()

    def test_aggregate_apps_merges_aliases(self):
        raw = [("com.microsoft.VSCode", 40.0), ("code", 20.0), ("kitty", 30.0)]
        self.assertEqual(aggregate_apps(raw), [("VS Code", 60.0), ("Kitty", 30.0)])

    def test_draw_stacked_distribution(self):
        bar_empty, legend_empty = draw_stacked_distribution([], width=20)
        self.assertEqual(bar_empty, f"[{'░' * 20}]")
        self.assertEqual(legend_empty, "")

        bar, legend = draw_stacked_distribution([("Firefox", 75.0), ("Kitty", 25.0)], width=20)
        self.assertEqual(bar.count("█"), 20)
        self.assertIn("Firefox (75.0%)", legend)

    def test_entrypoint_reexports(self):
        self.assertIs(app_tracker.TrackerDB, TrackerDB)
        self.assertIs(app_tracker.format_duration, format_duration)


if __name__ == "__main__":
    unittest.main()
