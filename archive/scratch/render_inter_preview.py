#!/usr/bin/env python3
import os
import cairo
import gi
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo

WIDTH = 980
HEIGHT = 820

surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
cr = cairo.Context(surface)

# Background: --bg-window (#201011)
cr.set_source_rgb(0x20/255.0, 0x10/255.0, 0x11/255.0)
cr.paint()

def draw_rounded_rect(cr, x, y, w, h, r, bg_color, border_color=None):
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -1.57079632679, 0)
    cr.arc(x + w - r, y + h - r, r, 0, 1.57079632679)
    cr.arc(x + r, y + h - r, r, 1.57079632679, 3.14159265359)
    cr.arc(x + r, y + r, r, 3.14159265359, 4.71238898038)
    cr.close_path()
    cr.set_source_rgba(*bg_color)
    cr.fill_preserve()
    if border_color:
        cr.set_source_rgba(*border_color)
        cr.set_line_width(1.0)
        cr.stroke()
    else:
        cr.new_path()

# Main Container Card
draw_rounded_rect(cr, 24, 24, WIDTH - 48, HEIGHT - 48, 16, 
                  (0x2A/255.0, 0x1A/255.0, 0x1E/255.0, 0.98), 
                  (1.0, 1.0, 1.0, 0.12))

layout = PangoCairo.create_layout(cr)

def render_pango_text(cr, layout, x, y, markup, wrap_width=None):
    if wrap_width:
        layout.set_width(wrap_width * Pango.SCALE)
        layout.set_wrap(Pango.WrapMode.WORD)
    else:
        layout.set_width(-1)
    layout.set_markup(markup, -1)
    cr.move_to(x, y)
    PangoCairo.show_layout(cr, layout)

# Header
header_markup = (
    "<span font='14' weight='bold' color='#FF2A55'>✿ </span>"
    "<span font='Inter 14' weight='bold' color='#FFF0F5'>Đánh giá trực quan: Inter (Cỡ 11) trong giao diện Control Center</span>\n"
    "<span font='Inter 10' color='#A68595'>So sánh phong cách UI Sans-serif hiện đại (Inter) vs Monospace (Fira Code / JetBrains Mono)</span>"
)
render_pango_text(cr, layout, 48, 46, header_markup)

# Sub Card 1: Inter 11 (Modern Sans-serif UI)
draw_rounded_rect(cr, 48, 105, 420, 580, 14,
                  (0x20/255.0, 0x10/255.0, 0x11/255.0, 0.95),
                  (0x50/255.0, 0xA6/255.0, 0xFF/255.0, 0.35))

# Sub Card 2: Monospace 11 (Techy Ricing UI)
draw_rounded_rect(cr, 512, 105, 420, 580, 14,
                  (0x20/255.0, 0x10/255.0, 0x11/255.0, 0.95),
                  (0xFF/255.0, 0x2A/255.0, 0x55/255.0, 0.35))

# --- INTER PANEL CONTENT ---
inter_title = "<span font='Inter 12' weight='bold' color='#50A6FF'>✦ Phong cách A: Inter (Cỡ 11)</span>\n<span font='Inter 9.5' color='#A68595'>Modern App UI · Thoát dáng, mượt mà</span>"
render_pango_text(cr, layout, 68, 120, inter_title)

# Mock UI: Header
draw_rounded_rect(cr, 68, 168, 380, 55, 10, (0x2A/255.0, 0x1A/255.0, 0x1E/255.0, 0.95), (1.0, 1.0, 1.0, 0.08))
mock_h_inter = (
    "<span font='15' color='#FF2A55'>✿  </span>"
    "<span font='Inter 13' weight='bold' color='#FFF0F5'>Control Center</span>\n"
    "<span font='Inter 10' color='#A68595'>     Quick Settings &amp; Alerts</span>"
)
render_pango_text(cr, layout, 82, 178, mock_h_inter)

# Mock UI: 2 Tiles
draw_rounded_rect(cr, 68, 235, 182, 75, 10, (0x2A/255.0, 0x1A/255.0, 0x1E/255.0, 0.95), (1.0, 1.0, 1.0, 0.08))
tile_inter_1 = (
    "<span font='FontAwesome 13' color='#FF2A55'></span>\n"
    "<span font='Inter 11' weight='bold' color='#FFF0F5'>Input Method</span>\n"
    "<span font='Inter 10' color='#E8C2D0'>Vietnamese (VIE)</span>"
)
render_pango_text(cr, layout, 82, 245, tile_inter_1)

