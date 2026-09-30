"""Armour and anatomy kit — the parts every humanoid in Graveborne is assembled from.

Units here are METRES (a 1.85 m mercenary); an asset's FIG_SCALE converts to tiles. Conventions follow the rig:
+Z up, the figure faces -Y (the camera), the figure's left is +X (the viewer's right).

Plates are thin solidified shells with rolled edges, dented by noise, riveted along their rims, because at
battle-map size that is what separates "armour" from "grey blob": a bright lip on every edge and a dark gap
between every overlapping plate.
"""
import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils import noise as mnoise

from . import kit as K


# ---------------------------------------------------------------- frames & small parts
def frame(d, back=(0.0, 1.0, 0.0)):
    """Rotation taking local +Z along `d`, with local -Y turned as close to the front (world -Y) as possible."""
    z = Vector(d).normalized()
    b = Vector(back)
    y = b - z * b.dot(z)
    if y.length < 1e-5:
        y = Vector((0.0, 0.0, 1.0)) - z * z.z
    y.normalize()
    x = y.cross(z)
    return Matrix((x, y, z)).transposed().to_4x4()


def place(ob, origin, rot):
    ob.matrix_world = Matrix.Translation(Vector(origin)) @ rot
    return ob


def solid(ob, t=0.004, offset=0.0):
    m = ob.modifiers.new('solid', 'SOLIDIFY')
    m.thickness = t
    m.offset = offset
    m.use_even_offset = True
    return m


def rivets(name, pts, r, mat):
    """Round-headed rivets (one mesh for all of them)."""
    bm = bmesh.new()
    for p in pts:
        g = bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=5, radius=r)
        bmesh.ops.translate(bm, vec=Vector(p), verts=g['verts'])
    if not pts:
        bm.verts.new((0, 0, -10))
    return K._obj(name, bm, mat)


def _dent(seed, amp):
    def f(i, a):
        v = Vector((math.cos(a) * 1.7, math.sin(a) * 1.7, i * 0.9 + seed * 3.1))
        return (amp * mnoise.noise(v), 0.0)
    return f


# ---------------------------------------------------------------- plates
def shell(name, a, b, profile, mat, sx=1.0, sy=1.0, arc=None, seg=28, dent=0.0, seed=0, thick=0.004,
          lip=0.005, back=(0.0, 1.0, 0.0), levels=1):
    """A plate shell around the segment a->b. profile = [(radius, t), ...] with t in 0..1 along the segment.
    arc (degrees, 0 = local +X, -90 = the front) leaves the back open. `lip` rolls both end edges outward."""
    a, b = Vector(a), Vector(b)
    L = (b - a).length
    prof = [(r, t * L) for r, t in profile]
    if lip:
        r0, z0 = prof[0]
        r1, z1 = prof[-1]
        prof = [(r0 + lip, z0), (r0 + lip * 0.9, z0 + 0.008)] + prof[1:-1] + [(r1 + lip * 0.9, z1 - 0.008), (r1 + lip, z1)]
    ob = K.lathe(name, prof, mat, seg=seg, sx=sx, sy=sy, arc=arc, cap_bottom=False, cap_top=False,
                 jitter=_dent(seed, dent) if dent else None)
    place(ob, a, frame(b - a, back))
    solid(ob, thick)
    if levels:
        K.subsurf(ob, levels)
    return ob


def shell_rim_points(a, b, r, t, arc, n, sx=1.0, sy=1.0, back=(0.0, 1.0, 0.0), inset=0.0):
    """World-space points along one ring of a shell() — where its rivets go."""
    a, b = Vector(a), Vector(b)
    M = frame(b - a, back)
    L = (b - a).length
    a0, a1 = arc if arc else (0.0, 360.0 * (n - 1) / n)
    pts = []
    for k in range(n):
        ang = math.radians(a0 + (a1 - a0) * (k + 0.5) / n) if arc else math.radians(a0 + (a1 - a0) * k / max(1, n - 1))
        local = Vector(((r + inset) * math.cos(ang) * sx, (r + inset) * math.sin(ang) * sy, t * L))
        pts.append(a + (M @ local.to_4d()).to_3d())
    return pts


