#!/usr/bin/env bash
# setup_ubuntu.sh — Hyprland installer and setup for Ubuntu 24.04.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_DIR="$REPO_ROOT/config"
ASSETS_DIR="$REPO_ROOT/assets"

RED='\033[1;31m'
PINK='\033[1;35m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${PINK}=== HYPRLAND SERENA DESKTOP SETUP (UBUNTU 24.04) ===${NC}\n"

# === DIRECTORY INITIALIZATION ===
echo -e "${YELLOW}[1/6] Initializing user config directories...${NC}"
mkdir -p "$HOME/.config/hypr/scripts/popups" "$HOME/.config/hypr/scripts/widgets" "$HOME/.config/hypr/scripts/services" "$HOME/.config/hypr/scripts/system"
mkdir -p "$HOME/.config/hypr/styles"
mkdir -p "$HOME/.config/hypr/assets"
mkdir -p "$HOME/.config/waybar"
mkdir -p "$HOME/.config/rofi"
mkdir -p "$HOME/.config/fastfetch"
mkdir -p "$HOME/.config/kitty"
mkdir -p "$HOME/.config/fcitx5/conf"
mkdir -p "$HOME/.config/gtk-3.0"
mkdir -p "$HOME/.config/gtk-4.0"
mkdir -p "$HOME/.config/wlogout/icons"
mkdir -p "$HOME/.config/swaync"
mkdir -p "$HOME/.config/btop/themes"
mkdir -p "$HOME/.icons/default"
mkdir -p "$HOME/.local/share/icons"
mkdir -p "$HOME/Pictures/Screenshots"
mkdir -p "$HOME/Pictures/wallpapers"
echo -e "  ${GREEN}✔ Directories initialized!${NC}"

# === CURSOR SETUP ===
echo -e "\n${YELLOW}[2/6] Installing Sylveon Custom cursor theme...${NC}"
if [ ! -f "$ASSETS_DIR/cursors/sylveon-custom/manifest.hl" ] || [ ! -d "$ASSETS_DIR/cursors/sylveon-custom/hyprcursors" ]; then
    echo -e "  ${YELLOW}Building native Hyprcursor package...${NC}"
    python3 "$REPO_ROOT/dev_tools/cursor_builder/build_linux_cursors.py"
fi

cp -rf "$ASSETS_DIR/cursors/sylveon-custom" "$HOME/.icons/"
cp -rf "$ASSETS_DIR/cursors/sylveon-custom" "$HOME/.local/share/icons/"
sudo cp -rf "$ASSETS_DIR/cursors/sylveon-custom" /usr/share/icons/ 2>/dev/null || true

cat > "$HOME/.icons/default/index.theme" << 'CURSOR_EOF'
[Icon Theme]
Name=Default
Comment=Default Cursor Theme
Inherits=sylveon-custom
CURSOR_EOF

cat > "$HOME/.config/gtk-3.0/settings.ini" << 'GTK3_EOF'
[Settings]
gtk-cursor-theme-name=sylveon-custom
gtk-cursor-theme-size=24
GTK3_EOF

cat > "$HOME/.config/gtk-4.0/settings.ini" << 'GTK4_EOF'
[Settings]
gtk-cursor-theme-name=sylveon-custom
gtk-cursor-theme-size=24
GTK4_EOF

gsettings set org.gnome.desktop.interface cursor-theme "sylveon-custom" 2>/dev/null || true
gsettings set org.gnome.desktop.interface cursor-size 24 2>/dev/null || true
echo -e "  ${GREEN}✔ Sylveon Dual Theme (Hyprcursor + Xcursor) installed!${NC}"

# === CONFIG DEPLOYMENT ===
echo -e "\n${YELLOW}[3/6] Deploying dotfiles to ~/.config/...${NC}"
cp -rf "$CONFIG_DIR/hypr/"* "$HOME/.config/hypr/"
rm -f "$HOME/.config/hypr/hyprland.conf"
chmod +x "$HOME/.config/hypr/scripts/popups/"* "$HOME/.config/hypr/scripts/widgets/"* "$HOME/.config/hypr/scripts/services/"* "$HOME/.config/hypr/scripts/system/"* 2>/dev/null || true

