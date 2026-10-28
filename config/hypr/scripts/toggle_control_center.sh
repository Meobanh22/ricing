#!/usr/bin/env bash
# toggle_control_center.sh — Toggle control center window.

SCRIPT_PATH="$HOME/.config/hypr/scripts/control_center.py"
PID_FILE="/tmp/control_center.pid"

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
if pgrep -f "control_center.py" > /dev/null 2>&1; then
    pkill -f "control_center.py" 2>/dev/null || true
    rm -f "$PID_FILE"
    exit 0
fi

# 2. Launch in background
rm -f "$PID_FILE"
python3 "$SCRIPT_PATH" &
exit 0
