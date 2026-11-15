#!/usr/bin/env python3
# build_theme.py — Compile single-source tokens.json to all component formats.

import json
import os
import sys

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    tokens_path = os.path.join(root_dir, "config", "theme", "tokens.json")

    if not os.path.exists(tokens_path):
        # Alternative search
        alt_path = os.path.expanduser("~/.config/hypr/theme/tokens.json")
        if os.path.exists(alt_path):
            tokens_path = alt_path
        else:
            print(f"Error: tokens.json not found at {tokens_path}")
            sys.exit(1)

    with open(tokens_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_colors = data.get("colors", {})
    gradient_str = data.get("gradient") or data.get("gradients", {}).get("sunset", "linear-gradient(to bottom, #A3183D 0%, #E53262 25%, #FF7299 50%, #EAA2C6 75%, #BE7AA8 100%)")
    typo = data.get("typography", {})
    geo = data.get("geometry", {})
    hypr_base = os.path.join(root_dir, "config")

    print("Compiling design tokens from tokens.json")

    def hex_to_rgba_str(h, alpha=1.0):
        h = h.strip().lstrip('#')
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        if alpha >= 1.0:
            return f"rgb({r}, {g}, {b})"
        return f"rgba({r}, {g}, {b}, {alpha:.2f})"

    def hex_to_hypr(h, alpha_hex="ff"):
        h = h.strip().lstrip('#')
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        return f"rgba({h}{alpha_hex})"

    def hex_to_hypr_rgb(h):
        h = h.strip().lstrip('#')
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        return f"rgb({h.upper()})"

    # Primitive color tokens (without semantic role names)
    dark_wine   = raw_colors.get("dark_wine",   raw_colors.get("bg_window", "#201011"))
    deep_wine   = raw_colors.get("deep_wine",   raw_colors.get("bg_card", "#2A1A1E"))
    soft_wine   = raw_colors.get("soft_wine",   raw_colors.get("bg_subtle", "#301F20"))
    light_wine  = raw_colors.get("light_wine",  raw_colors.get("bg_card_hover", "#3A222A"))
    dark_ruby   = raw_colors.get("dark_ruby",   raw_colors.get("border_waybar_3d", "#4D0A1C"))
    wine_red    = raw_colors.get("wine_red",    raw_colors.get("bg_waybar", "#851733"))
    vivid_red   = raw_colors.get("vivid_red",   raw_colors.get("accent", "#DC1A36"))
    light_red   = raw_colors.get("light_red",   raw_colors.get("accent_hover", "#F02D4C"))
    vivid_pink  = raw_colors.get("vivid_pink",  raw_colors.get("pokepuff_pink", "#FF5C8A"))
    soft_pink   = raw_colors.get("soft_pink",   raw_colors.get("text_secondary", "#E8C2D0"))
    muted_pink  = raw_colors.get("muted_pink",  raw_colors.get("text_muted", "#A68595"))
    cream_white = raw_colors.get("cream_white", raw_colors.get("text_primary", "#FFF0F5"))
    pure_white  = raw_colors.get("pure_white",  raw_colors.get("text_inverse", "#FFFFFF"))
    sky_blue    = raw_colors.get("sky_blue",    raw_colors.get("ribbon_blue", "#50A6FF"))
    light_cyan  = raw_colors.get("light_cyan",  raw_colors.get("screen_cyan", "#87F0FF"))
    warm_yellow = raw_colors.get("warm_yellow", raw_colors.get("status_warning", "#FFB86C"))
    soft_green  = raw_colors.get("soft_green",  raw_colors.get("status_success", "#8FBC8F"))

    # Map to complete semantic UI dictionary for Waybar, GTK, Hyprland, etc.
    colors = {
        "bg_window": dark_wine,
        "bg_window_alpha": hex_to_rgba_str(dark_wine, 0.98),
        "bg_window_hypr": hex_to_hypr(dark_wine, "fa"),
        "bg_card": deep_wine,
        "bg_card_alpha": hex_to_rgba_str(deep_wine, 0.95),
        "bg_card_hypr": hex_to_hypr(deep_wine, "f2"),
        "bg_card_hover": light_wine,
        "bg_card_hover_alpha": hex_to_rgba_str(light_wine, 0.98),
        "bg_card_hover_hypr": hex_to_hypr(light_wine, "fa"),
        "bg_subtle": soft_wine,
        "bg_subtle_alpha": hex_to_rgba_str(soft_wine, 0.95),
        "bg_subtle_hypr": hex_to_hypr(soft_wine, "f2"),
        "bg_ghost": "transparent",
        "bg_ghost_hover": hex_to_rgba_str(deep_wine, 0.50),
        "border_window": "rgba(255, 255, 255, 0.12)",
        "border_window_hypr": "rgba(ffffff1f)",
        "border_card": "rgba(255, 255, 255, 0.12)",
        "border_card_hypr": "rgba(ffffff1f)",
        "border_card_hover": hex_to_rgba_str(vivid_red, 0.65),
        "border_card_hover_hypr": hex_to_hypr(vivid_red, "a6"),
        "accent": vivid_red,
        "accent_hypr": hex_to_hypr_rgb(vivid_red),
        "accent_hover": light_red,
        "accent_hover_hypr": hex_to_hypr_rgb(light_red),
        "accent_dim": hex_to_rgba_str(vivid_red, 0.48),
        "accent_subtle": hex_to_rgba_str(vivid_red, 0.20),
        "accent_border": hex_to_rgba_str(vivid_red, 0.40),
        "text_primary": cream_white,
        "text_primary_hypr": hex_to_hypr_rgb(cream_white),
        "text_secondary": soft_pink,
        "text_secondary_hypr": hex_to_hypr_rgb(soft_pink),
        "text_muted": muted_pink,
        "text_muted_hypr": hex_to_hypr_rgb(muted_pink),
        "text_inverse": pure_white,
        "text_inverse_hypr": hex_to_hypr_rgb(pure_white),
        "status_warning": warm_yellow,
        "status_warning_hypr": hex_to_hypr_rgb(warm_yellow),
        "status_critical": vivid_red,
        "status_critical_hypr": hex_to_hypr_rgb(vivid_red),
        "status_success": soft_green,
        "status_success_hypr": hex_to_hypr_rgb(soft_green),
        "ribbon_blue": sky_blue,
        "ribbon_blue_alpha": hex_to_rgba_str(sky_blue, 0.95),
        "ribbon_blue_hypr": hex_to_hypr_rgb(sky_blue),
        "screen_cyan": light_cyan,
        "screen_cyan_alpha": hex_to_rgba_str(light_cyan, 0.55),
        "screen_cyan_hypr": hex_to_hypr_rgb(light_cyan),
        "bg_waybar": wine_red,
        "bg_waybar_hover": "#9C2241",
        "bg_waybar_hypr": hex_to_hypr(wine_red, "f2"),
        "border_waybar_3d": dark_ruby,
        "border_waybar_3d_hover": "#610E24",
        "border_waybar_3d_hypr": hex_to_hypr_rgb(dark_ruby),
        "shadow_extrusion": dark_ruby,
        "shadow_extrusion_hover": "#610E24",
        "shadow_extrusion_hypr": hex_to_hypr_rgb(dark_ruby),
        "border_tactile_white": "rgba(255, 255, 255, 0.65)",
        "border_tactile_white_bright": "rgba(255, 255, 255, 0.90)",
        "bg_tactile_cream": hex_to_rgba_str(cream_white, 0.96),
        "bg_tactile_cream_hypr": hex_to_hypr(cream_white, "f5"),
        "pokepuff_pink": vivid_pink,
        "pokepuff_pink_hypr": hex_to_hypr_rgb(vivid_pink),
        
        # Color primitives
        "dark_wine": dark_wine,
        "deep_wine": deep_wine,
        "soft_wine": soft_wine,
        "light_wine": light_wine,
        "dark_ruby": dark_ruby,
        "wine_red": wine_red,
        "vivid_red": vivid_red,
        "light_red": light_red,
        "vivid_pink": vivid_pink,
        "soft_pink": soft_pink,
        "muted_pink": muted_pink,
        "cream_white": cream_white,
        "pure_white": pure_white,
        "sky_blue": sky_blue,
        "light_cyan": light_cyan,
        "warm_yellow": warm_yellow,
        "soft_green": soft_green,
    }

    grad_sunset = gradient_str
    grad_sunset_hover = gradient_str

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

@define-color scrollbar_slider {colors.get('accent_dim', colors['accent'])};
@define-color scrollbar_slider_hover {colors['accent']};

@define-color text_primary {colors['text_primary']};
@define-color text_secondary {colors['text_secondary']};
@define-color text_muted {colors['text_muted']};
@define-color text_inverse {colors['text_inverse']};
@define-color text_white {colors['text_inverse']};

@define-color status_warning {colors['status_warning']};
@define-color status_critical {colors['status_critical']};
@define-color status_success {colors['status_success']};

@define-color ribbon_blue {colors['ribbon_blue']};
@define-color screen_cyan {colors.get('screen_cyan', '#87F0FF')};
@define-color bg_tactile_cream {colors.get('bg_tactile_cream', 'rgba(255, 240, 245, 0.96)')};
@define-color pokepuff_pink {colors.get('pokepuff_pink', '#FF5C8A')};

@define-color bg_waybar {colors.get('bg_waybar', '#851733')};
@define-color bg_waybar_hover {colors.get('bg_waybar_hover', '#9C2241')};
@define-color border_waybar_3d {colors.get('border_waybar_3d', '#4D0A1C')};
@define-color border_waybar_3d_hover {colors.get('border_waybar_3d_hover', '#610E24')};
@define-color shadow_extrusion {colors.get('shadow_extrusion', '#4D0A1C')};
@define-color shadow_extrusion_hover {colors.get('shadow_extrusion_hover', '#610E24')};
@define-color border_tactile_white {colors.get('border_tactile_white', 'rgba(255, 255, 255, 0.65)')};
@define-color border_tactile_white_bright {colors.get('border_tactile_white_bright', 'rgba(255, 255, 255, 0.90)')};

/* === GRADIENTS === */
.gradient-sunset {{
    background-image: {grad_sunset};
}}
.gradient-sunset:hover,
.gradient-sunset-hover {{
    background-image: {grad_sunset_hover};
}}
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

@define-color scrollbar_slider {colors.get('accent_dim', colors['accent'])};
@define-color scrollbar_slider_hover {colors['accent']};

@define-color text_primary {colors['text_primary']};
@define-color text_secondary {colors['text_secondary']};
@define-color text_muted {colors['text_muted']};
@define-color text_inverse {colors['text_inverse']};
@define-color text_white {colors['text_inverse']};

@define-color status_warning {colors['status_warning']};
@define-color status_critical {colors['status_critical']};
@define-color status_success {colors['status_success']};

@define-color ribbon_blue {colors['ribbon_blue']};
@define-color screen_cyan {colors.get('screen_cyan', '#87F0FF')};
@define-color bg_tactile_cream {colors.get('bg_tactile_cream', 'rgba(255, 240, 245, 0.96)')};
@define-color pokepuff_pink {colors.get('pokepuff_pink', '#FF5C8A')};

@define-color bg_waybar {colors.get('bg_waybar', '#851733')};
@define-color bg_waybar_hover {colors.get('bg_waybar_hover', '#9C2241')};
@define-color border_waybar_3d {colors.get('border_waybar_3d', '#4D0A1C')};
@define-color border_waybar_3d_hover {colors.get('border_waybar_3d_hover', '#610E24')};
@define-color shadow_extrusion {colors.get('shadow_extrusion', '#4D0A1C')};
@define-color shadow_extrusion_hover {colors.get('shadow_extrusion_hover', '#610E24')};
@define-color border_tactile_white {colors.get('border_tactile_white', 'rgba(255, 255, 255, 0.65)')};
@define-color border_tactile_white_bright {colors.get('border_tactile_white_bright', 'rgba(255, 255, 255, 0.90)')};

/* === GRADIENTS === */
.gradient-sunset {{
    background-image: {grad_sunset};
}}
.gradient-sunset:hover,
.gradient-sunset-hover {{
    background-image: {grad_sunset_hover};
}}
"""
    with open(hypr_styles_palette, "w", encoding="utf-8") as f:
        f.write(hypr_styles_css)
    print("  ✔ Generated hypr/styles/palette.css")

    # GTK-3.0, GTK-4.0, SwayNC, Wlogout palettes
    for p in [
        os.path.join(hypr_base, "gtk-3.0", "palette.css"),
        os.path.join(hypr_base, "gtk-4.0", "palette.css"),
        os.path.join(hypr_base, "swaync", "palette.css"),
        os.path.join(hypr_base, "wlogout", "palette.css")
    ]:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(hypr_styles_css)
    print("  ✔ Generated gtk-3.0, gtk-4.0, swaync, wlogout palette.css")

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
$screen_cyan          = {colors.get('screen_cyan_hypr', 'rgb(87F0FF)')}
$bg_waybar            = {colors.get('bg_waybar_hypr', 'rgba(851733f2)')}
$border_waybar_3d     = {colors.get('border_waybar_3d_hypr', 'rgb(4D0A1C)')}
$shadow_extrusion     = {colors.get('shadow_extrusion_hypr', 'rgb(4D0A1C)')}
$bg_tactile_cream     = {colors.get('bg_tactile_cream_hypr', 'rgba(FFF0F5f5)')}
$pokepuff_pink        = {colors.get('pokepuff_pink_hypr', 'rgb(FF5C8A)')}
"""
    with open(hypr_palette, "w", encoding="utf-8") as f:
        f.write(hypr_content)
    print("  ✔ Generated hypr/palette.conf")

    hypr_lua = os.path.join(hypr_base, "hypr", "palette.lua")
    hypr_lua_content = f"""-- palette.lua — Color tokens for Hyprland (Lua engine).
-- NOTE: Generated from tokens.json. Do not edit directly.

return {{
    bg_window            = "{colors['bg_window_hypr']}",
    bg_card              = "{colors['bg_card_hypr']}",
    bg_card_hover        = "{colors['bg_card_hover_hypr']}",
    bg_subtle            = "{colors['bg_subtle_hypr']}",
    border_window        = "{colors['border_window_hypr']}",
    border_card          = "{colors['border_card_hypr']}",
    border_card_hover    = "{colors['border_card_hover_hypr']}",
    accent               = "{colors['accent_hypr']}",
    accent_hover         = "{colors['accent_hover_hypr']}",
    text_primary         = "{colors['text_primary_hypr']}",
    text_secondary       = "{colors['text_secondary_hypr']}",
    text_muted           = "{colors['text_muted_hypr']}",
    text_inverse         = "{colors['text_inverse_hypr']}",
    status_warning       = "{colors['status_warning_hypr']}",
    status_critical      = "{colors['status_critical_hypr']}",
    status_success       = "{colors['status_success_hypr']}",
    ribbon_blue          = "{colors['ribbon_blue_hypr']}",
    screen_cyan          = "{colors.get('screen_cyan_hypr', 'rgb(87F0FF)')}",
    bg_waybar            = "{colors.get('bg_waybar_hypr', 'rgba(851733f2)')}",
    border_waybar_3d     = "{colors.get('border_waybar_3d_hypr', 'rgb(4D0A1C)')}",
    shadow_extrusion     = "{colors.get('shadow_extrusion_hypr', 'rgb(4D0A1C)')}",
    bg_tactile_cream     = "{colors.get('bg_tactile_cream_hypr', 'rgba(FFF0F5f5)')}",
    pokepuff_pink        = "{colors.get('pokepuff_pink_hypr', 'rgb(FF5C8A)')}",
}}
"""
    with open(hypr_lua, "w", encoding="utf-8") as f:
        f.write(hypr_lua_content)
    print("  ✔ Generated hypr/palette.lua")

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
    screen-cyan:        {colors.get('screen_cyan', '#87F0FF')};
    bg-tactile-cream:   {colors.get('bg_tactile_cream', 'rgba(255, 240, 245, 0.96)')};
    pokepuff-pink:      {colors.get('pokepuff_pink', '#FF5C8A')};
}}
"""
    with open(rofi_palette, "w", encoding="utf-8") as f:
        f.write(rofi_content)
    print("  ✔ Generated rofi/colors-rofi.rasi")

    # 4. Python GTK palette.py
    py_palette = os.path.join(hypr_base, "hypr", "scripts", "system", "palette.py")
    py_content = f"""#!/usr/bin/env python3