def pauldron(name, shoulder, side, steel, rivet_mat, size=1.0, lames=3, tilt=26.0, seed=0, dent=0.004):
    """A spaulder: a flattened dome over the shoulder and overlapping lames cascading down the upper arm.
    Open toward the neck so it sits on the body. side = -1 (figure's right) or +1 (left)."""
    s = size
    pole = Vector((side * math.sin(math.radians(tilt)), 0.0, math.cos(math.radians(tilt))))
    # a frame whose local +X points outward (away from the neck), so the open arc faces the body
    z = pole.normalized()
    x = (Vector((side, 0.0, 0.0)) - z * z.x * side).normalized()
    y = z.cross(x)
    M = Matrix((x, y, z)).transposed().to_4x4()
    top = Vector(shoulder) + Vector((side * 0.018 * s, 0.0, 0.05 * s))
    parts = []
    arc = (-128.0, 128.0)
    dome = K.lathe(name + '_dome', [(0.135 * s, -0.055 * s), (0.13 * s, -0.03 * s), (0.112 * s, -0.008 * s),
                                    (0.08 * s, 0.012 * s), (0.04 * s, 0.024 * s), (0.004, 0.028 * s)],
                   steel, seg=36, sy=1.08, arc=arc, cap_bottom=False, cap_top=False, jitter=_dent(seed, dent))
    place(dome, top, M)
    solid(dome, 0.005)
    K.subsurf(dome, 1)
    parts.append(dome)
    rp = []
    for k in range(lames):
        r0 = (0.138 + 0.008 * k) * s
        z0 = (-0.05 - 0.043 * k) * s
        lame = K.lathe(f'{name}_lame{k}', [(r0 + 0.002, z0), (r0 + 0.006, z0 - 0.022 * s), (r0 + 0.012, z0 - 0.05 * s)],
                       steel, seg=36, sy=1.08, arc=(arc[0] + 10 * (k + 1), arc[1] - 10 * (k + 1)),
                       cap_bottom=False, cap_top=False, jitter=_dent(seed + k + 1, dent))
        place(lame, top, M)
        solid(lame, 0.005)
        K.subsurf(lame, 1)
        parts.append(lame)
        for j in range(7):
            ang = math.radians(arc[0] + 10 * (k + 1) + (arc[1] - arc[0] - 20 * (k + 1)) * (j + 0.5) / 7)
            loc = Vector(((r0 + 0.014) * math.cos(ang), (r0 + 0.014) * math.sin(ang) * 1.08, z0 - 0.042 * s))
            rp.append(top + (M @ loc.to_4d()).to_3d())
    parts.append(rivets(name + '_rivets', rp, 0.0055 * s, rivet_mat))
    return parts


def cop(name, joint, facing, wing_out, steel, rivet_mat, r=0.075, seed=0):
    """A joint cop (knee: poleyn, elbow: couter): a dome facing `facing` plus a fan wing toward `wing_out`."""
    k = Vector(joint)
    f = Vector(facing).normalized()
    cup = K.lathe(name, [(r, 0.0), (r * 0.93, r * 0.27), (r * 0.7, r * 0.56), (r * 0.35, r * 0.75), (0.003, r * 0.8)],
                  steel, seg=28, sx=1.0, sy=1.15, cap_bottom=False, cap_top=False, jitter=_dent(seed, 0.003))
    place(cup, k - f * (r * 0.35), frame(f, back=(0.0, 0.0, 1.0)))
    solid(cup, 0.005)
    K.subsurf(cup, 1)
    o = Vector(wing_out).normalized()
    up = f.cross(o).normalized()
    s = r / 0.075
    wing = K.plate(name + '_wing', [(0.0, -0.05 * s), (0.07 * s, -0.035 * s), (0.085 * s, 0.0), (0.07 * s, 0.035 * s),
                                    (0.0, 0.05 * s)], k + o * (r * 0.5), up, o, 0.006, steel)
    return [cup, wing, rivets(name + '_r', [k + f * (r * 0.3) + up * (r * 0.55), k + f * (r * 0.3) - up * (r * 0.55)],
                              0.006, rivet_mat)]


