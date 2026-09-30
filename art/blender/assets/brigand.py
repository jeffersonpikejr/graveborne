"""BRIGAND. Wave 2, asset #10 (step 2 of the enemy plan, the brigand pass): the road's own, two to every Warband.

Brief (in the Line-Breaker's register): a man or a woman the war put out on the road with a sword and no lord. A
quilted gambeson in mustard gone to rags, patched where it wore through with dun and with the slate of a Karsk tabard
somebody didn't need any more; raw-leather belt and baldric, leg wraps, turnshoes; the company's shortsword, and a round
shield of planks, painted ochre and daubed with three black strokes. An ochre rag over the nose and mouth, or pulled
down round the neck, the face under it scarred and broken-nosed. On guard: the shield across the body, the sword back
and low, the knees bent. At 26 px a Brigand is the round shield (the only one on the board) and the ochre at the face.

The brigand kit lives here and dresses the Cutthroat and the Brigand Archer too (cutthroat.py, archer.py), and later
the Hound-Rider: the palette, what's worn from the belt down, the belt, and a rag mask's knotted ends.

Variants (ASSETS.md, the brigand pass): both forms, two looks each (masked; the mask pulled down); Hardened (tier 2,
TIER_UPGRADES' tag): a dented nasal helm, mail under the gambeson; the Captain (the ♛ when a brigand leads): a trophy
standard on the back, a fur-collared cloak, the greataxe Cut Off the Head gives its Butcher.
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

FIG_SCALE = 0.6
LOOKS = 100             # the brigands' heads: looks.foe(form, LOOKS + k), rough

# the brigand palette: faded ochre and mustard rags, undyed raw leather, rusted iron, dun; looted Karsk slate
PAL = dict(ochre='#7a6134', mustard='#6c6145', dun='#655c4b', umber='#4a3f30', raw='#7a5a3a', slate='#56626b',
           black='#1d1b19', soot='#302922', fur='#4b3d2e')

VARIANTS = {}
for _f, _sex in (('m', 'male'), ('f', 'female')):
    for _n in (1, 2):
        VARIANTS[f'foe_brigand_{_n}_{_f}'] = dict(sex=_sex, n=_n)
    VARIANTS[f'foe_brigand_hardened_1_{_f}'] = dict(sex=_sex, n=1, tag='hardened')
    VARIANTS[f'foe_brigand_captain_1_{_f}'] = dict(sex=_sex, n=1, tag='captain')

SWORD_DIR = (0.16, -0.72, 0.67)         # the shortsword's point: forward and up, from a fist held low by the hip


# ------------------------------------------------------------------------------------------------ the brigand kit
def materials():
    """The brigand kit's materials (the three foes share them)."""
    return dict(
        gambeson=G.cloth('brigand_gambeson', color=PAL['mustard'], blood=0.35, mud=1.8, grime=0.85, seed=31,
                         patches=(0.11, 0.1, (PAL['dun'], PAL['slate'], '#5b4a33'))),
        shirt=G.cloth('brigand_shirt', color='#8a7a58', blood=0.25, mud=1.4, grime=0.7, seed=32),
        breeches=G.cloth('brigand_breeches', color=PAL['umber'], blood=0.15, mud=2.0, grime=0.7, seed=37),
        wraps=G.cloth('brigand_wraps', color=PAL['dun'], blood=0.05, mud=2.8, grime=0.8, seed=39),
        rag=G.cloth('ochre_rag', color=PAL['ochre'], blood=0.3, mud=0.5, grime=0.75, seed=57),
        raw=G.leather('raw_leather', color=PAL['raw'], scuff_c='#a07d56', blood=0.2, mud=1.4, seed=43),
        shoes=G.leather('turnshoes', color='#5a4230', mud=2.8, seed=12),
        iron=G.steel('brigand_iron', color='#4b4642', rust=1.25, blood=0.35, grime=0.9, seed=61, edge=0.4, dents=0.8),
        blade=G.steel('brigand_blade', color='#7d8083', rough=0.3, rust=0.55, blood=0.85, grime=0.6, seed=8,
                      dents=0.3),
        wood=G.wood('brigand_wood', color='#4a3a2a', seed=48),
    )


