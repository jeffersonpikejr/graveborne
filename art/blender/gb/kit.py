"""Procedural modeling kit — the shared vocabulary every Graveborne asset is built from.

All helpers build real meshes (bmesh) with modifiers left live, so a figure stays parametric: proportions,
pose and kit are numbers in the asset script, and variants (commander banner, revenant) are flags, not re-sculpts.
"""
import math
import random
import bmesh
import bpy
from mathutils import Matrix, Vector

from . import mat as M
from .rig import BASE_H


# ---------------------------------------------------------------- plumbing
def _link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _obj(name, bm, mats, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = _link(bpy.data.objects.new(name, me))
    for m in (mats if isinstance(mats, (list, tuple)) else [mats]):
        if m is not None:
            me.materials.append(m)
    if smooth:
        me.shade_smooth()
    return ob


def root(name='figure'):
    e = _link(bpy.data.objects.new(name, None))
    return e


def parent(children, par):
    for c in children:
        c.parent = par
    return children


def subsurf(ob, levels=2):
    m = ob.modifiers.new('sub', 'SUBSURF')
    m.levels = m.render_levels = levels
    return m


def bevel(ob, width=0.004, segs=2):
    m = ob.modifiers.new('bev', 'BEVEL')
    m.width = width
    m.segments = segs
    m.limit_method = 'ANGLE'
    m.harden_normals = False
    return m


def z_to(direction):
    """Rotation matrix taking local +Z onto `direction`."""
    return Vector(direction).normalized().to_track_quat('Z', 'Y').to_matrix().to_4x4()


# ---------------------------------------------------------------- primitives
def skin_chain(name, pts, radii, mat, levels=2, extra_edges=()):
    """An organic tube through `pts` (joint positions) with per-joint radii — limbs, bodies, tails."""
    me = bpy.data.meshes.new(name)
    edges = [(i, i + 1) for i in range(len(pts) - 1)] + list(extra_edges)
    me.from_pydata([tuple(p) for p in pts], edges, [])
    ob = _link(bpy.data.objects.new(name, me))
    sk = ob.modifiers.new('skin', 'SKIN')
    sk.use_smooth_shade = True
    sk.branch_smoothing = 0.6
    for i, r in enumerate(radii):
        rv = tuple(r) if isinstance(r, (tuple, list)) else (r, r)
        me.skin_vertices[0].data[i].radius = rv
    me.skin_vertices[0].data[0].use_root = True
    subsurf(ob, levels)
    if mat:
        me.materials.append(mat)
    return ob


def lathe(name, profile, mat, seg=32, sx=1.0, sy=1.0, loc=(0, 0, 0), arc=None, band_mats=None,
          cap_bottom=True, cap_top=True, jitter=None, smooth=True):
    """Surface of revolution about Z. profile = [(radius, z), ...] bottom → top.
    sx/sy squash the cross-section into an ellipse. arc=(a0, a1) in degrees makes an open shell
    (0° = +X, -90° = toward the camera). band_mats[i] = material index for the band between rings i and i+1.
    jitter(ring_index, angle) -> (dr, dz) perturbs vertices (ragged hems)."""
    bm = bmesh.new()
    rings = []
    closed = arc is None
    n = seg if closed else seg + 1
    a0, a1 = (0.0, 360.0) if closed else arc
    for i, (r, z) in enumerate(profile):
        ring = []
        for k in range(n):
            a = math.radians(a0 + (a1 - a0) * k / seg)
            dr, dz = jitter(i, a) if jitter else (0.0, 0.0)
            rr = max(r + dr, 1e-4)
            ring.append(bm.verts.new((rr * math.cos(a) * sx + loc[0], rr * math.sin(a) * sy + loc[1], z + dz + loc[2])))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for k in range(seg):
            k2 = (k + 1) % n if closed else k + 1
            f = bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
            if band_mats:
                f.material_index = band_mats[min(i, len(band_mats) - 1)]
    if closed and cap_bottom:
        f = bm.faces.new(list(reversed(rings[0])))
        if band_mats:
            f.material_index = band_mats[0]
    if closed and cap_top:
        f = bm.faces.new(rings[-1])
        if band_mats:
            f.material_index = band_mats[-1]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, mat, smooth)


def sphere(name, loc, r, mat, scale=(1, 1, 1), seg=24, rings=12):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    bmesh.ops.scale(bm, vec=scale, verts=bm.verts)
    bmesh.ops.translate(bm, vec=loc, verts=bm.verts)
    return _obj(name, bm, mat)


