"""TERRAIN. Wave 4: what stands on the battle map's ground (ASSETS.md #27-#29): trees, boulders, ruined wall blocks,
broken columns, standing stones, brush. One sprite per tile, on the house stage (gb/rig.py), built from the terrain kit
(gb/terrain.py).

A blighted northern land: ragged dark conifers, a gnarled broadleaf holding a few dark leaves, a dead tree; grey
lichened rock; walls of coursed rough stone, broken down, their tops a litter of rubble.

Walls fill their tile exactly (x in [-0.5, 0.5], y in [-0.707, 0.707] on the ground) with flush faces, so the sprites
of neighbouring wall tiles butt into one wall; they carry no ground shadow (it would fall on the neighbours).
"""
import math

import numpy as np

from gb import mat as M
from gb import terrain as T

VARIANTS = {}
for _k, _n in (('tree', 4), ('boulder', 3), ('wall', 4), ('column', 2), ('stone', 2), ('brush', 3)):
    for _i in range(1, _n + 1):
        VARIANTS[f'terr_{_k}_{_i}'] = dict(kind=_k, n=_i)

UP = np.array((0.0, 0.0, 1.0))


def _rot(V, R, t=(0.0, 0.0, 0.0)):
    return np.asarray(V) @ np.asarray(R).T + np.asarray(t)


def _rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array(((1, 0, 0), (0, c, -s), (0, s, c)), np.float64)


def _ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array(((c, 0, s), (0, 1, 0), (-s, 0, c)), np.float64)


def _rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array(((c, -s, 0), (s, c, 0), (0, 0, 1)), np.float64)


def _pebbles(acc, rnd, nz, n, r0, r1, size=(0.03, 0.08), centre=(0.0, 0.0), sy=1.3):
    """Small stones lying round a foot (in a ring r0..r1, deeper north-south than across, like the tile)."""
    for _ in range(n):
        a = rnd.uniform(0.0, 2.0 * math.pi)
        rr = rnd.uniform(r0, r1)
        s = rnd.uniform(*size)
        V, F = T.rock(rnd, (s, s * rnd.uniform(0.7, 1.2), s * 0.6), n=10, cuts=2, rough=0.08, nz=nz)
        V = _rot(V, _rz(rnd.uniform(0.0, 3.0)), (centre[0] + math.cos(a) * rr, centre[1] + math.sin(a) * rr * sy, s * 0.12))
        acc.add(V, F)


def _tuft(acc, rnd, at, n=14, h=(0.06, 0.14), spread=0.5, width=0.012, base_r=0.02):
    """A tuft of grass blades."""
    P = np.asarray(at, np.float64)[None, :] + np.column_stack((rnd.normal(0, base_r, n), rnd.normal(0, base_r, n), np.zeros(n)))
    D = T.unit(np.column_stack((rnd.normal(0, spread, n), rnd.normal(0, spread, n), np.ones(n))))
    Nn = np.column_stack((rnd.normal(0, 1, n), rnd.normal(0, 1, n), np.full(n, 0.2)))
    L = rnd.uniform(h[0], h[1], n)
    acc.add(*T.blades(P, D, Nn, L, width, bend=rnd.uniform(0.1, 0.5, n)))


