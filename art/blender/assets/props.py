"""PROPS. Wave 3 objective props and the Wave 4 scatter kit (ASSETS.md #20-#23, #32), on the house stage:

  prop_menhir_1..2   a Blight-menhir: a cracked standing stone veined with the Blight's violet light
  prop_nest_1        a Blight-nest: a pod of flesh split with light, rooted in tendrils, bones at its foot
  prop_wagon_1       the escort wagon: a two-wheeled covered cart resting on its shafts
  prop_cache_1       a supply cache: an iron-bound chest, sacks and a keg
  prop_corpse_1..3   a fallen soldier: under a cloak with a sword by the hand; shrouded and corded with a shield
                     beside; cloaked, with arrows in the back
  deco_*             ground clutter at the tile centre: rocks, bones, a skull, a barrel, a crate, a broken wheel, a
                     stump, a log, planks, reeds, a fern

Man-made things are modelled in metres under a root scaled by FIG (the figures' own scale), so they sit at a
soldier's size and the grit materials' grain is the size it is on the soldiers' kit.
"""
import math

import numpy as np
from mathutils import Matrix, Vector

from gb import grit as G
from gb import kit as K
from gb import mat as M
from gb import terrain as T
import terrain as TA
from terrain import _rot, _rx, _ry, _rz, _pebbles, _tuft

FIG = 0.6
UP = np.array((0.0, 0.0, 1.0))

VARIANTS = {'prop_menhir_1': dict(kind='menhir', n=1), 'prop_menhir_2': dict(kind='menhir', n=2),
            'prop_nest_1': dict(kind='nest'), 'prop_wagon_1': dict(kind='wagon'), 'prop_cache_1': dict(kind='cache'),
            'prop_corpse_1': dict(kind='corpse', n=1), 'prop_corpse_2': dict(kind='corpse', n=2),
            'prop_corpse_3': dict(kind='corpse', n=3),
            'deco_rock_1': dict(kind='rock', n=1), 'deco_rock_2': dict(kind='rock', n=2),
            'deco_bones_1': dict(kind='bones'), 'deco_skull_1': dict(kind='skull'), 'deco_barrel_1': dict(kind='barrel'),
            'deco_crate_1': dict(kind='crate'), 'deco_wheel_1': dict(kind='wheel'), 'deco_stump_1': dict(kind='stump'),
            'deco_log_1': dict(kind='log'), 'deco_plank_1': dict(kind='plank'), 'deco_reeds_1': dict(kind='reeds'),
            'deco_fern_1': dict(kind='fern')}


def _scaled(parts, scale=FIG, turn=0.0, at=(0.0, 0.0)):
    r = T.root('prop')
    T.parent([p for p in parts if p is not None], r)
    r.scale = (scale,) * 3
    r.rotation_euler.z = math.radians(turn)
    r.location = (at[0], at[1], 0.0)
    return r


# ================================================================ shared pieces
def long_bone(acc, a, b, r=0.02):
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    s = np.array((0.0, 0.06, 0.16, 0.5, 0.84, 0.94, 1.0))
    acc.add(*T.tube(a[None, :] + (b - a)[None, :] * s[:, None], r * np.array((1.1, 1.75, 1.0, 0.82, 1.0, 1.7, 1.1)), seg=7,
                    cap0=True, cap1=True))


def skull(acc, dark, at, yaw=0.0, s=1.0, jaw=True, tilt=0.0):
    """A human skull resting on the ground at `at` (metres), facing -Y before `yaw`. dark: an Acc for the sockets."""
    R = _rz(yaw) @ _rx(tilt)
    a, d = T.Acc(), T.Acc()
    a.add(*T.ellipsoid((0, 0.01, 0.105), (0.075, 0.095, 0.08), seg=18, rings=12))                # cranium
    a.add(*T.ellipsoid((0, -0.062, 0.062), (0.052, 0.04, 0.05), seg=14, rings=10))                # face
    a.add(*T.ellipsoid((0.045, -0.05, 0.078), (0.022, 0.02, 0.014), seg=8, rings=6))              # cheekbones
    a.add(*T.ellipsoid((-0.045, -0.05, 0.078), (0.022, 0.02, 0.014), seg=8, rings=6))
    if jaw:
        a.add(*T.ellipsoid((0, -0.06, 0.018), (0.042, 0.04, 0.02), seg=12, rings=8))
    for sx in (-1, 1):
        d.add(*T.ellipsoid((sx * 0.027, -0.09, 0.092), (0.019, 0.016, 0.018), seg=10, rings=8))   # sockets
    d.add(*T.ellipsoid((0, -0.1, 0.062), (0.01, 0.012, 0.016), seg=8, rings=6))                   # the nose
    d.add(*T.ellipsoid((0, -0.094, 0.036), (0.03, 0.012, 0.007), seg=8, rings=6))                 # teeth line
    acc.merge(a.apply(R, at, s))
    dark.merge(d.apply(R, at, s))


def wheel(nz, R=0.55, spokes=10, missing=(), gap=None):
    """A cart wheel in the XZ plane (axle along Y), centred on the origin: an Acc, slot 0 wood, slot 1 iron.
    missing: spoke indices gone; gap=(a0, a1): the arc of rim that is left (radians), the rest broken away."""
    w = T.Acc()
    a0, a1 = gap if gap else (0.0, 2.0 * math.pi)
    a = np.linspace(a0, a1, max(8, int(48 * (a1 - a0) / 6.283)) + 1)
    ring = np.column_stack((np.cos(a), np.zeros(len(a)), np.sin(a)))
    w.add(*T.tube(ring * R, 0.05, seg=8, nz=nz, rough=0.12, squash=0.8, cap0=bool(gap), cap1=bool(gap)), mi=0)
    w.add(*T.tube(ring * (R + 0.042), 0.03, seg=6, squash=1.3), mi=1)                           # the iron tyre
    for k in range(spokes):
        if k in missing:
            continue
        ak = 2.0 * math.pi * (k + 0.5) / spokes
        if gap and not (a0 <= ak <= a1):
            ln = R * 0.55        # a spoke left standing where the rim is gone, snapped
        else:
            ln = R - 0.03
        d = np.array((math.cos(ak), 0.0, math.sin(ak)))
        w.add(*T.tube(np.array((d * 0.07, d * ln)), (0.027, 0.021), seg=6, cap1=True), mi=0)
    V, F, UV = T.lathe([(0.045, -0.12), (0.085, -0.08), (0.1, 0.0), (0.085, 0.08), (0.045, 0.12)], seg=16)
    w.add(_rot(V, _rx(-math.pi / 2)), F, UV, mi=0)
    V, F, UV = T.lathe([(0.05, -0.135), (0.05, 0.135)], seg=12)
    w.add(_rot(V, _rx(-math.pi / 2)), F, UV, mi=1)
    return w


