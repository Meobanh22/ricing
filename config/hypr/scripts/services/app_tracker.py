#!/usr/bin/env python3
# app_tracker.py — Lightweight Hyprland application & web usage tracker CLI entrypoint.

import argparse
import datetime
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from tracker.browser import FirefoxTabResolver  # noqa: E402,F401
from tracker.cli_report import (  # noqa: E402
    aggregate_apps,
    draw_stacked_distribution,  # noqa: F401
    get_term_layout,
    print_all_web_pages,
    print_app_details,
    print_combined_dashboard,
)
from tracker.daemon import (  # noqa: E402
    HyprlandAppTracker,
    is_daemon_running,
    show_status,
    start_daemon,
    stop_daemon,
)
from tracker.db import TrackerDB  # noqa: E402
from tracker.utils import (  # noqa: E402
    CLR_ACCENT,
    CLR_RESET,
    CLR_TEXT,
    CLR_WARNING,
    clean_app_name,  # noqa: F401
    clean_window_title,  # noqa: F401
    format_duration,  # noqa: F401
    get_boot_id,
    get_domain,  # noqa: F401
    get_uptime_seconds,
    is_browser_app,  # noqa: F401
)


def main():
    parser = argparse.ArgumentParser(
        description="Hyprland Application & Web Time Usage Tracker",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="session",
        choices=["session", "today", "web", "details", "daemon", "start", "stop", "restart", "status", "live"],
        help="Action to execute:\n"
             "  session  : Combined App + Web usage for current boot session (Default)\n"
             "  today    : Combined App + Web usage for today\n"
             "  web      : Show full web browsing history with links for current session\n"
             "  details  : Show window titles / tabs / links breakdown for a specific app\n"
             "  start    : Start background tracking daemon\n"
             "  stop     : Stop background tracking daemon\n"
             "  restart  : Restart background tracking daemon\n"
             "  status   : Check background daemon status and uptime\n"
             "  live     : Full-terminal real-time monitor (like htop)",
    )
    parser.add_argument("target", nargs="?", default=None, help="Target application class (e.g. firefox, code)")

    args = parser.parse_args()

    if args.command == "daemon":
        tracker = HyprlandAppTracker()
        tracker.run()
        return

    if args.command == "start":
        start_daemon(os.path.abspath(__file__))
        return

    if args.command == "stop":
        stop_daemon()
        return

    if args.command == "restart":
        stop_daemon()
        time.sleep(0.5)
        start_daemon(os.path.abspath(__file__))
        return

    if args.command == "status":
        show_status()
        return

    if not is_daemon_running() and args.command not in ("daemon", "stop", "status"):
        print(f"{CLR_WARNING}⚠️  App Tracker daemon is not running. Starting daemon...{CLR_RESET}")
        start_daemon(os.path.abspath(__file__))
        time.sleep(0.5)

    db = TrackerDB()
    boot_id = get_boot_id()
    uptime = get_uptime_seconds()

    if args.command == "session":
        _, lines, _, _, _, _ = get_term_layout()
        app_stats = db.get_session_stats(boot_id)
        grouped_count = len(aggregate_apps(app_stats))
        dynamic_limit = max(5, lines - grouped_count - 18)
        web_stats = db.get_top_web_titles(boot_id=boot_id, limit=dynamic_limit)
        print_combined_dashboard("SESSION USAGE REPORT (CURRENT BOOT)", app_stats, web_stats=web_stats, total_uptime=uptime)

    elif args.command == "today":
        today_str = datetime.date.today().isoformat()
        _, lines, _, _, _, _ = get_term_layout()
        app_stats = db.get_today_stats(today_str)
        grouped_count = len(aggregate_apps(app_stats))
        dynamic_limit = max(5, lines - grouped_count - 18)
        web_stats = db.get_top_web_titles(date_str=today_str, limit=dynamic_limit)
        print_combined_dashboard(f"DAILY USAGE REPORT ({today_str})", app_stats, web_stats=web_stats, total_uptime=None)

    elif args.command == "web":
        all_web = db.get_top_web_titles(boot_id=boot_id, limit=100)
        print_all_web_pages(all_web)

    elif args.command == "details":
        if not args.target:
            print(f"{CLR_ACCENT}Please specify an application class. Example: {CLR_TEXT}apptime details firefox{CLR_RESET}")
            return
        details = db.get_app_details(args.target, boot_id=boot_id)
        print_app_details(args.target, details)

    elif args.command == "live":
        sys.stdout.write("\033[?1049h\033[H\033[?25l")
        sys.stdout.flush()
        try:
            while True:
                sys.stdout.write("\033[H\033[2J")
                _, lines, _, _, _, _ = get_term_layout()
                app_stats = db.get_session_stats(boot_id)
                grouped_count = len(aggregate_apps(app_stats))
                dynamic_limit = max(5, lines - grouped_count - 18)
                web_stats = db.get_top_web_titles(boot_id=boot_id, limit=dynamic_limit)
                current_uptime = get_uptime_seconds()
                print_combined_dashboard("LIVE USAGE MONITOR (Ctrl+C to exit)", app_stats, web_stats=web_stats, total_uptime=current_uptime)
                time.sleep(2)
        except KeyboardInterrupt:
            pass
        finally:
            sys.stdout.write("\033[?1049l\033[?25h")
            sys.stdout.flush()

    db.close()


if __name__ == "__main__":
    main()
