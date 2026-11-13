"""VILLAGER. The Protect objective's charge: an unarmed peasant, to be kept alive.

Brief: nobody's soldier. A plain smock to the knee, undyed linen or brown wool, belted with a rope; hose and turnshoes;
no weapon, no iron, no livery. The hands empty and hanging open before the hips (1), or clutching a bundle of what could be carried
to the chest (2). Stooped a little, the feet together: someone who would rather be anywhere else. At 26 px a Villager
is a pale, unarmed figure with nothing in its hands or a bundle in its arms.

Built on the company's body and garment layers (gb/body.py, gb/garb.py) and the brigand kit's legs (brigand.py). Both
forms, two looks each; the heads come from the enemy look pool's far end, dealt as rolled (never a soldier's face).
"""
import math

import numpy as np
from mathutils import Vector

from gb import armor as A
from gb import body as BD
from gb import garb as GB
from gb import grit as G
from gb import kit as K
from gb import looks as LK
from gb import mat as M

import brigand as BR

FIG_SCALE = BR.FIG_SCALE
LOOKS = 300                         # looks.foe(form, LOOKS + n, rough=False)

VARIANTS = {}
for _f, _sex in (('m', 'male'), ('f', 'female')):
    for _n in (1, 2):
        VARIANTS[f'prop_villager_{_n}_{_f}'] = dict(sex=_sex, n=_n)

SMOCK = {1: '#857a63', 2: '#6b5843'}        # undyed linen; brown wool


def pose(sex, n=1):
    """Stooped, the feet near together. 1: the empty hands hanging a little before the hips. 2: both arms round a bundle
    held to the chest (fr.bundle: its centre)."""
    fr = BD.Frame(sex)
    fr.sex = sex
    hf = fr.hf
    fr.hunch(bend=9.0, pivot=1.0, drop=0.025 * hf, stride=0.07 * hf, spread=0.03)
    J = fr.joints
    sh_l, sh_r = J['sh_l'], J['sh_r']
    if n == 2:
        c = np.array((0.0, 0.5 * (sh_l[1] + sh_r[1]) - 0.2 * hf, 1.2 * hf), np.float32)
        fr.reach('l', c + np.array((0.1, -0.1, -0.03), np.float32), pole=(0.9, 0.2, -0.7))
        fr.reach('r', c + np.array((-0.09, -0.11, -0.08), np.float32), pole=(-0.9, 0.2, -0.7))
        fr.bundle = c
    else:
        fr.reach('l', (sh_l[0] + 0.045, sh_l[1] - 0.13 * hf, 0.97 * hf), pole=(0.5, 0.5, -1.0))
        fr.reach('r', (sh_r[0] - 0.04, sh_r[1] - 0.1 * hf, 0.95 * hf), pole=(-0.5, 0.5, -1.0))
    return fr


def head_frame(sex, portrait=False):
    return pose(sex).head_frame(portrait)


