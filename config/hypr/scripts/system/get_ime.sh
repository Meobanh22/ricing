#!/usr/bin/env bash
# get_ime.sh — Current input method state for Waybar.

if command -v fcitx5-remote &>/dev/null && pgrep -x "fcitx5" > /dev/null; then
    STATE=$(fcitx5-remote 2>/dev/null || echo "1")
    CURR=$(fcitx5-remote -n 2>/dev/null || echo "")

    if [ "$STATE" = "2" ] || [[ "$CURR" =~ [uU]nikey|[bB]amboo|[nN]gosen ]]; then
        echo "{\"text\": \"🇻🇳 VIE\", \"tooltip\": \"Bộ gõ: Ngó Sen (Tiếng Việt)\\nClick: Bật/Tắt tiếng Việt\", \"class\": \"vie\"}"
    else
        echo "{\"text\": \"🇬🇧 ENG\", \"tooltip\": \"Bộ gõ: Tiếng Anh (English)\\nClick: Bật tiếng Việt (Ngó Sen)\", \"class\": \"eng\"}"
    fi
    exit 0
fi

echo "{\"text\": \"🇬🇧 ENG\", \"tooltip\": \"Fcitx5 chưa khởi động\", \"class\": \"eng\"}"
