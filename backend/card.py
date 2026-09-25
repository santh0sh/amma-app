import pathlib
"""Renders the good-morning card: image + Tamil text on the image.

Tamil needs the raqm layout engine; without it letters like பி, து, கு break.
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont, features

from common import ROOT

W, H = 1080, 1350
FONT_B = str(ROOT / "fonts" / "NotoSansTamil-Bold.ttf")
FONT_R = str(ROOT / "fonts" / "NotoSansTamil-Regular.ttf")
FONT_LATIN = next((str(p) for p in (ROOT / "fonts" / "NotoSans-Regular.ttf",
                                      pathlib.Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
                   if p.exists()), FONT_R)
WEEKDAY_TA = ["திங்கட்கிழமை", "செவ்வாய்க்கிழமை", "புதன்கிழமை", "வியாழக்கிழமை",
              "வெள்ளிக்கிழமை", "சனிக்கிழமை", "ஞாயிற்றுக்கிழமை"]


def _font(path, size):
    if not features.check("raqm"):
        raise RuntimeError("Pillow built without raqm - Tamil would render wrongly")
    return ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)


def _cover(img, w, h):
    s = max(w / img.width, h / img.height)
    img = img.resize((int(img.width * s + 0.5), int(img.height * s + 0.5)), Image.LANCZOS)
    x = (img.width - w) // 2
    y = max(0, (img.height - h) // 3)  # keep faces/heads, which sit high in most art
    return img.crop((x, y, x + w, y + h))


def _fit(draw, text, path, size, max_w):
    while size > 30:
        f = _font(path, size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 4
    return _font(path, size)


def _shadow_text(base, xy, text, font, fill, anchor="ms"):
    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text(xy, text, font=font, fill=(0, 0, 0, 200), anchor=anchor)
    shadow = shadow.filter(ImageFilter.GaussianBlur(6))
    base.alpha_composite(shadow)
    ImageDraw.Draw(base).text(xy, text, font=font, fill=fill, anchor=anchor)


def render(photo, greeting="காலை வணக்கம்", day_line="", special_line="", credit="", size=(W, H)):
    w, h = size
    img = _cover(photo, w, h).convert("RGBA")
    # soft dark band at the bottom so white text is always readable
    band = Image.new("L", (1, h), 0)
    for y in range(h):
        t = max(0.0, (y - h * 0.52) / (h * 0.48))
        band.putpixel((0, y), int(215 * min(1.0, t) ** 1.2))
    dark = Image.new("RGBA", (w, h), (20, 10, 0, 255))
    dark.putalpha(band.resize((w, h)))
    img.alpha_composite(dark)
    d = ImageDraw.Draw(img)
    y = h - 90
    if credit:
        f = ImageFont.truetype(FONT_LATIN, 20)
        d.text((w - 24, h - 20), credit[:110], font=f, fill=(255, 255, 255, 150), anchor="rs")
    if special_line:
        f = _fit(d, special_line, FONT_B, 58, w - 100)
        _shadow_text(img, (w // 2, y), special_line, f, (255, 214, 102, 255))
        y -= 86
    if day_line:
        f = _fit(d, day_line, FONT_R, 50, w - 100)
        _shadow_text(img, (w // 2, y), day_line, f, (255, 255, 255, 255))
        y -= 96
    f = _fit(d, greeting, FONT_B, 124, w - 80)
    _shadow_text(img, (w // 2, y), greeting, f, (255, 255, 255, 255))
    return img.convert("RGB")


def credit_line(item):
    if item.get("custom"):
        return ""
    artist = (item.get("artist") or "").strip() or "Unknown"
    half = len(artist) // 2
    if len(artist) % 2 == 0 and artist[:half] == artist[half:]:
        artist = artist[:half]
    if artist.lower().startswith("unknown"):
        artist = "Unknown artist"
    lic = item.get("license", "")
    if lic.lower().startswith(("public domain", "pd", "cc0")):
        return f"Image: {artist} / Wikimedia Commons (public domain)"
    return f"Image: {artist} / Wikimedia Commons, {lic}"
