"""GRAVEGUARD. Wave 2, asset #11: the Risen's knight.

Brief: a knight the Blight got up again in the plate he was buried in. Black corroded iron from sabaton to helm, pitted
and rust-run; a great helm closed over whatever is left of the head, its eye slit lit violet from within (the only
light on him: no violet back-light, that marks the company's own risen); the rags of a tabard gone corpse grey-green
hanging from the belt; a halberd held upright, its butt on the ground, its blade over his head. At 26 px a Graveguard
is a black-iron knight, a violet slit, a halberd.

Built from the Fighter's plate shells (fighter.py's construction, laid on the body dial for both forms) in the Risen's
iron (gb/risen.py) under the corpse material mode. Two looks per form: 1 a sugarloaf helm, 2 a flat-topped barrel helm,
rustier plate, a paler shroud of a tabard and the left pauldron lost.
"""
import math

from mathutils import Matrix, Vector

from gb import armor as A
from gb import body as BD
from gb import grit as G
from gb import kit as K
from gb import mat as M
from gb import risen as RS

FIG_SCALE = 0.6

VARIANTS = {}
for _f, _sex in (('m', 'male'), ('f', 'female')):
    for _n in (1, 2):
        VARIANTS[f'foe_graveguard_{_n}_{_f}'] = dict(sex=_sex, n=_n)

HALBERD_UP = (-0.075, 0.0, 1.0)     # the haft leans its head out to the right, clear of the helm
TABARD = {1: '#8a977a', 2: '#a9a48c'}       # before the corpse mode sinks it: grey-green, a bone-grey shroud


def head_frame(sex, portrait=False):
    return BD.Frame(sex).head_frame(portrait)


