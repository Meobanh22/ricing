#!/usr/bin/env python3
# ==============================================================================
# 🌸 SERENA REAL NOTIFICATION RECORDER DAEMON
# ==============================================================================
# Eavesdrops on DBus org.freedesktop.Notifications to capture live notifications
# and maintains ~/.cache/serena_notifications.json for Serena Control Center.
# ==============================================================================

import os
import sys
import time
import json
import signal

if "DBUS_SESSION_BUS_ADDRESS" not in os.environ and os.path.exists(f"/run/user/{os.getuid()}/bus"):
    os.environ["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{os.getuid()}/bus"

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

CACHE_FILE = os.path.expanduser("~/.cache/serena_notifications.json")
PID_FILE = "/tmp/serena_notif_daemon.pid"

MAX_NOTIFICATIONS = 20

def ensure_cache_file():
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    if not os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
        except Exception:
            pass

def load_notifications():
    ensure_cache_file()
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_notifications(notifs):
    ensure_cache_file()
    temp_file = CACHE_FILE + ".tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(notifs[:MAX_NOTIFICATIONS], f, ensure_ascii=False, indent=2)
        os.replace(temp_file, CACHE_FILE)
    except Exception as e:
        print(f"Error saving notifications: {e}", file=sys.stderr)

def map_app_name(raw_name, summary, body):
    if not raw_name or raw_name.strip() == "":
        # Check summary/body clues
        combined = (summary + " " + body).lower()
        if "update" in combined or "patch" in combined:
            return "System"
        return "Notification"
    
    # Prettify common app names
    low = raw_name.lower()
    if "code" in low:
        return "VS Code"
    elif "discord" in low:
        return "Discord"
    elif "spotify" in low:
        return "Spotify"
    elif "firefox" in low:
        return "Firefox"
    elif "chrome" in low or "edge" in low:
        return "Browser"
    elif "slack" in low:
        return "Slack"
    elif "telegram" in low:
        return "Telegram"
    elif "terminal" in low or "kitty" in low or "alacritty" in low:
        return "Terminal"
    return raw_name

def on_notify_call(msg):
    try:
        args = msg.get_args_list()
        if len(args) < 5:
            return

        raw_app_name = str(args[0])
        replaces_id = int(args[1])
        app_icon = str(args[2])
        summary = str(args[3])
        body = str(args[4])

        # Ignore empty summary and body
        if not summary and not body:
            return

        app_name = map_app_name(raw_app_name, summary, body)
        
        notif_item = {
            "id": int(time.time() * 1000),
            "app_name": app_name,
            "raw_app": raw_app_name,
            "summary": summary,
            "body": body,
            "icon": app_icon,
            "timestamp": int(time.time())
        }

        notifs = load_notifications()
        # Prepend to list
        notifs.insert(0, notif_item)
        save_notifications(notifs)
    except Exception as e:
        print(f"Error in on_notify_call: {e}", file=sys.stderr)

def on_close_all_call(msg):
    try:
        save_notifications([])
    except Exception:
        pass

def main():
    # Check single instance
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, 0)
            # Already running
            print(f"Daemon already running with PID {old_pid}")
            return
        except (OSError, ValueError):
            pass

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    def handle_exit(signum, frame):
        try:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_exit)
    signal.signal(signal.SIGINT, handle_exit)

    DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()

    # Eavesdrop method calls to Notify
    bus.add_match_string_non_blocking("type='method_call',interface='org.freedesktop.Notifications',member='Notify',eavesdrop='true'")
    bus.add_match_string_non_blocking("type='method_call',interface='org.freedesktop.Notifications',member='CloseAllNotifications',eavesdrop='true'")
    bus.add_match_string_non_blocking("type='method_call',interface='org.erikreider.swaync.cc',member='CloseAllNotifications',eavesdrop='true'")

    def message_filter(bus, msg):
        member = msg.get_member()
        if member == "Notify":
            on_notify_call(msg)
        elif member == "CloseAllNotifications":
            on_close_all_call(msg)

    bus.add_message_filter(message_filter)

    loop = GLib.MainLoop()
    try:
        loop.run()
    finally:
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass

if __name__ == "__main__":
    main()

