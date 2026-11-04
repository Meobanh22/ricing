#!/usr/bin/env bash
# toggle_desktop_widgets.sh — Toggle desktop background widgets.

SCRIPT_PATH="$HOME/.config/hypr/scripts/desktop_widgets.py"
PID_FILE="/tmp/desktop_widgets.pid"

# Fallback to repo path if user config does not exist
if [ ! -f "$SCRIPT_PATH" ]; then
    SCRIPT_PATH="$HOME/custom/config/hypr/scripts/desktop_widgets.py"
fi

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
if pgrep -f "desktop_widgets.py" > /dev/null 2>&1; then
    pkill -f "desktop_widgets.py" 2>/dev/null || true
    rm -f "$PID_FILE"
    exit 0
fi

# 2. Launch detached via Hyprland compositor dispatcher
rm -f "$PID_FILE"
if command -v hyprctl >/dev/null 2>&1; then
    hyprctl dispatch exec "python3 $SCRIPT_PATH"
else
    nohup python3 "$SCRIPT_PATH" >/dev/null 2>&1 &
fi
exit 0
