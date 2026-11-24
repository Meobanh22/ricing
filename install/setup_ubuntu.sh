#!/usr/bin/env bash
# setup_ubuntu.sh — Hyprland installer and setup for Ubuntu 24.04.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ASSETS_DIR="$REPO_ROOT/assets"

RED='\033[1;31m'
PINK='\033[1;35m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${PINK}=== HYPRLAND SERENA DESKTOP SETUP (UBUNTU 24.04) ===${NC}\n"

# === CURSOR PREPARATION ===
echo -e "${YELLOW}[1/4] Installing Sylveon Custom cursor theme...${NC}"
mkdir -p "$HOME/.icons/default" "$HOME/.local/share/icons" "$HOME/Pictures/Screenshots"
if [ ! -f "$ASSETS_DIR/cursors/sylveon-custom/manifest.hl" ] || [ ! -d "$ASSETS_DIR/cursors/sylveon-custom/hyprcursors" ]; then
    echo -e "  ${YELLOW}Building native Hyprcursor package...${NC}"
    python3 "$REPO_ROOT/dev_tools/cursor_builder/build_linux_cursors.py"
fi

sudo cp -rf "$ASSETS_DIR/cursors/sylveon-custom" /usr/share/icons/ 2>/dev/null || true

cat > "$HOME/.icons/default/index.theme" << 'CURSOR_EOF'
[Icon Theme]
Name=Default
Comment=Default Cursor Theme
Inherits=sylveon-custom
CURSOR_EOF

gsettings set org.gnome.desktop.interface cursor-theme "sylveon-custom" 2>/dev/null || true
gsettings set org.gnome.desktop.interface cursor-size 24 2>/dev/null || true
echo -e "  ${GREEN}✔ Sylveon Dual Theme (Hyprcursor + Xcursor) ready!${NC}"

# === CONFIG & ASSETS DEPLOYMENT ===
echo -e "\n${YELLOW}[2/4] Deploying dotfiles, theme tokens & assets via sync.sh...${NC}"
bash "$REPO_ROOT/sync.sh" --no-reload

# === INPUT METHOD (FCITX5 / IBUS) ===
echo -e "\n${YELLOW}[3/4] Configuring input method...${NC}"
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
echo -e "\n${YELLOW}[4/4] Reloading live desktop environment...${NC}"
if [ "$XDG_CURRENT_DESKTOP" = "Hyprland" ] || pgrep -x "Hyprland" &>/dev/null; then
    bash "$REPO_ROOT/sync.sh"
fi

echo -e "\n${PINK}=== SETUP COMPLETED! ===${NC}\n"