def poleyn(name, knee, side, steel, rivet_mat, seed=0):
    return cop(name, knee, (side * 0.12, -1.0, 0.05), (side, 0.15, 0.0), steel, rivet_mat, 0.075, seed)


def torus(name, center, R, r, mat, sx=1.0, sy=1.0, seg=40, rseg=12, lumpy=0.0, seed=0, rz=None, folds=0.0):
    """A ring (a wrapped scarf, a belt roll). rz makes the section taller than it is thick (a flat band of cloth);
    lumpy and folds displace it so cloth doesn't look machined."""
    c = Vector(center)
    rz = rz or r
    bm = bmesh.new()
    rings = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        ca, sa = math.cos(a), math.sin(a)
        ring = []
        for j in range(rseg):
            b = 2 * math.pi * j / rseg
            lump = 1.0 + lumpy * mnoise.noise(Vector((ca * 2.3, sa * 2.3, b * 0.5 + seed)))
            fold = folds * math.sin(a * 11.0 + seed) * math.cos(b)
            rr = r * lump + fold
            p = Vector(((R + rr * math.cos(b)) * ca * sx, (R + rr * math.cos(b)) * sa * sy, rz * lump * math.sin(b)))
            ring.append(bm.verts.new(c + p))
        rings.append(ring)
    for i in range(seg):
        for j in range(rseg):
            a, b = rings[i][j], rings[i][(j + 1) % rseg]
            cc, d = rings[(i + 1) % seg][(j + 1) % rseg], rings[(i + 1) % seg][j]
            bm.faces.new((a, b, cc, d))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = K._obj(name, bm, mat)
    K.subsurf(ob, 1)
    return ob


# ---------------------------------------------------------------- the great shield
def _heater_half(s, w):
    """Half-width of a heater-kite outline at s (0 = top edge, 1 = the point): square shoulders, a long taper."""
    if s < 0.035:
        return (w / 2) * (0.86 + 0.14 * math.sqrt(s / 0.035))
    if s < 0.48:
        return (w / 2) * (1.0 - 0.07 * (s - 0.035) / 0.445)
    t = (s - 0.48) / 0.52
    return (w / 2) * 0.93 * max(0.0, math.cos(t * math.pi / 2)) ** 0.8


