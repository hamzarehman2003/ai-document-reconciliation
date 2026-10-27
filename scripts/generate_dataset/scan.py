"""Turn a clean PDF into one that looks scanned (image only, no text layer)."""

import io
import random
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

SCAN_DPI = 150


def make_scanned_copy(source: Path, target: Path, rng: random.Random) -> None:
    """Render each page of `source` to a noisy greyscale image PDF at `target`."""
    with pymupdf.open(source) as original, pymupdf.open() as scanned:
        for page in original:
            pixmap = page.get_pixmap(dpi=SCAN_DPI, colorspace=pymupdf.csGRAY)
            image = Image.frombytes("L", (pixmap.width, pixmap.height), pixmap.samples)
            image = add_scan_effects(image, rng)

            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=rng.randint(55, 75))
            new_page = scanned.new_page(width=page.rect.width, height=page.rect.height)
            new_page.insert_image(new_page.rect, stream=buffer.getvalue())
        scanned.save(target)


def add_scan_effects(image: Image.Image, rng: random.Random) -> Image.Image:
    """Slight tilt, soft focus, faded contrast and dust specks, like a cheap scanner."""
    image = image.rotate(
        rng.uniform(-1.5, 1.5),
        resample=Image.Resampling.BICUBIC,
        fillcolor=255,
    )
    image = image.filter(ImageFilter.GaussianBlur(radius=rng.uniform(0.3, 0.8)))
    image = ImageEnhance.Contrast(image).enhance(rng.uniform(0.75, 0.9))
    image = ImageEnhance.Brightness(image).enhance(rng.uniform(0.92, 1.0))

    draw = ImageDraw.Draw(image)
    for _ in range(rng.randint(150, 400)):
        x = rng.randrange(image.width)
        y = rng.randrange(image.height)
        radius = rng.choice([0, 0, 1])
        draw.ellipse((x, y, x + radius, y + radius), fill=rng.randint(60, 160))
    return image
