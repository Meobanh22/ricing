#!/usr/bin/env python3
# notif_helpers.py — Notification formatting and badge helpers.

import time
from typing import Tuple

try:
    from system.palette import C_ACCENT
except Exception:
    C_ACCENT = "#DC1A36"


def format_relative_time(timestamp: float) -> str:
    """Formats a UNIX timestamp into relative time string ('just now', '5m ago', '2h ago')."""
    if not timestamp:
        return "just now"
    now = time.time()
    diff = max(0, int(now - timestamp))
    if diff < 60:
        return "just now"
    elif diff < 3600:
        mins = diff // 60
        return f"{mins}m ago"
    elif diff < 86400:
        hours = diff // 3600
        return f"{hours}h ago"
    else:
        days = diff // 86400
        return f"{days}d ago"


def get_badge_info(app_name: str) -> Tuple[str, str]:
    """Returns (color, icon_glyph) for known applications and system fallbacks."""
    app_lower = (app_name or "").lower()
    if "discord" in app_lower:
        return "#5865F2", "󰙯"
    elif "firefox" in app_lower or "browser" in app_lower:
        return "#FF7139", "󰈹"
    elif "spotify" in app_lower or "music" in app_lower:
        return "#1ED760", "󰓇"
    elif "steam" in app_lower:
        return "#1b2838", "󰓓"
    elif "terminal" in app_lower or "alacritty" in app_lower or "kitty" in app_lower:
        return C_ACCENT, "󰆍"
    return C_ACCENT, "󰒓"
