#!/usr/bin/env python3
# tracker/daemon.py — Hyprland socket2 usage tracking daemon and process control.

import datetime
import json
import os
import select
import signal
import socket
import subprocess
import sys
import time

from tracker.browser import FirefoxTabResolver
from tracker.db import TrackerDB
from tracker.utils import (
    CLR_ACCENT,
    CLR_BOLD,
    CLR_MUTED,
    CLR_RESET,
    CLR_SUCCESS,
    CLR_WARNING,
    DATA_DIR,
    DB_PATH,
    FLUSH_INTERVAL_SECONDS,
    IDLE_TIMEOUT_SECONDS,
    LOG_FILE,
    PID_FILE,
    clean_window_title,
    format_duration,
    get_boot_id,
    get_uptime_seconds,
    is_browser_app,
)


class HyprlandAppTracker:
    """Monitors Hyprland activewindow events and records foreground duration."""

    def __init__(self):
        self.boot_id = get_boot_id()
        self.db = TrackerDB()
        self.running = True

        self.current_class = ""
        self.current_title = ""
        self.last_switch_time = time.monotonic()
        self.last_flush_time = time.monotonic()

        self.last_cursor_pos = None
        self.last_activity_time = time.monotonic()
        self.is_afk = False
        self.last_afk_check = 0.0
        self.cached_tabs = {}
        self.last_tabs_fetch = 0.0

        self.sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
        uid = os.getuid()
        runtime_dir = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{uid}")
        if self.sig:
            self.socket_path = os.path.join(runtime_dir, "hypr", self.sig, ".socket2.sock")
        else:
            self.socket_path = None

        self._fetch_initial_window()

    def _fetch_initial_window(self):
        try:
            out = subprocess.check_output(["hyprctl", "activewindow", "-j"], timeout=1.0)
            data = json.loads(out)
            self.current_class = data.get("class", "").strip()
            self.current_title = data.get("title", "").strip()
            self.last_switch_time = time.monotonic()
            self.last_activity_time = time.monotonic()
        except Exception:
            self.current_class = ""
            self.current_title = ""

    def _is_screen_locked(self) -> bool:
        try:
            for entry in os.scandir('/proc'):
                if entry.name.isdigit():
                    try:
                        with open(os.path.join(entry.path, 'comm'), 'r') as f:
                            if f.read().strip() == 'hyprlock':
                                return True
                    except (OSError, IOError):
                        continue
            return False
        except Exception:
            return False

    def _check_afk(self, force=False):
        now = time.monotonic()
        if not force and (now - self.last_afk_check) < 15.0:
            return
        self.last_afk_check = now

        if self._is_screen_locked():
            self.is_afk = True
            return

        try:
            out = subprocess.check_output(["hyprctl", "cursorpos"], timeout=0.5).decode("utf-8").strip()
            pos = tuple(int(x.strip()) for x in out.split(",") if x.strip().isdigit())
            if len(pos) == 2:
                if self.last_cursor_pos != pos:
                    self.last_cursor_pos = pos
                    self.last_activity_time = now
                    self.is_afk = False
                elif (now - self.last_activity_time) > IDLE_TIMEOUT_SECONDS:
                    self.is_afk = True
        except Exception:
            pass

    def _flush_current(self):
        now = time.monotonic()
        elapsed = now - self.last_switch_time
        self.last_switch_time = now

        if elapsed > 0 and self.current_class and not self.is_afk:
            today_str = datetime.date.today().isoformat()
            url = ""
            if is_browser_app(self.current_class):
                now_m = time.monotonic()
                if (now_m - self.last_tabs_fetch > 30.0) or (self.current_title not in self.cached_tabs):
                    self.cached_tabs = FirefoxTabResolver.get_open_tabs()
                    self.last_tabs_fetch = now_m
                clean_t = clean_window_title(self.current_title, self.current_class)
                url = self.cached_tabs.get(clean_t) or self.cached_tabs.get(self.current_title) or FirefoxTabResolver.guess_url_from_title(clean_t)
            self.db.record_usage(self.boot_id, today_str, self.current_class, self.current_title, elapsed, url=url)

    def _connect_socket(self):
        if not self.socket_path or not os.path.exists(self.socket_path):
            return None
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(self.socket_path)
            s.setblocking(False)
            return s
        except Exception:
            return None

    def run(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))

        def handle_signal(sig, frame):
            self.running = False

        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)

        sock = self._connect_socket()
        sock_buffer = ""

        try:
            while self.running:
                now = time.monotonic()
                self._check_afk()

                if now - self.last_flush_time >= FLUSH_INTERVAL_SECONDS:
                    self._flush_current()
                    self.last_flush_time = now

                if sock is None:
                    time.sleep(2.0)
                    sock = self._connect_socket()
                    continue

                readable, _, _ = select.select([sock], [], [], 1.0)
                if readable:
                    try:
                        chunk = sock.recv(4096).decode("utf-8", errors="ignore")
                        if not chunk:
                            sock.close()
                            sock = None
                            continue
                        sock_buffer += chunk

                        while "\n" in sock_buffer:
                            line, sock_buffer = sock_buffer.split("\n", 1)
                            line = line.strip()

                            if line.startswith("activewindow>>"):
                                payload = line[len("activewindow>>"):]
                                parts = payload.split(",", 1)
                                new_class = parts[0].strip()
                                new_title = parts[1].strip() if len(parts) > 1 else ""

                                self._flush_current()
                                self.current_class = new_class
                                self.current_title = new_title
                                self.last_switch_time = time.monotonic()
                                self.last_activity_time = time.monotonic()
                                self.is_afk = False

                    except (socket.error, OSError):
                        if sock:
                            sock.close()
                        sock = None

        finally:
            self._flush_current()
            self.db.close()
            if os.path.exists(PID_FILE):
                try:
                    os.remove(PID_FILE)
                except Exception:
                    pass


