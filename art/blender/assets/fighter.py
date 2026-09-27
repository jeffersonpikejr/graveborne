"""FIGHTER — the Line-Breaker. Asset #1 and the style anchor.

Brief: a broad, planted human mercenary built like a siege wedge, square to the viewer in battered half-plate over
dark maille; every layer heavy, practical, inherited from dead campaigns. The shield is the key silhouette:
large, bone-white, scraped down to dull steel and old oxblood smears. Tarnished gold only as rivets, repairs and
mismatched trim, never ornament. Bareheaded: windburned, stubborn, unimpressed by terror.

Commander (any class; here on the Fighter): the company banner strapped to the back, one tarnished mark of rank
(a gilt gorget), a founding scar across the face, gear repaired into biography, fewer loose pieces.
Veteran: assembled from dead men's armour — a foreign gilt pauldron, a mismatched greave, a patched cuirass.

Every model comes in male and female forms. Modelled in metres; FIG_SCALE converts to tiles.
"""
import math

from mathutils import Matrix, Vector

from gb import armor as A
from gb import grit as G
from gb import kit as K
from gb import looks as LK
from gb import mat as M

FIG_SCALE = 0.6          # 1 m = 0.6 tile: a 1.85 m mercenary stands ~1.1 tiles tall
HEAD_SCALE = 1.08        # heads a touch large, so faces read on the board
HEAD_TILT = -10.0        # chin up: unflinching, and it turns the face toward the camera

VARIANTS = {
    'fighter_m':                    {'sex': 'male'},
    'fighter_f':                    {'sex': 'female'},
    'fighter_commander_m':          {'sex': 'male', 'commander': True},
    'fighter_commander_f':          {'sex': 'female', 'commander': True},
    'fighter_veteran_m':            {'sex': 'male', 'veteran': True},
    'fighter_veteran_f':            {'sex': 'female', 'veteran': True},
    'fighter_revenant_m':           {'sex': 'male', 'revenant': True},
    'fighter_revenant_f':           {'sex': 'female', 'revenant': True},
    'fighter_commander_revenant_m': {'sex': 'male', 'commander': True, 'revenant': True},
    'fighter_commander_revenant_f': {'sex': 'female', 'commander': True, 'revenant': True},
}

BODY = {   # a siege wedge: broad through the shoulders and chest, heavy in the legs, planted wide (the faces: gb/looks.py)
    'male':   dict(hf=1.0, sh=0.272, chest=0.25, waist=0.206, sy=0.64, neck=0.08, bust=0.0, bulk=1.0),
    'female': dict(hf=0.965, sh=0.25, chest=0.233, waist=0.188, sy=0.66, neck=0.066, bust=0.03, bulk=0.94),
}


def head_frame(sex, portrait=False):
    """Where the head sits on the figure (figure space): on the neck, chin a touch up in battle, level in portraits."""
    return (Matrix.Translation(Vector((0.0, -0.012, 1.715 * BODY[sex]['hf'])))
            @ Matrix.Rotation(math.radians(0.0 if portrait else HEAD_TILT), 4, 'X') @ Matrix.Scale(HEAD_SCALE, 4))


def add_head(fig, look, sex, portrait=False):
    """Seat a look's head (gb/looks.py) on a figure built with head=False; returns the head's root."""
    hroot, _ = LK.build_head(look, gaze=16.0 if portrait else 0.0, tag=None if look.get('anchor') else look['id'])
    hroot.matrix_basis = head_frame(sex, portrait)
    hroot.parent = fig
    return hroot


