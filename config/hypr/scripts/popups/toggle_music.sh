#!/usr/bin/env bash
# toggle_music.sh — Toggle music visualizer window.

SCRIPT_PATH="$HOME/.config/hypr/scripts/popups/music_visualizer.py"
if [ ! -f "$SCRIPT_PATH" ]; then
    SCRIPT_PATH="$(dirname "$0")/music_visualizer.py"
fi
PID_FILE="/tmp/music_visualizer.pid"

# 1. Quick check via PID file
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        kill -15 "$PID" 2>/dev/null
        rm -f "$PID_FILE"
        exit 0
    fi
fi

# Fallback: if PID file is stale, use pkill
if pgrep -f "music_visualizer.py" > /dev/null 2>&1; then
    pkill -f "music_visualizer.py" 2>/dev/null || true
    rm -f "$PID_FILE"
    exit 0
fi

# 2. Launch in background
rm -f "$PID_FILE"
setsid python3 "$SCRIPT_PATH" </dev/null >/dev/null 2>&1 &
exit 0