cp -rf "$CONFIG_DIR/waybar/"* "$HOME/.config/waybar/"
cp -rf "$CONFIG_DIR/kitty/"* "$HOME/.config/kitty/"
cp -rf "$CONFIG_DIR/rofi/"* "$HOME/.config/rofi/"
cp -rf "$CONFIG_DIR/fastfetch/"* "$HOME/.config/fastfetch/"
cp -rf "$CONFIG_DIR/wlogout/"* "$HOME/.config/wlogout/"
cp -rf "$CONFIG_DIR/swaync/"* "$HOME/.config/swaync/"
cp -rf "$CONFIG_DIR/btop/"* "$HOME/.config/btop/"
cp -rf "$CONFIG_DIR/gtk-3.0/"* "$HOME/.config/gtk-3.0/"
cp -rf "$CONFIG_DIR/gtk-4.0/"* "$HOME/.config/gtk-4.0/"
cp -rf "$CONFIG_DIR/fcitx5/"* "$HOME/.config/fcitx5/"
cp -rf "$CONFIG_DIR/swappy/"* "$HOME/.config/swappy/" 2>/dev/null || true
mkdir -p "$HOME/.config/hypr/theme"
cp -rf "$CONFIG_DIR/theme/"* "$HOME/.config/hypr/theme/" 2>/dev/null || true

if [ -f "$HOME/.config/gtk-3.0/bookmarks" ]; then
    sed -i "s|\\\$HOME|$HOME|g" "$HOME/.config/gtk-3.0/bookmarks"
fi

echo -e "  ${GREEN}✔ Deployed configuration files!${NC}"

# === WALLPAPERS & ASSETS ===
echo -e "\n${YELLOW}[4/6] Synchronizing wallpapers & avatars...${NC}"
cp -rn "$ASSETS_DIR/wallpapers/"* "$HOME/Pictures/wallpapers/" 2>/dev/null || true
cp -rn "$ASSETS_DIR/avatars/"* "$HOME/.config/hypr/assets/" 2>/dev/null || true
mkdir -p "$HOME/.config/hypr/assets/pokemon" "$HOME/.config/hypr/assets/banners"
cp -rn "$ASSETS_DIR/pokemon/"* "$HOME/.config/hypr/assets/pokemon/" 2>/dev/null || true
cp -rn "$ASSETS_DIR/pokemon/"* "$HOME/.config/hypr/assets/" 2>/dev/null || true
cp -rn "$ASSETS_DIR/banners/"* "$HOME/.config/hypr/assets/banners/" 2>/dev/null || true
cp -rn "$ASSETS_DIR/banners/"* "$HOME/.config/hypr/assets/" 2>/dev/null || true
echo -e "  ${GREEN}✔ Wallpapers and avatars synchronized!${NC}"

# === INPUT METHOD (FCITX5 / IBUS) ===
echo -e "\n${YELLOW}[5/6] Configuring input method...${NC}"
if command -v fcitx5 &>/dev/null; then
    pkill -9 fcitx5 2>/dev/null || true
    sleep 0.3
    fcitx5 -d --replace &>/dev/null &
    echo -e "  ${GREEN}✔ Fcitx5 started!${NC}"
else
    gsettings set org.freedesktop.ibus.general preload-engines "['xkb:us::eng', 'Unikey']" 2>/dev/null || true
    gsettings set org.gnome.desktop.input-sources sources "[('xkb', 'us'), ('ibus', 'Unikey')]" 2>/dev/null || true
    pkill -9 ibus-daemon 2>/dev/null || true
    sleep 0.3
    ibus-daemon -drxR &>/dev/null &
    sleep 1.2
    ibus engine Unikey 2>/dev/null || true
    echo -e "  ${GREEN}✔ IBus started!${NC}"
fi

# === LIVE RELOAD ===
echo -e "\n${YELLOW}[6/6] Reloading live desktop environment...${NC}"
if [ "$XDG_CURRENT_DESKTOP" = "Hyprland" ] || pgrep -x "Hyprland" &>/dev/null; then
    hyprctl setcursor sylveon-custom 24 &>/dev/null || true
    python3 "$REPO_ROOT/scripts/theme_manager.py" "serena-wine" 2>/dev/null || true
    hyprctl reload &>/dev/null || true
    echo -e "  ${GREEN}✔ Hyprland reloaded!${NC}"

    pkill -x waybar 2>/dev/null || true
    sleep 0.5
    nohup waybar >/dev/null 2>&1 &
    echo -e "  ${GREEN}✔ Waybar started!${NC}"

    pkill -f settings.py 2>/dev/null || true
fi

echo -e "\n${PINK}=== SETUP COMPLETED! ===${NC}\n"