# palette.py — Python design tokens.
# NOTE: Generated automatically. Do not edit directly.

PALETTE = {json.dumps(colors, indent=4, ensure_ascii=False)}

def hex_to_rgba(hex_code: str, alpha: float = 1.0):
    h = hex_code.strip().lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, float(alpha))

# Color hex constants
C_BG_WIN        = PALETTE.get("bg_window", "#201011")
C_BG_CARD       = PALETTE.get("bg_card", "#2A1A1E")
C_BG_CARD_HOVER = PALETTE.get("bg_card_hover", "#3A222A")
C_BG_SUBTLE     = PALETTE.get("bg_subtle", "#301F20")
C_ACCENT        = PALETTE.get("accent", "#DC1A36")
C_ACCENT_HOVER  = PALETTE.get("accent_hover", "#F02D4C")
C_TEXT_PRI      = PALETTE.get("text_primary", "#FFF0F5")
C_TEXT_SEC      = PALETTE.get("text_secondary", "#E8C2D0")
C_TEXT_MUT      = PALETTE.get("text_muted", "#A68595")
C_TEXT_INV      = PALETTE.get("text_inverse", "#FFFFFF")
C_STATUS_WARN   = PALETTE.get("status_warning", "#FFB86C")
C_STATUS_CRIT   = PALETTE.get("status_critical", "#DC1A36")
C_STATUS_SUCC   = PALETTE.get("status_success", "#8FBC8F")
C_RIBBON        = PALETTE.get("ribbon_blue", "#50A6FF")
C_SCREEN_CYAN   = PALETTE.get("screen_cyan", "#87F0FF")
C_BG_CREAM      = PALETTE.get("bg_tactile_cream", "rgba(255, 240, 245, 0.96)")
C_BG_WAYBAR     = PALETTE.get("bg_waybar", "#851733")
C_BG_WAYBAR_HOV = PALETTE.get("bg_waybar_hover", "#9C2241")
C_BORDER_3D     = PALETTE.get("border_waybar_3d", "#4D0A1C")
C_SHADOW_EXTR   = PALETTE.get("shadow_extrusion", "#4D0A1C")
C_SHADOW_EXTR_H = PALETTE.get("shadow_extrusion_hover", "#610E24")
C_POKEPUFF_PINK = PALETTE.get("pokepuff_pink", "#FF5C8A")
C_SUNSET_PINK   = "{colors.get('vivid_pink', '#FF7299') if colors.get('vivid_pink') == '#FF7299' else '#FF7299'}"
C_SUNSET_PASTEL = "#EAA2C6"