# ================================================================ trees
def tree(n):
    rnd = np.random.default_rng(100 + n)
    nz = T.Field(40 + n)
    wood, green = T.Acc(), T.Acc()
    parts = []
    if n in (1, 2):
        bark = T.bark('conifer_bark', color='#3a2f27', seed=3 + n, moss=0.3, ridges=9.0, grain=3.0)
        needle = T.foliage('conifer_needles', color='#16231a', tip='#34452c', seed=5 + n, dead='#4a3a22', dead_share=0.1)
        if n == 1:
            T.conifer(wood, green, rnd, nz, base=(0.0, 0.0), H=1.3, R=0.4, lean=(0.03, 0.0), trunk_r=0.06, gap=0.14)
            T.roots(wood, rnd, nz, (0.0, 0.0), 0.06, n=5, reach=0.15)
        else:
            T.conifer(wood, green, rnd, nz, base=(-0.17, 0.12), H=1.2, R=0.3, lean=(-0.03, 0.0), trunk_r=0.045, gap=0.16)
            T.conifer(wood, green, rnd, nz, base=(0.2, -0.12), H=0.88, R=0.27, lean=(0.04, 0.0), trunk_r=0.04, gap=0.2,
                      bare=0.2)
            T.roots(wood, rnd, nz, (-0.17, 0.12), 0.045, n=4, reach=0.11)
            T.roots(wood, rnd, nz, (0.2, -0.12), 0.04, n=4, reach=0.1)
        parts.append(wood.obj('trunk', bark))
        parts.append(green.obj('needles', needle, smooth=False))
    else:
        dead = n == 4
        tips = []
        if dead:
            bark = T.bark('dead_bark', color='#3d3833', seed=9, moss=0.1, ridges=8.0, grain=2.5, lichen=0.5, pale='#8a8376')
            T.branching(wood, rnd, nz, (0.0, 0.0, 0.0), (0.06, 0.0, 1.0), 0.5, 0.075, 5, gnarl=0.3, lift=0.2,
                        shrink=0.68, kids=(2, 3), seg=10, tips=tips, snap=0.09)
            T.roots(wood, rnd, nz, (0.0, 0.0), 0.075, n=6, reach=0.2)
            print('fit', T.fit([wood], h_max=1.3, r_max=0.62))
        else:
            bark = T.bark('oak_bark', color='#372d25', seed=8, moss=0.45, ridges=7.0, grain=2.0, lichen=0.5)
            T.branching(wood, rnd, nz, (0.0, 0.0, 0.0), (-0.1, 0.0, 1.0), 0.5, 0.1, 4, gnarl=0.36, lift=0.13,
                        shrink=0.7, kids=(2, 3), seg=10, tips=tips)
            T.roots(wood, rnd, nz, (0.0, 0.0), 0.1, n=6, reach=0.22)
            for p, d in tips:
                if rnd.uniform() < 0.7:
                    T.leaf_cluster(green, rnd, p + d * 0.02, n=int(rnd.integers(30, 60)), spread=(0.15, 0.15, 0.08),
                                   size=(0.035, 0.06), width=0.6)
            print('fit', T.fit([wood, green], h_max=1.3, r_max=0.66))
            leaf = T.foliage('oak_leaves', color='#1f2614', tip='#414a25', seed=11, dead='#4f3a1f', dead_share=0.3)
            parts.append(green.obj('leaves', leaf, smooth=False))
        parts.append(wood.obj('trunk', bark))
    # a little ground at the foot: stones and grass, so the trunk doesn't stand on nothing
    stones, grass = T.Acc(), T.Acc()
    _pebbles(stones, rnd, nz, 5, 0.1, 0.3, size=(0.03, 0.07))
    for _ in range(6):
        a, rr = rnd.uniform(0, 6.283), rnd.uniform(0.08, 0.3)
        _tuft(grass, rnd, (math.cos(a) * rr, math.sin(a) * rr * 1.2, 0.0), n=10, h=(0.04, 0.1))
    parts.append(stones.obj('stones', T.stone('foot_stone', color='#5f5c54', moss=0.5, seed=3)))
    parts.append(grass.obj('grass', T.foliage('foot_grass', color='#2c2e17', tip='#5a5630', seed=4), smooth=False))
    return parts


