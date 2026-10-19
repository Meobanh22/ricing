#!/usr/bin/env bash
# ==============================================================================
# 🌸 SERENA QUICK SHELF & CLIPBOARD TOGGLE DISPATCHER
# ==============================================================================
# Usage:
#   toggle_shelf.sh          # Toggle (defaults to Clipboard)
#   toggle_shelf.sh --clip   # Toggle or switch to Clipboard tab
#   toggle_shelf.sh --shelf  # Toggle or switch to File Shelf tab
# ==============================================================================

SCRIPT_PATH="$HOME/.config/hypr/scripts/shelf.py"
PID_FILE="/tmp/serena_shelf.pid"
MODE_FILE="/tmp/serena_shelf.mode"

TARGET_MODE="clip"
if [[ "$1" == "--shelf" || "$1" == "-s" || "$1" == "shelf" || "$1" == "stash" ]]; then
    TARGET_MODE="shelf"
fi

# 1. Kiểm tra xem tiến trình có đang chạy không
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        # Đang mở: Kiểm tra tab hiện tại
        CURRENT_MODE="clip"
        [ -f "$MODE_FILE" ] && CURRENT_MODE=$(cat "$MODE_FILE" 2>/dev/null)

        if [ "$CURRENT_MODE" == "$TARGET_MODE" ]; then
            # Cùng phím tắt -> Đóng cửa sổ (Toggle Close)
            kill -15 "$PID" 2>/dev/null
            rm -f "$PID_FILE" "$MODE_FILE"
            exit 0
        else
            # Khác tab -> Chuyển ngay sang tab được yêu cầu
            echo "$TARGET_MODE" > "$MODE_FILE"
            exit 0
        fi
    fi
fi

# Fallback an toàn nếu PID file bị treo
if pgrep -f "shelf.py" > /dev/null 2>&1; then
    pkill -f "shelf.py" 2>/dev/null || true
    rm -f "$PID_FILE" "$MODE_FILE"
    exit 0
fi

# 2. Khởi chạy ngầm với tab được chọn
echo "$TARGET_MODE" > "$MODE_FILE"
python3 "$SCRIPT_PATH" "$TARGET_MODE" &
exit 0