def rbox(name, size, loc, mat, rot=None, bev=0.006, segs=2, smooth=False):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    if rot is not None:
        bmesh.ops.transform(bm, matrix=rot, verts=bm.verts)
    bmesh.ops.translate(bm, vec=loc, verts=bm.verts)
    ob = _obj(name, bm, mat, smooth)
    if bev:
        bevel(ob, bev, segs)
    return ob


def tube(name, a, b, r0, r1, mat, seg=12, caps=True):
    """Tapered cylinder from point a to point b."""
    a, b = Vector(a), Vector(b)
    L = (b - a).length
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, segments=seg, radius1=r0, radius2=r1, depth=L)
    bmesh.ops.translate(bm, vec=(0, 0, L / 2), verts=bm.verts)
    bmesh.ops.transform(bm, matrix=z_to(b - a), verts=bm.verts)
    bmesh.ops.translate(bm, vec=a, verts=bm.verts)
    return _obj(name, bm, mat)


# ---------------------------------------------------------------- arms & armour
def blade(name, length, width, thick, mat, fuller=True):
    """A straight double-edged blade along +Z from the guard (z=0) to the point. Diamond section, crisp edges."""
    bm = bmesh.new()
    secs = [(0.0, 1.0), (0.55, 0.92), (0.82, 0.70), (1.0, 0.0)]
    rings = []
    for t, s in secs:
        z = t * length
        hw, ht = width / 2 * s, thick / 2 * max(s, 0.25)
        if s == 0.0:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new(p) for p in ((hw, 0, z), (0, -ht, z), (-hw, 0, z), (0, ht, z))])
    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i + 1]
        for k in range(4):
            if len(r1) == 1:
                bm.faces.new((r0[k], r0[(k + 1) % 4], r1[0]))
            else:
                bm.faces.new((r0[k], r0[(k + 1) % 4], r1[(k + 1) % 4], r1[k]))
    bm.faces.new(list(reversed(rings[0])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, mat, smooth=False)


def sword(prefix, hand, direction, mats, blade_len=0.30, blade_w=0.034, grip=0.055):
    """A one-handed arming sword gripped at `hand`, blade pointing along `direction`.
    mats = (steel, grip_leather, brass). Returns the parts."""
    steel, leather, brass = mats
    d = Vector(direction).normalized()
    hand = Vector(hand)
    rot = z_to(d)
    guard_at = hand + d * (grip * 0.55)
    parts = []
    bl = blade(prefix + '_blade', blade_len, blade_w, 0.009, steel)
    bl.matrix_world = Matrix.Translation(guard_at + d * 0.006) @ rot
    parts.append(bl)
    gd = rbox(prefix + '_guard', (0.095, 0.014, 0.012), (0, 0, 0), steel, bev=0.004)
    gd.matrix_world = Matrix.Translation(guard_at) @ rot
    parts.append(gd)
    parts.append(tube(prefix + '_grip', hand - d * (grip * 0.45), guard_at, 0.011, 0.011, leather, seg=10))
    parts.append(sphere(prefix + '_pommel', hand - d * (grip * 0.45 + 0.012), 0.016, brass, scale=(1, 1, 0.8), seg=14, rings=8))
    return parts


def _basis(direction, outward=(-1.0, 0.0, 0.0)):
    """Orthonormal frame for a hafted weapon: d along the haft, o toward the blade side, n = d x o."""
    d = Vector(direction).normalized()
    o = Vector(outward)
    o = (o - d * o.dot(d)).normalized()
    return d, o, d.cross(o)


def plate(name, pts, origin, d, o, thick, mat):
    """A flat blade/head: polygon `pts` given as (along-outward, along-haft) pairs, extruded `thick` along n."""
    n = d.cross(o)
    bm = bmesh.new()
    front = [bm.verts.new(origin + o * u + d * z + n * (thick / 2)) for u, z in pts]
    back = [bm.verts.new(origin + o * u + d * z - n * (thick / 2)) for u, z in pts]
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    k = len(pts)
    for i in range(k):
        bm.faces.new((front[i], back[i], back[(i + 1) % k], front[(i + 1) % k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = _obj(name, bm, mat, smooth=False)
    bevel(ob, min(0.003, thick * 0.4), 2)
    return ob


def axe(prefix, hand, direction, mats, haft=0.42, head_scale=1.4):
    """A one-handed bearded war axe gripped at `hand`. mats = (steel, wood, leather)."""
    steel, wood, leather = mats
    d, o, n = _basis(direction)
    hand = Vector(hand)
    base = hand - d * 0.07
    parts = [tube(prefix + '_haft', base, base + d * haft, 0.012, 0.011, wood, seg=10),
             tube(prefix + '_wrap', hand - d * 0.03, hand + d * 0.03, 0.0135, 0.0135, leather, seg=10)]
    s = head_scale
    head = [(0.0, 0.0), (0.035, 0.004), (0.068, 0.022), (0.088, 0.03), (0.094, -0.012), (0.09, -0.058),
            (0.078, -0.078), (0.06, -0.05), (0.035, -0.03), (0.012, -0.022), (0.0, -0.02)]
    at = base + d * (haft - 0.035)
    parts.append(plate(prefix + '_head', [(u * s, z * s) for u, z in head], at, d, o, 0.013, steel))
    parts.append(plate(prefix + '_poll', [(0.0, 0.0), (-0.034, 0.005), (-0.036, -0.028), (0.0, -0.026)],
                       at, d, o, 0.024, steel))
    return parts


def mace(prefix, hand, direction, mats, haft=0.32):
    """A flanged mace gripped at `hand`. mats = (steel, wood, leather)."""
    steel, wood, leather = mats
    d, o, n = _basis(direction)
    hand = Vector(hand)
    base = hand - d * 0.06
    top = base + d * haft
    parts = [tube(prefix + '_haft', base, top, 0.012, 0.012, wood, seg=10),
             tube(prefix + '_wrap', hand - d * 0.03, hand + d * 0.03, 0.0135, 0.0135, leather, seg=10),
             sphere(prefix + '_core', top, 0.034, steel, seg=16, rings=10),
             sphere(prefix + '_cap', top + d * 0.04, 0.016, steel, seg=12, rings=8)]
    for k in range(6):
        a = k * math.pi / 3
        r = o * math.cos(a) + n * math.sin(a)
        t = d.cross(r)
        rot = Matrix((r, t, d)).transposed().to_4x4()
        fl = rbox(prefix + '_flange', (0.054, 0.009, 0.092), (0, 0, 0), steel, bev=0.0025)
        fl.matrix_world = Matrix.Translation(top + r * 0.032 - d * 0.004) @ rot
        parts.append(fl)
    return parts


def spear(prefix, hand, direction, mats, length=0.95, grip_at=0.42):
    """A spear held upright at `hand`, butt toward the ground. mats = (steel, wood, leather)."""
    steel, wood, leather = mats
    d, o, n = _basis(direction)
    hand = Vector(hand)
    butt = hand - d * (length * grip_at)
    tip_base = butt + d * length
    parts = [tube(prefix + '_haft', butt, tip_base, 0.01, 0.009, wood, seg=10),
             tube(prefix + '_wrap', hand - d * 0.03, hand + d * 0.03, 0.012, 0.012, leather, seg=10)]
    bl = blade(prefix + '_head', 0.12, 0.04, 0.012, steel)
    bl.matrix_world = Matrix.Translation(tip_base) @ z_to(d)
    parts.append(bl)
    return parts


def kite_shield(name, w, h, face_mat, rim_mat, thick=0.014, curve=2.2):
    """A Norman kite shield in local space: face toward -Y, centred on the origin, point down.
    `curve` bows it around the bearer (edges curl back toward +Y)."""
    bm = bmesh.new()
    rows, cols = 18, 12
    grid = []
    for j in range(rows + 1):
        s = j / rows                                   # 0 top → 1 bottom
        s_eff = min(s, 0.985)
        z = h * 0.5 - s_eff * h
        top_bulge = 0.05 * h * (1 - s) ** 6            # the rounded top edge
        half = (w / 2) * max(0.0, 1 - s_eff ** 2.1) ** 0.72
        row = []
        for i in range(cols + 1):
            u = -1 + 2 * i / cols
            x = u * half
            zz = z + top_bulge * math.cos(u * math.pi / 2)
            row.append(bm.verts.new((x, curve * x * x, zz)))
        grid.append(row)
    for j in range(rows):
        for i in range(cols):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # make sure the face normal points toward the viewer (-Y)
    if sum(f.normal.y for f in bm.faces) > 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    ob = _obj(name, bm, [face_mat, rim_mat])
    so = ob.modifiers.new('solid', 'SOLIDIFY')
    so.thickness = thick
    so.offset = 1.0
    so.use_rim = True
    so.material_offset_rim = 1
    so.material_offset = 0
    bevel(ob, 0.003, 2)
    return ob


def banner(name, length, height, mat, swallow=0.3, wave=0.018, cols=22, rows=10, seed=3):
    """A flag in the XZ plane hanging from its hoist edge at x=0 (top at z=0), streaming toward +X."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    grid = []
    ph = rnd.uniform(0, 6)
    for j in range(rows + 1):
        v = j / rows                          # 0 top → 1 bottom
        row = []
        for i in range(cols + 1):
            u = i / cols
            x = u * length
            # swallowtail: cut a V into the fly end
            notch = swallow * length * (1 - abs(2 * v - 1)) if swallow else 0.0
            x = min(x, length - notch * (u ** 4))
            y = wave * u * math.sin(u * 7.5 + ph) + 0.006 * math.sin(v * 5 + u * 3)
            z = -v * height - 0.02 * u * u        # droops a touch toward the fly
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for j in range(rows):
        for i in range(cols):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    ob = _obj(name, bm, mat)
    so = ob.modifiers.new('solid', 'SOLIDIFY')
    so.thickness = 0.004
    so.offset = 0.0
    subsurf(ob, 1)
    return ob


def glow(name, loc, color, energy, radius=0.02):
    """A small coloured point light — eyes and fires that should light what's around them."""
    ld = bpy.data.lights.new(name, 'POINT')
    ld.energy = energy
    ld.color = M.hexlin(color)
    ld.shadow_soft_size = radius
    ob = _link(bpy.data.objects.new(name, ld))
    ob.location = loc
    return ob


# ---------------------------------------------------------------- the miniature base
def mini_base(team='company', radius=0.36, seed=1, dressing=True):
    """A round wargaming base: a painted rim in the side's colour, a textured earth top, pebbles and a tuft.
    The rim colour is how friend and foe stay readable at 20px without the old coloured chips."""
    rim = M.painted('base_rim_' + team, M.PAL['team_' + team], rough=0.6, edge=0.25, wash=0.55, grime=0.2,
                    kind='stone', cracks=0.0, corrupt=False)
    earth = M.painted('base_earth', '#3a3224', rough=0.95, edge=0.25, wash=0.7, grime=0.35, kind='earth',
                      bump=0.9, bump_scale=60.0, cracks=0.0)
    under = M.painted('base_under', '#15120e', rough=0.9, edge=0.0, wash=0.2, grime=0.0, kind='stone',
                      cracks=0.0, corrupt=False)
    H = BASE_H
    prof = [(radius * 0.97, 0.0), (radius, 0.004), (radius, H * 0.55), (radius * 0.985, H * 0.9),
            (radius * 0.955, H), (radius * 0.7, H + 0.002), (radius * 0.35, H + 0.003), (0.001, H + 0.003)]
    b = lathe('base', prof, [rim, earth, under], seg=64, band_mats=[2, 0, 0, 0, 1, 1, 1], cap_top=False)
    parts = [b]
    if dressing:
        rnd = random.Random(seed)
        stone = M.painted('base_pebble', '#57503f', rough=0.8, edge=0.6, wash=0.6, grime=0.2, kind='stone', cracks=0.0)
        for _ in range(rnd.randint(4, 7)):
            a = rnd.uniform(0, 2 * math.pi)
            rr = rnd.uniform(0.16, radius * 0.85)
            s = rnd.uniform(0.012, 0.026)
            parts.append(sphere('pebble', (rr * math.cos(a), rr * math.sin(a), H + s * 0.3), s, stone,
                                scale=(1.0, rnd.uniform(0.7, 1.2), 0.55), seg=10, rings=6))
        grass = M.painted('base_grass', '#4a4a26', rough=0.9, edge=0.4, wash=0.4, grime=0.2, kind='cloth', cracks=0.0)
        for _ in range(rnd.randint(1, 2)):
            a = rnd.uniform(0, 2 * math.pi)
            rr = rnd.uniform(0.2, radius * 0.8)
            cx, cy = rr * math.cos(a), rr * math.sin(a)
            for k in range(7):
                ang = rnd.uniform(0, 2 * math.pi)
                tip = Vector((cx + math.cos(ang) * 0.03, cy + math.sin(ang) * 0.03, H + rnd.uniform(0.045, 0.075)))
                parts.append(tube('tuft', (cx, cy, H), tip, 0.004, 0.0005, grass, seg=4))
    return parts
