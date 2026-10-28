import os
from PIL import Image, ImageDraw, ImageFont # type: ignore

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE_DIR, "assets", "serena_fennekin_wallpaper_hd.jpg")
OUT_DIR = os.path.join(BASE_DIR, "wallpapers")
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 1920, 1080
CELL_W, CELL_H = 6, 10
COLS = WIDTH // CELL_W   # 320 cols
ROWS = HEIGHT // CELL_H  # 108 rows

font_candidates = [
    "/usr/share/fonts/truetype/noto/NotoMono-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/ubuntu/UbuntuSansMono-Regular.ttf",
    r"C:\Windows\Fonts\consolab.ttf",
]
font = None
for p in font_candidates:
    if os.path.exists(p):
        try:
            font = ImageFont.truetype(p, 10)
            break
        except Exception:
            pass
if font is None:
    font = ImageFont.load_default()
DETAILED_RAMP = " .':;!+*?%S#@&8B"

img = Image.open(SRC).convert("RGB")
resized = img.resize((COLS, ROWS), Image.Resampling.LANCZOS)
pix = resized.load()

def generate_wallpaper(warmth_level=1.0, filename="serena_fennekin_ascii_sakura.png"):
    canvas = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(canvas)

    for r in range(ROWS):
        for c in range(COLS):
            r_val, g_val, b_val = pix[c, r]
            
            # Kiểm tra pixel màu da (R > 180, G > 140, B > 100 và R > G > B)
            is_skin = (r_val > 180 and g_val > 140 and b_val > 100 and r_val > g_val and g_val > b_val)
            
            if is_skin:
                # Preserve the warm peach skin tones in the source image.
                fg_r = min(255, int(r_val * 1.05))
                fg_g = min(255, int(g_val * 0.98 * warmth_level))
                fg_b = min(255, int(b_val * 0.90 * warmth_level))
                
                # Nền ô màu da: ửng hồng ấm áp (warm peach glow)
                bg_col = (int(r_val * 0.36), int(g_val * 0.28), int(b_val * 0.24))
            else:
                bg_col = (int(r_val * 0.32), int(g_val * 0.32), int(b_val * 0.32))
                fg_r = min(255, int(r_val * 1.25))
                fg_g = min(255, int(g_val * 1.25))
                fg_b = min(255, int(b_val * 1.25))
            
            x = c * CELL_W
            y = r * CELL_H
            draw.rectangle([x, y, x + CELL_W - 1, y + CELL_H - 1], fill=bg_col)
            
            lum = 0.299 * r_val + 0.587 * g_val + 0.114 * b_val
            ramp_idx = int((lum / 255.0) * (len(DETAILED_RAMP) - 1))
            ch = DETAILED_RAMP[ramp_idx]
            if ch == " ":
                ch = "."
            
            draw.text((x, y), ch, font=font, fill=(fg_r, fg_g, fg_b))

    out_path = os.path.join(OUT_DIR, filename)
    canvas.save(out_path, "PNG")
    print("Saved:", out_path)

if __name__ == "__main__":
    # Generate the current ASCII wallpaper.
    generate_wallpaper(warmth_level=1.0, filename="serena_fennekin_ascii_sakura.png")

