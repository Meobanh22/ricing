#!/usr/bin/env bash
# toggle_vietnamese.sh — Toggle Vietnamese input method (Ngó Sen / Fcitx5).

if ! command -v fcitx5-remote &>/dev/null; then
    notify-send -u critical -a "Ngó Sen" "Lỗi Fcitx5" "Không tìm thấy lệnh fcitx5-remote"
    exit 1
fi

# 1. Start fcitx5 if not running
if ! pgrep -x "fcitx5" > /dev/null; then
    fcitx5 -d 2>/dev/null || true
    sleep 0.5
fi

# 2. Toggle Active / Inactive
fcitx5-remote -t 2>/dev/null || true
sleep 0.05
STATE=$(fcitx5-remote 2>/dev/null || echo "1")
CURR=$(fcitx5-remote -n 2>/dev/null || echo "")

if [ "$STATE" = "2" ] || [[ "$CURR" =~ [nN]gosen|[bB]amboo|[uU]nikey ]]; then
    if [ "$CURR" != "ngosen" ] && [ "$STATE" = "2" ]; then
        fcitx5-remote -s ngosen 2>/dev/null || true
    fi
    notify-send -a "Ngó Sen" -i input-keyboard -t 1200 "🇻🇳 Ngó Sen (BẬT)" "Đã bật gõ tiếng Việt"
else
    notify-send -a "Ngó Sen" -i input-keyboard -t 1200 "🇬🇧 English (TẮT)" "Đã chuyển sang tiếng Anh"
fi

# Refresh Waybar immediately via SIGRTMIN+8
pkill -RTMIN+8 waybar 2>/dev/null || true
