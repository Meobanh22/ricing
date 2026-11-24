#!/usr/bin/env bash
# sync.sh — Serena Dotfiles configuration synchronization tool.

set -e

# Resolve repository directory (works with symlinks)
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"

if [ -d "$SCRIPT_DIR/config" ]; then
    REPO_ROOT="$SCRIPT_DIR"
elif [ -d "$SCRIPT_DIR/../config" ]; then
    REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
else
    REPO_ROOT="$SCRIPT_DIR"
fi

DOTFILES_DIR="$REPO_ROOT/config"
ASSETS_DIR="$REPO_ROOT/assets"

# Display colors
RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
PINK='\033[1;35m'
BLUE='\033[1;34m'
CYAN='\033[1;36m'
NC='\033[0m'

# === PUSH: REPO -> SYSTEM (~/.config) ===
sync_push() {
    local no_reload="${1:-false}"
    echo -e "${PINK}=== SYNCHRONIZING CONFIG: REPO -> SYSTEM (~/.config) ===${NC}\n"

    # Compile Single Source of Truth tokens (tokens.json)
    BUILD_SCRIPT="$REPO_ROOT/scripts/build_theme.py"
    if [ -f "$BUILD_SCRIPT" ]; then
        python3 "$BUILD_SCRIPT" || true
    fi

    # Generate Poké Puff icons from theme tokens
    POKEPUFF_SCRIPT="$REPO_ROOT/scripts/generate_pokepuffs.py"
    if [ -f "$POKEPUFF_SCRIPT" ]; then
        python3 "$POKEPUFF_SCRIPT" || true
    fi

    # Create destination directories
    mkdir -p "$HOME/.config/hypr/scripts/popups"
    mkdir -p "$HOME/.config/hypr/scripts/terminal"
    mkdir -p "$HOME/.config/hypr/scripts/widgets"
    mkdir -p "$HOME/.config/hypr/scripts/services"
    mkdir -p "$HOME/.config/hypr/scripts/system"
    mkdir -p "$HOME/.config/hypr/scripts/ui_core"
    mkdir -p "$HOME/.config/hypr/styles"
    mkdir -p "$HOME/.config/hypr/assets"
    mkdir -p "$HOME/.config/waybar"
    mkdir -p "$HOME/.config/rofi"
    mkdir -p "$HOME/.config/kitty"
    mkdir -p "$HOME/.config/wlogout"
    mkdir -p "$HOME/.config/swaync"
    mkdir -p "$HOME/.config/btop/themes"
    mkdir -p "$HOME/.config/cava"
    mkdir -p "$HOME/.config/fastfetch"
    mkdir -p "$HOME/.config/gtk-3.0"
    mkdir -p "$HOME/.config/gtk-4.0"
    mkdir -p "$HOME/.config/Thunar"
    mkdir -p "$HOME/.config/fcitx5/conf"
    mkdir -p "$HOME/.icons"
    mkdir -p "$HOME/.local/share/icons"
    mkdir -p "$HOME/Pictures/wallpapers"

    # Synchronize tracked configurations
    echo -e "${YELLOW}📦 [1/4] Synchronizing configuration files...${NC}"

    # Clean up obsolete flat scripts and relocated services
    rm -f "$HOME/.config/hypr/scripts/"*.py "$HOME/.config/hypr/scripts/"*.sh "$HOME/.config/hypr/scripts/"*.bak 2>/dev/null || true
    rm -f "$HOME/.config/hypr/scripts/services/music"*.py 2>/dev/null || true
    rm -rf "$HOME/.config/hypr/scripts/ui_core/components" 2>/dev/null || true
    rm -f "$HOME/.config/hypr/styles/dashboard.css" 2>/dev/null || true

    # Hyprland (Native hyprland.lua engine, remove legacy hyprland.conf)
    cp -rf "$DOTFILES_DIR/hypr/"* "$HOME/.config/hypr/"
    rm -f "$HOME/.config/hypr/hyprland.conf"
    chmod +x "$HOME/.config/hypr/scripts/popups/"* "$HOME/.config/hypr/scripts/terminal/"* "$HOME/.config/hypr/scripts/widgets/"* "$HOME/.config/hypr/scripts/services/"* "$HOME/.config/hypr/scripts/system/"* "$HOME/.config/hypr/scripts/ui_core/"* 2>/dev/null || true
    echo -e "  ${GREEN}✔ Hyprland (hyprland.lua, hyprlock.conf, scripts/)${NC}"

    # Waybar
    cp -rf "$DOTFILES_DIR/waybar/"* "$HOME/.config/waybar/"
    echo -e "  ${GREEN}✔ Waybar (config.jsonc, style.css, palette.css)${NC}"

    # Rofi
    cp -rf "$DOTFILES_DIR/rofi/"* "$HOME/.config/rofi/"
    mkdir -p "$HOME/.config/rofiSearch" 2>/dev/null || true
    cp -f "$DOTFILES_DIR/rofi/config.rasi" "$HOME/.config/rofiSearch/config.rasi" 2>/dev/null || true
    echo -e "  ${GREEN}✔ Rofi (config.rasi, colors-rofi.rasi)${NC}"

    # Kitty Terminal
    cp -rf "$DOTFILES_DIR/kitty/"* "$HOME/.config/kitty/"
    echo -e "  ${GREEN}✔ Kitty Terminal (kitty.conf)${NC}"

    # Wlogout
    cp -rf "$DOTFILES_DIR/wlogout/"* "$HOME/.config/wlogout/"
    echo -e "  ${GREEN}✔ Wlogout (layout, style.css, icons/)${NC}"

    # SwayNC
    cp -rf "$DOTFILES_DIR/swaync/"* "$HOME/.config/swaync/"
    echo -e "  ${GREEN}✔ SwayNC (config.json, style.css, palette.css)${NC}"

    # Swappy
    if [ -d "$DOTFILES_DIR/swappy" ]; then
        mkdir -p "$HOME/.config/swappy"
        cp -rf "$DOTFILES_DIR/swappy/"* "$HOME/.config/swappy/"
        echo -e "  ${GREEN}✔ Swappy (config)${NC}"
    fi

    # Btop
    cp -rf "$DOTFILES_DIR/btop/"* "$HOME/.config/btop/"
    echo -e "  ${GREEN}✔ Btop (btop.conf, obsidian-wine.theme)${NC}"

    # Cava
    if [ -d "$DOTFILES_DIR/cava" ]; then
        mkdir -p "$HOME/.config/cava"
        cp -rf "$DOTFILES_DIR/cava/"* "$HOME/.config/cava/"
        echo -e "  ${GREEN}✔ Cava Audio Visualizer (config)${NC}"
    fi

    # Fastfetch
    if [ -d "$DOTFILES_DIR/fastfetch" ]; then
        cp -rf "$DOTFILES_DIR/fastfetch/"* "$HOME/.config/fastfetch/"
        echo -e "  ${GREEN}✔ Fastfetch (config.jsonc, sylveon_chibi.txt)${NC}"
    fi

    # Starship Prompt
    if [ -f "$DOTFILES_DIR/starship/starship.toml" ]; then
        cp -f "$DOTFILES_DIR/starship/starship.toml" "$HOME/.config/starship.toml"
        echo -e "  ${GREEN}✔ Starship Prompt (starship.toml)${NC}"
    fi

    # Desktop Entries & Local Music Launchers
    if [ -d "$DOTFILES_DIR/applications" ]; then
        mkdir -p "$HOME/.local/share/applications"
        cp -rf "$DOTFILES_DIR/applications/"* "$HOME/.local/share/applications/"
        command -v update-desktop-database &>/dev/null && update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
        echo -e "  ${GREEN}✔ Desktop entries (~/.local/share/applications/)${NC}"
    fi
    mkdir -p "$HOME/.local/bin"
    cat > "$HOME/.local/bin/music" << 'MUSIC_EOF'
#!/usr/bin/env bash
# music — Terminal Music Visualizer & Synced Lyrics
exec python3 "$HOME/.config/hypr/scripts/terminal/music.py" "$@"
MUSIC_EOF
    chmod +x "$HOME/.local/bin/music"
    ln -sf "$HOME/.config/hypr/scripts/terminal/open_music_player.sh" "$HOME/.local/bin/music-player"
    echo -e "  ${GREEN}✔ Music launchers (~/.local/bin/music, music-player)${NC}"

    # GTK-3.0 & GTK-4.0
    if [ -d "$DOTFILES_DIR/gtk-3.0" ]; then
        cp -rf "$DOTFILES_DIR/gtk-3.0/"* "$HOME/.config/gtk-3.0/"
        if [ -f "$DOTFILES_DIR/gtk-3.0/bookmarks" ]; then
            sed "s|\$HOME|$HOME|g" "$DOTFILES_DIR/gtk-3.0/bookmarks" > "$HOME/.config/gtk-3.0/bookmarks"
        fi
        echo -e "  ${GREEN}✔ GTK-3.0 (gtk.css, settings.ini, bookmarks)${NC}"
    fi
    if [ -d "$DOTFILES_DIR/gtk-4.0" ]; then
        cp -rf "$DOTFILES_DIR/gtk-4.0/"* "$HOME/.config/gtk-4.0/"
        echo -e "  ${GREEN}✔ GTK-4.0 (gtk.css, settings.ini)${NC}"
    fi

    # Thunar Custom Actions
    if [ -d "$DOTFILES_DIR/Thunar" ]; then
        cp -rf "$DOTFILES_DIR/Thunar/"* "$HOME/.config/Thunar/"
        echo -e "  ${GREEN}✔ Thunar File Manager (uca.xml)${NC}"
    fi

    # Fcitx5 Input Method
    if [ -d "$DOTFILES_DIR/fcitx5" ]; then
        cp -rf "$DOTFILES_DIR/fcitx5/"* "$HOME/.config/fcitx5/"
        echo -e "  ${GREEN}✔ Fcitx5 (config, profile, conf/)${NC}"
    fi

    # Firefox UI Rice & user.js
    if [ -d "$DOTFILES_DIR/firefox" ]; then
        for MOZ_DIR in "$HOME/.config/mozilla/firefox" "$HOME/.mozilla/firefox"; do
            if [ -d "$MOZ_DIR" ]; then
                for PROFILE_DIR in "$MOZ_DIR"/*.default*; do
                    if [ -d "$PROFILE_DIR" ]; then
                        mkdir -p "$PROFILE_DIR/chrome"
                        cp -rf "$DOTFILES_DIR/firefox/chrome/"* "$PROFILE_DIR/chrome/" 2>/dev/null || true
                        cp -f "$DOTFILES_DIR/firefox/user.js" "$PROFILE_DIR/user.js" 2>/dev/null || true
                    fi
                done
            fi
        done
        echo -e "  ${GREEN}✔ Firefox (userChrome.css, palette.css, user.js)${NC}"
    fi

    # Theme tokens Single Source of Truth
    if [ -d "$DOTFILES_DIR/theme" ]; then
        mkdir -p "$HOME/.config/hypr/theme"
        cp -rf "$DOTFILES_DIR/theme/"* "$HOME/.config/hypr/theme/"
        echo -e "  ${GREEN}✔ Theme tokens (tokens.json)${NC}"
    fi

    # Synchronize Cursors, Avatars & Wallpapers
    echo -e "\n${YELLOW}🖱️  [2/4] Checking cursors, avatars & wallpapers...${NC}"
    if [ -d "$ASSETS_DIR/cursors/sylveon-custom" ]; then
        cp -rf "$ASSETS_DIR/cursors/sylveon-custom" "$HOME/.icons/"
        cp -rf "$ASSETS_DIR/cursors/sylveon-custom" "$HOME/.local/share/icons/"
        echo -e "  ${GREEN}✔ Sylveon Custom cursor theme updated (~/.icons & ~/.local/share/icons)${NC}"
    fi

    if [ -d "$ASSETS_DIR/wallpapers" ]; then
        cp -rn "$ASSETS_DIR/wallpapers/"* "$HOME/Pictures/wallpapers/" 2>/dev/null || true
        echo -e "  ${GREEN}✔ Wallpapers directory (~/Pictures/wallpapers/)${NC}"

        # Ensure current wallpaper link/file exists for Hyprlock background
        mkdir -p "$HOME/.config/hypr/wallpaper_effects"
        if [ ! -f "$HOME/.config/hypr/wallpaper_effects/.wallpaper_current" ]; then
            if [ -f "$HOME/Pictures/wallpapers/serena_fennekin_wallpaper_grass_fixed.png" ]; then
                cp -f "$HOME/Pictures/wallpapers/serena_fennekin_wallpaper_grass_fixed.png" "$HOME/.config/hypr/wallpaper_effects/.wallpaper_current"
            elif [ -f "$ASSETS_DIR/wallpapers/serena_fennekin_wallpaper_grass_fixed.png" ]; then
                cp -f "$ASSETS_DIR/wallpapers/serena_fennekin_wallpaper_grass_fixed.png" "$HOME/.config/hypr/wallpaper_effects/.wallpaper_current"
            fi
        fi
    fi

    if [ -d "$ASSETS_DIR/avatars" ]; then
        cp -rf "$ASSETS_DIR/avatars/"* "$HOME/.config/hypr/assets/" 2>/dev/null || true
        echo -e "  ${GREEN}✔ Avatars (~/.config/hypr/assets/)${NC}"
    fi

    if [ -d "$ASSETS_DIR/pokemon" ]; then
        mkdir -p "$HOME/.config/hypr/assets/pokemon"
        cp -rf "$ASSETS_DIR/pokemon/"* "$HOME/.config/hypr/assets/pokemon/" 2>/dev/null || true
        cp -rf "$ASSETS_DIR/pokemon/"* "$HOME/.config/hypr/assets/" 2>/dev/null || true
        echo -e "  ${GREEN}✔ Pokemon sprites (~/.config/hypr/assets/)${NC}"
    fi

    if [ -d "$ASSETS_DIR/banners" ]; then
        mkdir -p "$HOME/.config/hypr/assets/banners"
        cp -rf "$ASSETS_DIR/banners/"* "$HOME/.config/hypr/assets/banners/" 2>/dev/null || true
        cp -rf "$ASSETS_DIR/banners/"* "$HOME/.config/hypr/assets/" 2>/dev/null || true
        echo -e "  ${GREEN}✔ Cover banners (~/.config/hypr/assets/)${NC}"
    fi

    if [ -d "$ASSETS_DIR/illustrations" ]; then
        mkdir -p "$HOME/.config/hypr/assets/illustrations"
        cp -rn "$ASSETS_DIR/illustrations/"* "$HOME/.config/hypr/assets/illustrations/" 2>/dev/null || true
        echo -e "  ${GREEN}✔ Minimalist illustrations (~/.config/hypr/assets/illustrations/)${NC}"
    fi

    if [ -d "$ASSETS_DIR/icons" ]; then
        mkdir -p "$HOME/.config/hypr/assets/icons"
        cp -rf "$ASSETS_DIR/icons/"* "$HOME/.config/hypr/assets/icons/" 2>/dev/null || true
        cp -rf "$ASSETS_DIR/icons/"* "$HOME/.config/hypr/assets/" 2>/dev/null || true
        echo -e "  ${GREEN}✔ Vector icons (~/.config/hypr/assets/icons/)${NC}"
    fi

    # Reload Live Compositor & Services
    if [ "$no_reload" = "true" ]; then
        echo -e "\n${YELLOW}⚡ [3/4] Skipping live reload (--no-reload).${NC}"
    else
        echo -e "\n${YELLOW}⚡ [3/4] Live reloading compositor & interface services...${NC}"
    fi
    if [ "$no_reload" != "true" ] && { [ "$XDG_CURRENT_DESKTOP" = "Hyprland" ] || pgrep -x "Hyprland" &>/dev/null; }; then
        hyprctl reload &>/dev/null || true
        echo -e "  ${GREEN}✔ Hyprland reloaded!${NC}"

        if pgrep -x "waybar" &>/dev/null; then
            pkill -SIGUSR2 waybar 2>/dev/null || (pkill -x waybar && sleep 0.3 && hyprctl dispatch exec waybar &>/dev/null)
            echo -e "  ${GREEN}✔ Waybar reloaded!${NC}"
        else
            hyprctl dispatch exec waybar &>/dev/null || (nohup waybar >/dev/null 2>&1 & disown)
            echo -e "  ${GREEN}✔ Waybar started!${NC}"
        fi

        if command -v fcitx5-remote &>/dev/null && pgrep -x "fcitx5" &>/dev/null; then
            fcitx5-remote -r 2>/dev/null || true
            echo -e "  ${GREEN}✔ Fcitx5 reloaded!${NC}"
        fi

        if pgrep -x "kitty" &>/dev/null; then
            pkill -USR1 kitty 2>/dev/null || true
            echo -e "  ${GREEN}✔ Kitty Terminal palette reloaded!${NC}"
        fi

        if pgrep -x "swaync" &>/dev/null; then
            swaync-client -R -rs &>/dev/null || true
            echo -e "  ${GREEN}✔ SwayNC reloaded!${NC}"
        fi

        if pgrep -f "desktop_widgets.py" &>/dev/null; then
            pkill -f "desktop_widgets.py" 2>/dev/null || true
            sleep 0.2
            hyprctl dispatch exec "python3 $HOME/.config/hypr/scripts/widgets/desktop_widgets.py" &>/dev/null || \
            setsid -f python3 "$HOME/.config/hypr/scripts/widgets/desktop_widgets.py" >/dev/null 2>&1
            echo -e "  ${GREEN}✔ Desktop widgets reloaded!${NC}"
        else
            hyprctl dispatch exec "python3 $HOME/.config/hypr/scripts/widgets/desktop_widgets.py" &>/dev/null || \
            setsid -f python3 "$HOME/.config/hypr/scripts/widgets/desktop_widgets.py" >/dev/null 2>&1
            echo -e "  ${GREEN}✔ Desktop widgets started!${NC}"
        fi

        hyprctl setcursor sylveon-custom 24 &>/dev/null || true

        gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark' 2>/dev/null || true
        gsettings set org.gnome.desktop.interface font-name 'JetBrains Mono 11' 2>/dev/null || true
        echo -e "  ${GREEN}✔ GTK theme & dark mode refreshed (gsettings)${NC}"
    fi

    echo -e "\n${PINK}=== SYNCHRONIZATION COMPLETE! All changes are live! ===${NC}\n"
}

# === PULL: SYSTEM (~/.config) -> REPO ===
sync_pull() {
    echo -e "${CYAN}=== PULLING CHANGES: SYSTEM (~/.config) -> REPO ===${NC}\n"

    # Hyprland (keep only clean Serena rice dotfiles)
    if [ -d "$HOME/.config/hypr" ]; then
        mkdir -p "$DOTFILES_DIR/hypr"
        for item in hyprland.lua palette.lua palette.conf hyprlock.conf hypridle.conf serena_lock_avatar.png; do
            [ -f "$HOME/.config/hypr/$item" ] && cp -f "$HOME/.config/hypr/$item" "$DOTFILES_DIR/hypr/"
        done
        for dir in styles scripts; do
            [ -d "$HOME/.config/hypr/$dir" ] && cp -rf "$HOME/.config/hypr/$dir" "$DOTFILES_DIR/hypr/"
        done
        if [ -d "$HOME/.config/hypr/theme" ]; then
            mkdir -p "$DOTFILES_DIR/theme"
            cp -rf "$HOME/.config/hypr/theme/"* "$DOTFILES_DIR/theme/"
        fi
        rm -rf "$DOTFILES_DIR/hypr/UserConfigs" "$DOTFILES_DIR/hypr/UserScripts" \
               "$DOTFILES_DIR/hypr/animations" "$DOTFILES_DIR/hypr/configs" \
               "$DOTFILES_DIR/hypr/Monitor_Profiles" "$DOTFILES_DIR/hypr/wallust" \
               "$DOTFILES_DIR/hypr/wallpaper_effects" "$DOTFILES_DIR/hypr/v2.3.20" \
               "$DOTFILES_DIR/hypr/hyprland.conf" 2>/dev/null || true
        echo -e "  ${GREEN}✔ Pulled ~/.config/hypr/ -> repo${NC}"
    fi

    # Waybar
    if [ -d "$HOME/.config/waybar" ]; then
        mkdir -p "$DOTFILES_DIR/waybar"
        for item in config.jsonc style.css palette.css; do
            [ -f "$HOME/.config/waybar/$item" ] && cp -f "$HOME/.config/waybar/$item" "$DOTFILES_DIR/waybar/"
        done
        echo -e "  ${GREEN}✔ Pulled ~/.config/waybar/ -> repo${NC}"
    fi

    # Rofi
    if [ -d "$HOME/.config/rofi" ]; then
        mkdir -p "$DOTFILES_DIR/rofi"
        for item in config.rasi colors-rofi.rasi; do
            [ -f "$HOME/.config/rofi/$item" ] && cp -f "$HOME/.config/rofi/$item" "$DOTFILES_DIR/rofi/"
        done
        echo -e "  ${GREEN}✔ Pulled ~/.config/rofi/ -> repo${NC}"
    fi

    # Kitty
    if [ -d "$HOME/.config/kitty" ]; then
        cp -rf "$HOME/.config/kitty/"* "$DOTFILES_DIR/kitty/"
        echo -e "  ${GREEN}✔ Pulled ~/.config/kitty/ -> repo${NC}"
    fi

    # Wlogout
    if [ -d "$HOME/.config/wlogout" ]; then
        cp -rf "$HOME/.config/wlogout/"* "$DOTFILES_DIR/wlogout/"
        echo -e "  ${GREEN}✔ Pulled ~/.config/wlogout/ -> repo${NC}"
    fi

    # SwayNC
    if [ -d "$HOME/.config/swaync" ]; then
        cp -rf "$HOME/.config/swaync/"* "$DOTFILES_DIR/swaync/"
        echo -e "  ${GREEN}✔ Pulled ~/.config/swaync/ -> repo${NC}"
    fi

    # Swappy
    if [ -d "$HOME/.config/swappy" ]; then
        mkdir -p "$DOTFILES_DIR/swappy"
        cp -rf "$HOME/.config/swappy/"* "$DOTFILES_DIR/swappy/"
        echo -e "  ${GREEN}✔ Pulled ~/.config/swappy/ -> repo${NC}"
    fi

    # Btop
    if [ -d "$HOME/.config/btop" ]; then
        cp -rf "$HOME/.config/btop/"* "$DOTFILES_DIR/btop/"
        echo -e "  ${GREEN}✔ Pulled ~/.config/btop/ -> repo${NC}"
    fi

    # Cava (sync only managed config, ignore built-in shaders/themes)
    if [ -f "$HOME/.config/cava/config" ]; then
        mkdir -p "$DOTFILES_DIR/cava"
        cp -f "$HOME/.config/cava/config" "$DOTFILES_DIR/cava/config"
        echo -e "  ${GREEN}✔ Pulled ~/.config/cava/config -> repo${NC}"
    fi

    # Starship Prompt
    if [ -f "$HOME/.config/starship.toml" ]; then
        mkdir -p "$DOTFILES_DIR/starship"
        cp -f "$HOME/.config/starship.toml" "$DOTFILES_DIR/starship/starship.toml"
        echo -e "  ${GREEN}✔ Pulled ~/.config/starship.toml -> repo${NC}"
    fi

    # Desktop Entries
    if [ -f "$HOME/.local/share/applications/serena-player.desktop" ]; then
        mkdir -p "$DOTFILES_DIR/applications"
        cp -f "$HOME/.local/share/applications/serena-player.desktop" "$DOTFILES_DIR/applications/serena-player.desktop"
        echo -e "  ${GREEN}✔ Pulled serena-player.desktop -> repo${NC}"
    fi

    # Fastfetch
    if [ -d "$HOME/.config/fastfetch" ]; then
        mkdir -p "$DOTFILES_DIR/fastfetch"
        cp -rf "$HOME/.config/fastfetch/"* "$DOTFILES_DIR/fastfetch/"
        echo -e "  ${GREEN}✔ Pulled ~/.config/fastfetch/ -> repo${NC}"
    fi

    # GTK-3.0 & GTK-4.0
    if [ -d "$HOME/.config/gtk-3.0" ]; then
        mkdir -p "$DOTFILES_DIR/gtk-3.0"
        cp -rf "$HOME/.config/gtk-3.0/"* "$DOTFILES_DIR/gtk-3.0/"
        if [ -f "$DOTFILES_DIR/gtk-3.0/bookmarks" ]; then
            sed -i "s|file:///home/[^/]*|file://\$HOME|g" "$DOTFILES_DIR/gtk-3.0/bookmarks"
        fi
        echo -e "  ${GREEN}✔ Pulled ~/.config/gtk-3.0/ -> repo${NC}"
    fi
    if [ -d "$HOME/.config/gtk-4.0" ]; then
        mkdir -p "$DOTFILES_DIR/gtk-4.0"
        cp -rf "$HOME/.config/gtk-4.0/"* "$DOTFILES_DIR/gtk-4.0/"
        echo -e "  ${GREEN}✔ Pulled ~/.config/gtk-4.0/ -> repo${NC}"
    fi

    # Thunar
    if [ -d "$HOME/.config/Thunar" ]; then
        mkdir -p "$DOTFILES_DIR/Thunar"
        cp -rf "$HOME/.config/Thunar/"* "$DOTFILES_DIR/Thunar/"
        echo -e "  ${GREEN}✔ Pulled ~/.config/Thunar/ -> repo${NC}"
    fi

    # Fcitx5
    if [ -d "$HOME/.config/fcitx5" ]; then
        mkdir -p "$DOTFILES_DIR/fcitx5"
        cp -rf "$HOME/.config/fcitx5/"* "$DOTFILES_DIR/fcitx5/"
        rm -f "$DOTFILES_DIR/fcitx5/conf/ngosen-app-rules.conf" "$DOTFILES_DIR/fcitx5/cached_layouts" "$DOTFILES_DIR/fcitx5/"*.bak 2>/dev/null || true
        echo -e "  ${GREEN}✔ Pulled ~/.config/fcitx5/ -> repo${NC}"
    fi

    echo -e "\n${CYAN}=== PULL COMPLETE! Use 'git status' or 'git diff' to review. ===${NC}\n"
}

# === DIFF: COMPARE REPO AND SYSTEM ===
sync_diff() {
    echo -e "${YELLOW}🔍 Comparing differences between Repo and ~/.config...${NC}\n"
    diff -rq -x 'UserConfigs' -x 'UserScripts' -x 'animations' -x 'configs' -x 'Monitor_Profiles' -x 'wallust' -x 'wallpaper_effects' -x 'v2.3.20' -x 'hyprland.conf' -x '__pycache__' -x 'theme' -x 'assets' "$DOTFILES_DIR/hypr" "$HOME/.config/hypr" 2>/dev/null || true
    diff -rq "$DOTFILES_DIR/waybar" "$HOME/.config/waybar" 2>/dev/null || true
    diff -rq "$DOTFILES_DIR/rofi" "$HOME/.config/rofi" 2>/dev/null || true
    diff -rq "$DOTFILES_DIR/kitty" "$HOME/.config/kitty" 2>/dev/null || true
    diff -rq "$DOTFILES_DIR/wlogout" "$HOME/.config/wlogout" 2>/dev/null || true
    diff -rq "$DOTFILES_DIR/swaync" "$HOME/.config/swaync" 2>/dev/null || true
    diff -rq "$DOTFILES_DIR/btop" "$HOME/.config/btop" 2>/dev/null || true
    diff -rq -x 'shaders' -x 'themes' "$DOTFILES_DIR/cava" "$HOME/.config/cava" 2>/dev/null || true
    diff -rq "$DOTFILES_DIR/fastfetch" "$HOME/.config/fastfetch" 2>/dev/null || true
    if [ -f "$DOTFILES_DIR/starship/starship.toml" ] || [ -f "$HOME/.config/starship.toml" ]; then
        diff -u "$DOTFILES_DIR/starship/starship.toml" "$HOME/.config/starship.toml" 2>/dev/null || true
    fi
    if [ -f "$DOTFILES_DIR/applications/serena-player.desktop" ] || [ -f "$HOME/.local/share/applications/serena-player.desktop" ]; then
        diff -u "$DOTFILES_DIR/applications/serena-player.desktop" "$HOME/.local/share/applications/serena-player.desktop" 2>/dev/null || true
    fi
    diff -rq -x 'bookmarks' "$DOTFILES_DIR/gtk-3.0" "$HOME/.config/gtk-3.0" 2>/dev/null || true
    if [ -f "$DOTFILES_DIR/gtk-3.0/bookmarks" ] && [ -f "$HOME/.config/gtk-3.0/bookmarks" ]; then
        diff -u <(sed "s|\\\$HOME|$HOME|g" "$DOTFILES_DIR/gtk-3.0/bookmarks") "$HOME/.config/gtk-3.0/bookmarks" || true
    fi
    diff -rq "$DOTFILES_DIR/gtk-4.0" "$HOME/.config/gtk-4.0" 2>/dev/null || true
    diff -rq -x 'accels.scm' "$DOTFILES_DIR/Thunar" "$HOME/.config/Thunar" 2>/dev/null || true
    diff -rq -x 'cached_layouts' -x '*.bak' -x 'ngosen-app-rules.conf' "$DOTFILES_DIR/fcitx5" "$HOME/.config/fcitx5" 2>/dev/null || true
    diff -rq "$DOTFILES_DIR/swappy" "$HOME/.config/swappy" 2>/dev/null || true
    diff -rq "$DOTFILES_DIR/theme" "$HOME/.config/hypr/theme" 2>/dev/null || true
    for MOZ_DIR in "$HOME/.config/mozilla/firefox" "$HOME/.mozilla/firefox"; do
        if [ -d "$MOZ_DIR" ]; then
            for PROFILE_DIR in "$MOZ_DIR"/*.default*; do
                if [ -d "$PROFILE_DIR" ]; then
                    diff -u "$DOTFILES_DIR/firefox/user.js" "$PROFILE_DIR/user.js" 2>/dev/null || true
                    for f in palette.css userChrome.css userContent.css; do
                        diff -u "$DOTFILES_DIR/firefox/chrome/$f" "$PROFILE_DIR/chrome/$f" 2>/dev/null || true
                    done
                fi
            done
        fi
    done
    echo -e "\n${GREEN}✔ Diff scan completed!${NC}"
}

# === COMMAND ROUTER ===
case "$1" in
    --pull|-p|pull)
        sync_pull
        ;;
    --diff|-d|diff)
        sync_diff
        ;;
    --no-reload)
        sync_push true
        ;;
    --help|-h|help)
        echo -e "${PINK}Usage:${NC} $0 [options]"
        echo -e "  ${GREEN}(no flags)${NC}      : Push configs from Repo -> ~/.config and reload live"
        echo -e "  ${GREEN}--no-reload${NC}     : Push configs from Repo -> ~/.config without reloading services"
        echo -e "  ${YELLOW}--pull / pull${NC}  : Pull changes from ~/.config -> Repo"
        echo -e "  ${BLUE}--diff / diff${NC}  : Compare differences between Repo and ~/.config"
        echo -e "  ${CYAN}--help / help${NC}  : Show this help message"
        ;;
    *)
        sync_push false
        ;;
esac
