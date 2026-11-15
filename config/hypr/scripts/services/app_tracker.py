#!/usr/bin/env python3
# app_tracker.py — Lightweight Hyprland application & web usage tracker and analytics daemon.
# Tracks active window duration and web browsing per boot session and per day using Hyprland socket2 IPC.

import os
import sys
import time
import datetime
import socket
import select
import sqlite3
import subprocess
import signal
import argparse
import json
import shutil
import struct
import glob
import urllib.parse

# === PATHS & CONFIGURATION ===
DATA_DIR = os.path.expanduser("~/.local/share/app_tracker")
DB_PATH = os.path.join(DATA_DIR, "usage.db")
PID_FILE = os.path.join(DATA_DIR, "tracker.pid")
LOG_FILE = os.path.join(DATA_DIR, "tracker.log")

IDLE_TIMEOUT_SECONDS = 300  # 5 minutes without cursor/window movement -> Idle
FLUSH_INTERVAL_SECONDS = 10  # Save to SQLite every 10 seconds

# Serena Wine Palette ANSI escape codes
CLR_ACCENT = "\033[38;2;220;26;54m"      # #DC1A36 Ruby Accent
CLR_TEXT = "\033[38;2;255;240;245m"       # #FFF0F5 Tactile Cream
CLR_MUTED = "\033[38;2;166;133;149m"     # #A68595 Muted Rose
CLR_SECONDARY = "\033[38;2;232;194;208m" # #E8C2D0 Secondary Text
CLR_SUCCESS = "\033[38;2;143;188;143m"   # #8FBC8F Sage Green
CLR_WARNING = "\033[38;2;255;184;108m"   # #FFB86C Pastel Orange
CLR_CYAN = "\033[38;2;135;240;255m"      # #87F0FF Screen Cyan
CLR_BOLD = "\033[1m"
CLR_RESET = "\033[0m"

# Distinct palette colors for row chart bars
PALETTE_COLORS = [
    "\033[38;2;220;26;54m",   # Ruby Accent
    "\033[38;2;80;166;255m",  # Ribbon Blue
    "\033[38;2;143;188;143m", # Sage Green
    "\033[38;2;255;184;108m", # Pastel Orange
    "\033[38;2;135;240;255m", # Screen Cyan
    "\033[38;2;255;92;138m",  # Poképuff Pink
    "\033[38;2;232;194;208m", # Secondary Rose
]


def get_boot_id() -> str:
    """Read current Linux kernel boot ID."""
    try:
        with open("/proc/sys/kernel/random/boot_id", "r") as f:
            return f.read().strip()
    except Exception:
        return "default-session"


def get_uptime_seconds() -> float:
    """Read total uptime in seconds from /proc/uptime."""
    try:
        with open("/proc/uptime", "r") as f:
            return float(f.readline().split()[0])
    except Exception:
        return 0.0


