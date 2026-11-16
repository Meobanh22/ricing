#!/usr/bin/env bash
# record_screen.sh — Screen recorder with internal media audio capture for Hyprland.

VIDEOS_DIR="$HOME/Videos/Recordings"
mkdir -p "$VIDEOS_DIR"

PID_FILE="/tmp/wf-recorder.pid"
TIME_FILE="/tmp/wf-recorder.time"

# 1. Stop recording if already running (Toggle off)
if pgrep -x "wf-recorder" >/dev/null 2>&1; then
    killall -s SIGINT wf-recorder 2>/dev/null || true
    sleep 0.6
    rm -f "$PID_FILE"
    rm -f "$PID_FILE" "$TIME_FILE"
    pkill -RTMIN+9 waybar 2>/dev/null || true
    LATEST_VIDEO="$(ls -t "$VIDEOS_DIR"/*.mp4 2>/dev/null | head -n 1)"
    if [ -n "$LATEST_VIDEO" ]; then
        notify-send -a "Screen Recorder" -i video-x-generic "󰕧 Recording Saved" "Saved to $(basename "$LATEST_VIDEO")"
    else
        notify-send -a "Screen Recorder" -i video-x-generic "󰕧 Recording Stopped" "Video saved to $VIDEOS_DIR"
    fi
    exit 0
fi

# 2. Check if wf-recorder is installed
if ! command -v wf-recorder &>/dev/null; then
    notify-send -u critical -a "Screen Recorder" -i dialog-error "wf-recorder is not installed" "Install with: sudo pacman -S wf-recorder"
    exit 1
fi

MODE="${1:-area}"   # area or full
AUDIO="${2:-media}" # media, mic, or none
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTPUT_FILE="$VIDEOS_DIR/recording_${TIMESTAMP}.mp4"

# 3. Audio source selection (Internal media vs microphone)
AUDIO_ARGS=()
if [ "$AUDIO" = "media" ]; then
    # Capture internal system/media audio (default sink monitor)
    DEFAULT_SINK="$(pactl get-default-sink 2>/dev/null)"
    if [ -n "$DEFAULT_SINK" ]; then
        AUDIO_ARGS=(-a "${DEFAULT_SINK}.monitor")
    else
        AUDIO_ARGS=(-a)
    fi
elif [ "$AUDIO" = "mic" ]; then
    # Capture microphone
    DEFAULT_SOURCE="$(pactl get-default-source 2>/dev/null)"
    if [ -n "$DEFAULT_SOURCE" ]; then
        AUDIO_ARGS=(-a "$DEFAULT_SOURCE")
    else
        AUDIO_ARGS=(-a)
    fi
fi

# 4. Target geometry (Area or Full)
GEOM_ARGS=()
if [ "$MODE" = "area" ]; then
    GEOM="$(slurp 2>/dev/null)"
    if [ -z "$GEOM" ]; then
        exit 0 # User cancelled selection
    fi
    GEOM_ARGS=(-g "$GEOM")
fi

# 5. Start recording
notify-send -a "Screen Recorder" -i media-record "󰻃 Recording Started..." "Mode: $MODE | Sound: $AUDIO\nPress shortcut again to finish."
notify-send -a "Screen Recorder" -i media-record "󰻃 Recording Started..." "Mode: $MODE | Sound: $AUDIO\nClick REC on Waybar or press shortcut to finish."
date +%s > "$TIME_FILE"
wf-recorder "${GEOM_ARGS[@]}" "${AUDIO_ARGS[@]}" -f "$OUTPUT_FILE" &
echo $! > "$PID_FILE"
pkill -RTMIN+9 waybar 2>/dev/null || true
