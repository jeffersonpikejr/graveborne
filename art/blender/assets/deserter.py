"""DESERTER. Wave 2, asset #15 (step 3 of the enemy plan, the Karsk deserters): the furthest gone, alone on the road.

Brief: the Shieldman's slate tabard with the Crown's device cut out of it with a knife, over a stained jack; no coif,
so the face shows; a dented, rusting kettle hat, worn, or slung at the back by its strap; a war axe low in the right
hand, the weight back; a bedroll slung across the back. At 26 px a Deserter is the slate tabard, the hat's brim and
the axe.

Built on the Karsk kit (gb/karsk.py) and the brigand kit's gambeson, legs, belt and look pool (brigand.py). Both
forms, two looks each: the hat worn (1), or slung (2).
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

FIG_SCALE = BR.FIG_SCALE

VARIANTS = {}
for _f, _sex in (('m', 'male'), ('f', 'female')):
    for _n in (1, 2):
        VARIANTS[f'foe_deserter_{_n}_{_f}'] = dict(sex=_sex, n=_n)

AXE_DIR = (-0.3, -0.5, -0.81)       # held low: its head down and forward, out from the right leg


def pose(sex):
    """Wary: the left foot forward, the weight back on the right; the axe low in the right fist, the left hand out
    before the body."""
    fr = BD.Frame(sex)
    fr.sex = sex
    hf = fr.hf
    fr.hunch(bend=4.0, pivot=1.0, drop=0.03 * hf, stride=0.15 * hf, spread=0.1)
    J = fr.joints
    sh_l, sh_r = J['sh_l'], J['sh_r']
    fr.reach('r', (sh_r[0] - 0.09, sh_r[1] - 0.09 * hf, 0.93 * hf), pole=(-0.5, 0.5, -1.0),
             grip=np.array(AXE_DIR, np.float32) / np.linalg.norm(AXE_DIR))
    fr.reach('l', (sh_l[0] + 0.05, sh_l[1] - 0.24 * hf, 1.06 * hf), pole=(0.6, 0.3, -1.0))
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
    seed = seed + 37 * n + (5 if form == 'f' else 0)
    if look is None:
        look = BR.look_for(form, 50 + n)
    mt = KK.materials()
    skin = G.skin(f'dsrt_skin_{look["id"]}', look['skin_hex'], windburn=look['windburn'], dirt=look['dirt'])
    roll = G.cloth('bedroll', color='#5d5340', blood=0.1, mud=1.2, grime=0.9, seed=seed + 3)
    fig = K.root('figure')
    parts = [D.skin('dsrt_body', skin)]
    drop = fr.spine[2]

    # ---------------------------------------------------------------- the stained jack, the tabard with its hole
    BR.lower(D, fr, mt, parts)
    BR.gambeson(D, fr, {'gambeson': mt['stained']}, parts, skirt_to=0.8, sleeve=0.95)
    wdef = 0.0 if sex == 'male' else 0.02
    zb = (1.04 + 1.3 * wdef) * hf - drop
    front, back = KK.tabard(D, fr, zb, seed=seed, z_hem=0.72, clear=0.034, rows=62, step=2.0)
    parts.append(KK.drape_mesh(front, 'tabard_front', mt['tabard'], thick=0.005,
                               hole=KK.crown_hole(-90.0, 1.25 * hf - drop, 19.0, 0.06 * hf, seed=seed)))
    parts.append(back.mesh('tabard_back', mt['tabard'], thick=0.005))
    BR.belt(D, fr, zb, mt['leather'], mt['dark'], parts, clear=0.04)
    parts.append(BR.neck_rag('collar', H, mt['stained'], seed=seed))

    # ---------------------------------------------------------------- the bedroll across the back, on its strap
    pts, nrm = [], []
    for k in range(40):
        a = 9.0 * k
        z = min(1.25 + 0.24 * math.cos(math.radians(a - 210.0)), 1.42) * hf - drop     # clear of the hole
        p, nn = D.on(a, z, 0.042, arms=False)
        pts.append(p)
        nrm.append(nn)
    parts += A.strap('roll_strap', pts, nrm, 0.04, 0.005, mt['leather'], mt['dark'], rivet_every=0.3, closed=True)
    lo, hi = pts[4] + nrm[4] * 0.075, pts[16] + nrm[16] * 0.075
    lo, hi = lo + (lo - hi).normalized() * 0.06, hi + (hi - lo).normalized() * 0.06
    parts.append(K.tube('bedroll', lo, hi, 0.072, 0.072, roll, seg=16))
    ax = (hi - lo).normalized()
    for t in (0.22, 0.78):
        tie = A.torus('roll_tie', (0.0, 0.0, 0.0), 0.074, 0.006, mt['leather'], seg=20, rseg=6)
        A.place(tie, lo + (hi - lo) * t, A.frame(ax))
        parts.append(tie)

    # ---------------------------------------------------------------- the kettle hat: worn, or slung at the back
    if n == 1:
        parts += KK.kettle_hat('hat', H, mt['hat_rust'], mt['dark'], seed=seed, bash=0.012)
    else:
        at = Vector(H @ Vector((0.0, 0.2, -0.12)))       # pushed back off the head, hanging behind the neck
        Hs = KK.slung_frame(at, crown=(0.12, 0.6, 0.8))
        parts += KK.kettle_hat('hat', Hs, mt['hat_rust'], mt['dark'], seed=seed, bash=0.012)
        throat = Vector(H @ Vector((0.0, -0.05, -0.17)))
        parts.append(GB.cord('hat_strap', [at + Vector((0.09, -0.06, 0.02)), throat, at + Vector((-0.09, -0.06, 0.02))],
                             0.005, mt['leather']))
    if head:
        hroot, _ = LK.build_head(look, tag=f'dsrt_{look["id"]}', helm=n == 1)
        hroot.matrix_world = H
        parts.append(hroot)

    # ---------------------------------------------------------------- the war axe, low
    parts += K.axe('axe', Vector(fr.fist('r')), AXE_DIR, (mt['blade'], mt['wood'], mt['leather']), haft=0.66,
                   head_scale=1.9)

    K.parent(parts, fig)
    fig.scale = (FIG_SCALE,) * 3
    fig.rotation_euler.z = math.radians(turn)
    return fig
