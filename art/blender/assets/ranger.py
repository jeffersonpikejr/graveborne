"""RANGER — the Harrier. Asset #2: the company's eyes, and its second silhouette.

Brief (in the Line-Breaker's register): a lean, weathered skirmisher who lives out ahead of the column. At 26 px a
Ranger is the hood and a rain-dark cloak, then the longbow. The hood is worn low, its front out over the brow so the
eyes sit in its shadow and the jaw, the mouth and the beard carry the soldier; it comes with a capelet over the
shoulders, and the cloak hangs from under it to the calf, moss-dark wool gone black at the mud-soaked hem. No
plate: a quilted jack in dirty undyed wool, a scuffed leather jerkin laced over it, a leather bracer on the bow arm,
wrapped calves, soft boots, all laid over the wearer's own body (gb/garb.py), so his barrel chest and her waist and
hips show through.
A yew longbow nearly as tall as its archer, held upright in the bow hand so its whole arc shows; a spare arrow in the
other hand, low, the way the Fighter holds his blade; arrows in a back quiver whose fletchings (grey goose, the cock
feather oxblood: the company's colour) stand over the right shoulder; a long knife at the hip. Tarnished gold only as
a buckle.

Commander (any class; here on the Ranger): the banner strapped to the back (the quiver moves to the hip), the
founding scar, one mark of rank (a tarnished gilt cloak clasp), fewer loose pieces. Veteran (level 5, the double
shot): dead men's gear — a mail mantle under the capelet, a blackened steel bracer with gilt rivets, a patched cloak.
Revenant: the same kit drained to grave-grey, violet light in the cracks and the eyes.
Weapons: the bow, or (one Ranger in three rolls one) a boar spear held upright, with the quiver left behind.

Under the hood a head keeps what fits: the crown styles (topknot, bun, braided crown) flatten under it, hair keeps what
fits inside it or falls out through the opening, and a ponytail comes out under the jaw and forward over the shoulder
(add_head).
"""
import math

from mathutils import Matrix, Vector
import numpy as np

from gb import armor as A
from gb import body as BD
from gb import garb as GB
from gb import grit as G
from gb import kit as K
from gb import looks as LK
from gb import mat as M

FIG_SCALE = 0.6          # 1 m = 0.6 tile, as every humanoid

VARIANTS = {}
for _w in ('', '_spear'):
    for _t, _v in (('', {}), ('_commander', {'commander': True}), ('_veteran', {'veteran': True}),
                   ('_revenant', {'revenant': True}), ('_commander_revenant', {'commander': True, 'revenant': True})):
        for _f, _sex in (('m', 'male'), ('f', 'female')):
            VARIANTS[f'ranger{_w}{_t}_{_f}'] = dict(_v, sex=_sex, **({'weapon': 'spear'} if _w else {}))

BOW_TILT = 8.0           # the bow's top leans out this far from upright (degrees)
_LAST = {}               # sex -> the last build's capelet (add_head lays a ponytail on it)


def pose(sex, weapon='bow'):
    """The Ranger's body and pose: the bow held upright before the left hip, the forearm forward; or a boar spear
    upright in the right fist, its butt on the ground; or (None) the arms at rest, as the reference sheet stands."""
    fr = BD.Frame(sex)
    hf, f = fr.hf, fr.f
    if weapon == 'spear':
        fr.reach('r', (-(f['shoulder'] + 0.075), -0.2 * hf, 1.03 * hf), pole=(-0.45, 0.45, -1.0), grip=(0.0, 0.0, 1.0))
    elif weapon == 'bow':
        t = math.radians(BOW_TILT)
        fr.reach('l', (f['shoulder'] + 0.04, -0.285 * hf, 1.12 * hf), pole=(0.35, 0.3, -1.0),
                 grip=(math.sin(t), -0.05, math.cos(t)))
    return fr


def head_frame(sex, portrait=False):
    return BD.Frame(sex).head_frame(portrait)