def lower(D, fr, mt, parts, wraps=True, shoe_top=0.1):
    """From the belt down: breeches, leg wraps up the calves, turnshoes."""
    hf = fr.hf
    parts.append(D.layer('breeches', mt['breeches'], lambda P: np.full(len(P), 0.0035, np.float32),
                         lambda P: np.maximum(D.heights(0.1, 1.0)(P), -D.arms(1.2)(P)), inner=0.002, tris=9000))
    if wraps:
        parts.append(D.layer('wraps', mt['wraps'], GB.wraps(fr),
                             lambda P: np.maximum(D.heights(0.09, 0.44)(P), -D.arms(1.2)(P)), inner=-0.0015,
                             feather=0.002, floor=0.9, tris=7000))
    parts.append(D.layer('shoes', mt['shoes'], lambda P: np.full(len(P), 0.0045, np.float32),
                         lambda P: np.maximum(D.heights(-0.02, shoe_top)(P), -D.arms(1.2)(P)), inner=-0.001,
                         tris=6000, smooth=40))
    return hf


def belt(D, fr, z, mat, buckle, parts, clear=0.02):
    """A raw-leather belt at height z (m), an iron buckle before; returns its ring (points, normals)."""
    bp, bn = D.ring(z, clear, n=56)
    parts += A.strap('belt', bp, bn, 0.04, 0.006, mat, closed=True)
    front = min(range(len(bp)), key=lambda i: bp[i].y)
    parts.append(K.rbox('buckle', (0.048, 0.012, 0.052), (bp[front].x - 0.02, bp[front].y - 0.009, z), buckle,
                        bev=0.005))
    return bp, bn


def mask_ends(name, H, knot, mat, lengths=(0.075, 0.1), r=0.0065):
    """A rag mask's two knotted ends hanging behind the head, from its knot (info['knot'], head space)."""
    k = Vector(H @ knot)
    parts = []
    for s, ln in zip((-1.0, 1.0), lengths):
        parts.append(GB.cord(name, [k, k + Vector((0.012 * s, 0.025, -0.35 * ln)), k + Vector((0.02 * s, 0.035, -ln))],
                             r, mat))
    return parts


def neck_rag(name, H, mat, seed=0):
    """The mask pulled down: the rag rolled round the neck under the jaw."""
    c = H @ Vector((0.0, 0.004, -0.165))
    ax = (H.to_3x3() @ Vector((0.0, 0.08, 1.0))).normalized()
    s = float(np.cbrt(abs(H.to_3x3().determinant())))
    ring = A.torus(name, (0.0, 0.0, 0.0), 0.066 * s, 0.017 * s, mat, sx=1.0, sy=1.12, seg=36, rseg=10, lumpy=0.22,
                   seed=seed, rz=0.014 * s, folds=0.004)
    A.place(ring, c, A.frame(ax, back=(0.0, 1.0, 0.0)))
    return ring


def look_for(form, k):
    return LK.foe(form, LOOKS + k)


def band(fr, D, z0, z1):
    """Between a height z0 of the posed figure (a hem, from the hips down) and a height z1 of the upright upper body (a
    collar, which goes with the upper body when the spine is bent), on the male anchor's scale."""
    if fr.spine is None:
        return D.heights(z0, z1)
    hf = fr.hf
    return lambda P: np.maximum(z0 * hf - P[:, 2], fr.to_upper(P)[:, 2] - z1 * hf)


