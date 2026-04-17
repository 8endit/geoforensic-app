"""
Generate favicon.ico and og-image.png for bodenbericht.de.

Run once (or whenever branding changes):
    python build_brand_assets.py

Requires: Pillow (pip install Pillow)
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

BRAND_GREEN = (22, 163, 74)      # #16a34a
BRAND_GREEN_LIGHT = (34, 197, 94) # #22c55e
NAVY_900 = (12, 29, 58)          # #0c1d3a
NAVY_800 = (18, 43, 82)          # #122b52
NAVY_700 = (26, 58, 107)         # #1a3a6b
WHITE = (255, 255, 255)
GRAY_300 = (203, 213, 225)
GRAY_400 = (148, 163, 184)


def find_bold_font():
    """Find a bold TrueType font on the system (Windows fallback)."""
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf",         # Arial Bold
        r"C:\Windows\Fonts\seguisb.ttf",         # Segoe UI Semibold
        r"C:\Windows\Fonts\segoeuib.ttf",        # Segoe UI Bold
        r"C:\Windows\Fonts\calibrib.ttf",        # Calibri Bold
        r"C:\Windows\Fonts\arial.ttf",           # Arial (last resort)
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    raise RuntimeError("No bold font found on system")


def find_regular_font():
    candidates = [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    raise RuntimeError("No font found")


def draw_rounded_rect(draw, xy, radius, fill):
    """Draw a filled rounded rectangle."""
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def build_favicon_ico(out_path):
    """Build multi-size favicon.ico (16x16, 32x32, 48x48)."""
    bold_font_path = find_bold_font()
    sizes = [16, 32, 48]
    images = []
    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Rounded square background
        radius = max(2, int(size * 0.22))
        draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=BRAND_GREEN)
        # White "B"
        font_size = int(size * 0.70)
        font = ImageFont.truetype(bold_font_path, font_size)
        text = "B"
        # Center the text
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        # font bbox includes ascent offset, so we need to account for bbox[1]
        tx = (size - tw) // 2 - bbox[0]
        ty = (size - th) // 2 - bbox[1]
        draw.text((tx, ty), text, font=font, fill=WHITE)
        images.append(img)
    # Save as multi-size ICO
    images[0].save(
        out_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )
    print(f"  wrote {out_path}  ({os.path.getsize(out_path)} bytes, sizes: {sizes})")


def build_og_image(out_path):
    """Build 1200x630 Open Graph preview image."""
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), NAVY_900)
    draw = ImageDraw.Draw(img)

    # Gradient background (manual, simple vertical + radial feel)
    # We fake a diagonal navy gradient
    for y in range(H):
        t = y / H
        r = int(NAVY_900[0] + (NAVY_700[0] - NAVY_900[0]) * t)
        g = int(NAVY_900[1] + (NAVY_700[1] - NAVY_900[1]) * t)
        b = int(NAVY_900[2] + (NAVY_700[2] - NAVY_900[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Subtle grid pattern (very low opacity)
    grid_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    grid_draw = ImageDraw.Draw(grid_img)
    for x in range(0, W, 40):
        grid_draw.line([(x, 0), (x, H)], fill=(255, 255, 255, 8))
    for y in range(0, H, 40):
        grid_draw.line([(0, y), (W, y)], fill=(255, 255, 255, 8))
    img = Image.alpha_composite(img.convert("RGBA"), grid_img).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Logo pill (top-left): green square with "B" + wordmark
    pad = 64
    logo_y = pad
    logo_size = 64
    draw.rounded_rectangle(
        (pad, logo_y, pad + logo_size, logo_y + logo_size),
        radius=14,
        fill=BRAND_GREEN,
    )
    bold_font = find_bold_font()
    logo_letter_font = ImageFont.truetype(bold_font, 44)
    bbox = draw.textbbox((0, 0), "B", font=logo_letter_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        (pad + (logo_size - tw) / 2 - bbox[0], logo_y + (logo_size - th) / 2 - bbox[1]),
        "B",
        font=logo_letter_font,
        fill=WHITE,
    )

    # Wordmark next to logo
    wordmark_font = ImageFont.truetype(bold_font, 34)
    wx = pad + logo_size + 18
    wy_center = logo_y + logo_size / 2
    wbbox = draw.textbbox((0, 0), "Bodenbericht", font=wordmark_font)
    wth = wbbox[3] - wbbox[1]
    draw.text((wx, wy_center - wth / 2 - wbbox[1]), "Boden", font=wordmark_font, fill=WHITE)
    boden_w = draw.textbbox((0, 0), "Boden", font=wordmark_font)[2]
    draw.text(
        (wx + boden_w, wy_center - wth / 2 - wbbox[1]),
        "bericht",
        font=wordmark_font,
        fill=BRAND_GREEN_LIGHT,
    )

    # Main headline (center-left)
    headline_font = ImageFont.truetype(bold_font, 78)
    headline = "Ihr Standort."
    headline2 = "Ihre Sicherheit."
    y1 = 220
    draw.text((pad, y1), headline, font=headline_font, fill=WHITE)
    h_bbox = draw.textbbox((0, 0), headline, font=headline_font)
    h_height = h_bbox[3] - h_bbox[1]
    draw.text((pad, y1 + h_height + 10), headline2, font=headline_font, fill=BRAND_GREEN_LIGHT)

    # Sub-headline
    regular_font_path = find_regular_font()
    sub_font = ImageFont.truetype(regular_font_path, 30)
    sub_y = y1 + (h_height + 10) * 2 + 40
    draw.text(
        (pad, sub_y),
        "Kostenloser Bodenbericht auf Basis von EU-Satellitendaten.",
        font=sub_font,
        fill=GRAY_300,
    )

    # Trust indicators (bottom)
    chip_font = ImageFont.truetype(regular_font_path, 22)
    chips = ["Copernicus EGMS", "ISRIC SoilGrids", "JRC LUCAS"]
    cx = pad
    cy = H - 110
    for chip in chips:
        cb = draw.textbbox((0, 0), chip, font=chip_font)
        cw = cb[2] - cb[0] + 32
        ch = cb[3] - cb[1] + 18
        draw.rounded_rectangle(
            (cx, cy, cx + cw, cy + ch),
            radius=ch // 2,
            outline=(255, 255, 255, 180),
            width=2,
        )
        draw.text((cx + 16, cy + 9 - cb[1]), chip, font=chip_font, fill=WHITE)
        cx += cw + 14

    # Domain (bottom-right)
    domain_font = ImageFont.truetype(bold_font, 26)
    domain = "bodenbericht.de"
    db = draw.textbbox((0, 0), domain, font=domain_font)
    dw = db[2] - db[0]
    draw.text((W - pad - dw, H - 80), domain, font=domain_font, fill=WHITE)

    img.save(out_path, "PNG", optimize=True)
    print(f"  wrote {out_path}  ({os.path.getsize(out_path)} bytes, 1200x630)")


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    print("Building favicon.ico...")
    build_favicon_ico(os.path.join(here, "favicon.ico"))
    print("Building og-image.png...")
    build_og_image(os.path.join(here, "og-image.png"))
    print("Done.")
