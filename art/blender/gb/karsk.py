"""Karsk: the Crown's kit, as its deserters wear it (ASSETS.md, step 3 of the enemy plan).

The shared pieces of the Shieldman, the Levy Pikeman and the Deserter: the slate livery and its materials, the kettle
hat (a riveted bowl and a brim sloping down all round; bare, painted or dented; worn, or slung at the back), a coif
worn up (a close hood round the face, in mail or padded cloth), the Crown's device as a shape (a crown) and the ways
it was taken off (a decal: scraped to the iron, a darker ghost on cloth; a hole cut through a tabard), the tabard, the
heater (the Fighter's great shield without its cross) and the pike.

Figure space as in body.py; head space as in face.py (an unscaled head, z = 0 at the eyes).
"""
import math
import random

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils import noise as mnoise

from . import armor as A
from . import face as F
from . import garb as GB
from . import grit as G
from . import kit as K

SLATE = '#56626b'
PAL = dict(slate=SLATE, ghost='#353e45', undyed='#857a62', stained='#6a5f4b', iron='#5a5c5e', dark_iron='#3d3e40',
           leather='#3b2a1d', breeches='#2f2c28', wraps='#5a5546')


def materials():
    """The Karsk kit's materials (the three foes share them)."""
    return dict(
        tabard=G.cloth('karsk_tabard', color=SLATE, blood=0.2, mud=1.7, grime=0.75, seed=71),
        ghost=G.cloth('karsk_ghost', color=PAL['ghost'], blood=0.0, mud=0.6, grime=0.5, seed=72),
        jack=G.cloth('karsk_jack', color=SLATE, blood=0.25, mud=1.8, grime=0.85, seed=73,
                     patches=(0.12, 0.08, (PAL['undyed'], '#454d52'))),
        undyed=G.cloth('karsk_undyed', color=PAL['undyed'], blood=0.3, mud=1.8, grime=0.9, seed=74,
                       patches=(0.12, 0.08, ('#6b5f49', SLATE))),
        stained=G.cloth('karsk_stained', color=PAL['stained'], blood=0.45, mud=2.0, grime=1.0, seed=75),
        padded=G.cloth('karsk_padded', color='#665f50', blood=0.15, mud=0.8, grime=1.0, seed=76),
        breeches=G.cloth('karsk_breeches', color=PAL['breeches'], blood=0.1, mud=1.9, grime=0.7, seed=77),
        wraps=G.cloth('karsk_wraps', color=PAL['wraps'], blood=0.05, mud=2.6, grime=0.8, seed=78),
        shoes=G.leather('karsk_shoes', color='#33261b', mud=2.6, seed=79),
        leather=G.leather('karsk_leather', color=PAL['leather'], mud=1.2, seed=80),
        mail=G.maille('karsk_mail', color='#505255', rust=0.5, blood=0.15, seed=81),
        iron=G.steel('karsk_iron', color='#707376', rust=0.5, blood=0.2, grime=0.8, seed=82, dents=0.8, dirt=0.4),
        hat_iron=G.steel('karsk_hat', color='#85888b', rust=0.45, blood=0.05, grime=0.55, seed=83, dents=0.9, dirt=0.3),
        hat_rust=G.steel('karsk_hat_rust', color='#6a6866', rust=0.95, blood=0.15, grime=1.0, seed=84, dents=1.2,
                         edge=0.5),
        hat_paint=G.paint_over_steel('karsk_hat_paint', paint=SLATE, steel_color='#63666a', chip=0.6, blood=0.15,
                                     seed=85),
        heater=G.paint_over_steel('karsk_heater', paint=SLATE, steel_color='#63666a', chip=0.5, blood=0.3, seed=86),
        scraped=G.steel('karsk_scraped', color='#7b7d80', rough=0.4, rust=0.35, blood=0.0, grime=0.4, scratch=2.4,
                        seed=87, dents=0.2),
        dark=G.steel('karsk_dark_iron', color=PAL['dark_iron'], rust=0.7, blood=0.2, seed=88, edge=0.5),
        blade=G.steel('karsk_blade', color='#7d8083', rough=0.3, rust=0.4, blood=0.6, grime=0.6, seed=89, dents=0.2),
        wood=G.wood('karsk_wood', color='#4a3a2a', seed=90),
        ash=G.wood('karsk_ash', color='#6a573c', seed=91),
    )


