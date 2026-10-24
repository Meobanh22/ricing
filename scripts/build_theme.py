#!/usr/bin/env python3
# build_theme.py — Compile single-source tokens.json to all component formats.

import json
import os
import sys

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    tokens_path = os.path.join(root_dir, "hyprland-serena", "theme", "tokens.json")

    if not os.path.exists(tokens_path):
        # Alternative search
        alt_path = os.path.join(os.path.dirname(root_dir), "theme", "tokens.json")
        if os.path.exists(alt_path):
            tokens_path = alt_path
        else:
            print(f"Error: tokens.json not found at {tokens_path}")
            sys.exit(1)

    with open(tokens_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    colors = data["colors"]
    typo = data.get("typography", {})
    geo = data.get("geometry", {})
    hypr_base = os.path.join(root_dir, "hyprland-serena")

    print("Compiling design tokens from tokens.json")

    # 1. Waybar & GTK CSS palette
    waybar_palette = os.path.join(hypr_base, "waybar", "palette.css")
    css_content = f"""/* palette.css — Color tokens for Waybar. */
/* NOTE: Generated from tokens.json. Do not edit directly. */

@define-color bg_window {colors['bg_window_alpha']};
@define-color bg_card {colors['bg_card_alpha']};
@define-color bg_card_hover {colors['bg_card_hover_alpha']};
@define-color bg_subtle {colors['bg_subtle_alpha']};
@define-color bg_ghost {colors['bg_ghost']};
@define-color bg_ghost_hover {colors['bg_ghost_hover']};

@define-color border_window {colors['border_window']};
@define-color border_card {colors['border_card']};
@define-color border_card_hover {colors['border_card_hover']};

@define-color accent {colors['accent']};
@define-color accent_hover {colors['accent_hover']};
@define-color text_primary {colors['text_primary']};
@define-color text_secondary {colors['text_secondary']};
@define-color text_muted {colors['text_muted']};
@define-color text_inverse {colors['text_inverse']};
@define-color text_white {colors['text_inverse']};

@define-color status_warning {colors['status_warning']};
@define-color status_critical {colors['status_critical']};
@define-color status_success {colors['status_success']};

@define-color ribbon_blue {colors['ribbon_blue']};
"""
    with open(waybar_palette, "w", encoding="utf-8") as f:
        f.write(css_content)
    print("  ✔ Generated waybar/palette.css")

    # Hypr GTK styles palette
    hypr_styles_dir = os.path.join(hypr_base, "hypr", "styles")
    os.makedirs(hypr_styles_dir, exist_ok=True)
    hypr_styles_palette = os.path.join(hypr_styles_dir, "palette.css")
    hypr_styles_css = f"""/* palette.css — Color tokens for Hypr GTK styles. */
/* NOTE: Generated from tokens.json. Do not edit directly. */

@define-color bg_window {colors['bg_window_alpha']};
@define-color bg_card {colors['bg_card_alpha']};
@define-color bg_card_hover {colors['bg_card_hover_alpha']};
@define-color bg_subtle {colors['bg_subtle_alpha']};
@define-color bg_ghost {colors['bg_ghost']};
@define-color bg_ghost_hover {colors['bg_ghost_hover']};

@define-color border_window {colors['border_window']};
@define-color border_card {colors['border_card']};
@define-color border_card_hover {colors['border_card_hover']};

@define-color accent {colors['accent']};
@define-color accent_hover {colors['accent_hover']};
@define-color text_primary {colors['text_primary']};
@define-color text_secondary {colors['text_secondary']};
@define-color text_muted {colors['text_muted']};
@define-color text_inverse {colors['text_inverse']};
@define-color text_white {colors['text_inverse']};

@define-color status_warning {colors['status_warning']};
@define-color status_critical {colors['status_critical']};
@define-color status_success {colors['status_success']};

@define-color ribbon_blue {colors['ribbon_blue']};
"""
    with open(hypr_styles_palette, "w", encoding="utf-8") as f:
        f.write(hypr_styles_css)
    print("  ✔ Generated hypr/styles/palette.css")

    # 2. Hyprland palette.conf
    hypr_palette = os.path.join(hypr_base, "hypr", "palette.conf")
    hypr_content = f"""# palette.conf — Color tokens for Hyprland.
# NOTE: Generated from tokens.json. Do not edit directly.

$bg_window            = {colors['bg_window_hypr']}
$bg_card              = {colors['bg_card_hypr']}
$bg_card_hover        = {colors['bg_card_hover_hypr']}
$bg_subtle            = {colors['bg_subtle_hypr']}
$border_window        = {colors['border_window_hypr']}
$border_card          = {colors['border_card_hypr']}
$border_card_hover    = {colors['border_card_hover_hypr']}
$accent               = {colors['accent_hypr']}
$accent_hover         = {colors['accent_hover_hypr']}
$text_primary         = {colors['text_primary_hypr']}
$text_secondary       = {colors['text_secondary_hypr']}
$text_muted           = {colors['text_muted_hypr']}
$text_inverse         = {colors['text_inverse_hypr']}
$status_warning       = {colors['status_warning_hypr']}
$status_critical      = {colors['status_critical_hypr']}
$status_success       = {colors['status_success_hypr']}
$ribbon_blue          = {colors['ribbon_blue_hypr']}
"""
    with open(hypr_palette, "w", encoding="utf-8") as f:
        f.write(hypr_content)
    print("  ✔ Generated hypr/palette.conf")

    # 3. Rofi colors-rofi.rasi
    rofi_palette = os.path.join(hypr_base, "rofi", "colors-rofi.rasi")
    rofi_content = f"""/* colors-rofi.rasi — Color tokens for Rofi. */
/* NOTE: Generated from tokens.json. Do not edit directly. */

* {{
    bg-window:          {colors['bg_window_alpha']};
    bg-card:            {colors['bg_card_alpha']};
    bg-card-hover:      {colors['bg_card_hover_alpha']};
    bg-subtle:          {colors['bg_subtle_alpha']};
    bg-ghost:           {colors['bg_ghost']};
    bg-ghost-hover:     {colors['bg_ghost_hover']};

    border-window:      {colors['border_window']};
    border-card:        {colors['border_card']};
    border-card-hover:  {colors['border_card_hover']};

    accent:             {colors['accent']};
    accent-hover:       {colors['accent_hover']};
    text-primary:       {colors['text_primary']};
    text-secondary:     {colors['text_secondary']};
    text-muted:         {colors['text_muted']};
    text-inverse:       {colors['text_inverse']};
    text-white:         {colors['text_inverse']};

    status-warning:     {colors['status_warning']};
    status-critical:    {colors['status_critical']};
    status-success:     {colors['status_success']};

    ribbon-blue:        {colors['ribbon_blue']};
}}
"""
    with open(rofi_palette, "w", encoding="utf-8") as f:
        f.write(rofi_content)
    print("  ✔ Generated rofi/colors-rofi.rasi")

    # 4. Python GTK palette.py
    py_palette = os.path.join(hypr_base, "hypr", "scripts", "palette.py")
    py_content = f"""#!/usr/bin/env python3
# palette.py — Python design tokens.
# NOTE: Generated from tokens.json. Do not edit directly.

PALETTE = {{
    "bg_window": "{colors['bg_window']}",
    "bg_window_alpha": "{colors['bg_window_alpha']}",
    "bg_card": "{colors['bg_card']}",
    "bg_card_alpha": "{colors['bg_card_alpha']}",
    "bg_card_hover": "{colors['bg_card_hover']}",
    "bg_card_hover_alpha": "{colors['bg_card_hover_alpha']}",
    "bg_subtle": "{colors['bg_subtle']}",
    "bg_subtle_alpha": "{colors['bg_subtle_alpha']}",
    "bg_ghost": "{colors['bg_ghost']}",
    "bg_ghost_hover": "{colors['bg_ghost_hover']}",

    "border_window": "{colors['border_window']}",
    "border_card": "{colors['border_card']}",
    "border_card_hover": "{colors['border_card_hover']}",

    "accent": "{colors['accent']}",
    "accent_hover": "{colors['accent_hover']}",

    "text_primary": "{colors['text_primary']}",
    "text_secondary": "{colors['text_secondary']}",
    "text_muted": "{colors['text_muted']}",
    "text_inverse": "{colors['text_inverse']}",

    "status_warning": "{colors['status_warning']}",
    "status_critical": "{colors['status_critical']}",
    "status_success": "{colors['status_success']}",

    "ribbon_blue": "{colors['ribbon_blue']}",
}}
"""
    with open(py_palette, "w", encoding="utf-8") as f:
        f.write(py_content)
    print("  ✔ Generated hypr/scripts/palette.py")

    # 5. btop theme
    btop_theme = os.path.join(hypr_base, "btop", "themes", "obsidian-wine.theme")
    btop_content = f"""# obsidian-wine.theme — Color tokens for btop.
# NOTE: Generated from tokens.json. Do not edit directly.

theme[main_bg]="{colors['bg_window']}"
theme[main_fg]="{colors['text_primary']}"
theme[title]="{colors['accent']}"
theme[hi_fg]="{colors['accent_hover']}"

theme[selected_bg]="{colors['accent']}"
theme[selected_fg]="{colors['text_inverse']}"

theme[inactive_fg]="{colors['text_muted']}"

theme[graph_text]="{colors['text_secondary']}"
theme[meter_bg]="{colors['bg_card']}"
theme[proc_misc]="{colors['accent_hover']}"

theme[cpu_box]="{colors['accent']}"
theme[mem_box]="{colors['accent_hover']}"
theme[net_box]="{colors['text_secondary']}"
theme[proc_box]="{colors['text_muted']}"
theme[div_line]="{colors['bg_card_hover']}"

theme[temp_start]="{colors['text_secondary']}"
theme[temp_mid]="{colors['accent_hover']}"
theme[temp_end]="{colors['accent']}"

theme[cpu_start]="{colors['text_muted']}"
theme[cpu_mid]="{colors['accent_hover']}"
theme[cpu_end]="{colors['accent']}"

theme[free_start]="{colors['text_muted']}"
theme[free_mid]="{colors['text_secondary']}"
theme[free_end]="{colors['text_primary']}"

theme[cached_start]="{colors['text_muted']}"
theme[cached_mid]="{colors['text_secondary']}"
theme[cached_end]="{colors['text_primary']}"

theme[available_start]="{colors['text_muted']}"
theme[available_mid]="{colors['text_secondary']}"
theme[available_end]="{colors['text_primary']}"

theme[used_start]="{colors['text_muted']}"
theme[used_mid]="{colors['text_secondary']}"
theme[used_end]="{colors['text_primary']}"

theme[download_start]="{colors['text_muted']}"
theme[download_mid]="{colors['accent_hover']}"
theme[download_end]="{colors['accent']}"

theme[upload_start]="{colors['text_muted']}"
theme[upload_mid]="{colors['accent_hover']}"
theme[upload_end]="{colors['accent']}"
"""
    with open(btop_theme, "w", encoding="utf-8") as f:
        f.write(btop_content)
    print("  ✔ Generated btop/themes/obsidian-wine.theme")

    # 6. Fastfetch config.jsonc
    fastfetch_dir = os.path.join(root_dir, "fastfetch")
    if not os.path.exists(fastfetch_dir):
        fastfetch_dir = os.path.join(hypr_base, "fastfetch")
    os.makedirs(fastfetch_dir, exist_ok=True)
    fastfetch_path = os.path.join(fastfetch_dir, "config.jsonc")

    fastfetch_data = {
        "$schema": "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json",
        "logo": {
            "type": "file",
            "source": "~/.config/fastfetch/sylveon_chibi.txt",
            "padding": {
                "top": 1,
                "right": 2
            }
        },
        "display": {
            "separator": " ✿ ",
            "color": {
                "keys": colors["accent"],
                "title": colors["accent_hover"],
                "separator": colors["text_secondary"],
                "output": colors["text_primary"]
            },
            "percent": {
                "color": {
                    "green": colors["ribbon_blue"],
                    "yellow": colors["accent_hover"],
                    "red": colors["accent"]
                }
            },
            "bar": {
                "color": {
                    "elapsed": colors["accent"],
                    "total": colors["bg_card_hover"],
                    "border": colors["text_muted"]
                }
            }
        },
        "modules": [
            {
                "type": "title",
                "format": "✿ {user-name-colored} @ {host-name-colored} ✿"
            },
            {
                "type": "separator",
                "string": "┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈",
                "outputColor": colors["text_muted"]
            },
            {
                "type": "os",
                "key": " OS",
                "format": "{2} {9} LTS"
            },
            {
                "type": "host",
                "key": "󰌢 Host",
                "format": "HP Pavilion x360"
            },
            {
                "type": "uptime",
                "key": "󱑂 Uptime"
            },
            {
                "type": "shell",
                "key": " Shell"
            },
            {
                "type": "terminal",
                "key": " Terminal"
            },
            {
                "type": "cpu",
                "key": " CPU",
                "format": "Intel i5-1135G7 ({4}) @ {7}"
            },
            {
                "type": "gpu",
                "key": "󰾲 GPU",
                "format": "{2}"
            },
            {
                "type": "memory",
                "key": "󰍛 Memory",
                "format": "{1} / {2} ({3})"
            },
            {
                "type": "disk",
                "key": " Disk",
                "folders": "/",
                "format": "{1} / {2} ({3})"
            },
            {
                "type": "battery",
                "key": " Battery",
                "format": "{4} [{5}]"
            },
            {
                "type": "separator",
                "string": "┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈",
                "outputColor": colors["text_muted"]
            },
            {
                "type": "colors",
                "symbol": "circle"
            }
        ]
    }

    with open(fastfetch_path, "w", encoding="utf-8") as f:
        json.dump(fastfetch_data, f, indent=2, ensure_ascii=False)
    print("  ✔ Generated fastfetch/config.jsonc")

    # Also update ~/.config/fastfetch/ if directory exists and is writable
    user_fastfetch_dir = os.path.expanduser("~/.config/fastfetch")
    if os.path.exists(user_fastfetch_dir):
        try:
            user_config_path = os.path.join(user_fastfetch_dir, "config.jsonc")
            with open(user_config_path, "w", encoding="utf-8") as f:
                json.dump(fastfetch_data, f, indent=2, ensure_ascii=False)
            for variant in ["config-compact.jsonc", "config-v2.jsonc", "config-pokemon.jsonc"]:
                variant_path = os.path.join(user_fastfetch_dir, variant)
                if os.path.exists(variant_path):
                    with open(variant_path, "w", encoding="utf-8") as f:
                        json.dump(fastfetch_data, f, indent=2, ensure_ascii=False)
            print("  ✔ Synchronized ~/.config/fastfetch/ configs")
        except OSError:
            pass

    # 7. Kitty terminal kitty.conf
    kitty_path = os.path.join(hypr_base, "kitty", "kitty.conf")
    kitty_content = f"""# kitty.conf — Terminal configuration and color tokens.
# NOTE: Generated from tokens.json. Do not edit directly.

# === FONT & WINDOW ===
font_family JetBrainsMono Nerd Font
bold_font auto
italic_font auto
bold_italic_font auto
font_size 12.0

window_padding_width 12
remember_window_size no
initial_window_width 860
initial_window_height 540
background_opacity 0.94
dynamic_background_opacity yes
confirm_os_window_close 0
enable_audio_bell no
linux_display_server auto

# === CURSOR ===
cursor {colors['accent']}
cursor_text_color {colors['bg_window']}
cursor_shape beam
cursor_trail 1

# === COLORS ===
background {colors['bg_window']}
foreground {colors['text_primary']}
selection_background {colors['accent']}
selection_foreground {colors['text_inverse']}

# === ANSI COLORS ===
# Black
color0 {colors['bg_window']}
color8 {colors['bg_card_hover']}

# Red
color1 {colors['accent']}
color9 {colors['accent_hover']}

# Green
color2 {colors['ribbon_blue']}
color10 {colors['ribbon_blue']}

# Yellow
color3 {colors['accent_hover']}
color11 {colors['accent_hover']}

# Blue
color4 {colors['ribbon_blue']}
color12 {colors['ribbon_blue']}

# Magenta
color5 {colors['text_secondary']}
color13 {colors['text_secondary']}

# Cyan
color6 {colors['ribbon_blue']}
color14 {colors['text_muted']}

# White
color7 {colors['text_primary']}
color15 {colors['text_inverse']}
"""
    with open(kitty_path, "w", encoding="utf-8") as f:
        f.write(kitty_content)
    print("  ✔ Generated kitty/kitty.conf")

    user_kitty_dir = os.path.expanduser("~/.config/kitty")
    if os.path.exists(user_kitty_dir):
        try:
            with open(os.path.join(user_kitty_dir, "kitty.conf"), "w", encoding="utf-8") as f:
                f.write(kitty_content)
            print("  ✔ Synchronized ~/.config/kitty/kitty.conf")
        except OSError:
            pass

    print("✨ All components synchronized with Single Source of Truth successfully!")

if __name__ == "__main__":
    main()