def build(v, seed=7, turn=-4.0, look=None, head=True):
    """One variant (VARIANTS). look: the head's look; by default the variant's own."""
    sex = v.get('sex', 'male')
    n = v.get('n', 1)
    form = 'm' if sex == 'male' else 'f'
    M.set_mode(revenant=False)
    fr = pose(sex, n)
    hf = fr.hf
    D = GB.dressed(fr)
    H = fr.head_frame(v.get('portrait') or v.get('level'))
    seed = seed + 41 * n + (5 if form == 'f' else 0)
    if look is None:
        look = LK.foe(form, LOOKS + n, rough=False)
    skin = G.skin(f'vill_skin_{look["id"]}', look['skin_hex'], windburn=look['windburn'], dirt=look['dirt'])
    smock = G.cloth(f'vill_smock{n}', color=SMOCK[n], blood=0.1, mud=1.8, grime=0.8, seed=seed + 1,
                    patches=(0.13, 0.07, ('#7d705a', '#5e5444')))
    mt = dict(breeches=G.cloth('vill_hose', color='#4a4034', blood=0.05, mud=2.0, grime=0.7, seed=93),
              wraps=G.cloth('vill_wraps', color='#6b6250', blood=0.0, mud=2.6, grime=0.8, seed=94),
              shoes=G.leather('vill_shoes', color='#4a3828', mud=2.8, seed=95))
    rope = G.cloth('vill_rope', color='#7a6d55', blood=0.0, mud=0.8, grime=0.5, seed=96)
    sack = G.cloth('vill_sack', color='#8a7d62', blood=0.0, mud=1.0, grime=0.9, seed=97,
                   patches=(0.09, 0.1, ('#6b5f49',)))
    fig = K.root('figure')
    parts = [D.skin('vill_body', skin)]
    drop = fr.spine[2]

    # ---------------------------------------------------------------- hose, shoes, the smock and its rope
    BR.lower(D, fr, mt, parts, wraps=n == 2)
    parts.append(D.layer('smock', smock, lambda P: np.full(len(P), 0.009, np.float32),
                         lambda P: np.maximum(BR.band(fr, D, 0.86, 1.54)(P), -D.hands(cuff=0.02)(P)), inner=0.003,
                         tris=13000, smooth=45))
    _, tf95, tb95 = (float(x) for x in fr.torso(0.95))
    hr = fr.hips() + 0.014
    sy = (max(tf95, tb95) + 0.03) / hr       # deep enough before for the forward thigh
    oy = (tb95 - tf95) / 2.0

    def hem(i, a):
        return (0.006 * math.sin(a * 6.0 + i + seed),
                (0.014 * math.sin(a * 7.0 + 1.1 + seed) + 0.006 * math.sin(a * 19.0)) if i == 0 else 0.0)
    sk = K.lathe('smock_skirt', [(hr + 0.065, 0.55 * hf - drop), (hr + 0.04, 0.72 * hf - drop),
                                 (hr + 0.008, 0.9 * hf - drop), (hr - 0.012, 1.0 * hf - drop)], smock, seg=40, sy=sy,
                 loc=(0.0, oy - 0.01, 0.0), cap_bottom=False, cap_top=False, jitter=hem)
    A.solid(sk, 0.007)
    K.subsurf(sk, 1)
    parts.append(sk)
    wdef = 0.0 if sex == 'male' else 0.02
    zb = (1.03 + 1.3 * wdef) * hf - drop
    rp, rn = D.ring(zb, 0.017, n=60)
    parts.append(GB.cord('rope', rp, 0.0095, rope, closed=True))
    front = min(range(len(rp)), key=lambda i: rp[i].y + 0.3 * abs(rp[i].x - 0.06))
    knot = rp[front] + rn[front] * 0.008
    parts.append(K.sphere('rope_knot', tuple(knot), 0.018, rope, scale=(1.2, 0.8, 1.0), seg=10, rings=6))
    for dx, ln in ((-0.012, 0.2), (0.014, 0.15)):
        parts.append(GB.cord('rope_end', [knot + Vector((dx, -0.004, 0.0)), knot + Vector((dx * 1.5, -0.016, -0.5 * ln)),
                                          knot + Vector((dx * 2.0, -0.02, -ln))], 0.008, rope))

    # ---------------------------------------------------------------- the bundle
    if n == 2:
        c = Vector(fr.bundle)
        parts.append(K.sphere('bundle', tuple(c), 0.125, sack, scale=(1.15, 0.8, 0.95), seg=18, rings=12))
        parts.append(K.sphere('bundle_knot', tuple(c + Vector((0.02, -0.04, 0.115))), 0.03, sack, scale=(1.2, 0.9, 0.8),
                              seg=10, rings=6))
        for s in (-1.0, 1.0):
            parts.append(GB.cord('bundle_ear', [c + Vector((0.02, -0.04, 0.12)), c + Vector((0.02 + 0.05 * s, -0.06, 0.16)),
                                                c + Vector((0.02 + 0.08 * s, -0.07, 0.13))], 0.009, sack))

    if head:
        hroot, _ = LK.build_head(look, tag=f'vill_{look["id"]}')
        hroot.matrix_world = H
        parts.append(hroot)

    K.parent(parts, fig)
    fig.scale = (FIG_SCALE,) * 3
    fig.rotation_euler.z = math.radians(turn)
    return fig