def barrel(nz, r=0.21, h=0.72, staves=14):
    """A barrel standing on the origin: (staves Acc, hoops Acc)."""
    wood, iron = T.Acc(), T.Acc()
    zs = np.linspace(0.0, h, 13)
    rs = r * (1.0 + 0.22 * np.sin(np.pi * zs / h) ** 0.9)
    prof = [(rs[i], zs[i]) for i in range(13)] + [(rs[-1] - 0.02, h), (rs[-1] - 0.025, h - 0.035), (0.0005, h - 0.035)]
    V, F, UV = T.lathe(prof, seg=staves * 8, nz=nz, rough=0.004, cap0=True, cap1=False)
    th = np.arctan2(V[:, 1], V[:, 0])
    groove = (np.cos(th * staves) > 0.93) & (V[:, 2] < h + 1e-6) & (np.hypot(V[:, 0], V[:, 1]) > r * 0.9)
    k = np.where(groove, 0.975, 1.0)
    V = V * np.column_stack((k, k, np.ones(len(V))))
    wood.add(V, F, UV)
    for zz in (0.07, 0.2, h - 0.2, h - 0.07):
        rr = r * (1.0 + 0.22 * math.sin(math.pi * zz / h) ** 0.9) + 0.006
        iron.add(*T.lathe([(rr - 0.004, zz - 0.022), (rr + 0.002, zz - 0.02), (rr + 0.002, zz + 0.02), (rr - 0.004, zz + 0.022)],
                          seg=40, cap0=False, cap1=False))
    return wood, iron


def sack(acc, nz, at, size=(0.22, 0.2, 0.27), yaw=0.0, lying=False):
    a = T.Acc()
    if lying:
        a.add(*T.ellipsoid((0, 0, size[1] * 0.8), (size[2] * 1.15, size[1], size[1] * 0.85), seg=20, rings=14, nz=nz, rough=0.12, scale=6.0))
        a.add(*T.tube(np.array(((size[2] * 1.05, 0, size[1] * 0.8), (size[2] * 1.35, 0, size[1] * 0.75))), (0.04, 0.06), seg=8, cap1=True))
    else:
        a.add(*T.ellipsoid((0, 0, size[2] * 0.9), size, seg=20, rings=14, nz=nz, rough=0.12, scale=6.0))
        a.add(*T.tube(np.array(((0, 0, size[2] * 1.75), (0.01, 0, size[2] * 1.95), (0.03, 0.01, size[2] * 2.15))), (0.05, 0.035, 0.065),
                      seg=8, cap1=True))
    for v in a.V:
        v[:, 2] = np.maximum(v[:, 2], 0.0)
    acc.merge(a.apply(_rz(yaw), at))


def boards(acc, nz, centre, size, n, axis, gap=0.008, skip=(), jitter=0.0, rnd=None):
    """A panel of `n` boards side by side filling the box `size` at `centre`: the boards run along the box's longest
    side and are laid across `axis` ('x', 'y' or 'z')."""
    ia = 'xyz'.index(axis)
    c, s = np.asarray(centre, np.float64), np.asarray(size, np.float64)
    w = s[ia] / n
    for k in range(n):
        if k in skip:
            continue
        cc, ss = c.copy(), s.copy()
        cc[ia] = c[ia] - s[ia] / 2 + w * (k + 0.5)
        ss[ia] = w - gap
        if jitter and rnd is not None:
            cc += rnd.normal(0.0, jitter, 3)
        acc.add(*T.block(cc, ss, bev=0.006, grid=0.09, nz=nz, rough=0.003))


# ================================================================ Blight-menhir
def menhir(n):
    rnd = np.random.default_rng(700 + n)
    nz = T.Field(120 + n)
    acc, small, dry = T.Acc(), T.Acc(), T.Acc()
    veins = dict(glow=9.0, scale=3.0, width=0.045, z0=0.05, z1=1.15, fade=0.55)
    m = T.stone(f'menhir_{n}', color='#4d4a55', color2='#2b2930', moss=0.0, lichen=0.25, cracks=1.0, seed=80 + n,
                scale=1.3, veins=veins, mud_h=0.1, soot=0.5)
    parts = []
    if n == 1:      # one tall stone
        V, F = T.rock(rnd, (0.5, 0.36, 1.6), n=20, cuts=4, rough=0.05, nz=nz, crag=0.04)
        acc.add(_rot(V, _ry(0.06) @ _rx(-0.04), (0.0, 0.0, 0.5)), F)
        light_at = (0.0, -0.3, 0.55)
    else:           # split down the middle, the halves leaning apart, light in the cleft
        V, F = T.rock(rnd, (0.34, 0.34, 1.35), n=18, cuts=4, rough=0.05, nz=nz, crag=0.04)
        acc.add(_rot(V, _ry(-0.2), (-0.17, 0.0, 0.42)), F)
        V, F = T.rock(rnd, (0.3, 0.32, 1.1), n=18, cuts=4, rough=0.05, nz=nz, crag=0.04)
        acc.add(_rot(V, _ry(0.24), (0.17, 0.02, 0.33)), F)
        heart = T.Acc()
        heart.add(*T.ellipsoid((0.0, 0.0, 0.3), (0.035, 0.07, 0.3), seg=12, rings=10, nz=nz, rough=0.3, scale=9.0))
        ob = heart.obj('heart', M.emissive('menhir_heart', '#b98cf0', 5.0))
        ob.visible_shadow = False
        parts.append(ob)
        light_at = (0.0, -0.22, 0.4)
    acc.V = [np.column_stack((v[:, 0], v[:, 1], np.maximum(v[:, 2], -0.01))) for v in acc.V]
    for _ in range(6):      # shards fallen from it
        a, rr = rnd.uniform(0, 6.283), rnd.uniform(0.28, 0.42)
        s = rnd.uniform(0.06, 0.13)
        V, F = T.rock(rnd, (s, s * 0.8, s * 0.7), n=9, cuts=2, rough=0.06, nz=nz, smooth=1)
        acc.add(V + (math.cos(a) * rr, math.sin(a) * rr * 1.1, s * 0.15), F)
    for _ in range(8):
        a = rnd.uniform(0, 6.283)
        _tuft(dry, rnd, (math.cos(a) * 0.36, math.sin(a) * 0.4, 0.0), n=8, h=(0.04, 0.1))
    parts += [acc.obj('menhir', m), dry.obj('dead_grass', T.foliage('blight_grass', color='#221d22', tip='#4a4046', seed=4), smooth=False)]
    parts.append(K.glow('menhir_light', light_at, T.BLIGHT, 2.5, radius=0.05))
    parts.append(K.glow('menhir_light2', (light_at[0] + 0.25, 0.1, light_at[2] + 0.4), T.BLIGHT, 1.2, radius=0.05))
    hz = K.sphere('menhir_bloom', (0.0, 0.0, 0.55), 0.46, M.halo('menhir_bloom', '#a070e8', 0.55, 0.16, falloff=2.2), seg=24, rings=14)
    hz.scale = (0.8, 0.8, 1.45)
    hz.visible_shadow = False
    parts.append(hz)
    return T.parent(parts, T.root('menhir'))