# ================================================================ boulders
def boulder(n):
    rnd = np.random.default_rng(210 + n)
    nz = T.Field(60 + n)
    acc, small, grass = T.Acc(), T.Acc(), T.Acc()
    if n == 1:          # one great boulder
        V, F = T.rock(rnd, (1.02, 1.1, 0.95), n=18, cuts=4, rough=0.07, nz=nz, crag=0.05)
        acc.add(_rot(V, _rz(0.3), (0.0, -0.05, 0.25)), F)
        _pebbles(small, rnd, nz, 7, 0.4, 0.5, size=(0.04, 0.12))
    elif n == 2:        # an outcrop: tilted slabs breaking out of the ground
        for (x, y, sx, sy, sz, tilt, turn) in ((-0.14, 0.1, 0.55, 0.6, 1.0, 0.3, 0.2), (0.2, -0.1, 0.5, 0.6, 0.7, -0.25, -0.5),
                                               (-0.22, -0.3, 0.42, 0.42, 0.42, 0.4, 1.0), (0.24, 0.3, 0.4, 0.5, 0.5, 0.2, 2.0)):
            V, F = T.rock(rnd, (sx, sy, sz), n=12, cuts=4, rough=0.06, nz=nz, crag=0.08, smooth=1)
            acc.add(_rot(V, _rz(turn) @ _ry(tilt), (x, y, sz * 0.22)), F)
        _pebbles(small, rnd, nz, 6, 0.38, 0.5, size=(0.04, 0.1))
    else:               # a low boulder split in two, mossed over
        for (x, sx, turn) in ((-0.2, 0.5, 0.1), (0.24, 0.42, -0.2)):
            V, F = T.rock(rnd, (sx, 0.95, 0.6), n=16, cuts=4, rough=0.07, nz=nz, crag=0.03)
            acc.add(_rot(V, _rz(turn) @ _ry(0.12 * np.sign(x)), (x, -0.02, 0.16)), F)
        _pebbles(small, rnd, nz, 8, 0.1, 0.5, size=(0.04, 0.11))
    P = acc.points()
    acc.V = [np.column_stack((v[:, 0], v[:, 1], np.maximum(v[:, 2], -0.01))) for v in acc.V]
    for _ in range(8):
        a = rnd.uniform(0, 6.283)
        _tuft(grass, rnd, (math.cos(a) * 0.44, math.sin(a) * 0.56, 0.0), n=10, h=(0.05, 0.12))
    moss = (0.35, 0.2, 0.75)[n - 1]
    rock_m = T.stone(f'boulder_{n}', color=('#6b6860', '#5d5b57', '#66645a')[n - 1], color2='#3b3a37', moss=moss,
                     lichen=0.7, cracks=0.9, seed=20 + n, scale=1.0, mud_h=0.12)
    return [acc.obj('boulder', rock_m), small.obj('stones', T.stone('foot_stone', color='#5f5c54', moss=0.4, seed=3)),
            grass.obj('grass', T.foliage('foot_grass', color='#2c2e17', tip='#5a5630', seed=4), smooth=False)]


# ================================================================ walls
COURSES = (0.14, 0.13, 0.13, 0.12)      # 0.52 to the top of the fourth course
WALL_H = sum(COURSES)


def _wall_top(n, nz):
    """The height of the wall's broken top over its footprint, per variant: f(x, y) -> z (arrays)."""
    def base(x, y):
        P = np.column_stack((x, y, np.zeros_like(x)))
        return (nz(P, 2.2, 3) - 0.5) * 0.07

    if n == 1:          # the courses standing, a stone or two gone from the top
        return lambda x, y: WALL_H - 0.005 + base(x, y) * 0.6
    if n == 2:          # the south-east corner fallen away
        def f(x, y):
            d = np.hypot((x - 0.5) / 0.62, (y + T.FOOT_Y) / 0.8)
            k = np.clip((d - 0.35) / 0.65, 0.0, 1.0)
            return 0.17 + (WALL_H - 0.17) * k * k * (3 - 2 * k) + base(x, y)
        return f
    if n == 3:          # broken low and heaped with its own rubble
        def f(x, y):
            m = np.exp(-(((x + 0.08) / 0.3) ** 2 + ((y - 0.1) / 0.42) ** 2))
            return 0.4 + 0.17 * m + base(x, y) * 1.3
        return f

    def f(x, y):        # old and mossed, sagging in the middle
        return WALL_H - 0.04 - 0.07 * np.exp(-((x - 0.12) / 0.2) ** 2) + base(x, y)
    return f