def format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration (Xh Ym Zs)."""
    s = int(round(seconds))
    if s < 60:
        return f"{s:02d}s"
    m = s // 60
    s = s % 60
    if m < 60:
        return f"{m:02d}m {s:02d}s"
    h = m // 60
    m = m % 60
    return f"{h}h {m:02d}m {s:02d}s"


def clean_app_name(raw_class: str) -> str:
    """Clean common desktop app class prefixes for display."""
    if not raw_class:
        return "Unknown"
    replacements = {
        "com.microsoft.VSCode": "VS Code",
        "code-oss": "VS Code OSS",
        "code": "VS Code",
        "org.telegram.desktop": "Telegram",
        "org.mozilla.firefox": "Firefox",
        "firefox": "Firefox",
        "kitty": "Kitty",
        "alacritty": "Alacritty",
        "foot": "Foot",
        "Spotify": "Spotify",
        "spotify": "Spotify",
        "discord": "Discord",
        "vesktop": "Vesktop",
        "org.pulseaudio.pavucontrol": "Pavucontrol",
        "pavucontrol": "Pavucontrol",
        "thunar": "Thunar",
        "nautilus": "Nautilus",
        "google-chrome": "Google Chrome",
        "brave-browser": "Brave",
    }
    return replacements.get(raw_class, raw_class)


def clean_window_title(title: str, app_class: str = "") -> str:
    """Strip browser and editor window suffixes for cleaner presentation."""
    if not title:
        return ""
    suffixes = [
        " — Mozilla Firefox",
        " - Mozilla Firefox",
        " — Google Chrome",
        " - Google Chrome",
        " — Brave",
        " - Brave",
        " - Visual Studio Code",
        " — Visual Studio Code",
        " - Code",
        " — Chromium",
    ]
    cleaned = title.strip()
    for s in suffixes:
        if cleaned.endswith(s):
            cleaned = cleaned[:-len(s)].strip()
            break
    return cleaned


def is_browser_app(app_class: str) -> bool:
    """Check if app class belongs to a web browser."""
    c = app_class.lower()
    return any(b in c for b in ("firefox", "chrome", "brave", "chromium", "zen", "vivaldi", "opera", "edge"))


def make_hyperlink(url: str, text: str) -> str:
    """Wrap text in an OSC 8 terminal hyperlink supported by modern terminals (Kitty, Alacritty)."""
    if not url:
        return text
    return f"\x1b]8;;{url}\x1b\\{text}\x1b]8;;\x1b\\"


def get_domain(url: str) -> str:
    """Extract clean domain name from URL."""
    if not url:
        return ""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.netloc:
            return parsed.netloc
        if parsed.scheme:
            return f"{parsed.scheme}:{parsed.path}"
        return url[:24]
    except Exception:
        return ""


# === FIREFOX ACTIVE TAB & URL RESOLVER ===
class FirefoxTabResolver:
    """Extracts URLs and tab titles from Firefox's sessionstore without any extension or CPU overhead."""

    @staticmethod
    def decompress_mozlz4(raw_bytes: bytes) -> bytes:
        """Decompress Mozilla mozlz4 headered raw LZ4 payload in pure Python."""
        if len(raw_bytes) < 12 or raw_bytes[:8] != b"mozLz40\0":
            return b""
        uncompressed_size = struct.unpack("<I", raw_bytes[8:12])[0]
        compressed = raw_bytes[12:]
        dest = bytearray(uncompressed_size)
        src_pos, dest_pos = 0, 0
        c_len = len(compressed)

        try:
            while src_pos < c_len and dest_pos < uncompressed_size:
                token = compressed[src_pos]
                src_pos += 1
                lit_len = token >> 4
                if lit_len == 15:
                    while src_pos < c_len:
                        extra = compressed[src_pos]
                        src_pos += 1
                        lit_len += extra
                        if extra != 255:
                            break
                dest[dest_pos : dest_pos + lit_len] = compressed[src_pos : src_pos + lit_len]
                dest_pos += lit_len
                src_pos += lit_len
                if dest_pos >= uncompressed_size:
                    break
                offset = compressed[src_pos] | (compressed[src_pos + 1] << 8)
                src_pos += 2
                match_len = (token & 0x0F) + 4
                if match_len == 19:
                    while src_pos < c_len:
                        extra = compressed[src_pos]
                        src_pos += 1
                        match_len += extra
                        if extra != 255:
                            break
                for _ in range(match_len):
                    dest[dest_pos] = dest[dest_pos - offset]
                    dest_pos += 1
            return bytes(dest)
        except Exception:
            return bytes(dest[:dest_pos])

    @classmethod
    def get_open_tabs(cls) -> dict:
        """Scan Firefox profile sessionstore files and return {title: url} map."""
        results = {}
        patterns = [
            os.path.expanduser("~/.config/mozilla/firefox/*default*/sessionstore-backups/recovery.jsonlz4"),
            os.path.expanduser("~/.mozilla/firefox/*default*/sessionstore-backups/recovery.jsonlz4"),
            os.path.expanduser("~/.config/mozilla/firefox/*default*/sessionstore-backups/recovery.baklz4"),
            os.path.expanduser("~/.mozilla/firefox/*default*/sessionstore-backups/recovery.baklz4"),
        ]
        files = []
        for p in patterns:
            files.extend(glob.glob(p))

        for fpath in files:
            try:
                with open(fpath, "rb") as f:
                    raw = f.read()
                dec = cls.decompress_mozlz4(raw)
                if not dec:
                    continue
                data = json.loads(dec.decode("utf-8", errors="ignore"))
                for w in data.get("windows", []):
                    for tab in w.get("tabs", []):
                        idx = tab.get("index", 1) - 1
                        entries = tab.get("entries", [])
                        if 0 <= idx < len(entries):
                            cur = entries[idx]
                            title = cur.get("title", "").strip()
                            url = cur.get("url", "").strip()
                            if title and url:
                                results[title] = url
                                # Also map cleaned title
                                clean_t = clean_window_title(title, "firefox")
                                if clean_t:
                                    results[clean_t] = url
            except Exception:
                pass
        return results

    @staticmethod
    def guess_url_from_title(title: str) -> str:
        """Heuristic fallback for common sites if tab was closed."""
        t = title.lower()
        if "gemini" in t:
            return "https://gemini.google.com"
        if "chatgpt" in t:
            return "https://chatgpt.com"
        if "youtube" in t:
            return "https://youtube.com"
        if "github" in t:
            return "https://github.com"
        if "reddit" in t:
            return "https://reddit.com"
        if "google search" in t:
            return "https://google.com"
        if "facebook" in t:
            return "https://facebook.com"
        if "add-ons for firefox" in t or "addons" in t:
            return "https://addons.mozilla.org"
        if "about:processes" in t or "process manager" in t:
            return "about:processes"
        if "about:addons" in t or "add-ons manager" in t:
            return "about:addons"
        return ""


