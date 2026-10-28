# UI/UX Design Guidelines — Agent Reference
> Ricing system inspired by Serena. Applies to: Hyprland · Waybar · Control Center · Shelf · Clipboard · Dashboard · Rofi · GTK3 apps.

---

## 0. Agent Rules (Read First)

These rules apply to every component, every file, every prompt.

**When creating any new component:**
- Pick colors ONLY from Section 2 tokens. No custom colors.
- Pick spacing from the approved scale in Section 4 or an explicit component-specific value defined there.
- Match the component type to its pattern in Section 6 and follow it exactly.
- When unsure → stop and ask. Do not guess or improvise.

**When writing CSS comments or file headers:**
- Header format: `/* filename.css — one-line description. */`
- Section divider: `/* === SECTION NAME === */`
- Inline note: `/* NOTE: reason */`
- No decorative ASCII borders. No marketing copy in comments.

**When naming things:**
- File titles and labels use plain descriptive names. Example: `waybar/style.css`, not `Serena Waybar Minimalist Stylesheet`.
- UI labels, titles, and status text must be in English (IME status indicators may use 🇻🇳 VIE / 🇬🇧 ENG).
- Use "Serena" only when referring to the character or the project by name — not as an adjective for every component.

**Fallback rule:**
> If a situation is not covered by this file → ask before doing anything.

**Scope rule:**
> If a change affects more than one component, or requires modifying shared tokens / layout / spacing — stop and confirm scope with the user before proceeding.

---

## 1. Design Identity

