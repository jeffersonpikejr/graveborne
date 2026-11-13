"""HOUND-RIDER. Wave 2, asset #16 (step 6 of the enemy plan): the Outriders' bow, mounted.

Brief (in the Line-Breaker's register): a brigand bowman on a great hound. The hound is the Blight-hound's rig at 1.4
of a dog's size, mangy grey-green, its eyes violet, a rag of a saddle blanket girthed over its back; the rider sits
it astride behind the withers, knees out round its barrel, in the Brigand Archer's kit (the ochre cowl worn low, a
raw-leather jerkin over a mustard shirt, breeches and calf wraps, a quiver at the hip), the hunting bow at half-draw.
At 26 px a Hound-Rider is a bowman up on a dog that runs over the edge of its tile.

Built from gb/beast.py (the hound; the seat: beast.legs and beast.Posed, the rider's legs posed astride by IK and his
clothes laid on him as on any body), the brigand kit (brigand.py) and the archer's bow. Both forms, two looks each.
The hound in corpse mode's palette, the rider among the living; no violet back-light.
"""
import math

import numpy as np
from mathutils import Vector

from gb import beast as BE
from gb import body as BD
from gb import face as F
from gb import garb as GB
from gb import grit as G
from gb import kit as K
from gb import looks as LK
from gb import mat as M

import brigand as BR

FIG_SCALE = BR.FIG_SCALE
MOUNT = 1.4             # the great hound: the hound's rig at 1.4 of a dog's size
SEAT_Y = 0.0            # where the rider sits along the hound's back (hound space)
TURN = -30.0

VARIANTS = {}
for _f, _sex in (('m', 'male'), ('f', 'female')):
    for _n in (1, 2):
        VARIANTS[f'foe_houndrider_{_n}_{_f}'] = dict(sex=_sex, n=_n)

CANT = (0.34, -0.12, 0.93)
MOUNTS = {1: dict(pose=dict(stride=(0.1, -0.07, -0.08, 0.09), head=(0.0, -0.62, 0.7), pitch=20.0, yaw=14.0, jaw=16.0,
                            tail=(0.05, 0.05), wound=0, torn=-1), hide='#6f7a5e', fur='#4f4a3c'),
          2: dict(pose=dict(stride=(-0.07, 0.1, 0.09, -0.07), head=(0.0, -0.6, 0.76), pitch=14.0, yaw=18.0, jaw=12.0,
                            tail=(-0.05, 0.08), wound=0, torn=1), hide='#687458', fur='#45413a')}


def pose(sex, half_width):
    """The seat: astride, the knees out and forward round the hound's barrel, the feet hanging at its flanks; the
    upper body as the Brigand Archer's at half-draw. Returns (frame, feet)."""
    fr = BD.Frame(sex)
    fr.sex = sex
    hf = fr.hf
    J = fr.joints
    lt = float(np.linalg.norm(J['kn_l'] - J['hp_l']))
    ls = float(np.linalg.norm(J['an_l'] - J['kn_l']))
    fr.hunch(bend=9.0, pivot=1.0, drop=0.0)
    feet = {}
    for s, side in ((1.0, 'l'), (-1.0, 'r')):
        hp = J['hp_' + side]
        an = np.array((s * (half_width + 0.07), hp[1] - 0.04, hp[2] - 0.58 * hf), np.float32)
        J['kn_' + side], J['an_' + side] = BE.ik(hp, an, lt, ls, (s * 0.9, -1.0, 0.25))
        feet[side] = (np.array((s * 0.25, -1.0, -0.4), np.float32), np.array((0.0, -0.35, 1.0), np.float32))
    sh_l, sh_r = J['sh_l'], J['sh_r']
    up = np.array(CANT, np.float32) / np.linalg.norm(CANT)
    bow = np.array((sh_l[0] + 0.42, sh_l[1] - 0.26 * hf, sh_l[2] - 0.03), np.float32)
    draw = bow + np.array((-0.45, 0.07, -0.03), np.float32)
    fr.reach('l', bow, pole=(0.1, 0.6, -1.0), grip=up)
    fr.reach('r', draw, pole=(-1.0, 0.4, 0.15), grip=np.array((0.05, 0.1, 1.0), np.float32))
    fr.bow_up = up
    return fr, feet