def wall(n):
    T.no_ground_shadow()
    rnd = np.random.default_rng(320 + n)
    nz = T.Field(80 + n)
    top = _wall_top(n, nz)
    FY = T.FOOT_Y
    moss = (0.3, 0.3, 0.2, 0.6)[n - 1]
    # ---- the south face: coursed stones, flush at y = -FOOT_Y
    face = T.Acc()
    z = 0.0
    for ci, ch in enumerate(COURSES):
        x = -0.5 - rnd.uniform(0.04, 0.3)
        while x < 0.5:
            w = rnd.uniform(0.2, 0.4)
            xc = np.array([np.clip(x + w / 2, -0.5, 0.5)])
            t = float(top(xc, np.array([-FY + 0.1]))[0])
            if z + ch * 0.55 < t:
                h = min(ch, max(t - z, 0.06)) if ci == len(COURSES) - 1 or z + ch > t else ch
                if ci == len(COURSES) - 1:
                    h = ch * rnd.uniform(0.8, 1.08)
                dp = rnd.uniform(0.2, 0.32)
                V, F = T.block((x + w / 2, -FY + dp / 2, z + h / 2), (w - 0.012, dp, h - 0.012), bev=0.016, grid=0.028,
                               nz=nz, rough=0.009, inward='-y')
                face.add(V, F)
            x += w
        z += ch
    stone_m = T.stone(f'wall_stone_{n}', color='#6c6961', color2='#4b4944', moss=moss, lichen=0.5, cracks=0.5,
                      seed=30 + n, scale=1.6, island=0.28, mud=0.6, mud_h=0.08)
    face_ob = T.clip_tile(face.obj('wall_face', stone_m))
    wd = face_ob.modifiers.new('weld', 'WELD')
    wd.merge_threshold = 0.0004
    # ---- the core: packed rubble and mortar, a height field with a skirt, exactly the footprint
    nx, ny = 44, 60
    xs = np.linspace(-0.5, 0.5, nx)
    ys = np.linspace(-FY + 0.014, FY, ny)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    P0 = np.column_stack((X.ravel(), Y.ravel(), np.zeros(X.size)))
    Z = top(X.ravel(), Y.ravel()) - 0.06 + (nz(P0 + 3.0, 9.0, 3) - 0.5) * 0.05
    Vt = np.column_stack((X.ravel(), Y.ravel(), np.maximum(Z, 0.03)))
    i, k = np.meshgrid(np.arange(nx - 1), np.arange(ny - 1), indexing='ij')
    q0 = (i * ny + k).ravel()
    Ft = np.concatenate((np.column_stack((q0, q0 + ny, q0 + ny + 1)), np.column_stack((q0, q0 + ny + 1, q0 + 1))))
    core = T.Acc()
    core.add(Vt, Ft)
    ring = np.concatenate((np.arange(nx) * ny, (nx - 1) * ny + np.arange(ny), np.arange(nx - 1, -1, -1) * ny + ny - 1,
                           np.arange(ny - 1, -1, -1)))
    Vr = Vt[ring]
    Vs = np.vstack((Vr, Vr * (1.0, 1.0, 0.0)))
    m = len(ring)
    a = np.arange(m)
    b = (a + 1) % m
    core.add(Vs, np.concatenate((np.column_stack((a, b, b + m)), np.column_stack((a, b + m, a + m)))))
    core_ob = core.obj('wall_core', T.earth(f'wall_core_{n}', color='#3f3b34', seed=50 + n, moss=moss * 0.8))
    # ---- the top: loose rubble lying on the core
    rub = T.Acc()
    # big stones bedded close together (the wall's own hearting), then the loose rubble lying over them
    gx, gy = 5, 7
    for ix in range(gx + 2):
        for iy in range(gy + 1):
            x = -0.5 + (ix - 0.5 + (0.5 if iy % 2 else 0.0) + rnd.uniform(-0.25, 0.25)) / gx
            y = -FY + 0.24 + (iy + rnd.uniform(-0.25, 0.25)) * (2 * FY - 0.2) / gy
            sx, sy = rnd.uniform(0.2, 0.27), rnd.uniform(0.2, 0.27)
            zt = float(top(np.array([np.clip(x, -0.5, 0.5)]), np.array([np.clip(y, -FY, FY)]))[0])
            V, F = T.rock(rnd, (sx, sy, 0.13), n=12, cuts=3, rough=0.05, nz=nz, smooth=1)
            rub.add(_rot(V, _rz(rnd.uniform(0.0, 3.1)) @ _rx(rnd.uniform(-0.12, 0.12)), (x, y, zt - 0.012)), F)
    count = (34, 46, 90, 30)[n - 1]
    for _ in range(count):
        x, y = rnd.uniform(-0.56, 0.56), rnd.uniform(-FY + 0.2, FY + 0.05)
        s = rnd.uniform(0.07, 0.17)
        zt = float(top(np.array([np.clip(x, -0.5, 0.5)]), np.array([np.clip(y, -FY, FY)]))[0])
        V, F = T.rock(rnd, (s, s * rnd.uniform(0.7, 1.3), s * rnd.uniform(0.5, 0.8)), n=10, cuts=3, rough=0.06, nz=nz,
                      smooth=1)
        rub.add(_rot(V, _rz(rnd.uniform(0.0, 3.1)) @ _rx(rnd.uniform(-0.3, 0.3)), (x, y, zt + s * 0.2)), F)
    rub_m = T.stone(f'wall_rubble_{n}', color='#716e65', color2='#4b4944', moss=moss * 0.9, lichen=0.5, cracks=0.3,
                    seed=40 + n, scale=2.0, island=0.3, mud=0.0)
    rub_ob = T.clip_tile(rub.obj('wall_rubble', rub_m), south=True)
    parts = [face_ob, core_ob, rub_ob]
    if n == 4:          # grass and weeds rooted in the top
        gr = T.Acc()
        for _ in range(16):
            x, y = rnd.uniform(-0.44, 0.44), rnd.uniform(-FY + 0.12, FY - 0.08)
            zt = float(top(np.array([x]), np.array([y]))[0])
            _tuft(gr, rnd, (x, y, zt - 0.04), n=9, h=(0.04, 0.1), base_r=0.015)
        parts.append(gr.obj('wall_grass', T.foliage('wall_grass', color='#2a3016', tip='#59592e', seed=6), smooth=False))
    return parts


