"""Download real JPEG photos for KaamDo UI + demo seed (not illustrations)."""

from __future__ import annotations

import io
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_IMAGES = ROOT / 'frontend' / 'assets' / 'images'
DEMO_PHOTOS = ROOT / 'backend' / 'media' / 'demo_seed'
USER_LOGO_CANDIDATES = [
    Path(r'C:\Users\karna-gr\.cursor\projects\d-project-kaam-do-Kaamdo-1\assets')
    / '342b991a-4478-42df-9442-1a201aa92d47-1806b741-c2c2-454b-9f06-c2d808c725e9.png',
    ROOT / 'frontend' / 'assets' / 'images' / 'logo-source.png',
]

# Curated Unsplash stills (real photos). Query params keep files web-sized.
PHOTO_URLS = {
    # Daily service categories
    'services/plumber.jpg': 'https://images.unsplash.com/photo-1607472586893-edb57bdc0e39?auto=format&fit=crop&w=800&h=500&q=80',
    'services/electrician.jpg': 'https://images.unsplash.com/photo-1621905251189-08b45d6a269e?auto=format&fit=crop&w=800&h=500&q=80',
    'services/house-clean.jpg': 'https://images.unsplash.com/photo-1581578731548-c64695cc6952?auto=format&fit=crop&w=800&h=500&q=80',
    'services/painter.jpg': 'https://images.unsplash.com/photo-1562259949-e8e7689d7828?auto=format&fit=crop&w=800&h=500&q=80',
    'services/ac-repair.jpg': 'https://images.unsplash.com/photo-1581092160562-40aa08e78837?auto=format&fit=crop&w=800&h=500&q=80',  # technician / tools
    'services/washroom-cleaning.jpg': 'https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=800&h=500&q=80',
    'services/agriculture-equipment-renting.jpg': 'https://images.unsplash.com/photo-1625246333195-78d9c38ad449?auto=format&fit=crop&w=800&h=500&q=80',
    'services/service.jpg': 'https://images.unsplash.com/photo-1504328345606-18bbc8c9d7d1?auto=format&fit=crop&w=800&h=500&q=80',
    # Account / home marketplace tiles
    'marketplace/daily.jpg': 'https://images.unsplash.com/photo-1581578731548-c64695cc6952?auto=format&fit=crop&w=800&h=500&q=80',
    'marketplace/jobs.jpg': 'https://images.unsplash.com/photo-1504307651254-35680f356dfd?auto=format&fit=crop&w=800&h=500&q=80',
    'marketplace/equipment.jpg': 'https://images.unsplash.com/photo-1574943320219-553eb213f72d?auto=format&fit=crop&w=800&h=500&q=80',
    'marketplace/farm.jpg': 'https://images.unsplash.com/photo-1625246333195-78d9c38ad449?auto=format&fit=crop&w=800&h=500&q=80',
    # Listing card fallbacks
    'listings/job.jpg': 'https://images.unsplash.com/photo-1504307651254-35680f356dfd?auto=format&fit=crop&w=960&h=560&q=80',
    'listings/farm.jpg': 'https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=960&h=560&q=80',
    'listings/equipment.jpg': 'https://images.unsplash.com/photo-1574943320219-553eb213f72d?auto=format&fit=crop&w=960&h=560&q=80',
    # Placeholders
    'placeholders/hero-bg.jpg': 'https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=1600&h=900&q=80',
    'placeholders/avatar-default.jpg': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=400&h=400&q=80',
    'placeholders/tractor-default.jpg': 'https://images.unsplash.com/photo-1574943320219-553eb213f72d?auto=format&fit=crop&w=960&h=560&q=80',
}

DEMO_URLS = {
    'workers/plumber.jpg': 'https://images.unsplash.com/photo-1607472586893-edb57bdc0e39?auto=format&fit=crop&w=640&h=640&q=80',
    'workers/electrician.jpg': 'https://images.unsplash.com/photo-1621905251189-08b45d6a269e?auto=format&fit=crop&w=640&h=640&q=80',
    'workers/cleaner.jpg': 'https://images.unsplash.com/photo-1581578731548-c64695cc6952?auto=format&fit=crop&w=640&h=640&q=80',
    'equipment/tractor.jpg': 'https://images.unsplash.com/photo-1574943320219-553eb213f72d?auto=format&fit=crop&w=960&h=600&q=80',
    'equipment/pump.jpg': 'https://images.unsplash.com/photo-1625246333195-78d9c38ad449?auto=format&fit=crop&w=960&h=600&q=80',
    'equipment/tiller.jpg': 'https://images.unsplash.com/photo-1574943320219-553eb213f72d?auto=format&fit=crop&w=960&h=600&q=80',
}

USER_AGENT = 'KaamDoAssetFetcher/1.0 (+local-dev)'


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def save_jpeg(path: Path, data: bytes, size: tuple[int, int] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.open(io.BytesIO(data)).convert('RGB')
    if size:
        image = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
    image.save(path, format='JPEG', quality=82, optimize=True)


def fallback_jpeg(path: Path, color: tuple[int, int, int], label: str, size=(640, 400)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new('RGB', size, color)
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype('arial.ttf', 48)
    except OSError:
        font = ImageFont.load_default()
    text = label[:28]
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size[0] - tw) / 2, (size[1] - th) / 2), text, fill=(255, 255, 255), font=font)
    image.save(path, format='JPEG', quality=82)


def download_map(base: Path, mapping: dict[str, str], size: tuple[int, int] | None = None) -> None:
    for relative, url in mapping.items():
        target = base / relative
        try:
            save_jpeg(target, fetch_bytes(url), size=size)
            print('OK', target.relative_to(ROOT))
        except (urllib.error.URLError, OSError, ValueError) as exc:
            print('FALLBACK', target.relative_to(ROOT), '-', exc)
            fallback_jpeg(target, (35, 126, 67), target.stem.replace('-', ' ').title(), size or (800, 500))


def install_logo() -> None:
    source = next((path for path in USER_LOGO_CANDIDATES if path.exists()), None)
    if source is None:
        print('Logo source missing; keeping existing logo files if present.')
        return

    raw = Image.open(source).convert('RGBA')
    # Drop near-black studio background so navbar stays clean on white.
    pixels = raw.load()
    width, height = raw.size
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if r < 28 and g < 28 and b < 28:
                pixels[x, y] = (r, g, b, 0)

    logo_png = FRONTEND_IMAGES / 'logo.png'
    logo_png.parent.mkdir(parents=True, exist_ok=True)
    raw.save(logo_png, format='PNG', optimize=True)

    # Square favicon crop around the mark.
    bbox = raw.getbbox() or (0, 0, width, height)
    cropped = raw.crop(bbox)
    side = max(cropped.size)
    square = Image.new('RGBA', (side, side), (0, 0, 0, 0))
    square.paste(cropped, ((side - cropped.size[0]) // 2, (side - cropped.size[1]) // 2))
    favicon = square.resize((192, 192), Image.Resampling.LANCZOS)
    favicon.save(FRONTEND_IMAGES / 'favicon.png', format='PNG', optimize=True)
    print('OK', logo_png.relative_to(ROOT))
    print('OK', (FRONTEND_IMAGES / 'favicon.png').relative_to(ROOT))


if __name__ == '__main__':
    download_map(FRONTEND_IMAGES, PHOTO_URLS)
    download_map(DEMO_PHOTOS, DEMO_URLS)
    install_logo()
    print('Real photo assets ready under', FRONTEND_IMAGES)
    print('Demo photos ready under', DEMO_PHOTOS)
