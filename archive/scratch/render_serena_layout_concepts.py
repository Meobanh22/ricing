#!/usr/bin/env python3
import math
import cairo
import gi
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo

WIDTH = 1200
HEIGHT = 700

surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
cr = cairo.Context(surface)

# Canvas Background: Dark Obsidian vignette (#140A0C)
cr.set_source_rgb(0x14/255.0, 0x0A/255.0, 0x0C/255.0)
cr.paint()

layout = PangoCairo.create_layout(cr)

def render_text(cr, layout, x, y, markup, wrap_width=None):
    if wrap_width:
        layout.set_width(wrap_width * Pango.SCALE)
        layout.set_wrap(Pango.WrapMode.WORD)
    else:
        layout.set_width(-1)
    layout.set_markup(markup, -1)
    cr.move_to(x, y)
    PangoCairo.show_layout(cr, layout)

# Header Title of the Specimen
header_markup = (
    "<span font='16' color='#FF2A55'>✿ </span>"
    "<span font='JetBrains Mono 14' weight='bold' color='#FFF0F5'>Bản Phác Thảo 3 Ý Tưởng Layout Dành Riêng Cho Serena</span>\n"
    "<span font='JetBrains Mono 10' color='#A68595'>Kích thước thực tế (315px) · Màu sắc Obsidian-Wine (#201011) · Ruby (#FF2A55) · Ribbon Blue (#50A6FF)</span>"
)
render_text(cr, layout, 40, 26, header_markup)

# Helper function to draw common mini-UI elements inside a panel
def draw_panel_inner_content(cr, layout, px, py, is_deck_split=False):
    # Header: ✿ Control Center
    h_markup = (
        "<span font='14' color='#FF2A55'>✿ </span>"
        "<span font='JetBrains Mono 12' weight='bold' color='#FFF0F5'>Control Center</span>\n"
        "<span font='JetBrains Mono 8.5' color='#A68595'>Quick Settings &amp; Alerts</span>"
    )
    render_text(cr, layout, px + 16, py + 16, h_markup)
    
    # 4 Quick Action Tiles (2x2 Grid)
    t_y = py + 56
    tiles = [
        ("", "Input", "Vietnamese", px + 16, t_y),
        ("", "Wi-Fi", "Connected", px + 148, t_y),
        ("", "Bluetooth", "On", px + 16, t_y + 52),
        ("", "Power", "Powersave", px + 148, t_y + 52)
    ]
    for icon, name, sub, tx, ty in tiles:
        # Tile background
        cr.new_sub_path()
        cr.arc(tx + 120 - 8, ty + 8, 8, -1.57, 0)
        cr.arc(tx + 120 - 8, ty + 46 - 8, 8, 0, 1.57)
        cr.arc(tx + 8, ty + 46 - 8, 8, 1.57, 3.14)
        cr.arc(tx + 8, ty + 8, 8, 3.14, 4.71)
        cr.close_path()
        cr.set_source_rgba(0x2A/255.0, 0x1A/255.0, 0x1E/255.0, 0.95)
        cr.fill()
        
        t_markup = (
            f"<span font='FontAwesome 9.5' color='#FF2A55'>{icon} </span>"
            f"<span font='JetBrains Mono 9.5' weight='bold' color='#FFF0F5'>{name}</span>\n"
            f"<span font='JetBrains Mono 8' color='#E8C2D0'>{sub}</span>"
        )
        render_text(cr, layout, tx + 10, ty + 8, t_markup)

    # Offset for body
    body_y = py + 172 if not is_deck_split else py + 196

    # Volume Slider
    render_text(cr, layout, px + 16, body_y, "<span font='FontAwesome 9' color='#FF2A55'></span> <span font='JetBrains Mono 9' color='#FFF0F5'>Volume</span>")
    render_text(cr, layout, px + 225, body_y, "<span font='JetBrains Mono 8.5' color='#E8C2D0'>45%</span>")
    cr.rectangle(px + 16, body_y + 18, 252, 4)
    cr.set_source_rgba(0x30/255.0, 0x1F/255.0, 0x20/255.0, 0.95)
    cr.fill()
    cr.rectangle(px + 16, body_y + 18, 114, 4)
    cr.set_source_rgb(0xFF/255.0, 0x2A/255.0, 0x55/255.0)
    cr.fill()
    cr.arc(px + 130, body_y + 20, 5, 0, 6.28)
    cr.set_source_rgb(1, 1, 1)
    cr.fill_preserve()
    cr.set_source_rgb(0xFF/255.0, 0x2A/255.0, 0x55/255.0)
    cr.set_line_width(1.5)
    cr.stroke()

    # Brightness Slider
    b_y = body_y + 34
    render_text(cr, layout, px + 16, b_y, "<span font='FontAwesome 9' color='#FF2A55'></span> <span font='JetBrains Mono 9' color='#FFF0F5'>Brightness</span>")
    render_text(cr, layout, px + 225, b_y, "<span font='JetBrains Mono 8.5' color='#E8C2D0'>60%</span>")
    cr.rectangle(px + 16, b_y + 18, 252, 4)
    cr.set_source_rgba(0x30/255.0, 0x1F/255.0, 0x20/255.0, 0.95)
    cr.fill()
    cr.rectangle(px + 16, b_y + 18, 151, 4)
    cr.set_source_rgb(0xFF/255.0, 0x2A/255.0, 0x55/255.0)
    cr.fill()
    cr.arc(px + 167, b_y + 20, 5, 0, 6.28)
    cr.set_source_rgb(1, 1, 1)
    cr.fill_preserve()
    cr.set_source_rgb(0xFF/255.0, 0x2A/255.0, 0x55/255.0)
    cr.set_line_width(1.5)
    cr.stroke()

    # Notifications Header & Item
    notif_y = b_y + 38
    render_text(cr, layout, px + 16, notif_y, "<span font='JetBrains Mono 10' weight='bold' color='#FFF0F5'>Notifications</span>")
    render_text(cr, layout, px + 215, notif_y + 1, "<span font='JetBrains Mono 8.5' color='#E8C2D0'>Clear all</span>")

    # 1 sample notification row
    notif_item_y = notif_y + 22
    cr.rectangle(px + 16, notif_item_y, 252, 38)
    cr.set_source_rgba(0x2A/255.0, 0x1A/255.0, 0x1E/255.0, 0.6)
    cr.fill()
    render_text(cr, layout, px + 24, notif_item_y + 6, 
                "<span font='JetBrains Mono 8.5' weight='bold' color='#50A6FF'>Discord</span> <span font='JetBrains Mono 7.5' color='#A68595'>· Vừa xong</span>\n"
                "<span font='JetBrains Mono 8' color='#E8C2D0'>Serena: Layout mới xinh xắn quá!</span>")

    # Bottom Power Menu row
    pwr_y = notif_item_y + 48
    render_text(cr, layout, px + 16, pwr_y, "<span font='FontAwesome 9' color='#FF2A55'></span>  <span font='JetBrains Mono 9.5' weight='bold' color='#FFF0F5'>Power Menu</span>")
    render_text(cr, layout, px + 258, pwr_y, "<span font='JetBrains Mono 9.5' color='#A68595'>&gt;</span>")


