"""Head review renders: faces in one light, at one scale, from matched cameras.

    python art/blender/review_heads.py views  [--out DIR]    both anchors: front, three-quarters from both sides,
                                                             profile, and a perspective neck-and-shoulders view
    python art/blender/review_heads.py styles [--out DIR]    every hairstyle on each anchor (his beards too),
                                                             from the front and the back three-quarter
    python art/blender/review_heads.py looks  [--out DIR] [--form m|f] [--count N] [--first K]
                                                             the look pool (gb/looks.py), a three-quarter each

Each mode writes its renders and a labelled contact sheet (<mode>_sheet.png) to DIR (default art/renders/heads).
Framing is fixed, never fitted to a head: every head shares one ortho scale and target, so size differences stay
visible (hers is 5% smaller). The perspective view is for judging the neck; sprites and portraits stay orthographic.
"""
import argparse
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, 'assets')]

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from gb import face as F, looks as LK, mat as M, rig  # noqa: E402

HEAD_Z = 1.2
BG = (34, 33, 31)
VIEWS = {   # name: (azimuth, elevation, ortho scale or None for perspective)
    'front': (0.0, 0.0, 0.3), 'tq_left': (28.0, 6.0, 0.3), 'tq_right': (-28.0, 6.0, 0.3), 'profile': (90.0, 0.0, 0.3),
    'neck': (35.0, -4.0, None),
}


def stage(res, samples):
    rig.stage(elev=0, res=res, samples=samples, look='portrait')
    M.set_mode(revenant=False)


def head(look, tag, bare=False):
    """Build a look's head at HEAD_Z (bare: shaved and clean-shaven, brows kept, so the skull reads)."""
    if bare:
        look = dict(look, style='shaved', beard=None)
    root, _ = LK.build_head(look, tag=tag)
    root.location = (0.0, 0.0, HEAD_Z)
    bpy.context.view_layer.update()
    return root


def shoot(path, az, el, scale, target=(0.0, 0.0, HEAD_Z - 0.03)):
    """Aim the house camera: ortho at `scale`, or perspective (scale None) for a close, slightly low bust."""
    cam = bpy.context.scene.camera
    th, a = math.radians(el), math.radians(az)
    d = Vector((-math.sin(a) * math.cos(th), math.cos(a) * math.cos(th), -math.sin(th)))
    if scale is None:       # a 50 mm lens at arm's length: the head, the neck and the top of the shoulders
        cam.data.type = 'PERSP'
        cam.data.sensor_fit, cam.data.sensor_width, cam.data.lens = 'AUTO', 36.0, 50.0
        cam.data.shift_x = cam.data.shift_y = 0.0
        t = Vector(target) + Vector((0.0, 0.0, -0.035))
        cam.location = t - d * 0.56
    else:
        cam.data.type = 'ORTHO'
        cam.data.ortho_scale = scale
        cam.location = Vector(target) - d * 10.0
    cam.rotation_euler = (math.pi / 2 - th, 0.0, a)
    rig.render(path)