def is_daemon_running() -> bool:
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return True
        except (ValueError, OSError):
            return False
    return False


def start_daemon(script_path: str = None):
    if is_daemon_running():
        print(f"{CLR_WARNING}⚠️  App Tracker daemon is already running.{CLR_RESET}")
        return

    os.makedirs(DATA_DIR, exist_ok=True)
    if not script_path:
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app_tracker.py")
    with open(LOG_FILE, "a") as log:
        subprocess.Popen(
            [sys.executable, script_path, "daemon"],
            stdout=log,
            stderr=log,
            start_new_session=True,
        )

    time.sleep(0.5)
    if is_daemon_running():
        print(f"{CLR_SUCCESS}✅ App Tracker daemon started successfully.{CLR_RESET}")
    else:
        print(f"{CLR_ACCENT}❌ Failed to start daemon. Check log at: {LOG_FILE}{CLR_RESET}")


def stop_daemon():
    if not is_daemon_running():
        print(f"{CLR_MUTED}App Tracker daemon is currently stopped.{CLR_RESET}")
        return

    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
        time.sleep(0.5)
        print(f"{CLR_SUCCESS}✅ App Tracker daemon stopped.{CLR_RESET}")
    except Exception as e:
        print(f"{CLR_ACCENT}❌ Could not stop daemon: {e}{CLR_RESET}")


def show_status():
    running = is_daemon_running()
    status_str = f"{CLR_SUCCESS}RUNNING (Active){CLR_RESET}" if running else f"{CLR_MUTED}STOPPED (Inactive){CLR_RESET}"
    uptime = get_uptime_seconds()

    print(f"\n  {CLR_BOLD}App Tracker Status:{CLR_RESET}  {status_str}")
    print(f"  {CLR_BOLD}System Uptime:{CLR_RESET}       {format_duration(uptime)}")
    print(f"  {CLR_BOLD}Current Boot ID:{CLR_RESET}     {get_boot_id()[:8]}...")
    print(f"  {CLR_BOLD}Database Path:{CLR_RESET}       {DB_PATH}\n")
