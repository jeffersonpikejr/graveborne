"""ASH ACOLYTE — the Grafted. Asset #4: "reads the Blight and answers it. Every rank of it a bill that comes due."

Brief (in the Line-Breaker's register): a runaway from the Conclave's grafting cells (a failed apprentice, a seminary
novice, the one survivor of a cohort) who carries the Blight in one arm and spends it for the company, in leather
armour of the Conclave's own make, taken when they ran. A cuirass of boiled leather moulded to the chest with a keel
down its middle, over a fauld of overlapping bands, scorched ash-black, worn ash-grey at every edge and dusted pale on
the shoulders; a skirt of hardened leather strips to mid-thigh over the company's oxblood, riveted at their feet; a high
standing collar, open at the throat, that the hood tucks into (the hood worn low, its front out over the brow so the
eyes sit in its shadow and the jaw and the mouth carry the soldier); on the sword arm a leather spaulder of three
lames and a vambrace; breeches, tall strapped boots, leather knee cops; a broad belt, and the company's oxblood again
as a sash knotted at the hip. The left arm is bare
from the shoulder for the graft: the flesh gone ash-grey and bruised violet and split by veins of violet light from the
palm up, bound in a harness of buckled straps, a broken Conclave manacle still locked on the wrist. Over the open palm
floats the ashfire: a white heart in a knot of violet flame, embers and flakes of ash turning round it, its light on
the arm, the armour and the face. A shortsword held low in the right hand, the way the Fighter holds his blade; a
scroll case at the hip. At 26 px an Acolyte is the hood, the dark ash-leather with its strip skirt, one bare arm, and
the violet point of the ashfire at the hand.

Commander (any class; here on the Acolyte): the banner strapped to the back, one mark of rank (a tarnished gilt clasp
and chain across the collar's throat), the founding scar, fewer loose pieces (the scroll case stays behind). Veteran
(level 5): dead men's gear (a blackened steel spaulder for the leather one, a mail hem under the strips, an iron plate
riveted over the heart), and the graft has taken more: bone barbs have broken through the forearm (the Serrated Graft).
Revenant: the same kit drained to grave-grey, violet light in the cracks and the eyes, and the ashfire burning colder.
Weapons: the shortsword, or (half of them) a spear held upright.

Everything is laid on the wearer's body (gb/garb.py): the shirt, the cuirass, the vambrace, the harness and the boots
are layers over the posed body, so his barrel chest and her waist show through the leather; the strips hang from the
belt (his at the hips, hers at her natural waist, flaring over her hips); the hood is the Ranger's cut, so the heads'
hair fits under it the same way.
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
SLEEVE_CUT = 0.3                        # the shirt's left sleeve is cut away this far down the upper arm
_LAST = {}                              # sex -> the last build's collar and body (add_head lays a ponytail on them)


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


def _tail_path(collar, D, H, hf):
    """A ponytail under the hood, in head space: tied low behind the left ear, brought forward inside the hood along
    the neck and out of its opening under the jaw, then over the collar and down the cuirass on the left of the chest."""
    Hi = H.inverted()
    pts = [Vector((0.058, 0.05, -0.06)), Vector((0.085, 0.005, -0.125)), Vector((0.062, -0.05, -0.18))]
    for a, z, lift in ((-44.0, 1.6 * hf + 0.006, 0.02), (-54.0, 1.535 * hf, 0.016)):
        pts.append(Hi @ collar.point(a, z, lift=lift)[0])
    for a, z, clear in ((-62.0, 1.44 * hf, 0.042), (-68.0, 1.34 * hf, 0.04)):
        pts.append(Hi @ D.on(a, z, clear)[0])
    return pts


def add_head(fig, look, sex, portrait=False):
    """Seat a look's head, fitted to the hood, on a figure built with head=False; returns the head's root."""
    last = _LAST.get(sex)
    H = BD.Frame(sex).head_frame(portrait)
    hood = {'tail': _tail_path(last['collar'], last['D'], H, last['hf'])} if (last and look['style'] == 'tail') else True
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


def _band(a, b, s0, w, radius):
    """A band round the limb segment a-b, `w` wide, centred s0 of the way along it: a rough signed distance."""
    L = float(np.linalg.norm(b - a))
    u = (b - a) / L

    def region(P):
        q = P - a
        s = q @ u
        rad = np.sqrt(np.maximum((q * q).sum(1) - s * s, 0.0))
        return np.maximum(rad - radius, np.abs(s - s0 * L) - w / 2.0)
    return region


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
    J = fr.joints

    # ---------------------------------------------------------------- materials
    cuir = G.leather('cuirbouilli', color='#221f21', blood=0.25, mud=0.8, seed=81, scuff_c='#67615a', ash=0.45,
                     crackle=0.1, cells=28.0)
    under = G.cloth('underskirt', color='#4a1411', blood=0.3, mud=1.4, grime=0.7, seed=79)
    strap = G.leather('straps', color='#2d2119', blood=0.15, mud=1.0, seed=83)
    wool = G.cloth('acolyte_shirt', color='#2f2b2b', blood=0.15, mud=0.8, grime=0.7, seed=71)
    hood_m = G.cloth('acolyte_hood', color='#2e2c31', blood=0.05, mud=0.0, grime=0.7, seed=73, ash=0.6)
    breech = G.cloth('breeches', color='#24211e', blood=0.1, mud=1.6, seed=37)
    sash_m = G.cloth('sash', color='#4a1411', blood=0.2, mud=0.5, grime=0.6, seed=75)
    boots = G.leather('boots', color='#241a14', mud=2.4, seed=12)
    gloves = G.leather('gloves', color='#2a2019', seed=41)
    case_m = G.leather('scrollcase', color='#3b261a', seed=77)
    brass = G.brass('brass')
    old_gilt = G.brass('old_gilt', color='#4c3b1c', tarnish=1.0, blood=0.25, seed=14, film=0.6)
    iron = G.steel('iron', color='#2c2d2f', rust=0.7, blood=0.2, seed=6, edge=0.35, scratch=0.6, dirt=0.8)
    blackened = G.steel('blackened', color='#3a3b3e', rust=0.3, blood=0.2, seed=4, edge=0.8)
    blade = G.steel('blade', color='#8f9295', rough=0.24, rust=0.1, blood=0.8, grime=0.45, seed=8, dents=0.05)
    spearhead = G.steel('spearhead', color='#6c6e71', rough=0.42, rust=0.45, blood=0.55, grime=0.85, seed=51, dents=0.1)
    ash = G.wood('ash', color='#5c4632', seed=48)
    wood = G.wood('wood')
    tone = '#94796a' if sex == 'male' else '#9e8476'
    skin = G.skin('acolyte_skin', tone, windburn=0.3, dirt=0.6)
    if 'l' in fr.open:
        hand_p, fire_at = palm(fr)
    else:
        hand_p = Vector(J['wr_l'] + fr.hand_dir('l') * f['hand'][0] * 0.38)
    graft = G.graft('graft', tone, tuple(hand_p), reach=0.34 * hf, glow=1.3, light=GB.ASHFIRE[rev][4])

    fig = K.root('figure')
    parts = []

    # ---------------------------------------------------------------- on the body: shirt, breeches, boots
    graft_side, _ = _graft_side(fr)
    hands = D.hands(cuff=0.012)
    parts.append(D.skin('acolyte_body', skin))
    parts.append(D.layer('shirt', wool, lambda P: np.full(len(P), 0.0055, np.float32),
                         lambda P: np.maximum(np.maximum(D.heights(0.88, 1.545)(P), -hands(P)), -graft_side(P)),
                         inner=0.003, tris=12000, smooth=45))
    parts.append(D.layer('breeches', breech, lambda P: np.full(len(P), 0.0035, np.float32),
                         lambda P: np.maximum(D.heights(0.1, 1.0)(P), -D.arms(1.2)(P)), inner=0.002, tris=9000))

    def boot_t(P):
        z = P[:, 2] / hf
        band = sum(np.exp(-((z - zz) / 0.011) ** 2) for zz in (0.2, 0.33))       # two straps round the shaft
        cuff = np.exp(-((z - 0.415) / 0.016) ** 2)
        return (0.006 + 0.0035 * band + 0.005 * cuff).astype(np.float32)
    parts.append(D.layer('tallboots', boots, boot_t, lambda P: np.maximum(D.heights(-0.02, 0.425)(P), -D.arms(1.2)(P)),
                         inner=-0.0015, tris=8000, smooth=40))

    # ---------------------------------------------------------------- the cuirass: moulded chest, banded fauld
    zb = (1.05 + 1.5 * wdef) * hf               # the belt: his at the hips, hers at her natural waist
    ft = zb + 0.15 * hf                         # the fauld's three bands, from here down to the belt
    region_c = lambda P: np.maximum(D.heights(zb / hf - 0.02, 1.52)(P), D.trunk(0.004)(P))    # noqa: E731

    def cuirass_t(P):
        z = P[:, 2]
        u = np.clip((ft - z) / (ft - zb + 0.02 * hf), 0.0, 0.999) * 3.0
        fauld = (u - np.floor(u)) * (z < ft)                                     # each band flares to its lower edge
        keel = np.exp(-(P[:, 0] / 0.018) ** 2) * (P[:, 1] < 0.0) * (z > ft)       # the moulded chest's ridge
        rim = np.exp(-(region_c(P) / 0.007) ** 2)                                # a rolled edge
        return (0.012 + 0.0065 * fauld + 0.004 * keel + 0.0035 * rim).astype(np.float32)
    parts.append(D.layer('cuirass', cuir, cuirass_t, region_c, inner=-0.007, feather=0.002, floor=0.9, tris=14000,
                         smooth=38))
    if vet:      # a dead man's steel plate riveted over the heart
        p, n = D.on(-66.0, 1.33 * hf, 0.03)
        plate = K.rbox('patch_plate', (0.085, 0.095, 0.006), (0, 0, 0), iron, bev=0.003)
        A.place(plate, p, A.frame(n, back=(0.0, 0.0, 1.0)))
        parts.append(plate)
        R3 = A.frame(n, back=(0.0, 0.0, 1.0))
        parts.append(A.rivets('patch_rivets', [p + (R3 @ Vector((x, y, 0.004, 0.0))).to_3d()
                                               for x in (-0.034, 0.034) for y in (-0.039, 0.039)], 0.005, old_gilt))

    # ---------------------------------------------------------------- the sword arm: spaulder, vambrace, glove
    spaul = (f['deltoid'] + 0.025) / (M0.f['deltoid'] + 0.025)
    sh = Vector(J['sh_r']) + Vector((-0.012, 0.0, 0.03 * hf))
    parts += A.pauldron('spaulder', sh, -1, blackened if vet else cuir, old_gilt if vet else iron, size=0.95 * spaul,
                        lames=3, seed=83)
    parts.append(D.layer('vambrace', cuir, lambda P: np.full(len(P), 0.013, np.float32),
                         D.forearm('r', 0.3, 0.9, radius=0.09), inner=-0.0065, feather=0.0015, floor=0.95, tris=3000,
                         smooth=35))
    parts.append(D.layer('glove', gloves, lambda P: np.full(len(P), 0.0032, np.float32),
                         lambda P: np.maximum(D.hands(cuff=0.04)(P), P[:, 0]), inner=0.002, tris=3000, smooth=45))

    # ---------------------------------------------------------------- the graft: bare flesh, its harness, the manacle
    parts.append(D.layer('graft', graft, lambda P: np.full(len(P), 0.003, np.float32), graft_side, inner=0.004,
                         feather=0.0015, floor=1.0, tris=8000, smooth=40))
    sh_l, el_l, wr_l = J['sh_l'], J['el_l'], J['wr_l']
    a0, a2 = f['arm'][0], f['arm'][2]
    bands = [(sh_l, el_l, 0.56, a0 * 1.45), (sh_l, el_l, 0.82, a0 * 1.4), (el_l, wr_l, 0.22, a2 * 1.45)]
    for k, (a, b, s0, rad) in enumerate(bands):
        parts.append(D.layer(f'harness{k}', strap, lambda P: np.full(len(P), 0.0045, np.float32),
                             _band(a, b, s0, 0.024, rad), inner=-0.0032, feather=0.001, floor=1.0, tris=1500, smooth=35))
        u = (b - a) / np.linalg.norm(b - a)
        out = np.array((1.0, 0.0, 0.25))
        out = out - u * float(out @ u)
        out /= np.linalg.norm(out)
        c = a + (b - a) * s0
        buckle = K.rbox(f'harness_buckle{k}', (0.026, 0.009, 0.03), (0, 0, 0), iron, bev=0.003)
        A.place(buckle, Vector(c + out * (rad * 0.78 + 0.004)), A.frame(Vector(out), back=tuple(u)))
        parts.append(buckle)
    fa = (wr_l - el_l) / np.linalg.norm(wr_l - el_l)
    parts += GB.manacle('manacle', Vector(el_l + (wr_l - el_l) * 0.86), Vector(fa), iron, r_in=f['arm'][3] + 0.0085)
    if vet:      # the graft has taken more: bone barbs broken through the forearm
        bone = G.flat('bone', '#b3a88f', rough=0.6)
        o = np.cross((0.0, 0.0, 1.0), fa)
        o = o / np.linalg.norm(o)
        for k, (t, ang, ln) in enumerate(((0.36, 0.95, 0.085), (0.5, 0.45, 0.075), (0.62, 1.2, 0.06), (0.74, 0.7, 0.05))):
            c = el_l + (wr_l - el_l) * t
            out = o * math.cos(ang) + np.array((0.0, 0.0, 1.0)) * math.sin(ang)
            base = c + out * (a2 * 0.8)
            tipp = base + (out * 0.75 - fa * 0.65) * ln
            parts.append(K.tube('barb', Vector(base - out * 0.008), Vector(tipp), 0.0095, 0.001, bone, seg=8))

    # ---------------------------------------------------------------- the skirt of strips, the belt, the sash
    skirt = GB.Drape(D, zb + 0.012, 0.6 * hf, [a * 5.0 for a in range(72)], 0.028, rows=16, oy=0.01, flare=0.06,
                     seed=seed, arms=False, closed=True)
    under_sk = GB.Drape(D, zb + 0.012, 0.64 * hf, [a * 5.0 for a in range(72)], 0.022, rows=16, oy=0.01, flare=0.05,
                        folds=0.006, fold_n=14, ragged=0.012, seed=seed + 2, arms=False, closed=True)
    parts.append(under_sk.mesh('underskirt', under, thick=0.004))      # the company's oxblood, between the strips
    parts += GB.strips('strips', skirt, 16, 0.056, zb + 0.012, 0.58 * hf, cuir, lift=0.004, offset=0.0, thick=0.005,
                       seed=seed + 1, rivet_mat=iron)
    if vet:      # a dead man's mail, its hem showing under the strips
        _, tf95, tb95 = (float(x) for x in fr.torso(0.95))
        hr = fr.hips() + 0.012
        sy = ((tf95 + tb95) / 2.0 + 0.012) / hr
        mail_sk = K.lathe('mail_hem', [(hr + 0.03 + 0.4 * wdef, 0.56 * hf), (hr + 0.018 + 0.25 * wdef, 0.72 * hf),
                                       (hr + 0.004, 0.9 * hf), (hr - 0.01, zb)],
                          G.maille('maille'), seg=48, sy=sy, loc=(0.0, (tb95 - tf95) / 2.0, 0.0), cap_bottom=False,
                          cap_top=False)
        A.solid(mail_sk, 0.006)
        parts.append(mail_sk)
    bp, bn = D.ring(zb, 0.036, n=56)
    parts += A.strap('belt', bp, bn, 0.044, 0.007, strap, iron, rivet_every=0.11, closed=True)
    front = min(range(len(bp)), key=lambda i: bp[i].y)
    parts.append(K.rbox('buckle', (0.05, 0.012, 0.055), (bp[front].x + 0.03, bp[front].y - 0.01, zb), iron, bev=0.005))
    knot, kn = D.on(-58.0, zb - 0.01, 0.05)
    parts.append(K.sphere('sash_knot', tuple(knot), 0.026, sash_m, scale=(1.2, 0.7, 1.0), seg=14, rings=10))
    for k, (da, ln) in enumerate(((-4.0, 0.3), (5.0, 0.24))):
        top, out = [], []
        for j in range(3):
            p, n = skirt.point(-58.0 + da + (j - 1) * 3.2, zb - 0.025, lift=0.02 + 0.004 * k)
            top.append(p)
            out.append(n)
        parts.append(A.cloth_panel('sash_end', top, out, ln * hf, sash_m, rows=8, tatter=0.12, slits=0, fold=0.006,
                                   seed=seed + 20 + k, thick=0.004))

    # ---------------------------------------------------------------- knee cops
    for side, s in (('l', 1.0), ('r', -1.0)):
        kn_ = J['kn_' + side]
        r = float(D.outer(np.array([kn_ + np.array((0.0, 0.0, 0.012 * hf))], np.float32),
                          np.array([[0.0, -1.0, 0.0]], np.float32), 0.004)[0])
        parts += A.cop('kneecop', Vector(kn_ + np.array((0.0, -r + 0.02, 0.012 * hf))), (s * 0.12, -1.0, 0.05),
                       (s, 0.15, 0.0), cuir, iron, r=0.058, seed=3 + int(s))

    # ---------------------------------------------------------------- the collar and the hood
    s_hr = s_head / 1.08
    collar = GB.Drape(D, 1.6 * hf, 1.465 * hf, [-60.0 + 5.0 * k for k in range(61)], 0.02, rows=10, oy=0.02,
                      collar=(0.138 * s_hr, 0.25), seed=seed, arms=False)
    parts.append(collar.mesh('collar', cuir, thick=0.008))
    z_bot = (Vector(H.inverted() @ Vector((0.0, 0.02, 1.6 * hf))).z) - 0.03
    parts.append(GB.hood('hood', H, z_bot, hood_m, seed=seed))
    _LAST[sex] = {'collar': collar, 'D': D, 'hf': hf}

    # ---------------------------------------------------------------- the ashfire over the open palm
    if armed:
        parts += GB.ashfire('ashfire', fire_at, revenant=rev, energy=1.0, seed=seed)

    # ---------------------------------------------------------------- the scroll case, at the right hip
    if not cmd:
        cp, cn = skirt.point(150.0, zb - 0.03, lift=0.03)
        d = Vector((-0.1, 0.25, -1.0)).normalized()
        a_, b_ = cp + cn * 0.012 - d * 0.03, cp + cn * 0.02 + d * 0.28
        parts.append(K.tube('scroll_case', a_, b_, 0.026, 0.024, case_m, seg=14))
        parts.append(K.tube('scroll_cap', a_ - d * 0.035, a_ + d * 0.012, 0.029, 0.029, iron, seg=14))
        parts.append(K.tube('scroll_foot', b_ - d * 0.01, b_ + d * 0.012, 0.027, 0.022, iron, seg=14))
        parts.append(GB.cord('scroll_strap', [D.on(158.0, zb, 0.04)[0], a_ + cn * 0.02], 0.005, strap))

    # ---------------------------------------------------------------- rank: a gilt clasp across the collar's throat
    if cmd:
        ends = [collar.point(a, 1.53 * hf, lift=0.006) for a in (-62.0, 242.0)]
        for k, (p, n) in enumerate(ends):
            disc = K.lathe('clasp', [(0.032, 0.0), (0.03, 0.007), (0.013, 0.012), (0.0, 0.013)], old_gilt, seg=20,
                           cap_bottom=True, cap_top=False)
            A.place(disc, p, A.frame(n, back=(0.0, 0.0, 1.0)))
            parts.append(disc)
        mid = (ends[0][0] + ends[1][0]) / 2.0 + Vector((0.0, -0.02, -0.035 * hf))
        parts.append(GB.cord('clasp_chain', [ends[0][0], mid, ends[1][0]], 0.006, old_gilt))

    # ---------------------------------------------------------------- the weapon
    if armed:
        if spear:
            parts += GB.boar_spear('spear', Vector(fr.fist('r')), (0.0, -0.02, 1.0), 2.02 * hf, ash, spearhead, strap,
                                   lugs=False)
        else:
            parts += A.broadsword('sword', Vector(fr.fist('r')), SWORD_DIR, blade, iron, strap, brass, length=0.56,
                                  width=0.052)

    # ---------------------------------------------------------------- the head
    head_c = Vector(H.translation)
    if head:
        if look is None:
            look = dict(LK.anchor(sex, commander=cmd, veteran=vet), seed=seed)
        hood = {'tail': _tail_path(collar, D, H, hf)} if look['style'] == 'tail' else True
        hroot, _ = LK.build_head(look, gaze=16.0 if v.get('portrait') else 0.0,
                                 tag=None if look.get('anchor') else look['id'], hood=hood)
        hroot.matrix_world = H
        parts.append(hroot)
    if rev:
        parts.append(K.glow('face_glow', head_c + Vector((0.0, -0.105, 0.012)), '#b98cf0', 0.18, radius=0.012))

    # ---------------------------------------------------------------- the Commander's banner, on the back
    if cmd:
        yb = max(D.on(90.0, 1.25 * hf, 0.06)[0].y, skirt.point(90.0, 0.9 * hf, lift=0.03)[0].y)
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