# ================================================================ Blight-nest
def nest(n=1):
    rnd = np.random.default_rng(801)
    nz = T.Field(131)
    H, R = 0.74, 0.3
    seg, rings = 144, 90
    th = np.linspace(-math.pi, math.pi, seg + 1)          # 0 faces the camera (-Y)
    t = np.linspace(0.0, 1.0, rings + 1)
    TH, TT = np.meshgrid(th, t, indexing='ij')
    lo = 0.82 + 0.18 * np.sqrt(np.clip(1.0 - ((0.4 - TT) / 0.4) ** 2, 0.0, 1.0))
    hi = np.sqrt(np.clip(1.0 - ((TT - 0.4) / 0.6) ** 2, 0.0, 1.0)) ** 0.85
    prof = np.where(TT < 0.4, lo, hi)
    r = R * prof * (1.0 + 0.07 * np.cos(7.0 * TH + 2.5 * np.sin(3.0 * TT)))
    th0 = 0.18
    dth = TH - th0
    w = 0.02 + 0.2 * np.sin(np.pi * np.clip((TT - 0.14) / 0.74, 0.0, 1.0)) ** 0.7 * (1.0 + 0.3 * np.sin(TT * 23.0))
    inside = np.clip(1.0 - (dth / w) ** 2, 0.0, 1.0) * ((TT > 0.14) & (TT < 0.88))
    lip = np.exp(-((np.abs(dth) - w * 1.25) / (w * 0.45)) ** 2) * ((TT > 0.12) & (TT < 0.9))
    r = r * (1.0 - 0.42 * inside ** 0.7 + 0.1 * lip)
    X = r * np.sin(TH) + 0.07 * TT ** 2
    Y = -r * np.cos(TH)
    Z = H * TT
    V = np.stack((X, Y, Z), axis=-1).reshape(-1, 3)
    d = (nz(V, 5.0, 4) - 0.5) * 0.09 + (nz(V + 4.0, 18.0, 3) - 0.5) * 0.025
    rad = T.unit(V * (1.0, 1.0, 0.25) - (0.0, 0.0, 0.05))
    keep = (1.0 - 0.8 * inside.reshape(-1))
    V = V + rad * (d * keep)[:, None]
    Vg = V.reshape(seg + 1, rings + 1, 3)
    Vg[-1] = Vg[0]
    V = Vg.reshape(-1, 3)
    m_ = rings + 1
    i, k = np.meshgrid(np.arange(seg), np.arange(rings), indexing='ij')
    q0 = (i * m_ + k).ravel()
    F = np.concatenate((np.column_stack((q0, q0 + m_, q0 + m_ + 1)), np.column_stack((q0, q0 + m_ + 1, q0 + 1))))
    fin = inside.reshape(-1)[F].mean(axis=1)
    pod = T.Acc()
    pod.add(V, F[fin <= 0.45], mi=0)
    pod.add(V, F[fin > 0.45], mi=1)
    src = (R * 0.8 * math.sin(th0), -R * 0.8 * math.cos(th0), H * 0.45)
    fl = T.flesh('nest_flesh', src, reach=0.5, glow=6.0, color='#513a45', seed=90)
    core = M.emissive('nest_core', '#b98cf0', 3.2)
    # tendrils rooting it, and climbing it
    for j in range(9):
        a = 2.0 * math.pi * j / 9 + rnd.uniform(-0.25, 0.25)
        L = rnd.uniform(0.2, 0.42) * (0.75 if math.sin(a) > 0.5 else 1.0)
        s = np.linspace(0.0, 1.0, 12)
        rr = R * 0.7 + L * s
        aa = a + 0.5 * np.sin(s * rnd.uniform(3.0, 6.0) + rnd.uniform(0, 3)) * s
        P = np.column_stack((np.cos(aa) * rr, np.sin(aa) * rr * 1.1, 0.07 * (1.0 - s) ** 2 + 0.012 + 0.02 * np.sin(s * 9.0) ** 2 * (1 - s)))
        pod.add(*T.tube(P, np.linspace(0.045, 0.007, 12) * rnd.uniform(0.8, 1.2), seg=8, nz=nz, rough=0.25, rough_scale=20.0, cap1=True), mi=0)
    for (x, y, s) in ((-0.3, -0.22, 0.1), (0.33, -0.12, 0.08), (0.22, 0.26, 0.11)):     # young pods at its foot
        pod.add(*T.ellipsoid((x, y, s * 0.8), (s, s, s * 1.25), seg=18, rings=12, nz=nz, rough=0.2, scale=9.0), mi=0)
    parts = [pod.obj('nest', [fl, core])]
    # bones at its foot
    bn, dk = T.Acc(), T.Acc()
    skull(bn, dk, (-0.2, -0.56, 0.0), yaw=0.5, s=1.0)
    long_bone(bn, (0.1, -0.6, 0.022), (0.5, -0.5, 0.022), 0.02)
    long_bone(bn, (0.42, -0.34, 0.02), (0.62, -0.62, 0.02), 0.017)
    long_bone(bn, (-0.62, -0.3, 0.02), (-0.42, -0.52, 0.05), 0.018)
    for j in range(4):      # a few ribs
        a = np.linspace(0.0, math.pi * 0.9, 8)
        P = np.column_stack((0.3 + 0.045 * j + 0.0 * a, -0.72 + 0.11 * np.cos(a), 0.01 + 0.1 * np.sin(a)))
        bn.add(*T.tube(P, np.linspace(0.011, 0.006, 8), seg=5, cap1=True))
    bn.apply(None, (0, 0, 0), FIG)
    dk.apply(None, (0, 0, 0), FIG)
    parts.append(bn.obj('bones', T.bone('nest_bone', seed=3)))
    parts.append(dk.obj('sockets', G.flat('socket', '#0b0908')))
    parts.append(K.glow('nest_light', (src[0] * 1.6, src[1] * 1.6, src[2]), T.BLIGHT, 2.0, radius=0.05))
    hz = K.sphere('nest_bloom', (src[0] * 0.9, src[1] * 0.9, src[2]), 0.3, M.halo('nest_bloom', '#a070e8', 0.6, 0.2, falloff=2.2), seg=24, rings=14)
    hz.scale = (0.8, 0.8, 1.3)
    hz.visible_shadow = False
    parts.append(hz)
    return T.parent(parts, T.root('nest'))


