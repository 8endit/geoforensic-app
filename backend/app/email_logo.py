"""Generate the Bodenbericht email header logo (PNG) at import time.

Produces a 600x80 PNG (navy background, green 'B' square, white 'Bodenbericht'
wordmark in green accent on "bericht"). The bytes are cached in memory so that
every outgoing email just attaches the already-built image.

Why this module?
    - Keeps email_service.py focused on SMTP logic.
    - The header is brand-critical; generating it in Python guarantees it
      matches the rest of the site (same hex colors) without shipping a
      pre-rendered PNG that could drift out of sync.
    - PNG is inlined via Content-ID ('cid:bodenbericht-logo'), which renders
      in every mail client even when external images are blocked.
"""
import io
import os

from PIL import Image, ImageDraw, ImageFont


# Brand palette (identical to landing/build_brand_assets.py)
BRAND_GREEN = (22, 163, 74)       # #16a34a
BRAND_GREEN_LIGHT = (34, 197, 94) # #22c55e
NAVY_900 = (12, 29, 58)           # #0c1d3a
NAVY_800 = (18, 43, 82)           # #122b52
NAVY_700 = (26, 58, 107)          # #1a3a6b
WHITE = (255, 255, 255)


def _find_bold_font() -> str:
    candidates = [
        # Linux (Docker container)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        # macOS
        "/System/Library/Fonts/Helvetica.ttc",
        # Windows (dev)
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    raise RuntimeError("No bold font found")


def build_header_png(width: int = 600, height: int = 80) -> bytes:
    """Render the email header banner and return PNG bytes."""
    img = Image.new("RGB", (width, height), NAVY_900)
    draw = ImageDraw.Draw(img)

    # Subtle gradient top -> bottom
    for y in range(height):
        t = y / height
        r = int(NAVY_900[0] + (NAVY_700[0] - NAVY_900[0]) * t)
        g = int(NAVY_900[1] + (NAVY_700[1] - NAVY_900[1]) * t)
        b = int(NAVY_900[2] + (NAVY_700[2] - NAVY_900[2]) * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    bold_font = _find_bold_font()

    # Green square logo on left
    pad_left = 28
    logo_size = 40
    logo_y = (height - logo_size) // 2
    draw.rounded_rectangle(
        (pad_left, logo_y, pad_left + logo_size, logo_y + logo_size),
        radius=8,
        fill=BRAND_GREEN,
    )
    # White "B" centered in the square
    letter_font = ImageFont.truetype(bold_font, 26)
    bbox = draw.textbbox((0, 0), "B", font=letter_font)
    lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        (pad_left + (logo_size - lw) / 2 - bbox[0], logo_y + (logo_size - lh) / 2 - bbox[1]),
        "B",
        font=letter_font,
        fill=WHITE,
    )

    # Wordmark "Bodenbericht" next to the logo
    word_font = ImageFont.truetype(bold_font, 22)
    wx = pad_left + logo_size + 14
    wy_center = height / 2
    wbbox = draw.textbbox((0, 0), "Bodenbericht", font=word_font)
    wth = wbbox[3] - wbbox[1]
    draw.text(
        (wx, wy_center - wth / 2 - wbbox[1]),
        "Boden",
        font=word_font,
        fill=WHITE,
    )
    boden_w = draw.textbbox((0, 0), "Boden", font=word_font)[2]
    draw.text(
        (wx + boden_w, wy_center - wth / 2 - wbbox[1]),
        "bericht",
        font=word_font,
        fill=BRAND_GREEN_LIGHT,
    )

    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


# Module-level cache: built once per process, reused for every email.
_cached_header_png: bytes | None = None


def get_header_png() -> bytes:
    global _cached_header_png
    if _cached_header_png is None:
        _cached_header_png = build_header_png()
    return _cached_header_png
