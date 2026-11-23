#!/usr/bin/env bash
# get_ime.sh — Current input method state for Waybar.

STATE=$(fcitx5-remote 2>/dev/null)
if [ $? -eq 0 ]; then
    if [ "$STATE" = "2" ]; then
        echo "{\"text\": \"🇻🇳 VIE\", \"tooltip\": \"\", \"class\": \"vie\"}"
        exit 0
    fi
    CURR=$(fcitx5-remote -n 2>/dev/null || echo "")
    if [[ "$CURR" =~ [uU]nikey|[bB]amboo|[nN]gosen ]]; then
        echo "{\"text\": \"🇻🇳 VIE\", \"tooltip\": \"\", \"class\": \"vie\"}"
    else
        echo "{\"text\": \"🇬🇧 ENG\", \"tooltip\": \"\", \"class\": \"eng\"}"
    fi
    exit 0
fi

echo "{\"text\": \"🇬🇧 ENG\", \"tooltip\": \"\", \"class\": \"eng\"}"
