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

    # Unescape HTML entities from browser MPRIS (e.g. &amp;, &#39;, &#x27;)
    if raw_title:
        raw_title = html.unescape(raw_title)
    if raw_artist:
        raw_artist = html.unescape(raw_artist)

    # Truncate cleanly by Unicode codepoints (never slice multi-byte UTF-8 bytes)
    max_len = 20
    if raw_title:
        title = raw_title[:max_len] + ("…" if len(raw_title) > max_len else "")
    else:
        title = "Playing" if status == "Playing" else "Paused"

    artist = raw_artist if raw_artist else ""

    if status == "Playing":
        icon = ""
        cls = "playing"
        tooltip = f"{artist} - {raw_title}" if artist and raw_title else (raw_title or title)
    elif status == "Paused":
        icon = "󰐎"
        cls = "paused"
        tooltip = f"Paused: {artist} - {raw_title}" if artist and raw_title else f"Paused: {raw_title or title}"
    else:
        icon = ""
        cls = "stopped"
        tooltip = "No music playing"

    # NOTE: Output raw unescaped text because Waybar's custom module has "escape": true,
    # which uses GLib/Pango g_markup_escape_text to safely escape markup entities without double-escaping.
    print(json.dumps({
        "text": f"{icon} {title}",
        "tooltip": tooltip,
        "class": cls
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
