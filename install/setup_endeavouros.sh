#!/usr/bin/env bash
# setup_endeavouros.sh — Automated installer for EndeavourOS / Arch Linux.

set -e

# Display colors
RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
PINK='\033[1;35m'
BLUE='\033[1;34m'
CYAN='\033[1;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${PINK}=== HYPRLAND SERENA DESKTOP SETUP — ENDEAVOUROS / ARCH LINUX ===${NC}\n"

# === OS DETECTION ===
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [[ "$ID" != "endeavouros" && "$ID" != "arch" && "$ID_LIKE" != *"arch"* ]]; then
        echo -e "${YELLOW}⚠️ Warning: Target system identified as $PRETTY_NAME.${NC}"
        echo -e "This script is optimized for EndeavourOS / Arch Linux. Continue anyway? (y/N)"
        read -r -p "Choice: " choice
        if [[ ! "$choice" =~ ^[Yy]$ ]]; then
            echo -e "${RED}Installation cancelled.${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✔ Detected compatible system: $PRETTY_NAME${NC}\n"
    fi
fi

# === AUR HELPER CHECK ===
AUR_HELPER=""
if command -v yay &>/dev/null; then
    AUR_HELPER="yay"
elif command -v paru &>/dev/null; then
    AUR_HELPER="paru"
else
    echo -e "${YELLOW}'yay' not found. Installing yay...${NC}"
    sudo pacman -S --needed --noconfirm base-devel git
    git clone https://aur.archlinux.org/yay-bin.git /tmp/yay-bin
    (cd /tmp/yay-bin && makepkg -si --noconfirm)
    rm -rf /tmp/yay-bin
    AUR_HELPER="yay"
fi
echo -e "${GREEN}✔ AUR Helper: $AUR_HELPER${NC}\n"

# === PACKAGE INSTALLATION ===
echo -e "${YELLOW}📦 [1/5] Installing package dependencies (Pacman & AUR)...${NC}"

PACMAN_PACKAGES=(
    # Hyprland & Wayland core
    hyprland
    hyprlock
    hypridle
    hyprcursor
    xdg-desktop-portal-hyprland
    xdg-desktop-portal-gtk
    waybar
    swaync
    swappy

    # Terminal & Tools
    kitty
    btop
    fastfetch
    cliphist
    wl-clipboard
    thunar
    thunar-archive-plugin
    file-roller
    grim
    slurp
    jq
    libnotify

    # Hardware, Audio & Bluetooth
    pipewire
    wireplumber
    pipewire-audio
    pipewire-alsa
    pipewire-pulse
    pavucontrol
    network-manager-applet
    power-profiles-daemon
    sound-theme-freedesktop
    playerctl
    brightnessctl
    bluez
    bluez-utils
    cava

    # GTK, Polkit & Python
    polkit-gnome
    gnome-keyring
    python
    python-gobject
    python-dbus
    python-pillow
    gtk3
    gtk4
    gtk-layer-shell
    loupe
    cairo
    python-cairo
    gobject-introspection
    libcanberra
    fcitx5
    fcitx5-bamboo
    fcitx5-configtool
    fcitx5-gtk
    fcitx5-qt
    fcitx5-unikey
    papirus-icon-theme

    # Fonts
    ttf-jetbrains-mono-nerd
    noto-fonts-emoji
    ttf-fira-code
)

AUR_PACKAGES=(
    # AUR Wayland Tools
    swww
    rofi-wayland
    wlogout
)

echo -e "  ${CYAN}➔ Updating package databases and installing Pacman packages...${NC}"
sudo pacman -S --needed --noconfirm "${PACMAN_PACKAGES[@]}"

echo -e "  ${CYAN}➔ Installing AUR packages via $AUR_HELPER...${NC}"
$AUR_HELPER -S --needed --noconfirm "${AUR_PACKAGES[@]}" || true

echo -e "  ${GREEN}✔ All packages installed successfully!${NC}\n"

# === DIRECTORY & CURSOR INSTALLATION ===
echo -e "${YELLOW}📁 [2/4] Installing Sylveon Custom cursor theme...${NC}"
mkdir -p "$HOME/.icons/default" "$HOME/.local/share/icons" "$HOME/Pictures/Screenshots"
CURSOR_SRC="$REPO_ROOT/assets/cursors/sylveon-custom"
if [ -d "$CURSOR_SRC" ]; then
    sudo cp -rf "$CURSOR_SRC" /usr/share/icons/ 2>/dev/null || true
    echo -e "  ${GREEN}✔ Installed Sylveon Dual Theme to /usr/share/icons/${NC}"
else
    echo -e "  ${RED}✖ Cursor directory not found: $CURSOR_SRC${NC}"
fi

cat > "$HOME/.icons/default/index.theme" << 'CURSOR_EOF'
[Icon Theme]
Name=Default
Comment=Default Cursor Theme
Inherits=sylveon-custom
CURSOR_EOF

# === CONFIG & ASSETS SYNCHRONIZATION ===
echo -e "\n${YELLOW}⚙️  [3/4] Deploying dotfiles, theme tokens & assets via sync.sh...${NC}"
bash "$REPO_ROOT/sync.sh" --no-reload

# === THEME & SERVICES ACTIVATION ===
echo -e "${YELLOW}🎨 [4/4] Activating system services & autologin...${NC}"

# Enable services
systemctl --user enable --now pipewire pipewire-pulse wireplumber 2>/dev/null || true
sudo systemctl enable --now bluetooth.service 2>/dev/null || true

# TTY1 autologin & Hyprland autostart with Hyprlock screen
TARGET_USER="${SUDO_USER:-$USER}"
sudo mkdir -p /etc/systemd/system/getty@tty1.service.d/
cat << AUTOLOGIN_EOF | sudo tee /etc/systemd/system/getty@tty1.service.d/autologin.conf > /dev/null
[Service]
ExecStart=
ExecStart=-/usr/bin/agetty -o '-p -f -- \\u' --noclear --autologin $TARGET_USER %I \$TERM
Type=idle
AUTOLOGIN_EOF
sudo systemctl daemon-reload 2>/dev/null || true

# Autostart Hyprland from login shell (zsh & bash)
for prof in "$HOME/.zprofile" "$HOME/.bash_profile"; do
    if ! grep -q "exec start-hyprland" "$prof" 2>/dev/null; then
        sed -i 's/exec Hyprland/exec start-hyprland/g' "$prof" 2>/dev/null || true
        if ! grep -q "exec start-hyprland" "$prof" 2>/dev/null; then
            cat >> "$prof" << 'PROFILE_EOF'

# Autostart Hyprland on TTY1
if [ -z "$WAYLAND_DISPLAY" ] && [ "$XDG_VTNR" = "1" -o "$(tty)" = "/dev/tty1" ]; then
    exec start-hyprland
fi
PROFILE_EOF
        fi
    fi
done

# Set desktop preferences
gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark' 2>/dev/null || true
gsettings set org.gnome.desktop.interface cursor-theme 'sylveon-custom' 2>/dev/null || true
gsettings set org.gnome.desktop.interface cursor-size 24 2>/dev/null || true
gsettings set org.gnome.desktop.interface font-name 'JetBrains Mono 11' 2>/dev/null || true

echo -e "\n${PINK}=== INSTALLATION COMPLETED ON ENDEAVOUROS! ===${NC}"
echo -e "You can now log into your Hyprland session or launch it with: ${CYAN}Hyprland${NC}\n"