# ==============================================================================
# CONCEPT 1: "Kalos Showcase Pass" (Ribbon Chamfer + Blue Ribbon Accent)
# ==============================================================================
c1_x = 50
c1_y = 85
c1_w = 285
c1_h = 445

cut_size = 34
cr.new_sub_path()
cr.arc(c1_x + c1_w - cut_size, c1_y + cut_size, 0, 0, 0)
cr.line_to(c1_x + c1_w, c1_y + cut_size)
cr.arc(c1_x + c1_w - 12, c1_y + c1_h - 12, 12, 0, 1.57)
cr.arc(c1_x + 12, c1_y + c1_h - 12, 12, 1.57, 3.14)
cr.arc(c1_x + 20, c1_y + 20, 20, 3.14, 4.71)
cr.line_to(c1_x + c1_w - cut_size, c1_y)
cr.line_to(c1_x + c1_w, c1_y + cut_size)
cr.close_path()

cr.set_source_rgba(0x20/255.0, 0x10/255.0, 0x11/255.0, 0.98)
cr.fill_preserve()
cr.set_source_rgba(1, 1, 1, 0.12)
cr.set_line_width(1.0)
cr.stroke()

# Draw Ribbon Blue decorative line on the cut-out corner
cr.new_sub_path()
cr.move_to(c1_x + c1_w - cut_size - 4, c1_y)
cr.line_to(c1_x + c1_w, c1_y + cut_size + 4)
cr.set_source_rgb(0x50/255.0, 0xA6/255.0, 0xFF/255.0)
cr.set_line_width(2.5)
cr.stroke()

# Ribbon bow icon in blue
render_text(cr, layout, c1_x + c1_w - 28, c1_y + 7, "<span font='9' color='#50A6FF'>🎀</span>")

draw_panel_inner_content(cr, layout, c1_x, c1_y)

# Concept 1 Caption
render_text(cr, layout, c1_x, c1_y + c1_h + 14, 
            "<span font='JetBrains Mono 11' weight='bold' color='#50A6FF'>1. Kalos Showcase Pass 🎀</span>\n"
            "<span font='JetBrains Mono 8.5' color='#E8C2D0'>• Góc trên vát khuyết 45° đính nơ xanh Serena.\n"
            "• Dáng thẻ bài sân khấu Tripokalon.\n"
            "• Gọn gàng, hiện đại và có điểm nhấn đắt giá.</span>",
            wrap_width=c1_w)