def build(v, seed=7, turn=-4.0, look=None, head=True):
    sex = v.get('sex', 'male')
    n = v.get('n', 1)
    M.set_mode(revenant=True, corpse=True)
    B = BD.Frame(sex)
    hf = B.hf
    dl = [B.d('leg', i) for i in range(5)]
    da = [B.d('arm', i) for i in range(4)]
    dhip = B.hips() - BD.Frame('male').hips()
    dhj, kin = B.d('hip'), B.f['knee_in']
    dnk = B.d('neck')
    fs, fw = B.ratio('foot', 0), B.d('foot', 1) / 2
    hsize = (B.ratio('hand', 0) + B.ratio('hand', 1)) / 2
    spaul = (B.f['deltoid'] + 0.025) / (BD.Frame('male').f['deltoid'] + 0.025)
    M0 = BD.Frame('male')
    wdef = (B.hips() - float(B.torso(1.17)[0])) - (M0.hips() - float(M0.torso(1.17)[0]))
    seed = seed + 13 * n + (5 if sex == 'female' else 0)

    def pinch(u):
        return 0.6 * wdef * math.exp(-((u - 1.15) / 0.05) ** 2)

    def V(x, y, z):
        return Vector((x, y, z * hf))

    # ---------------------------------------------------------------- materials
    mt = RS.iron(n)
    plate, lames, mail, rivet = mt['plate'], mt['lames'], mt['mail'], mt['rivet']
    leather = G.leather('grave_leather', color='#2a2019', mud=1.6, seed=11)
    boots = G.leather('grave_boots', color='#231a13', mud=2.6, seed=12)
    hose = G.cloth('grave_hose', color='#24211e', blood=0.1, mud=1.5, seed=10)
    rag = G.cloth(f'grave_tabard{n}', color=TABARD[n], blood=0.3, mud=2.2, grime=1.0, seed=9 + n)
    haft = G.wood('grave_haft', color='#4a3a2a', seed=48)

    fig = K.root('figure')
    parts = []

    # ---------------------------------------------------------------- legs: cuisses, poleyns, greaves, sabatons
    legs = ((V(0.116 + dhj, 0.0, 0.97), V(0.19 + dhj - kin, -0.035, 0.52), V(0.228 + dhj - kin * 0.5, 0.0, 0.12), 1),
            (V(-0.116 - dhj, 0.0, 0.97), V(-0.184 - dhj + kin, -0.04, 0.52), V(-0.222 - dhj + kin * 0.5, 0.0, 0.12), -1))
    for hip, knee, ank, s in legs:
        parts.append(K.skin_chain('leg', [hip, knee, ank], [0.114 + dl[0], 0.082 + dl[2], 0.064 + dl[4]], hose))
        d = (knee - hip).normalized()
        parts.append(A.shell('cuisse', hip + d * 0.07, knee - d * 0.05,
                             [(0.128 + dl[0], 0.0), (0.12 + dl[1], 0.5), (0.102 + dl[2], 1.0)],
                             plate, arc=(-172.0, -8.0), dent=0.005, seed=11 + s))
        parts += A.cop('poleyn', knee + Vector((0.0, -0.085 - dl[2], 0.0)), (s * 0.12, -1.0, 0.05), (s, 0.15, 0.0), plate,
                       rivet, r=0.086 + dl[2], seed=3 + s)
        dg = (ank - knee).normalized()
        parts.append(A.shell('greave', knee + dg * 0.07, ank + Vector((0.0, 0.0, 0.035)),
                             [(0.094 + dl[2], 0.0), (0.099 + dl[3], 0.3), (0.082 + (dl[3] + dl[4]) / 2, 0.78),
                              (0.075 + dl[4], 1.0)], lames, seg=30, dent=0.006, seed=21 + s))
        toe = Vector((s * 0.026, -0.215 * fs, -0.078 * hf))
        parts.append(K.skin_chain('boot', [ank + Vector((0.0, 0.0, 0.05 * hf)), ank + Vector((0.0, -0.012, -0.035 * hf)),
                                           ank + Vector((s * 0.013, -0.125 * fs, -0.07 * hf)), ank + toe],
                                  [0.076 + dl[4], 0.074 + dl[4], 0.064 + fw, 0.05 + fw], boots))
        for k in range(2):
            a0 = ank + Vector((s * 0.006 * k, (-0.045 - 0.045 * k) * fs, (-0.012 - 0.02 * k) * hf))
            parts.append(A.shell('sabaton', a0, a0 + Vector((s * 0.004, -0.05 * fs, -0.018 * hf)),
                                 [(0.064 + fw, 0.0), (0.06 + fw, 1.0)],
                                 lames, arc=(10.0, 170.0), seg=18, lip=0.003, back=(0.0, 0.0, 1.0), seed=31 + k))

    # ---------------------------------------------------------------- maille skirt, faulds, tassets
    def ragged(i, a):
        return (0.0, 0.035 * math.sin(a * 9.0 + 1.1 + n) * (1.0 if i == 0 else 0.0) + (0.014 * math.sin(a * 23.0) if i == 0 else 0.0))
    parts.append(K.lathe('skirt', [(0.242 + 1.3 * dhip, 0.68 * hf), (0.234 + 1.3 * dhip, 0.74 * hf), (0.217 + 1.3 * dhip, 0.88 * hf),
                                   (0.206 + B.dw(1.02), 0.99 * hf)],
                         mail, seg=48, sy=0.8, cap_bottom=False, cap_top=False, jitter=ragged))
    W0, C0 = 0.206, 0.25
    C = C0 + B.dw(1.35)
    sy = 0.64 + (B.dd(1.35) - 0.64 * B.dw(1.35)) / C
    for k, (z0, z1) in enumerate(((0.99, 1.04), (0.945, 0.995))):
        r = W0 + 0.022 + 0.01 * k + (B.dw(1.02) + 0.4 * dhip if k == 0 else 1.3 * dhip)
        band = K.lathe('fauld', [(r + 0.008, z0 * hf), (r, z1 * hf)], lames, seg=40, sy=sy + 0.1,
                       arc=(-205.0, 25.0), cap_bottom=False, cap_top=False)
        A.solid(band, 0.005)
        parts.append(band)
    for hip, knee, _, s in legs:
        d = (knee - hip).normalized()
        base = hip + Vector((s * (0.01 + 0.6 * dhip), -0.0, -0.035 * hf))
        for k in range(3):
            t0 = 0.12 * k
            parts.append(A.shell('tasset', base + d * t0, base + d * (t0 + 0.14),
                                 [(0.132 + 0.006 * k + dhip * 0.5, 0.0), (0.14 + 0.006 * k + dhip * 0.5, 1.0)],
                                 lames, arc=(-150.0 + s * 12.0, -30.0 + s * 12.0), seg=24, dent=0.005, seed=41 + k + s))

    # ---------------------------------------------------------------- cuirass, plackart
    prof = [(W0, 1.03), (W0 + 0.008, 1.1), ((W0 + C0) / 2 + 0.006, 1.18), (C0 - 0.004, 1.27), (C0, 1.35), (C0 - 0.006, 1.42),
            (C0 - 0.028, 1.47), (C0 - 0.07, 1.505), (0.136, 1.53)]
    prof = [(r + B.dw(z) - pinch(z), z) for r, z in prof]
    zs = [z for _, z in prof]

    def keel(a):
        return math.exp(-((a + math.pi / 2) / 0.22) ** 2)

    def cuirass_j(i, a):
        z = zs[i]
        dr = 0.022 * keel(a) * (1.0 if 0 < i < len(prof) - 1 else 0.4)
        dr += 0.03 * B.f['bust'] * math.exp(-((a + math.pi / 2) / 0.75) ** 2) * math.exp(-((z - 1.31) / 0.06) ** 2)
        dr += 0.006 * math.sin(a * 5.0 + i * 1.7 + n) * math.sin(a * 3.0 + 0.4)
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

    # ---------------------------------------------------------------- the belt, and what is left of the tabard
    ub = 1.05 + 1.5 * wdef
    rx = W0 + 0.04 + B.dw(ub) - pinch(ub)
    bp, bn = [], []
    for k in range(44):
        a = 2 * math.pi * k / 44
        bp.append(Vector((rx * math.cos(a), rx * (sy + 0.12) * math.sin(a), ub * hf)))
        bn.append(Vector((math.cos(a) / rx, math.sin(a) / (rx * (sy + 0.12)), 0.0)))
    parts += A.strap('belt', bp, bn, 0.056, 0.009, leather, rivet, rivet_every=0.1, closed=True)
    parts.append(K.rbox('buckle', (0.062, 0.014, 0.068), (-0.035, -rx * (sy + 0.12) - 0.012, ub * hf), rivet, bev=0.006))

    def panel(a0, a1, cols, length, tatter, slits, sd):
        top, out = [], []
        for k in range(cols):
            a = math.radians(a0 + (a1 - a0) * k / (cols - 1))
            r = W0 + 0.07 + (B.dw(1.03) + dhip) / 2
            top.append(Vector((r * math.cos(a), r * math.sin(a) * (sy + 0.18), 1.03 * hf)))
            out.append(Vector((math.cos(a), math.sin(a), 0.0)))
        return A.cloth_panel('tabard', top, out, length * hf, rag, rows=16, tatter=tatter, slits=slits,
                             fold=0.014, bulge=lambda t: 0.07 * math.sin(math.pi * min(t, 0.55) / 1.1), seed=sd)
    parts.append(panel(-124.0, -56.0, 9, 0.6 if n == 1 else 0.46, 0.55, 3, seed))
    parts.append(panel(-166.0, -138.0, 4, 0.42, 0.5, 0, seed + 1))
    if n == 1:
        parts.append(panel(-42.0, -14.0, 4, 0.36, 0.5, 0, seed + 2))
    parts.append(panel(40.0, 140.0, 9, 0.55, 0.6, 2, seed + 3))          # and down the back

    # ---------------------------------------------------------------- the gorget
    parts.append(A.shell('collar', V(0.0, 0.0, 1.47), V(0.0, -0.005, 1.565), [(0.135 + dnk, 0.0), (0.118 + dnk, 0.5), (0.108 + dnk, 1.0)],
                         plate, seg=32, lip=0.004, thick=0.005))

    # ---------------------------------------------------------------- arms: the right on the halberd, the left hanging
    sh = 0.272 + B.d('shoulder')
    arm_r = (V(-sh, 0.0, 1.455), V(-sh - 0.075 * hf, 0.035 * hf, 1.175), V(-sh - 0.1 * hf, -0.215 * hf, 1.14))
    arm_l = (V(sh, 0.0, 1.455), V(sh + 0.055 * hf, -0.01 * hf, 1.17), V(sh + 0.065 * hf, -0.12 * hf, 0.945))
    for (a, b, c), s in ((arm_r, -1), (arm_l, 1)):
        parts.append(K.skin_chain('arm', [a, b, c], [0.08 + da[0], 0.066 + da[1], 0.055 + da[3]], mail))
        u = (b - a).normalized()
        parts.append(A.shell('rerebrace', a + u * 0.14, b - u * 0.035, [(0.08 + da[0], 0.0), (0.073 + (da[0] + da[1]) / 2, 1.0)],
                             lames, seg=24, dent=0.004, seed=51 + s))
        parts += A.cop('couter', b, (s * 0.55, 0.8, 0.1), (s, -0.2, 0.0), plate, rivet, r=0.066 + da[1], seed=61 + s)
        f = (c - b).normalized()
        parts.append(A.shell('vambrace', b + f * 0.05, c - f * 0.015, [(0.072 + da[2], 0.0), (0.06 + da[3], 1.0)], plate,
                             seg=24, dent=0.004, seed=71 + s))
        parts += A.gauntlet('gauntlet', c, f, plate, leather, size=hsize)
    parts += A.pauldron('pauldron_r', arm_r[0], -1, plate, rivet, size=1.16 * spaul, lames=3, seed=81, dent=0.006)
    if n == 1:
        parts += A.pauldron('pauldron_l', arm_l[0], 1, plate, rivet, size=1.16 * spaul, lames=3, seed=82, dent=0.006)

    # ---------------------------------------------------------------- the great helm, its slit lit
    H = B.head_frame(v.get('portrait') or v.get('level'))
    if head:
        parts += RS.great_helm('helm', H, mt['helm'], rivet, kind=('sugarloaf', 'barrel')[n - 1], seed=seed)
        parts.append(K.glow('slit_glow', H @ Vector((0.0, -0.17, 0.0)), RS.VIOLET, 0.22, radius=0.012))

    # ---------------------------------------------------------------- the halberd, upright in the right fist
    fr_ = (arm_r[2] - arm_r[1]).normalized()
    hand = arm_r[2] + fr_ * 0.06
    if v.get('armed', True):
        parts += RS.halberd('halberd', hand, HALBERD_UP, 2.22 * (0.5 + 0.5 * hf), haft, mt['blade'], leather)

    K.parent(parts, fig)
    fig.scale = (FIG_SCALE,) * 3
    fig.rotation_euler.z = math.radians(turn)
    return fig