# ================================================================ the escort wagon
def wagon(n=1):
    rnd = np.random.default_rng(901)
    nz = T.Field(141)
    wood_m = T.timber('wagon_wood', color='#4b3a2a', seed=5, axis='x', mud=1.3, mud_h=0.2, wear=0.55)
    wheel_m = T.timber('wagon_wheel', color='#3f3125', seed=6, axis='z', mud=1.6, mud_h=0.3, wear=0.4)
    iron = G.steel('wagon_iron', color='#45423e', rust=1.2, blood=0.0, seed=7, edge=0.4, scratch=0.5, dirt=0.9)
    body, wh = T.Acc(), T.Acc()
    Rw = 0.55
    for sy in (-1, 1):
        wh.merge(wheel(nz, R=Rw, spokes=10).apply(_ry(rnd.uniform(0, 1.0)), (0.0, sy * 0.64, Rw)))
    wh.add(*T.tube(np.array(((0, -0.7, Rw), (0, 0.7, Rw))), 0.045, seg=8), mi=0)
    z0 = 0.72
    boards(body, nz, (0, 0, z0), (1.5, 1.0, 0.05), 5, 'y')                            # the bed
    for sy in (-1, 1):                                                                # sides
        boards(body, nz, (0, sy * 0.5, z0 + 0.24), (1.5, 0.035, 0.42), 3, 'z', gap=0.012)
        for sx in (-1, 1):
            body.add(*T.block((sx * 0.72, sy * 0.5, z0 + 0.22), (0.06, 0.07, 0.52), bev=0.008, grid=0.1, nz=nz, rough=0.003))
    boards(body, nz, (0.75, 0, z0 + 0.24), (0.035, 1.0, 0.42), 3, 'z', gap=0.012)     # headboard
    boards(body, nz, (-0.75, 0, z0 + 0.12), (0.035, 1.0, 0.2), 2, 'z', gap=0.012)     # tailboard, low
    for sy in (-1, 1):                                                                # bolsters down to the axle
        body.add(*T.block((0, sy * 0.4, z0 - 0.08), (0.12, 0.08, 0.13), bev=0.008, grid=0.1))
    for sy in (-1, 1):                                                                # the shafts, resting on the ground
        P = np.array(((0.3, sy * 0.42, z0 - 0.04), (0.78, sy * 0.4, z0 - 0.05), (1.15, sy * 0.36, 0.34), (1.45, sy * 0.33, 0.05)))
        body.add(*T.tube(P, (0.04, 0.04, 0.036, 0.03), seg=8, cap1=True))
    body.add(*T.tube(np.array(((1.2, -0.37, 0.27), (1.2, 0.37, 0.27))), 0.028, seg=6, cap0=True, cap1=True))
    # the tilt: canvas over four hoops, sagging between them
    nu, nv = 41, 33
    u = np.linspace(-0.8, 0.8, nu)
    v = np.linspace(-0.2, math.pi + 0.2, nv)
    U, Vv = np.meshgrid(u, v, indexing='ij')
    sag = np.sin(np.pi * (U + 0.8) / (1.6 / 3.0)) ** 2
    rr = 1.0 - 0.06 * sag * np.clip(np.sin(Vv), 0.0, 1.0)
    Yc = 0.535 * np.cos(Vv) * (1.0 + 0.0 * rr)
    Zc = z0 + 0.45 + 0.66 * np.sign(np.sin(Vv)) * np.abs(np.sin(Vv)) ** 0.8 * rr
    P = np.column_stack((U.ravel(), Yc.ravel(), Zc.ravel()))
    P[:, 2] += (nz(P, 7.0, 3) - 0.5) * 0.045
    P[:, 1] += (nz(P + 3.0, 5.0, 3) - 0.5) * 0.03
    i, k = np.meshgrid(np.arange(nu - 1), np.arange(nv - 1), indexing='ij')
    q0 = (i * nv + k).ravel()
    tilt = T.Acc()
    tilt.add(P, np.concatenate((np.column_stack((q0, q0 + nv, q0 + nv + 1)), np.column_stack((q0, q0 + nv + 1, q0 + 1)))))
    canvas = G.cloth('wagon_tilt', color='#8d846c', blood=0.0, mud=0.6, grime=0.9, seed=8,
                     patches=(0.2, 0.22, ('#6f6753', '#7a6c50', '#5d574a')))
    tilt_ob = tilt.obj('tilt', canvas)
    so = tilt_ob.modifiers.new('solid', 'SOLIDIFY')
    so.thickness = 0.012
    hoops = T.Acc()
    for x in (-0.79, -0.265, 0.265, 0.79):
        a = np.linspace(-0.2, math.pi + 0.2, 18)
        Ph = np.column_stack((np.full(18, x), 0.52 * np.cos(a), z0 + 0.45 + 0.645 * np.sign(np.sin(a)) * np.abs(np.sin(a)) ** 0.8))
        hoops.add(*T.tube(Ph, 0.018, seg=6))
    # the load: sacks and a keg in the tail
    load = T.Acc()
    sack(load, nz, (-0.5, -0.2, z0 + 0.02), size=(0.2, 0.19, 0.24), yaw=0.4)
    sack(load, nz, (-0.42, 0.22, z0 + 0.02), size=(0.22, 0.2, 0.26), yaw=1.4)
    sack(load, nz, (-0.05, 0.0, z0 + 0.02), size=(0.24, 0.22, 0.3), yaw=2.0)
    sack_m = G.cloth('sack', color='#75684f', blood=0.0, mud=0.8, grime=0.9, seed=9)
    parts = [body.obj('wagon_body', wood_m, weld=0.0005), wh.obj('wagon_wheels', [wheel_m, iron]), tilt_ob,
             hoops.obj('hoops', wood_m), load.obj('load', sack_m)]
    return _scaled(parts, 0.55, turn=14.0, at=(-0.2, -0.02))


# ================================================================ a supply cache
def cache(n=1):
    rnd = np.random.default_rng(1001)
    nz = T.Field(151)
    wood_m = T.timber('chest_wood', color='#4f3b27', seed=11, axis='x', mud=1.0, mud_h=0.08, wear=0.35)
    iron = G.steel('chest_iron', color='#4a4743', rust=0.9, blood=0.0, seed=12, edge=0.7, scratch=0.6, dirt=0.8)
    brass = G.brass('chest_brass', color='#6f5a2d', tarnish=0.9, blood=0.0, seed=13)
    ch, ir = T.Acc(), T.Acc()
    W, D, Hh = 0.84, 0.52, 0.4
    boards(ch, nz, (0, -D / 2, Hh / 2 + 0.02), (W, 0.03, Hh), 3, 'z')
    boards(ch, nz, (0, D / 2, Hh / 2 + 0.02), (W, 0.03, Hh), 3, 'z')
    for sx in (-1, 1):
        ch.add(*T.block((sx * W / 2, 0, Hh / 2 + 0.02), (0.03, D, Hh), bev=0.006, grid=0.09, nz=nz, rough=0.003))
    ch.add(*T.block((0, 0, 0.035), (W, D, 0.03), bev=0.006, grid=0.09))
    # the lid: a barrel top of staves
    nst = 7
    for k in range(nst):
        a0, a1 = math.pi * k / nst, math.pi * (k + 1) / nst
        am = (a0 + a1) / 2
        V, F = T.block((0, 0, 0), (W + 0.02, 2 * (D / 2 + 0.01) * math.sin((a1 - a0) / 2) * 1.02, 0.028), bev=0.006, grid=0.09, nz=nz, rough=0.003)
        V = _rot(V, _rx(am - math.pi / 2), (0, (D / 2) * math.cos(am), Hh + 0.03 + 0.19 * math.sin(am)))
        ch.add(V, F)
    for sx in (-1, 1):      # lid ends
        V, F = T.ellipsoid((sx * (W / 2), 0, Hh + 0.03), (0.012, D / 2 - 0.005, 0.185), seg=16, rings=8)
        V[:, 2] = np.maximum(V[:, 2], Hh + 0.03)
        ch.add(V, F)
    for x in (-0.3, 0.0, 0.3):      # iron bands up the front, over the lid and down the back
        a = np.linspace(0.0, math.pi, 12)
        arc = np.column_stack((np.full(12, x), -(D / 2 + 0.022) * np.cos(a), Hh + 0.03 + 0.212 * np.sin(a)))
        P = np.vstack(([[x, -D / 2 - 0.022, 0.03]], arc, [[x, D / 2 + 0.022, 0.03]]))
        ir.add(*T.tube(P, 0.034, seg=6, squash=0.22))
    for sx in (-1, 1):
        for sy in (-1, 1):
            ir.add(*T.block((sx * W / 2, sy * D / 2, Hh / 2 + 0.02), (0.045, 0.045, Hh + 0.01), bev=0.005, grid=0.2))
    parts = [ch.obj('chest', wood_m, weld=0.0005), ir.obj('bands', iron, weld=0.0005)]
    parts.append(K.rbox('lock', (0.1, 0.022, 0.13), (0.0, -D / 2 - 0.03, Hh - 0.02), brass, bev=0.004))
    load = T.Acc()
    sack(load, nz, (-0.66, 0.05, 0.0), size=(0.23, 0.21, 0.27), yaw=0.3)
    sack(load, nz, (0.5, -0.46, 0.0), size=(0.22, 0.2, 0.3), yaw=0.5, lying=True)
    sack(load, nz, (-0.5, -0.36, 0.0), size=(0.19, 0.18, 0.22), yaw=1.9)
    parts.append(load.obj('sacks', G.cloth('sack', color='#7b6d53', blood=0.0, mud=1.2, grime=0.9, seed=9)))
    bw, bi = barrel(nz, r=0.15, h=0.42, staves=12)
    for a_ in (bw, bi):
        a_.apply(None, (0.66, 0.1, 0.0))
    parts.append(bw.obj('keg', T.timber('keg_wood', color='#54402b', seed=14, axis='z', mud=1.0, mud_h=0.08)))
    parts.append(bi.obj('keg_hoops', iron))
    return _scaled(parts, FIG, turn=-9.0, at=(0.0, 0.02))


