#!/usr/bin/env python3
# build_theme.py — Compile single-source tokens.json to all component formats.

import json
import os
import re
import sys


def parse_gradient_stops(gradient_str, fallback):
    """Extract (offset_float, '#HEX') pairs from a CSS linear-gradient string."""
    matches = re.findall(r'(#[0-9A-Fa-f]{6})\s+(\d+(?:\.\d+)?)%', gradient_str or "")
    if not matches:
        return fallback
    return [(float(pct) / 100.0, hex_col.upper()) for hex_col, pct in matches]


def hex_to_rgba_str(h, alpha=1.0):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    if alpha >= 1.0:
        return f"rgb({r}, {g}, {b})"
    return f"rgba({r}, {g}, {b}, {alpha:.2f})"


def hex_to_hypr(h, alpha_hex="ff"):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return f"rgba({h}{alpha_hex})"


def hex_to_hypr_rgb(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return f"rgb({h.upper()})"


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    tokens_path = os.path.join(root_dir, "config", "theme", "tokens.json")

    if not os.path.exists(tokens_path):
        alt_path = os.path.expanduser("~/.config/hypr/theme/tokens.json")
        if os.path.exists(alt_path):
            tokens_path = alt_path
        else:
            print(f"Error: tokens.json not found at {tokens_path}")
            sys.exit(1)

    with open(tokens_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_colors = data.get("colors", {})
    gradient_str = data.get(
        "gradient",
        "linear-gradient(to bottom, #A3183D 0%, #E53262 25%, #FF7299 50%, #EAA2C6 75%, #BE7AA8 100%)",
    )
    gradient_hover_str = data.get(
        "gradient_hover",
        "linear-gradient(to bottom, #B52048 0%, #F04070 25%, #FF80A6 50%, #F2B2D2 75%, #CA8BB4 100%)",
    )
    typo = data.get("typography", {})
    geo = data.get("geometry", {})
    hypr_base = os.path.join(root_dir, "config")

    print("Compiling design tokens from tokens.json")

    # Canonical color primitives from tokens.json
    dark_wine = raw_colors.get("dark_wine", "#201011")
    deep_wine = raw_colors.get("deep_wine", "#2A1A1E")
    soft_wine = raw_colors.get("soft_wine", "#301F20")
    light_wine = raw_colors.get("light_wine", "#3A222A")
    dark_ruby = raw_colors.get("dark_ruby", "#4D0A1C")
    wine_red = raw_colors.get("wine_red", "#851733")
    vivid_red = raw_colors.get("vivid_red", "#DC1A36")
    light_red = raw_colors.get("light_red", "#F02D4C")
    vivid_pink = raw_colors.get("vivid_pink", "#FF5C8A")
    soft_pink = raw_colors.get("soft_pink", "#E8C2D0")
    muted_pink = raw_colors.get("muted_pink", "#A68595")
    cream_white = raw_colors.get("cream_white", "#FFF0F5")
    pure_white = raw_colors.get("pure_white", "#FFFFFF")
    sky_blue = raw_colors.get("sky_blue", "#50A6FF")
    light_cyan = raw_colors.get("light_cyan", "#87F0FF")
    warm_yellow = raw_colors.get("warm_yellow", "#FFB86C")
    soft_green = raw_colors.get("soft_green", "#8FBC8F")

    wine_red_hover = raw_colors.get("wine_red_hover", "#9C2241")
    dark_ruby_hover = raw_colors.get("dark_ruby_hover", "#610E24")

    # Pure swatch & derived opacity palette (no hardcoded UI roles)
    palette = {
        "dark_wine": dark_wine,
        "deep_wine": deep_wine,
        "soft_wine": soft_wine,
        "light_wine": light_wine,
        "dark_ruby": dark_ruby,
        "dark_ruby_hover": dark_ruby_hover,
        "wine_red": wine_red,
        "wine_red_hover": wine_red_hover,
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
        "dark_wine_98": hex_to_rgba_str(dark_wine, 0.98),
        "deep_wine_95": hex_to_rgba_str(deep_wine, 0.95),
        "deep_wine_50": hex_to_rgba_str(deep_wine, 0.50),
        "soft_wine_95": hex_to_rgba_str(soft_wine, 0.95),
        "light_wine_98": hex_to_rgba_str(light_wine, 0.98),
        "vivid_red_65": hex_to_rgba_str(vivid_red, 0.65),
        "vivid_red_48": hex_to_rgba_str(vivid_red, 0.48),
        "vivid_red_40": hex_to_rgba_str(vivid_red, 0.40),
        "vivid_red_20": hex_to_rgba_str(vivid_red, 0.20),
        "cream_white_96": hex_to_rgba_str(cream_white, 0.96),
        "pure_white_12": hex_to_rgba_str(pure_white, 0.12),
        "pure_white_65": hex_to_rgba_str(pure_white, 0.65),
        "pure_white_90": hex_to_rgba_str(pure_white, 0.90),
        "sky_blue_95": hex_to_rgba_str(sky_blue, 0.95),
        "light_cyan_55": hex_to_rgba_str(light_cyan, 0.55),
    }

    hypr_colors = {
        "dark_wine": hex_to_hypr_rgb(dark_wine),
        "deep_wine": hex_to_hypr_rgb(deep_wine),
        "soft_wine": hex_to_hypr_rgb(soft_wine),
        "light_wine": hex_to_hypr_rgb(light_wine),
        "dark_ruby": hex_to_hypr_rgb(dark_ruby),
        "wine_red": hex_to_hypr_rgb(wine_red),
        "vivid_red": hex_to_hypr_rgb(vivid_red),
        "light_red": hex_to_hypr_rgb(light_red),
        "vivid_pink": hex_to_hypr_rgb(vivid_pink),
        "soft_pink": hex_to_hypr_rgb(soft_pink),
        "muted_pink": hex_to_hypr_rgb(muted_pink),
        "cream_white": hex_to_hypr_rgb(cream_white),
        "pure_white": hex_to_hypr_rgb(pure_white),
        "sky_blue": hex_to_hypr_rgb(sky_blue),
        "light_cyan": hex_to_hypr_rgb(light_cyan),
        "warm_yellow": hex_to_hypr_rgb(warm_yellow),
        "soft_green": hex_to_hypr_rgb(soft_green),
        "dark_wine_98": hex_to_hypr(dark_wine, "fa"),
        "deep_wine_95": hex_to_hypr(deep_wine, "f2"),
        "soft_wine_95": hex_to_hypr(soft_wine, "f2"),
        "light_wine_98": hex_to_hypr(light_wine, "fa"),
        "wine_red_95": hex_to_hypr(wine_red, "f2"),
        "cream_white_96": hex_to_hypr(cream_white, "f5"),
        "pure_white_12": hex_to_hypr(pure_white, "1f"),
        "vivid_red_65": hex_to_hypr(vivid_red, "a6"),
    }

    grad_sunset = gradient_str
    grad_sunset_hover = gradient_hover_str
    sunset_stops = parse_gradient_stops(
        grad_sunset,
        [
            (0.00, "#A3183D"),
            (0.25, "#E53262"),
            (0.50, "#FF7299"),
            (0.75, "#EAA2C6"),
            (1.00, "#BE7AA8"),
        ],
    )
    sunset_pink = sunset_stops[2][1] if len(sunset_stops) > 2 else "#FF7299"
    sunset_pastel = sunset_stops[3][1] if len(sunset_stops) > 3 else "#EAA2C6"
    sunset_stops_repr = ",\n    ".join(f'({pos:.2f}, "{col}")' for pos, col in sunset_stops)

    css_define_block = f"""@define-color dark_wine {palette['dark_wine']};
@define-color deep_wine {palette['deep_wine']};
@define-color soft_wine {palette['soft_wine']};
@define-color light_wine {palette['light_wine']};
@define-color dark_ruby {palette['dark_ruby']};
@define-color dark_ruby_hover {palette['dark_ruby_hover']};
@define-color wine_red {palette['wine_red']};
@define-color wine_red_hover {palette['wine_red_hover']};
@define-color vivid_red {palette['vivid_red']};
@define-color light_red {palette['light_red']};
@define-color vivid_pink {palette['vivid_pink']};
@define-color soft_pink {palette['soft_pink']};
@define-color muted_pink {palette['muted_pink']};
@define-color cream_white {palette['cream_white']};
@define-color pure_white {palette['pure_white']};
@define-color sky_blue {palette['sky_blue']};
@define-color light_cyan {palette['light_cyan']};
@define-color warm_yellow {palette['warm_yellow']};
@define-color soft_green {palette['soft_green']};

@define-color dark_wine_98 {palette['dark_wine_98']};
@define-color deep_wine_95 {palette['deep_wine_95']};
@define-color deep_wine_50 {palette['deep_wine_50']};
@define-color soft_wine_95 {palette['soft_wine_95']};
@define-color light_wine_98 {palette['light_wine_98']};
@define-color cream_white_96 {palette['cream_white_96']};
@define-color pure_white_12 {palette['pure_white_12']};
@define-color pure_white_65 {palette['pure_white_65']};
@define-color pure_white_90 {palette['pure_white_90']};
@define-color vivid_red_65 {palette['vivid_red_65']};
@define-color vivid_red_48 {palette['vivid_red_48']};
@define-color vivid_red_40 {palette['vivid_red_40']};
@define-color vivid_red_20 {palette['vivid_red_20']};
@define-color sky_blue_95 {palette['sky_blue_95']};
@define-color light_cyan_55 {palette['light_cyan_55']};"""

    # 1. Waybar & GTK CSS palette
    waybar_palette = os.path.join(hypr_base, "waybar", "palette.css")
    css_content = f"""/* palette.css — Color tokens for Waybar. */
/* NOTE: Generated from tokens.json. Do not edit directly. */

{css_define_block}

/* === GRADIENTS === */
.gradient-sunset,
#custom-media,
#mpris {{
    background-image: {grad_sunset};
}}
.gradient-sunset:hover,
.gradient-sunset-hover,
#custom-media:hover,
#mpris:hover {{
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

{css_define_block}

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
        os.path.join(hypr_base, "wlogout", "palette.css"),
    ]:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(hypr_styles_css)
    print("  ✔ Generated gtk-3.0, gtk-4.0, swaync, wlogout palette.css")

    # 2. Hyprland palette.conf & palette.lua
    font_primary = typo.get("font_primary", "JetBrains Mono Nerd Font")
    font_stack = typo.get("font_stack", '"JetBrains Mono Nerd Font", "FiraCode Nerd Font", "Segoe UI", sans-serif')
    base_size = int(typo.get("base_size", 13))
    radius_window = int(geo.get("radius_window", 16))
    radius_card = int(geo.get("radius_card", 10))
    radius_button = int(geo.get("radius_button", 8))
    radius_badge = int(geo.get("radius_badge", 4))
    radius_scrollbar = int(geo.get("radius_scrollbar", 4))
    width_control_center = int(geo.get("width_control_center", 315))
    width_shelf = int(geo.get("width_shelf", 464))
    width_rofi = int(geo.get("width_rofi", 640))

    hypr_palette = os.path.join(hypr_base, "hypr", "palette.conf")
    hypr_content = f"""# palette.conf — Color, typography and geometry tokens for Hyprland.
# NOTE: Generated from tokens.json. Do not edit directly.

$dark_wine            = {hypr_colors['dark_wine']}
$deep_wine            = {hypr_colors['deep_wine']}
$soft_wine            = {hypr_colors['soft_wine']}
$light_wine           = {hypr_colors['light_wine']}
$dark_ruby            = {hypr_colors['dark_ruby']}
$wine_red             = {hypr_colors['wine_red']}
$vivid_red            = {hypr_colors['vivid_red']}
$light_red            = {hypr_colors['light_red']}
$vivid_pink           = {hypr_colors['vivid_pink']}
$soft_pink            = {hypr_colors['soft_pink']}
$muted_pink           = {hypr_colors['muted_pink']}
$cream_white          = {hypr_colors['cream_white']}
$pure_white           = {hypr_colors['pure_white']}
$sky_blue             = {hypr_colors['sky_blue']}
$light_cyan           = {hypr_colors['light_cyan']}
$warm_yellow          = {hypr_colors['warm_yellow']}
$soft_green           = {hypr_colors['soft_green']}

$dark_wine_98         = {hypr_colors['dark_wine_98']}
$deep_wine_95         = {hypr_colors['deep_wine_95']}
$soft_wine_95         = {hypr_colors['soft_wine_95']}
$light_wine_98        = {hypr_colors['light_wine_98']}
$wine_red_95          = {hypr_colors['wine_red_95']}
$cream_white_96       = {hypr_colors['cream_white_96']}
$pure_white_12        = {hypr_colors['pure_white_12']}
$vivid_red_65         = {hypr_colors['vivid_red_65']}

$font_primary         = {font_primary}
$radius_window        = {radius_window}
$radius_card          = {radius_card}
$radius_button        = {radius_button}
"""
    with open(hypr_palette, "w", encoding="utf-8") as f:
        f.write(hypr_content)
    print("  ✔ Generated hypr/palette.conf")

    hypr_lua = os.path.join(hypr_base, "hypr", "palette.lua")
    hypr_lua_content = f"""-- palette.lua — Color, typography and geometry tokens for Hyprland (Lua engine).
-- NOTE: Generated from tokens.json. Do not edit directly.

return {{
    dark_wine            = "{hypr_colors['dark_wine']}",
    deep_wine            = "{hypr_colors['deep_wine']}",
    soft_wine            = "{hypr_colors['soft_wine']}",
    light_wine           = "{hypr_colors['light_wine']}",
    dark_ruby            = "{hypr_colors['dark_ruby']}",
    wine_red             = "{hypr_colors['wine_red']}",
    vivid_red            = "{hypr_colors['vivid_red']}",
    light_red            = "{hypr_colors['light_red']}",
    vivid_pink           = "{hypr_colors['vivid_pink']}",
    soft_pink            = "{hypr_colors['soft_pink']}",
    muted_pink           = "{hypr_colors['muted_pink']}",
    cream_white          = "{hypr_colors['cream_white']}",
    pure_white           = "{hypr_colors['pure_white']}",
    sky_blue             = "{hypr_colors['sky_blue']}",
    light_cyan           = "{hypr_colors['light_cyan']}",
    warm_yellow          = "{hypr_colors['warm_yellow']}",
    soft_green           = "{hypr_colors['soft_green']}",
    dark_wine_98         = "{hypr_colors['dark_wine_98']}",
    deep_wine_95         = "{hypr_colors['deep_wine_95']}",
    soft_wine_95         = "{hypr_colors['soft_wine_95']}",
    light_wine_98        = "{hypr_colors['light_wine_98']}",
    wine_red_95          = "{hypr_colors['wine_red_95']}",
    cream_white_96       = "{hypr_colors['cream_white_96']}",
    pure_white_12        = "{hypr_colors['pure_white_12']}",
    vivid_red_65         = "{hypr_colors['vivid_red_65']}",
    font_primary         = "{font_primary}",
    radius_window        = {radius_window},
    radius_card          = {radius_card},
    radius_button        = {radius_button},
    width_control_center = {width_control_center},
    width_shelf          = {width_shelf},
    width_rofi           = {width_rofi},
}}
"""
    with open(hypr_lua, "w", encoding="utf-8") as f:
        f.write(hypr_lua_content)
    print("  ✔ Generated hypr/palette.lua")

    # 3. Rofi colors-rofi.rasi
    rofi_palette = os.path.join(hypr_base, "rofi", "colors-rofi.rasi")
    rofi_content = f"""/* colors-rofi.rasi — Color, typography and geometry tokens for Rofi. */
/* NOTE: Generated from tokens.json. Do not edit directly. */

* {{
    dark-wine:          {palette['dark_wine']};
    dark-wine-98:       {palette['dark_wine_98']};
    deep-wine:          {palette['deep_wine']};
    deep-wine-95:       {palette['deep_wine_95']};
    deep-wine-50:       {palette['deep_wine_50']};
    soft-wine:          {palette['soft_wine']};
    soft-wine-95:       {palette['soft_wine_95']};
    light-wine:         {palette['light_wine']};
    light-wine-98:      {palette['light_wine_98']};
    dark-ruby:          {palette['dark_ruby']};
    wine-red:           {palette['wine_red']};
    vivid-red:          {palette['vivid_red']};
    vivid-red-65:       {palette['vivid_red_65']};
    light-red:          {palette['light_red']};
    vivid-pink:         {palette['vivid_pink']};
    soft-pink:          {palette['soft_pink']};
    muted-pink:         {palette['muted_pink']};
    cream-white:        {palette['cream_white']};
    cream-white-96:     {palette['cream_white_96']};
    pure-white:         {palette['pure_white']};
    pure-white-12:      {palette['pure_white_12']};
    sky-blue:           {palette['sky_blue']};
    light-cyan:         {palette['light_cyan']};
    warm-yellow:        {palette['warm_yellow']};
    soft-green:         {palette['soft_green']};

    font-primary:       "{font_primary} {base_size}";
    width-rofi:         {width_rofi}px;
    radius-window:      {radius_window}px;
    radius-card:        {radius_card}px;
    radius-button:      {radius_button}px;
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

PALETTE = {json.dumps(palette, indent=4, ensure_ascii=False)}
TYPOGRAPHY = {json.dumps(typo, indent=4, ensure_ascii=False)}
GEOMETRY = {json.dumps(geo, indent=4, ensure_ascii=False)}


def hex_to_rgba(hex_code: str, alpha: float = 1.0):
    h = hex_code.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, float(alpha))


# Typography & Geometry constants
FONT_PRIMARY         = TYPOGRAPHY.get("font_primary", "JetBrains Mono Nerd Font")
FONT_STACK           = TYPOGRAPHY.get("font_stack", {json.dumps(font_stack)})
FONT_BASE_SIZE       = int(TYPOGRAPHY.get("base_size", 13))
FONT_HEADING_SIZE    = int(TYPOGRAPHY.get("heading_size", 14))
FONT_CAPTION_SIZE    = int(TYPOGRAPHY.get("caption_size", 11))
FONT_MICRO_SIZE      = int(TYPOGRAPHY.get("micro_size", 10))
FONT_HERO_SIZE       = int(TYPOGRAPHY.get("hero_size", 54))

RADIUS_WINDOW        = int(GEOMETRY.get("radius_window", 16))
RADIUS_CARD          = int(GEOMETRY.get("radius_card", 10))
RADIUS_BUTTON        = int(GEOMETRY.get("radius_button", 8))
RADIUS_BADGE         = int(GEOMETRY.get("radius_badge", 4))
RADIUS_SCROLLBAR     = int(GEOMETRY.get("radius_scrollbar", 4))
WIDTH_CONTROL_CENTER = int(GEOMETRY.get("width_control_center", 315))
WIDTH_SHELF          = int(GEOMETRY.get("width_shelf", 464))
WIDTH_ROFI           = int(GEOMETRY.get("width_rofi", 640))

# Color constants (aligned 1:1 with tokens.json)
DARK_WINE       = PALETTE.get("dark_wine", "#201011")
DEEP_WINE       = PALETTE.get("deep_wine", "#2A1A1E")
SOFT_WINE       = PALETTE.get("soft_wine", "#301F20")
LIGHT_WINE      = PALETTE.get("light_wine", "#3A222A")
DARK_RUBY       = PALETTE.get("dark_ruby", "#4D0A1C")
DARK_RUBY_HOVER = PALETTE.get("dark_ruby_hover", "#610E24")
WINE_RED        = PALETTE.get("wine_red", "#851733")
WINE_RED_HOVER  = PALETTE.get("wine_red_hover", "#9C2241")
VIVID_RED       = PALETTE.get("vivid_red", "#DC1A36")
LIGHT_RED       = PALETTE.get("light_red", "#F02D4C")
VIVID_PINK      = PALETTE.get("vivid_pink", "#FF5C8A")
SOFT_PINK       = PALETTE.get("soft_pink", "#E8C2D0")
MUTED_PINK      = PALETTE.get("muted_pink", "#A68595")
CREAM_WHITE     = PALETTE.get("cream_white", "#FFF0F5")
CREAM_WHITE_96  = PALETTE.get("cream_white_96", "rgba(255, 240, 245, 0.96)")
PURE_WHITE      = PALETTE.get("pure_white", "#FFFFFF")
SKY_BLUE        = PALETTE.get("sky_blue", "#50A6FF")
LIGHT_CYAN      = PALETTE.get("light_cyan", "#87F0FF")
WARM_YELLOW     = PALETTE.get("warm_yellow", "#FFB86C")
SOFT_GREEN      = PALETTE.get("soft_green", "#8FBC8F")
SUNSET_PINK     = "{sunset_pink}"
SUNSET_PASTEL   = "{sunset_pastel}"

# Gradient Design Tokens
GRADIENTS = {{
    "sunset": "{grad_sunset}"
}}
SUNSET_STOPS = [
    {sunset_stops_repr}
]

# Pre-computed Cairo RGBA tuples
DARK_WINE_RGBA        = hex_to_rgba(DARK_WINE, 0.98)
DEEP_WINE_RGBA        = hex_to_rgba(DEEP_WINE, 0.95)
LIGHT_WINE_RGBA       = hex_to_rgba(LIGHT_WINE, 0.98)
SOFT_WINE_RGBA        = hex_to_rgba(SOFT_WINE, 0.95)
WINE_RED_RGBA         = hex_to_rgba(WINE_RED, 1.0)
DARK_RUBY_RGBA        = hex_to_rgba(DARK_RUBY, 1.0)
VIVID_RED_RGBA        = hex_to_rgba(VIVID_RED, 1.0)
LIGHT_RED_RGBA        = hex_to_rgba(LIGHT_RED, 1.0)
VIVID_RED_48_RGBA     = hex_to_rgba(VIVID_RED, 0.48)
VIVID_RED_20_RGBA     = hex_to_rgba(VIVID_RED, 0.20)
VIVID_PINK_RGBA       = hex_to_rgba(VIVID_PINK, 1.0)
PURE_WHITE_12_RGBA    = (1.0, 1.0, 1.0, 0.12)
"""
    with open(py_palette, "w", encoding="utf-8") as f:
        f.write(py_content)
    print("  ✔ Generated hypr/scripts/system/palette.py")

    # 5. btop theme
    btop_theme = os.path.join(hypr_base, "btop", "themes", "obsidian-wine.theme")
    btop_content = f"""# obsidian-wine.theme — Color tokens for btop.
# NOTE: Generated from tokens.json. Do not edit directly.

theme[main_bg]="{dark_wine}"
theme[main_fg]="{cream_white}"
theme[title]="{vivid_red}"
theme[hi_fg]="{light_red}"

theme[selected_bg]="{vivid_red}"
theme[selected_fg]="{pure_white}"

theme[inactive_fg]="{muted_pink}"

theme[graph_text]="{soft_pink}"
theme[meter_bg]="{deep_wine}"
theme[proc_misc]="{light_red}"

theme[cpu_box]="{vivid_red}"
theme[mem_box]="{light_red}"
theme[net_box]="{soft_pink}"
theme[proc_box]="{muted_pink}"
theme[div_line]="{light_wine}"

theme[temp_start]="{soft_pink}"
theme[temp_mid]="{light_red}"
theme[temp_end]="{vivid_red}"

theme[cpu_start]="{muted_pink}"
theme[cpu_mid]="{light_red}"
theme[cpu_end]="{vivid_red}"

theme[free_start]="{muted_pink}"
theme[free_mid]="{soft_pink}"
theme[free_end]="{cream_white}"

theme[cached_start]="{muted_pink}"
theme[cached_mid]="{soft_pink}"
theme[cached_end]="{cream_white}"

theme[available_start]="{muted_pink}"
theme[available_mid]="{soft_pink}"
theme[available_end]="{cream_white}"

theme[used_start]="{muted_pink}"
theme[used_mid]="{soft_pink}"
theme[used_end]="{cream_white}"

theme[download_start]="{muted_pink}"
theme[download_mid]="{light_red}"
theme[download_end]="{vivid_red}"

theme[upload_start]="{muted_pink}"
theme[upload_mid]="{light_red}"
theme[upload_end]="{vivid_red}"
"""
    with open(btop_theme, "w", encoding="utf-8") as f:
        f.write(btop_content)
    print("  ✔ Generated btop/themes/obsidian-wine.theme")

    # 5b. Cava config (Terminal Music Visualizer)
    cava_dir = os.path.join(hypr_base, "cava")
    os.makedirs(cava_dir, exist_ok=True)
    cava_path = os.path.join(cava_dir, "config")
    cava_content = f"""## Configuration file for CAVA — Serena Wine Sunset Theme

[general]
live-config = 1
framerate = 60
autosens = 1
sensitivity = 100
bars = 0
bar_width = 2
bar_spacing = 1
center_align = 1
max_height = 100
lower_cutoff_freq = 50
higher_cutoff_freq = 12000
sleep_timer = 0

[input]
method = pipewire
source = auto

[output]
method = noncurses
channels = mono
orientation = bottom

[color]
background = default
gradient = 1
gradient_color_1 = '{dark_ruby}'
gradient_color_2 = '{wine_red}'
gradient_color_3 = '#A3183D'
gradient_color_4 = '{vivid_red}'
gradient_color_5 = '#E53262'
gradient_color_6 = '{vivid_pink}'
gradient_color_7 = '#FF7299'
gradient_color_8 = '{sky_blue}'

[smoothing]
monstercat = 0
waves = 0
noise_reduction = 65

[eq]
1 = 1.0
2 = 1.1
3 = 1.3
4 = 1.6
5 = 2.0
"""
    with open(cava_path, "w", encoding="utf-8") as f:
        f.write(cava_content)
    user_cava_dir = os.path.expanduser("~/.config/cava")
    os.makedirs(user_cava_dir, exist_ok=True)
    with open(os.path.join(user_cava_dir, "config"), "w", encoding="utf-8") as f:
        f.write(cava_content)
    print("  ✔ Generated cava/config")

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
            "padding": {"top": 1, "right": 2},
        },
        "display": {
            "separator": " • ",
            "color": {
                "keys": vivid_red,
                "title": light_red,
                "separator": soft_pink,
                "output": cream_white,
            },
            "percent": {
                "color": {
                    "green": sky_blue,
                    "yellow": light_red,
                    "red": vivid_red,
                }
            },
            "bar": {
                "color": {
                    "elapsed": vivid_red,
                    "total": light_wine,
                    "border": muted_pink,
                }
            },
        },
        "modules": [
            {"type": "title", "format": "{user-name-colored} @ {host-name-colored}"},
            {"type": "separator", "string": "┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈", "outputColor": muted_pink},
            {"type": "os", "key": " OS"},
            {"type": "host", "key": "󰌢 Host"},
            {"type": "uptime", "key": "󱑂 Uptime"},
            {"type": "shell", "key": " Shell"},
            {"type": "terminal", "key": " Terminal"},
            {"type": "cpu", "key": " CPU", "format": "{1} ({4})"},
            {"type": "gpu", "key": "󰾲 GPU", "format": "{2}"},
            {"type": "memory", "key": "󰍛 Memory", "format": "{1} / {2} ({3})"},
            {"type": "disk", "key": " Disk", "folders": "/", "format": "{1} / {2} ({3})"},
            {"type": "battery", "key": " Battery", "format": "{4} [{5}]"},
            {"type": "separator", "string": "┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈", "outputColor": muted_pink},
            {"type": "colors", "symbol": "circle"},
        ],
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
                module["outputColor"] = muted_pink
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
allow_remote_control password
remote_control_password "" music_control.py
confirm_os_window_close 0
enable_audio_bell no
linux_display_server auto
shell zsh

# === CURSOR ===
cursor {vivid_red}
cursor_text_color {dark_wine}
cursor_shape beam
cursor_trail 1

# === COLORS ===
background {dark_wine}
foreground {cream_white}
selection_background {vivid_red}
selection_foreground {pure_white}

# === ANSI COLORS ===
# Black
color0 {dark_wine}
color8 {light_wine}

# Red
color1 {vivid_red}
color9 {light_red}

# Green
color2 {sky_blue}
color10 {sky_blue}

# Yellow
color3 {light_red}
color11 {light_red}

# Blue
color4 {sky_blue}
color12 {sky_blue}

# Magenta
color5 {soft_pink}
color13 {soft_pink}

# Cyan
color6 {sky_blue}
color14 {muted_pink}

# White
color7 {cream_white}
color15 {pure_white}
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
    --dark-wine: {palette['dark_wine']};
    --dark-wine-98: {palette['dark_wine_98']};
    --deep-wine: {palette['deep_wine']};
    --deep-wine-95: {palette['deep_wine_95']};
    --deep-wine-50: {palette['deep_wine_50']};
    --soft-wine: {palette['soft_wine']};
    --soft-wine-95: {palette['soft_wine_95']};
    --light-wine: {palette['light_wine']};
    --light-wine-98: {palette['light_wine_98']};
    --dark-ruby: {palette['dark_ruby']};
    --wine-red: {palette['wine_red']};
    --vivid-red: {palette['vivid_red']};
    --light-red: {palette['light_red']};
    --vivid-pink: {palette['vivid_pink']};
    --soft-pink: {palette['soft_pink']};
    --muted-pink: {palette['muted_pink']};
    --cream-white: {palette['cream_white']};
    --pure-white: {palette['pure_white']};
    --sky-blue: {palette['sky_blue']};
    --light-cyan: {palette['light_cyan']};
    --warm-yellow: {palette['warm_yellow']};
    --soft-green: {palette['soft_green']};

    --pure-white-12: {palette['pure_white_12']};
    --vivid-red-65: {palette['vivid_red_65']};
    --vivid-red-48: {palette['vivid_red_48']};
    --vivid-red-40: {palette['vivid_red_40']};
    --vivid-red-20: {palette['vivid_red_20']};

    --radius-window: {radius_window}px;
    --radius-card: {radius_card}px;
    --radius-button: {radius_button}px;
    --font-primary: "{font_primary}";
}}
"""
    with open(firefox_palette, "w", encoding="utf-8") as f:
        f.write(firefox_palette_content)
    print("  ✔ Generated firefox/chrome/palette.css")

    for mozilla_base in [
        os.path.expanduser("~/.config/mozilla/firefox"),
        os.path.expanduser("~/.mozilla/firefox"),
    ]:
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
