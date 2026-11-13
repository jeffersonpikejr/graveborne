"""CUTTHROAT. Wave 2, asset #7 (step 2 of the enemy plan, the brigand pass): the Warband's knife, fast (speed 6), and
the one that comes round the flank.

Brief (in the Line-Breaker's register): the brigand who doesn't stand in the line. Low in a crouch, the weight forward,
the head up and the eyes on you; two long knives held reversed along the forearms. A black wrap over the nose and mouth,
bound round the head, its tail trailing a forearm's length behind; a close soot-dark jerkin over a shirt with its sleeves
pushed up, the forearms bound in linen; dark breeches, calf wraps, soft boots. At 26 px a Cutthroat is the lowest
living silhouette on the board, dark, with a black wrap and a tail behind it, and two glints of steel before it; beside
the Husk's pale slump it is coiled, not slumped.

Built on the brigand kit (brigand.py): its palette, what's worn from the belt down, the belt. The game arms it with a
shortsword; it is drawn as the pair of long knives it fights with. Both forms, two looks each (black or soot-brown
wraps); no tier looks (its upgrades, a better blade and more speed, carry no tag).
"""
import math

import numpy as np
from mathutils import Matrix, Vector

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
        VARIANTS[f'foe_cutthroat_{_n}_{_f}'] = dict(sex=_sex, n=_n)

LIFT = -20.0                        # degrees the head is raised against the crouch, about the base of its neck
LIFT_AT = (0.0, 0.03, -0.17)        # (head space)
WRAPS = {1: BR.PAL['black'], 2: '#2e2620'}      # the face-wrap: black, or soot-brown


def _reversed(fr, side, target, pole):
    """Reach a fist to target with the knife held reversed: the grip turned so the blade lies back along the forearm,
    a little out from it."""
    fr.reach(side, target, pole=pole)
    J = fr.joints
    back = J['el_' + side] - J['wr_' + side]
    back = back / np.linalg.norm(back)
    out = np.array((1.0 if side == 'l' else -1.0, -0.3, -0.35), np.float32)
    d = back + 0.35 * (out - back * float(out @ back))
    d = (d / np.linalg.norm(d)).astype(np.float32)
    fr.reach(side, target, pole=pole, grip=d)
    return d


def pose(sex):
    """The crouch: hips sunk, knees deep, the feet wide and the left one forward, the back bent over them; both fists
    forward and low, the knives reversed; the head raised against the bend."""
    fr = BD.Frame(sex)
    fr.sex = sex
    hf = fr.hf
    fr.hunch(bend=24.0, pivot=1.0, drop=0.13 * hf, stride=0.2 * hf, spread=0.18)
    J = fr.joints
    sh_l, sh_r = J['sh_l'], J['sh_r']
    fr.knives = {'l': _reversed(fr, 'l', (sh_l[0] + 0.05, sh_l[1] - 0.3 * hf, 0.86 * hf), (0.7, 0.3, -1.0)),
                 'r': _reversed(fr, 'r', (sh_r[0] - 0.03, sh_r[1] - 0.2 * hf, 0.76 * hf), (-0.7, 0.4, -1.0))}
    return fr


def _lift(H):
    return (H @ Matrix.Translation(Vector(LIFT_AT)) @ Matrix.Rotation(math.radians(LIFT), 4, 'X')
            @ Matrix.Translation(-Vector(LIFT_AT)))


def head_frame(sex, portrait=False):
    return _lift(pose(sex).head_frame(portrait))


def _arm_wraps(fr):
    """Linen bound round each forearm from the wrist to near the elbow, overlapping itself (Dressed.layer t)."""
    J = fr.joints

    def t(P):
        out = np.zeros(len(P), np.float32)
        best = np.full(len(P), np.inf, np.float32)
        for s in 'lr':
            el, wr = J['el_' + s], J['wr_' + s]
            u = (el - wr) / np.linalg.norm(el - wr)
            q = P - wr
            along = q @ u
            dist = GB.seg_dist(P, wr, el)
            ax = wr + along[:, None] * u
            o = np.cross(u, (0.0, 0.0, 1.0))
            o = o / np.linalg.norm(o)
            th = np.arctan2((P - ax) @ np.cross(u, o), (P - ax) @ o)
            band = 0.5 + 0.5 * np.cos(along / 0.03 * 2.0 * np.pi + th)
            sel = dist < best
            out = np.where(sel, 0.0045 + 0.002 * band, out)
            best = np.minimum(best, dist)
        return out
    return t


