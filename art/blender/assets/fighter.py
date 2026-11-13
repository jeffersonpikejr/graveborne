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
from gb import body as BD
from gb import grit as G
from gb import kit as K
from gb import looks as LK
from gb import mat as M

FIG_SCALE = 0.6          # 1 m = 0.6 tile: a 1.85 m mercenary stands ~1.1 tiles tall

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

# The kit is laid on the body (gb/body.py). Every dimension below is the male anchor's (a siege wedge: broad through
# the shoulders and chest, heavy in the legs, planted wide), plus the difference the wearer's body makes at that
# point: her narrower shoulders, shallower chest, defined waist, wider hips, slimmer limbs, knees a touch closer,
# smaller hands and feet, 92% of his height. On him every difference is zero, so his armour never moves.


def head_frame(sex, portrait=False):
    """Where the head sits on the figure (figure space): on the neck, chin a touch up in battle, level in portraits."""
    return BD.Frame(sex).head_frame(portrait)


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
    B = BD.Frame(sex)
    hf = B.hf
    dl = [B.d('leg', i) for i in range(5)]           # thigh, mid-thigh, knee, calf, ankle
    da = [B.d('arm', i) for i in range(4)]           # upper arm, elbow, forearm, wrist
    dhip = B.hips() - BD.Frame('male').hips()        # across the hips
    dhj, kin = B.d('hip'), B.f['knee_in']            # the hip joints; her knees closer together
    dnk = B.d('neck')
    fs, fw = B.ratio('foot', 0), B.d('foot', 1) / 2  # the foot's length (ratio) and half-breadth
    hsize = (B.ratio('hand', 0) + B.ratio('hand', 1)) / 2
    spaul = (B.f['deltoid'] + 0.025) / (BD.Frame('male').f['deltoid'] + 0.025)  # the pauldron follows the deltoid
    # how much more her waist is defined than his (hips over waist): her plate closes in at the waist, the belt
    # cinches it there, and the faulds and tassets flare over her hips (a touch past her anatomy, so it reads at
    # sprite size, as the guide's silhouettes do)
    M0 = BD.Frame('male')
    wdef = (B.hips() - float(B.torso(1.17)[0])) - (M0.hips() - float(M0.torso(1.17)[0]))

    def pinch(u):
        return 0.6 * wdef * math.exp(-((u - 1.15) / 0.05) ** 2)

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
    legs = ((V(0.116 + dhj, 0.0, 0.97), V(0.19 + dhj - kin, -0.035, 0.52), V(0.228 + dhj - kin * 0.5, 0.0, 0.12), 1),
            (V(-0.116 - dhj, 0.0, 0.97), V(-0.184 - dhj + kin, -0.04, 0.52), V(-0.222 - dhj + kin * 0.5, 0.0, 0.12), -1))
    for hip, knee, ank, s in legs:
        parts.append(K.skin_chain('leg', [hip, knee, ank], [0.114 + dl[0], 0.082 + dl[2], 0.064 + dl[4]], hose))
        d = (knee - hip).normalized()
        parts.append(A.shell('cuisse', hip + d * 0.07, knee - d * 0.05,
                             [(0.128 + dl[0], 0.0), (0.12 + dl[1], 0.5), (0.102 + dl[2], 1.0)],
                             plate, arc=(-172.0, -8.0), dent=0.004, seed=11 + s))
        parts += A.cop('poleyn', knee + Vector((0.0, -0.085 - dl[2], 0.0)), (s * 0.12, -1.0, 0.05), (s, 0.15, 0.0), plate,
                       brass, r=0.086 + dl[2], seed=3 + s)
        dg = (ank - knee).normalized()
        parts.append(A.shell('greave', knee + dg * 0.07, ank + Vector((0.0, 0.0, 0.035)),
                             [(0.094 + dl[2], 0.0), (0.099 + dl[3], 0.3), (0.082 + (dl[3] + dl[4]) / 2, 0.78),
                              (0.075 + dl[4], 1.0)],
                             blackened if (vet and s < 0) else lames, seg=30, dent=0.005, seed=21 + s))
        if vet and s < 0:          # the mismatched greave came with a dead man's gilt trim
            parts.append(A.rivets('greave_trim', A.shell_rim_points(knee + dg * 0.07, ank + Vector((0, 0, 0.035)),
                                                                     0.09, 0.02, None, 14), 0.006, brass))
        toe = Vector((s * 0.026, -0.215 * fs, -0.078 * hf))
        parts.append(K.skin_chain('boot', [ank + Vector((0.0, 0.0, 0.05 * hf)), ank + Vector((0.0, -0.012, -0.035 * hf)),
                                           ank + Vector((s * 0.013, -0.125 * fs, -0.07 * hf)), ank + toe],
                                  [0.076 + dl[4], 0.074 + dl[4], 0.064 + fw, 0.05 + fw], boots))
        for k in range(2):             # sabaton lames over the instep
            a0 = ank + Vector((s * 0.006 * k, (-0.045 - 0.045 * k) * fs, (-0.012 - 0.02 * k) * hf))
            parts.append(A.shell('sabaton', a0, a0 + Vector((s * 0.004, -0.05 * fs, -0.018 * hf)),
                                 [(0.064 + fw, 0.0), (0.06 + fw, 1.0)],
                                 lames, arc=(10.0, 170.0), seg=18, lip=0.003, back=(0.0, 0.0, 1.0), seed=31 + k))

    # ---------------------------------------------------------------- maille skirt, faulds, tassets
    def ragged(i, a):
        return (0.0, 0.03 * math.sin(a * 9.0 + 1.1) * (1.0 if i == 0 else 0.0) + (0.012 * math.sin(a * 23.0) if i == 0 else 0.0))
    parts.append(K.lathe('skirt', [(0.242 + 1.3 * dhip, 0.68 * hf), (0.234 + 1.3 * dhip, 0.74 * hf), (0.217 + 1.3 * dhip, 0.88 * hf),
                                   (0.206 + B.dw(1.02), 0.99 * hf)],
                         mail, seg=48, sy=0.8, cap_bottom=False, cap_top=False, jitter=ragged))
    W0, C0 = 0.206, 0.25                    # his cuirass: at the waist, at the chest
    W, C = W0 + B.dw(1.03), C0 + B.dw(1.35)
    sy = 0.64 + (B.dd(1.35) - 0.64 * B.dw(1.35)) / C     # its depth over its width: her chest is shallower
    for k, (z0, z1) in enumerate(((0.99, 1.04), (0.945, 0.995))):     # over the iliac crest, then the hips
        r = W0 + 0.022 + 0.01 * k + (B.dw(1.02) + 0.4 * dhip if k == 0 else 1.3 * dhip)
        band = K.lathe('fauld', [(r + 0.008, z0 * hf), (r, z1 * hf)], lames, seg=40, sy=sy + 0.1,
                       arc=(-205.0, 25.0), cap_bottom=False, cap_top=False)
        A.solid(band, 0.005)
        parts.append(band)
        parts.append(A.rivets('fauld_r', [Vector(((r + 0.012) * math.cos(math.radians(a)), (r + 0.012) * math.sin(math.radians(a)) * (sy + 0.1), (z0 + 0.012) * hf))
                                          for a in range(-195, 20, 23)], 0.006, brass))
    for hip, knee, _, s in legs:
        d = (knee - hip).normalized()
        base = hip + Vector((s * (0.01 + 0.6 * dhip), -0.0, -0.035 * hf))
        for k in range(3):
            t0 = 0.12 * k
            parts.append(A.shell('tasset', base + d * t0, base + d * (t0 + 0.14),
                                 [(0.132 + 0.006 * k + dhip * 0.5, 0.0), (0.14 + 0.006 * k + dhip * 0.5, 1.0)],
                                 lames, arc=(-150.0 + s * 12.0, -30.0 + s * 12.0), seg=24, dent=0.004, seed=41 + k + s))

    # ---------------------------------------------------------------- cuirass, plackart
    prof = [(W0, 1.03), (W0 + 0.008, 1.1), ((W0 + C0) / 2 + 0.006, 1.18), (C0 - 0.004, 1.27), (C0, 1.35), (C0 - 0.006, 1.42),
            (C0 - 0.028, 1.47), (C0 - 0.07, 1.505), (0.136, 1.53)]     # closes in to the collar: no open neckline
    prof = [(r + B.dw(z) - pinch(z), z) for r, z in prof]      # hers is waisted, and flares onto her hips
    zs = [z for _, z in prof]

    def keel(a):
        return math.exp(-((a + math.pi / 2) / 0.22) ** 2)

    def cuirass_j(i, a):
        z = zs[i]
        dr = 0.022 * keel(a) * (1.0 if 0 < i < len(prof) - 1 else 0.4)
        dr += 0.03 * B.f['bust'] * math.exp(-((a + math.pi / 2) / 0.75) ** 2) * math.exp(-((z - 1.31) / 0.06) ** 2)
        dr += 0.004 * math.sin(a * 5.0 + i * 1.7) * math.sin(a * 3.0 + 0.4)     # dents
        return (dr, 0.0)
    cu = K.lathe('cuirass', [(r, z * hf) for r, z in prof], plate, seg=56, sy=sy, cap_bottom=False,
                 cap_top=False, jitter=cuirass_j)
    A.solid(cu, 0.006)
    K.subsurf(cu, 1)
    parts.append(cu)

    def plack_j(i, a):
        return (0.02 * keel(a), 0.075 * math.exp(-((a + math.pi / 2) / 0.4) ** 2) if i == 2 else 0.0)
    pl = K.lathe('plackart', [(W0 + 0.014 + B.dw(1.025) - pinch(1.025), 1.025 * hf), (W0 + 0.02 + B.dw(1.1) - pinch(1.1), 1.1 * hf),
                              ((W0 + C0) / 2 + 0.024 + B.dw(1.17) - pinch(1.17), 1.17 * hf)], lames,
                 seg=40, sy=sy, arc=(-155.0, -25.0), cap_bottom=False, cap_top=False, jitter=plack_j)
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
        n = Vector((math.cos(a) * sy, math.sin(a), 0.0)).normalized()
        return Vector((r * math.cos(a), r * math.sin(a) * sy, z)) + n * lift, n

    if vet:    # a patch riveted over a breach, in a different steel
        patch = K.lathe('patch', [(C0 + 0.009 + B.dw(1.27), 1.27 * hf), (C0 + 0.011 + B.dw(1.38), 1.38 * hf)], blackened,
                        seg=12, sy=sy,
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
    ub = 1.05 + 1.5 * wdef                  # the belt cinches the waist: hers higher, at her natural waist
    rx = W0 + 0.04 + B.dw(ub) - pinch(ub)
    bp, bn = ring_path(lambda a: ub * hf, rx, rx * (sy + 0.12))
    parts += A.strap('belt', bp, bn, 0.056, 0.009, leather, brass, rivet_every=0.1, closed=True)
    parts.append(K.rbox('buckle', (0.062, 0.014, 0.068), (-0.035, -rx * (sy + 0.12) - 0.012, ub * hf), brass, bev=0.006))
    if not cmd:
        rx2 = W0 + 0.055 + 1.1 * dhip        # the sword belt rides the hips
        sp, sn = ring_path(lambda a: (0.985 + 0.04 * math.cos(a)) * hf, rx2, rx2 * (sy + 0.16))
        parts += A.strap('swordbelt', sp, sn, 0.045, 0.008, leather, brass, rivet_every=0.12, closed=True)
        for ang, zz in ((-160.0, 0.95), (-25.0, 1.0)):     # pouches hang off the hip
            a = math.radians(ang)
            p = Vector((rx2 * 1.04 * math.cos(a), rx2 * (sy + 0.16) * 1.04 * math.sin(a), zz * hf - 0.04))
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
            r = W0 + 0.07 + (B.dw(1.03) + dhip) / 2     # hung from the belt, over the hips
            top.append(Vector((r * math.cos(a), r * math.sin(a) * (sy + 0.18), 1.03 * hf)))
            out.append(Vector((math.cos(a), math.sin(a), 0.0)))
        return A.cloth_panel('tabard', top, out, length * hf, ox, rows=16, tatter=tatter, slits=slits,
                             fold=0.014, bulge=lambda t: 0.07 * math.sin(math.pi * min(t, 0.55) / 1.1), seed=sd)
    tatter = 0.18 if cmd else 0.38
    parts.append(panel(-122.0, -58.0, 9, 0.64, tatter, 1 if cmd else 3, seed))
    parts.append(panel(-162.0, -138.0, 4, 0.5, tatter, 0, seed + 1))
    parts.append(panel(-42.0, -18.0, 4, 0.5, tatter, 0, seed + 2))

    # ---------------------------------------------------------------- collar, scarf, rank
    parts.append(A.shell('collar', V(0.0, 0.0, 1.47), V(0.0, -0.005, 1.555), [(0.13 + dnk, 0.0), (0.108 + dnk, 0.5), (0.095 + dnk, 1.0)],
                         plate, seg=32, lip=0.004, thick=0.005))
    # the scarf: oxblood wool wound round the neck like a cowl, bunched at the throat, clear of the jaw
    parts.append(A.torus('scarf', V(0.0, -0.004, 1.575), 0.088 + dnk, 0.023, ox, sy=0.95, lumpy=0.4, rz=0.034, folds=0.006,
                         seed=seed, rseg=14))
    parts.append(A.torus('scarf2', V(0.002, -0.01, 1.54), 0.108 + dnk, 0.024, ox, sy=0.9, lumpy=0.45, rz=0.036,
                         folds=0.006, seed=seed + 3, rseg=14))
    parts.append(A.torus('scarf3', V(0.004, -0.014, 1.508), 0.124 + dnk, 0.018, ox, sy=0.84, lumpy=0.45, rz=0.03,
                         folds=0.006, seed=seed + 5, rseg=14))
    if cmd:    # one tarnished mark of rank: a gilt gorget on the breast, the company's roundel at its centre
        gg = K.lathe('gorget', [(C0 + 0.004 + B.dw(1.43), 1.43 * hf), (C0 - 0.026 + B.dw(1.475), 1.475 * hf)], old_gilt, seg=24,
                     sy=sy + 0.06, arc=(-128.0, -52.0), cap_bottom=False, cap_top=False)
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
            top.append(V(0.03 + 0.02 * k, -0.122 - 0.004 * k - B.dd(1.505, 'front'), 1.515))
            out.append(Vector((0.0, -1.0, 0.0)))
        parts.append(A.cloth_panel('scarf_end', top, out, 0.24 * hf, ox, rows=10, tatter=0.3, slits=0, fold=0.008,
                                   bulge=lambda t: 0.045 * math.sin(math.pi * t * 0.9), seed=seed + 5))

    # ---------------------------------------------------------------- arms
    sh = 0.272 + B.d('shoulder')            # her shoulders sit narrower; her arms are as much shorter as she is
    arm_r = (V(-sh, 0.0, 1.455), V(-sh - 0.055 * hf, -0.01 * hf, 1.17), V(-sh - 0.065 * hf, -0.12 * hf, 0.945))
    arm_l = (V(sh, 0.0, 1.455), V(sh + 0.1 * hf, 0.03 * hf, 1.2), V(sh + 0.05 * hf, -0.2 * hf, 1.105))
    for (a, b, c), s in ((arm_r, -1), (arm_l, 1)):
        parts.append(K.skin_chain('arm', [a, b, c], [0.08 + da[0], 0.066 + da[1], 0.055 + da[3]], mail))
        u = (b - a).normalized()
        parts.append(A.shell('rerebrace', a + u * 0.14, b - u * 0.035, [(0.08 + da[0], 0.0), (0.073 + (da[0] + da[1]) / 2, 1.0)],
                             lames, seg=24, dent=0.003, seed=51 + s))
        parts += A.cop('couter', b, (s * 0.55, 0.8, 0.1), (s, -0.2, 0.0), plate, brass, r=0.066 + da[1], seed=61 + s)
        f = (c - b).normalized()
        parts.append(A.shell('vambrace', b + f * 0.05, c - f * 0.015, [(0.072 + da[2], 0.0), (0.06 + da[3], 1.0)], plate,
                             seg=24, dent=0.003, seed=71 + s))
        parts += A.gauntlet('gauntlet', c, f, plate, leather, size=hsize)
    gold_right = vet
    parts += A.pauldron('pauldron_r', arm_r[0], -1, old_gilt if gold_right else plate, brass, size=1.14 * spaul, lames=3,
                        seed=81)
    parts += A.pauldron('pauldron_l', arm_l[0], 1, plate, brass, size=1.14 * spaul, lames=3, seed=82)
    if gold_right:   # the foreign pauldron: somebody else's gilt, a worn lion mask at its crown
        boss_at = arm_r[0] + Vector((-0.1, -0.02, 0.075)) * spaul
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
        hroot.matrix_world = B.head_frame(v.get('portrait') or v.get('level'))     # level: straight review views
        parts.append(hroot)
    if rev:   # blight light spilling from the eyes onto the face
        parts.append(K.glow('face_glow', head_c + Vector((0.0, -0.105, 0.012)), '#b98cf0', 0.18, radius=0.012))

    # ---------------------------------------------------------------- the great shield (left arm)
    armed = v.get('armed', True)        # (the body review shows the kit without them)
    sp_, _ = A.great_shield('shield', 0.6, 1.04, shield_face, iron, lames, brass, plate) if armed else ([], None)
    sroot = K.root('shield_root')
    K.parent(sp_, sroot)
    grip = Vector((0.305 + (sh - 0.272) + 0.05 * (hf - 1.0), -0.305 + 0.2 * (1.0 - hf), 0.87 * hf + 0.235 * (hf - 1.0)))
    sroot.matrix_world = (Matrix.Translation(grip) @ Matrix.Rotation(math.radians(27), 4, 'Z')     # held where her hand is
                          @ Matrix.Rotation(math.radians(-5), 4, 'X'))
    parts.append(sroot)

    # ---------------------------------------------------------------- the broadsword, held low
    fr = (arm_r[2] - arm_r[1]).normalized()
    hand = arm_r[2] + fr * 0.06
    if armed:
        parts += A.broadsword('sword', hand, (-0.28, -0.35, -0.9), blade, old_gilt, leather, old_gilt)

    # ---------------------------------------------------------------- the Commander's banner, strapped to the back
    if cmd:
        yb = B.dd(1.3, 'back')              # strapped to her back: a shallower back
        parts.append(K.tube('pole', V(0.02, 0.19 + yb, 0.95), V(0.02, 0.236 + yb, 2.3), 0.017, 0.015, wood, seg=12))
        parts.append(K.tube('crossbar', V(-0.285, 0.232 + yb, 2.2), V(0.325, 0.232 + yb, 2.2), 0.011, 0.011, wood, seg=10))
        tip = K.blade('finial', 0.07, 0.032, 0.012, brass, secs=[(0.0, 1.0), (0.4, 1.0), (1.0, 0.0)])
        A.place(tip, V(0.02, 0.236 + yb, 2.3), A.frame((0.0, 0.0, 1.0)))
        parts.append(tip)
        cz = (2.19 - 0.29) * hf
        flag_m = G.cloth('banner', color='#551714', blood=0.25, mud=0.0, seed=23, device=(0.02, cz, 0.12, '#b39a62'))
        top, out = [], []
        for k in range(16):
            top.append(V(-0.275 + 0.59 * k / 15, 0.24 + yb, 2.19))
            out.append(Vector((0.0, -1.0, 0.0)))
        parts.append(A.cloth_panel('banner', top, out, 0.62 * hf, flag_m, rows=18, tatter=0.3, slits=1, fold=0.022,
                                   seed=seed + 12))

    K.parent(parts, fig)
    fig.scale = (FIG_SCALE,) * 3
    fig.rotation_euler.z = math.radians(turn)
    return fig
