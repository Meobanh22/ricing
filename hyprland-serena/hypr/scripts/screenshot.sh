#!/usr/bin/env bash
# screenshot.sh — Screenshot capture tool using grim and slurp.

DIR="$HOME/Pictures/Screenshots"
mkdir -p "$DIR"
NAME="screenshot_$(date +%Y%m%d_%H%M%S).png"
FILE="$DIR/$NAME"

MODE=${1:-area}

case "$MODE" in
    area)
        # Chụp vùng chọn (Win + Shift + S hoặc PrintScreen)
        grim -g "$(slurp)" - | tee "$FILE" | wl-copy --type image/png
        if [ ! -s "$FILE" ]; then
            rm -f "$FILE"
        fi
        ;;
    edit)
        # Chụp vùng chọn và mở trình vẽ chỉnh sửa Swappy
        grim -g "$(slurp)" - | swappy -f -
        ;;
    full)
        # Chụp toàn màn hình
        grim "$FILE"
        wl-copy --type image/png < "$FILE"
        ;;
esac