# ================================================================ the fallen
def _height(prims, X, Y):
    Z = np.zeros_like(X)
    for (cx, cy, cz, rx, ry, rz_) in prims:
        q = 1.0 - ((X - cx) / rx) ** 2 - ((Y - cy) / ry) ** 2
        Z = np.maximum(Z, np.where(q > 0, cz + rz_ * np.sqrt(np.clip(q, 0, 1)), 0.0))
    return Z


def _limb(a, b, r0, r1, z0, z1, n=6):
    """Ellipsoid beads along a limb (for the height field)."""
    out = []
    for s in np.linspace(0.0, 1.0, n):
        r = r0 + (r1 - r0) * s
        out.append((a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s, z0 + (z1 - z0) * s, r, r * 1.3, r))
    return out


def _blur(Z):
    P = np.pad(Z, 1, mode='edge')
    return (P[:-2, 1:-1] + P[2:, 1:-1] + P[1:-1, :-2] + P[1:-1, 2:] + 4.0 * Z + P[:-2, :-2] + P[2:, 2:] + P[:-2, 2:] + P[2:, :-2]) / 12.0


def drape(prims, nz, bounds, hem, res=0.014, tent=14, wrinkle=0.022, seed_off=0.0):
    """Cloth lying over a body on the ground: the body's height field, tented outward, wrinkled, cut to a ragged
    outline (hem(X, Y) > 0 is cloth). (V, F), metres."""
    x0, x1, y0, y1 = bounds
    xs = np.arange(x0, x1 + res, res)
    ys = np.arange(y0, y1 + res, res)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    Zb = _height(prims, X, Y)
    Z = Zb.copy()
    for _ in range(tent):
        Z = np.maximum(Z, _blur(Z) * 0.985)
    for _ in range(2):
        Z = _blur(Z)
    P = np.column_stack((X.ravel(), Y.ravel(), np.zeros(X.size)))
    wr = (nz(P + seed_off, 7.0, 3) - 0.5) * 2.0 * wrinkle + (nz(P * (3.0, 1.0, 1.0) + 7.0 + seed_off, 9.0, 2) - 0.5) * wrinkle
    Zf = Z.ravel()
    Zf = np.maximum(Zf + wr * np.clip(Zf / 0.05, 0.0, 1.0) * (0.4 + 0.6 * np.clip(1.0 - Zb.ravel() / 0.12, 0.0, 1.0)), 0.0) + 0.006
    rag = (nz(P + 11.0 + seed_off, 11.0, 3) - 0.5) * 0.09
    inside = ((hem(X, Y).ravel() + rag) > 0) & (Z.ravel() > 0.012)
    V = np.column_stack((X.ravel(), Y.ravel(), Zf))
    ny = len(ys)
    i, k = np.meshgrid(np.arange(len(xs) - 1), np.arange(ny - 1), indexing='ij')
    q0 = (i * ny + k).ravel()
    ok = inside[q0] & inside[q0 + ny] & inside[q0 + ny + 1] & inside[q0 + 1]
    q0 = q0[ok]
    F = np.concatenate((np.column_stack((q0, q0 + ny, q0 + ny + 1)), np.column_stack((q0, q0 + ny + 1, q0 + 1))))
    return V, F, (xs, ys, Z)


