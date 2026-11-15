# UI/UX Guidelines

Applies to Hyprland, Waybar, Control Center, Shelf, Clipboard, Dashboard, Rofi, and GTK apps. The project uses a warm, subdued anime minimalist style.

## Colors

`config/theme/tokens.json` is the source of truth. This table is a quick reference for the Serena Wine palette. Components use these roles through generated palettes or the shared Python palette.

| Use | Token | Default color |
| :--- | :--- | :--- |
| Window / panel | `bg_window` | `#201011` |
| Card / tile | `bg_card` | `#2A1A1E` |
| Card hover | `bg_card_hover` | `#3A222A` |
| Small surface | `bg_subtle` | `#301F20` |
| Quiet row / hover | `bg_ghost` / `bg_ghost_hover` | `transparent` / `rgba(42,26,30,0.50)` |
| Outer / card border | `border_window` / `border_card` | `rgba(255,255,255,0.12)` |
| Card hover border | `border_card_hover` | `rgba(220,26,54,0.65)` |
| Accent / hover | `accent` / `accent_hover` | `#DC1A36` / `#F02D4C` |
| Main / supporting text | `text_primary` / `text_secondary` | `#FFF0F5` / `#E8C2D0` |
| Muted / inverse text | `text_muted` / `text_inverse` | `#A68595` / `#FFFFFF` |
| Warning / critical / success | `status_warning` / `status_critical` / `status_success` | `#FFB86C` / `#DC1A36` / `#8FBC8F` |
| Ribbon / Screen | `ribbon_blue` / `screen_cyan` | `#50A6FF` / `#87F0FF` |
| Waybar Ruby / 3D Shadow | `bg_waybar` / `border_waybar_3d` | `#851733` / `#4D0A1C` |
| Tactile Cream Card | `bg_tactile_cream` | `rgba(255,240,245,0.96)` |
| Poképuff Pink | `pokepuff_pink` | `#FF5C8A` |
| Sunset Gradient | `gradient_sunset` | `#A3183D` $\to$ `#E53262` $\to$ `#FF7299` $\to$ `#EAA2C6` $\to$ `#BE7AA8` |

- Interactive status icons use `accent`. System badges use `accent` with `text_inverse`. Official third-party notification icons may retain their brand colors.
- Do not add a local color when an existing role fits. Opacity variants may derive from a role's RGB value; exact alpha values are in `tokens.json`.
- Ask before adding a color role or changing the shared palette. If two components using the same role appear different, check opacity, overlays, and stylesheet imports first.

## Layout and interaction

- Follow the existing component's structure. Adjust width, spacing, radius, and text size to keep content readable and unclipped; the old numeric scales are not requirements.
- Keep static popups aligned with Waybar. Shelf remains draggable. Hover states may change surface, border, icon, or text color using the roles above. Keyboard focus must remain visible.
- Avoid neon, glow, and decorative shadows. Keep motion short and subtle. Do not add tooltips to desktop background widgets.

## Text and files

- UI labels and status text are in English. IME indicators may use 🇻🇳 VIE / 🇬🇧 ENG. Use plain descriptive file names and labels.
- CSS comments use `/* filename.css — one-line description. */` for headers, `/* === SECTION NAME === */` for sections, and `/* NOTE: reason */` for inline notes. Avoid decorative borders and marketing copy.
