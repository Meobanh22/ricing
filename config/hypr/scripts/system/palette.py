#!/usr/bin/env python3
# palette.py — Python design tokens.
# NOTE: Generated automatically. Do not edit directly.

PALETTE = {
    "dark_wine": "#201011",
    "deep_wine": "#2A1A1E",
    "soft_wine": "#301F20",
    "light_wine": "#3A222A",
    "plum_slate": "#241C20",
    "dark_ruby": "#4D0A1C",
    "dark_ruby_hover": "#610E24",
    "wine_red": "#851733",
    "wine_red_hover": "#9C2241",
    "vivid_red": "#DC1A36",
    "light_red": "#F02D4C",
    "vivid_pink": "#FF5C8A",
    "soft_pink": "#E8C2D0",
    "muted_pink": "#A68595",
    "cream_white": "#FFF0F5",
    "pure_white": "#FFFFFF",
    "sky_blue": "#50A6FF",
    "light_cyan": "#87F0FF",
    "warm_yellow": "#FFB86C",
    "soft_green": "#8FBC8F",
    "dark_wine_98": "rgba(32, 16, 17, 0.98)",
    "deep_wine_95": "rgba(42, 26, 30, 0.95)",
    "deep_wine_50": "rgba(42, 26, 30, 0.50)",
    "soft_wine_95": "rgba(48, 31, 32, 0.95)",
    "light_wine_98": "rgba(58, 34, 42, 0.98)",
    "plum_slate_98": "rgba(36, 28, 32, 0.98)",
    "plum_slate_95": "rgba(36, 28, 32, 0.95)",
    "vivid_red_65": "rgba(220, 26, 54, 0.65)",
    "vivid_red_48": "rgba(220, 26, 54, 0.48)",
    "vivid_red_40": "rgba(220, 26, 54, 0.40)",
    "vivid_red_20": "rgba(220, 26, 54, 0.20)",
    "cream_white_96": "rgba(255, 240, 245, 0.96)",
    "pure_white_12": "rgba(255, 255, 255, 0.12)",
    "pure_white_65": "rgba(255, 255, 255, 0.65)",
    "pure_white_90": "rgba(255, 255, 255, 0.90)",
    "sky_blue_95": "rgba(80, 166, 255, 0.95)",
    "light_cyan_55": "rgba(135, 240, 255, 0.55)"
}
TYPOGRAPHY = {
    "font_primary": "JetBrains Mono Nerd Font",
    "font_stack": "\"JetBrains Mono Nerd Font\", \"FiraCode Nerd Font\", \"Segoe UI\", sans-serif",
    "base_size": 13,
    "heading_size": 14,
    "caption_size": 11,
    "micro_size": 10,
    "hero_size": 54
}
GEOMETRY = {
    "radius_window": 16,
    "radius_card": 10,
    "radius_button": 8,
    "radius_badge": 4,
    "radius_scrollbar": 4,
    "width_control_center": 315,
    "width_shelf": 464,
    "width_rofi": 640
}


def hex_to_rgba(hex_code: str, alpha: float = 1.0):
    h = hex_code.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, float(alpha))


# Typography & Geometry constants
FONT_PRIMARY         = TYPOGRAPHY.get("font_primary", "JetBrains Mono Nerd Font")
FONT_STACK           = TYPOGRAPHY.get("font_stack", "\"JetBrains Mono Nerd Font\", \"FiraCode Nerd Font\", \"Segoe UI\", sans-serif")
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
PLUM_SLATE      = PALETTE.get("plum_slate", "#241C20")
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
SUNSET_PINK     = "#FF7299"
SUNSET_PASTEL   = "#EAA2C6"

# Gradient Design Tokens
GRADIENTS = {
    "sunset": "linear-gradient(to bottom, #A3183D 0%, #E53262 25%, #FF7299 50%, #EAA2C6 75%, #BE7AA8 100%)"
}
SUNSET_STOPS = [
    (0.00, "#A3183D"),
    (0.25, "#E53262"),
    (0.50, "#FF7299"),
    (0.75, "#EAA2C6"),
    (1.00, "#BE7AA8")
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
