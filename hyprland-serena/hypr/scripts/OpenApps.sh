#!/usr/bin/env bash
# ==============================================================================
# 🌸 SERENA APP LAUNCHER (ROCK SOLID & FAILPROOF)
# ==============================================================================
# Hỗ trợ mở menu ứng dụng siêu mượt:
# 1. Nếu menu đang mở thì bấm sẽ đóng lại (Toggle)
# 2. Ưu tiên Rofi chuẩn Wayland
# 3. Tự động fallback sang Wofi nếu có trục trặc
# ==============================================================================

if pgrep -x "rofi" > /dev/null; then
    pkill -x "rofi"
    exit 0
fi

# Chạy Rofi với theme chuẩn
if command -v rofi &> /dev/null; then
    rofi -show drun -modi drun,run,filebrowser
    exit 0
fi

# Fallback sang Wofi nếu không có Rofi
if command -v wofi &> /dev/null; then
    wofi --show drun --prompt "🌸 Tìm ứng dụng..."
    exit 0
fi

