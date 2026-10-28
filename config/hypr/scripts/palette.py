#!/usr/bin/env python3
# palette.py — Python design tokens.
# NOTE: Generated automatically. Do not edit directly.

PALETTE = {
    "bg_window": "#201011",
    "bg_window_alpha": "rgba(32, 16, 17, 0.98)",
    "bg_window_hypr": "rgba(201011fa)",
    "bg_card": "#2A1A1E",
    "bg_card_alpha": "rgba(42, 26, 30, 0.95)",
    "bg_card_hypr": "rgba(2A1A1Ef2)",
    "bg_card_hover": "#3A222A",
    "bg_card_hover_alpha": "rgba(58, 34, 42, 0.98)",
    "bg_card_hover_hypr": "rgba(3A222Afa)",
    "bg_subtle": "#301F20",
    "bg_subtle_alpha": "rgba(48, 31, 32, 0.95)",
    "bg_subtle_hypr": "rgba(301F20f2)",
    "bg_ghost": "transparent",
    "bg_ghost_hover": "rgba(42, 26, 30, 0.50)",
    "bg_card_soft": "rgba(42, 26, 30, 0.40)",
    "bg_card_subtle": "rgba(42, 26, 30, 0.70)",
    "bg_action": "rgba(48, 31, 32, 0.90)",
    "bg_action_hover": "rgba(58, 34, 42, 0.98)",
    "border_window": "rgba(255, 255, 255, 0.12)",
    "border_window_hypr": "rgba(ffffff1f)",
    "border_card": "rgba(255, 255, 255, 0.12)",
    "border_card_hypr": "rgba(ffffff1f)",
    "border_card_hover": "rgba(255, 42, 85, 0.65)",
    "border_card_hover_hypr": "rgba(FF2A55a6)",
    "accent": "#FF2A55",
    "accent_hypr": "rgb(FF2A55)",
    "accent_hover": "#FF597B",
    "accent_hover_hypr": "rgb(FF597B)",
    "accent_dim": "rgba(255, 42, 85, 0.48)",
    "accent_subtle": "rgba(255, 42, 85, 0.20)",
    "accent_soft": "rgba(255, 42, 85, 0.12)",
    "accent_border": "rgba(255, 42, 85, 0.40)",
    "accent_dash": "rgba(255, 42, 85, 0.45)",
    "text_primary": "#FFF0F5",
    "text_primary_hypr": "rgb(FFF0F5)",
    "text_secondary": "#E8C2D0",
    "text_secondary_hypr": "rgb(E8C2D0)",
    "text_muted": "#A68595",
    "text_muted_hypr": "rgb(A68595)",
    "text_inverse": "#FFFFFF",
    "text_inverse_hypr": "rgb(FFFFFF)",
    "status_warning": "#FFB86C",
    "status_warning_hypr": "rgb(FFB86C)",
    "status_critical": "#FF2A55",
    "status_critical_hypr": "rgb(FF2A55)",
    "status_success": "#8FBC8F",
    "status_success_hypr": "rgb(8FBC8F)",
    "ribbon_blue": "#50A6FF",
    "ribbon_blue_alpha": "rgba(80, 166, 255, 0.95)",
    "ribbon_blue_hypr": "rgb(50A6FF)"
}

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
C_ACCENT        = PALETTE.get("accent", "#FF2A55")
C_ACCENT_HOVER  = PALETTE.get("accent_hover", "#FF597B")
C_TEXT_PRI      = PALETTE.get("text_primary", "#FFF0F5")
C_TEXT_SEC      = PALETTE.get("text_secondary", "#E8C2D0")
C_TEXT_MUT      = PALETTE.get("text_muted", "#A68595")
C_TEXT_INV      = PALETTE.get("text_inverse", "#FFFFFF")
C_STATUS_WARN   = PALETTE.get("status_warning", "#FFB86C")
C_STATUS_CRIT   = PALETTE.get("status_critical", "#FF2A55")
C_STATUS_SUCC   = PALETTE.get("status_success", "#8FBC8F")
C_RIBBON        = PALETTE.get("ribbon_blue", "#50A6FF")

# Pre-computed Cairo RGBA tuples
BG_WINDOW_RGBA     = hex_to_rgba(C_BG_WIN, 0.98)
BG_CARD_RGBA       = hex_to_rgba(C_BG_CARD, 0.95)
BG_CARD_HOVER_RGBA = hex_to_rgba(C_BG_CARD_HOVER, 0.98)
BG_SUBTLE_RGBA     = hex_to_rgba(C_BG_SUBTLE, 0.95)
ACCENT_RGBA        = hex_to_rgba(C_ACCENT, 1.0)
ACCENT_HOVER_RGBA  = hex_to_rgba(C_ACCENT_HOVER, 1.0)
ACCENT_DIM_RGBA    = hex_to_rgba(C_ACCENT, 0.48)
ACCENT_SUBTLE_RGBA = hex_to_rgba(C_ACCENT, 0.20)
BORDER_WINDOW_RGBA = (1.0, 1.0, 1.0, 0.12)
BORDER_CARD_RGBA   = (1.0, 1.0, 1.0, 0.12)
