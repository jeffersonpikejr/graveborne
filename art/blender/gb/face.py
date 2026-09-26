"""Faces — heads whose features read, from a battle sprite up to a portrait.

Stylised at the RuneScape / Project Zomboid level: every feature is its own shape, slightly exaggerated —
eyes with whites, irises and heavy lids; thick brows; a nose with a bridge, tip and nostrils; lips; shaped ears;
hair and beards with volume and tufts — so a face survives the trip down to a 20px sprite and holds up close.

Everything is built in the head's own frame (metres, origin at the skull centre, face toward -Y, up +Z). The skull
is sculpted first; every feature is then placed on it by ray-casting, so features sit on the face whatever its
proportions. head() returns an empty the caller places: tilt, scale and position move the whole head as one.
"""
import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils import noise as mnoise
from mathutils.bvhtree import BVHTree

from . import kit as K
from .mat import MODE, hexlin

# per-form proportions (metres) and feature sizes
# Proportions follow the grimdark portrait reference sheet: long, gaunt faces; eyes at mid-head, narrow and
# heavy-lidded over dark circles; thin low brows; a long nose rising out of the brow; a small thin-lipped mouth a
# third of the way from nose to chin; hollow cheeks under hard cheekbones.
FORMS = {
    'male':   dict(W=0.078, D=0.1, H=0.121, jaw=0.04, chin=0.08, brow=0.075, eye=0.0122, eye_x=0.0292, eye_z=0.004,
                   nose=1.0, mouth=0.021, lip=1.0),
    'female': dict(W=0.072, D=0.096, H=0.115, jaw=0.22, chin=0.035, brow=0.045, eye=0.0122, eye_x=0.0278, eye_z=0.004,
                   nose=0.86, mouth=0.019, lip=1.08),
}


def _shape(u, f):
    """Unit sphere point -> head (unit space). Only the skull's masses: features are separate meshes."""
    x, y, z = u
    front = max(0.0, -y)
    if z > 0.25:                                      # a lower crown: heads are not eggs
        z = 0.25 + (z - 0.25) * 0.82
    if z < -0.12:                                     # jaw and neck taper
        t = min(1.0, (-z - 0.12) / 0.88)
        x *= 1.0 - f['jaw'] * t
        if y > 0:
            y *= 1.0 - 0.55 * t
    if y < 0:                                         # a flatter face plane
        y *= 0.9 + 0.1 * min(1.0, abs(x) * 1.6)
    ez = f['eye_z'] / f['H']                          # sockets sit exactly where the eyes go
    ex_u = f['eye_x'] / f['W']
    g = math.exp(-((z - ez - 0.17) ** 2) / 0.008) * math.exp(-(x * x) / 0.45) * front ** 2
    y -= f['brow'] * g                                # brow shelf, low over the eyes
    for ex in (-ex_u, ex_u):                          # eye sockets
        g = math.exp(-((x - ex) ** 2 + (z - ez) ** 2) / 0.026) * front
        y += 0.17 * g
    g = math.exp(-(x * x) / 0.02) * math.exp(-((z - ez + 0.1) ** 2) / 0.02) * front ** 3
    y -= 0.05 * g                                     # the nose's root between the eyes
    for cx in (-0.55, 0.55):                          # hard cheekbones, and gaunt hollows under them
        g = math.exp(-((x - cx) ** 2 + (z - ez + 0.14) ** 2) / 0.035) * front
        y -= 0.055 * g
        g = math.exp(-((x - cx * 0.88) ** 2 + (z + 0.42) ** 2) / 0.03) * front
        y += 0.055 * g
    g = math.exp(-(x * x) / 0.06) * math.exp(-((z + 0.55) ** 2) / 0.05) * front
    y -= 0.03 * g                                     # the muzzle the lips sit on
    g = math.exp(-((z + 0.82) ** 2) / 0.02) * math.exp(-(x * x) / 0.08) * front
    y -= f['chin'] * g                                # chin
    if y > 0 and z > -0.25:
        y *= 1.06
    return x, y, z