def great_shield(name, w, h, face, band, rim, rivet_mat, boss_mat, curve=0.9, cross_at=0.36, thick=0.022):
    """The Line-Breaker's shield, built in local space: face toward -Y, centred on the origin, point down.
    Scraped bone-white face, a dark iron cross with its arms riveted down, a riveted rim, a boss at the crossing.
    Returns (parts, local_z_of_the_crossing)."""
    rows, cols = 26, 16
    bm = bmesh.new()
    grid = []
    for j in range(rows + 1):
        s = min(j / rows, 0.992)
        z = h * 0.5 - s * h + 0.02 * h * (1 - s) ** 8
        half = _heater_half(s, w)
        row = []
        for i in range(cols + 1):
            x = (-1 + 2 * i / cols) * half
            row.append(bm.verts.new((x, curve * x * x, z)))
        grid.append(row)
    for j in range(rows):
        for i in range(cols):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if sum(f.normal.y for f in bm.faces) > 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    body = K._obj(name, bm, [face, rim])
    so = body.modifiers.new('solid', 'SOLIDIFY')
    so.thickness = thick
    so.offset = -1.0
    so.use_rim = True
    so.material_offset_rim = 1
    K.bevel(body, 0.004, 2)
    parts = [body]

    def on_face(x, z, lift=0.0):
        n = Vector((2 * curve * x, -1.0, 0.0)).normalized()
        return Vector((x, curve * x * x, z)) + n * lift, n

    # riveted rim band following the outline just inside the edge: down the left side, up the right, across the top
    inset = 0.018
    left = []
    for k in range(48):
        s = 0.012 + 0.975 * k / 47
        zz = h * 0.5 - s * h + 0.02 * h * (1 - s) ** 8
        x = max(0.004, _heater_half(s, w) - inset)
        left.append(on_face(-x, zz - (inset if k == 0 else 0.0), 0.003))
    right = [(Vector((-p.x, p.y, p.z)), Vector((-n.x, n.y, n.z))) for p, n in reversed(left)]
    x0 = -left[0][0].x
    top = [on_face(x0 - 2 * x0 * k / 9, left[0][0].z + 0.012 * math.sin(math.pi * k / 9), 0.003) for k in range(1, 9)]
    loop = left + right[1:] + top
    parts += strap(name + '_rim', [p for p, _ in loop], [n for _, n in loop], 0.032, 0.006, rim, rivet_mat,
                   rivet_every=0.07, closed=True)
    # the cross: a vertical and a horizontal iron band, riveted along both edges
    zc = h * 0.5 - cross_at * h
    vpts, vn = [], []
    for k in range(20):
        z = h * 0.5 - 0.03 - (h - 0.1) * k / 19
        p, n = on_face(0.0, z, 0.005)
        vpts.append(p)
        vn.append(n)
    parts += strap(name + '_pale', vpts, vn, 0.055, 0.007, band, rivet_mat, rivet_every=0.085)
    half = _heater_half(cross_at, w) - 0.03
    hpts, hn = [], []
    for k in range(16):
        x = -half + 2 * half * k / 15
        p, n = on_face(x, zc, 0.006)
        hpts.append(p)
        hn.append(n)
    parts += strap(name + '_fess', hpts, hn, 0.055, 0.007, band, rivet_mat, rivet_every=0.085)
    # boss at the crossing
    boss = K.lathe(name + '_boss', [(0.08, 0.0), (0.074, 0.014), (0.056, 0.034), (0.03, 0.047), (0.004, 0.051)],
                   boss_mat, seg=32, cap_bottom=False, cap_top=False)
    place(boss, on_face(0.0, zc, 0.012)[0], frame((0.0, -1.0, 0.0), back=(0.0, 0.0, 1.0)))
    K.subsurf(boss, 1)
    parts.append(boss)
    parts.append(torus(name + '_bossring', (0.0, 0.0, 0.0), 0.08, 0.009, rivet_mat, seg=32, rseg=8))
    place(parts[-1], on_face(0.0, zc, 0.012)[0], frame((0.0, -1.0, 0.0), back=(0.0, 0.0, 1.0)))
    return parts, zc


# ---------------------------------------------------------------- the broadsword
# ---------------------------------------------------------------- the round shield, the nasal helm
def round_shield(name, centre, facing, up, r, face, rim, boss, nail_mat, dish=0.03, boss_r=0.068, seed=0):
    """A round shield of planks held at its centre, the fist behind its boss: its face dished out along `facing`, its
    planks running along `up`; an iron boss over the hand, nails round it, the rim bound in rawhide. face: the planks'
    material (grit.planks: its object space is the shield's own, y along the planks, the boss at the origin)."""
    R = frame(facing, back=up)
    rnd = random.Random(seed)

    def warp(i, a):     # a board or two sprung, the rim not quite true
        return (0.004 * mnoise.noise(Vector((math.cos(a) * 1.3, math.sin(a) * 1.3, seed + 0.7))) * (i / 3.0), 0.0)
    disc = K.lathe(name + '_face', [(r, 0.0), (0.72 * r, 0.45 * dish), (0.4 * r, 0.82 * dish), (boss_r * 0.9, dish)],
                   face, seg=56, cap_bottom=False, cap_top=True, jitter=warp)
    solid(disc, 0.011, -1.0)
    parts = [disc]
    dome = K.lathe(name + '_boss', [(boss_r + 0.01, dish - 0.002), (boss_r + 0.008, dish + 0.004), (boss_r, dish + 0.008),
                                    (boss_r * 0.84, dish + 0.034), (boss_r * 0.45, dish + 0.056), (0.0, dish + 0.062)],
                   boss, seg=32, cap_bottom=True, cap_top=False, jitter=_dent(seed + 3, 0.002))
    parts.append(dome)
    parts.append(torus(name + '_rim', (0.0, 0.0, 0.0), r, 0.0095, rim, seg=64, rseg=10, lumpy=0.12, seed=seed))
    nails = []
    for k in range(6):
        a = 2.0 * math.pi * (k + 0.5) / 6.0
        nails.append(Vector((math.cos(a) * (boss_r + 0.004), math.sin(a) * (boss_r + 0.004), dish + 0.006)))
    for k in range(14):
        a = 2.0 * math.pi * (k + rnd.uniform(-0.2, 0.2)) / 14.0
        nails.append(Vector((math.cos(a) * (r - 0.03), math.sin(a) * (r - 0.03), 0.0012)))
    parts.append(rivets(name + '_nails', nails, 0.0055, nail_mat))
    for ob in parts:
        place(ob, Vector(centre), R)
    return parts


