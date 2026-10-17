#!/usr/bin/env bash
# ==============================================================================
# 🎵 SERENA MPRIS / MUSIC MODULE FOR WAYBAR
# Luôn hiển thị nốt nhạc  khi không có nhạc đang phát
# ==============================================================================

STATUS=$(playerctl status 2>/dev/null || echo "None")

if [ "$STATUS" = "Playing" ]; then
    TITLE=$(playerctl metadata --format "{{title}}" 2>/dev/null | cut -c 1-20)
    ARTIST=$(playerctl metadata --format "{{artist}}" 2>/dev/null)
    [ -z "$TITLE" ] && TITLE="Playing"
    echo "{\"text\": \" $TITLE\", \"tooltip\": \"$ARTIST - $TITLE\", \"class\": \"playing\"}"
elif [ "$STATUS" = "Paused" ]; then
    TITLE=$(playerctl metadata --format "{{title}}" 2>/dev/null | cut -c 1-20)
    [ -z "$TITLE" ] && TITLE="Paused"
    echo "{\"text\": \"󰐎 $TITLE\", \"tooltip\": \"Paused: $TITLE\", \"class\": \"paused\"}"
else
    # Khi không có nhạc bật -> luôn hiển thị icon nốt nhạc 
    echo "{\"text\": \"\", \"tooltip\": \"No music playing\", \"class\": \"stopped\"}"
fi