def corpse(n):
    rnd = np.random.default_rng(1100 + n)
    nz = T.Field(160 + n)
    # the body, face down, head to +Y (metres)
    head = (0.0, 0.8, 0.02, 0.105, 0.125, 0.19)
    torso = [(0.0, 0.5, 0.02, 0.25, 0.22, 0.2), (0.0, 0.3, 0.02, 0.21, 0.28, 0.2), (0.0, 0.02, 0.02, 0.2, 0.24, 0.19)]
    legs = _limb((-0.1, -0.1), (-0.17, -0.55), 0.09, 0.07, 0.07, 0.05) + _limb((0.1, -0.1), (0.2, -0.5), 0.09, 0.07, 0.07, 0.05)
    shins = [((-0.17, -0.55), (-0.2, -1.0)), ((0.2, -0.5), (0.36, -0.9))]
    parts = []
    cloth, limbs, boots, skin_a = T.Acc(), T.Acc(), T.Acc(), T.Acc()
    bone_m = None
    if n == 2:      # shrouded head to foot and corded
        prims = [head] + torso + legs
        for a, b in shins:
            prims += _limb(a, b, 0.07, 0.06, 0.05, 0.05)
        prims += [(-0.2, -1.02, 0.03, 0.06, 0.07, 0.13), (0.36, -0.94, 0.03, 0.06, 0.07, 0.13)]
        prims += _limb((-0.25, 0.5), (-0.1, 0.12), 0.06, 0.05, 0.14, 0.15) + _limb((0.25, 0.5), (0.08, 0.16), 0.06, 0.05, 0.14, 0.16)
        V, F, (xs, ys, Zg) = drape(prims, nz, (-0.5, 0.62, -1.25, 1.05), lambda X, Y: np.full_like(X, 1.0), tent=7, wrinkle=0.02)
        cloth.add(V, F)
        cords = T.Acc()
        for yy in (0.66, 0.36, -0.1, -0.52, -0.9):       # cords binding it
            j = int(np.argmin(np.abs(ys - yy)))
            zz = Zg[:, j]
            on = zz > 0.03
            if on.sum() > 3:
                P = np.column_stack((xs[on], np.full(on.sum(), yy) + 0.02 * np.sin(xs[on] * 9.0), zz[on] + 0.012))
                cords.add(*T.tube(P[::2], 0.011, seg=5))
        cloth_m = G.cloth('shroud', color='#a69c84', blood=1.4, mud=2.2, grime=1.0, seed=21)
        parts.append(cords.obj('cords', G.cloth('rope', color='#5f5443', blood=0.1, mud=1.0, grime=0.6, seed=61)))
        sh = K.kite_shield('shield', 0.5, 0.82, G.planks('corpse_shield', paint='#5d2a22', wood='#55412d', plank=0.1, chip=0.6, blood=0.5, mud=1.4, seed=23),
                           G.steel('shield_rim', color='#4f4d4a', rust=1.0, blood=0.3, seed=24), thick=0.016, curve=1.2)
        sh.matrix_world = Matrix.Translation(Vector((0.68, -0.1, 0.08))) @ Matrix.Rotation(math.radians(24), 4, 'Z') @ \
            Matrix.Rotation(math.radians(-82), 4, 'X')
        parts.append(sh)
        pool = ((-0.42, 0.3), 0.3)
    else:           # under his cloak: boots and a forearm showing
        arm_out = [(0.26, 0.56), (0.5, 0.6), (0.62, 0.88)] if n == 1 else [(-0.26, 0.56), (-0.5, 0.42), (-0.56, 0.12)]
        arm_in = _limb((-0.25, 0.52), (-0.3, 0.1), 0.065, 0.05, 0.06, 0.05) if n == 1 else _limb((0.25, 0.52), (0.32, 0.12), 0.065, 0.05, 0.06, 0.05)
        prims = [head] + torso + legs + arm_in + _limb(arm_out[0], arm_out[1], 0.07, 0.06, 0.06, 0.05)
        hem_y = -0.42 if n == 1 else -0.62
        V, F, _g = drape(prims, nz, (-0.62, 0.72, -0.85, 1.08),
                         lambda X, Y: np.minimum(Y - hem_y + 0.25 * np.abs(X), 0.6 - np.abs(X) - 0.2 * np.clip(Y - 0.6, 0, 1)),
                         tent=16, wrinkle=0.028, seed_off=n * 5.0)
        cloth.add(V, F)
        cloth_m = G.cloth(f'cloak_{n}', color=('#3f3a34', '', '#4a211c')[n - 1], blood=0.9, mud=2.0, grime=0.9, seed=20 + n)
        for (a, b) in shins:        # shins and boots
            P = np.array(((a[0], a[1], 0.07), ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 0.06), (b[0], b[1], 0.055)))
            limbs.add(*T.tube(P[:2], (0.075, 0.065), seg=10))
            boots.add(*T.tube(P[1:], (0.068, 0.06), seg=10))
            dx = 0.07 if b[0] > 0 else -0.07
            boots.add(*T.ellipsoid((b[0] + dx * 0.6, b[1] - 0.03, 0.05), (0.1, 0.055, 0.05), seg=12, rings=8))
        a1, a2 = np.array((*arm_out[1], 0.05)), np.array((*arm_out[2], 0.035))
        limbs.add(*T.tube(np.array((a1, a2)), (0.055, 0.045), seg=10))
        skin_a.add(*T.ellipsoid(a2 + (a2 - a1) / np.linalg.norm(a2 - a1) * 0.05, (0.05, 0.06, 0.022), seg=12, rings=8))
        parts.append(limbs.obj('limbs', G.cloth('corpse_wool', color='#2d2a26', blood=0.5, mud=2.4, grime=0.9, seed=25)))
        parts.append(boots.obj('boots', G.leather('corpse_boots', color='#2a1f17', mud=1.8, seed=26)))
        parts.append(skin_a.obj('hand', G.flat('dead_hand', '#7d7867', rough=0.7)))
        steel = G.steel('corpse_steel', color='#5a5b5c', rust=0.5, blood=0.8, seed=27)
        if n == 1:      # his sword, a hand's breadth from his fingers
            parts += K.sword('sword', Vector((0.52, 1.02, 0.02)), (-0.9, 0.35, 0.0),
                             (steel, G.leather('grip', color='#2e2219', seed=41), G.brass('pommel', color='#6f5a2d', seed=14)),
                             blade_len=0.74, blade_w=0.046, grip=0.1)
            pool = ((0.34, 0.2), 0.3)
        else:           # arrows in his back
            arr, fl = T.Acc(), T.Acc()
            for (x, y, lx, ly) in ((0.06, 0.42, 0.25, -0.5), (-0.08, 0.2, -0.3, -0.35), (0.12, 0.05, 0.1, -0.6)):
                base = np.array((x, y, 0.2))
                d = T.unit(np.array((lx, ly, 1.0)))
                tip = base + d * 0.52
                arr.add(*T.tube(np.array((base - d * 0.05, tip)), 0.008, seg=5, cap1=True))
                for a_ in (0.0, 2.1, 4.2):
                    side = T.unit(np.cross(d, (math.cos(a_), math.sin(a_), 0.3)))
                    k = 5
                    s = np.linspace(0.36, 0.5, k)
                    fl.add(*T.blades(base[None, :] + d[None, :] * s[:, None], np.tile(side, (k, 1)), np.tile(np.cross(d, side), (k, 1)), 0.035, 0.045))
            parts.append(arr.obj('arrows', T.timber('arrow_shaft', color='#6a5a40', seed=28, axis='z', mud=0.0)))
            parts.append(fl.obj('fletch', G.flat('fletch', '#8a8272', rough=0.9), smooth=False))
            pool = ((-0.3, 0.28), 0.34)
    parts.append(cloth.obj('cloth', cloth_m))
    pl = T.Acc()
    pl.add(*T.disc(pool[1], n=56, z=0.004, nz=nz, wobble=0.35, centre=pool[0], sy=1.15, scale=1.6))
    pl.add(*T.disc(pool[1] * 0.4, n=30, z=0.0045, nz=nz, wobble=0.4, centre=(pool[0][0] + pool[1] * 1.0, pool[0][1] - pool[1] * 0.7), scale=2.0))
    pob = pl.obj('blood', T.gore())
    pob.visible_shadow = False
    parts.append(pob)
    return _scaled(parts, FIG, turn=(-24.0, 18.0, 30.0)[n - 1], at=((0.02, -0.02), (-0.06, 0.0), (0.02, 0.0))[n - 1])


