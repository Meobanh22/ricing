#!/usr/bin/env bash
# toggle_shelf.sh — Toggle Shelf and Clipboard panel.

SCRIPT_PATH="$HOME/.config/hypr/scripts/popups/shelf.py"
if [ ! -f "$SCRIPT_PATH" ]; then
    SCRIPT_PATH="$(dirname "$0")/shelf.py"
fi
PID_FILE="/tmp/shelf.pid"
MODE_FILE="/tmp/shelf.mode"

TARGET_MODE="clip"
if [[ "$1" == "--shelf" || "$1" == "-s" || "$1" == "shelf" || "$1" == "stash" ]]; then
    TARGET_MODE="shelf"
fi

# 1. Check if shelf.py is actively running
SHELF_PID=""
if [ -f "$PID_FILE" ]; then
    CANDIDATE_PID=$(cat "$PID_FILE" 2>/dev/null)
    if [ -n "$CANDIDATE_PID" ] && kill -0 "$CANDIDATE_PID" 2>/dev/null && grep -qa "shelf.py" /proc/"$CANDIDATE_PID"/cmdline 2>/dev/null; then
        SHELF_PID="$CANDIDATE_PID"
    else
        # Stale PID file
        rm -f "$PID_FILE"
    fi
fi

# Fallback if PID file missing or desynced: locate python3 running shelf.py
if [ -z "$SHELF_PID" ]; then
    MATCHING_PID=$(pgrep -f "python3.*shelf\.py" | head -n 1)
    if [ -n "$MATCHING_PID" ]; then
        SHELF_PID="$MATCHING_PID"
        echo "$SHELF_PID" > "$PID_FILE"
    fi
fi

# If process is running: send SIGUSR1 to toggle show/hide/tab instantly
if [ -n "$SHELF_PID" ]; then
    echo "$TARGET_MODE" > "$MODE_FILE"
    kill -USR1 "$SHELF_PID" 2>/dev/null
    exit 0
fi

# Ensure cliphist daemon is watching clipboard
pgrep -f "cliphist store" > /dev/null 2>&1 || {
    wl-paste --type text --watch cliphist store >/dev/null 2>&1 &
    wl-paste --type image --watch cliphist store >/dev/null 2>&1 &
}

# 2. Launch in background with selected tab
echo "$TARGET_MODE" > "$MODE_FILE"
setsid python3 "$SCRIPT_PATH" "$TARGET_MODE" </dev/null >/dev/null 2>&1 &
exit 0

