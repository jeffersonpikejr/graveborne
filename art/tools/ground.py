#!/usr/bin/env python3
"""Paint the battlefield's ground: seamless top-down textures, one per kind of earth.

    .bvenv/bin/python art/tools/ground.py                 # every texture -> art/sprites/ground_<name>.webp
    .bvenv/bin/python art/tools/ground.py heath water     # just those
    .bvenv/bin/python art/tools/ground.py --sheet out.png # a contact sheet of them all

A texture is SPAN (8) tiles square and wraps on both axes: the game lays one sheet under the whole field and each tile
shows its own window of it, so no two neighbouring tiles repeat. Everything is built from periodic noise (white noise
shaped in the frequency domain, so it tiles by construction), lit from the viewer's lower left like the house rig's key
light, and kept dark and low in contrast: the ground is a stage for the figures, never louder than them.
Needs numpy and Pillow only (no Blender).
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'art', 'sprites')
SPAN = 8            # tiles across a texture
PX = 1024           # 128 px a tile: enough for a 2x display at the default zoom
TILE = PX // SPAN


def hexc(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def fbm(rng, beta=2.0, lo=1.0, hi=None, n=PX):
    """Periodic fractal noise in 0..1: white noise with a 1/f^beta spectrum, band-limited to [lo, hi] cycles."""
    f = np.fft.fft2(rng.standard_normal((n, n)))
    fy = np.fft.fftfreq(n)[:, None] * n
    fx = np.fft.fftfreq(n)[None, :] * n
    r = np.sqrt(fx * fx + fy * fy)
    amp = np.where(r > 0, 1.0 / np.maximum(r, 1e-6) ** (beta / 2.0), 0.0)
    amp = np.where(r < lo, 0.0, amp)
    if hi:
        amp = amp * np.exp(-(r / hi) ** 4)
    v = np.real(np.fft.ifft2(f * amp))
    v -= v.min()
    return (v / max(v.max(), 1e-9)).astype(np.float32)


def norm(v):
    v = v - v.min()
    return v / max(float(v.max()), 1e-9)


def smooth(lo, hi, v):
    d = hi - lo                      # lo > hi runs the step the other way (1 below hi, 0 above lo)
    t = np.clip((v - lo) / (d if abs(d) > 1e-9 else 1e-9), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def shade(h, strength=1.0, light=(-0.62, 0.48, 0.62)):
    """Lambert light on a height field (image y runs down, so a light from the viewer's lower left has +y)."""
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    k = strength * PX / 22.0
    nx, ny, nz = -gx * k, -gy * k, np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    L = np.array(light, np.float32)
    L = L / np.linalg.norm(L)
    d = (nx * L[0] + ny * L[1] + nz * L[2]) / ln
    return d / L[2]            # 1.0 on flat ground


def mix(a, b, t):
    return a + (b - a) * t[..., None]


def ramp(v, stops):
    """Colour a 0..1 field through [(pos, '#hex'), ...]."""
    out = np.zeros(v.shape + (3,), np.float32)
    ps = [p for p, _ in stops]
    cs = [hexc(c) for _, c in stops]
    out[:] = cs[0]
    for i in range(len(stops) - 1):
        t = np.clip((v - ps[i]) / max(ps[i + 1] - ps[i], 1e-9), 0, 1)
        out = np.where((v >= ps[i])[..., None], mix(np.broadcast_to(cs[i], out.shape), np.broadcast_to(cs[i + 1], out.shape), t), out)
    return out


class Layer:
    """An RGBA paint layer drawn at 2x and wrapped, for strokes and stones that must tile."""

    def __init__(self, ss=2):
        self.ss = ss
        self.n = PX * ss
        self.im = Image.new('RGBA', (self.n, self.n), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im, 'RGBA')

    def _wrap(self, x, y, r):
        n = self.n
        for ox in ((0,) + ((n,) if x < r else ()) + ((-n,) if x > n - r else ())):
            for oy in ((0,) + ((n,) if y < r else ()) + ((-n,) if y > n - r else ())):
                yield ox, oy

    def line(self, x0, y0, x1, y1, col, w=1):
        s = self.ss
        x0, y0, x1, y1 = x0 * s, y0 * s, x1 * s, y1 * s
        r = abs(x1 - x0) + abs(y1 - y0) + w * s + 2
        for ox, oy in self._wrap(x0, y0, r):
            self.d.line([x0 + ox, y0 + oy, x1 + ox, y1 + oy], fill=col, width=max(1, int(round(w * s))))

    def blob(self, x, y, rx, ry, col):
        s = self.ss
        x, y, rx, ry = x * s, y * s, rx * s, ry * s
        for ox, oy in self._wrap(x, y, max(rx, ry) + 2):
            self.d.ellipse([x - rx + ox, y - ry + oy, x + rx + ox, y + ry + oy], fill=col)

    def poly(self, pts, col):
        s = self.ss
        pts = [(x * s, y * s) for x, y in pts]
        cx, cy = pts[0]
        r = max(max(abs(x - cx), abs(y - cy)) for x, y in pts) + 2
        for ox, oy in self._wrap(cx, cy, r):
            self.d.polygon([(x + ox, y + oy) for x, y in pts], fill=col)

    def array(self, blur=0.0):
        im = self.im
        if blur:
            im = wrap_blur(im, blur * self.ss)
        im = im.resize((PX, PX), Image.LANCZOS)
        return np.asarray(im, np.float32) / 255.0


def wrap_blur(im, r):
    n = im.size[0]
    pad = int(r * 3) + 2
    big = Image.new(im.mode, (n + 2 * pad, n + 2 * pad))
    for ox in (-n, 0, n):
        for oy in (-n, 0, n):
            big.paste(im, (pad + ox, pad + oy))
    return big.filter(ImageFilter.GaussianBlur(r)).crop((pad, pad, pad + n, pad + n))


def over(rgb, layer):
    a = layer[..., 3:4]
    return rgb * (1 - a) + layer[..., :3] * a


def col8(c, a=255, jitter=0.0, rng=None):
    c = hexc(c) if isinstance(c, str) else np.asarray(c, np.float32)
    if jitter and rng is not None:
        c = np.clip(c * (1 + rng.uniform(-jitter, jitter)) + rng.uniform(-jitter, jitter, 3) * 0.05, 0, 1)
    return tuple(int(round(float(v) * 255)) for v in c) + (int(a),)


def stones(rng, n, rmin, rmax, cols, mask=None, dark='#0d0b08', flat=0.8):
    """Pebbles and stones: a dark contact shadow down-right, the stone, a lit crescent on its lower-left shoulder."""
    sh, st, hl = Layer(), Layer(), Layer()
    placed = 0
    tries = 0
    while placed < n and tries < n * 30:
        tries += 1
        x, y = rng.uniform(0, PX, 2)
        if mask is not None and rng.random() > mask[int(y) % PX, int(x) % PX]:
            continue
        r = rmin + (rmax - rmin) * rng.random() ** 2.2
        rx, ry = r * rng.uniform(0.8, 1.25), r * flat * rng.uniform(0.75, 1.1)
        c = cols[rng.integers(len(cols))]
        sh.blob(x + r * 0.28, y - r * 0.22, rx * 1.12, ry * 1.12, col8(dark, 150))
        st.blob(x, y, rx, ry, col8(c, 255, 0.12, rng))
        hl.blob(x - rx * 0.22, y + ry * 0.2, rx * 0.55, ry * 0.5, col8(hexc(c) * 1.45 + 0.03, 130))
        placed += 1
    return sh.array(blur=1.2), st.array(blur=0.35), hl.array(blur=0.9)


def blades(rng, n, length, cols, mask=None, lean=0.35, width=0.7, alpha=200):
    """Grass: short strokes leaning with the wind, darker ones laid first."""
    ly = Layer()
    order = np.argsort(rng.random(len(cols)))
    for i in range(n):
        x, y = rng.uniform(0, PX, 2)
        if mask is not None and rng.random() > mask[int(y) % PX, int(x) % PX]:
            continue
        ln = length * rng.uniform(0.45, 1.25)
        a = -np.pi / 2 + lean + rng.normal(0, 0.45)
        c = cols[order[i % len(cols)]] if i < n * 0.4 else cols[rng.integers(len(cols))]
        ly.line(x, y, x + np.cos(a) * ln, y + np.sin(a) * ln, col8(c, alpha * rng.uniform(0.55, 1.0), 0.18, rng), width)
    return ly.array(blur=0.25)


def finish(rgb, rng, contrast=1.0, grain=0.012, lift=0.0):
    g = rng.standard_normal(rgb.shape[:2]).astype(np.float32)[..., None] * grain
    rgb = (rgb - 0.5) * contrast + 0.5 + g + lift
    return np.clip(rgb, 0, 1)


# ------------------------------------------------------------------------------------------------ the open ground
def earth(seed, mud, turf, grass, pebble, turf_amt=0.5, blade_n=26000, blade_len=9.0, stone_n=260, relief=1.0,
          wet=0.0, leaf=None, crack=0.0, dead=None, lean=0.35):
    """Open ground: churned mud with turf in patches, grass blades on the turf, pebbles in the bare places.
    mud/turf: colour ramps; grass/pebble: colour lists; leaf: a leaf-litter colour list; dead: dry-stalk colours."""
    rng = np.random.default_rng(seed)
    big = fbm(rng, 2.6, 1, 14)          # where the turf lies
    mid = fbm(rng, 2.0, 6, 70)          # lumps
    fine = fbm(rng, 1.2, 40, 400)       # grit
    h = big * 0.55 + mid * 0.33 + fine * 0.12
    tf = big * 0.7 + mid * 0.3 + (fine - 0.5) * 0.12
    thr = float(np.quantile(tf, 1.0 - turf_amt))        # turf_amt of the ground is turf
    tmask = smooth(thr - 0.03, thr + 0.05, tf)
    base = mix(ramp(norm(mid * 0.6 + fine * 0.4), mud), ramp(norm(mid * 0.5 + fine * 0.5), turf), tmask)
    lit = shade(h, 0.55 * relief)
    rgb = base * np.clip(lit, 0.45, 1.5)[..., None]
    # hollows hold the dark, and the wet
    hollow = smooth(0.42, 0.2, big * 0.5 + mid * 0.5)
    rgb *= (1 - 0.42 * hollow)[..., None]
    if wet:
        pv = big * 0.6 + mid * 0.4
        pq = float(np.quantile(pv, 0.11))
        pool = smooth(pq + 0.03, pq - 0.03, pv) * wet
        sky = hexc('#27313a') * (0.7 + 0.5 * fbm(rng, 2.4, 2, 30))[..., None]
        rgb = mix(rgb, sky, np.clip(pool, 0, 0.8))
    if crack:
        c = np.abs(fbm(rng, 1.9, 8, 60) - 0.5)
        line = smooth(0.012, 0.0, c) * crack * (1 - tmask)
        rgb *= (1 - 0.7 * line)[..., None]
    bare = np.clip(1 - tmask * 1.15, 0, 1)
    if stone_n:
        sh, st, hl = stones(rng, stone_n, 1.2, 6.5, pebble, mask=bare * 0.9 + 0.1)
        rgb = over(over(over(rgb, sh), st), hl)
    if leaf:
        ly = Layer()
        for _ in range(9000):
            x, y = rng.uniform(0, PX, 2)
            r = rng.uniform(1.0, 2.6)
            a = rng.uniform(0, np.pi)
            dx, dy = np.cos(a) * r, np.sin(a) * r * 0.55
            ly.poly([(x - dx, y - dy), (x + dy * 0.6, y - dx * 0.6), (x + dx, y + dy), (x - dy * 0.6, y + dx * 0.6)],
                    col8(leaf[rng.integers(len(leaf))], rng.uniform(110, 210), 0.2, rng))
        rgb = over(rgb, ly.array(blur=0.3))
    if blade_n:
        gm = np.clip(tmask * 1.2 - 0.08, 0, 1)
        dark = [tuple(hexc(c) * 0.55) for c in grass]
        rgb = over(rgb, blades(rng, int(blade_n * 0.7), blade_len * 0.8, dark, gm, lean, 0.9, 170))
        rgb = over(rgb, blades(rng, blade_n, blade_len, grass, gm, lean, 0.7, 190))
    if dead:
        rgb = over(rgb, blades(rng, int(blade_n * 0.18) + 1500, blade_len * 1.3, dead, np.clip(tmask * 0.7 + 0.15, 0, 1), lean + 0.2, 0.6, 150))
    return finish(rgb, rng)


def flagstones(seed, stone=('#3d3a35', '#4a463f', '#35322d', '#44413b'), mortar='#15130f', moss=None, size=1.0):
    """A paved floor: courses of worn flags, their joints dark, some cracked, some sunk."""
    rng = np.random.default_rng(seed)
    rgb = np.zeros((PX, PX, 3), np.float32) + hexc(mortar)
    hgt = np.zeros((PX, PX), np.float32)
    rows = int(round(SPAN * 2 / size))
    rh = PX / rows
    lay, hl = Layer(), Layer()
    for r in range(rows):
        x = rng.uniform(0, rh)
        y0 = r * rh
        start = x
        while x < start + PX - 1:
            w = rh * rng.uniform(0.9, 2.1)
            if x + w > start + PX - rh * 0.6:
                w = start + PX - x
            g = rng.uniform(1.0, 2.2)
            c = stone[rng.integers(len(stone))]
            j = rng.uniform(-1.2, 1.2, 8)
            pts = [(x + g + j[0], y0 + g + j[1]), (x + w - g + j[2], y0 + g + j[3]), (x + w - g + j[4], y0 + rh - g + j[5]),
                   (x + g + j[6], y0 + rh - g + j[7])]
            pts = [((px_ % PX), py_) for px_, py_ in pts] if False else pts
            lay.poly(pts, col8(c, 255, 0.1, rng))
            lay.poly([(p[0] - PX, p[1]) for p in pts], col8(c, 255, 0.1, rng))
            lay.poly([(p[0] + PX, p[1]) for p in pts], col8(c, 255, 0.1, rng))
            for off in (0, -PX, PX):       # a lit lower-left edge, a dark upper-right one
                hl.line(pts[3][0] + off, pts[3][1], pts[2][0] + off, pts[2][1], col8('#8d877a', 70), 1.2)
                hl.line(pts[0][0] + off, pts[0][1], pts[3][0] + off, pts[3][1], col8('#8d877a', 50), 1.0)
                hl.line(pts[0][0] + off, pts[0][1], pts[1][0] + off, pts[1][1], col8('#000000', 90), 1.2)
                hl.line(pts[1][0] + off, pts[1][1], pts[2][0] + off, pts[2][1], col8('#000000', 70), 1.0)
                if rng.random() < 0.16:    # a crack
                    cx, cy = x + w * rng.uniform(0.2, 0.8) + off, y0 + g
                    for _ in range(4):
                        nx_, ny_ = cx + rng.uniform(-5, 5), cy + rh / 4.2
                        hl.line(cx, cy, nx_, ny_, col8('#000000', 150), 0.8)
                        cx, cy = nx_, ny_
            x += w
    rgb = over(rgb, lay.array(blur=0.4))
    wear = fbm(rng, 2.2, 2, 40)
    fine = fbm(rng, 1.0, 60, 500)
    rgb *= (0.74 + 0.46 * wear + 0.10 * (fine - 0.5))[..., None]
    rgb *= np.clip(shade(fbm(rng, 2.0, 10, 90), 0.09), 0.75, 1.25)[..., None]
    rgb = over(rgb, hl.array(blur=0.3))
    if moss:
        m = smooth(0.58, 0.7, fbm(rng, 2.4, 2, 24) * 0.7 + fine * 0.3)
        rgb = mix(rgb, ramp(fine, moss), m * 0.75)
    dirt = smooth(0.6, 0.78, fbm(rng, 2.6, 1, 10))
    rgb = mix(rgb, np.broadcast_to(hexc('#1c1811'), rgb.shape), dirt * 0.55)
    return finish(rgb, rng, grain=0.01)


def road(seed):
    """A road: packed earth paler than the land beside it, stones trodden in, puddled ruts."""
    rng = np.random.default_rng(seed)
    big, mid, fine = fbm(rng, 2.6, 1, 12), fbm(rng, 2.0, 8, 80), fbm(rng, 1.1, 50, 450)
    h = big * 0.4 + mid * 0.4 + fine * 0.2
    rgb = ramp(norm(mid * 0.55 + fine * 0.45), [(0, '#2a241a'), (0.45, '#3f3626'), (0.8, '#4f4531'), (1, '#5a4f39')])
    rgb *= np.clip(shade(h, 0.22), 0.6, 1.35)[..., None]
    pool = smooth(0.30, 0.2, big * 0.55 + mid * 0.45)
    rgb = mix(rgb, np.broadcast_to(hexc('#1d1d1b'), rgb.shape), pool * 0.8)
    rgb = mix(rgb, hexc('#4a5560') * (0.6 + 0.6 * fbm(rng, 2.4, 2, 30))[..., None], smooth(0.24, 0.16, big * 0.55 + mid * 0.45) * 0.55)
    sh, st, hl = stones(rng, 520, 1.0, 5.0, ['#5b554a', '#6a6253', '#4b463c', '#70685a'])
    rgb = over(over(over(rgb, sh), st), hl)
    return finish(rgb, rng)


def mire(seed):
    """Mire: black standing water between hummocks of rotten turf, a scum of weed on it."""
    rng = np.random.default_rng(seed)
    big, mid, fine = fbm(rng, 2.5, 1.5, 16), fbm(rng, 2.0, 8, 80), fbm(rng, 1.1, 50, 450)
    lvl = big * 0.6 + mid * 0.4
    land = smooth(0.46, 0.58, lvl)
    mud = ramp(norm(mid * 0.5 + fine * 0.5), [(0, '#15160f'), (0.5, '#262818'), (1, '#383a22')])
    mud *= np.clip(shade(lvl * 0.7 + fine * 0.3, 0.6), 0.5, 1.5)[..., None]
    water = hexc('#0c1012') + (hexc('#2a3436') - hexc('#0c1012')) * (smooth(0.55, 0.9, fbm(rng, 2.2, 2, 26)) * 0.5)[..., None]
    scum = smooth(0.6, 0.72, fbm(rng, 1.8, 6, 90)) * (1 - land)
    water = mix(water, np.broadcast_to(hexc('#3b4420'), water.shape), scum * 0.6)
    rgb = mix(water, mud, land)
    rim = smooth(0.40, 0.47, lvl) * (1 - land)      # a wet dark shore
    rgb *= (1 - 0.35 * rim)[..., None]
    rgb = over(rgb, blades(rng, 9000, 10.0, ['#4c4f26', '#5c5a2e', '#3a3f1e', '#6a6436'], np.clip(land * 1.1 - 0.1, 0, 1), 0.25, 0.7, 190))
    return finish(rgb, rng)


def water(seed):
    """Deep slow water: near black, a cold sheen along the swells, a few flecks of foam and weed."""
    rng = np.random.default_rng(seed)
    swell = fbm(rng, 2.4, 2, 22)
    rip = fbm(rng, 1.6, 14, 120)
    # stretch the ripples sideways: sample the field with x compressed
    idx = (np.arange(PX)[None, :] // 1 + (np.arange(PX)[:, None] * 0)) % PX
    rip2 = (rip + np.roll(rip, 9, 1) + np.roll(rip, -9, 1) + np.roll(rip, 18, 1) + np.roll(rip, -18, 1)) / 5.0
    h = swell * 0.6 + norm(rip2) * 0.4
    lit = shade(h, 0.28, light=(-0.3, 0.75, 0.55))
    rgb = ramp(norm(h), [(0, '#070b0e'), (0.5, '#101a20'), (0.85, '#1b2a33'), (1, '#27383f')])
    sheen = smooth(1.10, 1.5, lit)
    rgb = mix(rgb, np.broadcast_to(hexc('#5d7582'), rgb.shape), sheen * 0.42)
    rgb *= np.clip(0.75 + 0.25 * lit, 0.5, 1.3)[..., None]
    weed = smooth(0.7, 0.8, fbm(rng, 2.0, 5, 70))
    rgb = mix(rgb, np.broadcast_to(hexc('#26301c'), rgb.shape), weed * 0.4)
    return finish(rgb, rng, grain=0.008)


def planks(seed):
    """Bridge deck: boards laid across the way (the boards run up the image; the game turns the tile for a bridge that
    runs north-south), nailed, split and muddy. Wraps like the rest, so two bridge tiles in a row carry on."""
    rng = np.random.default_rng(seed)
    rgb = np.zeros((PX, PX, 3), np.float32) + hexc('#0b0906')
    lay, hl = Layer(), Layer()
    bw = TILE / 5.0
    for i in range(int(PX / bw)):
        x0 = i * bw
        c = ['#4b3b29', '#574531', '#3f3222', '#5e4b35', '#463726'][rng.integers(5)]
        y = -rng.uniform(0, TILE)
        while y < PX:
            ln = TILE * rng.uniform(1.6, 3.2)
            lay.poly([(x0 + 0.9, y + 0.8), (x0 + bw - 0.9, y + 0.8), (x0 + bw - 0.9, y + ln - 0.8), (x0 + 0.9, y + ln - 0.8)], col8(c, 255, 0.12, rng))
            for yy in (y + 5, y + ln - 5):
                hl.blob(x0 + bw / 2, yy % PX, 1.3, 1.3, col8('#0d0a07', 220))
            y += ln
        hl.line(x0 + 1.4, 0, x0 + 1.4, PX, col8('#8a7556', 46), 1.0)
        hl.line(x0 + bw - 1.2, 0, x0 + bw - 1.2, PX, col8('#000000', 80), 1.0)
    rgb = over(rgb, lay.array(blur=0.35))
    g = fbm(rng, 1.6, 30, 400)
    grainv = norm(g + np.roll(g, 7, 0) + np.roll(g, -7, 0) + np.roll(g, 14, 0) + np.roll(g, -14, 0))   # the grain runs with the board
    rgb *= (0.66 + 0.62 * grainv)[..., None]
    rgb = over(rgb, hl.array(blur=0.3))
    mud = smooth(0.5, 0.85, fbm(rng, 2.8, 1, 9))
    rgb = mix(rgb, np.broadcast_to(hexc('#221b11'), rgb.shape), mud * 0.4)
    return finish(rgb, rng, grain=0.01)


def blight(seed):
    """The Blight's stain, laid over any ground (RGBA): dead black earth cracked with violet light."""
    rng = np.random.default_rng(seed)
    big, mid = fbm(rng, 2.4, 2, 18), fbm(rng, 1.9, 8, 70)
    vein = np.abs(fbm(rng, 1.9, 6, 46) - 0.5)
    v = smooth(0.022, 0.0, vein)
    glow = smooth(0.09, 0.0, vein)
    rgb = ramp(norm(mid), [(0, '#0d0a10'), (0.6, '#1c1622'), (1, '#2a2233')])
    rgb = mix(rgb, np.broadcast_to(hexc('#5a3d80'), rgb.shape), glow * 0.55)
    rgb = mix(rgb, np.broadcast_to(hexc('#b58ae6'), rgb.shape), v * 0.9)
    a = np.clip(0.50 + 0.25 * big + 0.35 * glow, 0, 0.92)
    return np.concatenate([finish(rgb, rng, grain=0.008), a[..., None]], -1)


def chasm(seed):
    """The drop: nothing, with the rock's last ledges just catching the light."""
    rng = np.random.default_rng(seed)
    big, mid = fbm(rng, 2.6, 1, 10), fbm(rng, 2.0, 10, 90)
    rgb = ramp(norm(big * 0.7 + mid * 0.3), [(0, '#020203'), (0.6, '#07080a'), (0.85, '#101114'), (1, '#1a1b1e')])
    return finish(rgb, rng, grain=0.006)


MUD = [(0, '#1a150e'), (0.5, '#2d2518'), (1, '#3e3423')]
TEXTURES = {
    # heath: the common ground of the March — churned mud and coarse grass (fields, river, boulders, ritual)
    'heath': lambda: earth(11, MUD, [(0, '#22241a'), (0.5, '#31341f'), (1, '#3f4226')],
                           ['#4a4d2a', '#57582f', '#3c4023', '#636037', '#50502c'], ['#5a554a', '#48443a', '#6b6456'],
                           turf_amt=0.5, dead=['#7d7442', '#8a7d4a']),
    # forest floor: needle mould and moss in the dark under trees (woods)
    'forest': lambda: earth(12, [(0, '#14110a'), (0.5, '#231c11'), (1, '#30271a')], [(0, '#181d12'), (0.5, '#242b19'), (1, '#30381f')],
                            ['#384222', '#434c27', '#2c351b'], ['#4a463c', '#3c382f'], turf_amt=0.5, blade_n=14000,
                            blade_len=7.0, stone_n=120, leaf=['#4a3320', '#5a3f22', '#3a2a1a', '#6a4a26', '#33301c']),
    # marsh: sodden black ground, standing water in the hollows (marsh, causeway)
    'marsh': lambda: earth(13, [(0, '#13140d'), (0.5, '#222416'), (1, '#30321f')], [(0, '#1d2014'), (0.5, '#2a2e1b'), (1, '#373b22')],
                           ['#50522b', '#5d5a30', '#424424', '#6a6338'], ['#45443a'], turf_amt=0.5, blade_len=11.0,
                           stone_n=60, wet=0.6, dead=['#857b48']),
    # stony: scree and thin soil of the high places (pass, cliffs, quarry)
    'stony': lambda: earth(14, [(0, '#221f19'), (0.5, '#37322a'), (1, '#4a4439')], [(0, '#262717'), (0.5, '#35371f'), (1, '#424426')],
                           ['#5a5a30', '#66633a', '#494a28'], ['#6a6559', '#575248', '#7b7568', '#4a463d'], turf_amt=0.22,
                           blade_n=9000, stone_n=1500, relief=1.4, crack=0.6, dead=['#8a8050']),
    # dirt: trodden yard earth, grass only at the edges (town, ruins, camp)
    'dirt': lambda: earth(15, [(0, '#231b10'), (0.5, '#3a2e1d'), (1, '#4c3e28')], [(0, '#262814'), (0.5, '#36391e'), (1, '#454725')],
                          ['#585c2c', '#646634', '#494c24'], ['#5f594c', '#4d483d', '#6e6757'], turf_amt=0.26, blade_n=11000,
                          stone_n=620, crack=0.35, dead=['#8a7b4a']),
    # ashen: Blight-touched ground, the grass dead and grey with a violet cast (menhir fields)
    'ashen': lambda: earth(16, [(0, '#17131a'), (0.5, '#28232b'), (1, '#373039')], [(0, '#211f22'), (0.5, '#302d2e'), (1, '#3d3a37')],
                           ['#5b5650', '#6a6458', '#4a4644', '#5a4d66'], ['#55505a', '#443f49', '#676070'], turf_amt=0.45,
                           blade_len=8.0, stone_n=420, crack=0.5, dead=['#857d6c']),
    # grave turf: rank dark grass over turned earth (graveyard)
    'grave': lambda: earth(17, [(0, '#171310'), (0.5, '#29211a'), (1, '#372d22')], [(0, '#1a1f14'), (0.5, '#262d1b'), (1, '#323a21')],
                           ['#414a2a', '#4d552f', '#353d22', '#585d35'], ['#6b675e', '#56534b', '#807b70'], turf_amt=0.7,
                           blade_len=11.0, stone_n=160, dead=['#6f6c44']),
    # flagstones: a paved floor underground (crypt)
    'flag': lambda: flagstones(18),
    'road': lambda: road(21),
    'mire': lambda: mire(22),
    'water': lambda: water(23),
    'planks': lambda: planks(24),
    'chasm': lambda: chasm(25),
    'blight': lambda: blight(26),
}


def crag(seed):
    """High rock for the march map's mountains: ridges catching the light, scree in the folds."""
    rng = np.random.default_rng(seed)
    big, mid, fine = fbm(rng, 2.4, 2, 14), fbm(rng, 2.0, 8, 70), fbm(rng, 1.2, 40, 400)
    ridge = norm(1 - np.abs(big - 0.5) * 2) * 0.6 + norm(1 - np.abs(mid - 0.5) * 2) * 0.3 + fine * 0.1
    rgb = ramp(norm(ridge), [(0, '#1f1d1a'), (0.45, '#3a3731'), (0.8, '#55514a'), (1, '#76726a')])
    rgb *= np.clip(shade(ridge, 1.1), 0.4, 1.6)[..., None]
    return finish(rgb, rng)


# the march map: the same earth seen from far higher (a quarter of the scale), one sheet per kind of country
MAP = {'plains': 'heath', 'forest': 'forest', 'hills': 'stony', 'marsh': 'mire', 'mountain': None, 'blight': 'ashen', 'setl': 'dirt'}
MAP_TINT = {'plains': (1.0, 1.0, 1.0), 'forest': (0.72, 0.86, 0.72), 'hills': (1.12, 1.04, 0.92), 'marsh': (0.9, 1.0, 1.0),
            'mountain': (0.8, 0.79, 0.76), 'blight': (1.05, 0.9, 1.25), 'setl': (1.15, 1.08, 0.95)}


def map_sheets(out, made, px=320):
    for name, src in MAP.items():
        arr = (made.get(src) if src else None)
        if arr is None:
            arr = TEXTURES[src]() if src else crag(41)
        rgb = arr[..., :3]
        if name == 'blight':
            b = made.get('blight') if made.get('blight') is not None else TEXTURES['blight']()
            rgb = rgb * (1 - b[..., 3:4] * 0.6) + b[..., :3] * b[..., 3:4] * 0.6
        rgb = np.clip(np.power(np.clip(rgb, 0, 1), 0.78) * 1.12 * np.array(MAP_TINT[name], np.float32), 0, 1)   # a map reads lighter than the ground underfoot
        im = Image.fromarray((rgb * 255 + 0.5).astype(np.uint8), 'RGB').resize((px, px), Image.LANCZOS)
        dst = os.path.join(out, f'map_{name}.webp')
        im.save(dst, 'WEBP', quality=80, method=6)
        print(f'{dst}  {os.path.getsize(dst) / 1024:.0f} KB', flush=True)


def ui_grain(out, px=256):
    """The interface's own surface: a faint worn-leather grain laid over every panel (RGBA, mostly transparent)."""
    rng = np.random.default_rng(51)
    a_ = fbm(rng, 1.6, 6, 120, n=px)
    b_ = fbm(rng, 2.4, 1, 10, n=px)
    v = norm(a_ * 0.7 + b_ * 0.3)
    lum = np.where(v > 0.5, 1.0, 0.0).astype(np.float32)           # light flecks and dark pores
    alpha = np.abs(v - 0.5) * 2 * 0.16
    arr = np.stack([lum * 0.93, lum * 0.86, lum * 0.72, alpha], -1)
    im = Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA')
    dst = os.path.join(out, 'ui_grain.webp')
    im.save(dst, 'WEBP', quality=80, method=6, exact=True)
    print(f'{dst}  {os.path.getsize(dst) / 1024:.0f} KB', flush=True)


def edge_masks(out):
    """The ragged edge one ground takes when it runs over its neighbour: an alpha mask per side (the paint is opaque on
    that side of the tile and breaks up toward the middle). The game masks a window of the neighbour's own texture."""
    rng = np.random.default_rng(31)
    n = 192
    for side in 'nesw':
        nz = fbm(rng, 1.9, 2, 40, n=n * 2)[:n, :n]
        t = np.linspace(0, 1, n, dtype=np.float32)
        d = {'n': t[:, None] + 0 * t[None, :], 's': 1 - t[:, None] + 0 * t[None, :], 'w': t[None, :] + 0 * t[:, None],
             'e': 1 - t[None, :] + 0 * t[:, None]}[side]
        # reach about a quarter of the tile in, ragged by the noise; fade the mask's two ends so corners don't square off
        a = smooth(0.30, 0.10, d + (nz - 0.5) * 0.42)
        a8 = (np.clip(a, 0, 1) * 255).astype(np.uint8)
        im = Image.merge('RGBA', [Image.new('L', (n, n), 255)] * 3 + [Image.fromarray(a8, 'L')])
        im.save(os.path.join(out, f'ground_edge_{side}.webp'), 'WEBP', lossless=True, method=6, exact=True)


def save(name, arr, out, quality=82):
    a8 = (np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)
    im = Image.fromarray(a8, 'RGBA' if a8.shape[2] == 4 else 'RGB')
    dst = os.path.join(out, f'ground_{name}.webp')
    im.save(dst, 'WEBP', quality=quality, method=6, exact=True)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('names', nargs='*')
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--sheet')
    ap.add_argument('--quality', type=int, default=82)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    names = a.names or list(TEXTURES)
    made = {}
    for n in names:
        if n not in TEXTURES:
            sys.exit(f'no such ground: {n} (have {", ".join(TEXTURES)})')
        made[n] = TEXTURES[n]()
        dst = save(n, made[n], a.out, a.quality)
        print(f'{dst}  {os.path.getsize(dst) / 1024:.0f} KB', flush=True)
    if not a.names:
        edge_masks(a.out)
        map_sheets(a.out, made)
        ui_grain(a.out)
    if a.sheet:
        k = 384
        sh = Image.new('RGB', (k * 4, k * ((len(made) + 3) // 4)), (10, 9, 7))
        for i, (n, arr) in enumerate(made.items()):
            rgb = arr[..., :3] if arr.shape[2] == 3 else arr[..., :3] * arr[..., 3:4] + hexc('#3b3a26') * (1 - arr[..., 3:4])
            im = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).crop((0, 0, k, k))
            sh.paste(im, ((i % 4) * k, (i // 4) * k))
            ImageDraw.Draw(sh).text(((i % 4) * k + 6, (i // 4) * k + 4), n, fill=(232, 217, 160))
        sh.save(a.sheet)
        print(a.sheet)


if __name__ == '__main__':
    main()
