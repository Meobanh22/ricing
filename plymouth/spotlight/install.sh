#!/usr/bin/env bash
# install.sh — Installs and activates the Spotlight Plymouth theme on EndeavourOS / Arch.

set -e

THEME_NAME="spotlight"
THEME_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THEME_DEST="/usr/share/plymouth/themes/$THEME_NAME"

echo "=== INSTALLING PLYMOUTH SPOTLIGHT THEME ==="

# 1. Install Plymouth if missing
if ! command -v plymouth &>/dev/null; then
    echo "📦 [1/7] Installing plymouth..."
    sudo pacman -S --needed --noconfirm plymouth
else
    echo "✔ [1/7] Plymouth is already installed."
fi

# 2. Copy theme files to /usr/share/plymouth/themes/
echo "📂 [2/7] Copying theme assets to $THEME_DEST..."
sudo mkdir -p "$THEME_DEST"
sudo rm -rf "$THEME_DEST"/*
sudo cp -f "$THEME_SRC/spotlight.plymouth" "$THEME_DEST/"
sudo cp -f "$THEME_SRC/spotlight.script" "$THEME_DEST/"
sudo cp -f "$THEME_SRC/background.png" "$THEME_DEST/"
sudo cp -f "$THEME_SRC/frames/"*.png "$THEME_DEST/"

# 3. Set Spotlight as default theme
echo "🎯 [3/7] Setting default Plymouth theme to '$THEME_NAME'..."
sudo plymouth-set-default-theme "$THEME_NAME"

# 4. Integrate Plymouth into Dracut & rebuild initramfs (crucial for clean shutdown)
echo "🔄 [4/7] Configuring dracut and rebuilding initramfs..."
sudo mkdir -p /etc/dracut.conf.d
echo 'add_dracutmodules+=" plymouth "' | sudo tee /etc/dracut.conf.d/plymouth.conf >/dev/null

if command -v dracut-rebuild &>/dev/null; then
    sudo dracut-rebuild
elif command -v dracut &>/dev/null; then
    sudo dracut -f
elif command -v mkinitcpio &>/dev/null; then
    sudo mkinitcpio -P
fi

# 5. Allow passwordless sudo for plymouth quit during handover
echo "🔑 [5/7] Configuring sudoers permission for seamless Hyprlock quit..."
echo "meobanh ALL=(ALL) NOPASSWD: /usr/bin/plymouth" | sudo tee /etc/sudoers.d/99-plymouth >/dev/null
sudo chmod 0440 /etc/sudoers.d/99-plymouth

# 6. Configure systemd: seamless boot handover & completely silent fast shutdown
echo "🛡️  [6/7] Configuring systemd handover & silent shutdown..."
sudo systemctl unmask plymouth-quit.service plymouth-quit-wait.service 2>/dev/null || true

# 6a. Boot handover: Keep Plymouth animating smoothly until Hyprland starts (no early freeze or 2s gap)
sudo mkdir -p /etc/systemd/system/plymouth-quit.service.d
cat << 'EOF' | sudo tee /etc/systemd/system/plymouth-quit.service.d/override.conf >/dev/null
[Unit]
Description=Hold Plymouth until Hyprland starts

[Service]
ExecStart=
ExecStart=-/usr/bin/true
EOF

# 6b. Quit-wait override: don't block getty once plymouth has deactivated
sudo mkdir -p /etc/systemd/system/plymouth-quit-wait.service.d
cat << 'EOF' | sudo tee /etc/systemd/system/plymouth-quit-wait.service.d/override.conf >/dev/null
[Service]
ExecStart=
ExecStart=-/usr/bin/true
EOF

# 6c. Fast natural shutdown (remove any sleep delays)
sudo rm -rf /etc/systemd/system/plymouth-poweroff.service.d
sudo rm -rf /etc/systemd/system/plymouth-reboot.service.d

# 6d. Silence kernel printk, watchdog and systemd logs completely during shutdown
sudo mkdir -p /etc/sysctl.d
echo 'kernel.printk = 3 3 3 3' | sudo tee /etc/sysctl.d/20-quiet-printk.conf >/dev/null

sudo mkdir -p /etc/modprobe.d
cat << 'EOF' | sudo tee /etc/modprobe.d/nowatchdog.conf >/dev/null
blacklist iTCO_wdt
blacklist iTCO_vendor_support
blacklist intel_oc_wdt
EOF

sudo mkdir -p /etc/systemd/system.conf.d
cat << 'EOF' | sudo tee /etc/systemd/system.conf.d/silent.conf >/dev/null
[Manager]
ShowStatus=no
LogLevel=err
LogTarget=journal
EOF

# 6e. Silence TTY1 login completely (no corner terminal artifacts)
sudo mkdir -p /etc/systemd/system/getty@tty1.service.d
cat << 'EOF' | sudo tee /etc/systemd/system/getty@tty1.service.d/autologin.conf >/dev/null
[Service]
ExecStart=
ExecStart=-/usr/bin/agetty -o '-p -f -- \u' --skip-login --nonewline --noissue --nohints --nohostname --noclear --noreset --autologin meobanh %I $TERM
TTYVTDisallocate=no
Type=idle
StandardInput=tty
StandardOutput=null
StandardError=null
EOF

# Ensure ~/.zprofile and ~/.bash_profile do not run clear (prevents 80x25 corner terminal glitch)
sed -i '/^[[:blank:]]*clear[[:blank:]]*$/d' "$HOME/.zprofile" 2>/dev/null || true
sed -i '/^[[:blank:]]*clear[[:blank:]]*$/d' "$HOME/.bash_profile" 2>/dev/null || true

touch "$HOME/.hushlogin"
sudo systemctl daemon-reload

# 7. Update GRUB: Clean background, eliminate echo lines & silence kernel text
echo "🔧 [7/7] Checking GRUB configuration..."

# 7a. Suppress the two "echo 'Loading Linux ...'" and "echo 'Loading initial ramdisk ...'" lines in GRUB scripts
if [ -f /etc/grub.d/10_linux ]; then
    echo "  -> Removing 'Loading Linux ...' and 'Loading initial ramdisk ...' echo lines from /etc/grub.d/10_linux..."
    sudo sed -i -E 's/^\techo\t.*message.*grub_quote.*/\t# echo suppressed/g' /etc/grub.d/10_linux
