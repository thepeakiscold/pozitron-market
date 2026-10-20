#!/usr/bin/env python3
"""
Normalizes product photos whose file extension is .jpg but whose real content is
AVIF / WebP / PNG. Such files break any code path that calls PIL.Image.open()
directly (Pillow on this system has no AVIF plugin) and some social/CDN pipelines.

Originals are backed up to assets/products/_originals/ before conversion.
Usage: python3 scripts/normalize_product_images.py [--dry-run]
"""
import os
import shutil
import subprocess
import sys

from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCTS_DIR = os.path.join(BASE_DIR, 'assets', 'products')
BACKUP_DIR = os.path.join(PRODUCTS_DIR, '_originals')


def sniff(path: str) -> str:
    with open(path, 'rb') as f:
        h = f.read(32)
    if h[:3] == b'\xff\xd8\xff':
        return 'jpeg'
    if h[:4] == b'\x89PNG':
        return 'png'
    if b'ftypavif' in h or b'ftypavis' in h:
        return 'avif'
    if h[8:12] == b'WEBP':
        return 'webp'
    return 'unknown'


def to_rgb_on_white(im: Image.Image) -> Image.Image:
    if im.mode in ('RGBA', 'LA', 'P'):
        im = im.convert('RGBA')
        bg = Image.new('RGB', im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        return bg
    return im.convert('RGB')


def decode(path: str):
    try:
        return Image.open(path)
    except Exception:
        tmp = f"/tmp/pztr_norm_{os.getpid()}.png"
        r = subprocess.run(['ffmpeg', '-y', '-loglevel', 'quiet', '-i', path, tmp], timeout=20)
        if r.returncode == 0 and os.path.exists(tmp):
            im = Image.open(tmp)
            im.load()
            os.remove(tmp)
            return im
    return None


def main(dry_run: bool = False, convert_all: bool = False):
    converted, failed = 0, []
    os.makedirs(BACKUP_DIR, exist_ok=True)
    for fname in sorted(os.listdir(PRODUCTS_DIR)):
        path = os.path.join(PRODUCTS_DIR, fname)
        if not os.path.isfile(path) or not fname.lower().endswith(('.jpg', '.jpeg')):
            continue
        kind = sniff(path)
        if kind == 'jpeg' or (kind in ('png', 'webp') and not convert_all):
            continue
        if dry_run:
            print(f"[DRY] {fname}: {kind} -> jpeg")
            converted += 1
            continue
        im = decode(path)
        if im is None:
            failed.append(fname)
            continue
        backup = os.path.join(BACKUP_DIR, fname + '.' + kind)
        if not os.path.exists(backup):
            shutil.copy2(path, backup)
        to_rgb_on_white(im).save(path, 'JPEG', quality=93, optimize=True, progressive=True)
        converted += 1
    print(f"converted={converted} failed={len(failed)} {failed[:10]}")


if __name__ == '__main__':
    main(dry_run='--dry-run' in sys.argv, convert_all='--all' in sys.argv)