**Style:** Anime minimalist — warm, subdued, no neon, no glow.
**Character reference:** Serena (the project's namesake and visual anchor).
**Scope:** Hyprland · Waybar · Control Center · Shelf · Clipboard · Dashboard · Rofi · GTK3 apps

---

## 2. Color Tokens

> Do not use any color outside this table. If a role is missing, ask before adding a new token.

| Token | Value | Role |
| :--- | :--- | :--- |
| `--bg-window` | `rgba(32,16,18,0.98)` · `#201011` | Window and panel background |
| `--bg-card` | `rgba(42,26,31,0.95)` · `#2A1A1E` | Card, tile, section surface |
| `--bg-card-hover` | `rgba(58,34,42,0.98)` · `#3A222A` | Card on hover |
| `--bg-subtle` | `rgba(48,31,32,0.95)` · `#301F20` | Small chips, icon header cells |
| `--bg-ghost` | `transparent` | Notification rows, power buttons |
| `--bg-ghost-hover` | `rgba(42,26,31,0.50)` | Ghost elements on hover |
| `--border-window` | `rgba(255,255,255,0.12)` | Outer window border (only one) |
| `--border-card` | `rgba(255,255,255,0.12)` | Card border (default) |
| `--border-card-hover` | `rgba(255,42,85,0.65)` | Card border on hover |
| `--accent` | `#FF2A55` | Icons, badges, toggle ON, slider, pin |
| `--accent-hover` | `#FF597B` | Accent on hover |
| `--text-primary` | `#FFF0F5` | Headings, main labels |
| `--text-secondary` | `#E8C2D0` | Status, percentage, subtitle |
| `--text-muted` | `#A68595` | Timestamp, caption, placeholder |
| `--text-inverse` | `#FFFFFF` | Text on accent backgrounds, active buttons, slider thumbs |
| `--status-warning` | `#FFB86C` | Warning alerts, low battery (<30%), temperature warning |
| `--status-critical` | `#FF2A55` | Critical alerts, password fail, battery critical (<15%) |
| `--status-success` | `#8FBC8F` | Subdued sage, online indicator, battery full |
| `--ribbon-blue` | `#50A6FF` | Blue ribbon accent | 

**Icon rule:** All interactive status icons use `--accent`.

**Badge & Brand rule:** System badges and generic chips use `--accent` with `--text-inverse`. In notification lists, official third-party application icons/badges (e.g., Discord, Firefox, Spotify) may keep their recognizable brand hue or use subtle `--bg-subtle` chips with `--accent` icons to maintain instant visual recognition without disrupting the subdued anime aesthetic.

**Sync rule:** All components share these tokens. Do not redeclare colors locally if a token already covers the role. If two windows look different despite using the same token, check opacity, overlays, and local stylesheets before adding anything new.

---

## 3. Typography

| Property | Value |
| :--- | :--- |
| Font stack | `"JetBrains Mono Nerd Font"`, `"FiraCode Nerd Font"`, `"Segoe UI"`, sans-serif |
| Base size | `13px` |
| Heading / label | `14px`, `font-weight: 600` |
| Caption / muted text | `11–12px`, `font-weight: 400` |
| Micro / compact label | `9.5–10.5px`, `font-weight: 500` (dense cards, compact panel tags in ≤ 315px windows) |
| Display / Hero (Clock) | `24px / 36px / 54px`, `font-weight: 700` (Lockscreen time, Dashboard clock) |
| Letter spacing | `0.02em` for headings; `normal` for body (use Pango markup `letter_spacing` where supported) |
| Language | English only for all UI text |

---

## 4. Spacing & Shape

> Use only values from the approved scale below or explicit component-specific exceptions in this file. Do not round to nearest "feels right" number.

### 4.1 Approved Spacing Scale

| Token | Value | Typical use |
| :--- | :---: | :--- |
| `space-2` | 2px | Micro gaps, border offsets |
| `space-4` | 4px | Icon–text gap, inner card gap |
| `space-6` | 6px | Inline icon gaps, header button spacing |
| `space-8` | 8px | Row gap, button gap, scrollbar margin |
| `space-10` | 10px | Flowbox spacing, card horizontal padding |
| `space-12` | 12px | Section gap, search horizontal padding |
| `space-14` | 14px | Compact panel inner padding |
| `space-16` | 16px | Wide panel inner padding |
| `space-20` | 20px | Modal padding |

These are approved spacing values, not a mathematical multiple-of-four grid. Explicit offsets such as the 44px Waybar anchor margin in Section 4.4 are component-specific exceptions.

### 4.2 Spatial Hierarchy

| Level | Element | Radius | Padding | Border |
| :--- | :--- | :---: | :---: | :--- |
| Window / Panel | Outer frame | 16px | 14px (compact) · 16px (wide) | `1px solid --border-window` |
| Card / Tile | Tile, clip chip | 10px | 8px × 10px (or 6px × 8px compact) | `1px solid --border-card` → hover: `--border-card-hover` (or flat borderless variant) |
| Button / Input | Action, search | 8px | 4px × 10px (btn) · 6px × 12px (input) | none or `1px solid rgba(255,255,255,0.08)` |
| Tag / Badge | Chip, label | 4px | 2px × 6px | none |
| Scrollbar slider | — | 4px | — | none; width 6px → hover 8px; min-height 36px |
| Horizontal slider | GtkScale volume/brightness | 3px track · 50% thumb | — | track: none; thumb: 2px solid `--accent` |

### 4.3 Panel Widths

| Component | Width |
| :--- | :---: |
| Control Center | 315px |
| Music Visualizer | 315px |
| Dashboard | 682–720px |
| Shelf / Clipboard | 464px |
| Popout Preview Card | 260px |
| Image Lightbox | 400–720px (responsive) |

### 4.4 Layer-Shell Architecture

**Group 1 — Static (anchored to Waybar):**
- Music Visualizer: `TOP | LEFT`, margin top 44px left 14px, width 315px. Shortcut `Super+M`.
- Dashboard: `TOP` centered, margin top 44px, width 682–720px. Shortcut `Super+S`.
- Control Center: `TOP | RIGHT`, margin top 44px right 14px, width 315px. Shortcut `Super+N`.

**Group 2 — Dynamic (freely draggable):**
- Shelf / Clipboard: draggable via header, saves position per session, double-click to reset center. Width 464px.

---

## 5. Animation

| Trigger | Value |
| :--- | :--- |
| Popup open / close | `200ms ease-out` — slide + fade |
| Hover | `150ms ease` — color change only |
| Notification appear | `180ms ease-in` — fade from top |
| Performance target | All popups open in < 50ms |

---

## 6. Component Patterns

Copy exactly. Do not improvise values not listed here.

### Window / Panel
```
bg:             --bg-window
border:         1px solid --border-window
border-radius:  16px
padding:        14px (compact) · 16px (wide)
box-shadow:     none
```

### Card (tile, quick-action, clip chip)
```
bg:             --bg-card
border:         1px solid --border-card (or none for compact multi-column flat tiles)
border-radius:  10px
padding:        8px 10px (standard) · 6px 8px (compact tiles in ≤ 315px windows)
hover bg:       --bg-card-hover
hover border:   1px solid --border-card-hover (or none for flat tiles — subtle bg shift only)
hover effect:   bg + border change only — no shadow, no glow
structure:      icon (--accent) + heading (--text-primary) + status (--text-secondary)
```

### Ghost Item (notification row, list row, power button)
```
bg:             transparent
border:         none
border-radius:  8px
padding:        8px 10px
hover bg:       --bg-ghost-hover
hover effect:   bg change only
```

### Launcher List Item (Rofi / Menu keyboard focus)
```
bg:             transparent
border:         none
border-radius:  8px
padding:        8px 10px
keyboard focus: bg: --bg-card-hover, border: 1px solid --border-card-hover, text: --text-primary
hover bg:       --bg-ghost-hover
hover effect:   clear focus visibility for keyboard navigation without neon glow
```

### Search Entry
```
bg:             rgba(42,26,31,0.95)
border:         1px solid rgba(255,255,255,0.08)
border-radius:  8px
padding:        6px 12px
focus border:   1px solid --accent
caret:          --accent
font-size:      11.5px
```

### Button (action, tab)
```
bg:             rgba(42,26,31,0.95)  |  active: --accent
text:           --text-secondary     |  active: --text-inverse (#FFFFFF)
border-radius:  8px
padding:        4px 10px
hover:          --bg-card-hover      |  active hover: --accent-hover
transition:     150ms ease
```

### Badge / Tag
```
bg:             --accent
text:           --text-inverse (#FFFFFF)
border-radius:  4px
padding:        2px 6px
font-size:      11px
```

### Horizontal Scale Slider (Volume / Brightness)
```
trough:         bg: rgba(48,31,32,0.95) · height: 5px · border-radius: 3px
highlight:      bg: --accent (#FF2A55) · border-radius: 3px
thumb/slider:   bg: --text-inverse (#FFFFFF) · border: 2px solid --accent · border-radius: 50% · size: 12px
thumb hover:    bg: #FFF0F5 · border-color: --accent-hover
```

### Scrollbar
```
trough:         transparent
slider:         rgba(255,42,85,0.48), width 6px, min-height 36px, border-radius 4px
slider hover:   --accent (#FF2A55), width 8px
margin-right:   8px
```
