#!/usr/bin/env python3
# tracker/utils.py — Shared constants, formatting, and URL/app helpers for app_tracker.

import os
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
CLR_TEXT = "\033[38;2;255;240;245m"      # #FFF0F5 Tactile Cream
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
    "\033[38;2;255;92;138m",  # Pokepuff Pink
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