draw_rounded_rect(cr, 266, 235, 182, 75, 10, (0x2A/255.0, 0x1A/255.0, 0x1E/255.0, 0.95), (1.0, 1.0, 1.0, 0.08))
tile_inter_2 = (
    "<span font='FontAwesome 13' color='#FF2A55'></span>\n"
    "<span font='Inter 11' weight='bold' color='#FFF0F5'>Wi-Fi Network</span>\n"
    "<span font='Inter 10' color='#E8C2D0'>Connected · Tang2</span>"
)
render_pango_text(cr, layout, 280, 245, tile_inter_2)

# Mock UI: Sliders
draw_rounded_rect(cr, 68, 322, 380, 65, 10, (0x2A/255.0, 0x1A/255.0, 0x1E/255.0, 0.95), (1.0, 1.0, 1.0, 0.08))
sliders_inter = (
    "<span font='FontAwesome 12' color='#FF2A55'> </span>"
    "<span font='Inter 11' weight='bold' color='#FFF0F5'>Volume</span>"
    "<span font='Inter 10' color='#E8C2D0'>                                                45%</span>\n"
    "<span font='FontAwesome 12' color='#FF2A55'> </span>"
    "<span font='Inter 11' weight='bold' color='#FFF0F5'>Brightness</span>"
    "<span font='Inter 10' color='#E8C2D0'>                                            60%</span>"
)
render_pango_text(cr, layout, 82, 335, sliders_inter)

# Mock UI: Notification Section
mock_notif_inter = (
    "<span font='Inter 12' weight='bold' color='#FFF0F5'>Notifications</span>"
    "<span font='Inter 10' color='#E8C2D0'>                                    Clear all</span>\n\n"
    "<span font='Inter 11' weight='bold' color='#FFF0F5'>Discord</span> <span font='Inter 9.5' color='#A68595'>· Vừa xong</span>\n"
    "<span font='Inter 10' color='#E8C2D0'>Serena: Chào bạn, hôm nay giao diện nhìn rất mượt!</span>\n\n"
    "<span font='Inter 11' weight='bold' color='#FFF0F5'>Spotify</span> <span font='Inter 9.5' color='#A68595'>· 2m ago</span>\n"
    "<span font='Inter 10' color='#E8C2D0'>Đang phát: Dorihe - Bài hát chủ đề</span>"
)
render_pango_text(cr, layout, 72, 405, mock_notif_inter)

# Inter Pros Note
inter_pros = (
    "<span font='Inter 10' weight='bold' color='#50A6FF'>Ưu điểm của Inter 11:</span>\n"
    "<span font='Inter 9.5' color='#FFF0F5'>• Chữ tự nhiên, gọn chiều ngang (tiết kiệm không gian 315px).\n"
    "• Tiếng Việt dấu thanh cực kỳ chuẩn xác, không bị dính nét.\n"
    "• Mang phong cách hiện đại như iOS, macOS, Figma, Linear.</span>"
)
render_pango_text(cr, layout, 72, 595, inter_pros, wrap_width=372)


# --- MONOSPACE PANEL CONTENT ---
mono_title = "<span font='Fira Code 12' weight='bold' color='#FF597B'>✦ Phong cách B: Monospace (Cỡ 11)</span>\n<span font='Fira Code 9.5' color='#A68595'>Techy / Geek Ricing · Đầm nét, cá tính</span>"
render_pango_text(cr, layout, 532, 120, mono_title)

# Mock UI: Header
draw_rounded_rect(cr, 532, 168, 380, 55, 10, (0x2A/255.0, 0x1A/255.0, 0x1E/255.0, 0.95), (1.0, 1.0, 1.0, 0.08))
mock_h_mono = (
    "<span font='15' color='#FF2A55'>✿  </span>"
    "<span font='Fira Code 13' weight='bold' color='#FFF0F5'>Control Center</span>\n"
    "<span font='Fira Code 10' color='#A68595'>     Quick Settings &amp; Alerts</span>"
)
render_pango_text(cr, layout, 546, 178, mock_h_mono)

# Mock UI: 2 Tiles
draw_rounded_rect(cr, 532, 235, 182, 75, 10, (0x2A/255.0, 0x1A/255.0, 0x1E/255.0, 0.95), (1.0, 1.0, 1.0, 0.08))
tile_mono_1 = (
    "<span font='FontAwesome 13' color='#FF2A55'></span>\n"
    "<span font='Fira Code 11' weight='bold' color='#FFF0F5'>Input Method</span>\n"
    "<span font='Fira Code 9.5' color='#E8C2D0'>Vietnamese (VIE)</span>"
)
render_pango_text(cr, layout, 546, 245, tile_mono_1)