# ------------------------------------------------------------------------------------------------ the kettle hat
HAT_TILT = 13.0     # degrees: its rim sits higher at the brow than at the nape
HAT_RIM = -0.012    # the rim's height off the bowl's centre (face.HELM_C), hat space


def kettle_hat(name, H, iron, rivet_mat, seed=0, grow=0.004, dent=0.0018, brim=0.052, drop=0.022, bash=0.0):
    """A kettle hat on a head placed by H (the head's frame: body.Frame.head_frame, or any frame for a hat slung):
    a riveted bowl close over the head (face.HELM_*: face.head(helm=True) fits the hair under it) and a brim `brim`
    wide sloping down `drop` all round. bash: a dent knocked into the bowl and the brim bent (m)."""
    cx, cy, cz = F.HELM_C
    rx, ry, rz = F.HELM_R[0] + grow, F.HELM_R[1] + grow, F.HELM_R[2] + grow + 0.008
    phi_r = math.acos(HAT_RIM / rz)
    nt = 48
    rnd = random.Random(seed)
    b_th, b_ph = rnd.uniform(-1.2, 1.2), rnd.uniform(0.5, 0.9)
    wob = [rnd.uniform(0.0, 6.28) for _ in range(2)]

    def bowl(th, phi, lift=0.0):
        sp, cp = math.sin(phi), math.cos(phi)
        p = Vector(((rx + lift) * sp * math.sin(th), -(ry + lift) * sp * math.cos(th), (rz + lift) * cp))
        p += p.normalized() * dent * mnoise.noise(p * 30.0 + Vector((seed, 0.0, 0.0)))
        if bash:
            c = Vector((rx * math.sin(b_ph) * math.sin(b_th), -ry * math.sin(b_ph) * math.cos(b_th), rz * math.cos(b_ph)))
            p -= p.normalized() * bash * math.exp(-((p - c).length / 0.035) ** 2)
        return p

    def rim(th, d, lift=0.0):
        p = bowl(th, phi_r, lift)
        n = Vector((math.sin(th) / rx, -math.cos(th) / ry, 0.0)).normalized()
        t = d / brim
        z = -drop * t ** 1.15 + 0.6 * bash * t * (math.sin(th * 2.0 + wob[0]) + 0.6 * math.sin(th * 5.0 + wob[1]))
        return p + n * d + Vector((0.0, 0.0, z))
    bm = bmesh.new()
    rows = [[bm.verts.new(rim(2.0 * math.pi * i / nt, brim * f)) for i in range(nt)] for f in (1.0, 0.66, 0.33, 0.06)]
    for k in range(11):
        phi = phi_r * (1.0 - k / 11.0)
        rows.append([bm.verts.new(bowl(2.0 * math.pi * i / nt, phi)) for i in range(nt)])
    for a, b in zip(rows[:-1], rows[1:]):
        for i in range(nt):
            bm.faces.new((a[i], a[(i + 1) % nt], b[(i + 1) % nt], b[i]))
    pole = bm.verts.new(bowl(0.0, 0.0))
    for i in range(nt):
        bm.faces.new((rows[-1][i], rows[-1][(i + 1) % nt], pole))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    hat = K._obj(name, bm, iron)
    A.solid(hat, 0.003, 1.0)
    K.subsurf(hat, 1)
    rp = [bowl(2.0 * math.pi * (i + 0.5) / 18, phi_r * 0.9, 0.004) for i in range(18)]      # round the bowl's foot
    for q in range(4):                                                                     # and up its four seams
        rp += [bowl(math.pi * (q + 0.5) / 2.0, phi_r * f, 0.004) for f in (0.7, 0.5, 0.3)]
    rp += [rim(2.0 * math.pi * i / 14, brim * 0.9) + Vector((0.0, 0.0, 0.004)) for i in range(14)]
    parts = [hat, A.rivets(name + '_rivets', rp, 0.0036, rivet_mat)]
    T = Matrix.Translation((cx, cy, cz)) @ Matrix.Rotation(math.radians(-HAT_TILT), 4, 'X')
    for ob in parts:
        ob.matrix_world = H @ T
    return parts


