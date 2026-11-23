#!/usr/bin/env python3
# get_media.py — MPRIS music status module for Waybar.
import subprocess
import json
import html

def main():
    try:
        res = subprocess.run(
            ["playerctl", "metadata", "--format", "{{status}}\t{{title}}\t{{artist}}"],
            capture_output=True, text=True, errors="replace", timeout=1
        )
        line = res.stdout.strip()
    except Exception:
        line = ""

    if not line:
        print(json.dumps({"text": "", "tooltip": "", "class": "stopped"}, ensure_ascii=False))
        return

    parts = line.split("\t")
    status = parts[0] if len(parts) > 0 else "Stopped"
    raw_title = parts[1] if len(parts) > 1 else ""
    raw_artist = parts[2] if len(parts) > 2 else ""

    if not status or status == "Stopped" or (not raw_title and status != "Playing"):
        print(json.dumps({"text": "", "tooltip": "", "class": "stopped"}, ensure_ascii=False))
        return

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

    if status == "Playing":
        icon = ""
        cls = "playing"
    elif status == "Paused":
        icon = "󰐎"
        cls = "paused"
    else:
        print(json.dumps({"text": "", "tooltip": "", "class": "stopped"}, ensure_ascii=False))
        return

    # NOTE: Output raw unescaped text because Waybar's custom module has "escape": true,
    # which uses GLib/Pango g_markup_escape_text to safely escape markup entities without double-escaping.
    print(json.dumps({
        "text": f"{icon} {title}",
        "tooltip": "",
        "class": cls
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
