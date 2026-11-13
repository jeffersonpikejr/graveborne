"""LEVY PIKEMAN. Wave 2, asset #13 (step 3 of the enemy plan, the Karsk deserters): the Shieldwall's reach.

Brief: a levy who kept the pike and little else. A quilted levy jack worn through (slate, or undyed under a slate sash),
a darker patch on its breast where the badge was torn off; a padded coif under a kettle hat; breeches, leg wraps,
turnshoes; a long knife. The pike set against a charge: its butt grounded out by the right foot, both hands on the
shaft, the point high to the left and leaning toward you. At 26 px a Pikeman is the pike, slanting corner to corner
across the sprite, the longest weapon on the board.

Built on the Karsk kit (gb/karsk.py) and the brigand kit's gambeson, legs and belt (brigand.py). Both forms, two looks.
"""
import math

import numpy as np
from mathutils import Vector

from gb import armor as A
from gb import body as BD
from gb import garb as GB
from gb import grit as G
from gb import karsk as KK
from gb import kit as K
from gb import looks as LK
from gb import mat as M

import brigand as BR
import shieldman as SM

FIG_SCALE = BR.FIG_SCALE

VARIANTS = {}
for _f, _sex in (('m', 'male'), ('f', 'female')):
    for _n in (1, 2):
        VARIANTS[f'foe_pikeman_{_n}_{_f}'] = dict(sex=_sex, n=_n)

PIKE_DIR = (0.33, -0.25, 0.91)      # up to the figure's left, leaning toward the camera
PIKE_LEN = 3.3                      # (m): what the canvas holds at that slant
BUTT_X = -0.4                       # where the butt is grounded, out by the right foot


def pose(sex):
    """The pike set: the feet wide, the left one forward, the knees bent; the right fist low on the shaft before the
    hip, the left high on it before the chest. Sets fr.pike = (butt, direction)."""
    fr = BD.Frame(sex)
    fr.sex = sex
    hf = fr.hf
    fr.hunch(bend=7.0, pivot=1.0, drop=0.04 * hf, stride=0.2 * hf, spread=0.3)
    d = np.array(PIKE_DIR, np.float32)
    d /= np.linalg.norm(d)
    butt = np.array((BUTT_X, 0.0, 0.0), np.float32)

    def on_shaft(z):
        return butt + d * (z / d[2])
    for side, z, pole in (('r', 0.9 * hf, (-0.7, 0.5, -0.6)), ('l', 1.36 * hf, (0.8, 0.2, -0.8))):
        target = on_shaft(z)
        wrist = target.copy()
        for _ in range(4):      # bring the fist (not the wrist) onto the shaft
            fr.reach(side, wrist, pole=pole, grip=d)
            f = fr.fist(side)
            near = butt + d * float((f - butt) @ d)
            wrist = wrist + (near - f)
    fr.pike = (butt, d)
    return fr


def head_frame(sex, portrait=False):
    return pose(sex).head_frame(portrait)


def build(v, seed=7, turn=-4.0, look=None, head=True):
    """One variant (VARIANTS). look: the head's look; by default the variant's own, from the enemy pool."""
    sex = v.get('sex', 'male')
    n = v.get('n', 1)
    form = 'm' if sex == 'male' else 'f'
    M.set_mode(revenant=False)
    fr = pose(sex)
    hf = fr.hf
    D = GB.dressed(fr)
    H = fr.head_frame(v.get('portrait') or v.get('level'))
    seed = seed + 31 * n + (5 if form == 'f' else 0)
    if look is None:
        look = BR.look_for(form, 40 + n)
    look = SM.coifed(look)
    mt = KK.materials()
    skin = G.skin(f'pike_skin_{look["id"]}', look['skin_hex'], windburn=look['windburn'], dirt=look['dirt'])
    fig = K.root('figure')
    parts = [D.skin('pike_body', skin)]
    drop = fr.spine[2]

    # ---------------------------------------------------------------- the levy jack, the badge torn from its breast
    BR.lower(D, fr, mt, parts)
    BR.gambeson(D, fr, {'gambeson': mt['jack'] if n == 1 else mt['undyed']}, parts, skirt_to=0.74, sleeve=0.85)
    parts.append(KK.decal('torn_badge', KK.on_body(D, -113.0, 1.31 * hf - drop, 15.0, 0.05 * hf, 0.0135), mt['ghost'],
                          n=20, seed=seed))
    wdef = 0.0 if sex == 'male' else 0.02
    zb = (1.03 + 1.2 * wdef) * hf - drop
    BR.belt(D, fr, zb, mt['leather'], mt['dark'], parts)
    kp, kn = D.on(-126.0, zb, 0.03)
    parts += GB.long_knife('knife', kp + kn * 0.012 + Vector((0.0, 0.0, 0.012)), (-0.12, -0.22, -1.0), mt['leather'],
                           mt['wood'], mt['blade'], mt['dark'])
    if n == 2:      # undyed, under a slate sash from the right shoulder to the left hip
        pts, nrm = [], []
        for k in range(40):
            a = 9.0 * k
            z = (1.235 + 0.2 * math.cos(math.radians(a - 180.0))) * hf - drop
            p, nn = D.on(a, z, 0.02, arms=False)
            pts.append(p)
            nrm.append(nn)
        parts += A.strap('sash', pts, nrm, 0.09, 0.006, mt['tabard'], closed=True)

    # ---------------------------------------------------------------- the padded coif and the kettle hat
    cape, z_bot = KK.mantle(D, fr, H, mt['padded'], seed=seed, z_hem=1.43, clear=0.034)
    parts.append(cape)
    parts.append(KK.coif('coif', H, z_bot, mt['padded'], seed=seed))
    parts += KK.kettle_hat('hat', H, mt['hat_iron'] if n == 1 else mt['hat_paint'], mt['dark'], seed=seed, grow=0.009,
                           bash=0.006)
    if head:
        hroot, _ = LK.build_head(look, tag=f'pike_{look["id"]}', helm=True)
        hroot.matrix_world = H
        parts.append(hroot)

    # ---------------------------------------------------------------- the pike
    butt, d = fr.pike
    parts += KK.pike('pike', Vector(butt), Vector(d), PIKE_LEN, mt['ash'], mt['blade'], shadow_to=1.9)

    K.parent(parts, fig)
    fig.scale = (FIG_SCALE,) * 3
    fig.rotation_euler.z = math.radians(turn)
    return fig