def build(v, seed=7, turn=-4.0, look=None, head=True):
    """One variant (VARIANTS). look: a soldier's own face from gb/looks.py; by default the variant's anchor face (the
    Commander's founding scar, the Veteran's broken nose and greying beard). head=False leaves the head off, for the
    look pipeline to seat each look's head on one built body (render.py --looks)."""
    sex = v.get('sex', 'male')
    rev, cmd, vet = v.get('revenant', False), v.get('commander', False), v.get('veteran', False)
    M.set_mode(revenant=rev)
    Bd = BODY[sex]
    hf = Bd['hf']

    def V(x, y, z):
        return Vector((x, y, z * hf))

    head_c = V(0.0, -0.012, 1.715)

    # ---------------------------------------------------------------- materials
    plate = G.steel('plate', rust=0.4, blood=0.38, seed=1)
    lames = G.steel('lames', color='#5a5c5e', rust=0.5, blood=0.42, seed=2)
    blackened = G.steel('blackened', color='#3a3b3e', rust=0.3, blood=0.2, seed=4, edge=0.8)
    iron = G.steel('iron', color='#2c2d2f', rust=0.6, blood=0.3, seed=6, edge=0.35, scratch=0.6, dirt=0.7)
    blade = G.steel('blade', color='#8f9295', rough=0.24, rust=0.1, blood=0.8, grime=0.45, seed=8, dents=0.05)
    mail = G.maille('maille')
    brass = G.brass('brass')
    old_gilt = G.brass('old_gilt', color='#4c3b1c', tarnish=1.0, blood=0.25, seed=14, film=0.6)   # dead men's gold: dark, worn
    leather = G.leather('leather')
    boots = G.leather('boots', color='#2b2017', mud=2.4, seed=12)
    hose = G.cloth('hose', color='#2a2622', blood=0.1, seed=10)
    ox = G.cloth('oxblood', blood=0.5, seed=9)
    shield_face = G.paint_over_steel('shield_face', chip=0.6, blood=0.85)
    wood = G.wood('wood')

    fig = K.root('figure')
    parts = []

    # ---------------------------------------------------------------- legs: cuisses, poleyns, greaves, boots
    k_ = Bd['bulk']
    legs = ((V(0.116, 0.0, 0.97), V(0.19, -0.035, 0.52), V(0.228, 0.0, 0.12), 1),
            (V(-0.116, 0.0, 0.97), V(-0.184, -0.04, 0.52), V(-0.222, 0.0, 0.12), -1))
    for hip, knee, ank, s in legs:
        parts.append(K.skin_chain('leg', [hip, knee, ank], [0.114 * k_, 0.082 * k_, 0.064 * k_], hose))
        d = (knee - hip).normalized()
        parts.append(A.shell('cuisse', hip + d * 0.07, knee - d * 0.05,
                             [(0.128 * k_, 0.0), (0.12 * k_, 0.5), (0.102 * k_, 1.0)],
                             plate, arc=(-172.0, -8.0), dent=0.004, seed=11 + s))
        parts += A.cop('poleyn', knee + Vector((0.0, -0.085, 0.0)), (s * 0.12, -1.0, 0.05), (s, 0.15, 0.0), plate,
                       brass, r=0.086 * k_, seed=3 + s)
        dg = (ank - knee).normalized()
        parts.append(A.shell('greave', knee + dg * 0.07, ank + Vector((0.0, 0.0, 0.035)),
                             [(0.094 * k_, 0.0), (0.099 * k_, 0.3), (0.082 * k_, 0.78), (0.075 * k_, 1.0)],
                             blackened if (vet and s < 0) else lames, seg=30, dent=0.005, seed=21 + s))
        if vet and s < 0:          # the mismatched greave came with a dead man's gilt trim
            parts.append(A.rivets('greave_trim', A.shell_rim_points(knee + dg * 0.07, ank + Vector((0, 0, 0.035)),
                                                                     0.09, 0.02, None, 14), 0.006, brass))
        toe = Vector((s * 0.026, -0.215, -0.078))
        parts.append(K.skin_chain('boot', [ank + Vector((0.0, 0.0, 0.05)), ank + Vector((0.0, -0.012, -0.035)),
                                           ank + Vector((s * 0.013, -0.125, -0.07)), ank + toe],
                                  [0.076 * k_, 0.074 * k_, 0.064 * k_, 0.05 * k_], boots))
        for k in range(2):             # sabaton lames over the instep
            a0 = ank + Vector((s * 0.006 * k, -0.045 - 0.045 * k, -0.012 - 0.02 * k))
            parts.append(A.shell('sabaton', a0, a0 + Vector((s * 0.004, -0.05, -0.018)), [(0.064, 0.0), (0.06, 1.0)],
                                 lames, arc=(10.0, 170.0), seg=18, lip=0.003, back=(0.0, 0.0, 1.0), seed=31 + k))

    # ---------------------------------------------------------------- maille skirt, faulds, tassets
    def ragged(i, a):
        return (0.0, 0.03 * math.sin(a * 9.0 + 1.1) * (1.0 if i == 0 else 0.0) + (0.012 * math.sin(a * 23.0) if i == 0 else 0.0))
    parts.append(K.lathe('skirt', [(0.242, 0.68 * hf), (0.234, 0.74 * hf), (0.217, 0.88 * hf), (0.206, 0.99 * hf)],
                         mail, seg=48, sy=0.8, cap_bottom=False, cap_top=False, jitter=ragged))
    W = Bd['waist']
    for k, (z0, z1) in enumerate(((0.99, 1.04), (0.945, 0.995))):
        r = W + 0.022 + 0.01 * k
        band = K.lathe('fauld', [(r + 0.008, z0 * hf), (r, z1 * hf)], lames, seg=40, sy=Bd['sy'] + 0.1,
                       arc=(-205.0, 25.0), cap_bottom=False, cap_top=False)
        A.solid(band, 0.005)
        parts.append(band)
        parts.append(A.rivets('fauld_r', [Vector(((r + 0.012) * math.cos(math.radians(a)), (r + 0.012) * math.sin(math.radians(a)) * (Bd['sy'] + 0.1), (z0 + 0.012) * hf))
                                          for a in range(-195, 20, 23)], 0.006, brass))
    for hip, knee, _, s in legs:
        d = (knee - hip).normalized()
        base = hip + Vector((s * 0.01, -0.0, -0.035))
        for k in range(3):
            t0 = 0.12 * k
            parts.append(A.shell('tasset', base + d * t0, base + d * (t0 + 0.14), [(0.132 + 0.006 * k, 0.0), (0.14 + 0.006 * k, 1.0)],
                                 lames, arc=(-150.0 + s * 12.0, -30.0 + s * 12.0), seg=24, dent=0.004, seed=41 + k + s))

    # ---------------------------------------------------------------- cuirass, plackart
    C = Bd['chest']
    prof = [(W, 1.03), (W + 0.008, 1.1), ((W + C) / 2 + 0.006, 1.18), (C - 0.004, 1.27), (C, 1.35), (C - 0.006, 1.42),
            (C - 0.028, 1.47), (C - 0.07, 1.505), (0.136, 1.53)]     # closes in to the collar: no open neckline
    zs = [z for _, z in prof]

    def keel(a):
        return math.exp(-((a + math.pi / 2) / 0.22) ** 2)

    def cuirass_j(i, a):
        z = zs[i]
        dr = 0.022 * keel(a) * (1.0 if 0 < i < len(prof) - 1 else 0.4)
        dr += Bd['bust'] * math.exp(-((a + math.pi / 2) / 0.75) ** 2) * math.exp(-((z - 1.31) / 0.06) ** 2)
        dr += 0.004 * math.sin(a * 5.0 + i * 1.7) * math.sin(a * 3.0 + 0.4)     # dents
        return (dr, 0.0)
    cu = K.lathe('cuirass', [(r, z * hf) for r, z in prof], plate, seg=56, sy=Bd['sy'], cap_bottom=False,
                 cap_top=False, jitter=cuirass_j)
    A.solid(cu, 0.006)
    K.subsurf(cu, 1)
    parts.append(cu)

    def plack_j(i, a):
        return (0.02 * keel(a), 0.075 * math.exp(-((a + math.pi / 2) / 0.4) ** 2) if i == 2 else 0.0)
    pl = K.lathe('plackart', [(W + 0.014, 1.025 * hf), (W + 0.02, 1.1 * hf), ((W + C) / 2 + 0.024, 1.17 * hf)], lames,
                 seg=40, sy=Bd['sy'], arc=(-155.0, -25.0), cap_bottom=False, cap_top=False, jitter=plack_j)
    A.solid(pl, 0.006)
    K.subsurf(pl, 1)
    parts.append(pl)

    def on_cuirass(a_deg, z, lift=0.012):
        """A point on the cuirass (with its keel) and the outward normal there — where straps lie."""
        a = math.radians(a_deg)
        zz = z / hf
        for j in range(len(zs) - 1):
            if zs[j] <= zz <= zs[j + 1]:
                t = (zz - zs[j]) / (zs[j + 1] - zs[j])
                r = prof[j][0] * (1 - t) + prof[j + 1][0] * t
                break
        else:
            r = prof[-1][0] if zz > zs[-1] else prof[0][0]
        r += 0.022 * keel(a)
        n = Vector((math.cos(a) * Bd['sy'], math.sin(a), 0.0)).normalized()
        return Vector((r * math.cos(a), r * math.sin(a) * Bd['sy'], z)) + n * lift, n

    if vet:    # a patch riveted over a breach, in a different steel
        patch = K.lathe('patch', [(C + 0.009, 1.27 * hf), (C + 0.011, 1.38 * hf)], blackened, seg=12, sy=Bd['sy'],
                        arc=(-140.0, -112.0), cap_bottom=False, cap_top=False)
        A.solid(patch, 0.004)
        parts.append(patch)
        parts.append(A.rivets('patch_r', [on_cuirass(a, z * hf, 0.016)[0] for a in (-138, -126, -114)
                                          for z in (1.28, 1.37)], 0.006, brass))

    # ---------------------------------------------------------------- belts, baldric, pouches
    def ring_path(z_of_a, rx, ry, n=44):
        pts, nrm = [], []
        for k in range(n):
            a = 2 * math.pi * k / n
            pts.append(Vector((rx * math.cos(a), ry * math.sin(a), z_of_a(a))))
            nrm.append(Vector((math.cos(a) / rx, math.sin(a) / ry, 0.0)))
        return pts, nrm
    rx = W + 0.04
    bp, bn = ring_path(lambda a: 1.05 * hf, rx, rx * (Bd['sy'] + 0.12))
    parts += A.strap('belt', bp, bn, 0.056, 0.009, leather, brass, rivet_every=0.1, closed=True)
    parts.append(K.rbox('buckle', (0.062, 0.014, 0.068), (-0.035, -rx * (Bd['sy'] + 0.12) - 0.012, 1.05 * hf), brass, bev=0.006))
    if not cmd:
        rx2 = W + 0.055
        sp, sn = ring_path(lambda a: (0.985 + 0.04 * math.cos(a)) * hf, rx2, rx2 * (Bd['sy'] + 0.16))
        parts += A.strap('swordbelt', sp, sn, 0.045, 0.008, leather, brass, rivet_every=0.12, closed=True)
        for ang, zz in ((-160.0, 0.95), (-25.0, 1.0)):     # pouches hang off the hip
            a = math.radians(ang)
            p = Vector((rx2 * 1.04 * math.cos(a), rx2 * (Bd['sy'] + 0.16) * 1.04 * math.sin(a), zz * hf - 0.04))
            rot = Matrix.Rotation(a + math.pi / 2, 4, 'Z')
            parts.append(K.rbox('pouch', (0.085, 0.052, 0.095), (0, 0, 0), leather, rot=rot, bev=0.012, segs=2))
            parts[-1].location = p
            parts.append(K.rbox('flap', (0.09, 0.058, 0.035), (0, 0, 0), leather, rot=rot, bev=0.008, segs=2))
            parts[-1].location = p + Vector((0, 0, 0.035))

    def diagonal(a0, a1, z0, z1, n=18):
        pts, nrm = [], []
        for k in range(n):
            t = k / (n - 1)
            p, nn = on_cuirass(a0 + (a1 - a0) * t, (z0 + (z1 - z0) * t) * hf, 0.014)
            pts.append(p)
            nrm.append(nn)
        return pts, nrm
    dp, dn = diagonal(-128.0, -38.0, 1.47, 1.07)
    parts += A.strap('baldric', dp, dn, 0.05, 0.008, leather, brass, rivet_every=0.08)
    if cmd:    # the banner harness crosses the baldric
        hp, hn = diagonal(-52.0, -142.0, 1.47, 1.08)
        parts += A.strap('harness', hp, hn, 0.045, 0.008, leather, brass, rivet_every=0.09)

    # ---------------------------------------------------------------- tabard: torn oxblood panels
    def panel(a0, a1, cols, length, tatter, slits, sd):
        top, out = [], []
        for k in range(cols):
            a = math.radians(a0 + (a1 - a0) * k / (cols - 1))
            r = W + 0.07
            top.append(Vector((r * math.cos(a), r * math.sin(a) * (Bd['sy'] + 0.18), 1.03 * hf)))
            out.append(Vector((math.cos(a), math.sin(a), 0.0)))
        return A.cloth_panel('tabard', top, out, length * hf, ox, rows=16, tatter=tatter, slits=slits,
                             fold=0.014, bulge=lambda t: 0.07 * math.sin(math.pi * min(t, 0.55) / 1.1), seed=sd)
    tatter = 0.18 if cmd else 0.38
    parts.append(panel(-122.0, -58.0, 9, 0.64, tatter, 1 if cmd else 3, seed))
    parts.append(panel(-162.0, -138.0, 4, 0.5, tatter, 0, seed + 1))
    parts.append(panel(-42.0, -18.0, 4, 0.5, tatter, 0, seed + 2))

    # ---------------------------------------------------------------- collar, scarf, rank
    parts.append(A.shell('collar', V(0.0, 0.0, 1.47), V(0.0, -0.005, 1.555), [(0.13, 0.0), (0.108, 0.5), (0.095, 1.0)],
                         plate, seg=32, lip=0.004, thick=0.005))
    # the scarf: oxblood wool wound round the neck like a cowl, bunched at the throat, clear of the jaw
    parts.append(A.torus('scarf', V(0.0, -0.004, 1.575), 0.088, 0.023, ox, sy=0.95, lumpy=0.4, rz=0.034, folds=0.006,
                         seed=seed, rseg=14))
    parts.append(A.torus('scarf2', V(0.002, -0.01, 1.54), 0.108, 0.024, ox, sy=0.9, lumpy=0.45, rz=0.036,
                         folds=0.006, seed=seed + 3, rseg=14))
    parts.append(A.torus('scarf3', V(0.004, -0.014, 1.508), 0.124, 0.018, ox, sy=0.84, lumpy=0.45, rz=0.03,
                         folds=0.006, seed=seed + 5, rseg=14))
    if cmd:    # one tarnished mark of rank: a gilt gorget on the breast, the company's roundel at its centre
        gg = K.lathe('gorget', [(C + 0.004, 1.43 * hf), (C - 0.026, 1.475 * hf)], old_gilt, seg=24,
                     sy=Bd['sy'] + 0.06, arc=(-128.0, -52.0), cap_bottom=False, cap_top=False)
        A.solid(gg, 0.005)
        parts.append(gg)
        c0, nn = on_cuirass(-90.0, 1.448 * hf, 0.022)
        disc = K.lathe('rank', [(0.028, 0.0), (0.026, 0.006), (0.0, 0.009)], old_gilt, seg=24, cap_bottom=True,
                       cap_top=False)
        A.place(disc, c0, A.frame(nn, back=(0.0, 0.0, 1.0)))
        parts.append(disc)
    else:      # the scarf's loose end hangs over the breastplate
        top, out = [], []
        for k in range(4):
            top.append(V(0.03 + 0.02 * k, -0.122 - 0.004 * k, 1.515))
            out.append(Vector((0.0, -1.0, 0.0)))
        parts.append(A.cloth_panel('scarf_end', top, out, 0.24 * hf, ox, rows=10, tatter=0.3, slits=0, fold=0.008,
                                   bulge=lambda t: 0.045 * math.sin(math.pi * t * 0.9), seed=seed + 5))

    # ---------------------------------------------------------------- arms
    sh = Bd['sh']
    arm_r = (V(-sh, 0.0, 1.455), V(-sh - 0.055, -0.01, 1.17), V(-sh - 0.065, -0.12, 0.945))
    arm_l = (V(sh, 0.0, 1.455), V(sh + 0.1, 0.03, 1.2), V(sh + 0.05, -0.2, 1.105))
    for (a, b, c), s in ((arm_r, -1), (arm_l, 1)):
        parts.append(K.skin_chain('arm', [a, b, c], [0.08 * k_, 0.066 * k_, 0.055 * k_], mail))
        u = (b - a).normalized()
        parts.append(A.shell('rerebrace', a + u * 0.14, b - u * 0.035, [(0.08 * k_, 0.0), (0.073 * k_, 1.0)], lames,
                             seg=24, dent=0.003, seed=51 + s))
        parts += A.cop('couter', b, (s * 0.55, 0.8, 0.1), (s, -0.2, 0.0), plate, brass, r=0.066 * k_, seed=61 + s)
        f = (c - b).normalized()
        parts.append(A.shell('vambrace', b + f * 0.05, c - f * 0.015, [(0.072 * k_, 0.0), (0.06 * k_, 1.0)], plate,
                             seg=24, dent=0.003, seed=71 + s))
        parts += A.gauntlet('gauntlet', c, f, plate, leather)
    gold_right = vet
    parts += A.pauldron('pauldron_r', arm_r[0], -1, old_gilt if gold_right else plate, brass, size=1.14 * k_, lames=3,
                        seed=81)
    parts += A.pauldron('pauldron_l', arm_l[0], 1, plate, brass, size=1.14 * k_, lames=3, seed=82)
    if gold_right:   # the foreign pauldron: somebody else's gilt, a worn lion mask at its crown
        boss_at = arm_r[0] + Vector((-0.1, -0.02, 0.075))
        parts.append(K.sphere('lion', boss_at, 0.052, old_gilt, scale=(0.7, 1.0, 1.0), seg=20, rings=14))
        for dz, dy in ((0.03, -0.035), (-0.03, -0.035)):
            parts.append(K.sphere('lion_ear', boss_at + Vector((-0.012, dy + 0.02, dz)), 0.018, old_gilt, seg=10, rings=6))

    # ---------------------------------------------------------------- neck & head
    # the head carries its own neck (sternomastoids, trapezius), rising from under the back of the skull
    if head:     # portraits hold the head level, like the reference sheet
        if look is None:
            look = dict(LK.anchor(sex, commander=cmd, veteran=vet), seed=seed)
        hroot, _ = LK.build_head(look, gaze=16.0 if v.get('portrait') else 0.0,
                                 tag=None if look.get('anchor') else look['id'])
        hroot.matrix_world = head_frame(sex, v.get('portrait'))
        parts.append(hroot)
    if rev:   # blight light spilling from the eyes onto the face
        parts.append(K.glow('face_glow', head_c + Vector((0.0, -0.105, 0.012)), '#b98cf0', 0.18, radius=0.012))

    # ---------------------------------------------------------------- the great shield (left arm)
    sp_, _ = A.great_shield('shield', 0.6, 1.04, shield_face, iron, lames, brass, plate)
    sroot = K.root('shield_root')
    K.parent(sp_, sroot)
    sroot.matrix_world = (Matrix.Translation(V(0.305, -0.305, 0.87)) @ Matrix.Rotation(math.radians(27), 4, 'Z')
                          @ Matrix.Rotation(math.radians(-5), 4, 'X'))
    parts.append(sroot)

    # ---------------------------------------------------------------- the broadsword, held low
    fr = (arm_r[2] - arm_r[1]).normalized()
    hand = arm_r[2] + fr * 0.06
    parts += A.broadsword('sword', hand, (-0.28, -0.35, -0.9), blade, old_gilt, leather, old_gilt)

    # ---------------------------------------------------------------- the Commander's banner, strapped to the back
    if cmd:
        parts.append(K.tube('pole', V(0.02, 0.19, 0.95), V(0.02, 0.236, 2.3), 0.017, 0.015, wood, seg=12))
        parts.append(K.tube('crossbar', V(-0.285, 0.232, 2.2), V(0.325, 0.232, 2.2), 0.011, 0.011, wood, seg=10))
        tip = K.blade('finial', 0.07, 0.032, 0.012, brass, secs=[(0.0, 1.0), (0.4, 1.0), (1.0, 0.0)])
        A.place(tip, V(0.02, 0.236, 2.3), A.frame((0.0, 0.0, 1.0)))
        parts.append(tip)
        cz = (2.19 - 0.29) * hf
        flag_m = G.cloth('banner', color='#551714', blood=0.25, mud=0.0, seed=23, device=(0.02, cz, 0.12, '#b39a62'))
        top, out = [], []
        for k in range(16):
            top.append(V(-0.275 + 0.59 * k / 15, 0.24, 2.19))
            out.append(Vector((0.0, -1.0, 0.0)))
        parts.append(A.cloth_panel('banner', top, out, 0.62 * hf, flag_m, rows=18, tatter=0.3, slits=1, fold=0.022,
                                   seed=seed + 12))

    K.parent(parts, fig)
    fig.scale = (FIG_SCALE,) * 3
    fig.rotation_euler.z = math.radians(turn)
    return fig