def _tail_path(cape, H):
    """A ponytail under the hood, in head space: tied low behind the left ear, brought forward inside the hood along
    the neck and out of its opening under the jaw, then over the capelet on the left shoulder."""
    Hi = H.inverted()
    pts = [Vector((0.058, 0.05, -0.06)), Vector((0.085, 0.005, -0.125)), Vector((0.062, -0.05, -0.18))]
    zc = cape.Z
    for a, t, lift in ((-44.0, 0.0, 0.02), (-54.0, 0.28, 0.015), (-63.0, 0.6, 0.014), (-69.0, 0.9, 0.012)):
        z = float(zc[0] + (zc[-1] - zc[0]) * t) + (0.006 if t == 0.0 else 0.0)     # over the collar's edge, then down
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


def build(v, seed=7, turn=-4.0, look=None, head=True):
    """One variant (VARIANTS). look: a soldier's own face (gb/looks.py); by default the variant's anchor face.
    head=False leaves the head off, for the look pipeline (render.py --looks) to seat each look's head."""
    sex = v.get('sex', 'male')
    rev, cmd, vet = v.get('revenant', False), v.get('commander', False), v.get('veteran', False)
    spear = v.get('weapon') == 'spear'
    armed = v.get('armed', True)
    M.set_mode(revenant=rev)
    fr = pose(sex, ('spear' if spear else 'bow') if armed else None)
    hf, f = fr.hf, fr.f
    D = GB.dressed(fr)
    H = fr.head_frame(v.get('portrait') or v.get('level'))
    s_head = fr.head_scale
    M0 = BD.Frame('male')
    wdef = (fr.hips() - float(fr.torso(1.17)[0])) - (M0.hips() - float(M0.torso(1.17)[0]))

    # ---------------------------------------------------------------- materials
    wool = G.cloth('ranger_wool', color='#384030', blood=0.12, mud=1.9, grime=0.75, seed=31)
    jackc = G.cloth('jack', color='#6b5d47', blood=0.28, mud=1.3, grime=0.65, seed=33)
    breech = G.cloth('breeches', color='#2c2924', blood=0.1, mud=1.6, seed=37)
    wrapc = G.cloth('wraps', color='#575141', blood=0.05, mud=2.4, seed=39)
    jerk = G.leather('jerkin', color='#271b13', seed=35)
    boots = G.leather('boots', color='#2b2017', mud=2.4, seed=12)
    gloves = G.leather('gloves', color='#2e2219', seed=41)
    bracer_l = G.leather('bracer', color='#4d3825', seed=43)
    leather = G.leather('leather')
    quiv = G.leather('quiver', color='#3a281b', seed=49)
    brass = G.brass('brass')
    old_gilt = G.brass('old_gilt', color='#4c3b1c', tarnish=1.0, blood=0.25, seed=14, film=0.6)
    yew = G.wood('yew', color='#6d4526', seed=45)
    horn = G.wood('horn', color='#8f8671', seed=46)
    string = G.flat('bowstring', '#b3a88c')
    shaft = G.wood('shaft', color='#86704f', seed=47)
    ash = G.wood('ash', color='#5c4632', seed=48)
    point = G.steel('arrowhead', color='#3a3b3e', rust=0.5, blood=0.4, seed=52, edge=0.6)
    grey = G.cloth('fletch', color='#8d897e', blood=0.0, mud=0.0, grime=0.2, seed=53)
    oxf = G.cloth('fletch_ox', color='#5a1613', blood=0.0, mud=0.0, grime=0.2, seed=54)
    blade = G.steel('blade', color='#8f9295', rough=0.24, rust=0.1, blood=0.8, grime=0.45, seed=8, dents=0.05)
    spearhead = G.steel('spearhead', color='#6c6e71', rough=0.42, rust=0.45, blood=0.55, grime=0.85, seed=51, dents=0.1)
    wood = G.wood('wood')
    skin = G.skin('ranger_skin', '#94796a' if sex == 'male' else '#9e8476', windburn=0.35, dirt=0.6)

    fig = K.root('figure')
    parts = []

    # ---------------------------------------------------------------- clothes on the body
    hands = D.hands(cuff=0.012)
    no_hands = lambda P: -hands(P)                                              # noqa: E731
    parts.append(D.skin('ranger_body', skin))
    parts.append(D.layer('breeches', breech, lambda P: np.full(len(P), 0.0035, np.float32),
                         lambda P: np.maximum(D.heights(0.1, 1.0)(P), -D.arms(1.2)(P)), inner=0.002, tris=9000))
    parts.append(D.layer('wraps', wrapc, GB.wraps(fr), lambda P: np.maximum(D.heights(0.14, 0.45)(P), -D.arms(1.2)(P)),
                         inner=-0.0015, feather=0.002, floor=0.9, tris=7000))

    def boot_t(P):
        cuff = np.exp(-((P[:, 2] - 0.19 * hf) / 0.018) ** 2)
        return (0.0055 + 0.0045 * cuff).astype(np.float32)
    parts.append(D.layer('boots', boots, boot_t, lambda P: np.maximum(D.heights(-0.02, 0.205)(P), -D.arms(1.2)(P)),
                         inner=-0.001, tris=7000, smooth=40))
    parts.append(D.layer('jack', jackc, GB.quilted(fr), lambda P: np.maximum(D.heights(0.86, 1.545)(P), no_hands(P)),
                         inner=0.003, tris=14000, smooth=45))

    def jerkin_region(P):
        r = np.maximum(D.heights(0.9, 1.5)(P), D.trunk(0.004)(P))
        lace = np.maximum(np.abs(P[:, 0]) - 0.011, np.maximum(P[:, 1], 1.22 * hf - P[:, 2]))    # laced at the front
        return np.maximum(r, -lace)
    parts.append(D.layer('jerkin', jerk, lambda P: np.full(len(P), 0.0165, np.float32), jerkin_region,
                         inner=-0.0095, feather=0.002, floor=0.9, tris=9000, smooth=40))
    parts.append(D.layer('gloves', gloves, lambda P: np.full(len(P), 0.0032, np.float32), D.hands(cuff=0.04),
                         inner=0.002, tris=5000, smooth=45))
    if vet:      # a dead man's steel bracer, gilt-riveted
        bmat = G.steel('blackened', color='#3a3b3e', rust=0.3, blood=0.2, seed=4, edge=0.8)
    else:
        bmat = bracer_l
    parts.append(D.layer('bracer_vet' if vet else 'bracer', bmat, lambda P: np.full(len(P), 0.015, np.float32),
                         D.forearm('l', 0.38, 0.93, radius=0.09), inner=-0.006, feather=0.0015, floor=0.95,
                         tris=3000, smooth=35))
    if vet:
        el, wr = fr.joints['el_l'], fr.joints['wr_l']
        u = (wr - el) / np.linalg.norm(wr - el)
        o = np.cross(u, (0.0, 0.0, 1.0))
        o = o / np.linalg.norm(o)
        o2 = np.cross(u, o)
        rp = []
        for tt in (0.45, 0.62, 0.8):
            c = el + (wr - el) * tt
            for ang in (0.0, 2.1, 4.2):
                rp.append(Vector(c + (o * math.cos(ang) + o2 * math.sin(ang)) * (f['arm'][2] * 0.8 + 0.017)))
        parts.append(A.rivets('bracer_rivets', rp, 0.004, old_gilt))

    # the jack's skirt, split front and back, quilted, flaring over the hips
    _, tf95, tb95 = (float(x) for x in fr.torso(0.95))
    hr = fr.hips() + 0.014
    sy = ((tf95 + tb95) / 2.0 + 0.014) / hr
    oy = (tb95 - tf95) / 2.0

    def skirt_j(i, a):
        return (-0.0035 * math.exp(-(math.sin(a * 13.0) / 0.3) ** 2) + 0.004 * math.sin(a * 5.0 + i), 0.0)
    for arc in ((-84.0, 84.0), (96.0, 264.0)):
        sk = K.lathe('jack_skirt', [(hr + 0.03 + 0.4 * wdef, 0.64 * hf), (hr + 0.014 + 0.25 * wdef, 0.78 * hf),
                                    (hr, 0.9 * hf), (hr - 0.012, 0.985 * hf)],
                     jackc, seg=24, sy=sy, loc=(0.0, oy, 0.0), arc=arc, cap_bottom=False, cap_top=False, jitter=skirt_j)
        A.solid(sk, 0.008)
        K.subsurf(sk, 1)
        parts.append(sk)

    # ---------------------------------------------------------------- belt, knife, pouch
    zb = (1.05 + 1.5 * wdef) * hf               # his at the hips, hers cinched at her waist
    bp, bn = D.ring(zb, 0.0175, n=56)
    parts += A.strap('belt', bp, bn, 0.042, 0.007, leather, brass, rivet_every=0.12, closed=True)
    front = min(range(len(bp)), key=lambda i: bp[i].y)
    parts.append(K.rbox('buckle', (0.05, 0.012, 0.055), (bp[front].x - 0.03, bp[front].y - 0.01, zb), old_gilt, bev=0.005))
    kp, kn = D.on(-128.0, zb, 0.03)
    parts += GB.long_knife('knife', kp + kn * 0.012 + Vector((0.0, 0.0, 0.012)), (-0.12, -0.22, -1.0), leather, wood,
                           blade, brass)
    if not cmd:
        pp, pn = D.on(-42.0, zb - 0.05 * hf, 0.03)
        rot = Matrix.Rotation(math.atan2(pn.y, pn.x) + math.pi / 2, 4, 'Z')
        parts.append(K.rbox('pouch', (0.075, 0.046, 0.085), (0, 0, 0), leather, rot=rot, bev=0.012, segs=2))
        parts[-1].location = pp + pn * 0.024
        parts.append(K.rbox('flap', (0.08, 0.052, 0.03), (0, 0, 0), leather, rot=rot, bev=0.008, segs=2))
        parts[-1].location = pp + pn * 0.026 + Vector((0.0, 0.0, 0.035))

    # ---------------------------------------------------------------- capelet, hood, cloak
    ztop = 1.58 * hf               # the collar rises round the hood's neck, just under the chin
    collar = 0.1 * s_head + 0.012
    cape = GB.Drape(D, ztop, 1.27 * hf, [a * 5.0 for a in range(72)], 0.044, rows=20, oy=0.02,
                    collar=(collar, 0.5), flare=0.03, folds=0.01, fold_n=9, ragged=0.014, seed=seed, closed=True,
                    hem=lambda a: 0.055 * hf * max(0.0, -math.sin(math.radians(a))) ** 1.5)     # shorter in front
    parts.append(cape.mesh('capelet', wool, thick=0.006))
    if vet:      # a mail mantle under it, showing below its hem
        mant = GB.Drape(D, ztop - 0.006, 1.17 * hf, [a * 5.0 for a in range(72)], 0.03, rows=22, oy=0.02,
                        collar=(0.1 * s_head + 0.0095, 0.5), flare=0.012, folds=0.004, fold_n=9, ragged=0.008,
                        seed=seed + 3, closed=True)
        parts.append(mant.mesh('mantle', G.maille('maille'), thick=0.005))
    z_bot = (Vector(H.inverted() @ Vector((0.0, 0.02, ztop))).z) - 0.03
    parts.append(GB.hood('hood', H, z_bot, wool, seed=seed))
    cloak = GB.Drape(D, 1.4 * hf, 0.36 * hf, [8.0 + 164.0 * k / 40 for k in range(41)], 0.03, rows=30, oy=0.02,
                     flare=0.19, folds=0.022, fold_n=7, ragged=0.035, seed=seed + 1)
    parts.append(cloak.mesh('cloak', wool, thick=0.006))
    if vet:      # patched: a square of somebody else's cloth on the left flank
        top, out = [], []
        for k in range(5):
            a = 16.0 + 14.0 * k / 4
            p, n = cloak.point(a, 0.86 * hf, lift=0.006)
            top.append(p)
            out.append(n)
        parts.append(A.cloth_panel('patch', top, out, 0.17 * hf, G.cloth('patch', color='#4c2a1d', blood=0.2, seed=55),
                                   rows=6, tatter=0.05, slits=0, fold=0.003, seed=seed + 4, thick=0.003))
    _LAST[sex] = {'cape': cape}

    # ---------------------------------------------------------------- the quiver, its strap
    if armed and not spear and not cmd:
        B = cloak.point(66.0, 0.99 * hf, lift=0.05)[0]
        T = cape.point(122.0, 1.44 * hf, lift=0.055)[0]
        parts += GB.quiver('quiver', B, T, quiv, leather, grey, oxf, shaft, point, n=12, seed=seed)
        knots = [(122.0, 1.43), (150.0, 1.47), (180.0, 1.5), (-150.0, 1.5), (-122.0, 1.46), (-104.0, 1.38),
                 (-90.0, 1.3), (-78.0, 1.2), (-66.0, 1.1), (-56.0, 1.0)]
        sp, sn = [], []
        for (a0, z0), (a1, z1) in zip(knots[:-1], knots[1:]):
            da = ((a1 - a0 + 180.0) % 360.0) - 180.0
            for k in range(4):
                a, z = a0 + da * k / 4, (z0 + (z1 - z0) * k / 4) * hf
                if z > 1.275 * hf:
                    p, n = cape.point(a, z, lift=0.004)
                else:
                    p, n = D.on(a, z, 0.019)
                sp.append(p)
                sn.append(n)
        parts += A.strap('quiver_strap', sp, sn, 0.03, 0.005, leather, old_gilt, rivet_every=0.2)
    if armed and not spear and cmd:     # the Commander carries the banner on the back: the quiver rides the hip
        B = D.on(200.0, 0.62 * hf, 0.07)[0] + Vector((0.0, 0.03, 0.0))
        T = D.on(192.0, 1.04 * hf, 0.08)[0] + Vector((0.0, -0.02, 0.0))
        parts += GB.quiver('quiver', B, T, quiv, leather, grey, oxf, shaft, point, n=9, r_top=0.045, r_bot=0.034,
                           seed=seed)

    # ---------------------------------------------------------------- the bow, the spare arrow, or the spear
    if armed and not spear:
        t = math.radians(BOW_TILT)
        up = Vector((math.sin(t), -0.05, math.cos(t))).normalized()
        side = Vector((-math.cos(math.radians(20.0)), math.sin(math.radians(20.0)), 0.0))
        bp_, _, _ = GB.longbow('bow', Vector(fr.fist('l')), up, side, 1.8 * hf, yew, leather, horn, string)
        parts += bp_
        wr, el = fr.joints['wr_r'], fr.joints['el_r']
        hd = Vector((wr - el) / np.linalg.norm(wr - el))
        hand = Vector(wr) + hd * f['hand'][0] * 0.45
        d = Vector((0.06, -0.5, -0.86)).normalized()
        parts += GB.arrow('spare', hand - d * 0.16, d, grey, oxf, shaft, point)
    if armed and spear:
        parts += GB.boar_spear('spear', Vector(fr.fist('r')), (0.0, -0.02, 1.0), 2.08 * hf, ash, spearhead, leather)

    # ---------------------------------------------------------------- rank: the clasp
    if cmd:
        p, n = cape.point(-90.0, ztop - 0.045 * hf, lift=0.004)
        disc = K.lathe('clasp', [(0.037, 0.0), (0.034, 0.008), (0.014, 0.013), (0.0, 0.014)], old_gilt, seg=24,
                       cap_bottom=True, cap_top=False)
        A.place(disc, p, A.frame(n, back=(0.0, 0.0, 1.0)))
        parts.append(disc)
        parts.append(A.torus('clasp_ring', (0.0, 0.0, 0.0), 0.037, 0.0055, old_gilt, seg=24, rseg=8))
        A.place(parts[-1], p + n * 0.003, A.frame(n, back=(0.0, 0.0, 1.0)))

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

    # ---------------------------------------------------------------- the Commander's banner, over the cloak
    if cmd:
        yb = cloak.point(90.0, 1.2 * hf, lift=0.03)[0].y
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