# ================================================================ columns
def _drum(r0, r1, z0, z1, nz, flutes=18, seg=72, jag=0.0, chip=0.012, tilt_seed=0.0):
    """A column drum about the z axis from z0 to z1: fluted, chipped; jag: its top broken off unevenly. (V, F)."""
    rings = max(3, int((z1 - z0) / 0.025))
    a = np.linspace(0.0, 2.0 * math.pi, seg, endpoint=False)
    t = np.linspace(0.0, 1.0, rings + 1)
    flute = 1.0 - 0.075 * np.abs(np.sin(a * flutes / 2.0)) ** 0.6 if flutes else np.ones(seg)
    ca, sa = np.cos(a), np.sin(a)
    ztop = np.full(seg, z1)
    if jag:
        Pa = np.column_stack((ca, sa, np.full(seg, tilt_seed)))
        ztop = z1 - jag * (nz(Pa, 1.3, 3) * 1.4 - 0.2).clip(0.0, 1.0)
    R = (r0 + (r1 - r0) * t)[:, None] * flute[None, :]
    Zz = z0 + (ztop[None, :] - z0) * t[:, None]
    V = np.stack((R * ca[None, :], R * sa[None, :], Zz), axis=-1).reshape(-1, 3)
    d = (nz(V + tilt_seed, 16.0, 3) - 0.5)
    d = -np.clip(d - 0.12, 0.0, 1.0) * chip * 8.0 + (nz(V, 60.0, 2) - 0.5) * 0.004
    rad = T.unit(V * (1.0, 1.0, 0.0))
    V = V + rad * d[:, None]
    i, k = np.meshgrid(np.arange(rings), np.arange(seg), indexing='ij')
    q0 = (i * seg + k).ravel()
    q1 = (i * seg + (k + 1) % seg).ravel()
    F = np.concatenate((np.column_stack((q0, q1, q1 + seg)), np.column_stack((q0, q1 + seg, q0 + seg))))
    nv = len(V)
    top_c = np.array([[0.0, 0.0, float(ztop.mean()) - (jag * 0.3 if jag else 0.0)]])
    bot_c = np.array([[0.0, 0.0, z0]])
    V = np.vstack((V, top_c, bot_c))
    ks = np.arange(seg)
    F = np.vstack((F, np.column_stack((np.full(seg, nv), rings * seg + ks, rings * seg + (ks + 1) % seg)),
                   np.column_stack((np.full(seg, nv + 1), (ks + 1) % seg, ks))))
    return V, F