class _Skull:
    def __init__(self, f, seg=128, rings=96):
        self.f = f
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
        for v in bm.verts:
            x, y, z = _shape(v.co.copy(), f)
            v.co = Vector((x * f['W'], y * f['D'], z * f['H']))
        bm.normal_update()
        bm.verts.ensure_lookup_table()
        bm.verts.index_update()
        self.bm = bm
        self.bvh = BVHTree.FromBMesh(bm)

    def hit(self, x, z, lift=0.0):
        """The front surface at (x, z), pushed `lift` out along the normal."""
        loc, n, _, _ = self.bvh.ray_cast(Vector((x, -1.0, z)), Vector((0.0, 1.0, 0.0)))
        if loc is None:
            return Vector((x, 0.0, z)), Vector((0.0, -1.0, 0.0))
        return loc + n * lift, n

    def region(self, name, keep, mat, push, thick=0.003, levels=1):
        """A copy of the skull faces where keep(centre) is true, each vertex pushed out by push(co, normal)."""
        bm = bmesh.new()
        vmap = {}
        for face in self.bm.faces:
            c = face.calc_center_median()
            if not keep(c):
                continue
            vs = []
            for v in face.verts:
                if v.index not in vmap:
                    vmap[v.index] = bm.verts.new(v.co + v.normal * push(v.co, v.normal))
                vs.append(vmap[v.index])
            bm.faces.new(vs)
        if not bm.faces:
            bm.verts.new((0.0, 0.0, -1.0))
        ob = K._obj(name, bm, mat)
        if thick:
            m = ob.modifiers.new('solid', 'SOLIDIFY')
            m.thickness = thick
            m.offset = -1.0
        if levels:
            K.subsurf(ob, levels)
        return ob

    def mesh(self, name, mat):
        self.bm.verts.index_update()
        me = bpy.data.meshes.new(name)
        self.bm.to_mesh(me)
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        me.materials.append(mat)
        me.shade_smooth()
        return ob


def _ball(name, r, mat, loc, scale=(1.0, 1.0, 1.0), seg=24, rings=16):
    """A sphere built at the origin and moved by location, so its object space is its own (for eye masks)."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    bmesh.ops.scale(bm, vec=scale, verts=bm.verts)
    ob = K._obj(name, bm, mat)
    ob.location = Vector(loc)
    return ob


def _cap(name, r, mat, loc, keep, thick=0.0022):
    """Part of a sphere around `loc` (an eyelid): keep(x, y, z) in the sphere's own frame."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=28, radius=r)
    kill = [v for v in bm.verts if not keep(v.co.x / r, v.co.y / r, v.co.z / r)]
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    ob = K._obj(name, bm, mat)
    ob.location = Vector(loc)
    m = ob.modifiers.new('solid', 'SOLIDIFY')
    m.thickness = thick
    m.offset = 1.0
    K.subsurf(ob, 1)
    return ob


def _ribbon(name, pts, normals, widths, t, mat):
    """A tapered flat strip lying on the face (a brow)."""
    bm = bmesh.new()
    L, R = [], []
    n = len(pts)
    for i in range(n):
        tan = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        side = tan.cross(normals[i]).normalized() * (widths[i] / 2)
        L.append(bm.verts.new(pts[i] + side))
        R.append(bm.verts.new(pts[i] - side))
    for i in range(n - 1):
        bm.faces.new((L[i], L[i + 1], R[i + 1], R[i]))
    ob = K._obj(name, bm, mat)
    m = ob.modifiers.new('solid', 'SOLIDIFY')
    m.thickness = t
    m.offset = 1.0
    K.subsurf(ob, 2)
    return ob


def _tufts(name, ob_src, n, length, radius, droop, mat, seed=0, outward=0.7):
    """Scatter small cones over a mesh's outer surface: the chunky texture of hair and beards."""
    rnd = random.Random(seed)
    me = ob_src.data
    polys = [p for p in me.polygons]
    if not polys:
        return None
    areas = [p.area for p in polys]
    total = sum(areas)
    bm = bmesh.new()
    for _ in range(n):
        r = rnd.random() * total
        acc = 0.0
        for p, a in zip(polys, areas):
            acc += a
            if acc >= r:
                break
        c = Vector(p.center)
        nrm = Vector(p.normal)
        d = (nrm * outward + Vector(droop) * (1.0 - outward)).normalized()
        ln = length * rnd.uniform(0.6, 1.25)
        cone = bmesh.ops.create_cone(bm, cap_ends=True, segments=5, radius1=radius * rnd.uniform(0.7, 1.2),
                                     radius2=0.0, depth=ln)
        vs = cone['verts']
        bmesh.ops.translate(bm, vec=(0, 0, ln / 2), verts=vs)
        rot = d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        bmesh.ops.transform(bm, matrix=rot, verts=vs)
        bmesh.ops.translate(bm, vec=c - nrm * radius * 0.6, verts=vs)
    return K._obj(name, bm, mat)