fi
if [ -f /etc/grub.d/20_linux_xen ]; then
    sudo sed -i -E 's/^\techo\t.*message.*grub_quote.*/\t# echo suppressed/g' /etc/grub.d/20_linux_xen 2>/dev/null || true
fi

# 7b. Neutralize EndeavourOS purple splash image so no component can ever load it
if [ -f /usr/share/endeavouros/splash.png ]; then
    if [ ! -f /usr/share/endeavouros/splash.png.bak ]; then
        echo "  -> Backing up original purple EndeavourOS splash to /usr/share/endeavouros/splash.png.bak..."
        sudo cp -f /usr/share/endeavouros/splash.png /usr/share/endeavouros/splash.png.bak
    fi
    echo "  -> Neutralizing /usr/share/endeavouros/splash.png with dark stage background..."
    sudo cp -f "$THEME_SRC/background.png" /usr/share/endeavouros/splash.png
fi

if [ -f /etc/default/grub ]; then
    # Disable EndeavourOS splash image in GRUB so it doesn't leave stray buffers
    sudo sed -i "s|^GRUB_BACKGROUND=.*|#GRUB_BACKGROUND=''|" /etc/default/grub

    TARGET_CMDLINE="nowatchdog nvme_load=YES loglevel=3 quiet splash rd.udev.log_priority=3 vt.global_cursor_default=0 systemd.show_status=0 rd.systemd.show_status=0 fbcon=nodefer"
    sudo sed -i "s|^GRUB_CMDLINE_LINUX_DEFAULT=.*|GRUB_CMDLINE_LINUX_DEFAULT='${TARGET_CMDLINE}'|" /etc/default/grub

    echo "🔄 Updating GRUB configuration..."
    sudo grub-mkconfig -o /boot/grub/grub.cfg
fi

echo -e "\n✨ HOÀN TẤT! Đã cài đặt hoàn chỉnh Spotlight Theme."
echo "1. Đèn chính giữa giờ sẽ bật sáng rực rỡ và các đèn phụ cách đều nhau không bị lỗi hình."
echo "2. Chuyển cảnh sang Hyprlock mượt mà 100% không còn màn hình tím/chữ EndeavourOS."
echo "3. Khi tắt máy, toàn bộ ánh đèn sẽ mờ dần về đen cùng lúc trong ~0.6s và tắt tự nhiên trong 1-2s, KHÔNG HIỆN MÀN TERMINAL!"