# ------------------------------------------------------------------------------------------------ the Brigand
def pose(sex, tag=None):
    """On guard: the knees bent, the left foot forward; the shield fist before the body at the waist, the sword fist
    low by the right hip, its point up at the foe. The Captain holds the greataxe across his body in both hands."""
    fr = BD.Frame(sex)
    fr.sex = sex
    hf = fr.hf
    fr.hunch(bend=9.0, pivot=1.0, drop=0.035 * hf, stride=0.16 * hf, spread=0.1)
    J = fr.joints
    sh_l, sh_r = J['sh_l'], J['sh_r']
    if tag == 'captain':
        lo = np.array((sh_r[0] + 0.03, sh_r[1] - 0.2 * hf, 0.93 * hf), np.float32)
        hi = np.array((sh_l[0] - 0.09, sh_l[1] - 0.3 * hf, 1.2 * hf), np.float32)
        ax = (hi - lo) / np.linalg.norm(hi - lo)
        fr.reach('r', lo, pole=(-0.6, 0.4, -1.0), grip=ax)
        fr.reach('l', hi, pole=(0.7, 0.3, -1.0), grip=ax)
        fr.axe_axis = ax
    else:
        fr.reach('l', (sh_l[0] - 0.02, sh_l[1] - 0.33 * hf, sh_l[2] - 0.34 * hf), pole=(0.6, 0.2, -1.0),
                 grip=np.array((1.0, 0.0, 0.0), np.float32))
        fr.reach('r', (sh_r[0] - 0.02, sh_r[1] - 0.16 * hf, 0.94 * hf), pole=(-0.6, 0.5, -1.0),
                 grip=np.array(SWORD_DIR, np.float32) / np.linalg.norm(SWORD_DIR))
    return fr


def head_frame(sex, portrait=False):
    return pose(sex).head_frame(portrait)


def gambeson(D, fr, mt, parts, skirt_to=0.72, sleeve=0.55):
    """The quilted gambeson: the trunk and the sleeves to `sleeve` of the forearm, its skirt split front and back and
    flaring over the hips down to `skirt_to` (on the male anchor's scale)."""
    hf = fr.hf
    drop = fr.spine[2] if fr.spine is not None else 0.0
    J = fr.joints

    def region(P):
        r = np.maximum(band(fr, D, 0.86, 1.545)(P), -D.hands(cuff=0.03)(P))
        for s in 'lr':      # the sleeves end part-way down the forearm, raggedly
            el, wr = J['el_' + s], J['wr_' + s]
            u = (wr - el) / np.linalg.norm(wr - el)
            past = (P - el) @ u - sleeve * float(np.linalg.norm(wr - el))
            near = GB.seg_dist(P, el, wr + u * 0.1) < 0.075
            r = np.where(near & (past > 0), np.maximum(r, past), r)
        return r
    parts.append(D.layer('gambeson', mt['gambeson'], GB.quilted(fr), region, inner=0.003, tris=14000, smooth=45))
    _, tf95, tb95 = (float(x) for x in fr.torso(0.95))
    hr = fr.hips() + 0.016
    sy = ((tf95 + tb95) / 2.0 + 0.016) / hr
    oy = (tb95 - tf95) / 2.0

    def skirt_j(i, a):
        return (-0.0035 * math.exp(-(math.sin(a * 13.0) / 0.3) ** 2) + 0.005 * math.sin(a * 5.0 + i),
                0.012 * math.sin(a * 7.0 + 2.0) if i == 0 else 0.0)
    for arc in ((-82.0, 82.0), (98.0, 262.0)):
        sk = K.lathe('gambeson_skirt', [(hr + 0.034, skirt_to * hf - drop), (hr + 0.016, 0.8 * hf - drop),
                                        (hr, 0.9 * hf - drop), (hr - 0.012, 0.985 * hf - drop)],
                     mt['gambeson'], seg=24, sy=sy, loc=(0.0, oy, 0.0), arc=arc, cap_bottom=False, cap_top=False,
                     jitter=skirt_j)
        A.solid(sk, 0.009)
        K.subsurf(sk, 1)
        parts.append(sk)


