"""
Process the public-domain 1903 map of ancient Greece into a dark
gold-brown duotone background texture for the Streamlit app theme.

Source: "Map of Ancient Greece (as drawn in 1903)", Wikimedia Commons,
public domain.
https://commons.wikimedia.org/wiki/File:Map_of_Ancient_Greece_(as_drawn_in_1903).jpg

Re-run this if you want to adjust the tone/darkness/blur — it overwrites
app/assets/map_bg.jpg and app/assets/map_bg_b64.txt, which app/theme.py
reads at runtime.
"""

import base64
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

ASSETS = Path(__file__).resolve().parent.parent / "app" / "assets"
SOURCE = ASSETS / "ancient_greece_map_full.jpg"
OUTPUT = ASSETS / "map_bg.jpg"
OUTPUT_B64 = ASSETS / "map_bg_b64.txt"

TARGET_WIDTH = 1800
DARK = (8, 7, 11)
LIGHT = (110, 86, 46)
BLUR_RADIUS = 1.8
BRIGHTNESS = 0.38
CONTRAST = 0.85


def duotone(gray_img, dark, light):
    return Image.merge("RGB", [
        gray_img.point(lambda i, b=band: int(dark[b] + (light[b] - dark[b]) * (i / 255)))
        for band in range(3)
    ])


def main():
    img = Image.open(SOURCE).convert("RGB")
    ratio = TARGET_WIDTH / img.width
    img = img.resize((TARGET_WIDTH, int(img.height * ratio)), Image.LANCZOS)

    gray = ImageOps.grayscale(img)
    gray = ImageEnhance.Contrast(gray).enhance(1.1)

    toned = duotone(gray, DARK, LIGHT)
    toned = toned.filter(ImageFilter.GaussianBlur(radius=BLUR_RADIUS))
    toned = ImageEnhance.Brightness(toned).enhance(BRIGHTNESS)
    toned = ImageEnhance.Contrast(toned).enhance(CONTRAST)

    toned.save(OUTPUT, quality=76)
    OUTPUT_B64.write_text(base64.b64encode(OUTPUT.read_bytes()).decode("ascii"))
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