# Gradient Design Tokens
GRADIENTS = {{
    "sunset": "{grad_sunset}"
}}
SUNSET_STOPS = [
    (0.00, "#A3183D"),
    (0.25, "#E53262"),
    (0.50, "#FF7299"),
    (0.75, "#EAA2C6"),
    (1.00, "#BE7AA8")
]

# Pre-computed Cairo RGBA tuples
BG_WINDOW_RGBA        = hex_to_rgba(C_BG_WIN, 0.98)
BG_CARD_RGBA          = hex_to_rgba(C_BG_CARD, 0.95)
BG_CARD_HOVER_RGBA    = hex_to_rgba(C_BG_CARD_HOVER, 0.98)
BG_SUBTLE_RGBA        = hex_to_rgba(C_BG_SUBTLE, 0.95)
BG_WAYBAR_RGBA        = hex_to_rgba(C_BG_WAYBAR, 1.0)
SHADOW_EXTRUSION_RGBA = hex_to_rgba(C_SHADOW_EXTR, 1.0)
ACCENT_RGBA           = hex_to_rgba(C_ACCENT, 1.0)
ACCENT_HOVER_RGBA     = hex_to_rgba(C_ACCENT_HOVER, 1.0)
ACCENT_DIM_RGBA       = hex_to_rgba(C_ACCENT, 0.48)
ACCENT_SUBTLE_RGBA    = hex_to_rgba(C_ACCENT, 0.20)
POKEPUFF_PINK_RGBA    = hex_to_rgba(C_POKEPUFF_PINK, 1.0)
BORDER_WINDOW_RGBA    = (1.0, 1.0, 1.0, 0.12)
BORDER_CARD_RGBA      = (1.0, 1.0, 1.0, 0.12)
"""
    with open(py_palette, "w", encoding="utf-8") as f:
        f.write(py_content)
    print("  ✔ Generated hypr/scripts/system/palette.py")

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
            "separator": " • ",
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
                "format": "{user-name-colored} @ {host-name-colored}"
            },
            {
                "type": "separator",
                "string": "┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈",
                "outputColor": colors["text_muted"]
            },
            {
                "type": "os",
                "key": " OS"
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

    if os.path.exists(fastfetch_path):
        with open(fastfetch_path, "r", encoding="utf-8") as f:
            existing_fastfetch = json.load(f)
        display = existing_fastfetch.setdefault("display", {})
        display["color"] = fastfetch_data["display"]["color"]
        display.setdefault("percent", {})["color"] = fastfetch_data["display"]["percent"]["color"]
        display.setdefault("bar", {})["color"] = fastfetch_data["display"]["bar"]["color"]
        for module in existing_fastfetch.get("modules", []):
            if module.get("type") == "separator":
                module["outputColor"] = colors["text_muted"]
        fastfetch_data = existing_fastfetch

    with open(fastfetch_path, "w", encoding="utf-8") as f:
        json.dump(fastfetch_data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("  ✔ Updated fastfetch/config.jsonc colors")

    # 7. Kitty terminal kitty.conf
    kitty_path = os.path.join(hypr_base, "kitty", "kitty.conf")
    kitty_content = f"""# kitty.conf — Terminal configuration and color tokens.
