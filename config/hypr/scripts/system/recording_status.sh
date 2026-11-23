#!/usr/bin/env bash
# recording_status.sh — Output Waybar JSON for active screen recording.

TIME_FILE="/tmp/wf-recorder.time"
PID_FILE="/tmp/wf-recorder.pid"

# Fast path: If neither marker file exists, recorder is inactive (0 subprocess forks)
if [ ! -f "$TIME_FILE" ] && [ ! -f "$PID_FILE" ]; then
    exit 0
fi

if ! pgrep -x "wf-recorder" >/dev/null 2>&1; then
    rm -f "$TIME_FILE" "$PID_FILE" 2>/dev/null
    exit 0
fi
if [ -f "$TIME_FILE" ]; then
    START_TIME=$(cat "$TIME_FILE" 2>/dev/null)
    NOW=$(date +%s)
    ELAPSED=$((NOW - START_TIME))
    if [ "$ELAPSED" -lt 0 ]; then ELAPSED=0; fi
else
    ELAPSED=0
fi

MINS=$((ELAPSED / 60))
SECS=$((ELAPSED % 60))
TIME_STR=$(printf "%02d:%02d" "$MINS" "$SECS")

echo "{\"text\": \"󰑋 REC ${TIME_STR}\", \"tooltip\": \"\", \"class\": \"recording\"}"
