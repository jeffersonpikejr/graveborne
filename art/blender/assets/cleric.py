"""CLERIC — the Chirurgeon. Asset #3: "field-surgeon and last rites both; holds the line's soul together."

Brief (in the Line-Breaker's register): the company's chaplain and its surgeon, who sewed soldiers shut through three
wars and buried more than she saved. A mail hauberk to the knee under a long surcoat of the company's bone-white,
stained dark to the knees with mud and old blood, a broad oxblood cross front and back; belted with a rope girdle,
its knotted ends hanging. The mail coif is pushed back into a heavy collar round the neck and shoulders, so the face
and the hair show and every soldier stays their own. A chirurgeon's satchel on a strap across the body, a girdle
book at the hip. A flanged mace held low in the right hand, head down, the way the Fighter holds his blade; in the
left, a chapel lantern with a small iron cross on its cap, its warm light on the surcoat. At 26 px a Cleric is the
pale surcoat with its dark cross, and the lantern's point of light.

Commander (any class; here on the Cleric): the banner strapped to the back, one mark of rank (a tarnished gilt chain
of office with a medallion), the founding scar, fewer loose pieces (the satchel stays behind). Veteran (level 5):
dead men's gear — a blackened steel spaulder on the left shoulder, a tarnished gilt reliquary on a chain, a patched
surcoat. Revenant: the same kit drained to grave-grey, violet light in the cracks, the eyes and the lantern.
Weapons: the mace, or (a Cleric rolls each one time in three) a spear held upright, or a shortsword held low.

Everything is laid on the wearer's body (gb/garb.py): the hauberk and breeches are layers over the posed body, the
surcoat is draped over it and belted at the waist (his at the hips, hers at her natural waist), so his barrel chest
and her waist and hips show through.
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
for _w in ('', '_spear', '_shortsword'):
    for _t, _v in (('', {}), ('_commander', {'commander': True}), ('_veteran', {'veteran': True}),
                   ('_revenant', {'revenant': True}), ('_commander_revenant', {'commander': True, 'revenant': True})):
        for _f, _sex in (('m', 'male'), ('f', 'female')):
            VARIANTS[f'cleric{_w}{_t}_{_f}'] = dict(_v, sex=_sex, **({'weapon': _w[1:]} if _w else {}))

MACE_DIR = (-0.12, -0.34, -0.93)        # held low, head down and a little forward
SWORD_DIR = (-0.2, -0.32, -0.93)


def pose(sex, weapon='mace'):
    """The Cleric's body and pose: the lantern held out before the left hip; the mace or shortsword low in the right
    fist, or a spear upright in it (butt on the ground); or (None) the arms at rest."""
    fr = BD.Frame(sex)
    hf, f = fr.hf, fr.f
    if weapon is None:
        return fr
    fr.reach('l', (f['shoulder'] + 0.085, -0.2 * hf, 1.02 * hf), pole=(0.4, 0.35, -1.0), grip=(1.0, 0.0, 0.0))
    if weapon == 'spear':
        fr.reach('r', (-(f['shoulder'] + 0.075), -0.2 * hf, 1.03 * hf), pole=(-0.45, 0.45, -1.0), grip=(0.0, 0.0, 1.0))
    else:
        d = np.array(MACE_DIR if weapon == 'mace' else SWORD_DIR, np.float32)
        fr.reach('r', (-(f['shoulder'] + 0.07), -0.045 * hf, 0.915 * hf), pole=(-0.3, 0.4, -1.0), grip=d)
    return fr


def head_frame(sex, portrait=False):
    return BD.Frame(sex).head_frame(portrait)


def add_head(fig, look, sex, portrait=False):
    """Seat a look's head on a figure built with head=False; returns the head's root."""
    hroot, _ = LK.build_head(look, gaze=16.0 if portrait else 0.0, tag=None if look.get('anchor') else look['id'])
    hroot.matrix_basis = BD.Frame(sex).head_frame(portrait)
    hroot.parent = fig
    return hroot


def build(v, seed=7, turn=-4.0, look=None, head=True):
    """One variant (VARIANTS). look: a soldier's own face (gb/looks.py); by default the variant's anchor face.
    head=False leaves the head off, for the look pipeline (render.py --looks) to seat each look's head."""
    sex = v.get('sex', 'male')
    rev, cmd, vet = v.get('revenant', False), v.get('commander', False), v.get('veteran', False)
    weapon = v.get('weapon', 'mace')
    armed = v.get('armed', True)
    M.set_mode(revenant=rev)
    fr = pose(sex, weapon if armed else None)
    hf, f = fr.hf, fr.f
    D = GB.dressed(fr)
    H = fr.head_frame(v.get('portrait') or v.get('level'))
    M0 = BD.Frame('male')
    wdef = (fr.hips() - float(fr.torso(1.17)[0])) - (M0.hips() - float(M0.torso(1.17)[0]))

    # ---------------------------------------------------------------- materials
    surcoat = G.cloth('surcoat', color='#b3a88f', blood=0.5, mud=2.1, grime=0.75, seed=57, kind='bone',
                      cross=(0.0, 1.235 * hf, 0.125 * hf, 0.072 * hf, '#4a1210'))
    mail = G.maille('maille')
    breech = G.cloth('breeches', color='#2c2924', blood=0.1, mud=1.6, seed=37)
    boots = G.leather('boots', color='#2b2017', mud=2.4, seed=12)
    gloves = G.leather('gloves', color='#2e2219', seed=41)
    leather = G.leather('leather')
    rope = G.cloth('rope', color='#7a6d55', blood=0.05, mud=0.8, grime=0.5, seed=61)
    cover = G.leather('bookcover', color='#3d1f16', seed=62)
    pages = G.flat('pages', '#a89a7c')
    brass = G.brass('brass')
    old_gilt = G.brass('old_gilt', color='#4c3b1c', tarnish=1.0, blood=0.25, seed=14, film=0.6)
    iron = G.steel('iron', color='#2c2d2f', rust=0.6, blood=0.3, seed=6, edge=0.35, scratch=0.6, dirt=0.7)
    head_steel = G.steel('macehead', color='#4c4e50', rough=0.55, rust=0.5, blood=0.75, seed=63, dents=0.3, edge=0.3,
                         scratch=0.6)
    blade = G.steel('blade', color='#8f9295', rough=0.24, rust=0.1, blood=0.8, grime=0.45, seed=8, dents=0.05)
    spearhead = G.steel('spearhead', color='#6c6e71', rough=0.42, rust=0.45, blood=0.55, grime=0.85, seed=51, dents=0.1)
    ash = G.wood('ash', color='#5c4632', seed=48)
    wood = G.wood('wood')
    skin = G.skin('cleric_skin', '#94796a' if sex == 'male' else '#9e8476', windburn=0.35, dirt=0.6)
    if rev:
        glow_c, horn = '#b98cf0', M.emissive('lantern_horn_rev', '#8d63c4', 1.4)
        flame = M.emissive('lantern_flame_rev', '#d7b8ff', 30.0)
    else:
        glow_c, horn = '#ffb45a', M.emissive('lantern_horn', '#d4914a', 1.4)
        flame = M.emissive('lantern_flame', '#ffd394', 30.0)

    fig = K.root('figure')
    parts = []

    # ---------------------------------------------------------------- on the body: breeches, boots, hauberk, gloves
    parts.append(D.skin('cleric_body', skin))
    parts.append(D.layer('breeches', breech, lambda P: np.full(len(P), 0.0035, np.float32),
                         lambda P: np.maximum(D.heights(0.1, 1.0)(P), -D.arms(1.2)(P)), inner=0.002, tris=9000))

    def boot_t(P):
        cuff = np.exp(-((P[:, 2] - 0.34 * hf) / 0.022) ** 2)
        return (0.0058 + 0.005 * cuff).astype(np.float32)
    parts.append(D.layer('tallboots', boots, boot_t, lambda P: np.maximum(D.heights(-0.02, 0.36)(P), -D.arms(1.2)(P)),
                         inner=-0.0015, tris=8000, smooth=40))
    parts.append(D.layer('hauberk', mail, lambda P: np.full(len(P), 0.008, np.float32),
                         lambda P: np.maximum(D.heights(0.88, 1.545)(P), -D.hands(cuff=0.03)(P)),
                         inner=0.003, tris=14000, smooth=45))
    parts.append(D.layer('gloves', gloves, lambda P: np.full(len(P), 0.0032, np.float32), D.hands(cuff=0.045),
                         inner=0.002, tris=5000, smooth=45))
    # the hauberk's skirt, to the knee
    _, tf95, tb95 = (float(x) for x in fr.torso(0.95))
    hr = fr.hips() + 0.012
    sy = ((tf95 + tb95) / 2.0 + 0.012) / hr
    oy = (tb95 - tf95) / 2.0

    def ragged(i, a):
        return (0.0, (0.012 * math.sin(a * 9.0 + 1.1) + 0.006 * math.sin(a * 23.0)) if i == 0 else 0.0)
    sk = K.lathe('mail_skirt', [(hr + 0.035 + 0.4 * wdef, 0.53 * hf), (hr + 0.02 + 0.25 * wdef, 0.72 * hf),
                                (hr + 0.004, 0.9 * hf), (hr - 0.01, 1.0 * hf)],
                 mail, seg=48, sy=sy, loc=(0.0, oy, 0.0), cap_bottom=False, cap_top=False, jitter=ragged)
    A.solid(sk, 0.006)
    parts.append(sk)

    # ---------------------------------------------------------------- the surcoat, belted
    zb = (1.05 + 1.5 * wdef) * hf               # his at the hips, hers cinched at her natural waist
    front = GB.Drape(D, 1.5 * hf, 0.34 * hf, [-150.0 + 3.0 * k for k in range(41)], 0.022, rows=40, oy=0.01,
                     flare=0.035, folds=0.011, fold_n=11, ragged=0.022, seed=seed, arms=False, cinch=(zb, 0.021))
    back = GB.Drape(D, 1.5 * hf, 0.34 * hf, [30.0 + 3.0 * k for k in range(41)], 0.022, rows=40, oy=0.01,
                    flare=0.04, folds=0.012, fold_n=9, ragged=0.024, seed=seed + 1, arms=False, cinch=(zb, 0.021))
    parts.append(front.mesh('surcoat_front', surcoat, thick=0.005))
    parts.append(back.mesh('surcoat_back', surcoat, thick=0.005))
    if vet:      # patched, low on the front, in somebody else's cloth
        top, out = [], []
        for k in range(5):
            p, n = front.point(-112.0 + 7.0 * k, 0.78 * hf, lift=0.005)
            top.append(p)
            out.append(n)
        parts.append(A.cloth_panel('patch', top, out, 0.15 * hf, G.cloth('patch', color='#4a3a2a', blood=0.3, seed=55),
                                   rows=6, tatter=0.06, slits=0, fold=0.003, seed=seed + 4, thick=0.003))

    def girdle_point(a, z, lift):
        a = ((a + 180.0) % 360.0) - 180.0
        if -150.0 <= a <= -30.0:
            return front.point(a, z, lift=lift)
        if 30.0 <= a <= 150.0:
            return back.point(a, z, lift=lift)
        return D.on(a, z, 0.012 + lift)
    ring = [girdle_point(a, zb, 0.011)[0] for a in range(0, 360, 6)]
    parts.append(GB.cord('girdle', ring, 0.011, rope, closed=True))
    knot, kn = girdle_point(-62.0, zb, 0.02)
    for k, (dx, ln) in enumerate(((-0.012, 0.32), (0.014, 0.27))):
        pts = [knot + Vector((dx, 0.0, 0.0)) + kn * 0.004 + Vector((0.004 * math.sin(t * 5.0), -0.012 * t, -ln * t * hf))
               for t in np.linspace(0.0, 1.0, 7)]
        parts.append(GB.cord('girdle_end', pts, 0.0095, rope))
        parts.append(K.sphere('girdle_knot', tuple(pts[-1]), 0.016, rope, seg=10, rings=6))
    parts.append(K.sphere('girdle_tie', tuple(knot + kn * 0.006), 0.021, rope, scale=(1.3, 0.8, 1.0), seg=12, rings=8))

    # ---------------------------------------------------------------- the coif, pushed back into a collar
    collar = GB.Drape(D, 1.585 * hf, 1.415 * hf, [a * 5.0 for a in range(72)], 0.038, rows=12, oy=0.01,
                      collar=(0.1 * fr.head_scale + 0.012, 0.55), flare=0.012, folds=0.006, fold_n=13, ragged=0.008,
                      seed=seed + 2, closed=True)
    parts.append(collar.mesh('coif_collar', mail, thick=0.006))
    parts.append(A.torus('coif_roll', (0.0, 0.012, 1.572 * hf), 0.1 * fr.head_scale + 0.02, 0.024, mail, sy=0.94,
                         lumpy=0.35, rz=0.03, folds=0.005, seed=seed, rseg=12))

    # ---------------------------------------------------------------- satchel and book, hung from the girdle
    if not cmd:     # (the Commander leaves the satchel behind)
        sp_, sn_ = D.on(-6.0, zb - 0.1 * hf, 0.06)
        parts.append(GB.cord('satchel_cord', [girdle_point(-14.0, zb, 0.012)[0], sp_ + sn_ * 0.02 + Vector((0.0, 0.0, 0.08))],
                             0.005, leather))
        bag = K.rbox('satchel', (0.06, 0.2, 0.17), (0, 0, 0), leather, bev=0.02, segs=3)
        A.place(bag, sp_ + sn_ * 0.02, A.frame(sn_, back=(0.0, 0.0, 1.0)))
        parts.append(bag)
        flap = K.rbox('satchel_flap', (0.064, 0.205, 0.07), (0, 0, 0), leather, bev=0.012, segs=2)
        A.place(flap, sp_ + sn_ * 0.024 + Vector((0.0, 0.0, 0.055)), A.frame(sn_, back=(0.0, 0.0, 1.0)))
        parts.append(flap)
        parts.append(K.tube('saw_handle', sp_ + sn_ * 0.02 + Vector((0.0, 0.05, 0.08)),
                            sp_ + sn_ * 0.03 + Vector((0.0, 0.07, 0.16)), 0.011, 0.012, wood, seg=8))
    bk, bn = girdle_point(-122.0, zb - 0.1 * hf, 0.03)
    parts += GB.book('book', bk, bn, cover, pages, old_gilt)
    parts.append(GB.cord('book_strap', [girdle_point(-122.0, zb, 0.012)[0], bk + Vector((0.0, 0.0, 0.07))], 0.004,
                         leather))

    # ---------------------------------------------------------------- rank and relics
    if cmd:      # a tarnished gilt chain of office over the collar, its medallion on the breast
        chain = [collar.point(a, z, lift=0.006)[0] for a, z in
                 [(a, 1.5 * hf - 0.1 * hf * max(0.0, -math.sin(math.radians(a))) ** 2) for a in range(0, 360, 10)]]
        parts.append(GB.cord('chain', chain, 0.0055, old_gilt, closed=True))
        p, n = front.point(-90.0, 1.335 * hf, lift=0.008)
        disc = K.lathe('medallion', [(0.05, 0.0), (0.047, 0.009), (0.022, 0.016), (0.0, 0.017)], old_gilt, seg=28,
                       cap_bottom=True, cap_top=False)
        A.place(disc, p, A.frame(n, back=(0.0, 0.0, 1.0)))
        parts.append(disc)
    if vet:      # a dead man's spaulder, blackened; a reliquary on a chain
        blackened = G.steel('blackened', color='#3a3b3e', rust=0.3, blood=0.2, seed=4, edge=0.8)
        spaul = (f['deltoid'] + 0.025) / (M0.f['deltoid'] + 0.025)
        sh = Vector(fr.joints['sh_l']) + Vector((0.01, 0.0, 0.035 * hf))
        parts += A.pauldron('spaulder', sh, 1, blackened, old_gilt, size=1.05 * spaul, lames=2, seed=83)
        p, n = front.point(-78.0, 1.3 * hf, lift=0.018)
        box = K.rbox('reliquary', (0.05, 0.022, 0.064), (0, 0, 0), old_gilt, bev=0.006, segs=2)
        A.place(box, p, A.frame(n, back=(0.0, 0.0, 1.0)))
        parts.append(box)
        top_ = collar.point(-60.0, 1.44 * hf, lift=0.006)[0]
        parts.append(GB.cord('reliquary_chain', [top_, p + Vector((0.0, 0.0, 0.034))], 0.003, old_gilt))

    # ---------------------------------------------------------------- the lantern, the weapon
    if armed:
        parts += GB.lantern('lantern', Vector(fr.fist('l')), iron, horn, flame, glow_c, energy=2.4)
        if weapon == 'spear':
            parts += GB.boar_spear('spear', Vector(fr.fist('r')), (0.0, -0.02, 1.0), 2.02 * hf, ash, spearhead, leather,
                                   lugs=False)
        elif weapon == 'shortsword':
            parts += A.broadsword('sword', Vector(fr.fist('r')), SWORD_DIR, blade, iron, leather, brass, length=0.56,
                                  width=0.052)
        else:
            parts += K.mace('mace', Vector(fr.fist('r')), MACE_DIR, (head_steel, wood, leather), haft=0.5)

    # ---------------------------------------------------------------- the head
    head_c = Vector(H.translation)
    if head:
        if look is None:
            look = dict(LK.anchor(sex, commander=cmd, veteran=vet), seed=seed)
        hroot, _ = LK.build_head(look, gaze=16.0 if v.get('portrait') else 0.0,
                                 tag=None if look.get('anchor') else look['id'])
        hroot.matrix_world = H
        parts.append(hroot)
    if rev:
        parts.append(K.glow('face_glow', head_c + Vector((0.0, -0.105, 0.012)), '#b98cf0', 0.18, radius=0.012))

    # ---------------------------------------------------------------- the Commander's banner, over the surcoat
    if cmd:
        yb = back.point(90.0, 1.2 * hf, lift=0.03)[0].y
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