def build(v, seed=7, turn=-4.0, look=None, head=True):
    """One variant (VARIANTS). look: the head's look; by default the variant's own, from the enemy pool."""
    sex = v.get('sex', 'male')
    n = v.get('n', 1)
    form = 'm' if sex == 'male' else 'f'
    M.set_mode(revenant=False)
    fr = pose(sex)
    hf = fr.hf
    D = GB.dressed(fr)
    H = _lift(fr.head_frame(v.get('portrait') or v.get('level')))
    seed = seed + 23 * n + (5 if form == 'f' else 0)
    if look is None:
        look = BR.look_for(form, 10 + n)
    mt = BR.materials()
    skin = G.skin(f'cut_skin_{look["id"]}', look['skin_hex'], windburn=look['windburn'], dirt=look['dirt'])
    wrap = G.cloth(f'cut_wrap{n}', color=WRAPS[n], blood=0.25, mud=0.3, grime=0.5, seed=seed + 1)
    jerkin = G.leather('cut_jerkin', color='#2c2520', scuff_c='#5a4a3a', blood=0.3, mud=1.2, seed=seed + 2)
    shirt = G.cloth('cut_shirt', color='#3d3328', blood=0.3, mud=1.2, grime=0.8, seed=seed + 3)
    linen = G.cloth('cut_linen', color='#7a6f58', blood=0.45, mud=0.6, grime=0.8, seed=seed + 4)
    boots = G.leather('cut_boots', color='#241c16', mud=2.6, seed=seed + 5)
    grips = G.leather('cut_grips', color='#1f1813', seed=seed + 6)
    mt['breeches'] = G.cloth('cut_breeches', color='#2e2a24', blood=0.15, mud=2.2, grime=0.7, seed=seed + 7)
    mt['wraps'] = G.cloth('cut_legwraps', color='#4a4336', blood=0.05, mud=2.8, grime=0.8, seed=seed + 8)
    mt['shoes'] = boots
    fig = K.root('figure')
    parts = [D.skin('cut_body', skin)]

    # ---------------------------------------------------------------- clothes
    BR.lower(D, fr, mt, parts, shoe_top=0.24)
    J = fr.joints

    def shirt_region(P):         # sleeves pushed up above the elbows
        r = np.maximum(BR.band(fr, D, 0.9, 1.54)(P), -D.hands(cuff=0.03)(P))
        for s in 'lr':
            sh, el = J['sh_' + s], J['el_' + s]
            u = (el - sh) / np.linalg.norm(el - sh)
            past = (P - sh) @ u - 0.88 * float(np.linalg.norm(el - sh))
            near = GB.seg_dist(P, sh, J['wr_' + s]) < 0.08
            r = np.where(near & (past > 0), np.maximum(r, past), r)
        return r
    parts.append(D.layer('shirt', shirt, lambda P: np.full(len(P), 0.0045, np.float32), shirt_region, inner=0.003,
                         tris=10000, smooth=45))
    parts.append(D.layer('jerkin', jerkin, lambda P: np.full(len(P), 0.013, np.float32),
                         lambda P: np.maximum(BR.band(fr, D, 0.88, 1.5)(P), D.trunk(0.004)(P)), inner=-0.006,
                         feather=0.002, floor=0.9, tris=9000, smooth=40))
    parts.append(D.layer('arm_wraps', linen, _arm_wraps(fr),
                         lambda P: np.maximum(np.minimum(D.forearm('l', 0.12, 0.98, 0.085)(P),
                                                         D.forearm('r', 0.12, 0.98, 0.085)(P)),
                                              D.hands(cuff=0.004)(P) * -1.0), inner=-0.001, feather=0.0015,
                         floor=0.9, tris=5000, smooth=40))
    zb = 1.02 * hf - fr.spine[2]
    BR.belt(D, fr, zb, mt['raw'], mt['iron'], parts)
    for a, dn in ((-60.0, (0.15, -0.3, -1.0)), (230.0, (-0.1, 0.35, -1.0))):      # the knives' empty sheaths
        sp, sn = D.on(a, zb, 0.03)
        sheath = K.lathe('sheath', [(0.004, 0.3), (0.017, 0.26), (0.021, 0.05), (0.02, 0.0)], jerkin, seg=12, sx=1.0,
                         sy=0.42, cap_bottom=True, cap_top=True)
        d = Vector(dn).normalized()
        A.place(sheath, sp + sn * 0.016 + d * 0.3, A.frame(-d, back=(0.0, 1.0, 0.0)))
        parts.append(sheath)

    # ---------------------------------------------------------------- the knives, reversed
    for s in 'lr':
        parts += K.sword('knife_' + s, Vector(fr.fist(s)), Vector(fr.knives[s]), (mt['blade'], grips, mt['iron']),
                         blade_len=0.27, blade_w=0.03, grip=0.1)

    # ---------------------------------------------------------------- the head in its wrap, the tail behind
    if head:
        hroot, info = LK.build_head(look, tag=f'cut_{look["id"]}', mask=('wrap', wrap))
        hroot.matrix_world = H
        parts.append(hroot)
        k = Vector(H @ info['knot'])
        back = Vector((0.0, 1.0, 0.0))
        up, side = Vector((0.0, 0.0, 1.0)), Vector((1.0, 0.0, 0.0))
        # streaming behind and out past the right shoulder, where the battle camera sees it (straight back, it
        # would stand over the head like a plume)
        tail = [k + back * b + up * u - side * s for b, u, s in ((0.0, 0.0, 0.0), (0.06, -0.01, 0.03),
                (0.12, -0.04, 0.08), (0.17, -0.09, 0.14), (0.2, -0.16, 0.19), (0.21, -0.24, 0.22))]
        parts.append(GB.ribbon('wrap_tail', tail, 0.05, wrap, twist=60.0, taper=0.45))
        parts += BR.mask_ends('wrap_end', H, info['knot'], wrap, lengths=(0.06,), r=0.006)

    K.parent(parts, fig)
    fig.scale = (FIG_SCALE,) * 3
    fig.rotation_euler.z = math.radians(turn)
    return fig
