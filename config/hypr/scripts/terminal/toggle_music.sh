#!/usr/bin/env bash
# toggle_music.sh — Toggle Terminal Music Visualizer & Synced Lyrics.

# 1. If running inside interactive terminal, run directly in-place
if [ -t 0 ] && [ -t 1 ]; then
    exec music "$@"
fi

# 2. If running from GUI shortcut (Super+M) or Waybar:
# Toggle Kitty terminal running music with class 'music-vis'
if pgrep -f "kitty --class music-vis" >/dev/null 2>&1; then
    pkill -f "kitty --class music-vis" 2>/dev/null || true
    pkill -RTMIN+7 waybar 2>/dev/null || true
    exit 0
fi

kitty --class music-vis --override window_padding_width=0 music &
(sleep 0.3 && pkill -RTMIN+7 waybar 2>/dev/null || true) &
exit 0