def nasal_helm(name, H, iron, rivet_mat, seed=0, dent=0.0025, band=0.024):
    """An iron skullcap and nasal on a head placed by H (the head's frame, its scale in it: body.Frame.head_frame):
    close over the head from above the brow round over the ears to the nape (face.HELM_*; face.head(helm=True) fits
    the hair under it), a riveted band round its rim and a nasal down the bridge of the nose, dented and rusted."""
    from . import face as F
    cx, cy, cz = F.HELM_C
    rx, ry, rz = F.HELM_R
    fr_, sr, br = F.HELM_RIM

    def phi_rim(th):
        c = math.cos(th)
        z = sr + (fr_ - sr) * c if c > 0.0 else sr + (sr - br) * c
        return math.acos(max(-1.0, min(1.0, (z - cz) / rz)))

    def at(th, phi, grow=0.0):
        sp, cp = math.sin(phi), math.cos(phi)
        p = Vector((cx + (rx + grow) * sp * math.sin(th), cy - (ry + grow) * sp * math.cos(th), cz + (rz + grow) * cp))
        return p + p.normalized() * dent * mnoise.noise(p * 38.0 + Vector((seed, 0.0, 0.0)))

    def cap(nm, rows, grow, top):
        """A band of the cap from the rim up: rows are fractions of the way from the rim (0) to the crown (1)."""
        nt = 48
        bm = bmesh.new()
        grid = []
        for f in rows:
            ring = []
            for i in range(nt):
                th = 2.0 * math.pi * i / nt
                pr = phi_rim(th)
                ring.append(bm.verts.new(at(th, pr - (pr - 0.05) * f, grow)))
            grid.append(ring)
        for a, b in zip(grid[:-1], grid[1:]):
            for i in range(nt):
                bm.faces.new((a[i], a[(i + 1) % nt], b[(i + 1) % nt], b[i]))
        if top:
            pole = bm.verts.new(Vector((cx, cy, cz + rz + grow)))
            for i in range(nt):
                bm.faces.new((grid[-1][i], grid[-1][(i + 1) % nt], pole))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return K._obj(nm, bm, iron)
    dome = cap(name + '_cap', [k / 13.0 for k in range(14)], 0.0, True)
    solid(dome, 0.0026, 1.0)
    K.subsurf(dome, 1)
    brim_f = band / 0.11          # the band's height as a fraction of the way to the crown
    rim_band = cap(name + '_band', [0.0, brim_f * 0.5, brim_f], 0.0026, False)
    solid(rim_band, 0.003, 1.0)
    parts = [dome, rim_band]
    rp = []
    for i in range(22):
        th = 2.0 * math.pi * (i + 0.5) / 22.0
        pr = phi_rim(th)
        rp.append(at(th, pr - (pr - 0.05) * brim_f * 0.5, 0.0062))
    top, bot = Vector(F.HELM_NASAL[0]), Vector(F.HELM_NASAL[1])
    d = (bot - top).normalized()
    ln = (bot - top).length
    parts.append(K.plate(name + '_nasal', [(-0.0115, -0.006), (0.0115, -0.006), (0.0075, ln), (-0.0075, ln)], top, d,
                         Vector((1.0, 0.0, 0.0)), 0.0032, iron))
    rp.append(top + d * 0.004 + Vector((0.0, -0.002, 0.0)))
    parts.append(rivets(name + '_rivets', rp, 0.0034, rivet_mat))
    for ob in parts:
        ob.matrix_world = H @ ob.matrix_world
    return parts