def head(name, sex, skin, lips, hair, eye_mat, dark, beard=True, hair_style='crop', scar=None, crooked=0.0,
         greying=None, seed=0):
    """Build a head. Returns (root_empty, info). Place the root; everything else follows it.

    skin/lips/hair/eye_mat/dark are materials (dark: nostrils); scar: side (+1/-1) to cut a founding scar down
    through the brow past the eye's outer corner; crooked: a once-broken nose's sideways kink (metres);
    greying: an optional second hair material mixed into the beard and temples (a veteran)."""
    f = FORMS[sex]
    rnd = random.Random(seed)
    sk = _Skull(f)
    parts = [sk.mesh(name, skin)]
    K.subsurf(parts[0], 1)
    W, D, H = f['W'], f['D'], f['H']

    # ---- eyes: a dim white, iris, pupil — a narrow almond under a heavy upper lid, a lower lid under it
    re = f['eye']
    ez = f['eye_z']
    eyes = []
    for s in (-1, 1):
        p, _ = sk.hit(s * f['eye_x'], ez)
        c = p + Vector((0.0, re - 0.005, 0.0))
        eyes.append(c)
        parts.append(_ball(f'{name}_eye', re, eye_mat, c))
        up = lambda x, y, z: y < 0.4 and z > 0.2 * (1 - x * x) - 0.03           # noqa: E731 — heavy, tired lid
        lo = lambda x, y, z: y < 0.35 and z < -0.36 * (1 - x * x) + 0.02         # noqa: E731
        parts.append(_cap(f'{name}_lid', re + 0.0012, skin, c, up, thick=0.003))
        parts.append(_cap(f'{name}_lidlo', re + 0.0009, skin, c, lo, thick=0.0018))

    # ---- brows: thin, low and straight, lowered at the inner end (a face that has stopped flinching)
    for s in (-1, 1):
        xs = [0.008, 0.019, 0.031, 0.043, 0.053]
        zs = [ez + 0.012, ez + 0.017, ez + 0.02, ez + 0.019, ez + 0.014]
        ws = [0.0048, 0.0058, 0.0055, 0.0045, 0.0024]
        segs = [list(range(5))]
        if scar == s:                                  # the scar cuts the brow in two
            segs = [[0, 1, 2], [3, 4]]
        for k, idx in enumerate(segs):
            P, Nn = [], []
            for i in idx:
                x = s * xs[i]
                if scar == s and k == 0 and i == idx[-1]:
                    x = s * 0.038
                if scar == s and k == 1 and i == idx[0]:
                    x = s * 0.05
                pp, nn = sk.hit(x, zs[i], 0.0022)
                P.append(pp)
                Nn.append(nn)
            if len(P) >= 2:
                parts.append(_ribbon(f'{name}_brow', P, Nn, [ws[i] for i in idx], 0.0024, hair))

    # ---- nose: lofted out of the face — a long bridge rising from between the brows to a narrow tip, its edges
    # sunk into the skin so it grows from the face instead of sitting on it; nostril wings; the dark of the nostrils
    ns = f['nose']
    stations = [(ez + 0.016, 0.002, 0.0115), (ez, 0.0065, 0.0078), (ez - 0.016, 0.0105, 0.007),
                (ez - 0.03, 0.0155, 0.0076), (ez - 0.04, 0.0185, 0.0092), (ez - 0.047, 0.0115, 0.0086),
                (ez - 0.052, 0.002, 0.0062)]
    nb = bmesh.new()
    rows = []
    for k, (z, pr, w) in enumerate(stations):
        kink = crooked * math.sin(math.pi * min(1.0, k / 4.0))          # a once-broken nose bends mid-bridge
        row = []
        for j in range(9):
            th = -math.pi / 2 + math.pi * j / 8
            x = w * ns * math.sin(th) + kink
            face_y = sk.hit(x, z)[0].y
            y = face_y + 0.0035 - (pr * ns + 0.0035) * max(0.0, math.cos(th)) ** 1.25
            row.append(nb.verts.new((x, y, z)))
        rows.append(row)
    for k in range(len(rows) - 1):
        for j in range(8):
            nb.faces.new((rows[k][j], rows[k][j + 1], rows[k + 1][j + 1], rows[k + 1][j]))
    bmesh.ops.recalc_face_normals(nb, faces=nb.faces)
    nose = K._obj(f'{name}_nose', nb, skin)
    K.subsurf(nose, 2)
    parts.append(nose)
    zt = ez - 0.042
    tip = Vector((crooked * 0.6, sk.hit(0.0, zt)[0].y - 0.0185 * ns, zt))
    for s in (-1, 1):
        parts.append(_ball(f'{name}_ala', 0.0056 * ns, skin, tip + Vector((s * 0.0098 * ns, 0.0095, -0.002)),
                           scale=(1.0, 1.15, 0.85), seg=16, rings=10))
        parts.append(_ball(f'{name}_nostril', 0.0024 * ns, dark, tip + Vector((s * 0.0048 * ns, 0.0062, -0.0068)),
                           scale=(1.3, 1.0, 0.65), seg=10, rings=6))

    # ---- lips: thin and small, a third of the way from nose to chin, the corners turned down
    mw = f['mouth']
    for which, z0, drop, rc, rs, lift in (('lip', ez - 0.07, 0.0034, 0.0021, 0.001, 0.0014),
                                          ('liplo', ez - 0.0765, 0.0018, 0.0029, 0.0012, 0.0009)):
        P, R = [], []
        for k in range(7):
            x = -mw + 2 * mw * k / 6
            t = x / mw
            z = z0 - drop * t * t
            if which == 'lip':
                z -= 0.0011 * math.exp(-(x / 0.004) ** 2)       # the bow
            pp, _ = sk.hit(x, z, lift)
            P.append(pp)
            rr = (rs + (rc - rs) * (1 - t * t)) * f['lip']
            R.append((rr, rr * 0.65))
        parts.append(K.skin_chain(f'{name}_{which}', P, R, lips))

    # ---- ears, from the brow line down to the nose's base: a flat body swept back, a rolled rim (helix) round the
    # back and top, the lobe below, and a reddish hollow (concha) in front of the canal — never a black hole
    for s in (-1, 1):
        c = Vector((s * (W * 0.99), 0.012, ez - 0.016))
        tilt = (math.radians(-14), 0.0, s * math.radians(-12))
        body = _ball(f'{name}_ear', 1.0, skin, c, scale=(0.0065, 0.016, 0.028), seg=20, rings=14)
        body.rotation_euler = tilt
        parts.append(body)
        for k, (dy, dz, r) in enumerate(((0.009, 0.012, 0.0042), (0.013, 0.0, 0.0038), (0.01, -0.012, 0.0036),
                                          (0.002, 0.021, 0.0036))):
            rim = _ball(f'{name}_helix', r, skin, c + Vector((s * 0.0045, dy, dz)), scale=(0.9, 1.0, 1.6), seg=12, rings=8)
            rim.rotation_euler = tilt
            parts.append(rim)
        parts.append(_ball(f'{name}_lobe', 0.0058, skin, c + Vector((s * 0.002, 0.004, -0.026)), scale=(0.8, 1.0, 1.1),
                           seg=12, rings=8))
        concha = _ball(f'{name}_concha', 1.0, lips, c + Vector((s * 0.0045, -0.001, -0.004)), scale=(0.0035, 0.008, 0.011),
                       seg=12, rings=8)
        concha.rotation_euler = tilt
        parts.append(concha)

    # ---- beard: thickest at the chin, a ragged upper edge, a mustache, tufts
    if beard:
        def bzone(c):
            x, y, z = c
            if y > 0.045:
                return False
            top = ez - 0.084 + 0.084 * min(1.0, abs(x) / 0.066) ** 1.3 + 0.005 * mnoise.noise(c * 90.0)
            mouth = abs(x) < mw + 0.005 and ez - 0.084 < z < ez - 0.062
            return z < top and not mouth

        def bpush(co, n):
            chin = math.exp(-(co.x / 0.034) ** 2) * min(1.0, max(0.0, (ez - 0.072 - co.z) / 0.045))
            return 0.004 + 0.011 * chin + 0.0022 * (mnoise.noise(co * 110.0) + 1.0)
        bmat = greying or hair
        bd = sk.region(f'{name}_beard', bzone, hair, bpush, thick=0.004)
        parts.append(bd)
        tuft = _tufts(f'{name}_beardtufts', bd, 150, 0.011, 0.0024, (0.0, -0.2, -1.0), bmat, seed=seed + 1, outward=0.55)
        if tuft:
            parts.append(tuft)
        P, R = [], []
        for x, z, r in ((-mw - 0.004, ez - 0.086, 0.0024), (-0.016, ez - 0.067, 0.004), (0.0, ez - 0.0625, 0.0046),
                        (0.016, ez - 0.067, 0.004), (mw + 0.004, ez - 0.086, 0.0024)):
            pp, _ = sk.hit(x, z, 0.0055)
            P.append(pp)
            R.append((r, r * 0.8))
        parts.append(K.skin_chain(f'{name}_moustache', P, R, hair))

    # ---- hair
    def hairline(c, recede):
        x, y, z = c
        front = max(0.0, -y / D)
        back = max(0.0, y / D)
        h = 0.038 + 0.03 * front - 0.105 * back
        h += recede * 0.012 * math.exp(-((abs(x) - 0.045) / 0.012) ** 2) * front
        return z > h + 0.004 * mnoise.noise(c * 80.0)
    if hair_style == 'crop':
        hr = sk.region(f'{name}_hair', lambda c: hairline(c, 1.0), hair,
                       lambda co, n: 0.003 + 0.0012 * (mnoise.noise(co * 120.0) + 1.0), thick=0.003)
        parts.append(hr)
        tuft = _tufts(f'{name}_hairtufts', hr, 260, 0.0075, 0.0024, (0.0, 1.0, -0.3), greying or hair, seed=seed + 2,
                      outward=0.6)
        if tuft:
            parts.append(tuft)
    else:   # the war-knot: pulled back hard, a bound knot at the crown, loose strands framing the face
        hr = sk.region(f'{name}_hair', lambda c: hairline(c, 0.0) or (c.y > 0.02 and c.z > -0.075), hair,
                       lambda co, n: 0.004 + 0.0015 * (mnoise.noise(co * 90.0) + 1.0), thick=0.004)
        parts.append(hr)
        tuft = _tufts(f'{name}_hairtufts', hr, 220, 0.012, 0.0022, (0.0, 1.0, 0.25), hair, seed=seed + 2,
                      outward=0.2)                  # flat, swept back toward the knot
        if tuft:
            parts.append(tuft)
        knot = Vector((0.0, D * 0.62, H * 0.86))
        parts.append(_ball(f'{name}_knot', 0.024, hair, knot, scale=(1.0, 1.05, 0.85), seg=18, rings=12))
        for k in range(2):
            coil = K.lathe(f'{name}_coil', [(0.02 + 0.004 * k, -0.008), (0.028 + 0.004 * k, 0.0), (0.02 + 0.004 * k, 0.008)],
                           hair, seg=20, cap_bottom=False, cap_top=False)
            coil.location = knot + Vector((0.0, 0.004 * k, -0.012 - 0.009 * k))
            coil.rotation_euler = (math.radians(-35), 0.0, 0.0)
            parts.append(coil)
        parts.append(K.tube(f'{name}_tie', knot + Vector((0.0, -0.012, -0.03)), knot + Vector((0.0, -0.004, -0.018)),
                            0.014, 0.014, dark, seg=12))
        for s in (-1, 1):                              # loose strands at the temples, hanging past the ears
            P, R = [], []
            for k, (x, z) in enumerate(((0.056, 0.055), (0.066, 0.03), (0.071, 0.0), (0.07, -0.03), (0.066, -0.058))):
                pp, _ = sk.hit(s * x, z, 0.0065 + 0.002 * math.sin(k * 1.7 + s))
                P.append(pp)
                R.append((0.0048 - 0.0005 * k, 0.0032))
            parts.append(K.skin_chain(f'{name}_strand', P, R, hair))

    # ---- the founding scar: a raised seam from the brow, past the eye's outer corner, onto the cheek
    if scar:
        P, R = [], []
        for x, z in ((0.036, 0.066), (0.041, 0.045), (0.046, 0.022), (0.05, 0.0), (0.05, -0.022), (0.046, -0.042)):
            pp, _ = sk.hit(scar * x, z, 0.0012)
            P.append(pp)
            R.append((0.0016, 0.001))
        scar_m = bpy.data.materials.new(name + '_scar')
        scar_m.use_nodes = True
        b = scar_m.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = (*hexlin('#6f5f78' if MODE['revenant'] else '#8a3f37'), 1.0)
        b.inputs['Roughness'].default_value = 0.45
        parts.append(K.skin_chain(f'{name}_scar', P, R, scar_m))

    root = K.root(name + '_root')
    K.parent(parts, root)
    return root, dict(eyes=eyes, chin=sk.hit(0.0, -0.1)[0])
