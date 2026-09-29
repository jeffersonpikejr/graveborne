"""ASH ACOLYTE — the Grafted. Asset #4: "reads the Blight and answers it. Every rank of it a bill that comes due."

Brief (in the Line-Breaker's register): a runaway from the Conclave's grafting cells (a failed apprentice, a seminary
novice, the one survivor of a cohort) who carries the Blight in one arm and spends it for the company. A hooded robe of
undyed wool gone charcoal with soot, ash settled pale on the shoulders and the crown of the hood, the hem burnt ragged
and heavy with mud; a mantle over the shoulders, the hood up but pulled back off the brow, so the face and the hair
show and every soldier stays their own; an oxblood sash (the company's colour) knotted at the hip. The left sleeve is
cut away from the graft: the arm bare from above the elbow, the flesh gone ash-grey and bruised violet and split by
veins of violet light from the palm up, a broken Conclave manacle still locked on the wrist, its chain hanging. Over the
open palm floats the ashfire: a white heart in a knot of violet flame, embers and flakes of ash turning round it, its
light on the arm, the robe and the face. A shortsword held low in the right hand, the way the Fighter holds his blade;
a scroll case at the hip; soft boots. At 26 px an Acolyte is the dark hood and robe and the violet point of the
ashfire at the hand.

Commander (any class; here on the Acolyte): the banner strapped to the back, one mark of rank (a tarnished gilt morse
clasping the mantle), the founding scar, fewer loose pieces (the scroll case stays behind). Veteran (level 5): dead
men's gear (a blackened spaulder on the sword arm, a patched robe), and the graft has taken more: bone barbs have
broken through the forearm (the Serrated Graft). Revenant: the same kit drained to grave-grey, violet light in the
cracks and the eyes, and the ashfire burning colder.
Weapons: the shortsword, or (half of them) a spear held upright.

Everything is laid on the wearer's body (gb/garb.py): the robe's body and sleeves are a layer over the posed body, its
skirt is draped from the sash and hangs afresh below it (his from the hips, hers from her natural waist over her hips),
and the mantle and hood are the Ranger's cut, so the heads' hair fits under the hood the same way.
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

FIG_SCALE = 0.6

VARIANTS = {}
for _w in ('', '_spear'):
    for _t, _v in (('', {}), ('_commander', {'commander': True}), ('_veteran', {'veteran': True}),
                   ('_revenant', {'revenant': True}), ('_commander_revenant', {'commander': True, 'revenant': True})):
        for _f, _sex in (('m', 'male'), ('f', 'female')):
            VARIANTS[f'acolyte{_w}{_t}_{_f}'] = dict(_v, sex=_sex, **({'weapon': 'spear'} if _w else {}))

SWORD_DIR = (-0.2, -0.32, -0.93)        # held low, point down and a little forward
SLEEVE_CUT = 0.42                       # the left sleeve is cut away this far down the upper arm
_LAST = {}                              # sex -> the last build's mantle (add_head lays a ponytail on it)


def pose(sex, weapon='shortsword'):
    """The Acolyte's body and pose: the left forearm raised forward, the open palm turned up under the ashfire; the
    shortsword low in the right fist, or a spear upright in it (butt on the ground); or (None) the arms at rest."""
    fr = BD.Frame(sex)
    hf, f = fr.hf, fr.f
    if weapon is None:
        return fr
    fr.reach('l', (f['shoulder'] + 0.14, -0.26 * hf, 1.18 * hf), pole=(0.35, 0.45, -1.0))
    fr.open_hand('l', (0.38, -1.0, 0.08), (0.0, 0.0, 1.0))
    if weapon == 'spear':
        fr.reach('r', (-(f['shoulder'] + 0.075), -0.2 * hf, 1.03 * hf), pole=(-0.45, 0.45, -1.0), grip=(0.0, 0.0, 1.0))
    else:
        fr.reach('r', (-(f['shoulder'] + 0.07), -0.045 * hf, 0.915 * hf), pole=(-0.3, 0.4, -1.0),
                 grip=np.array(SWORD_DIR, np.float32))
    return fr


def palm(fr):
    """The middle of the open left palm (figure space), and where the ashfire floats over it."""
    wr = fr.joints['wr_l']
    d, n = fr.open['l']
    p = wr + d * fr.f['hand'][0] * 0.38 + n * 0.012
    return Vector(p), Vector(p + n * 0.14 * fr.hf)


def head_frame(sex, portrait=False):
    return BD.Frame(sex).head_frame(portrait)


def _tail_path(cape, H):
    """A ponytail under the hood, in head space: tied low behind the left ear, just in front of the hood's edge, then
    brought forward over the mantle on the left shoulder."""
    Hi = H.inverted()
    pts = [Vector((0.07, 0.036, -0.046)), Vector((0.096, 0.004, -0.1))]
    zc = cape.Z
    for a, t, lift in ((-44.0, 0.0, 0.02), (-54.0, 0.22, 0.015), (-63.0, 0.5, 0.014), (-69.0, 0.75, 0.012)):
        z = float(zc[0] + (zc[-1] - zc[0]) * t) + (0.006 if t == 0.0 else 0.0)
        p, _ = cape.point(a, z, lift=lift)
        pts.append(Hi @ p)
    return pts


def add_head(fig, look, sex, portrait=False):
    """Seat a look's head, fitted to the hood, on a figure built with head=False; returns the head's root."""
    last = _LAST.get(sex)
    H = BD.Frame(sex).head_frame(portrait)
    hood = {'tail': _tail_path(last['cape'], H)} if (last and look['style'] == 'tail') else True
    hroot, _ = LK.build_head(look, gaze=16.0 if portrait else 0.0, tag=None if look.get('anchor') else look['id'],
                             hood=hood)
    hroot.matrix_basis = H
    hroot.parent = fig
    return hroot


def _seg_dist(P, a, b):
    """Distance from points P to the segment a-b."""
    pa, ba = P - a, b - a
    h = np.clip((pa @ ba) / float(ba @ ba), 0.0, 1.0)
    return np.sqrt(((pa - h[:, None] * ba) ** 2).sum(1))


def _graft_side(fr):
    """The left arm from where its sleeve is cut away (SLEEVE_CUT down the upper arm, the cut torn unevenly) to the
    fingertips: a rough signed distance, negative on the arm. Returns (region, distance past the cut)."""
    J = fr.joints
    sh, el, wr = J['sh_l'], J['el_l'], J['wr_l']
    tip = wr + fr.hand_dir('l') * fr.f['hand'][0]
    u = (el - sh) / np.linalg.norm(el - sh)
    cut = sh + (el - sh) * SLEEVE_CUT
    o1 = np.cross(u, (0.0, 1.0, 0.0))
    o1 /= np.linalg.norm(o1)
    o2 = np.cross(u, o1)
    a0, a1, a2, a3 = fr.f['arm']

    def past(P):
        q = P - cut
        ph = np.arctan2(q @ o2, q @ o1)
        return q @ u + 0.011 * np.sin(3.0 * ph + 0.7) + 0.006 * np.sin(7.0 * ph + 2.0)

    def region(P):
        fore = np.minimum(_seg_dist(P, el, wr) - (a2 + 0.012), _seg_dist(P, wr, tip) - 0.065)
        upper = np.maximum(_seg_dist(P, sh, el) - (a0 + 0.015), -past(P))
        return np.minimum(fore, upper)
    return region, past


def build(v, seed=7, turn=-4.0, look=None, head=True):
    """One variant (VARIANTS). look: a soldier's own face (gb/looks.py); by default the variant's anchor face.
    head=False leaves the head off, for the look pipeline (render.py --looks) to seat each look's head."""
    sex = v.get('sex', 'male')
    rev, cmd, vet = v.get('revenant', False), v.get('commander', False), v.get('veteran', False)
    spear = v.get('weapon') == 'spear'
    armed = v.get('armed', True)
    M.set_mode(revenant=rev)
    fr = pose(sex, ('spear' if spear else 'shortsword') if armed else None)
    hf, f = fr.hf, fr.f
    D = GB.dressed(fr)
    H = fr.head_frame(v.get('portrait') or v.get('level'))
    s_head = fr.head_scale
    M0 = BD.Frame('male')
    wdef = (fr.hips() - float(fr.torso(1.17)[0])) - (M0.hips() - float(M0.torso(1.17)[0]))

    # ---------------------------------------------------------------- materials
    robe = G.cloth('acolyte_robe', color='#222127', blood=0.15, mud=0.9, grime=0.7, seed=71, ash=0.4,
                   char=(0.15, 0.9))
    mantle_m = G.cloth('acolyte_mantle', color='#29282f', blood=0.1, mud=0.5, grime=0.7, seed=73, ash=0.7)
    sash_m = G.cloth('sash', color='#4a1411', blood=0.2, mud=0.5, grime=0.6, seed=75)
    boots = G.leather('boots', color='#241a14', mud=2.4, seed=12)
    gloves = G.leather('gloves', color='#2a2019', seed=41)
    leather = G.leather('leather')
    case_m = G.leather('scrollcase', color='#3b261a', seed=77)
    brass = G.brass('brass')
    old_gilt = G.brass('old_gilt', color='#4c3b1c', tarnish=1.0, blood=0.25, seed=14, film=0.6)
    iron = G.steel('iron', color='#2c2d2f', rust=0.7, blood=0.2, seed=6, edge=0.35, scratch=0.6, dirt=0.8)
    blade = G.steel('blade', color='#8f9295', rough=0.24, rust=0.1, blood=0.8, grime=0.45, seed=8, dents=0.05)
    spearhead = G.steel('spearhead', color='#6c6e71', rough=0.42, rust=0.45, blood=0.55, grime=0.85, seed=51, dents=0.1)
    ash = G.wood('ash', color='#5c4632', seed=48)
    wood = G.wood('wood')
    tone = '#94796a' if sex == 'male' else '#9e8476'
    skin = G.skin('acolyte_skin', tone, windburn=0.3, dirt=0.6)
    if 'l' in fr.open:
        hand_p, fire_at = palm(fr)
    else:
        hand_p = Vector(fr.joints['wr_l'] + fr.hand_dir('l') * f['hand'][0] * 0.38)
    graft = G.graft('graft', tone, tuple(hand_p), reach=0.34 * hf, glow=1.3,
                    light=GB.ASHFIRE[rev][4])

    fig = K.root('figure')
    parts = []

    # ---------------------------------------------------------------- on the body: boots, the robe, the graft, a glove
    graft_side, past_cut = _graft_side(fr)
    parts.append(D.skin('acolyte_body', skin))

    def boot_t(P):
        cuff = np.exp(-((P[:, 2] - 0.24 * hf) / 0.018) ** 2)
        return (0.0055 + 0.004 * cuff).astype(np.float32)
    parts.append(D.layer('softboots', boots, boot_t, lambda P: np.maximum(D.heights(-0.02, 0.25)(P), -D.arms(1.2)(P)),
                         inner=-0.001, tris=7000, smooth=40))
    right_hand = D.hands(cuff=0.012)
    J = fr.joints
    sh_l, el_l = J['sh_l'], J['el_l']
    el_r, wr_r = J['el_r'], J['wr_r']
    u_r = (wr_r - el_r) / np.linalg.norm(wr_r - el_r)
    lf_r = float(np.linalg.norm(wr_r - el_r))

    def robe_t(P):
        th = np.arctan2(P[:, 0], -P[:, 1])
        folds = 0.5 + 0.5 * np.sin(th * 9.0 + 1.3 * np.sin(P[:, 2] * 23.0))
        on_arm = np.clip(1.0 - BD._arms(P, fr, 1.0) / 0.02, 0.0, 1.0)
        s = np.clip(((P - el_r) @ u_r) / lf_r, 0.0, 1.0) * (P[:, 0] < 0.0)
        cuff = np.clip((s - 0.55) / 0.45, 0.0, 1.0) ** 1.5 * on_arm                  # the right sleeve's bell
        roll = np.exp(-(past_cut(P) / 0.012) ** 2) * (_seg_dist(P, sh_l, el_l) < 0.09)   # the torn left sleeve's edge
        return (0.0085 + 0.003 * folds * (1.0 - on_arm) + 0.013 * cuff + 0.005 * roll).astype(np.float32)
    parts.append(D.layer('robe', robe, robe_t,
                         lambda P: np.maximum(np.maximum(D.heights(0.86, 1.545)(P), -right_hand(P)), -graft_side(P)),
                         inner=0.003, tris=15000, smooth=45))
    parts.append(D.layer('graft', graft, lambda P: np.full(len(P), 0.003, np.float32), graft_side, inner=0.004,
                         feather=0.0015, floor=1.0, tris=8000, smooth=40))
    parts.append(D.layer('glove', gloves, lambda P: np.full(len(P), 0.0032, np.float32),
                         lambda P: np.maximum(D.hands(cuff=0.04)(P), P[:, 0]), inner=0.002, tris=3000, smooth=45))

    # ---------------------------------------------------------------- the skirt, hanging from the sash
    zb = (1.05 + 1.5 * wdef) * hf               # his at the hips, hers cinched at her natural waist
    skirt = GB.Drape(D, zb + 0.035 * hf, 0.075 * hf, [a * 5.0 for a in range(72)], 0.024, rows=36, oy=0.01,
                     flare=0.09, folds=0.016, fold_n=10, ragged=0.03, seed=seed, arms=False, closed=True,
                     cinch=(zb, 0.022))
    parts.append(skirt.mesh('robe_skirt', robe, thick=0.005))
    if vet:      # patched low on the front, in somebody else's cloth
        top, out = [], []
        for k in range(5):
            p, n = skirt.point(-118.0 + 7.0 * k, 0.62 * hf, lift=0.005)
            top.append(p)
            out.append(n)
        parts.append(A.cloth_panel('patch', top, out, 0.15 * hf, G.cloth('patch', color='#4a3a2a', blood=0.3, seed=55),
                                   rows=6, tatter=0.06, slits=0, fold=0.003, seed=seed + 4, thick=0.003))

    # ---------------------------------------------------------------- the sash, knotted at the left hip
    ring = [skirt.point(a, zb, lift=0.012) for a in range(0, 360, 6)]
    parts += A.strap('sash', [p for p, _ in ring], [n for _, n in ring], 0.052, 0.01, sash_m, closed=True)
    knot, kn = skirt.point(-58.0, zb, lift=0.03)
    parts.append(K.sphere('sash_knot', tuple(knot), 0.028, sash_m, scale=(1.2, 0.7, 1.0), seg=14, rings=10))
    for k, (da, ln) in enumerate(((-4.0, 0.3), (5.0, 0.24))):
        top, out = [], []
        for j in range(3):
            p, n = skirt.point(-58.0 + da + (j - 1) * 3.2, zb - 0.02, lift=0.034 + 0.004 * k)
            top.append(p)
            out.append(n)
        parts.append(A.cloth_panel('sash_end', top, out, ln * hf, sash_m, rows=8, tatter=0.12, slits=0, fold=0.006,
                                   seed=seed + 20 + k, thick=0.004))

    # ---------------------------------------------------------------- mantle and hood
    ztop = 1.58 * hf               # as the Ranger's capelet: the collar rises round the hood's neck, just under the chin
    cape = GB.Drape(D, ztop, 1.27 * hf, [a * 5.0 for a in range(72)], 0.044, rows=20, oy=0.02,
                    collar=(0.1 * s_head + 0.012, 0.5), flare=0.03, folds=0.012, fold_n=9, ragged=0.02, seed=seed,
                    closed=True, arms=False, hem=lambda a: 0.055 * hf * max(0.0, -math.sin(math.radians(a))) ** 1.5)
    parts.append(cape.mesh('mantle', mantle_m, thick=0.006))
    z_bot = (Vector(H.inverted() @ Vector((0.0, 0.02, ztop))).z) - 0.03
    parts.append(GB.hood('hood', H, z_bot, mantle_m, seed=seed))
    _LAST[sex] = {'cape': cape}

    # ---------------------------------------------------------------- the graft: its manacle; the Veteran's barbs
    wr_l = J['wr_l']
    fa = (wr_l - el_l) / np.linalg.norm(wr_l - el_l)
    parts += GB.manacle('manacle', Vector(el_l + (wr_l - el_l) * 0.86), Vector(fa), iron,
                        r_in=f['arm'][3] + 0.0085)
    if vet:
        bone = G.flat('bone', '#b3a88f', rough=0.6)
        o = np.cross((0.0, 0.0, 1.0), fa)          # outward, away from the body
        o = o / np.linalg.norm(o)
        for k, (t, ang, ln) in enumerate(((0.22, 0.55, 0.07), (0.36, 0.95, 0.085), (0.5, 0.45, 0.075), (0.62, 1.2, 0.06),
                                         (0.74, 0.7, 0.05))):
            c = el_l + (wr_l - el_l) * t
            out = o * math.cos(ang) + np.array((0.0, 0.0, 1.0)) * math.sin(ang)
            base = c + out * (f['arm'][2] * 0.8)
            tipp = base + (out * 0.75 - fa * 0.65) * ln
            parts.append(K.tube('barb', Vector(base - out * 0.008), Vector(tipp), 0.0095, 0.001, bone, seg=8))

    # ---------------------------------------------------------------- the ashfire over the open palm
    if armed:
        parts += GB.ashfire('ashfire', fire_at, revenant=rev, energy=1.0, seed=seed)

    # ---------------------------------------------------------------- the scroll case, at the right hip
    if not cmd:
        cp, cn = skirt.point(150.0, zb - 0.02, lift=0.03)
        d = Vector((-0.1, 0.25, -1.0)).normalized()
        a_, b_ = cp + cn * 0.012 - d * 0.03, cp + cn * 0.02 + d * 0.28
        parts.append(K.tube('scroll_case', a_, b_, 0.026, 0.024, case_m, seg=14))
        parts.append(K.tube('scroll_cap', a_ - d * 0.035, a_ + d * 0.012, 0.029, 0.029, iron, seg=14))
        parts.append(K.tube('scroll_foot', b_ - d * 0.01, b_ + d * 0.012, 0.027, 0.022, iron, seg=14))
        parts.append(GB.cord('scroll_strap', [skirt.point(158.0, zb, lift=0.014)[0], a_ + cn * 0.02], 0.005, leather))

    # ---------------------------------------------------------------- rank: the morse; the Veteran's spaulder
    if cmd:
        p, n = cape.point(-90.0, ztop - 0.05 * hf, lift=0.004)
        disc = K.lathe('morse', [(0.042, 0.0), (0.039, 0.009), (0.016, 0.015), (0.0, 0.016)], old_gilt, seg=24,
                       cap_bottom=True, cap_top=False)
        A.place(disc, p, A.frame(n, back=(0.0, 0.0, 1.0)))
        parts.append(disc)
        parts.append(A.torus('morse_ring', (0.0, 0.0, 0.0), 0.042, 0.006, old_gilt, seg=24, rseg=8))
        A.place(parts[-1], p + n * 0.003, A.frame(n, back=(0.0, 0.0, 1.0)))
    if vet:
        blackened = G.steel('blackened', color='#3a3b3e', rust=0.3, blood=0.2, seed=4, edge=0.8)
        spaul = (f['deltoid'] + 0.025) / (M0.f['deltoid'] + 0.025)
        sh = Vector(J['sh_r']) + Vector((-0.03, 0.0, -0.005 * hf))      # seated on the mantle
        parts += A.pauldron('spaulder', sh, -1, blackened, old_gilt, size=1.0 * spaul, lames=2, seed=83)

    # ---------------------------------------------------------------- the weapon
    if armed:
        if spear:
            parts += GB.boar_spear('spear', Vector(fr.fist('r')), (0.0, -0.02, 1.0), 2.02 * hf, ash, spearhead, leather,
                                   lugs=False)
        else:
            parts += A.broadsword('sword', Vector(fr.fist('r')), SWORD_DIR, blade, iron, leather, brass, length=0.56,
                                  width=0.052)

    # ---------------------------------------------------------------- the head
    head_c = Vector(H.translation)
    if head:
        if look is None:
            look = dict(LK.anchor(sex, commander=cmd, veteran=vet), seed=seed)
        hood = {'tail': _tail_path(cape, H)} if look['style'] == 'tail' else True
        hroot, _ = LK.build_head(look, gaze=16.0 if v.get('portrait') else 0.0,
                                 tag=None if look.get('anchor') else look['id'], hood=hood)
        hroot.matrix_world = H
        parts.append(hroot)
    if rev:
        parts.append(K.glow('face_glow', head_c + Vector((0.0, -0.105, 0.012)), '#b98cf0', 0.18, radius=0.012))

    # ---------------------------------------------------------------- the Commander's banner, over the robe
    if cmd:
        yb = max(skirt.point(90.0, zb - 0.1 * hf, lift=0.03)[0].y, cape.point(90.0, 1.3 * hf, lift=0.03)[0].y)
        parts.append(K.tube('pole', Vector((0.02, yb, 0.95 * hf)), Vector((0.02, yb + 0.04, 2.3 * hf)), 0.017, 0.015,
                            wood, seg=12))
        parts.append(K.tube('crossbar', Vector((-0.285, yb + 0.036, 2.2 * hf)), Vector((0.325, yb + 0.036, 2.2 * hf)),
                            0.011, 0.011, wood, seg=10))
        tip = K.blade('finial', 0.07, 0.032, 0.012, brass, secs=[(0.0, 1.0), (0.4, 1.0), (1.0, 0.0)])
        A.place(tip, Vector((0.02, yb + 0.04, 2.3 * hf)), A.frame((0.0, 0.0, 1.0)))
        parts.append(tip)
        cz = (2.19 - 0.29) * hf
        flag_m = G.cloth('banner', color='#551714', blood=0.25, mud=0.0, seed=23, device=(0.02, cz, 0.12, '#b39a62'))
        top, out = [], []
        for k in range(16):
            top.append(Vector((-0.275 + 0.59 * k / 15, yb + 0.044, 2.19 * hf)))
            out.append(Vector((0.0, -1.0, 0.0)))
        parts.append(A.cloth_panel('banner', top, out, 0.62 * hf, flag_m, rows=18, tatter=0.3, slits=1, fold=0.022,
                                   seed=seed + 12))

    K.parent(parts, fig)
    fig.scale = (FIG_SCALE,) * 3
    fig.rotation_euler.z = math.radians(turn)
    return fig
