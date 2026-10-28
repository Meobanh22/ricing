#!/usr/bin/env bash
# Wlogout.sh — Launch wlogout power menu.

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

# Calculate centered dock margins (optimal 1-row card ratio ~177x180px)
dock_w=950
dock_h=180

[ "$dock_w" -gt "$((res_w - 60))" ] && dock_w=$((res_w - 60))
[ "$dock_h" -gt "$((res_h - 60))" ] && dock_h=$((res_h - 60))

T_val=$(( (res_h - dock_h) / 2 ))
B_val=$T_val
L_val=$(( (res_w - dock_w) / 2 ))
R_val=$L_val

[ "$L_val" -lt 30 ] && L_val=30
[ "$R_val" -lt 30 ] && R_val=30
[ "$T_val" -lt 30 ] && T_val=30
[ "$B_val" -lt 30 ] && B_val=30

CONFIG_DIR="$HOME/.config/wlogout"
LAYOUT_OPT=""
CSS_OPT=""
[ -f "$CONFIG_DIR/layout" ] && LAYOUT_OPT="-l $CONFIG_DIR/layout"
[ -f "$CONFIG_DIR/style.css" ] && CSS_OPT="-C $CONFIG_DIR/style.css"

wlogout --protocol layer-shell -b 5 $LAYOUT_OPT $CSS_OPT -T "$T_val" -B "$B_val" -L "$L_val" -R "$R_val" -c 16 -r 16 &
