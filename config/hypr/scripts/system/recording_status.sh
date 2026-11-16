#!/usr/bin/env bash
# recording_status.sh — Output Waybar JSON for active screen recording.

if ! pgrep -x "wf-recorder" >/dev/null 2>&1; then
    exit 0
fi

TIME_FILE="/tmp/wf-recorder.time"
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

echo "{\"text\": \"󰑋 REC ${TIME_STR}\", \"tooltip\": \"Recording active (${TIME_STR})\\nClick to stop recording\", \"class\": \"recording\"}"