def column(n):
    rnd = np.random.default_rng(430 + n)
    nz = T.Field(90 + n)
    acc, small, grass = T.Acc(), T.Acc(), T.Acc()
    r = 0.17
    cx, cy = (0.0, 0.0) if n == 1 else (-0.14, 0.1)
    # plinth and base mouldings
    V, F = T.block((cx, cy, 0.035), (0.5, 0.5, 0.07), bev=0.012, grid=0.03, nz=nz, rough=0.007)
    acc.add(V, F)
    for (ra, rb, z0, z1) in ((r * 1.32, r * 1.36, 0.07, 0.1), (r * 1.36, r * 1.12, 0.1, 0.135), (r * 1.2, r * 1.06, 0.135, 0.165)):
        V, F = _drum(ra, rb, z0, z1, nz, flutes=0, chip=0.008, tilt_seed=z0)
        acc.add(V + (cx, cy, 0.0), F)
    if n == 1:      # standing to two thirds of its height, snapped
        z = 0.165
        for (h, jag) in ((0.34, 0.0), (0.33, 0.0), (0.28, 0.16)):
            ra = r * (1.0 - 0.1 * (z - 0.165))
            V, F = _drum(ra, ra * 0.985, z, z + h - 0.006, nz, jag=jag, tilt_seed=z * 3.0)
            acc.add(_rot(V, _rz(rnd.uniform(0, 3.0))) + (cx + rnd.uniform(-0.006, 0.006), cy + rnd.uniform(-0.006, 0.006), 0.0), F)
            z += h
        _pebbles(small, rnd, nz, 6, 0.3, 0.42, size=(0.04, 0.1))
    else:           # a stump of shaft, and a drum fallen beside it
        V, F = _drum(r, r * 0.985, 0.165, 0.5, nz, jag=0.14, tilt_seed=1.0)
        acc.add(V + (cx, cy, 0.0), F)
        V, F = _drum(r * 0.97, r * 0.95, -0.2, 0.2, nz, jag=0.07, tilt_seed=2.0)
        V = _rot(V, _rz(0.55) @ _ry(math.pi / 2 + 0.06), (0.2, -0.3, r * 0.9))
        acc.add(V, F)
        _pebbles(small, rnd, nz, 9, 0.2, 0.46, size=(0.04, 0.12))
    for _ in range(7):
        a = rnd.uniform(0, 6.283)
        _tuft(grass, rnd, (cx + math.cos(a) * 0.3, cy + math.sin(a) * 0.32, 0.0), n=9, h=(0.04, 0.11))
    m = T.stone(f'column_{n}', color='#8a8679', color2='#5c5a53', moss=0.4, lichen=0.8, cracks=0.8, seed=60 + n,
                scale=1.8, mud_h=0.1, relief=0.6)
    ob = acc.obj('column', m, weld=0.0004)
    return [ob, small.obj('stones', T.stone('col_chips', color='#827e72', moss=0.3, seed=3, scale=2.0)),
            grass.obj('grass', T.foliage('foot_grass', color='#2c2e17', tip='#5a5630', seed=4), smooth=False)]


