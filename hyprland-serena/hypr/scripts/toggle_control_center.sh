#!/usr/bin/env bash
# ==============================================================================
# 🌸 SERENA CONTROL CENTER TOGGLE & STATUS SYNCHRONIZER
# Updates IME, WiFi, and Battery in the SwayNC expanded panel before opening
# ==============================================================================

# 1. Get IME (Language)
IME=$(~/.config/hypr/scripts/get_ime.sh 2>/dev/null | tr -d '\n')
[ -z "$IME" ] && IME="ENG"

# 2. Get Battery % and Status
BAT_CAP=$(cat /sys/class/power_supply/BAT*/capacity 2>/dev/null | head -n1)
BAT_STAT=$(cat /sys/class/power_supply/BAT*/status 2>/dev/null | head -n1)
if [ -n "$BAT_CAP" ]; then
    if [ "$BAT_STAT" = "Charging" ]; then
        BAT_ICON="󰂄"
    elif [ "$BAT_CAP" -le 20 ]; then
        BAT_ICON="󰂃"
    else
        BAT_ICON="󰁹"
    fi
    BAT_TXT="$BAT_ICON $BAT_CAP%"
else
    BAT_TXT="󰚥 AC"
fi

# 3. Get WiFi SSID
SSID=$(nmcli -t -f active,ssid dev wifi 2>/dev/null | grep '^yes' | cut -d: -f2 | head -n1)
[ -z "$SSID" ] && SSID="Offline"
WIFI_TXT="󰖩 $SSID"

STATUS_LINE="  $IME   •   $WIFI_TXT   •   $BAT_TXT  "

# 4. Update SwayNC label text quickly
CONFIG="$HOME/.config/swaync/config.json"
if [ -f "$CONFIG" ]; then
    # Replace the label text with current live values
    python3 -c "
import json
try:
    with open('$CONFIG', 'r') as f:
        data = json.load(f)
    if 'widget-config' in data and 'label' in data['widget-config']:
        data['widget-config']['label']['text'] = '''$STATUS_LINE'''
        with open('$CONFIG', 'w') as f:
            json.dump(data, f, indent=2)
except Exception:
    pass
"
    swaync-client --reload-config >/dev/null 2>&1
fi

# 5. Toggle SwayNC Control Center
swaync-client -t -sw