def build(v, seed=7, turn=-4.0, look=None, head=True):
    """One variant (VARIANTS). look: the head's look; by default the variant's own, from the enemy pool."""
    sex = v.get('sex', 'male')
    n, tag = v.get('n', 1), v.get('tag')
    form = 'm' if sex == 'male' else 'f'
    M.set_mode(revenant=False)
    fr = pose(sex, tag)
    hf, f = fr.hf, fr.f
    D = GB.dressed(fr)
    H = fr.head_frame(v.get('portrait') or v.get('level'))
    seed = seed + 17 * n + (5 if form == 'f' else 0) + {'hardened': 3, 'captain': 7}.get(tag, 0)
    if look is None:
        look = look_for(form, {None: n, 'hardened': 3, 'captain': 4}[tag])
    mt = materials()
    skin = G.skin(f'brigand_skin_{look["id"]}', look['skin_hex'], windburn=look['windburn'], dirt=look['dirt'])
    rawhide = G.leather('rawhide', color='#8f7657', scuff_c='#b39a74', mud=0.8, seed=44)
    planks = G.planks('brigand_shield', paint=PAL['ochre'], wood='#5b4530', chip=0.3, device=(PAL['black'], 28.0),
                      seed=seed + 2)
    fig = K.root('figure')
    parts = [D.skin('brigand_body', skin)]

    # ---------------------------------------------------------------- clothes
    lower(D, fr, mt, parts)
    if tag in ('hardened', 'captain'):      # mail under the gambeson: at its hem and down the forearms
        maille = G.maille('brigand_mail', color='#48494a', rust=0.9, blood=0.25, seed=seed + 5)
        parts.append(D.layer('mail', maille, lambda P: np.full(len(P), 0.006, np.float32),
                             lambda P: np.maximum(band(fr, D, 0.62, 1.5)(P), -D.hands(cuff=0.035)(P)), inner=0.001,
                             tris=10000, smooth=40))
    gambeson(D, fr, mt, parts)
    wdef = 0.0 if sex == 'male' else 0.02
    zb = (1.03 + 1.2 * wdef) * hf - fr.spine[2]
    bp, bn = belt(D, fr, zb, mt['raw'], mt['iron'], parts)
    kp, kn = D.on(-126.0, zb, 0.03)
    parts += GB.long_knife('knife', kp + kn * 0.012 + Vector((0.0, 0.0, 0.012)), (-0.12, -0.22, -1.0), mt['raw'],
                           mt['wood'], mt['blade'], mt['iron'])
    if tag != 'captain':    # the baldric, over the right shoulder to the left hip, the sword's empty scabbard on it
        pts, nrm = [], []
        for k in range(40):
            a = 9.0 * k
            z = (1.235 + 0.2 * math.cos(math.radians(a - 180.0))) * hf - fr.spine[2]
            p, nn = D.on(a, z, 0.026, arms=False)
            pts.append(p)
            nrm.append(nn)
        parts += A.strap('baldric', pts, nrm, 0.036, 0.005, mt['raw'], mt['iron'], rivet_every=0.3, closed=True)
        sp, sn = D.on(28.0, zb - 0.03, 0.055)
        down = Vector((0.3, 0.3, -1.0)).normalized()
        sheath = K.lathe('scabbard', [(0.004, 0.44), (0.02, 0.4), (0.024, 0.08), (0.026, 0.0)], mt['raw'], seg=12,
                         sx=1.0, sy=0.4, cap_bottom=True, cap_top=True)
        A.place(sheath, sp + sn * 0.02 + down * 0.44, A.frame(-down, back=(0.0, 1.0, 0.0)))
        parts.append(sheath)
    bracer = D.forearm('r', 0.55, 0.95, radius=0.09)
    parts.append(D.layer('bracer', mt['raw'], lambda P: np.full(len(P), 0.012, np.float32), bracer, inner=-0.004,
                         feather=0.0015, floor=0.95, tris=3000, smooth=35))

    # ---------------------------------------------------------------- arms: the sword and the shield, or the greataxe
    if tag == 'captain':
        parts += K.axe('greataxe', Vector(fr.fist('r')), Vector(fr.axe_axis), (mt['iron'], mt['wood'], mt['raw']),
                       haft=1.16, head_scale=2.7)
    else:
        parts += K.sword('sword', Vector(fr.fist('r')), SWORD_DIR, (mt['blade'], mt['raw'], mt['iron']),
                         blade_len=0.36, blade_w=0.036)
        facing = Vector((0.3, -0.93, 0.2)).normalized()
        centre = Vector(fr.fist('l')) + facing * 0.045
        parts += A.round_shield('shield', centre, facing, (0.05, 0.15, 1.0), 0.29, planks, rawhide, mt['iron'],
                                mt['iron'], seed=seed)

    # ---------------------------------------------------------------- the Captain: the standard, the fur, the cloak
    if tag == 'captain':
        wool = G.cloth('captain_cloak', color='#3d3428', blood=0.25, mud=2.2, grime=0.8, seed=seed + 8)
        fur = G.hair('captain_fur', PAL['fur'], seed=seed + 9, flow='down')
        oy_sh = float(fr.joints['sh_l'][1] + fr.joints['sh_r'][1]) / 2.0 + 0.02     # round the hunched shoulders
        oy_nk = float(fr.from_upper(np.array((0.0, 0.01, 1.53 * hf), np.float32))[1])
        cloak = GB.Drape(D, 1.42 * hf, 0.42 * hf, [10.0 + 160.0 * k / 40 for k in range(41)], 0.035, rows=28,
                         oy=oy_sh, flare=0.16, folds=0.02, fold_n=7, ragged=0.05, seed=seed + 1)
        parts.append(cloak.mesh('cloak', wool, thick=0.006))
        collar = GB.Drape(D, 1.55 * hf, 1.36 * hf, [a * 5.0 for a in range(72)], 0.05, rows=10, oy=oy_nk,
                          collar=(0.1 * fr.head_scale + 0.02, 0.4), flare=0.02, folds=0.012, fold_n=16, ragged=0.02,
                          seed=seed + 2, closed=True)
        parts.append(collar.mesh('fur_collar', fur, thick=0.022))
        yb = cloak.point(90.0, 1.1 * hf, lift=0.03)[0].y
        slate = G.paint_over_steel('kettle_slate', paint=PAL['slate'], steel_color='#5a5d60', chip=0.6, seed=seed + 3)
        bone = G.cloth('bone', color='#b9ae95', blood=0.2, mud=0.3, grime=0.8, kind='bone', seed=seed + 4)
        oxblood = G.cloth('company_rag', color='#551714', blood=0.2, mud=0.4, grime=0.6, seed=seed + 5)
        cordm = G.cloth('cord', color='#2e271e', blood=0.0, mud=0.2, seed=seed + 6)
        parts += GB.trophy_standard('standard', (0.03, yb + 0.03, 0.9 * hf), (0.05, yb + 0.09, 2.28 * hf), mt['wood'],
                                    slate, bone, oxblood, cordm, seed=seed)
        rp, rn = D.ring(1.28 * hf - fr.spine[2] * 0.3, 0.03, n=48, arms=False)
        parts += A.strap('standard_strap', rp, rn, 0.03, 0.005, mt['raw'], mt['iron'], rivet_every=0.3, closed=True)

    # ---------------------------------------------------------------- the head: masked, the mask down, or helmed
    masked = tag == 'hardened' or (tag is None and n == 1)
    if head:
        hroot, info = LK.build_head(look, tag=f'brig_{look["id"]}', helm=tag == 'hardened',
                                    mask=('rag', mt['rag']) if masked else None)
        hroot.matrix_world = H
        parts.append(hroot)
        if masked:
            parts += mask_ends('rag_end', H, info['knot'], mt['rag'])
    if not masked and tag != 'captain':
        parts.append(neck_rag('neck_rag', H, mt['rag'], seed=seed))
    if tag == 'hardened':
        parts += A.nasal_helm('helm', H, mt['iron'], mt['iron'], seed=seed)

    K.parent(parts, fig)
    fig.scale = (FIG_SCALE,) * 3
    fig.rotation_euler.z = math.radians(turn)
    return fig
