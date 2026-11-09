#!/usr/bin/env bash
# OpenApps.sh — Application launcher toggle.

if pgrep -x "rofi" > /dev/null; then
    pkill -x "rofi"
    exit 0
fi

# Run Rofi with theme
if command -v rofi &> /dev/null; then
    CONFIG_FILE="$HOME/.config/rofi/config.rasi"
    if [ ! -f "$CONFIG_FILE" ]; then
        CONFIG_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../rofi" 2>/dev/null && pwd)/config.rasi"
    fi
    rofi -show drun -modi drun,run,filebrowser \
        -font "JetBrains Mono Nerd Font 13" \
        -show-icons -icon-theme "Papirus" \
        -display-drun "Apps" \
        -display-run "Run" \
        -display-filebrowser "Files" \
        -drun-display-format "{name}" \
        -config "$CONFIG_FILE"
    exit 0
fi

# Fallback to Wofi
if command -v wofi &> /dev/null; then
    wofi --show drun --prompt "Search apps..."
    exit 0
fi