def sheet(out, cells, cols, label_h=34):
    """cells: [(png, label)] -> one contact sheet on the board's ground."""
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
    except OSError:
        font = ImageFont.load_default()
    ims = []
    for p, label in cells:
        im = Image.open(p).convert('RGBA')
        bg = Image.new('RGBA', im.size, BG + (255,))
        bg.alpha_composite(im)
        ims.append((bg.convert('RGB'), label))
    w, h = ims[0][0].size
    rows = (len(ims) + cols - 1) // cols
    sh = Image.new('RGB', (w * cols, (h + label_h) * rows), BG)
    dr = ImageDraw.Draw(sh)
    for i, (im, label) in enumerate(ims):
        x, y = w * (i % cols), (h + label_h) * (i // cols)
        sh.paste(im, (x, y))
        for j, line in enumerate(label.split('\n')[:2]):
            dr.text((x + 8, y + h + 2 + 15 * j), line, fill=(216, 205, 184), font=font)
    sh.save(out)
    print('[sheet]', out, flush=True)


def views(a):
    cells = []
    for form in ('m', 'f'):
        for bare in (True, False):
            stage(a.res, a.samples)
            head(LK.anchor(form), tag=f'{form}_bare' if bare else None, bare=bare)
            for name, (az, el, scale) in VIEWS.items():
                if bare and name == 'neck':
                    continue
                p = os.path.join(a.out, f'view_{form}_{"bare" if bare else "dressed"}_{name}.png')
                shoot(p, az, el, scale)
                cells.append((p, f'{LK.FORMS[form]} {"bare" if bare else "dressed"} · {name.replace("_", " ")}'))
    sheet(os.path.join(a.out, 'views_sheet.png'), cells, cols=5)


def styles(a):
    cells = []
    for form in ('f', 'm'):
        entries = [(s, None, 0.0) for s in F.STYLES if form == 'm' or s not in ('crop', 'buzz', 'shaved')]
        if form == 'm':     # the anchor crop with each beard, and receding
            entries = ([('crop', b, 0.0) for b in F.BEARDS] + [('crop', None, 0.0), ('crop', 'short', 0.8)]
                       + [(s, 'stubble', 0.0) for s in F.STYLES if s not in ('crop', 'bob', 'long', 'bun', 'braids')])
        for style, beard, recede in entries:
            t = time.time()
            stage(a.res, a.samples)
            look = dict(LK.anchor(form), style=style, beard=beard, recede=recede)
            head(look, tag=f'{form}_{style}_{beard}_{recede}')
            label = f'{style}' + (f' · {beard} beard' if beard else '') + (' · receding' if recede else '')
            for name, az, el in (('front', 28.0, 6.0), ('back', 150.0, 8.0)):
                p = os.path.join(a.out, f'style_{form}_{style}_{beard}_{recede}_{name}.png')
                shoot(p, az, el, 0.36, target=(0.0, 0.0, HEAD_Z - 0.045))
                cells.append((p, f'{LK.FORMS[form]} · {label}'))
            print(f'[style] {form} {label}: {time.time() - t:.1f}s', flush=True)
    sheet(os.path.join(a.out, 'styles_sheet.png'), cells, cols=6)


def describe(lk):
    bits = [lk['style']] + ([f"{lk['beard']} beard"] if lk['beard'] else [])
    if lk['recede']:
        bits.append('receding')
    if lk['scar']:
        bits.append(f"{lk['scar'][0]} scar")
    if lk['crooked']:
        bits.append('broken nose')
    fa = lk['factors']
    shape = ', '.join(w for w, v in (('broad', fa.get('build', 0) > 1), ('slight', fa.get('build', 0) < -1),
                                     ('long', fa.get('length', 0) > 1), ('short', fa.get('length', 0) < -1),
                                     ('gaunt', fa.get('lean', 0) > 1), ('full', fa.get('lean', 0) < -1)) if v)
    return f"{lk['id']} · age {lk['age']:.2f}" + (f' · {shape}' if shape else '') + '\n' + ' · '.join(bits)


def looks(a):
    cells = []
    for form in ([a.form] if a.form else ['m', 'f']):
        for n in range(a.first, a.first + a.count):
            t = time.time()
            lk = LK.roll(form, n)
            stage(a.res, a.samples)
            head(lk, tag=lk['id'])
            p = os.path.join(a.out, f"look_{lk['id']}.png")
            shoot(p, 28.0, 6.0, 0.36, target=(0.0, 0.0, HEAD_Z - 0.045))
            cells.append((p, describe(lk)))
            print(f"[look] {lk['id']}: {time.time() - t:.1f}s", flush=True)
    sheet(os.path.join(a.out, 'looks_sheet.png'), cells, cols=a.cols)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['views', 'styles', 'looks'])
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'renders', 'heads'))
    ap.add_argument('--res', type=int, default=384)
    ap.add_argument('--samples', type=int, default=24)
    ap.add_argument('--form', choices=['m', 'f'])
    ap.add_argument('--count', type=int, default=LK.POOL)
    ap.add_argument('--first', type=int, default=0)
    ap.add_argument('--cols', type=int, default=6)
    a = ap.parse_args()
    a.out = os.path.normpath(a.out)
    os.makedirs(a.out, exist_ok=True)
    {'views': views, 'styles': styles, 'looks': looks}[a.mode](a)


if __name__ == '__main__':
    main()
