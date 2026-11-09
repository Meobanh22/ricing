#!/usr/bin/env bash
# get_ime.sh — Current input method state for Waybar.

if command -v fcitx5-remote &>/dev/null && pgrep -x "fcitx5" > /dev/null; then
    CURR=$(fcitx5-remote -n 2>/dev/null || echo "")
    if [[ "$CURR" =~ [uU]nikey|[bB]amboo ]]; then
        echo "🇻🇳 VIE"
    else
        echo "🇬🇧 ENG"
    fi
    exit 0
fi

echo "🇬🇧 ENG"
