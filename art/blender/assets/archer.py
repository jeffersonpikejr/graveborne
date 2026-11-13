"""BRIGAND ARCHER. Wave 2, asset #14 (step 2 of the enemy plan, the brigand pass): the Warband's bow, armed with the
game's own Hunting Bow.

Brief (in the Line-Breaker's register): the one who shoots first from the treeline. A short ochre cowl, the hood worn
low and a cape to the shoulders, and no cloak (the Ranger's falls to the calves); a raw-leather jerkin laced over a
mustard shirt, a bracer on the bow arm, a quiver at the hip; breeches, calf wraps, turnshoes. A short hunting bow with
recurved tips at half-draw: the bow arm out to the left, the stave canted, the string drawn back to the chest, an arrow
nocked. At 26 px an Archer is the ochre cowl and a bow held out and drawn, where the Ranger's rests upright.

Built on the brigand kit (brigand.py) and the company's hood (garb.hood: the head fits its hair under it). Both forms,
two looks each; no tier looks (its upgrade, a war bow, carries no tag).
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

VARIANTS = {}
for _f, _sex in (('m', 'male'), ('f', 'female')):
    for _n in (1, 2):
        VARIANTS[f'foe_archer_{_n}_{_f}'] = dict(sex=_sex, n=_n)

CANT = (0.34, -0.12, 0.93)      # the stave's lean: out to the left and a little toward the camera


def pose(sex):
    """The half-draw: the feet apart, the bow arm out to the left at the shoulder's height, its fist round the grip; the
    draw hand back before the chest, the elbow up and out."""
    fr = BD.Frame(sex)
    fr.sex = sex
    hf = fr.hf
    fr.hunch(bend=5.0, pivot=1.0, drop=0.025 * hf, stride=0.15 * hf, spread=0.08)
    J = fr.joints
    sh_l, sh_r = J['sh_l'], J['sh_r']
    up = np.array(CANT, np.float32) / np.linalg.norm(CANT)
    bow = np.array((sh_l[0] + 0.42, sh_l[1] - 0.26 * hf, sh_l[2] - 0.03), np.float32)
    draw = bow + np.array((-0.45, 0.07, -0.03), np.float32)
    fr.reach('l', bow, pole=(0.1, 0.6, -1.0), grip=up)
    fr.reach('r', draw, pole=(-1.0, 0.4, 0.15), grip=np.array((0.05, 0.1, 1.0), np.float32))
    fr.bow_up = up
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
    seed = seed + 29 * n + (5 if form == 'f' else 0)
    if look is None:
        look = BR.look_for(form, 20 + n)
    mt = BR.materials()
    skin = G.skin(f'arch_skin_{look["id"]}', look['skin_hex'], windburn=look['windburn'], dirt=look['dirt'])
    cowl = G.cloth(f'archer_cowl{n}', color=(BR.PAL['ochre'], '#6b5530')[n - 1], blood=0.2, mud=0.8, grime=0.8,
                   seed=seed + 1)       # the second look's cowl a darker ochre, so a pod isn't four of one hood
    jerk = G.leather('archer_jerkin', color=BR.PAL['raw'], scuff_c='#a07d56', blood=0.25, mud=1.2, seed=seed + 2)
    quiv = G.leather('archer_quiver', color='#5e4630', seed=seed + 3)
    bowwood = G.wood('hunting_bow', color='#5a3a22', seed=seed + 4)
    horn = G.wood('bow_horn', color='#8f8671', seed=46)
    string = G.flat('bowstring', '#b3a88c')
    shaft = G.wood('shaft', color='#86704f', seed=47)
    point = G.steel('arrowhead', color='#3a3b3e', rust=0.6, blood=0.3, seed=52, edge=0.6)
    grey = G.cloth('fletch', color='#8d897e', blood=0.0, mud=0.0, grime=0.2, seed=53)
    ochf = G.cloth('fletch_ochre', color=BR.PAL['ochre'], blood=0.0, mud=0.0, grime=0.2, seed=54)
    fig = K.root('figure')
    parts = [D.skin('arch_body', skin)]

    # ---------------------------------------------------------------- clothes
    BR.lower(D, fr, mt, parts)
    parts.append(D.layer('shirt', mt['shirt'], lambda P: np.full(len(P), 0.0045, np.float32),
                         lambda P: np.maximum(BR.band(fr, D, 0.88, 1.545)(P), -D.hands(cuff=0.02)(P)), inner=0.003,
                         tris=11000, smooth=45))

    def jerkin_region(P):
        r = np.maximum(BR.band(fr, D, 0.9, 1.5)(P), D.trunk(0.004)(P))
        lace = np.maximum(np.abs(P[:, 0]) - 0.011, np.maximum(P[:, 1], 1.22 * hf - P[:, 2]))    # laced at the front
        return np.maximum(r, -lace)
    parts.append(D.layer('jerkin', jerk, lambda P: np.full(len(P), 0.0165, np.float32), jerkin_region, inner=-0.0095,
                         feather=0.002, floor=0.9, tris=9000, smooth=40))
    parts.append(D.layer('bracer', mt['raw'], lambda P: np.full(len(P), 0.013, np.float32),
                         D.forearm('l', 0.4, 0.95, radius=0.09), inner=-0.005, feather=0.0015, floor=0.95, tris=3000,
                         smooth=35))
    zb = 1.04 * hf - fr.spine[2]
    BR.belt(D, fr, zb, mt['raw'], mt['iron'], parts)
    kp, kn = D.on(-54.0, zb, 0.03)
    parts += GB.long_knife('knife', kp + kn * 0.012 + Vector((0.0, 0.0, 0.012)), (0.12, -0.22, -1.0), mt['raw'],
                           mt['wood'], mt['blade'], mt['iron'])

    # ---------------------------------------------------------------- the cowl: the hood worn low, a cape to the shoulders
    ztop = 1.58 * hf - fr.spine[2]
    oy = float(fr.from_upper(np.array((0.0, 0.02, 1.53 * hf), np.float32))[1])
    # a short cape, so its hem is torn only shallowly (deeper, it would fold back over the row above); the bow arm
    # comes out from under it
    cape = GB.Drape(D, ztop, 1.37 * hf, [a * 5.0 for a in range(72)], 0.042, rows=10, oy=oy,
                    collar=(0.1 * fr.head_scale + 0.012, 0.5), flare=0.03, folds=0.012, fold_n=9, ragged=0.01,
                    seed=seed, closed=True, arms=False,
                    hem=lambda a: 0.04 * hf * max(0.0, -math.sin(math.radians(a))) ** 1.5)     # shorter in front
    parts.append(cape.mesh('cowl_cape', cowl, thick=0.006))
    z_bot = (Vector(H.inverted() @ Vector((0.0, oy + 0.02, ztop))).z) - 0.03
    parts.append(GB.hood('hood', H, z_bot, cowl, seed=seed))

    # ---------------------------------------------------------------- the quiver at the right hip
    B = D.on(200.0, 0.64 * hf, 0.07)[0] + Vector((0.0, 0.03, 0.0))
    T = D.on(190.0, 1.05 * hf, 0.08)[0] + Vector((0.0, -0.02, 0.0))
    parts += GB.quiver('quiver', B, T, quiv, mt['raw'], grey, ochf, shaft, point, n=9, r_top=0.045, r_bot=0.034,
                       seed=seed)

    # ---------------------------------------------------------------- the bow at half-draw, an arrow on the string
    grip = Vector(fr.fist('l'))
    hand = Vector(fr.fist('r'))
    up = Vector(fr.bow_up)
    nock = hand + (grip - hand).normalized() * 0.03
    side = (nock - grip)
    side = (side - up * side.dot(up)).normalized()
    bp_, _, _ = GB.longbow('bow', grip, up, side, 1.25 * hf, bowwood, mt['raw'], horn, string, brace=0.13,
                           recurve=0.045, draw=nock)
    parts += bp_
    rest = grip - side * 0.012 + up.cross(side).normalized() * 0.018        # the arrow rests on the bow hand
    parts += GB.arrow('arrow', nock, (rest - nock).normalized(), grey, ochf, shaft, point, length=0.72)

    # ---------------------------------------------------------------- the head under the hood
    if head:
        hroot, _ = LK.build_head(look, tag=f'arch_{look["id"]}', hood=True)
        hroot.matrix_world = H
        parts.append(hroot)

    K.parent(parts, fig)
    fig.scale = (FIG_SCALE,) * 3
    fig.rotation_euler.z = math.radians(turn)
    return fig
