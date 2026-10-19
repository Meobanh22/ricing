#!/usr/bin/env bash
# ==============================================================================
# 🌹 MINIMALIST WLOGOUT LAUNCHER (1-ROW FLOATING DOCK)
# ==============================================================================

if pgrep -x "wlogout" > /dev/null; then
    pkill -x "wlogout"
    exit 0
fi

# Detect monitor resolution & scaling
res_h=$(hyprctl -j monitors 2>/dev/null | jq -r '.[] | select(.focused==true) | .height / .scale' 2>/dev/null | awk -F'.' '{print $1}')
res_w=$(hyprctl -j monitors 2>/dev/null | jq -r '.[] | select(.focused==true) | .width / .scale' 2>/dev/null | awk -F'.' '{print $1}')

# Fallbacks if undetected
[[ -z "$res_h" || "$res_h" -le 0 ]] && res_h=1080
[[ -z "$res_w" || "$res_w" -le 0 ]] && res_w=1920

# Calculate centered dock margins
T_val=$(( (res_h - 220) / 2 ))
B_val=$T_val
L_val=$(( (res_w - 1100) / 2 ))
R_val=$L_val

[ "$L_val" -lt 50 ] && L_val=50
[ "$R_val" -lt 50 ] && R_val=50
[ "$T_val" -lt 50 ] && T_val=50
[ "$B_val" -lt 50 ] && B_val=50

wlogout --protocol layer-shell -b 5 -T "$T_val" -B "$B_val" -L "$L_val" -R "$R_val" -c 16 -r 16 &