def slung_frame(at, crown=(0.0, 1.0, 0.25), scale=1.08):
    """A frame for a kettle hat hung at `at` (figure space) by its strap, its crown turned along `crown`."""
    cx, cy, cz = F.HELM_C
    R = A.frame(crown, back=(0.0, 0.0, -1.0))
    return Matrix.Translation(Vector(at)) @ R @ Matrix.Scale(scale, 4) @ Matrix.Translation((-cx, -cy, -cz))


# ------------------------------------------------------------------------------------------------ the coif
COIF_C, COIF_R = (0.0, 0.01, 0.002), (0.08, 0.107, 0.114)
COIF_NECK = ((0.0, 0.03, -0.06), (0.0, 0.026, -0.3), 0.088)
COIF_OPEN = ([-0.4, -0.142, -0.124, -0.095, -0.04, 0.0, 0.022, 0.036, 0.06],
             [-40.0, -40.0, 16.0, 42.0, 50.0, 48.0, 40.0, 0.0, -30.0])


def coif_inner(P):
    """Signed distance (head space) to the inside of a coif worn up: close over the skull and the jaw, round the neck."""
    head = F._ell(P, np.array(COIF_C, np.float32), np.array(COIF_R, np.float32))
    neck = F._cap(P, np.array(COIF_NECK[0], np.float32), np.array(COIF_NECK[1], np.float32), COIF_NECK[2])
    return F._smin(head, neck, 0.04)


def coif_front(P):
    """Negative in the coif's opening: the face, from the brow to the chin (an arc distance, as face.hood_front)."""
    q = P[:, 1] - F.HOOD_AXIS
    rho = np.sqrt(P[:, 0] ** 2 + q ** 2)
    th = np.arctan2(np.abs(P[:, 0]), -q)
    return (th - np.radians(np.interp(P[:, 2], *COIF_OPEN))) * rho


def coif(name, H, z_bot, mat, thick=0.0055, grid=0.003, seed=0, tris=7000, z_top=0.05):
    """A coif worn up round a head placed by H: the hood's construction cut close, open round the face from the brow
    to the chin; it ends at z_bot (head space), tucked into its mantle, and at z_top under the hat."""
    Hm = np.array(H, np.float32)
    Hi = np.linalg.inv(Hm)
    s = float(np.cbrt(abs(np.linalg.det(Hm[:3, :3]))))
    R3, t3 = Hi[:3, :3], Hi[:3, 3]
    noise = F._Noise(seed + 211)

    def to_head(Q):
        return Q @ R3.T + t3

    def env(Q):
        P = to_head(Q)
        return (coif_inner(P) + 0.0015 * (noise(P, 30.0) - 0.5)) * s

    def t(Q):
        P = to_head(Q)
        return (thick + 0.003 * np.exp(-(coif_front(P) / 0.008) ** 2)).astype(np.float32)

    def region(Q):
        P = to_head(Q)
        return np.maximum(np.maximum(-coif_front(P), z_bot - P[:, 2]), P[:, 2] - z_top) * s
    c = Hm[:3, 3]
    lo = c + np.array((-0.2, -0.2, -0.36)) * s / 1.08
    hi = c + np.array((0.2, 0.22, 0.2)) * s / 1.08
    g = F._Grid(None, None, tuple(lo), tuple(hi), band=(-0.004, 0.014), h=grid, m=4, fn=env)
    return F._mesh(name, *F._nets(g.shell(t, region, inner=0.0, feather=0.002, floor=1.0), g.lo, g.h), mat, tris,
                   smooth_angle=60)