# === DATABASE MANAGER ===
class TrackerDB:
    def __init__(self, db_path=DB_PATH):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, timeout=10.0)
        self.conn.execute("PRAGMA journal_mode = WAL;")
        self.conn.execute("PRAGMA synchronous = NORMAL;")
        self._init_tables()

    def _init_tables(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS app_usage (
                    boot_id TEXT,
                    date TEXT,
                    app_class TEXT,
                    total_seconds REAL DEFAULT 0,
                    PRIMARY KEY (boot_id, date, app_class)
                );
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS app_titles (
                    boot_id TEXT,
                    date TEXT,
                    app_class TEXT,
                    title TEXT,
                    total_seconds REAL DEFAULT 0,
                    url TEXT DEFAULT '',
                    PRIMARY KEY (boot_id, date, app_class, title)
                );
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS boot_meta (
                    boot_id TEXT PRIMARY KEY,
                    boot_time REAL,
                    first_seen REAL,
                    last_seen REAL
                );
            """)
            try:
                self.conn.execute("ALTER TABLE app_titles ADD COLUMN url TEXT DEFAULT '';")
            except Exception:
                pass

    def record_usage(self, boot_id: str, date_str: str, app_class: str, title: str, seconds: float, url: str = ""):
        if seconds <= 0:
            return
        now = time.time()
        title_trimmed = (title or "")[:200].strip()

        with self.conn:
            self.conn.execute("""
                INSERT INTO app_usage (boot_id, date, app_class, total_seconds)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(boot_id, date, app_class)
                DO UPDATE SET total_seconds = total_seconds + excluded.total_seconds;
            """, (boot_id, date_str, app_class, seconds))

            if title_trimmed:
                self.conn.execute("""
                    INSERT INTO app_titles (boot_id, date, app_class, title, total_seconds, url)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(boot_id, date, app_class, title)
                    DO UPDATE SET 
                        total_seconds = total_seconds + excluded.total_seconds,
                        url = CASE WHEN excluded.url != '' THEN excluded.url ELSE app_titles.url END;
                """, (boot_id, date_str, app_class, title_trimmed, seconds, url))

            self.conn.execute("""
                INSERT INTO boot_meta (boot_id, boot_time, first_seen, last_seen)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(boot_id)
                DO UPDATE SET last_seen = excluded.last_seen;
            """, (boot_id, now - get_uptime_seconds(), now, now))

    def get_session_stats(self, boot_id: str):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT app_class, SUM(total_seconds) as total
            FROM app_usage
            WHERE boot_id = ?
            GROUP BY app_class
            ORDER BY total DESC;
        """, (boot_id,))
        return cursor.fetchall()

    def get_today_stats(self, date_str: str):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT app_class, SUM(total_seconds) as total
            FROM app_usage
            WHERE date = ?
            GROUP BY app_class
            ORDER BY total DESC;
        """, (date_str,))
        return cursor.fetchall()

    def get_top_web_titles(self, boot_id: str = None, date_str: str = None, limit: int = 8):
        cursor = self.conn.cursor()
        query = """
            SELECT app_class, title, SUM(total_seconds) as total, MAX(url) as saved_url
            FROM app_titles
            WHERE (app_class LIKE '%firefox%' OR app_class LIKE '%chrome%' OR app_class LIKE '%brave%' OR app_class LIKE '%chromium%' OR app_class LIKE '%zen%')
        """
        params = []
        if boot_id:
            query += " AND boot_id = ?"
            params.append(boot_id)
        elif date_str:
            query += " AND date = ?"
            params.append(date_str)

        query += " GROUP BY title ORDER BY total DESC LIMIT 60;"
        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Query live Firefox session tabs for real URLs
        live_tabs = FirefoxTabResolver.get_open_tabs()

        results = []
        seen = set()
        for app_cls, title, duration, saved_url in rows:
            clean = clean_window_title(title, app_cls)
            low = clean.lower()
            if not clean or low in ("mozilla firefox", "firefox", "google chrome", "brave", "new tab", "tab mới"):
                continue
            if clean in seen:
                continue
            seen.add(clean)

            # Match URL: 1. saved_url -> 2. live session tab -> 3. heuristic guess
            resolved_url = saved_url or ""
            if not resolved_url:
                resolved_url = live_tabs.get(clean) or live_tabs.get(title) or ""
            if not resolved_url:
                resolved_url = FirefoxTabResolver.guess_url_from_title(clean)

            domain = get_domain(resolved_url)
            results.append((app_cls, clean, duration, resolved_url, domain))
            if len(results) >= limit:
                break
        return results

    def get_app_details(self, app_class: str, boot_id: str = None, date_str: str = None):
        cursor = self.conn.cursor()
        query = """
            SELECT title, SUM(total_seconds) as total, MAX(url) as saved_url
            FROM app_titles
            WHERE (app_class = ? OR app_class LIKE ?)
        """
        params = [app_class, f"%{app_class}%"]
        if boot_id:
            query += " AND boot_id = ?"
            params.append(boot_id)
        elif date_str:
            query += " AND date = ?"
            params.append(date_str)

        query += " GROUP BY title ORDER BY total DESC LIMIT 40;"
        cursor.execute(query, params)
        rows = cursor.fetchall()

        live_tabs = FirefoxTabResolver.get_open_tabs() if is_browser_app(app_class) else {}
        results = []
        for title, duration, saved_url in rows:
            clean = clean_window_title(title, app_class)
            resolved_url = saved_url or live_tabs.get(clean) or live_tabs.get(title) or FirefoxTabResolver.guess_url_from_title(clean)
            results.append((title, duration, resolved_url))
        return results

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass


# === DAEMON IMPLEMENTATION ===
class HyprlandAppTracker:
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
            res = subprocess.run(["pidof", "hyprlock"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return res.returncode == 0
        except Exception:
            return False

    def _check_afk(self):
        if self._is_screen_locked():
            self.is_afk = True
            return

        try:
            out = subprocess.check_output(["hyprctl", "cursorpos"], timeout=0.5).decode("utf-8").strip()
            pos = tuple(int(x.strip()) for x in out.split(",") if x.strip().isdigit())
            if len(pos) == 2:
                if self.last_cursor_pos != pos:
                    self.last_cursor_pos = pos
                    self.last_activity_time = time.monotonic()
                    self.is_afk = False
                elif (time.monotonic() - self.last_activity_time) > IDLE_TIMEOUT_SECONDS:
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
                tabs = FirefoxTabResolver.get_open_tabs()
                clean_t = clean_window_title(self.current_title, self.current_class)
                url = tabs.get(clean_t) or tabs.get(self.current_title) or FirefoxTabResolver.guess_url_from_title(clean_t)
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


# === RESPONSIVE LAYOUT & CLI FORMATTING ===
def get_term_layout():
    """Dynamically determine terminal dimensions and column widths to fit terminal frame."""
    cols, lines = shutil.get_terminal_size((80, 24))
    w = max(cols - 2, 58)
    app_w = min(22, max(14, int(w * 0.22)))
    bar_w = max(12, w - (app_w + 23) - 4)
    web_bar_w = min(22, max(10, int(w * 0.22)))
    web_title_w = max(24, w - web_bar_w - 22)
    return w, lines, app_w, bar_w, web_title_w, web_bar_w


def draw_stacked_distribution(items: list, width: int = 50) -> tuple:
    """Draw a continuous horizontal distribution bar with a colored legend."""
    total = sum(x[1] for x in items)
    if total <= 0:
        return f"[{'░' * width}]", ""

    segments = []
    allocated = 0
    legend_parts = []

    for i, (name, dur) in enumerate(items):
        clr = PALETTE_COLORS[i % len(PALETTE_COLORS)]
        pct = (dur / total) * 100.0
        seg_len = int(round((dur / total) * width))
        segments.append((name, dur, seg_len, clr))
        allocated += seg_len
        legend_parts.append(f"{clr}■{CLR_RESET} {name} ({pct:.1f}%)")

    diff = width - allocated
    if segments:
        name, dur, seg_len, clr = segments[0]
        segments[0] = (name, dur, max(0, seg_len + diff), clr)

    bar_str = "["
    for _, _, seg_len, clr in segments:
        if seg_len > 0:
            bar_str += f"{clr}{'█' * seg_len}"
    bar_str += f"{CLR_RESET}]"

    legend_str = "   ".join(legend_parts[:4])
    return bar_str, legend_str


def aggregate_apps(raw_stats: list) -> list:
    """Group apps by their friendly display name to prevent duplicates (e.g. code vs com.microsoft.VSCode)."""
    agg = {}
    for app_class, duration in raw_stats:
        name = clean_app_name(app_class)
        agg[name] = agg.get(name, 0.0) + duration
    return sorted(agg.items(), key=lambda x: x[1], reverse=True)


def print_combined_dashboard(title: str, app_stats: list, web_stats: list = None, total_uptime: float = None):
    w, lines, app_w, bar_w, web_title_w, web_bar_w = get_term_layout()

    print()
    print(f"{CLR_ACCENT}┌{'─' * (w - 2)}┐{CLR_RESET}")
    print(f"{CLR_ACCENT}│{CLR_RESET}  {CLR_BOLD}{CLR_TEXT}{title.center(w - 6)}{CLR_RESET}  {CLR_ACCENT}│{CLR_RESET}")
    print(f"{CLR_ACCENT}└{'─' * (w - 2)}┘{CLR_RESET}")

    grouped_apps = aggregate_apps(app_stats)
    total_tracked = sum(s[1] for s in grouped_apps)

    if total_uptime and total_uptime > 0:
        idle_time = max(0.0, total_uptime - total_tracked)
        tracked_pct = (total_tracked / total_uptime) * 100.0 if total_uptime > 0 else 0.0
        idle_pct = (idle_time / total_uptime) * 100.0 if total_uptime > 0 else 0.0
        print(f"  {CLR_CYAN}🖥  System Uptime:{CLR_RESET}     {CLR_BOLD}{format_duration(total_uptime)}{CLR_RESET}")
        print(f"  {CLR_SUCCESS}📊 Active Apps:{CLR_RESET}       {CLR_BOLD}{format_duration(total_tracked)}{CLR_RESET} ({tracked_pct:.1f}% of total uptime)")
        print(f"  {CLR_MUTED}💤 Idle / Desktop:{CLR_RESET}    {CLR_BOLD}{format_duration(idle_time)}{CLR_RESET} ({idle_pct:.1f}%)")
    else:
        print(f"  {CLR_SUCCESS}📊 Total App Time:{CLR_RESET}    {CLR_BOLD}{format_duration(total_tracked)}{CLR_RESET}")

    print()
    if not grouped_apps:
        print(f"  {CLR_MUTED}No application activity recorded yet.{CLR_RESET}")
        print(f"  {CLR_MUTED}Ensure the daemon is running: {CLR_TEXT}apptime start{CLR_RESET}\n")
        return

    # Section 1: Stacked Horizontal Distribution Bar
    stacked_width = max(16, w - 8)
    stacked_bar, legend = draw_stacked_distribution(grouped_apps, width=stacked_width)
    print(f"  {CLR_BOLD}{CLR_TEXT}📈 USAGE DISTRIBUTION (ROW OVERVIEW){CLR_RESET}")
    print(f"  {stacked_bar}")
    if legend:
        print(f"  {CLR_MUTED}{legend}{CLR_RESET}")
    print()

    # Section 2: Desktop Apps (Horizontal Row Chart)
    print(f"  {CLR_BOLD}{CLR_TEXT}📱 DESKTOP APPLICATIONS (ROW CHART){CLR_RESET}")
    print(f"  {CLR_MUTED}{'APPLICATION':<{app_w}} {'TIME':<9} {'USAGE CHART':<{bar_w + 2}}  {'SHARE'}{CLR_RESET}")
    print(f"  {CLR_MUTED}{'─' * (w - 4)}{CLR_RESET}")

    base_time = total_tracked if total_tracked > 0 else 1.0

    for i, (friendly_name, duration) in enumerate(grouped_apps, start=0):
        pct = (duration / base_time) * 100.0
        row_clr = PALETTE_COLORS[i % len(PALETTE_COLORS)]
        filled_len = int(round(bar_w * (pct / 100.0)))
        filled_len = max(0, min(bar_w, filled_len))
        empty_len = bar_w - filled_len
        bar = f"{row_clr}{'█' * filled_len}{CLR_MUTED}{'░' * empty_len}{CLR_RESET}"
        time_str = format_duration(duration)

        print(f"  {CLR_BOLD}{CLR_TEXT}{friendly_name[:app_w]:<{app_w}}{CLR_RESET} {CLR_CYAN}{time_str:<8}{CLR_RESET} │{bar}│  {CLR_SECONDARY}{pct:>5.1f}%{CLR_RESET}")

    # Section 3: Web Browsing Activity (Horizontal Row Chart with Link & Domain)
    if web_stats:
        total_web_time = sum(w[2] for w in web_stats)
        base_web = total_web_time if total_web_time > 0 else 1.0
        print()
        print(f"  {CLR_BOLD}{CLR_TEXT}🌐 TOP WEBSITES & LINKS (ROW CHART · CLICK TO OPEN){CLR_RESET}")
        print(f"  {CLR_MUTED}{'WEBSITE / DOMAIN':<{web_title_w}} {'TIME':<9} {'USAGE CHART':<{web_bar_w + 2}}  {'SHARE'}{CLR_RESET}")
        print(f"  {CLR_MUTED}{'─' * (w - 4)}{CLR_RESET}")

        for j, (app_cls, clean_title, duration, url, domain) in enumerate(web_stats, start=0):
            # Display: Title (domain) if domain available
            if domain:
                display_label = f"{clean_title[:web_title_w - len(domain) - 4]} ({domain})"
            else:
                display_label = clean_title[:web_title_w - 2]

            pct = (duration / base_web) * 100.0
            row_clr = PALETTE_COLORS[j % len(PALETTE_COLORS)]
            filled_len = int(round(web_bar_w * (pct / 100.0)))
            filled_len = max(0, min(web_bar_w, filled_len))
            empty_len = web_bar_w - filled_len
            bar = f"{row_clr}{'█' * filled_len}{CLR_MUTED}{'░' * empty_len}{CLR_RESET}"
            time_str = format_duration(duration)

            # Make title clickable hyperlink if url available
            padded_label = f"{display_label:<{web_title_w}}"
            if url:
                clickable_title = make_hyperlink(url, f"{CLR_TEXT}{padded_label}{CLR_RESET}")
            else:
                clickable_title = f"{CLR_TEXT}{padded_label}{CLR_RESET}"

            print(f"  {clickable_title} {CLR_CYAN}{time_str:<8}{CLR_RESET} │{bar}│  {CLR_SECONDARY}{pct:>5.1f}%{CLR_RESET}")

    print(f"  {CLR_MUTED}{'─' * (w - 4)}{CLR_RESET}")
    print(f"  {CLR_MUTED}💡 Commands: {CLR_TEXT}apptime web{CLR_MUTED} (all links) | {CLR_TEXT}apptime details <app>{CLR_MUTED} | {CLR_TEXT}apptime live{CLR_RESET}\n")


def print_app_details(app_name: str, details: list):
    w, lines, app_w, bar_w, web_title_w, web_bar_w = get_term_layout()
    title_w = max(24, int(w * 0.40))
    url_w = max(22, w - title_w - 18)

    print()
    print(f"{CLR_ACCENT}┌{'─' * (w - 2)}┐{CLR_RESET}")
    title_str = f"APPLICATION DETAILS: {clean_app_name(app_name).upper()}"
    print(f"{CLR_ACCENT}│{CLR_RESET}  {CLR_BOLD}{CLR_TEXT}{title_str.center(w - 6)}{CLR_RESET}  {CLR_ACCENT}│{CLR_RESET}")
    print(f"{CLR_ACCENT}└{'─' * (w - 2)}┘{CLR_RESET}")

    if not details:
        print(f"\n  {CLR_MUTED}No detailed history found for: {CLR_TEXT}{app_name}{CLR_RESET}\n")
        return

    total_time = sum(d[1] for d in details)
    print(f"  {CLR_SUCCESS}📊 Total Tracked Time:{CLR_RESET} {CLR_BOLD}{format_duration(total_time)}{CLR_RESET}\n")

    print(f"  {CLR_MUTED}{'#':<3} {'WINDOW TITLE / WEBPAGE':<{title_w}} {'LINK / URL':<{url_w}} {'TIME'}{CLR_RESET}")
    print(f"  {CLR_MUTED}{'─' * (w - 4)}{CLR_RESET}")

    for i, (title, duration, url) in enumerate(details, start=1):
        clean_title = clean_window_title(title, app_name)
        if not clean_title:
            clean_title = "(Untitled Window)"
        clean_title = clean_title[:title_w - 2]
        time_str = format_duration(duration)

        clean_url = url if url else "-"
        clean_url_disp = clean_url[:url_w - 2]

        padded_t = f"{clean_title:<{title_w}}"
        if url:
            click_t = make_hyperlink(url, f"{CLR_TEXT}{padded_t}{CLR_RESET}")
            click_u = make_hyperlink(url, f"{CLR_CYAN}{clean_url_disp:<{url_w}}{CLR_RESET}")
        else:
            click_t = f"{CLR_TEXT}{padded_t}{CLR_RESET}"
            click_u = f"{CLR_MUTED}{clean_url_disp:<{url_w}}{CLR_RESET}"

        print(f"  {CLR_MUTED}{i:<3}{CLR_RESET} {click_t} {click_u} {CLR_CYAN}{time_str}{CLR_RESET}")

    print(f"  {CLR_MUTED}{'─' * (w - 4)}{CLR_RESET}\n")


def print_all_web_pages(web_stats: list):
    w, lines, app_w, bar_w, web_title_w, web_bar_w = get_term_layout()
    title_w = max(24, int(w * 0.40))
    url_w = max(22, w - title_w - 18)

    print()
    print(f"{CLR_ACCENT}┌{'─' * (w - 2)}┐{CLR_RESET}")
    title_str = "WEB BROWSING HISTORY (CURRENT SESSION)"
    print(f"{CLR_ACCENT}│{CLR_RESET}  {CLR_BOLD}{CLR_TEXT}{title_str.center(w - 6)}{CLR_RESET}  {CLR_ACCENT}│{CLR_RESET}")
    print(f"{CLR_ACCENT}└{'─' * (w - 2)}┘{CLR_RESET}")

    if not web_stats:
        print(f"\n  {CLR_MUTED}No web browsing activity recorded yet.{CLR_RESET}\n")
        return

    total_web_time = sum(w[2] for w in web_stats)
    print(f"  {CLR_SUCCESS}📊 Total Browsing Time:{CLR_RESET} {CLR_BOLD}{format_duration(total_web_time)}{CLR_RESET}\n")

    print(f"  {CLR_MUTED}{'#':<3} {'WEBSITE / TAB TITLE':<{title_w}} {'LINK / DOMAIN':<{url_w}} {'TIME'}{CLR_RESET}")
    print(f"  {CLR_MUTED}{'─' * (w - 4)}{CLR_RESET}")

    for i, (app_cls, title, duration, url, domain) in enumerate(web_stats, start=1):
        clean_t = title[:title_w - 2]
        time_str = format_duration(duration)

        link_disp = domain if domain else (url[:url_w - 2] if url else "-")
        link_disp = link_disp[:url_w - 2]

        padded_t = f"{clean_t:<{title_w}}"
        if url:
            click_t = make_hyperlink(url, f"{CLR_TEXT}{padded_t}{CLR_RESET}")
            click_u = make_hyperlink(url, f"{CLR_CYAN}{link_disp:<{url_w}}{CLR_RESET}")
        else:
            click_t = f"{CLR_TEXT}{padded_t}{CLR_RESET}"
            click_u = f"{CLR_MUTED}{link_disp:<{url_w}}{CLR_RESET}"

        print(f"  {CLR_MUTED}{i:<3}{CLR_RESET} {click_t} {click_u} {CLR_CYAN}{time_str}{CLR_RESET}")

    print(f"  {CLR_MUTED}{'─' * (w - 4)}{CLR_RESET}\n")


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


def start_daemon():
    if is_daemon_running():
        print(f"{CLR_WARNING}⚠️  App Tracker daemon is already running.{CLR_RESET}")
        return

    os.makedirs(DATA_DIR, exist_ok=True)
    script_path = os.path.abspath(__file__)
    with open(LOG_FILE, "a") as log:
        subprocess.Popen(
            [sys.executable, script_path, "daemon"],
            stdout=log,
            stderr=log,
            start_new_session=True
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


# === ENTRYPOINT ===
def main():
    parser = argparse.ArgumentParser(
        description="Hyprland Application & Web Time Usage Tracker",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("command", nargs="?", default="session",
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
                             "  live     : Full-terminal real-time monitor (like htop)")
    parser.add_argument("target", nargs="?", default=None, help="Target application class (e.g. firefox, code)")

    args = parser.parse_args()

    if args.command == "daemon":
        tracker = HyprlandAppTracker()
        tracker.run()
        return

    if args.command == "start":
        start_daemon()
        return

    if args.command == "stop":
        stop_daemon()
        return

    if args.command == "restart":
        stop_daemon()
        time.sleep(0.5)
        start_daemon()
        return

    if args.command == "status":
        show_status()
        return

    if not is_daemon_running() and args.command not in ("daemon", "stop", "status"):
        print(f"{CLR_WARNING}⚠️  App Tracker daemon is not running. Starting daemon...{CLR_RESET}")
        start_daemon()
        time.sleep(0.5)

    db = TrackerDB()
    boot_id = get_boot_id()
    uptime = get_uptime_seconds()

    if args.command == "session":
        w, lines, _, _, _, _ = get_term_layout()
        app_stats = db.get_session_stats(boot_id)
        grouped_count = len(aggregate_apps(app_stats))
        dynamic_limit = max(5, lines - grouped_count - 18)
        web_stats = db.get_top_web_titles(boot_id=boot_id, limit=dynamic_limit)
        print_combined_dashboard("SESSION USAGE REPORT (CURRENT BOOT)", app_stats, web_stats=web_stats, total_uptime=uptime)

    elif args.command == "today":
        today_str = datetime.date.today().isoformat()
        w, lines, _, _, _, _ = get_term_layout()
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
        # Enter alternate screen buffer & hide cursor for full-terminal experience
        sys.stdout.write("\033[?1049h\033[H\033[?25l")
        sys.stdout.flush()
        try:
            while True:
                sys.stdout.write("\033[H\033[2J")  # Clear screen and return cursor to top-left
                w, lines, _, _, _, _ = get_term_layout()
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
            # Restore normal screen buffer & show cursor
            sys.stdout.write("\033[?1049l\033[?25h")
            sys.stdout.flush()

    db.close()


if __name__ == "__main__":
    main()
