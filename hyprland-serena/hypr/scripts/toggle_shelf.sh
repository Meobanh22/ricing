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

# 1. Kiểm tra xem tiến trình shelf.py có đang chạy thực sự không
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

# Fallback nếu PID file chưa có hoặc bị lệch: tìm chính xác tiến trình python3 running shelf.py
if [ -z "$SHELF_PID" ]; then
    MATCHING_PID=$(pgrep -f "python3.*shelf\.py" | head -n 1)
    if [ -n "$MATCHING_PID" ]; then
        SHELF_PID="$MATCHING_PID"
        echo "$SHELF_PID" > "$PID_FILE"
    fi
fi

# Nếu tiến trình đang chạy: Toggle hoặc chuyển tab
if [ -n "$SHELF_PID" ]; then
    CURRENT_MODE="clip"
    [ -f "$MODE_FILE" ] && CURRENT_MODE=$(cat "$MODE_FILE" 2>/dev/null)

    if [ "$CURRENT_MODE" == "$TARGET_MODE" ]; then
        # Cùng phím tắt -> Đóng cửa sổ (Toggle Close)
        kill -15 "$SHELF_PID" 2>/dev/null
        rm -f "$PID_FILE" "$MODE_FILE"
        exit 0
    else
        # Khác tab -> Chuyển ngay sang tab được yêu cầu
        echo "$TARGET_MODE" > "$MODE_FILE"
        exit 0
    fi
fi

# Đảm bảo daemon cliphist theo dõi clipboard
pgrep -f "cliphist store" > /dev/null 2>&1 || {
    wl-paste --type text --watch cliphist store >/dev/null 2>&1 &
    wl-paste --type image --watch cliphist store >/dev/null 2>&1 &
}

# 2. Khởi chạy ngầm với tab được chọn
echo "$TARGET_MODE" > "$MODE_FILE"
python3 "$SCRIPT_PATH" "$TARGET_MODE" &
exit 0