def build(v, seed=7, turn=TURN, look=None, head=True):
    """One variant (VARIANTS)."""
    sex = v.get('sex', 'male')
    n = v.get('n', 1)
    form = 'm' if sex == 'male' else 'f'
    seed = seed + 29 * n + (5 if form == 'f' else 0)
    fig = K.root('figure')

    # ---------------------------------------------------------------- the great hound
    md = MOUNTS[n]
    M.set_mode(revenant=True, corpse=True)
    hide = G.skin(f'mount_hide{n}', md['hide'], windburn=0.0, dirt=1.0, rot=0.6, seed=seed)
    fur = G.hair(f'mount_fur{n}', md['fur'], seed=seed + 1, flow='back')
    bone = G.cloth('mount_bone', color='#b9ae95', blood=0.25, mud=0.3, grime=0.7, kind='bone', seed=seed + 2)
    q = BE.Quad(**md['pose'])
    mparts, _ = BE.hound('mount', q, hide, fur, bone, seed=seed, spines=0.0, glow=0.9, patch=0.42)
    mount = K.root('mount')
    K.parent(mparts, mount)
    mount.scale = (MOUNT,) * 3
    mount.parent = fig
    top = q.top(SEAT_Y) * MOUNT
    half = q.side(SEAT_Y, q.top(SEAT_Y) - 0.2) * MOUNT

    # ---------------------------------------------------------------- the rider
    M.set_mode(revenant=False)
    fr, feet = pose(sex, half)
    hf = fr.hf
    J = fr.joints
    Jn = np.array(list(J.values()))
    lo, hi = Jn.min(0) - 0.27, Jn.max(0) + 0.27
    hi[2] = 1.58 * hf
    D = BE.Posed(fr, BE.figure_field(fr, feet=feet), lo, hi, grid=0.004)
    H = fr.head_frame(v.get('portrait') or v.get('level'))
    if look is None:
        look = BR.look_for(form, 30 + n)
    mt = BR.materials()
    skin = G.skin(f'rider_skin_{look["id"]}', look['skin_hex'], windburn=look['windburn'], dirt=look['dirt'])
    cowl = G.cloth(f'rider_cowl{n}', color=(BR.PAL['ochre'], '#6b5530')[n - 1], blood=0.2, mud=0.8, grime=0.8,
                   seed=seed + 1)
    jerk = G.leather('rider_jerkin', color=BR.PAL['raw'], scuff_c='#a07d56', blood=0.25, mud=1.2, seed=seed + 2)
    quiv = G.leather('rider_quiver', color='#5e4630', seed=seed + 3)
    bowwood = G.wood('hunting_bow', color='#5a3a22', seed=seed + 4)
    horn = G.wood('bow_horn', color='#8f8671', seed=46)
    string = G.flat('bowstring', '#b3a88c')
    shaft = G.wood('shaft', color='#86704f', seed=47)
    point = G.steel('arrowhead', color='#3a3b3e', rust=0.6, blood=0.3, seed=52, edge=0.6)
    grey = G.cloth('fletch', color='#8d897e', blood=0.0, mud=0.0, grime=0.2, seed=53)
    ochf = G.cloth('fletch_ochre', color=BR.PAL['ochre'], blood=0.0, mud=0.0, grime=0.2, seed=54)
    blanket = G.cloth('saddle_rag', color=BR.PAL['mustard'], blood=0.2, mud=0.6, grime=0.9, seed=seed + 6,
                      patches=(0.11, 0.2, (BR.PAL['dun'], BR.PAL['slate'])))
    parts = [D.skin('rider_body', skin)]

    def shin(t0, radius):       # down each shin from t0 of the way from the knee, the foot with it
        def region(P):
            out = None
            for s in 'lr':
                kn, an = J['kn_' + s], J['an_' + s]
                toe = feet[s][0] / np.linalg.norm(feet[s][0])
                d = np.minimum(F._cap(P, kn + (an - kn) * t0, an, radius), F._cap(P, an, an + toe * 0.2, radius))
                out = d if out is None else np.minimum(out, d)
            return out
        return region

    def foot(P):
        out = None
        for s in 'lr':
            an = J['an_' + s]
            toe = feet[s][0] / np.linalg.norm(feet[s][0])
            d = F._cap(P, an + np.array((0.0, 0.0, 0.02), np.float32), an + toe * 0.22, 0.1)
            out = d if out is None else np.minimum(out, d)
        return out

    parts.append(D.layer('breeches', mt['breeches'], lambda P: np.full(len(P), 0.0035, np.float32),
                         lambda P: np.maximum(P[:, 2] - 1.0 * hf, -D.arms(1.2)(P)), inner=0.002, tris=9000))
    parts.append(D.layer('wraps', mt['wraps'], GB.wraps(fr), lambda P: np.maximum(shin(0.22, 0.1)(P), -foot(P)),
                         inner=-0.0015, feather=0.002, floor=0.9, tris=7000))
    parts.append(D.layer('shoes', mt['shoes'], lambda P: np.full(len(P), 0.0045, np.float32), foot, inner=-0.001,
                         tris=6000, smooth=40))
    parts.append(D.layer('shirt', mt['shirt'], lambda P: np.full(len(P), 0.0045, np.float32),
                         lambda P: np.maximum(BR.band(fr, D, 0.88, 1.545)(P), -D.hands(cuff=0.02)(P)), inner=0.003,
                         tris=11000, smooth=45))

    def jerkin_region(P):
        r = np.maximum(BR.band(fr, D, 0.9, 1.5)(P), D.trunk(0.004)(P))
        lace = np.maximum(np.abs(P[:, 0]) - 0.011, np.maximum(P[:, 1], 1.22 * hf - P[:, 2]))
        return np.maximum(r, -lace)
    parts.append(D.layer('jerkin', jerk, lambda P: np.full(len(P), 0.0165, np.float32), jerkin_region, inner=-0.0095,
                         feather=0.002, floor=0.9, tris=9000, smooth=40))
    parts.append(D.layer('bracer', mt['raw'], lambda P: np.full(len(P), 0.013, np.float32),
                         D.forearm('l', 0.4, 0.95, radius=0.09), inner=-0.005, feather=0.0015, floor=0.95, tris=3000,
                         smooth=35))
    zb = 1.04 * hf
    BR.belt(D, fr, zb, mt['raw'], mt['iron'], parts)

    # the cowl: the hood worn low, a cape to the shoulders
    ztop = 1.58 * hf
    oy = float(fr.from_upper(np.array((0.0, 0.02, 1.53 * hf), np.float32))[1])
    cape = GB.Drape(D, ztop, 1.37 * hf, [a * 5.0 for a in range(72)], 0.042, rows=10, oy=oy,
                    collar=(0.1 * fr.head_scale + 0.012, 0.5), flare=0.03, folds=0.012, fold_n=9, ragged=0.01,
                    seed=seed, closed=True, arms=False,
                    hem=lambda a: 0.04 * hf * max(0.0, -math.sin(math.radians(a))) ** 1.5)
    parts.append(cape.mesh('cowl_cape', cowl, thick=0.006))
    z_bot = (Vector(H.inverted() @ Vector((0.0, oy + 0.02, ztop))).z) - 0.03
    parts.append(GB.hood('hood', H, z_bot, cowl, seed=seed))

    # the quiver at the right hip, behind the thigh
    B = D.on(160.0, 0.9 * hf, 0.07)[0] + Vector((-0.02, 0.1, -0.2))
    T = D.on(170.0, 1.08 * hf, 0.08)[0] + Vector((0.0, 0.0, 0.1))
    parts += GB.quiver('quiver', B, T, quiv, mt['raw'], grey, ochf, shaft, point, n=9, r_top=0.045, r_bot=0.034,
                       seed=seed)

    # the bow at half-draw, an arrow on the string
    grip = Vector(fr.fist('l'))
    hand = Vector(fr.fist('r'))
    up = Vector(fr.bow_up)
    nock = hand + (grip - hand).normalized() * 0.03
    side = (nock - grip)
    side = (side - up * side.dot(up)).normalized()
    bp_, _, _ = GB.longbow('bow', grip, up, side, 1.25 * hf, bowwood, mt['raw'], horn, string, brace=0.13,
                           recurve=0.045, draw=nock)
    parts += bp_
    rest = grip - side * 0.012 + up.cross(side).normalized() * 0.018
    parts += GB.arrow('arrow', nock, (rest - nock).normalized(), grey, ochf, shaft, point, length=0.72)

    if head:
        hroot, _ = LK.build_head(look, tag=f'rider_{look["id"]}', hood=True)
        hroot.matrix_world = H
        parts.append(hroot)

    rider = K.root('rider')
    K.parent(parts, rider)
    seat_z = top - 0.9 * hf + 0.035          # the seat of the breeches on the hound's back
    rider.location = (0.0, SEAT_Y * MOUNT + 0.02, seat_z)
    rider.parent = fig

    # the saddle rag: a blanket over the hound's back under the rider, girthed
    pad = K.sphere('saddle_rag', (0.0, SEAT_Y * MOUNT + 0.02, top - 0.15), 1.0, blanket,
                   scale=(half + 0.035, 0.27, 0.175), seg=28, rings=16)
    pad.parent = fig

    fig.scale = (FIG_SCALE,) * 3
    fig.location.y = 0.07       # (tiles) the pair stood a little back, so the hound's head and forepaws stay inside the canvas
    fig.rotation_euler.z = math.radians(turn)
    return fig
