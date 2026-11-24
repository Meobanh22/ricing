#!/usr/bin/env python3
# desktop_widgets.py — Pinned Desktop Background Widgets entrypoint for Hyprland.

import gc
import os
import signal
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from panels.common import (  # noqa: E402
    apply_global_css,
    get_repo_root,  # noqa: F401
    get_uptime_str,  # noqa: F401
    on_window_draw_clear,  # noqa: F401
)
from gi.repository import GLib, Gtk  # noqa: E402
from panels.calendar_widget import DesktopCalendarWindow, Tactile3DMonthWidget  # noqa: E402,F401
from panels.profile_card import ProfileCardWindow  # noqa: E402
from panels.weather_service import (  # noqa: E402,F401
    get_user_location,
    get_weather_icon,
    parse_forecast_day,
    parse_open_meteo_forecast,
)
from panels.weather_widget import Tactile3DTemperatureWidget, WeatherForecastWindow  # noqa: E402,F401

PID_FILE = "/tmp/desktop_widgets.pid"


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

    gc.collect()
    Gtk.main()


if __name__ == "__main__":
    main()