def mantle(D, fr, H, mat, seed=0, z_hem=1.37, clear=0.04, name='mantle'):
    """The coif's mantle over the shoulders (a short closed drape), and where the coif tucks into it: returns
    (object, z_bot in head space)."""
    hf = fr.hf
    drop = fr.spine[2] if fr.spine is not None else 0.0
    ztop = 1.58 * hf - drop
    up = np.array((0.0, 0.02, 1.53 * hf), np.float32)
    oy = float(fr.from_upper(up)[1]) if fr.spine is not None else 0.02
    cape = GB.Drape(D, ztop, z_hem * hf - drop, [a * 5.0 for a in range(72)], clear, rows=10, oy=oy,
                    collar=(0.1 * fr.head_scale + 0.01, 0.5), flare=0.02, folds=0.008, fold_n=9, ragged=0.012,
                    seed=seed, closed=True, arms=False)
    z_bot = (Vector(H.inverted() @ Vector((0.0, oy + 0.02, ztop))).z) - 0.03
    return cape.mesh(name, mat, thick=0.006), z_bot


# ------------------------------------------------------------------------------------------------ the device
def crown(u, v):
    """The Crown's device in the unit square (u across, v up, arrays): a band under three points."""
    pk = np.min(np.abs(u[:, None] - np.array((-0.8, 0.0, 0.8), np.float32)[None, :]), 1)
    return (np.abs(u) <= 0.84) & (v >= -0.8) & (v <= np.maximum(-0.1, 0.85 - 2.2 * pk))


