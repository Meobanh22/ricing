#!/usr/bin/env bash
# ==============================================================================
# 🇻🇳 LẤY TRẠNG THÁI BỘ GÕ HIỆN TẠI CHO WAYBAR (HỖ TRỢ CẢ FCITX5 & IBUS)
# ==============================================================================

if command -v fcitx5-remote &>/dev/null && pgrep -x "fcitx5" > /dev/null; then
    CURR=$(fcitx5-remote -n 2>/dev/null || echo "")
    if [[ "$CURR" =~ [uU]nikey ]]; then
        echo "🇻🇳 VIE"
    else
        echo "🇬🇧 ENG"
    fi
    exit 0
fi

# Fallback IBus
CURR=$(ibus engine 2>/dev/null || echo "")
if [ "$CURR" = "Unikey" ]; then
    echo "🇻🇳 VIE"
else
    echo "🇬🇧 ENG"
fi

