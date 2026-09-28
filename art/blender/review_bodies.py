"""Body review renders: the bare bodies and the armour laid on them, male and female, at one scale.

    python art/blender/review_bodies.py [--out DIR] [--res 640] [--samples 24] [--asset fighter]

Writes, to DIR (default art/renders/bodies):
  bare_<m|f>_<front|side|back|tq>.png    the bare body in a chest wrap and shorts, as on the reference sheet
  kit_<m|f>_<front|side|back>.png        the asset's base kit on it, unarmed, so the armour's waist and hips show
  kit_<m|f>_game.png                     the kit as the game shows it: armed, from the battle camera
  measures.json                          heights, head counts and widths, from the model
  (--only variants) var_<m|f>_<lean|anchor|heavy|tall|short>.png: the guide's variation row on either anchor
and three sheets: bare_sheet.png (with each body's head-count scale), kit_sheet.png, and silhouettes.png (her outline
filled, his dashed over it, feet aligned; bare and in the kit).
Every straight view shares one ortho scale and target, never fitted to a body, so the difference in size stays real.
"""
import argparse
import importlib
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, 'assets')]

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from gb import body as B, face as F, grit as G, looks as LK, mat as M, rig  # noqa: E402

SCALE, TARGET = 2.1, 0.96          # the straight views: metres across the frame, the height they centre on
BG = (34, 33, 31)
VIEWS = {'front': 0.0, 'side': 90.0, 'back': 180.0, 'tq': 30.0}


def shoot(path, az):
    cam = bpy.context.scene.camera
    a = math.radians(az)
    cam.data.type, cam.data.ortho_scale = 'ORTHO', SCALE
    cam.location = Vector((0.0, 0.0, TARGET)) - Vector((-math.sin(a), math.cos(a), 0.0)) * 10.0
    cam.rotation_euler = (math.pi / 2, 0.0, a)
    rig.render(path)


def head_marks(fr, look):
    """The skull's crown and the chin in figure space, from the head's own field (hair left out, as figure drawing
    measures a head)."""
    L = F.Layout(LK.settings(look) if not look.get('anchor') else LK.FORMS[look['form']])
    c = fr.head_frame(portrait=True).translation.z
    top = next(z for z in np.arange(0.2, 0.0, -0.0005) if F.field(np.array([[0.0, 0.014, z]], np.float32), L)[0] < 0)
    ys = np.linspace(-0.11, -0.062, 49).astype(np.float32)
    chin = next(z for z in np.arange(-0.16, -0.05, 0.0005)
                if (F.field(np.column_stack((np.zeros_like(ys), ys, np.full_like(ys, z))), L) < 0).any())
    return float(c + top * fr.head_scale), float(c + chin * fr.head_scale)


def measures(fr, look):
    crown, chin = head_marks(fr, look)
    f = fr.f
    return dict(height=round(crown, 3), head=round(crown - chin, 3), heads=round(crown / (crown - chin), 2),
                shoulders=round(2 * (f['shoulder'] + f['deltoid']), 3), chest=round(2 * float(fr.torso(1.38)[0]), 3),
                waist=round(2 * float(fr.torso(1.17)[0]), 3), hips=round(2 * fr.hips(), 3),
                hand=f['hand'][0], foot=f['foot'][0], crown=round(crown, 3), chin=round(chin, 3))


def bare(a, meas):
    for form in ('m', 'f'):
        rig.stage(elev=0, res=a.res, samples=a.samples, look='portrait')
        M.set_mode(revenant=False)
        fr = B.Frame(LK.FORMS[form])
        look = LK.anchor(form)
        skin = G.skin('bodyskin', look['skin_hex'], windburn=0.3, dirt=0.45)
        wrap = G.cloth('wrap', color='#6f604c', blood=0.0, mud=0.2, grime=0.4, seed=3)
        shorts = G.cloth('shorts', color='#3d2f24', blood=0.0, mud=0.5, seed=4)
        B.bare('body', fr, look, skin, wrap, shorts)
        for view, az in VIEWS.items():
            shoot(os.path.join(a.out, f'bare_{form}_{view}.png'), az)
        meas[form] = measures(fr, look)
        print(f'[bare] {form}: {meas[form]}', flush=True)


def variants(a):
    """The guide's variation row: each anchor lean, heavy, tall and short (body.VARIATIONS), front on, one scale."""
    for form in ('m', 'f'):
        for name in ('lean', 'anchor', 'heavy', 'tall', 'short'):
            rig.stage(elev=0, res=a.res, samples=a.samples, look='portrait')
            M.set_mode(revenant=False)
            dial = 0.0 if form == 'm' else 1.0
            fr = B.Frame(B.form(dial, None if name == 'anchor' else B.VARIATIONS[name][form]))
            look = LK.anchor(form)
            skin = G.skin('bodyskin', look['skin_hex'], windburn=0.3, dirt=0.45)
            wrap = G.cloth('wrap', color='#6f604c', blood=0.0, mud=0.2, grime=0.4, seed=3)
            shorts = G.cloth('shorts', color='#3d2f24', blood=0.0, mud=0.5, seed=4)
            B.bare('body', fr, look, skin, wrap, shorts)
            shoot(os.path.join(a.out, f'var_{form}_{name}.png'), 0.0)
            print(f'[variant] {form} {name}', flush=True)