def broadsword(name, hand, direction, blade_mat, guard_mat, grip_mat, pommel_mat, length=0.9, width=0.074):
    """A heavy straight blade gripped at `hand`, pointing along `direction`: broad nearly to the tip, then a short
    angled point; straight bar guard, leather grip, disc pommel."""
    d = Vector(direction).normalized()
    hand = Vector(hand)
    R = frame(d, back=(0.0, 0.0, 1.0))
    guard_at = hand + d * 0.075
    bl = K.blade(name + '_blade', length, width, 0.013, blade_mat,
                 secs=[(0.0, 1.0), (0.72, 0.94), (0.9, 0.82), (1.0, 0.0)])
    place(bl, guard_at + d * 0.012, R)
    gd = K.rbox(name + '_guard', (0.23, 0.03, 0.032), (0, 0, 0), guard_mat, bev=0.008, segs=2)
    place(gd, guard_at, R)
    gr = K.tube(name + '_grip', hand - d * 0.075, guard_at, 0.017, 0.016, grip_mat, seg=12)
    pm = K.lathe(name + '_pommel', [(0.012, -0.016), (0.034, -0.012), (0.036, 0.0), (0.034, 0.012), (0.012, 0.016)],
                 pommel_mat, seg=24)
    place(pm, hand - d * 0.1, frame(R.col[1].to_3d(), back=(0.0, 0.0, 1.0)))
    return [bl, gd, gr, pm]


def gauntlet(name, wrist, knuckle_dir, steel, leather, fist=True, size=1.0):
    """A mitten gauntlet: flared cuff, back-of-hand plate, knuckle ridge. Built around the fist centre; size follows
    the hand inside it (a woman's is smaller)."""
    s = size
    w = Vector(wrist)
    d = Vector(knuckle_dir).normalized()
    parts = [shell(name + '_cuff', w - d * 0.06 * s, w + d * 0.015 * s, [(0.052 * s, 0.0), (0.043 * s, 1.0)], steel,
                   seg=18, lip=0.004, thick=0.004)]
    c = w + d * 0.06 * s
    hand = K.rbox(name + '_hand', (0.085 * s, 0.07 * s, 0.1 * s), (0, 0, 0), leather, bev=0.02 * s, segs=3)
    place(hand, c, frame(d, back=(0.0, 0.0, 1.0)))
    parts.append(hand)
    plate = K.rbox(name + '_plate', (0.09 * s, 0.04 * s, 0.075 * s), (0, 0, 0), steel, bev=0.012 * s, segs=2)
    place(plate, c + d * -0.008 * s, frame(d, back=(0.0, 0.0, 1.0)) @ Matrix.Translation((0, 0.028 * s, 0)))
    parts.append(plate)
    return parts


# ---------------------------------------------------------------- straps, belts, cloth
def strap(name, path, normals, w, t, mat, rivet_mat=None, rivet_every=0.07, closed=False):
    """A flat leather strap following `path`, lying against surfaces whose outward normals are `normals`."""
    P = [Vector(p) for p in path]
    Nn = [Vector(n).normalized() for n in normals]
    bm = bmesh.new()
    left, right = [], []
    n = len(P)
    for i in range(n):
        tan = (P[(i + 1) % n] - P[i - 1]) if closed else (P[min(i + 1, n - 1)] - P[max(i - 1, 0)])
        side = tan.cross(Nn[i]).normalized() * (w / 2)
        left.append(bm.verts.new(P[i] + side))
        right.append(bm.verts.new(P[i] - side))
    for i in range(n if closed else n - 1):
        j = (i + 1) % n
        bm.faces.new((left[i], left[j], right[j], right[i]))    # winding puts the face normal along +normal
    ob = K._obj(name, bm, mat)
    solid(ob, t, 1.0)
    parts = [ob]
    if rivet_mat is not None:
        rp, acc = [], 0.0
        for i in range(1, n):
            acc += (P[i] - P[i - 1]).length
            if acc >= rivet_every:
                acc = 0.0
                rp.append(P[i] + Nn[i] * (t + 0.002))
        parts.append(rivets(name + '_r', rp, w * 0.12, rivet_mat))
    return parts


