#!/usr/bin/env bash
# ==============================================================================
# 🌸 SERENA DASHBOARD TOGGLE (ULTRA-FAST & RELIABLE TOGGLE DISPATCHER)
# ==============================================================================

SCRIPT_PATH="$HOME/.config/hypr/scripts/dashboard.py"
PID_FILE="/tmp/dashboard.pid"

# 1. Kiểm tra nhanh bằng PID file (cực nhanh 0.1ms, không cần scan /proc)
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        kill -15 "$PID" 2>/dev/null
        rm -f "$PID_FILE"
        exit 0
    fi
fi

# Fallback an toàn: nếu PID file bị lệch hoặc chết treo, dùng pkill
if pgrep -f "dashboard.py" > /dev/null 2>&1; then
    pkill -f "dashboard.py" 2>/dev/null || true
    rm -f "$PID_FILE"
    exit 0
fi

# 2. Khởi chạy ngầm ngay lập tức
rm -f "$PID_FILE"
python3 "$SCRIPT_PATH" &
exit 0
