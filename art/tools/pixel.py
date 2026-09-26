"""Pixel-art pass for portraits: render in 3D, finish as a sprite.

    python art/tools/pixel.py art/renders/fighter/*_portrait.png --out art/portraits --px 64 --colors 28

Downsamples a portrait render to `px` pixels, cuts it to a small shared palette with no dithering (the look of
hand-placed pixels), and scales it back up with nearest-neighbour so every pixel stays a crisp square. The
background is the portrait frame's charcoal, like the reference sheet.
"""
import argparse
import os

from PIL import Image

BG = (34, 33, 31, 255)


def pixelate(path, px=64, colors=28, scale=6, bg=BG):
    im = Image.open(path).convert('RGBA')
    base = Image.new('RGBA', im.size, bg)
    base.alpha_composite(im)
    small = base.convert('RGB').resize((px, px), Image.LANCZOS)
    q = small.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    return q.convert('RGB').resize((px * scale, px * scale), Image.NEAREST)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('paths', nargs='+')
    ap.add_argument('--out', required=True)
    ap.add_argument('--px', type=int, default=64)
    ap.add_argument('--colors', type=int, default=28)
    ap.add_argument('--scale', type=int, default=6)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for p in a.paths:
        name = os.path.splitext(os.path.basename(p))[0].replace('_portrait', '')
        dst = os.path.join(a.out, name + '.png')
        pixelate(p, a.px, a.colors, a.scale).save(dst, optimize=True)
        print(dst)