# ================================================================ the scatter kit
def deco(kind, n=1):
    rnd = np.random.default_rng(1300 + sum(map(ord, kind)) + n)
    nz = T.Field(170 + sum(map(ord, kind)) % 50 + n)
    parts = []
    scale, turn = FIG, 0.0
    grass = T.Acc()
    if kind == 'rock':
        acc = T.Acc()
        if n == 1:
            for (x, y, s) in ((-0.1, 0.05, 0.52), (0.28, -0.14, 0.3), (0.0, -0.3, 0.2), (-0.36, -0.2, 0.14)):
                V, F = T.rock(rnd, (s, s * 0.85, s * 0.7), n=14, cuts=3, rough=0.07, nz=nz)
                acc.add(_rot(V, _rz(rnd.uniform(0, 3))) + (x, y, s * 0.2), F)
        else:
            for _ in range(11):
                a, rr = rnd.uniform(0, 6.283), rnd.uniform(0.0, 0.42)
                s = rnd.uniform(0.1, 0.28)
                V, F = T.rock(rnd, (s, s * 0.85, s * 0.6), n=12, cuts=3, rough=0.07, nz=nz)
                acc.add(_rot(V, _rz(rnd.uniform(0, 3))) + (math.cos(a) * rr, math.sin(a) * rr, s * 0.16), F)
        acc.V = [np.column_stack((v[:, 0], v[:, 1], np.maximum(v[:, 2], -0.01))) for v in acc.V]
        parts.append(acc.obj('rocks', T.stone(f'deco_rock_{n}', color='#66635b', color2='#3f3e3a', moss=0.45, lichen=0.6,
                                               cracks=0.5, seed=95 + n, scale=1.6, mud_h=0.06)))
        for _ in range(5):
            a = rnd.uniform(0, 6.283)
            _tuft(grass, rnd, (math.cos(a) * 0.4, math.sin(a) * 0.4, 0.0), n=9, h=(0.08, 0.2), base_r=0.03, width=0.02)
    elif kind in ('bones', 'skull'):
        bn, dk = T.Acc(), T.Acc()
        if kind == 'bones':     # a ribcage sunk in the ground, its long bones scattered
            for j in range(7):
                a = np.linspace(0.05, math.pi * 0.95, 10)
                w = 0.15 - 0.012 * abs(j - 3)
                P = np.column_stack((-0.2 + 0.065 * j + 0.02 * np.sin(a), w * np.cos(a) * 1.1, -0.01 + (0.17 - 0.01 * abs(j - 3)) * np.sin(a)))
                if j in (1, 5):
                    P = P[:6]
                bn.add(*T.tube(_rot(P, _rz(0.5)), np.linspace(0.013, 0.007, len(P)), seg=5, cap1=True))
            sp = np.column_stack((np.linspace(-0.26, 0.26, 9), np.zeros(9), np.full(9, 0.012)))
            bn.add(*T.tube(_rot(sp, _rz(0.5), (0.07, -0.13, 0)), 0.02 * (1 + 0.3 * np.cos(np.arange(9) * 3.14)), seg=6, cap0=True, cap1=True))
            long_bone(bn, (-0.5, 0.2, 0.022), (-0.1, 0.42, 0.022), 0.022)
            long_bone(bn, (0.25, -0.42, 0.02), (0.55, -0.2, 0.02), 0.019)
            long_bone(bn, (-0.45, -0.3, 0.018), (-0.2, -0.45, 0.018), 0.016)
            skull(bn, dk, (0.42, 0.3, 0.0), yaw=-0.6)
        else:
            skull(bn, dk, (0.0, 0.0, 0.0), yaw=0.35, s=1.5, jaw=False, tilt=-0.15)
            a = T.Acc()        # its jaw lying apart
            arc = np.linspace(-1.2, 1.2, 9)
            a.add(*T.tube(np.column_stack((0.075 * np.sin(arc), -0.085 * np.cos(arc), np.full(9, 0.015))), 0.014, seg=5, cap0=True, cap1=True))
            bn.merge(a.apply(_rz(-0.5), (-0.26, -0.2, 0.0), 1.5))
            long_bone(bn, (0.16, -0.26, 0.02), (0.46, -0.12, 0.02), 0.02)
            long_bone(bn, (-0.36, 0.14, 0.018), (-0.2, 0.34, 0.018), 0.016)
        parts.append(bn.obj('bones', T.bone('deco_bone', seed=5)))
        parts.append(dk.obj('sockets', G.flat('socket', '#0b0908')))
        for _ in range(4):
            a = rnd.uniform(0, 6.283)
            _tuft(grass, rnd, (math.cos(a) * 0.35, math.sin(a) * 0.35, 0.0), n=8, h=(0.08, 0.18), base_r=0.03, width=0.02)
    elif kind == 'barrel':
        bw, bi = barrel(nz)
        parts.append(bw.obj('barrel', T.timber('barrel_wood', color='#523f2b', seed=31, axis='z', mud=1.2, mud_h=0.1)))
        parts.append(bi.obj('hoops', G.steel('barrel_iron', color='#45423e', rust=1.2, blood=0.0, seed=32, edge=0.5, dirt=0.9)))
    elif kind == 'crate':
        cr = T.Acc()
        W, D, Hh = 0.62, 0.5, 0.44
        boards(cr, nz, (0, 0, Hh), (W, D, 0.025), 4, 'y', skip=(2,))
        boards(cr, nz, (0, -D / 2, Hh / 2), (W, 0.025, Hh), 4, 'z')
        boards(cr, nz, (0, D / 2, Hh / 2), (W, 0.025, Hh), 4, 'z')
        for sx in (-1, 1):
            boards(cr, nz, (sx * W / 2, 0, Hh / 2), (0.025, D, Hh), 4, 'z')
            for sy in (-1, 1):
                cr.add(*T.block((sx * (W / 2 - 0.02), sy * (D / 2 + 0.014), Hh / 2), (0.07, 0.025, Hh + 0.02), bev=0.005, grid=0.1))
        V, F = T.block((0, 0, 0), (W * 0.95, 0.11, 0.025), bev=0.006, grid=0.09, nz=nz, rough=0.003)     # the prised board
        cr.add(_rot(V, _rz(0.5) @ _ry(-0.25), (0.3, -0.42, 0.09)), F)
        parts.append(cr.obj('crate', T.timber('crate_wood', color='#59472f', seed=33, axis='x', mud=1.2, mud_h=0.1), weld=0.0005))
        parts.append(K.rbox('crate_in', (W - 0.04, D - 0.04, Hh - 0.06), (0, 0, Hh / 2 - 0.02), G.flat('crate_dark', '#0d0b09'), bev=0.0))
        turn = 18.0
    elif kind == 'wheel':
        w = wheel(nz, R=0.52, spokes=10, missing=(2, 3, 7), gap=(0.9, 5.6))
        w.apply(_ry(0.12) @ _rx(math.pi / 2 - 0.1), (0.0, 0.0, 0.1))
        for v in w.V:
            v[:, 2] = np.maximum(v[:, 2], -0.01)
        parts.append(w.obj('wheel', [T.timber('wheel_wood', color='#43352a', seed=34, axis='z', mud=1.6, mud_h=0.06, moss=0.4),
                                     G.steel('wheel_iron', color='#45423e', rust=1.4, blood=0.0, seed=35, edge=0.4, dirt=0.9)]))
        for _ in range(6):
            a, rr = rnd.uniform(0, 6.283), rnd.uniform(0.1, 0.5)
            _tuft(grass, rnd, (math.cos(a) * rr, math.sin(a) * rr, 0.0), n=9, h=(0.1, 0.24), base_r=0.03, width=0.02)
    elif kind in ('stump', 'log'):
        wood, cut = T.Acc(), T.Acc()
        if kind == 'stump':
            zs = np.linspace(0.0, 0.42, 8)
            P = np.column_stack((0.01 * np.sin(zs * 9), np.zeros(8), zs))
            Rr = 0.24 + 0.1 * np.clip(1 - zs / 0.16, 0, 1) ** 2
            wood.add(*T.tube(P, Rr, seg=18, nz=nz, rough=0.16, rough_scale=6.0))
            V, F = T.disc(0.235, n=36, z=0.42, nz=nz, wobble=0.1, scale=3.0)
            V[:, 2] += (nz(V, 6.0, 2) - 0.5) * 0.05
            cut.add(V, F)
            sp = np.array(((0.12, 0.05, 0.4), (0.15, 0.08, 0.55), (0.17, 0.09, 0.66)))          # a splinter left standing
            wood.add(*T.tube(sp, (0.06, 0.035, 0.004), seg=6))
            T.roots(wood, rnd, nz, (0.0, 0.0), 0.3, n=6, reach=0.34)
        else:
            s = np.linspace(-0.62, 0.62, 12)
            P = np.column_stack((s, 0.04 * np.sin(s * 3.0), np.full(12, 0.17)))
            wood.add(*T.tube(P, 0.17 * (1.0 - 0.12 * (s + 0.62)), seg=18, nz=nz, rough=0.14, rough_scale=6.0))
            for end, sg in ((P[0], -1), (P[-1], 1)):
                V, F = T.disc(0.165 if sg < 0 else 0.14, n=30, z=0.0, nz=nz, wobble=0.08, scale=3.0)
                cut.add(_rot(V, _ry(sg * math.pi / 2), end + (sg * 0.003, 0, 0)), F)
            for (x, a_) in ((-0.2, 0.9), (0.25, 2.3)):      # branch stubs
                d = np.array((0.15, math.cos(a_), math.sin(a_)))
                o = np.array((x, 0.0, 0.17))
                wood.add(*T.tube(np.array((o, o + d * 0.3)), (0.05, 0.035), seg=8, cap1=True))
            wood.apply(_rz(0.35))
            cut.apply(_rz(0.35))
        parts.append(wood.obj(kind, T.bark(f'{kind}_bark', color='#3a3028', seed=36, moss=0.6, ridges=9.0, grain=3.0, lichen=0.5)))
        parts.append(cut.obj('cut', T.timber(f'{kind}_cut', color='#6c5a40', seed=37, axis='z', mud=0.3, wear=0.7, moss=0.3)))
        for _ in range(6):
            a = rnd.uniform(0, 6.283)
            _tuft(grass, rnd, (math.cos(a) * 0.42, math.sin(a) * 0.36, 0.0), n=9, h=(0.08, 0.2), base_r=0.03, width=0.02)
    elif kind == 'plank':
        pk = T.Acc()
        for (x, y, L, yaw, tilt, z) in ((0.0, 0.05, 0.95, 0.3, 0.0, 0.02), (-0.1, -0.18, 0.7, -0.5, 0.05, 0.04), (0.2, 0.22, 0.5, 1.2, -0.04, 0.045),
                                        (0.3, -0.3, 0.36, 0.1, 0.0, 0.02)):
            V, F = T.block((0, 0, 0), (L, 0.15, 0.03), bev=0.006, grid=0.05, nz=nz, rough=0.004)
            end = np.abs(V[:, 0]) > L / 2 - 0.05                                      # broken ends
            V[end, 0] += (nz(V[end] * (0, 1, 1) + x, 30.0, 2) - 0.5) * 0.09
            pk.add(_rot(V, _rz(yaw) @ _ry(tilt), (x, y, z)), F)
        parts.append(pk.obj('planks', T.timber('plank_wood', color='#54422d', seed=38, axis='x', mud=1.4, mud_h=0.03, wear=0.7), weld=0.0005))
    elif kind == 'reeds':
        rd, heads, stems = T.Acc(), T.Acc(), T.Acc()
        for _ in range(11):
            a, rr = rnd.uniform(0, 6.283), rnd.uniform(0.0, 0.34)
            o = (math.cos(a) * rr, math.sin(a) * rr, 0.0)
            _tuft(rd, rnd, o, n=9, h=(0.35, 0.8), spread=0.16, width=0.022, base_r=0.03)
            if rnd.uniform() < 0.7:
                tip = np.array(o) + (rnd.normal(0, 0.05), rnd.normal(0, 0.05), rnd.uniform(0.6, 0.9))
                stems.add(*T.tube(np.array((o, tip)), 0.008, seg=5))
                d = T.unit(tip - np.array(o))
                heads.add(*T.tube(np.array((tip - d * 0.02, tip + d * 0.12)), 0.022, seg=7, cap0=True, cap1=True))
        parts.append(rd.obj('reeds', T.foliage('reed', color='#3a3f1f', tip='#77703c', seed=41, dead='#7a6a3e', dead_share=0.35), smooth=False))
        parts.append(stems.obj('reed_stems', T.foliage('reed_stem', color='#4a4526', tip='#6a6236', seed=42)))
        parts.append(heads.obj('reed_heads', G.flat('reed_head', '#35261a', rough=0.95)))
    elif kind == 'fern':
        gr, st = T.Acc(), T.Acc()
        for j in range(13):
            b = 2.0 * math.pi * j / 13 + rnd.uniform(-0.2, 0.2)
            L, h = rnd.uniform(0.36, 0.6), rnd.uniform(0.2, 0.36)
            s = np.linspace(0.0, 1.0, 14)
            d = np.array((math.cos(b), math.sin(b), 0.0))
            P = d[None, :] * (0.03 + L * s)[:, None]
            P[:, 2] = h * np.sin(s * math.pi * rnd.uniform(0.6, 0.8)) ** 0.7
            st.add(*T.tube(P, np.linspace(0.008, 0.002, 14), seg=4))
            Tn = T.unit(np.gradient(P, axis=0))
            side = T.unit(np.cross(Tn, UP))
            idx = np.arange(2, 14)
            ln = L * 0.3 * np.sin(np.linspace(0.3, 1.0, len(idx)) * math.pi) + 0.02
            for sg in (-1.0, 1.0):
                Dl = T.unit(side[idx] * sg + Tn[idx] * 0.4 + UP * -0.1)
                gr.add(*T.blades(P[idx], Dl, UP + rnd.normal(0, 0.2, (len(idx), 3)), ln, ln * 0.32, bend=0.3))
        parts.append(gr.obj('fern', T.foliage('fern', color='#1f2e17', tip='#4a5a2a', seed=43, dead='#5a4424', dead_share=0.2), smooth=False))
        parts.append(st.obj('fern_stems', T.foliage('fern_stem', color='#2c3018', tip='#4a4a26', seed=44)))
    if not grass.empty():
        parts.append(grass.obj('grass', T.foliage('foot_grass', color='#2c2e17', tip='#5a5630', seed=4), smooth=False))
    return _scaled(parts, scale, turn=turn)


def build(v):
    M.set_mode(revenant=False)
    kind = v['kind']
    if kind == 'menhir':
        return menhir(v['n'])
    if kind == 'nest':
        return nest()
    if kind == 'wagon':
        return wagon()
    if kind == 'cache':
        return cache()
    if kind == 'corpse':
        return corpse(v['n'])
    return deco(kind, v.get('n', 1))