# NOTE: Generated from tokens.json. Do not edit directly.

# === FONT & WINDOW ===
font_family JetBrainsMono Nerd Font
bold_font auto
italic_font auto
bold_italic_font auto
font_size 11.5

window_padding_width 8
remember_window_size no
initial_window_width 860
initial_window_height 540
background_opacity 0.94
dynamic_background_opacity yes
confirm_os_window_close 0
enable_audio_bell no
linux_display_server auto
shell zsh

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

    # 8. Firefox chrome/palette.css
    firefox_chrome_dir = os.path.join(hypr_base, "firefox", "chrome")
    os.makedirs(firefox_chrome_dir, exist_ok=True)
    firefox_palette = os.path.join(firefox_chrome_dir, "palette.css")
    firefox_palette_content = f"""/* palette.css — Color tokens for Firefox userChrome. */
/* NOTE: Generated from tokens.json. Do not edit directly. */

:root {{
    --bg-window: {colors['bg_window']};
    --bg-window-alpha: {colors['bg_window_alpha']};
    --bg-card: {colors['bg_card']};
    --bg-card-alpha: {colors['bg_card_alpha']};
    --bg-card-hover: {colors['bg_card_hover']};
    --bg-subtle: {colors['bg_subtle']};
    --bg-ghost: {colors['bg_ghost']};
    --bg-ghost-hover: {colors['bg_ghost_hover']};

    --border-window: {colors['border_window']};
    --border-card: {colors['border_card']};
    --border-card-hover: {colors['border_card_hover']};

    --accent: {colors['accent']};
    --accent-hover: {colors['accent_hover']};
    --accent-dim: {colors.get('accent_dim', colors['accent'])};
    --accent-subtle: {colors.get('accent_subtle', 'rgba(220, 26, 54, 0.20)')};

    --text-primary: {colors['text_primary']};
    --text-secondary: {colors['text_secondary']};
    --text-muted: {colors['text_muted']};
    --text-inverse: {colors['text_inverse']};

    --status-warning: {colors['status_warning']};
    --status-critical: {colors['status_critical']};
    --status-success: {colors['status_success']};

    --radius-window: {geo.get('radius_window', 16)}px;
    --radius-card: {geo.get('radius_card', 10)}px;
    --radius-button: {geo.get('radius_button', 8)}px;
    --font-primary: "{typo.get('font_primary', 'JetBrains Mono Nerd Font')}";
}}
"""
    with open(firefox_palette, "w", encoding="utf-8") as f:
        f.write(firefox_palette_content)
    print("  ✔ Generated firefox/chrome/palette.css")

    # Also update any live Firefox profiles if found
    for mozilla_base in [os.path.expanduser("~/.config/mozilla/firefox"), os.path.expanduser("~/.mozilla/firefox")]:
        if os.path.isdir(mozilla_base):
            for entry in os.listdir(mozilla_base):
                if entry.endswith(".default-release") or entry.endswith(".default"):
                    profile_chrome = os.path.join(mozilla_base, entry, "chrome")
                    os.makedirs(profile_chrome, exist_ok=True)
                    with open(os.path.join(profile_chrome, "palette.css"), "w", encoding="utf-8") as f:
                        f.write(firefox_palette_content)

    print("  ✔ Generated repository theme files")

if __name__ == "__main__":
    main()

