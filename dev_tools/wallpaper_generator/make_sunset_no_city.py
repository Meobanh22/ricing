"""Create a flower-field wallpaper without the distant city using Pillow."""

import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).resolve().parent / "serena_fennekin_original.jpg"
MEADOW_REPAIR = Path(__file__).resolve().parent / "serena_meadow_repair.png"
LANDSCAPE_REPAIR = Path(__file__).resolve().parent / "serena_landscape_repair.png"
MEADOW_STYLE_REPAIR = Path(__file__).resolve().parent / "serena_meadow_style_repair.png"
OUTPUT = ROOT / "assets/wallpapers/serena_fennekin_wallpaper_hd.jpg"


def feathered_polygon(size, points, radius):
    mask = Image.new("L", size)
    ImageDraw.Draw(mask).polygon(points, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(radius))


def erase_glow(image, x, y, radius, offset_x, offset_y=0):
    box = (x - radius, y - radius, x + radius, y + radius)
    sample_box = tuple(
        value + (offset_x if index % 2 == 0 else offset_y)
        for index, value in enumerate(box)
    )
    patch = image.crop(sample_box)
    mask = Image.new("L", patch.size)
    ImageDraw.Draw(mask).ellipse((2, 2, patch.width - 2, patch.height - 2), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(max(2, radius // 5)))
    image.paste(patch, box, mask)


def clamp(value):
    return max(0.0, min(1.0, value))


def ridge_heights(width):
    points = [
        (0, 405), (100, 391), (200, 434), (320, 415),
        (600, 420), (900, 430), (1040, 420), (1140, 389),
        (1220, 416), (1320, 390), (1376, 402),
    ]
    heights = []
    segment = 0
    for x in range(width):
        while segment + 2 < len(points) and x > points[segment + 1][0]:
            segment += 1
        x0, y0 = points[segment]
        x1, y1 = points[segment + 1]
        fraction = (x - x0) / (x1 - x0)
        heights.append(y0 + (y1 - y0) * fraction)
    return heights


def add_wildflowers(image):
    rng = random.Random(26)
    overlay = Image.new("RGBA", image.size)
    draw = ImageDraw.Draw(overlay)
    patches = [
        (100, 630, 95, 85, 360),
        (215, 730, 90, 55, 260),
        (1110, 555, 120, 65, 430),
        (1220, 600, 115, 65, 330),
        (1260, 675, 115, 85, 550),
        (1080, 735, 110, 55, 350),
        (760, 742, 145, 35, 260),
    ]
    petals = [
        (230, 166, 190),
        (207, 124, 160),
        (247, 222, 191),
        (239, 193, 182),
        (242, 215, 154),
    ]

    def open_meadow(x, y):
        return (
            (y >= 525 and x < (300 if y < 590 else 230 if y < 650 else 175))
            or (x >= 1030 and y >= 490)
            or (880 <= x < 1030 and y >= 675)
            or (625 <= x < 880 and y >= 718)
        )

    for center_x, center_y, spread_x, spread_y, count in patches:
        for _ in range(count):
            x = rng.gauss(center_x, spread_x)
            y = rng.gauss(center_y, spread_y)
            if not (8 <= x < image.width - 8 and 490 <= y < image.height - 5):
                continue
            if not open_meadow(x, y):
                continue

            depth = clamp((y - 490) / 278)
            size = 0.7 + 3.0 * depth * rng.uniform(0.7, 1.25)
            red, green, blue = rng.choice(petals)
            opacity = int(120 + 95 * depth)
            angle = rng.uniform(0, math.tau)

            if size < 2.0:
                draw.ellipse(
                    (x - size, y - size * 0.6, x + size, y + size * 0.6),
                    fill=(red, green, blue, opacity),
                )
                continue

            if rng.random() < 0.35:
                draw.line(
                    (x, y + size * 0.5, x + rng.uniform(-2, 2), y + size * 3),
                    fill=(66, 91, 61, int(opacity * 0.7)),
                    width=1,
                )
            for petal in range(5):
                direction = angle + math.tau * petal / 5
                petal_x = x + math.cos(direction) * size * 0.85
                petal_y = y + math.sin(direction) * size * 0.62
                draw.ellipse(
                    (
                        petal_x - size * 0.65,
                        petal_y - size * 0.48,
                        petal_x + size * 0.65,
                        petal_y + size * 0.48,
                    ),
                    fill=(red, green, blue, opacity),
                )
            draw.ellipse(
                (x - size * 0.32, y - size * 0.32,
                 x + size * 0.32, y + size * 0.32),
                fill=(245, 218, 149, opacity),
            )

    overlay = overlay.filter(ImageFilter.GaussianBlur(0.45))
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def harmonize_meadow(image):
    """Match the repaired right meadow to the warm field on the left."""
    mask = Image.new("L", image.size)
    draw = ImageDraw.Draw(mask)
    draw.polygon([(1045, 438), (1376, 428), (1376, 768), (1045, 768)], fill=255)
    draw.polygon([(895, 458), (1045, 432), (1045, 552), (895, 565)], fill=255)
    draw.polygon([(895, 697), (1045, 677), (1045, 768), (895, 768)], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(25))

    pixels = image.load()
    mask_pixels = mask.load()
    for y in range(420, image.height):
        depth = clamp((y - 500) / 200)
        offsets = (35 - 22 * depth, 22 - 9 * depth, 28 - 14 * depth)
        for x in range(870, image.width):
            opacity = mask_pixels[x, y] / 255
            if not opacity:
                continue
            red, green, blue = pixels[x, y]
            highlight = clamp((235 - max(red, green, blue)) / 55)
            opacity *= 0.6 + 0.4 * highlight
            pixels[x, y] = tuple(
                min(255, round(channel + offset * opacity))
                for channel, offset in zip((red, green, blue), offsets)
            )
    return image


def remove_upper_flowers(image):
    """Keep flowers in the foreground and clear the distant upper slope."""
    median = image.filter(ImageFilter.MedianFilter(13))
    region = feathered_polygon(
        image.size,
        [
            (875, 480), (1030, 438), (1376, 430),
            (1376, 565), (1030, 565), (875, 565),
        ],
        9,
    )
    mask = Image.new("L", image.size)
    pixels = image.load()
    median_pixels = median.load()
    region_pixels = region.load()
    mask_pixels = mask.load()
    for y in range(415, min(580, image.height)):
        for x in range(850, image.width):
            if not region_pixels[x, y]:
                continue
            red, green, blue = pixels[x, y]
            base_red, base_green, base_blue = median_pixels[x, y]
            brightness_difference = (
                red + green + blue - base_red - base_green - base_blue
            )
            blossom = (
                red - base_red > 20
                and brightness_difference > 36
                and (blue - base_blue > 12 or green - base_green > 18)
            )
            if blossom:
                mask_pixels[x, y] = region_pixels[x, y]
    mask = mask.filter(ImageFilter.MaxFilter(5))
    mask = mask.filter(ImageFilter.GaussianBlur(1.1))
    image.paste(median, (0, 0), mask)
    return image


def remove_far_flowers(image):
    """Inpaint individual distant blossoms without flattening the grass."""
    neighbors = [
        (-1, 0), (1, 0), (0, -1), (0, 1),
        (-1, -1), (1, -1), (-1, 1), (1, 1),
    ]
    passes = [
        (555, 641, 16, 28, 8, 11, 610, 640),
        (550, 626, 12, 22, 6, 9, 600, 630),
    ]
    for start_y, end_y, red_min, bright_min, blue_min, green_min, fade_start, fade_end in passes:
        crop_box = (1004, start_y - 12, image.width, end_y + 12)
        median = image.crop(crop_box).filter(ImageFilter.MedianFilter(17))
        source_pixels = image.load()
        median_pixels = median.load()
        mask = Image.new("L", image.size)
        mask_pixels = mask.load()

        for y in range(start_y, end_y):
            for x in range(1015, image.width):
                red, green, blue = source_pixels[x, y]
                base_red, base_green, base_blue = median_pixels[
                    x - crop_box[0], y - crop_box[1]
                ]
                dr, dg, db = red - base_red, green - base_green, blue - base_blue
                if dr > red_min and dr + dg + db > bright_min and (
                    db > blue_min or dg > green_min
                ):
                    mask_pixels[x, y] = 255

        mask = mask.filter(ImageFilter.MaxFilter(3))
        mask_pixels = mask.load()
        missing = {
            (x, y)
            for y in range(start_y - 1, end_y + 1)
            for x in range(1014, image.width)
            if mask_pixels[x, y]
        }
        filled = image.copy()
        filled_pixels = filled.load()
        while missing:
            updates = []
            for x, y in missing:
                adjacent = [
                    filled_pixels[x + dx, y + dy]
                    for dx, dy in neighbors
                    if (x + dx, y + dy) not in missing
                    and 0 <= x + dx < image.width
                    and 0 <= y + dy < image.height
                ]
                if adjacent:
                    color = tuple(
                        round(sum(pixel[channel] for pixel in adjacent) / len(adjacent))
                        for channel in range(3)
                    )
                    updates.append((x, y, color))
            if not updates:
                break
            for x, y, color in updates:
                filled_pixels[x, y] = color
                missing.remove((x, y))

        soft_mask = mask.filter(ImageFilter.GaussianBlur(0.8))
        soft_pixels = soft_mask.load()
        for y in range(start_y - 2, min(end_y + 2, image.height)):
            fade_y = 1 if y <= fade_start else clamp((fade_end - y) / (fade_end - fade_start))
            for x in range(1013, image.width):
                fade_x = clamp((x - 1015) / 25)
                opacity = soft_pixels[x, y] / 255 * fade_x * fade_y
                if not opacity:
                    continue
                old = source_pixels[x, y]
                new = filled_pixels[x, y]
                source_pixels[x, y] = tuple(
                    round(old[channel] * (1 - opacity) + new[channel] * opacity)
                    for channel in range(3)
                )
    return image


def repair_landscape(image):
    """Replace the visible hillside seams with one continuous painted field."""
    landscape = Image.open(LANDSCAPE_REPAIR).convert("RGB")
    landscape = landscape.resize((image.width - 995, 280), Image.Resampling.LANCZOS)
    color_offsets = [
        (380, (-7, 0, -6)), (400, (4, 0, -4)),
        (420, (14, 6, 7)), (440, (25, 18, 22)),
        (460, (26, 21, 32)), (480, (19, 15, 31)),
        (500, (11, 9, 31)), (550, (16, 21, 42)),
        (600, (10, 15, 40)), (660, (5, 15, 40)),
    ]
    landscape_pixels = landscape.load()
    for y in range(landscape.height):
        target_y = y + 380
        offsets = color_offsets[-1][1]
        for index in range(len(color_offsets) - 1):
            start_y, start = color_offsets[index]
            end_y, end = color_offsets[index + 1]
            if target_y <= end_y:
                amount = clamp((target_y - start_y) / (end_y - start_y))
                offsets = tuple(
                    start[channel] * (1 - amount) + end[channel] * amount
                    for channel in range(3)
                )
                break
        for x in range(landscape.width):
            channels = landscape_pixels[x, y]
            landscape_pixels[x, y] = tuple(
                max(0, min(255, round(channels[channel] + offsets[channel])))
                for channel in range(3)
            )

    layer = image.copy()
    layer.paste(landscape, (995, 380))
    mask = feathered_polygon(
        image.size,
        [(1000, 395), (1376, 395), (1376, 650), (1000, 650)],
        28,
    )
    subjects = Image.new("L", image.size)
    subject_draw = ImageDraw.Draw(subjects)
    subject_draw.polygon(
        [(970, 310), (1050, 310), (1050, 490), (970, 490)], fill=255
    )
    subject_draw.polygon(
        [(976, 535), (1013, 535), (1024, 558),
         (1027, 620), (1015, 665), (975, 680)],
        fill=255,
    )
    subjects = subjects.filter(ImageFilter.GaussianBlur(6))
    mask = ImageChops.multiply(mask, ImageChops.invert(subjects))
    image.paste(layer, (0, 0), mask)
    return image


def match_meadow_style(image):
    """Give the distant grass the broad painted texture of the near field."""
    meadow = Image.open(MEADOW_STYLE_REPAIR).convert("RGB")
    meadow = meadow.resize(
        (image.width - 995, image.height - 380), Image.Resampling.LANCZOS
    )
    color_offsets = [
        (480, (23, 11, 7)), (500, (13, 6, 7)),
        (540, (15, 14, 14)), (580, (7, 7, 12)),
        (620, (-2, 0, 2)), (650, (-3, -1, 0)),
    ]
    meadow_pixels = meadow.load()
    for y in range(meadow.height):
        target_y = y + 380
        offsets = color_offsets[-1][1]
        for index in range(len(color_offsets) - 1):
            start_y, start = color_offsets[index]
            end_y, end = color_offsets[index + 1]
            if target_y <= end_y:
                amount = clamp((target_y - start_y) / (end_y - start_y))
                offsets = tuple(
                    start[channel] * (1 - amount) + end[channel] * amount
                    for channel in range(3)
                )
                break
        for x in range(meadow.width):
            channels = meadow_pixels[x, y]
            meadow_pixels[x, y] = tuple(
                max(0, min(255, round(channels[channel] + offsets[channel])))
                for channel in range(3)
            )

    layer = image.copy()
    layer.paste(meadow, (995, 380))
    mask = feathered_polygon(
        image.size,
        [(1000, 490), (1376, 490), (1376, 620), (1000, 620)],
        23,
    )
    subjects = Image.new("L", image.size)
    subject_draw = ImageDraw.Draw(subjects)
    subject_draw.polygon(
        [(970, 310), (1050, 310), (1050, 490), (970, 490)], fill=255
    )
    subject_draw.polygon(
        [(976, 535), (1013, 535), (1024, 558),
         (1027, 620), (1015, 665), (975, 680)],
        fill=255,
    )
    subjects = subjects.filter(ImageFilter.GaussianBlur(6))
    mask = ImageChops.multiply(mask, ImageChops.invert(subjects))
    image.paste(layer, (0, 0), mask)
    return image


def main():
    original = Image.open(SOURCE).convert("RGB")
    image = original.copy()

    # Copy clear sky and distant hills over the tower.
    sky_hills = original.crop((1170, 260, 1376, 510))
    sky_layer = Image.new("RGB", image.size)
    sky_layer.paste(sky_hills, (1000, 260))
    tower_mask = feathered_polygon(
        image.size,
        [(1078, 288), (1164, 288), (1178, 450), (1068, 470)],
        15,
    )
    image.paste(sky_layer, (0, 0), tower_mask)

    # A clean stretch of the same meadow replaces the skyline and its lights.
    meadow = original.crop((1100, 560, 1376, 725))
    meadow = meadow.resize((501, 185), Image.Resampling.BICUBIC)
    meadow = meadow.filter(ImageFilter.GaussianBlur(1.2))
    meadow_layer = Image.new("RGB", image.size)
    meadow_layer.paste(meadow, (875, 395))
    city_mask = feathered_polygon(
        image.size,
        [
            (895, 515), (910, 470), (970, 449), (1048, 435),
            (1110, 425), (1180, 430), (1280, 445), (1376, 470),
            (1376, 560), (1165, 535), (1045, 548), (920, 555),
        ],
        9,
    )
    image.paste(meadow_layer, (0, 0), city_mask)

    # Remove the large floating glows and luminous leaves with nearby scenery.
    for glow in [
        (1110, 201, 22, 55, 0),
        (940, 256, 17, 85, 0),
        (1248, 251, 36, 65, 0),
        (1118, 253, 20, 100, 0),
        (1160, 273, 20, 100, 0),
        (981, 232, 13, 90, 0),
        (1220, 331, 12, 55, 0),
        (1320, 525, 37, -80, 0),
        (1048, 695, 37, 85, 0),
        (135, 570, 29, 55, 0),
        (811, 704, 22, 65, 0),
        (1196, 552, 20, -70, 0),
        (1129, 596, 21, -55, 0),
        (74, 562, 14, 35, 0),
        (288, 376, 15, -40, 0),
        (997, 482, 20, 35, 0),
        (1225, 491, 18, -60, 0),
        (1225, 460, 13, 60, 0),
        (1030, 446, 13, 50, 0),
        (1176, 638, 10, -50, 0),
        (1320, 617, 10, -50, 0),
        (197, 545, 11, -70, 0),
        (266, 565, 9, -80, 0),
        (604, 569, 10, 450, 0),
        (771, 27, 9, 40, 0),
        (1037, 58, 9, 45, 0),
        (1270, 48, 9, -45, 0),
        (1216, 460, 15, -45, 0),
        (1274, 460, 15, -45, 0),
        (981, 483, 15, 55, 0),
        (1018, 483, 15, -55, 0),
        (604, 538, 13, 0, 40),
        (617, 565, 8, -50, 0),
        (244, 356, 14, 50, 0),
        (234, 257, 9, -35, 0),
        (300, 297, 9, -35, 0),
        (418, 75, 7, 35, 0),
        (852, 60, 8, 35, 0),
        (914, 61, 8, -35, 0),
        (964, 81, 15, 40, 0),
        (995, 232, 8, -35, 0),
        (747, 62, 8, 25, 0),
        (810, 80, 8, 25, 0),
        (1007, 98, 8, 25, 0),
        (739, 124, 7, 25, 0),
        (722, 134, 7, 25, 0),
        (1001, 232, 11, 30, 0),
        (1019, 539, 19, 65, 0),
        (1227, 528, 14, 45, 0),
        (1310, 527, 14, -70, 0),
        (227, 640, 20, -90, 0),
        (286, 613, 11, -32, 0),
    ]:
        erase_glow(image, *glow)

    # Remove tiny star points from the open sky without softening the subjects.
    ridge = ridge_heights(image.width)
    median = image.filter(ImageFilter.MedianFilter(7))
    pixels = image.load()
    median_pixels = median.load()
    for y in range(0, 420):
        for x in range(image.width):
            if y >= ridge[x] - 12:
                continue
            if 320 < x < 620 and 58 < y < 450:
                continue
            if 590 < x < 1045 and 55 < y < 480:
                continue
            pixels[x, y] = median_pixels[x, y]

    # Warm the sky while preserving the source image's cloud and meadow tones.
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue = pixels[x, y]
            cool = clamp((blue - red + 20) / 40)
            cool *= clamp((blue - green + 5) / 30)

            horizon = clamp(y / ridge[x])
            sky_mix = clamp((ridge[x] + 10 - y) / 22)
            sky = (
                red + 0.75 * (blue - red) + 25 + 20 * horizon,
                green + 0.25 * (blue - green) + 50 * horizon,
                blue - 0.60 * (blue - red) - 45 * horizon,
            )
            terrain = (
                red + 0.15 * blue,
                green + 0.25 * blue,
                blue * 0.55,
            )
            target = tuple(
                sky_mix * sky[index] + (1 - sky_mix) * terrain[index]
                for index in range(3)
            )
            strength = cool * (sky_mix + 0.75 * (1 - sky_mix))
            pixels[x, y] = (
                max(0, min(255, int(red * (1 - strength) + target[0] * strength))),
                max(0, min(255, int(green * (1 - strength) + target[1] * strength))),
                max(0, min(255, int(blue * (1 - strength) + target[2] * strength))),
            )

    # Keep Serena's blue eyes and bow from the source image.
    source_pixels = original.load()
    for left, top, right, bottom in [
        (410, 215, 463, 322),
        (505, 210, 563, 330),
        (344, 460, 505, 585),
    ]:
        for y in range(top, bottom):
            for x in range(left, right):
                red, green, blue = source_pixels[x, y]
                if blue > red * 1.08 and blue > green * 1.04:
                    pixels[x, y] = (red, green, blue)

    for sparkle in [(325, 200, 8, -45), (465, 62, 7, -35), (877, 297, 8, 160)]:
        erase_glow(image, *sparkle)
    image = add_wildflowers(image)

    # Restore painted shrubs and rolling grass over the old city replacement.
    repair = Image.open(MEADOW_REPAIR).convert("RGB")
    repair = repair.resize(image.size, Image.Resampling.LANCZOS)
    repair_mask = feathered_polygon(
        image.size,
        [
            (895, 455), (945, 435), (1040, 430), (1120, 425),
            (1200, 430), (1376, 438), (1376, 560),
            (1210, 552), (1080, 565), (930, 565),
        ],
        25,
    )
    image.paste(repair, (0, 0), repair_mask)
    image = harmonize_meadow(image)
    image = remove_upper_flowers(image)
    image = remove_far_flowers(image)
    image = repair_landscape(image)
    image = match_meadow_style(image)

    image.save(OUTPUT, format="JPEG", quality=95, subsampling=0, optimize=True)
    print(OUTPUT)


if __name__ == "__main__":
    main()