def decal(name, at, mat, n=30, thick=0.0015, ragged=0.07, seed=0, shape=crown):
    """Where the device was, as a thin patch lying on a surface: at(U, V) -> points (N, 3) for unit-square arrays (the
    surface, lifted a little). The patch is the device's shape with its edge ragged (a scrape, a ghost, a tear)."""
    ax = np.linspace(-1.0, 1.0, n + 1).astype(np.float32)
    U, V = np.meshgrid(ax, ax, indexing='ij')
    P = np.asarray(at(U.ravel(), V.ravel()), np.float32).reshape(n + 1, n + 1, 3)
    cu = ((ax[:-1] + ax[1:]) / 2.0)
    CU, CV = np.meshgrid(cu, cu, indexing='ij')
    rnd = np.random.RandomState(seed)
    ph = rnd.uniform(0.0, 6.28, 4)
    wu = CU + ragged * (np.sin(CV * 9.0 + ph[0]) + 0.6 * np.sin(CV * 23.0 + ph[1]))
    wv = CV + ragged * (np.sin(CU * 8.0 + ph[2]) + 0.6 * np.sin(CU * 21.0 + ph[3]))
    inside = shape(wu.ravel().astype(np.float32), wv.ravel().astype(np.float32)).reshape(n, n)
    bm = bmesh.new()
    vs = {}

    def vert(i, j):
        if (i, j) not in vs:
            vs[(i, j)] = bm.verts.new(tuple(map(float, P[i, j])))
        return vs[(i, j)]
    for i in range(n):
        for j in range(n):
            if inside[i, j]:
                bm.faces.new((vert(i, j), vert(i + 1, j), vert(i + 1, j + 1), vert(i, j + 1)))
    if not vs:
        bm.verts.new((0.0, 0.0, -10.0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = K._obj(name, bm, mat)
    A.solid(ob, thick, 0.0)
    return ob


def on_drape(drape, a_mid, z_mid, half_a, half_z, lift=0.004):
    """decal()'s `at` for a patch on a drape: centred at angle a_mid (degrees) and height z_mid."""
    def at(U, V):
        return np.array([tuple(drape.point(a_mid + float(u) * half_a, z_mid + float(v) * half_z, lift)[0])
                         for u, v in zip(U, V)], np.float32)
    return at


def on_body(D, a_mid, z_mid, half_a, half_z, clear):
    """decal()'s `at` for a patch on the trunk (over a jack `clear` thick)."""
    def at(U, V):
        a = np.radians(a_mid + U * half_a)
        dirs = np.column_stack((np.cos(a), np.sin(a), np.zeros(len(a)))).astype(np.float32)
        O = np.column_stack((np.zeros(len(a)), np.zeros(len(a)), z_mid + V * half_z)).astype(np.float32)
        r = D.outer(O, dirs, clear, arms=False)
        return O + dirs * r[:, None]
    return at


def drape_mesh(drape, name, mat, thick=0.005, hole=None, levels=1):
    """garb.Drape.mesh, with a hole cut through it: hole(angle (degrees), z) -> True where the cloth is gone."""
    Gd = drape.grid()
    nr, nc = Gd.shape[:2]
    bm = bmesh.new()
    V = [[bm.verts.new(tuple(map(float, Gd[k, i]))) for i in range(nc)] for k in range(nr)]
    span = nc if drape.closed else nc - 1
    for k in range(nr - 1):
        for i in range(span):
            j = (i + 1) % nc
            if hole is not None and hole(0.5 * float(drape.A[i] + drape.A[min(i + 1, nc - 1)]),
                                         0.5 * float(drape.Zg[k, i] + drape.Zg[k + 1, i])):
                continue
            bm.faces.new((V[k][i], V[k][j], V[k + 1][j], V[k + 1][i]))
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = K._obj(name, bm, mat)
    A.solid(ob, thick).use_even_offset = False      # (even offset spikes at the hole's corners)
    if levels:
        K.subsurf(ob, levels)
    return ob


def crown_hole(a_mid, z_mid, half_a, half_z, seed=0):
    """drape_mesh()'s hole: the device cut out with a knife."""
    rnd = random.Random(seed)
    ph = [rnd.uniform(0.0, 6.28) for _ in range(2)]

    def hole(a, z):
        u, v = (a - a_mid) / half_a, (z - z_mid) / half_z
        u += 0.08 * math.sin(v * 7.0 + ph[0])
        v += 0.08 * math.sin(u * 6.0 + ph[1])
        return bool(crown(np.array([u], np.float32), np.array([v], np.float32))[0])
    return hole


# ------------------------------------------------------------------------------------------------ the tabard
def tabard(D, fr, zb, seed=0, z_hem=0.7, clear=0.024, rows=44, step=2.5):
    """The Karsk tabard: the Cleric's surcoat cut short at the thigh, a panel before and one behind, belted at zb (m).
    Returns the two drapes (front, back); mesh them with drape_mesh (the Deserter's has a hole) or Drape.mesh."""
    hf = fr.hf
    drop = fr.spine[2] if fr.spine is not None else 0.0
    oy = 0.5 * float(fr.joints['sh_l'][1] + fr.joints['sh_r'][1]) * 0.5 + 0.005
    zt = 1.5 * hf - drop - 0.012
    n = int(120.0 / step) + 1
    front = GB.Drape(D, zt, z_hem * hf - drop, [-150.0 + step * k for k in range(n)], clear, rows=rows, oy=oy,
                     flare=0.03, folds=0.009, fold_n=11, ragged=0.02, seed=seed, arms=False, cinch=(zb, clear - 0.002))
    back = GB.Drape(D, zt, z_hem * hf - drop, [30.0 + step * k for k in range(n)], clear, rows=rows, oy=oy,
                    flare=0.035, folds=0.01, fold_n=9, ragged=0.022, seed=seed + 1, arms=False,
                    cinch=(zb, clear - 0.002))
    return front, back


# ------------------------------------------------------------------------------------------------ the heater
def heater(name, w, h, face, rim, rivet_mat, scraped=None, curve=0.9, grip_at=0.4, seed=0):
    """The Karsk heater: the Fighter's great shield (armor.great_shield, local space: its face toward -Y, point down)
    painted in the livery, the iron cross and the boss left off; scraped: the material of the scrape where the
    Crown's device was taken off, back to the iron. Returns (parts, local z of the grip)."""
    parts, zc = A.great_shield(name, w, h, face, rim, rim, rivet_mat, rim, curve=curve, cross_at=grip_at)
    keep = []
    for ob in parts:
        if any(t in ob.name for t in ('_pale', '_fess', '_boss')):
            bpy.data.objects.remove(ob)
        else:
            keep.append(ob)
    if scraped is not None:
        zd, hw, hh = 0.14 * h, 0.2 * w, 0.14 * w

        def at(U, V):
            x = U * hw
            return np.column_stack((x, curve * x * x - 0.002, zd + V * hh))
        keep.append(decal(name + '_scrape', at, scraped, n=34, ragged=0.04, seed=seed))
    return keep, zc


# ------------------------------------------------------------------------------------------------ the pike
def pike(name, butt, direction, length, shaft, steel, r=0.018, shadow_to=None):
    """A pike from its grounded `butt` along `direction`: an ash shaft `length` long (m), a small head on long
    langets. shadow_to: the shaft above this far along casts no shadow (so a long one's stays inside the sprite)."""
    d = Vector(direction).normalized()
    B = Vector(butt)
    top = B + d * length
    cut = min(shadow_to or length, length)
    parts = [K.tube(name + '_shaft', B, B + d * cut, r, r * 0.92, shaft, seg=10)]
    upper = []
    if cut < length:
        upper.append(K.tube(name + '_shaft_hi', B + d * cut, top, r * 0.92, r * 0.8, shaft, seg=10))
    upper.append(K.tube(name + '_socket', top - d * 0.1, top + d * 0.04, r * 0.95, r * 0.7, steel, seg=10))
    side = d.cross(Vector((0.0, 1.0, 0.0))).normalized()
    for s in (-1.0, 1.0):       # the langets, riveted down the shaft
        upper.append(K.tube(name + '_langet', top - d * 0.46 + side * (s * r * 0.8), top - d * 0.08 + side * (s * r * 0.75),
                            0.005, 0.005, steel, seg=6))
    bl = K.blade(name + '_head', 0.24, 0.052, 0.014, steel, secs=[(0.0, 0.45), (0.2, 1.0), (0.5, 0.8), (1.0, 0.0)])
    A.place(bl, top + d * 0.03, A.frame(d, back=(0.0, 1.0, 0.0)))
    upper.append(bl)
    upper.append(K.tube(name + '_shoe', B, B + d * 0.08, r * 1.15, r * 1.05, steel, seg=10))
    if shadow_to is not None:
        for ob in upper[:-1]:
            ob.visible_shadow = False
    return parts + upper


# ------------------------------------------------------------------------------------------------ plate on an arm
def arm_plate(fr, side, steel, rivet_mat, seed=0, pauldron=True, lames=2):
    """The Fighter's plate laid on a posed arm (body.Frame joints): a rerebrace, a couter, a vambrace, and a spaulder
    over the shoulder."""
    J, f = fr.joints, fr.f
    s = 1.0 if side == 'l' else -1.0
    sh, el, wr = (Vector(J[k + side]) for k in ('sh_', 'el_', 'wr_'))
    a0, a1, a2, a3 = f['arm']
    u = (el - sh).normalized()
    w = (wr - el).normalized()
    parts = [A.shell('rerebrace', sh + u * 0.12, el - u * 0.04, [(a0 + 0.02, 0.0), (a1 + 0.024, 1.0)], steel, seg=20,
                     dent=0.003, seed=51 + seed),
             A.shell('vambrace', el + w * 0.045, wr - w * 0.01, [(a2 + 0.02, 0.0), (a3 + 0.022, 1.0)], steel, seg=20,
                     dent=0.003, seed=71 + seed)]
    out = (u.cross(w)).cross(u + w)
    if out.length < 1e-4:
        out = Vector((s, 0.3, 0.0))
    back = -(u - w).normalized() if (u - w).length > 0.05 else Vector((s * 0.5, 0.8, 0.1))
    parts += A.cop('couter', el, back, (s, -0.2, 0.0), steel, rivet_mat, r=a1 + 0.026, seed=61 + seed)
    if pauldron:
        m_d = 0.064 + 0.025
        parts += A.pauldron('spaulder_' + side, sh + Vector((s * 0.012, 0.0, 0.03 * fr.hf)), s, steel, rivet_mat,
                            size=0.98 * (f['deltoid'] + 0.025) / m_d, lames=lames, seed=81 + seed)
    return parts