# ================================================================ standing stones
def standing(n):
    rnd = np.random.default_rng(540 + n)
    nz = T.Field(100 + n)
    acc, small, grass = T.Acc(), T.Acc(), T.Acc()
    if n == 1:      # a tall weathered monolith, leaning a little
        V, F = T.rock(rnd, (0.42, 0.3, 1.5), n=20, cuts=4, rough=0.05, nz=nz, crag=0.03)
        acc.add(_rot(V, _ry(0.07) @ _rx(-0.05), (0.0, 0.0, 0.5)), F)
    else:           # a squat slab like a grave marker, sunk and tilted, a smaller stone at its foot
        V, F = T.rock(rnd, (0.56, 0.2, 1.1), n=22, cuts=4, rough=0.04, nz=nz, crag=0.02)
        acc.add(_rot(V, _ry(-0.14) @ _rx(0.1), (-0.04, 0.05, 0.34)), F)
        V, F = T.rock(rnd, (0.3, 0.26, 0.24), n=12, cuts=3, rough=0.06, nz=nz)
        acc.add(V + (0.26, -0.22, 0.06), F)
    acc.V = [np.column_stack((v[:, 0], v[:, 1], np.maximum(v[:, 2], -0.01))) for v in acc.V]
    _pebbles(small, rnd, nz, 6, 0.22, 0.4, size=(0.035, 0.09))
    for _ in range(9):
        a = rnd.uniform(0, 6.283)
        _tuft(grass, rnd, (math.cos(a) * 0.26, math.sin(a) * 0.24, 0.0), n=10, h=(0.05, 0.13))
    m = T.stone(f'standing_{n}', color='#64625b', color2='#42413e', moss=0.6, lichen=0.8, cracks=0.8, seed=70 + n,
                scale=1.3, mud_h=0.14)
    return [acc.obj('stone', m), small.obj('stones', T.stone('foot_stone', color='#5f5c54', moss=0.4, seed=3)),
            grass.obj('grass', T.foliage('foot_grass', color='#2c2e17', tip='#5a5630', seed=4), smooth=False)]


