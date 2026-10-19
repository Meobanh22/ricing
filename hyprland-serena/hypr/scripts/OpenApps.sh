#!/usr/bin/env bash
# ==============================================================================
# 🌸 APP LAUNCHER (ROCK SOLID & FAILPROOF)
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
    THEME_FILE="$HOME/.config/rofi/config.rasi"
    if [ ! -f "$THEME_FILE" ]; then
        THEME_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../rofi" 2>/dev/null && pwd)/config.rasi"
    fi
    rofi -show drun -modi drun,run,filebrowser -theme "$THEME_FILE"
    exit 0
fi

# Fallback sang Wofi nếu không có Rofi
if command -v wofi &> /dev/null; then
    wofi --show drun --prompt "🌸 Search apps..."
    exit 0
fi

