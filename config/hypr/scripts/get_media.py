#!/usr/bin/env python3
# get_media.py — MPRIS music status module for Waybar.
import subprocess
import json
import html

def get_output(cmd):
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=1)
        return res.stdout.strip()
    except Exception:
        return ""

def main():
    status = get_output(["playerctl", "status"])
    if not status or status == "None" or status == "Stopped":
        print(json.dumps({"text": "", "tooltip": "No music playing", "class": "stopped"}, ensure_ascii=False))
        return

    raw_title = get_output(["playerctl", "metadata", "--format", "{{title}}"])
    raw_artist = get_output(["playerctl", "metadata", "--format", "{{artist}}"])

    # Truncate cleanly by Unicode codepoints (never slice multi-byte UTF-8 bytes)
    max_len = 20
    if raw_title:
        title = raw_title[:max_len] + ("…" if len(raw_title) > max_len else "")
    else:
        title = "Playing" if status == "Playing" else "Paused"

    # Escape HTML/Pango markup entities (&, <, >) to prevent GTK crashes
    safe_title = html.escape(title)
    safe_artist = html.escape(raw_artist) if raw_artist else ""

    if status == "Playing":
        icon = ""
        cls = "playing"
        tooltip = f"{safe_artist} - {safe_title}" if safe_artist else safe_title
    elif status == "Paused":
        icon = "󰐎"
        cls = "paused"
        tooltip = f"Paused: {safe_title}"
    else:
        icon = ""
        cls = "stopped"
        tooltip = "No music playing"

    print(json.dumps({
        "text": f"{icon} {safe_title}",
        "tooltip": tooltip,
        "class": cls
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
