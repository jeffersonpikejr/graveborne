"""Post-process master renders into shippable sprites and review sheets.

    python art/tools/post.py ship  art/renders/fighter/*.png   --out art/sprites
    python art/tools/post.py sheet art/renders/fighter/*.png   --out review.png [--labels a b c]

ship:  master (1.5 tiles square, tile centre at 50%/74%) -> <name>.webp at 384px, alpha kept.
sheet: each master at the game's real on-screen sizes, over the battle map's own ground colour — a sprite is
       judged at 45px (phone, 1x zoom) and 60px (desktop, 1x), not at the size it was rendered.
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFont

GROUND = (40, 36, 27, 255)          # TILE_BG.grass  #28241b
GROUND_LIT = (46, 42, 32, 255)
SHIP_PX = 384                       # 256 px per tile: covers the 2.8x zoom on a 2x display
CANVAS = 1.5                        # tiles across a master
DISPLAY = [('phone 1x', 30), ('desktop 1x', 40), ('zoom 1.5x', 60), ('zoom 2.8x', 112)]   # tile px on screen


def load(path):
    return Image.open(path).convert('RGBA')


def ship(paths, out, px=SHIP_PX, quality=90):
    os.makedirs(out, exist_ok=True)
    for p in paths:
        im = load(p).resize((px, px), Image.LANCZOS)
        name = os.path.splitext(os.path.basename(p))[0]
        dst = os.path.join(out, name + '.webp')
        im.save(dst, 'WEBP', quality=quality, method=6, exact=True)
        print(f'{dst}  {os.path.getsize(dst) / 1024:.1f} KB')


def _font(size):
    for f in ('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def tile_bg(w, h, ts, ox=0, oy=0):
    """A patch of the battle map's ground with faint tile boundaries, so scale reads correctly."""
    bg = Image.new('RGBA', (w, h), GROUND)
    d = ImageDraw.Draw(bg)
    for y in range(-ts, h + ts, ts):
        for x in range(-ts, w + ts, ts):
            if ((x - ox) // ts + (y - oy) // ts) % 2 == 0:
                d.rectangle([x + ox % ts, y + oy % ts, x + ox % ts + ts - 1, y + oy % ts + ts - 1], fill=GROUND_LIT)
    return bg


def sheet(paths, out, labels=None, scale=2):
    """One row per master: the big render, then the sprite at each real display size.
    Rendered at `scale`x (a 2x display) and never upscaled, so small sizes look exactly as they will."""
    labels = labels or [os.path.splitext(os.path.basename(p))[0] for p in paths]
    big = 300
    pad = 22
    cols = [big] + [int(ts * CANVAS * scale) for _, ts in DISPLAY]
    W = pad + sum(c + pad for c in cols)
    rowh = big + 46
    H = 40 + rowh * len(paths) + pad
    sh = Image.new('RGBA', (W, H), (16, 14, 12, 255))
    d = ImageDraw.Draw(sh)
    f, fs = _font(16), _font(12)
    x = pad
    for i, c in enumerate(cols):
        t = 'master render' if i == 0 else f'{DISPLAY[i - 1][0]} ({DISPLAY[i - 1][1]}px tile)'
        d.text((x, 12), t, fill=(201, 162, 39, 255), font=fs)
        x += c + pad
    for r, (p, lab) in enumerate(zip(paths, labels)):
        im = load(p)
        y0 = 40 + r * rowh
        x = pad
        for i, c in enumerate(cols):
            ts = big / CANVAS if i == 0 else DISPLAY[i - 1][1] * scale
            bg = tile_bg(c, c, int(ts), ox=int((c - ts) / 2), oy=int(c * 0.74 - ts / 2))
            spr = im.resize((c, c), Image.LANCZOS)
            bg.alpha_composite(spr)
            sh.alpha_composite(bg, (x, y0 + (big - c)))
            x += c + pad
        d.text((pad, y0 + big + 8), lab, fill=(216, 205, 184, 255), font=f)
    sh.convert('RGB').save(out)
    print(out)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['ship', 'sheet'])
    ap.add_argument('paths', nargs='+')
    ap.add_argument('--out', required=True)
    ap.add_argument('--labels', nargs='*')
    a = ap.parse_args()
    if a.cmd == 'ship':
        ship(a.paths, a.out)
    else:
        sheet(a.paths, a.out, a.labels)
