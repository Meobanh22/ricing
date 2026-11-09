#!/usr/bin/env bash
# toggle_settings.sh — Toggle settings window.

SCRIPT_PATH="$HOME/.config/hypr/scripts/popups/settings.py"
if [ ! -f "$SCRIPT_PATH" ]; then
    SCRIPT_PATH="$(dirname "$0")/settings.py"
fi
PID_FILE="/tmp/settings.pid"

# 1. Quick check via PID file
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        kill -USR1 "$PID" 2>/dev/null
        exit 0
    fi
fi

# Fallback: if PID file is stale, use pkill
if pgrep -f "settings.py" > /dev/null 2>&1; then
    pkill -15 -f "settings.py" 2>/dev/null || true
    rm -f "$PID_FILE"
    exit 0
fi

# 2. Launch in background
rm -f "$PID_FILE"
setsid python3 "$SCRIPT_PATH" </dev/null >/dev/null 2>&1 &
exit 0