def cloth_panel(name, top, outward, length, mat, rows=14, tatter=0.35, slits=2, fold=0.012, bulge=None, seed=0,
                thick=0.004):
    """A hanging panel of heavy cloth: `top` is its attached edge (points), `outward` the push-away direction per
    column. Columns hang to different lengths (a torn hem), `slits` tears run up from the hem, folds ripple it."""
    rnd = random.Random(seed)
    cols = len(top)
    lens = []
    for i in range(cols):
        f = 1.0 - tatter * rnd.random() ** 1.6
        if rnd.random() < 0.18:
            f *= 0.72
        lens.append(max(0.35, f))
    tears = set(rnd.sample(range(1, cols - 1), min(slits, max(0, cols - 2))))
    bm = bmesh.new()
    grid = []
    for i in range(cols):
        col = []
        o = Vector(outward[i]).normalized()
        for j in range(rows + 1):
            v = j / rows
            h = length * lens[i] * v
            push = (bulge(v) if bulge else 0.0) + fold * math.sin(i * 1.35 + seed + v * 2.0) * (0.4 + v)
            col.append(bm.verts.new(Vector(top[i]) + Vector((0.0, 0.0, -h)) + o * push))
        grid.append(col)
    for i in range(cols - 1):
        for j in range(rows):
            if (i + 1) in tears and j >= rows * 0.45:
                continue                                  # a tear: this seam stays open below the rip
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = K._obj(name, bm, mat)
    solid(ob, thick)
    K.subsurf(ob, 1)
    return ob


# ---------------------------------------------------------------- heads
def _head_shape(u, sex):
    """Deform a unit-sphere point into a head (unit space; the face looks toward -Y)."""
    x, y, z = u
    fem = sex == 'female'
    front = max(0.0, -y)
    # a lower crown (heads are not eggs)
    if z > 0.25:
        z = 0.25 + (z - 0.25) * 0.82
    # jaw and neck taper (a square, heavy jaw on the male form)
    if z < -0.12:
        t = min(1.0, (-z - 0.12) / 0.88)
        x *= 1.0 - (0.3 if fem else 0.1) * t
        if y > 0:
            y *= 1.0 - 0.55 * t
    # a flatter face plane
    if y < 0:
        y *= 0.9 + 0.1 * min(1.0, abs(x) * 1.6)
    # brow ridge: the shelf that puts the eyes in shadow
    g = math.exp(-((z - 0.24) ** 2) / 0.01) * math.exp(-(x * x) / 0.45) * front ** 2
    y -= (0.05 if fem else 0.09) * g
    # eye sockets
    for ex in (-0.36, 0.36):
        g = math.exp(-((x - ex) ** 2 + (z - 0.08) ** 2) / 0.024) * front
        y += 0.17 * g
    # nose: a ridge from the bridge to the tip — broad, a little broken
    if -0.42 < z < 0.22:
        prof = 0.25 + 0.75 * min(1.0, (0.22 - z) / 0.48)
        fade = 1.0 if z > -0.28 else max(0.0, 1.0 - (-0.28 - z) / 0.14)
        g = math.exp(-(x * x) / (0.016 if not fem else 0.011)) * prof * fade * front ** 3
        y -= (0.22 if fem else 0.28) * g
    # cheekbones
    for cx in (-0.55, 0.55):
        g = math.exp(-((x - cx) ** 2 + (z + 0.05) ** 2) / 0.04) * front
        y -= 0.05 * g
    # mouth line and chin
    g = math.exp(-((z + 0.5) ** 2) / 0.004) * math.exp(-(x * x) / 0.05) * front
    y += 0.035 * g
    g = math.exp(-((z + 0.8) ** 2) / 0.02) * math.exp(-(x * x) / 0.08) * front
    y -= (0.03 if fem else 0.08) * g
    # a fuller skull behind
    if y > 0 and z > -0.25:
        y *= 1.06
    return (x, y, z)


def _deformed_sphere(sex, W, D, H, keep=None, grow=1.0, seg=40, rings=28):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    kill = []
    for v in bm.verts:
        u = v.co.copy()
        x, y, z = _head_shape(u, sex)
        v.co = Vector((x * W * grow, y * D * grow, z * H * grow))
        if keep is not None and not keep(u):
            kill.append(v)
    if kill:
        bmesh.ops.delete(bm, geom=kill, context='VERTS')
    return bm