# ==============================================================================
# CONCEPT 2: "Petal Asymmetry" (Dáng Cánh Hoa So Le 🌸)
# ==============================================================================
c2_x = 455
c2_y = 85
c2_w = 285
c2_h = 445

r_big = 28
r_small = 6

cr.new_sub_path()
cr.arc(c2_x + c2_w - r_small, c2_y + r_small, r_small, -1.57, 0)
cr.arc(c2_x + c2_w - r_big, c2_y + c2_h - r_big, r_big, 0, 1.57)
cr.arc(c2_x + r_small, c2_y + c2_h - r_small, r_small, 1.57, 3.14)
cr.arc(c2_x + r_big, c2_y + r_big, r_big, 3.14, 4.71)
cr.close_path()

cr.set_source_rgba(0x20/255.0, 0x10/255.0, 0x11/255.0, 0.98)
cr.fill_preserve()
cr.set_source_rgba(1, 1, 1, 0.12)
cr.set_line_width(1.0)
cr.stroke()

# Glowing Ruby accent along the deep curved top-left edge
cr.new_sub_path()
cr.arc(c2_x + r_big, c2_y + r_big, r_big, 3.14, 4.71)
cr.set_source_rgb(0xFF/255.0, 0x2A/255.0, 0x55/255.0)
cr.set_line_width(2.0)
cr.stroke()

draw_panel_inner_content(cr, layout, c2_x, c2_y)

# Concept 2 Caption
render_text(cr, layout, c2_x, c2_y + c2_h + 14, 
            "<span font='JetBrains Mono 11' weight='bold' color='#FF597B'>2. Petal Asymmetry 🌸</span>\n"
            "<span font='JetBrains Mono 8.5' color='#E8C2D0'>• Bo góc so le (28px &amp; 6px) mềm như cánh hoa.\n"
            "• Viền đỏ Ruby mềm mại ở đường cong chính.\n"
            "• Rất bay bổng, nữ tính, đậm chất anime thơ mộng.</span>",
            wrap_width=c2_w)


# ==============================================================================
# CONCEPT 3: "Dual Floating Deck" (2 Tầng Đảo Nổi Tách Rời 🚀)
# ==============================================================================
c3_x = 860
c3_y = 85
c3_w = 285

# Deck 1: Top Quick Settings (Height: 168px)
d1_h = 168
cr.new_sub_path()
cr.arc(c3_x + c3_w - 14, c3_y + 14, 14, -1.57, 0)
cr.arc(c3_x + c3_w - 14, c3_y + d1_h - 14, 14, 0, 1.57)
cr.arc(c3_x + 14, c3_y + d1_h - 14, 14, 1.57, 3.14)
cr.arc(c3_x + 14, c3_y + 14, 14, 3.14, 4.71)
cr.close_path()
cr.set_source_rgba(0x20/255.0, 0x10/255.0, 0x11/255.0, 0.98)
cr.fill_preserve()
cr.set_source_rgba(1, 1, 1, 0.12)
cr.set_line_width(1.0)
cr.stroke()

# Deck 2: Bottom Sliders & Notifications (Height: 265px, Gap: 12px)
d2_y = c3_y + d1_h + 12
d2_h = 265
cr.new_sub_path()
cr.arc(c3_x + c3_w - 14, d2_y + 14, 14, -1.57, 0)
cr.arc(c3_x + c3_w - 14, d2_y + d2_h - 14, 14, 0, 1.57)
cr.arc(c3_x + 14, d2_y + d2_h - 14, 14, 1.57, 3.14)
cr.arc(c3_x + 14, d2_y + 14, 14, 3.14, 4.71)
cr.close_path()
cr.set_source_rgba(0x20/255.0, 0x10/255.0, 0x11/255.0, 0.98)
cr.fill_preserve()
cr.set_source_rgba(1, 1, 1, 0.12)
cr.set_line_width(1.0)
cr.stroke()

draw_panel_inner_content(cr, layout, c3_x, c3_y, is_deck_split=True)

# Concept 3 Caption
render_text(cr, layout, c3_x, c1_y + c1_h + 14, 
            "<span font='JetBrains Mono 11' weight='bold' color='#FF2A55'>3. Dual Floating Deck 🚀</span>\n"
            "<span font='JetBrains Mono 8.5' color='#E8C2D0'>• Tách đôi thành 2 hòn đảo nổi độc lập.\n"
            "• Khe hở 12px lộ hình nền desktop tạo chiều sâu.\n"
            "• Cảm giác công nghệ tương lai như PokéNav HUD.</span>",
            wrap_width=c3_w)

out_path = "/home/meobanh/.gemini/antigravity/brain/b100facb-dc25-46a1-bf2b-50841a962fae/serena_layout_concepts.png"
surface.write_to_png(out_path)
print(f"Generated {out_path}")

