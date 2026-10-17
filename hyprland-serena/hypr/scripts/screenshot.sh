#!/usr/bin/env bash
# ==============================================================================
# 🌸 SERENA SCREENSHOT TOOL (Grim + Slurp + Swappy)
# ==============================================================================
# - area: Chụp vùng chọn -> Tự lưu vào Clipboard & ~/Pictures/Screenshots/
# - edit: Chụp vùng chọn -> Mở Swappy để vẽ nơ, mũi tên, thêm chữ
# - full: Chụp toàn bộ màn hình
# Thiết kế tối giản: KHÔNG popup thông báo
# ==============================================================================

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