def head(name, center, sex, skin_mat, hair_mat, eye_mat, beard=True, hair_style='crop', scale=1.0):
    """Head, eyes, ears, hair and (optionally) beard. Returns (parts, eye_positions)."""
    c = Vector(center)
    s = scale * (0.95 if sex == 'female' else 1.0)
    W, D, H = 0.086 * s, 0.101 * s, 0.113 * s
    parts = []
    bm = _deformed_sphere(sex, W, D, H, seg=96, rings=64)
    bmesh.ops.translate(bm, vec=c, verts=bm.verts)
    hd = K._obj(name, bm, skin_mat)
    K.subsurf(hd, 1)
    parts.append(hd)
    # eyes sit in the sockets
    eyes = []
    for ex in (-0.36, 0.36):
        x, y, z = _head_shape((ex, -0.93, 0.12), sex)
        p = c + Vector((x * W, y * D + 0.008 * s, z * H))
        eyes.append(p)
        parts.append(K.sphere(name + '_eye', p, 0.0125 * s, eye_mat, scale=(1.15, 1.0, 0.8), seg=14, rings=10))
    for side in (-1, 1):
        parts.append(K.sphere(name + '_ear', c + Vector((side * W * 1.0, 0.004, 0.0)), 0.03 * s, skin_mat,
                              scale=(0.28, 0.55, 0.95), seg=12, rings=8))
    # hair: a close crop, or pulled back tight into a high knot. A thin, ragged layer — not a cap.
    def hairline(u):
        x, y, z = u
        h = 0.2 + (-y) * 0.2 if y < 0 else 0.2 - y * 0.6
        if y < 0 and hair_style != 'knot':        # receding at the temples
            h += 0.12 * math.exp(-((abs(x) - 0.42) ** 2) / 0.02) * (-y)
        if hair_style == 'knot':
            h -= 0.07
        return z > h + 0.05 * mnoise.noise(Vector(u) * 5.0)
    grow = 1.03 if hair_style == 'knot' else 1.016
    bmh = _deformed_sphere(sex, W, D, H, keep=hairline, grow=grow, seg=72, rings=48)
    for v in bmh.verts:                                     # scruff
        v.co += v.co.normalized() * (0.0025 * mnoise.noise(v.co * 70.0) + 0.001)
    bmesh.ops.translate(bmh, vec=c, verts=bmh.verts)
    hr = K._obj(name + '_hair', bmh, hair_mat)
    solid(hr, 0.004 * s, 1.0)
    K.subsurf(hr, 1)
    parts.append(hr)
    if hair_style == 'knot':
        parts.append(K.sphere(name + '_knot', c + Vector((0.0, D * 0.78, H * 0.55)), 0.042 * s, hair_mat,
                              scale=(1.0, 0.9, 0.8), seg=16, rings=10))
        parts.append(K.tube(name + '_tie', c + Vector((0.0, D * 0.62, H * 0.5)), c + Vector((0.0, D * 0.7, H * 0.52)),
                            0.02 * s, 0.02 * s, hair_mat, seg=10))
    if beard:
        def beardzone(u):
            x, y, z = u
            # the upper edge rises from under the nose to the cheekbones and sideburns, raggedly
            top = -0.36 + 0.42 * abs(x) ** 1.4 + 0.06 * mnoise.noise(Vector(u) * 6.0)
            return z < top and y < 0.42
        bmb = _deformed_sphere(sex, W, D, H, keep=beardzone, grow=1.055, seg=72, rings=48)
        for v in bmb.verts:      # always outward: a beard sits on the skin, never inside it
            v.co += v.co.normalized() * (0.0035 * (mnoise.noise(v.co * 55.0) + 1.0) + 0.002)
        bmesh.ops.translate(bmb, vec=c, verts=bmb.verts)
        bd = K._obj(name + '_beard', bmb, hair_mat)
        solid(bd, 0.008 * s, 1.0)
        K.subsurf(bd, 1)
        parts.append(bd)
    return parts, eyes
