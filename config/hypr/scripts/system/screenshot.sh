#!/usr/bin/env bash
# screenshot.sh — Screenshot capture tool using grim and slurp.

DIR="$HOME/Pictures/Screenshots"
mkdir -p "$DIR"
NAME="screenshot_$(date +%Y%m%d_%H%M%S).png"
FILE="$DIR/$NAME"

MODE=${1:-area}

case "$MODE" in
    area)
        # Capture selected area (Super + Shift + S or PrintScreen)
        grim -g "$(slurp)" - | tee "$FILE" | wl-copy --type image/png
        if [ ! -s "$FILE" ]; then
            rm -f "$FILE"
        fi
        ;;
    edit)
        # Capture selected area and open in Swappy editor
        grim -g "$(slurp)" - | swappy -f -
        ;;
    full)
        # Capture fullscreen
        grim "$FILE"
        wl-copy --type image/png < "$FILE"
        ;;
esac