draw_rounded_rect(cr, 730, 235, 182, 75, 10, (0x2A/255.0, 0x1A/255.0, 0x1E/255.0, 0.95), (1.0, 1.0, 1.0, 0.08))
tile_mono_2 = (
    "<span font='FontAwesome 13' color='#FF2A55'></span>\n"
    "<span font='Fira Code 11' weight='bold' color='#FFF0F5'>Wi-Fi Network</span>\n"
    "<span font='Fira Code 9.5' color='#E8C2D0'>Connected · Tang2</span>"
)
render_pango_text(cr, layout, 744, 245, tile_mono_2)

# Mock UI: Sliders
draw_rounded_rect(cr, 532, 322, 380, 65, 10, (0x2A/255.0, 0x1A/255.0, 0x1E/255.0, 0.95), (1.0, 1.0, 1.0, 0.08))
sliders_mono = (
    "<span font='FontAwesome 12' color='#FF2A55'> </span>"
    "<span font='Fira Code 11' weight='bold' color='#FFF0F5'>Volume</span>"
    "<span font='Fira Code 10' color='#E8C2D0'>                                        45%</span>\n"
    "<span font='FontAwesome 12' color='#FF2A55'> </span>"
    "<span font='Fira Code 11' weight='bold' color='#FFF0F5'>Brightness</span>"
    "<span font='Fira Code 10' color='#E8C2D0'>                                    60%</span>"
)
render_pango_text(cr, layout, 546, 335, sliders_mono)

# Mock UI: Notification Section
mock_notif_mono = (
    "<span font='Fira Code 12' weight='bold' color='#FFF0F5'>Notifications</span>"
    "<span font='Fira Code 10' color='#E8C2D0'>                            Clear all</span>\n\n"
    "<span font='Fira Code 11' weight='bold' color='#FFF0F5'>Discord</span> <span font='Fira Code 9.5' color='#A68595'>· Vừa xong</span>\n"
    "<span font='Fira Code 10' color='#E8C2D0'>Serena: Chào bạn, hôm nay giao diện nhìn rất mượt!</span>\n\n"
    "<span font='Fira Code 11' weight='bold' color='#FFF0F5'>Spotify</span> <span font='Fira Code 9.5' color='#A68595'>· 2m ago</span>\n"
    "<span font='Fira Code 10' color='#E8C2D0'>Đang phát: Dorihe - Bài hát chủ đề</span>"
)
render_pango_text(cr, layout, 536, 405, mock_notif_mono)

# Monospace Pros Note
mono_pros = (
    "<span font='Fira Code 10' weight='bold' color='#FF2A55'>Ưu điểm của Monospace 11:</span>\n"
    "<span font='Fira Code 9.5' color='#FFF0F5'>• Đậm đà, góc cạnh cá tính, chất Linux ricer / hacker rõ rệt.\n"
    "• Khoảng cách cố định (mỗi ký tự rộng bằng nhau), số đếm đều tăm tắp.\n"
    "• Đồng bộ triệt để nếu bạn thích một phông chữ duy nhất cho toàn hệ thống.</span>"
)
render_pango_text(cr, layout, 536, 595, mono_pros, wrap_width=372)

# Footer Conclusion
draw_rounded_rect(cr, 48, 705, WIDTH - 96, 75, 10,
                  (0x20/255.0, 0x10/255.0, 0x11/255.0, 0.95),
                  (1.0, 1.0, 1.0, 0.08))

summary_text = (
    "<span font='Inter 10' weight='bold' color='#FFF0F5'>💡 Kết luận: </span>"
    "<span font='Inter 9.5' color='#E8C2D0'>Nếu bạn muốn giao diện Control Center &amp; Waybar mang cảm giác <b>App chuyên nghiệp, thanh lịch, chữ gọn gàng</b> thì <b>Inter 11</b> là số 1.\n"
    "Còn nếu bạn yêu thích chất <b>Ricing anime / terminal hacker đồng bộ</b> thì <b>Monospace 11</b> vẫn mang bản sắc riêng không thể thay thế!</span>"
)
render_pango_text(cr, layout, 68, 715, summary_text, wrap_width=WIDTH - 136)

out_path = "/home/meobanh/.gemini/antigravity/brain/b100facb-dc25-46a1-bf2b-50841a962fae/inter_vs_jetbrains_preview.png"
surface.write_to_png(out_path)
print(f"Generated {out_path}")