def kit(a):
    mod = importlib.import_module(a.asset)
    for form in ('m', 'f'):
        sex = LK.FORMS[form]
        rig.stage(elev=0, res=a.res, samples=a.samples, look='portrait')
        fig = mod.build({'sex': sex, 'armed': False, 'level': True})
        fig.scale = (1.0, 1.0, 1.0)                 # in metres, square to the camera, like the bare body
        fig.rotation_euler.z = 0.0
        bpy.context.view_layer.update()
        for view in ('front', 'side', 'back'):
            shoot(os.path.join(a.out, f'kit_{form}_{view}.png'), VIEWS[view])
        rig.stage(elev=45.0, res=a.res, samples=a.samples)      # the game's own camera and light
        mod.build({'sex': sex})
        rig.render(os.path.join(a.out, f'kit_{form}_game.png'))
        print(f'[kit] {form}', flush=True)


def _flat(im):
    from PIL import Image
    bg = Image.new('RGBA', im.size, BG + (255,))
    bg.alpha_composite(im)
    return bg.convert('RGB')


def sheets(a, meas):
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
    except OSError:
        font = ImageFont.load_default()
    R = a.res
    px = R / SCALE                                  # pixels per metre

    def ypix(z):                                    # a height (m) to a row of the straight views
        return (TARGET - z) * px + R / 2

    def load(name):
        return Image.open(os.path.join(a.out, name)).convert('RGBA')

    # the bare bodies, with each one's head-count scale on the front view (crown to the ground, in its own heads)
    cells = []
    for view in ('front', 'side', 'back', 'tq'):
        for form in ('m', 'f'):
            im = _flat(load(f'bare_{form}_{view}.png'))
            if view == 'front' and form in meas:
                dr = ImageDraw.Draw(im)
                m = meas[form]
                col = (96, 150, 214) if form == 'm' else (214, 96, 96)
                for k in range(0, 9):
                    z = m['crown'] - k * m['head']
                    if z < -0.01:
                        break
                    y = ypix(z)
                    dr.line((R * 0.1, y, R * 0.18, y), fill=col, width=2)
                    if k:
                        dr.text((R * 0.03, y - 18), str(k), fill=col, font=font)
                dr.text((R * 0.03, R - 26), f"{m['heads']:.1f} heads", fill=(216, 205, 184), font=font)
            cells.append(im.crop((int(R * 0.18), 0, int(R * 0.82), R)) if view != 'front' else im.crop((0, 0, int(R * 0.82), R)))
    w = sum(c.width for c in cells[:8])
    sheet = Image.new('RGB', (w, R), BG)
    x = 0
    for c in cells:
        sheet.paste(c, (x, 0))
        x += c.width
    sheet.save(os.path.join(a.out, 'bare_sheet.png'))
    # the kit, unarmed, and from the game's camera
    cells = [_flat(load(f'kit_{form}_{view}.png')).crop((int(R * 0.12), 0, int(R * 0.88), R))
             for view in ('front', 'side', 'back') for form in ('m', 'f')]
    cells += [_flat(load(f'kit_{form}_game.png')).resize((int(R * 0.76), int(R * 0.76))) for form in ('m', 'f')]
    sheet = Image.new('RGB', (sum(c.width for c in cells), R), BG)
    x = 0
    for c in cells:
        sheet.paste(c, (x, (R - c.height) // 2))
        x += c.width
    sheet.save(os.path.join(a.out, 'kit_sheet.png'))
    # silhouettes: hers filled, his outline dashed over it, feet aligned (the same camera, so they already are)
    out = []
    for prefix in ('bare', 'kit'):
        him = np.asarray(load(f'{prefix}_m_front.png'))[..., 3] > 128
        her = np.asarray(load(f'{prefix}_f_front.png'))[..., 3] > 128
        img = np.zeros((R, R, 3), np.uint8)
        img[:] = BG
        img[her] = (180, 154, 130)
        edge = him & ~(np.roll(him, 1, 0) & np.roll(him, -1, 0) & np.roll(him, 1, 1) & np.roll(him, -1, 1))
        ys, xs = np.nonzero(edge)
        keep = ((ys // 4 + xs // 4) % 2) == 0          # dashed
        pil = Image.fromarray(img)
        dr = ImageDraw.Draw(pil)
        for yy, xx in zip(ys[keep], xs[keep]):
            dr.rectangle((xx - 1, yy - 1, xx + 1, yy + 1), fill=(96, 150, 214))
        out.append(pil.crop((int(R * 0.15), 0, int(R * 0.85), R)))
    sheet = Image.new('RGB', (sum(c.width for c in out), R), BG)
    x = 0
    for c in out:
        sheet.paste(c, (x, 0))
        x += c.width
    sheet.save(os.path.join(a.out, 'silhouettes.png'))
    print('[sheets] done', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'renders', 'bodies'))
    ap.add_argument('--res', type=int, default=640)
    ap.add_argument('--samples', type=int, default=24)
    ap.add_argument('--asset', default='fighter')
    ap.add_argument('--only', choices=['bare', 'kit', 'variants', 'sheets'])
    a = ap.parse_args()
    a.out = os.path.normpath(a.out)
    os.makedirs(a.out, exist_ok=True)
    mpath = os.path.join(a.out, 'measures.json')
    meas = json.load(open(mpath)) if os.path.exists(mpath) else {}
    if a.only in (None, 'bare'):
        bare(a, meas)
        json.dump(meas, open(mpath, 'w'), indent=1)
    if a.only in (None, 'kit'):
        kit(a)
    if a.only == 'variants':
        variants(a)
        return
    sheets(a, meas)


if __name__ == '__main__':
    main()