# ================================================================ brush
def brush(n):
    """Low cover a figure stands in: kept under 0.35 high and thin enough to see a figure through."""
    rnd = np.random.default_rng(650 + n)
    nz = T.Field(110 + n)
    wood, green, dry = T.Acc(), T.Acc(), T.Acc()
    if n == 1:      # thorn scrub: arching bare canes, a few dark leaves
        for _ in range(9):
            a, rr = rnd.uniform(0, 6.283), rnd.uniform(0.05, 0.36)
            o = np.array((math.cos(a) * rr, math.sin(a) * rr * 1.25, 0.0))
            for _c in range(int(rnd.integers(3, 6))):
                b = rnd.uniform(0, 6.283)
                L, h = rnd.uniform(0.18, 0.34), rnd.uniform(0.14, 0.3)
                s = np.linspace(0.0, 1.0, 9)
                d = np.array((math.cos(b), math.sin(b), 0.0))
                P = o[None, :] + d[None, :] * (L * s ** 1.3)[:, None]
                P[:, 2] = h * np.sin(s * math.pi * rnd.uniform(0.55, 0.8)) ** 0.8
                P += nz.vec(P, 9.0, 2) * 0.04 * s[:, None]
                P[:, 2] = np.clip(P[:, 2], 0.0, 0.33)
                wood.add(*T.tube(P, np.linspace(0.0065, 0.002, 9), seg=5))
                k = 7
                idx = rnd.integers(2, 9, k)
                Tn = T.unit(np.gradient(P, axis=0))[idx]
                Dl = T.unit(rnd.normal(0, 1, (k, 3)) + Tn * 0.5)
                green.add(*T.blades(P[idx], Dl, rnd.normal(0, 1, (k, 3)) + UP, rnd.uniform(0.025, 0.045, k), 0.016, bend=0.2))
                kt = 10      # thorns
                idx = rnd.integers(1, 9, kt)
                dry.add(*T.blades(P[idx], T.unit(rnd.normal(0, 1, (kt, 3)) + UP * 0.3), rnd.normal(0, 1, (kt, 3)),
                                  rnd.uniform(0.012, 0.02, kt), 0.005))
    elif n == 2:    # dead bracken: brown fronds arching over
        for _ in range(26):
            a, rr = rnd.uniform(0, 6.283), rnd.uniform(0.0, 0.34)
            o = np.array((math.cos(a) * rr, math.sin(a) * rr * 1.25, 0.0))
            b = rnd.uniform(0, 6.283)
            L, h = rnd.uniform(0.16, 0.3), rnd.uniform(0.1, 0.26)
            s = np.linspace(0.0, 1.0, 10)
            d = np.array((math.cos(b), math.sin(b), 0.0))
            P = o[None, :] + d[None, :] * (L * s)[:, None]
            P[:, 2] = h * np.sin(s * math.pi * rnd.uniform(0.6, 0.85)) ** 0.7
            wood.add(*T.tube(P, np.linspace(0.004, 0.0012, 10), seg=4))
            Tn = T.unit(np.gradient(P, axis=0))
            side = T.unit(np.cross(Tn, UP))
            acc = dry if rnd.uniform() < 0.75 else green
            for sg in (-1.0, 1.0):
                idx = np.arange(2, 10)
                ln = L * 0.34 * np.sin(np.linspace(0.25, 1.0, len(idx)) * math.pi) + 0.012
                Dl = T.unit(side[idx] * sg + Tn[idx] * 0.45 + UP * rnd.uniform(-0.3, 0.1, (len(idx), 1)))
                acc.add(*T.blades(P[idx], Dl, UP + rnd.normal(0, 0.25, (len(idx), 3)), ln, ln * 0.3, bend=0.3))
    else:           # heather and dry grass: low twiggy mounds, pale blades standing out of them
        for _ in range(8):
            a, rr = rnd.uniform(0, 6.283), rnd.uniform(0.05, 0.36)
            o = np.array((math.cos(a) * rr, math.sin(a) * rr * 1.25, 0.0))
            k = 90
            P = o[None, :] + rnd.normal(0, 1, (k, 3)) * (0.07, 0.07, 0.03) + (0, 0, 0.04)
            P[:, 2] = np.clip(P[:, 2], 0.0, 0.14)
            D = T.unit(rnd.normal(0, 0.7, (k, 3)) + UP)
            green.add(*T.blades(P, D, rnd.normal(0, 1, (k, 3)), rnd.uniform(0.025, 0.05, k), 0.012, bend=0.2))
            for _c in range(4):
                b = rnd.uniform(0, 6.283)
                tip = o + np.array((math.cos(b) * 0.09, math.sin(b) * 0.09, rnd.uniform(0.08, 0.16)))
                wood.add(*T.tube(np.array((o, (o + tip) / 2 + (0, 0, 0.02), tip)), (0.004, 0.003, 0.0015), seg=4))
        for _ in range(16):
            a, rr = rnd.uniform(0, 6.283), rnd.uniform(0.0, 0.4)
            _tuft(dry, rnd, (math.cos(a) * rr, math.sin(a) * rr * 1.25, 0.0), n=12, h=(0.1, 0.3), spread=0.35, width=0.009)
    stem = T.bark('brush_stem', color='#3b2f25', seed=12, moss=0.0, ridges=4.0, grain=6.0, lichen=0.0)
    leaf = T.foliage(f'brush_leaf_{n}', color=('#232a16', '#2e3319', '#2b2a1c')[n - 1], tip=('#474d27', '#565a2c', '#4d4630')[n - 1],
                     seed=13 + n, dead='#4a3520', dead_share=0.2)
    dry_m = T.foliage(f'brush_dry_{n}', color=('#2e241a', '#3d2c1d', '#5e5433')[n - 1], tip=('#57483a', '#64503a', '#8f8556')[n - 1],
                      seed=16 + n, rough=0.8)
    return [wood.obj('stems', stem), green.obj('leaves', leaf, smooth=False), dry.obj('dry', dry_m, smooth=False)]


BUILDERS = {'tree': tree, 'boulder': boulder, 'wall': wall, 'column': column, 'stone': standing, 'brush': brush}


def build(v):
    M.set_mode(revenant=False)
    parts = [p for p in BUILDERS[v['kind']](v.get('n', 1)) if p is not None]
    return T.parent(parts, T.root(v['kind']))
