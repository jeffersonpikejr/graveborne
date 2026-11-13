"""Terrain kit — what stands on the battlefield: stone, bark, foliage, bone, blight-flesh, and the geometry they go on.

Everything here is built in numpy and handed to Blender as finished meshes (Acc), so a tree is ten thousand blades
at the cost of one object. The materials are grit materials (gb/grit.py's _G): the same grime in the recesses, the
same mud climbing from the same ground line, the same grade as the figures that stand next to them.

World contract (gb/rig.py): 1 unit = 1 tile, origin = tile centre, +Y north (away from the camera), +Z up. The camera
looks north pitched 45 degrees down, so a tile is 1.0 wide in X by 1.414 deep in Y on the ground (FOOT_Y), and
a point's height up the screen is 0.707 * (y + z).
"""
import math

import bmesh
import bpy
import numpy as np
from bmesh.types import BMVert

from .face import _Noise
from .grit import COL, _G, _lerp
from .mat import _CACHE, MODE, _maprange, _math, _mix, hexlin

FOOT_X = 0.5                    # half a tile across
FOOT_Y = 0.5 * math.sqrt(2.0)   # half a tile deep, on the ground, under the 45-degree camera
BLIGHT = '#b07cf0'


# ================================================================ noise
class Field:
    """Fractal value noise over points (numpy), in roughly [0, 1]."""

    def __init__(self, seed):
        self.n = _Noise(seed)
        self.off = np.random.default_rng(seed).uniform(3.0, 40.0, 3)

    def __call__(self, P, scale, octaves=4, gain=0.5):
        P = np.asarray(P, np.float64).reshape(-1, 3) + self.off
        out = np.zeros(len(P))
        amp, tot = 1.0, 0.0
        for k in range(octaves):
            out += amp * self.n(P + 17.3 * k, scale * 2.0 ** k)
            tot += amp
            amp *= gain
        return out / tot

    def vec(self, P, scale, octaves=2):
        """Three decorrelated channels, centred on 0."""
        P = np.asarray(P, np.float64).reshape(-1, 3)
        return np.column_stack([self(P + 31.7 * k, scale, octaves) - 0.5 for k in range(3)])


def unit(v):
    v = np.asarray(v, np.float64)
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.maximum(n, 1e-9)


# ================================================================ mesh accumulator
class Acc:
    """Triangles gathered in numpy, built into one mesh object. Each add() may carry UVs (per vertex) and a
    material slot."""

    def __init__(self):
        self.V, self.F, self.UV, self.MI = [], [], [], []
        self.n = 0

    def add(self, V, F, uv=None, mi=0):
        V = np.asarray(V, np.float64).reshape(-1, 3)
        F = np.asarray(F, np.int64).reshape(-1, 3)
        if len(V) == 0 or len(F) == 0:
            return
        self.V.append(V)
        self.F.append(F + self.n)
        self.UV.append(np.asarray(uv, np.float64) if uv is not None else np.zeros((len(V), 2)))
        self.MI.append(np.full(len(F), mi, np.int32))
        self.n += len(V)

    def empty(self):
        return self.n == 0

    def points(self):
        return np.concatenate(self.V) if self.V else np.zeros((0, 3))

    def transform(self, scale=1.0, offset=(0.0, 0.0, 0.0), rot_z=0.0):
        c, s = math.cos(rot_z), math.sin(rot_z)
        R = np.array(((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0)))
        self.V = [(v @ R.T) * scale + np.asarray(offset) for v in self.V]

    def apply(self, R=None, t=(0.0, 0.0, 0.0), scale=1.0):
        """Rotate (3x3), scale and move everything gathered so far."""
        R = np.eye(3) if R is None else np.asarray(R, np.float64)
        self.V = [(v @ R.T) * scale + np.asarray(t, np.float64) for v in self.V]
        return self

    def merge(self, other, mi=None):
        base = 0
        for V, F, UV, MI in zip(other.V, other.F, other.UV, other.MI):
            self.V.append(V)
            self.F.append(F - base + self.n)
            self.UV.append(UV)
            self.MI.append(MI if mi is None else np.full(len(MI), mi, np.int32))
            self.n += len(V)
            base += len(V)
        return self

    def obj(self, name, mats, smooth=True, weld=0.0):
        if self.n == 0:
            return None
        V = np.concatenate(self.V).astype(np.float32)
        F = np.concatenate(self.F).astype(np.int32)
        UV = np.concatenate(self.UV).astype(np.float32)
        MI = np.concatenate(self.MI)
        me = bpy.data.meshes.new(name)
        nf = len(F)
        me.vertices.add(len(V))
        me.vertices.foreach_set('co', V.ravel())
        me.loops.add(nf * 3)
        me.loops.foreach_set('vertex_index', F.ravel())
        me.polygons.add(nf)
        me.polygons.foreach_set('loop_start', np.arange(0, nf * 3, 3, dtype=np.int32))
        try:
            me.polygons.foreach_set('loop_total', np.full(nf, 3, np.int32))
        except Exception:       # derived from the offsets in newer Blenders
            pass
        me.polygons.foreach_set('material_index', MI)
        uvl = me.uv_layers.new(name='UVMap')
        uvl.data.foreach_set('uv', UV[F.ravel()].ravel())
        me.update(calc_edges=True)
        me.validate()
        for m in (mats if isinstance(mats, (list, tuple)) else [mats]):
            me.materials.append(m)
        if smooth:
            me.shade_smooth()
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        if weld:
            w = ob.modifiers.new('weld', 'WELD')
            w.merge_threshold = weld
        return ob


def clip(ob, planes):
    """Cut a mesh object by planes, keeping the side each normal points away from: [(point, normal), ...]."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    for co, no in planes:
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                               clear_outer=True, clear_inner=False, dist=1e-6)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return ob


def clip_tile(ob, south=False, pad=0.0):
    """Cut a mesh to the tile's footprint: flush at x = +-0.5 and at the north edge (and the south, if asked).
    pad: let it run that far past x = +-0.5 (a pixel and a half of overlap, so the antialiased edges of two
    neighbouring sprites don't leave a hairline of ground showing between them)."""
    planes = [((FOOT_X + pad, 0, 0), (1, 0, 0)), ((-FOOT_X - pad, 0, 0), (-1, 0, 0)), ((0, FOOT_Y, 0), (0, 1, 0))]
    if south:
        planes.append(((0, -FOOT_Y, 0), (0, -1, 0)))
    return clip(ob, planes)


# ================================================================ geometry: tubes, blades, rocks, blocks
def _frames(P):
    """Parallel-transport frames along a polyline: tangents, normals (starting toward +Y, so a tube's UV seam is on
    the side away from the camera), binormals."""
    P = np.asarray(P, np.float64)
    T = np.zeros_like(P)
    T[1:-1] = P[2:] - P[:-2]
    T[0] = P[1] - P[0]
    T[-1] = P[-1] - P[-2]
    T = unit(T)
    N = np.zeros_like(P)
    ref = np.array((0.0, 1.0, 0.0))
    n0 = ref - T[0] * (ref @ T[0])
    if np.linalg.norm(n0) < 0.05:
        ref = np.array((1.0, 0.0, 0.0))
        n0 = ref - T[0] * (ref @ T[0])
    N[0] = unit(n0)
    for i in range(1, len(P)):
        v = N[i - 1] - T[i] * (N[i - 1] @ T[i])
        N[i] = unit(v)
    B = np.cross(T, N)
    return T, N, B


def tube(P, R, seg=8, nz=None, rough=0.0, rough_scale=18.0, cap0=False, cap1=False, v0=0.0, squash=1.0):
    """A tube swept along the polyline P with radii R: (V, F, UV). rough: its surface pushed in and out by noise (a
    share of the radius). UV: u round it (0..1), v its length in world units. squash: flattens it along its normal."""
    P = np.asarray(P, np.float64)
    R = np.broadcast_to(np.asarray(R, np.float64), (len(P),)).copy()
    T, N, B = _frames(P)
    a = np.linspace(0.0, 2.0 * math.pi, seg + 1)
    ring = np.cos(a)[None, :, None] * N[:, None, :] * squash + np.sin(a)[None, :, None] * B[:, None, :]
    V = P[:, None, :] + ring * R[:, None, None]
    if nz is not None and rough:
        d = (nz(V.reshape(-1, 3), rough_scale, 3) - 0.5).reshape(len(P), seg + 1) * 2.0 * rough
        d[:, -1] = d[:, 0]
        V = P[:, None, :] + ring * (R[:, None] * (1.0 + d))[:, :, None]
    ln = np.concatenate(([0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1)))) + v0
    UV = np.stack(np.broadcast_arrays((a / (2.0 * math.pi))[None, :], ln[:, None]), axis=-1)
    n, m = len(P), seg + 1
    i, k = np.meshgrid(np.arange(n - 1), np.arange(seg), indexing='ij')
    q0 = (i * m + k).ravel()
    q1, q2, q3 = q0 + 1, q0 + m + 1, q0 + m
    F = np.concatenate((np.column_stack((q0, q1, q2)), np.column_stack((q0, q2, q3))))
    V, UV = V.reshape(-1, 3), UV.reshape(-1, 2)
    for end, on in ((0, cap0), (n - 1, cap1)):
        if on:
            c = len(V)
            V = np.vstack((V, P[end][None, :]))
            UV = np.vstack((UV, [[0.5, ln[end]]]))
            ks = np.arange(seg)
            F = np.vstack((F, np.column_stack((np.full(seg, c), end * m + ks, end * m + ks + 1))))
    return V, F, UV


def blades(P, D, Nn, L, W, bend=0.0):
    """Flat tapering blades (needles, leaves, grass): base points P, directions D, face normals Nn, lengths L, widths
    W. bend: how far the tip curls back along -Nn, as a share of the length. (V, F), five vertices a blade."""
    P = np.asarray(P, np.float64).reshape(-1, 3)
    n = len(P)
    if n == 0:
        return np.zeros((0, 3)), np.zeros((0, 3), np.int64)
    D, Nn = unit(D), unit(Nn)
    L = np.broadcast_to(np.asarray(L, np.float64), (n,))[:, None]
    W = np.broadcast_to(np.asarray(W, np.float64), (n,))[:, None]
    bend = np.broadcast_to(np.asarray(bend, np.float64), (n,))[:, None]
    S = unit(np.cross(D, Nn))
    mid = P + D * L * 0.5 - Nn * L * bend * 0.25
    tip = P + D * L - Nn * L * bend
    V = np.stack((P - S * W * 0.35, P + S * W * 0.35, mid - S * W * 0.5, mid + S * W * 0.5, tip), axis=1).reshape(-1, 3)
    b = np.arange(n)[:, None] * 5
    F = np.concatenate((b + (0, 1, 3), b + (0, 3, 2), b + (2, 3, 4)))
    return V, F


def rock(rnd, size, n=16, cuts=3, rough=0.08, nz=None, smooth=2, crag=0.0, detail=0.35):
    """A rock: the convex hull of a few random points (so it has planes and corners, not a potato's roundness),
    subdivided, its edges eased, then roughened by noise. size = (x, y, z) extents, centred on the origin: (V, F)."""
    sx, sy, sz = size
    bm = bmesh.new()
    for _ in range(n):
        d = rnd.normal(size=3)
        d /= np.linalg.norm(d)
        r = rnd.uniform(0.72, 1.0)
        bm.verts.new((d[0] * sx * 0.5 * r, d[1] * sy * 0.5 * r, d[2] * sz * 0.5 * r))
    res = bmesh.ops.convex_hull(bm, input=bm.verts[:])
    junk = [e for e in res.get('geom_interior', []) + res.get('geom_unused', []) if isinstance(e, BMVert)]
    if junk:
        bmesh.ops.delete(bm, geom=list(set(junk)), context='VERTS')
    for _ in range(cuts):
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    for _ in range(smooth):
        bmesh.ops.smooth_vert(bm, verts=bm.verts[:], factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.normal_update()
    bm.verts.ensure_lookup_table()
    V = np.array([v.co[:] for v in bm.verts], np.float64)
    Nr = np.array([v.normal[:] for v in bm.verts], np.float64)
    F = np.array([[v.index for v in f.verts] for f in bm.faces], np.int64)
    bm.free()
    if nz is not None and rough:
        s = max(sx, sy, sz)
        d = (nz(V, 2.2 / s, 4) - 0.5) * 2.0 * rough * s
        d += (nz(V + 9.1, 9.0 / s, 3) - 0.5) * 2.0 * rough * s * detail
        if crag:        # ledges: the surface stepped along a tilted axis
            ax = unit(np.array((0.25, 0.15, 1.0)))
            h = V @ ax / s
            d += (np.abs(((h * 5.0 + nz(V, 3.0 / s, 2) * 1.5) % 1.0) - 0.5) - 0.25) * crag * s
        V = V + Nr * d[:, None]
    return V, F


def block(centre, size, bev=0.012, grid=0.03, nz=None, rough=0.006, inward=None):
    """A dressed stone: a box with eased edges, its faces gridded and roughened. inward: an axis ('-y') on whose
    face the roughness only cuts in, so that face stays inside its plane (a wall's flush face). (V, F), unwelded
    face by face: weld it (Acc.obj weld=)."""
    h = np.asarray(size, np.float64) * 0.5
    b = min(bev, float(h.min()) * 0.6)
    Vs, Fs, n0 = [], [], 0
    lines = []
    for ax in range(3):
        k = max(2, int(round(2 * h[ax] / grid)))
        t = np.linspace(-h[ax], h[ax], k + 1)
        t = np.unique(np.concatenate((t, [-h[ax] + b * 0.5, -h[ax] + b, h[ax] - b, h[ax] - b * 0.5])))
        lines.append(t)
    for ax in range(3):
        u_ax, v_ax = [a for a in range(3) if a != ax]
        U, Vv = np.meshgrid(lines[u_ax], lines[v_ax], indexing='ij')
        for sgn in (-1.0, 1.0):
            Pp = np.zeros(U.shape + (3,))
            Pp[..., u_ax], Pp[..., v_ax], Pp[..., ax] = U, Vv, sgn * h[ax]
            Pp = Pp.reshape(-1, 3)
            Q = np.clip(Pp, -(h - b), h - b)
            Nr = unit(Pp - Q)
            Pr = Q + Nr * b
            if nz is not None and rough:
                W = Pr + np.asarray(centre)
                d = (nz(W, 14.0, 3) - 0.5) * 2.0 * rough + (nz(W + 5.0, 45.0, 2) - 0.5) * rough
                if inward:
                    ia = 'xyz'.index(inward[1])
                    sg = -1.0 if inward[0] == '-' else 1.0
                    on = Nr[:, ia] * sg > 0.5
                    d = np.where(on, -np.abs(d) * 1.6, d)
                Pr = Pr + Nr * d[:, None]
            nu, nv = U.shape
            i, k = np.meshgrid(np.arange(nu - 1), np.arange(nv - 1), indexing='ij')
            q0 = (i * nv + k).ravel() + n0
            q1, q2, q3 = q0 + nv, q0 + nv + 1, q0 + 1
            Vs.append(Pr + np.asarray(centre))
            Fs.append(np.concatenate((np.column_stack((q0, q1, q2)), np.column_stack((q0, q2, q3)))))
            n0 += len(Pr)
    return np.concatenate(Vs), np.concatenate(Fs)


def disc(r, n=40, z=0.002, nz=None, wobble=0.25, centre=(0.0, 0.0), sy=1.0, scale=4.0):
    """A flat ragged disc lying on the ground (a pool, a scorch): (V, F)."""
    a = np.linspace(0.0, 2.0 * math.pi, n, endpoint=False)
    rr = np.full(n, float(r))
    P = np.column_stack((np.cos(a), np.sin(a), np.zeros(n)))
    if nz is not None:
        rr = rr * (1.0 + (nz(P * 1.0 + (centre[0], centre[1], 0.0), scale, 3) - 0.5) * 2.0 * wobble)
    V = np.column_stack((centre[0] + np.cos(a) * rr, centre[1] + np.sin(a) * rr * sy, np.full(n, z)))
    V = np.vstack((V, [[centre[0], centre[1], z]]))
    k = np.arange(n)
    F = np.column_stack((np.full(n, n), k, (k + 1) % n))
    return V, F


# ================================================================ materials
def _up(g):
    """World-space up-ness of the surface (1 facing the sky)."""
    sep = g.N.new('ShaderNodeSeparateXYZ')
    g.L.new(g.geo.outputs['Normal'], sep.inputs[0])
    return sep.outputs['Z']


def _warped_voronoi(g, scale, warp=0.25, w=0.0):
    vo = g.N.new('ShaderNodeTexVoronoi')
    vo.feature = 'DISTANCE_TO_EDGE'
    vo.inputs['Scale'].default_value = scale
    vm = g.N.new('ShaderNodeVectorMath')
    vm.operation = 'MULTIPLY_ADD'
    wn = g.N.new('ShaderNodeTexNoise')
    wn.inputs['Scale'].default_value = scale * 0.8
    g.L.new(g.obj, wn.inputs['Vector'])
    vm.inputs[1].default_value = (warp, warp, warp)
    off = g.N.new('ShaderNodeVectorMath')
    off.operation = 'ADD'
    g.L.new(g.obj, off.inputs[0])
    off.inputs[1].default_value = (g.seed * 1.37 + w, g.seed * 0.71, w)
    g.L.new(wn.outputs['Color'], vm.inputs[0])
    g.L.new(off.outputs[0], vm.inputs[2])
    g.L.new(vm.outputs[0], vo.inputs['Vector'])
    return vo.outputs['Distance']


def _key(kind, name):
    k = ((kind, name), MODE['revenant'])
    return _CACHE.get(k), k


def stone(name, color='#67645d', color2=None, moss=0.0, lichen=0.4, cracks=0.6, mud=1.0, seed=31, scale=1.0,
          island=0.0, veins=None, relief=1.0, soot=0.0, mud_h=0.14):
    """Weathered rough stone: mottled, pitted, cracked; grime in the recesses, lichen in pale scabs, moss on what
    faces the sky, mud climbing from the ground. island: how much each separate stone of a mesh differs in tone (a
    wall's blocks). veins = dict(glow=, scale=, width=, z0=, z1=, color=): the Blight's light in wandering veins, brightest
    between heights z0..z1 (world). scale: the texture's scale (1 = a boulder a tile across)."""
    hit, key = _key('t_stone', name)
    if hit:
        return hit
    g = _G(name, seed, ao_dist=0.05)
    nt = g.nt
    big = g.noise(2.6 * scale, detail=5.0, rough=0.6, w=1.0)
    mid = g.noise(11.0 * scale, detail=6.0, rough=0.65, w=2.0)
    fine = g.noise(55.0 * scale, detail=5.0, rough=0.7, w=3.0)
    speck = g.noise(240.0 * scale, detail=2.0, w=4.0)
    c1 = g.col(color, 'stone')
    c2 = g.col(color2, 'stone') if color2 else tuple(c * 0.55 for c in c1)
    col = _mix(nt, 'MIX', c1, c2, _maprange(nt, big, 0.32, 0.7))
    col = _mix(nt, 'MULTIPLY', col, _maprange(nt, mid, 0.25, 0.75, 0.68, 1.22))
    col = _mix(nt, 'MULTIPLY', col, _maprange(nt, speck, 0.3, 0.7, 0.82, 1.12))
    if island:
        col = _mix(nt, 'MULTIPLY', col, _maprange(nt, g.geo.outputs['Random Per Island'], 0.0, 1.0, 1.0 - island,
                                                  1.0 + island * 0.55))
    # edges worn paler, recesses packed dark
    col = _mix(nt, 'MIX', col, tuple(min(1.0, c * 1.9 + 0.01) for c in c1), _math(nt, 'MULTIPLY', g.edge, 0.35))
    crack = None
    if cracks > 0:
        cn = g.noise(1.7 * scale, detail=4.0, rough=0.62, distort=0.7, w=6.0)       # long wandering fissures
        d = _math(nt, 'ABSOLUTE', _math(nt, 'SUBTRACT', cn, 0.5))
        region = _maprange(nt, g.noise(1.3 * scale, w=7.0), 0.5 - 0.14 * cracks, 0.62 - 0.14 * cracks)
        crack = _math(nt, 'MULTIPLY', _maprange(nt, d, 0.0, 0.006, 1.0, 0.0), region)
        col = _mix(nt, 'MIX', col, g.col('#14120f', 'stone'), _math(nt, 'MULTIPLY', crack, 0.9))
    col = _mix(nt, 'MIX', col, g.col(COL['grime'], 'earth'), _math(nt, 'MULTIPLY', g.cavity, 0.75))
    if soot > 0:
        col = _mix(nt, 'MIX', col, g.col('#17151a', 'stone'), _maprange(nt, g.noise(3.0 * scale, w=8.0), 0.35, 0.7, 0.0, soot))
    up = _up(g)
    lm = None
    if lichen > 0:
        blot = _maprange(nt, g.noise(7.0 * scale, detail=8.0, rough=0.75, w=11.0), 0.64 - 0.1 * lichen, 0.67 - 0.1 * lichen)
        lm = _math(nt, 'MULTIPLY', blot, _maprange(nt, fine, 0.3, 0.55))
        lc = _mix(nt, 'MIX', g.col('#8f927c', 'stone'), g.col('#93864f', 'stone'), _maprange(nt, g.noise(3.0 * scale, w=12.0), 0.4, 0.6))
        col = _mix(nt, 'MIX', col, lc, _math(nt, 'MULTIPLY', lm, 0.8))
    mm = None
    if moss > 0:
        drive = _math(nt, 'ADD', _math(nt, 'ADD', up, _math(nt, 'MULTIPLY', _math(nt, 'SUBTRACT', g.noise(5.0 * scale, detail=6.0, w=14.0), 0.5), 1.3)),
                      _math(nt, 'MULTIPLY', g.cavity, 0.5))
        t = 1.25 - 0.85 * moss
        mm = _maprange(nt, drive, t, t + 0.18)
        mc = _mix(nt, 'MIX', g.col('#252c14', 'cloth'), g.col('#4b5326', 'cloth'), _maprange(nt, fine, 0.3, 0.7))
        col = _mix(nt, 'MIX', col, mc, mm)
    rgh = 0.9
    if mud > 0:
        mdm = g.mud(height=mud_h, amount=mud)
        col = _mix(nt, 'MIX', col, g.col(COL['mud'], 'earth'), mdm)
    if veins:
        vscale = veins.get('scale', 5.0) * scale
        width = veins.get('width', 0.03)
        n1 = g.noise(vscale, detail=3.0, rough=0.55, distort=0.4, vec=g.stretched(1.0, 1.0, 0.4), w=93.0)
        d1 = _math(nt, 'ABSOLUTE', _math(nt, 'SUBTRACT', n1, 0.5))
        n2 = g.noise(vscale * 2.3, detail=3.0, rough=0.55, distort=0.4, vec=g.stretched(1.0, 1.0, 0.5), w=95.0)
        d2 = _math(nt, 'ABSOLUTE', _math(nt, 'SUBTRACT', n2, 0.5))
        zone = _maprange(nt, _math(nt, 'ADD', g.wz, _math(nt, 'MULTIPLY', _math(nt, 'SUBTRACT', g.noise(4.0 * scale, w=96.0), 0.5), 0.5)),
                         veins.get('z0', 0.0), veins.get('z1', 0.6), 1.0, veins.get('fade', 0.25))
        patch = _maprange(nt, g.noise(1.4 * scale, detail=2.0, w=97.0), 0.5 - 0.12 * veins.get('spread', 0.5),
                          0.58 - 0.12 * veins.get('spread', 0.5))                     # veined in places, not all over
        fine_on = _math(nt, 'MULTIPLY', zone, patch)
        core = _math(nt, 'MAXIMUM', _math(nt, 'MULTIPLY', _maprange(nt, d1, 0.0, width * 0.4, 1.0, 0.0), patch),
                     _math(nt, 'MULTIPLY', _maprange(nt, d2, 0.0, width * 0.3, 1.0, 0.0), fine_on))
        halo = _math(nt, 'MAXIMUM', _math(nt, 'MULTIPLY', _maprange(nt, d1, 0.0, width * 1.6, 1.0, 0.0), patch),
                     _math(nt, 'MULTIPLY', _maprange(nt, d2, 0.0, width * 1.2, 1.0, 0.0), fine_on))
        col = _mix(nt, 'MIX', col, g.col('#2a1236', 'stone'), _math(nt, 'MULTIPLY', halo, 0.85))
        glow = veins.get('glow', 4.0)
        em = _math(nt, 'MULTIPLY', _math(nt, 'ADD', _math(nt, 'MULTIPLY', core, glow), _math(nt, 'MULTIPLY', halo, glow * 0.12)), zone)
        g.bsdf.inputs['Emission Color'].default_value = (*hexlin(veins.get('color', BLIGHT)), 1.0)
        g.L.new(em, g.bsdf.inputs['Emission Strength'])
        g.bump(halo, -3.0)
    g.bump(big, 6.0 * relief)
    g.bump(mid, 5.0 * relief)
    g.bump(fine, 2.5 * relief)
    g.bump(speck, 0.6)
    if crack is not None:
        g.bump(crack, -6.0)
    if lm is not None:
        g.bump(lm, 1.2)
    if mm is not None:
        g.bump(_math(nt, 'MULTIPLY', mm, g.noise(90.0 * scale, detail=3.0, w=15.0)), 4.0)
        rgh = _lerp(nt, rgh, 1.0, mm)
    g.bsdf.inputs['Specular IOR Level'].default_value = 0.3
    m = g.finish(col, rgh, 0.0)
    _CACHE[key] = m
    return m


def bark(name, color='#3a3129', seed=33, moss=0.25, ridges=10.0, grain=2.5, lichen=0.3, mud=1.0, pale=None):
    """Bark on a tube() (its UVs: u round, v along): deep furrows running along the limb, flaked and lichened, moss on
    the upper side. pale: a dead tree's barkless grey wood showing through in long patches (hex)."""
    hit, key = _key('t_bark', name)
    if hit:
        return hit
    g = _G(name, seed, ao_dist=0.03)
    nt = g.nt
    mp = g.N.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (ridges, grain, 1.0)
    g.L.new(g.tco.outputs['UV'], mp.inputs['Vector'])
    n = g.noise(1.0, detail=4.0, rough=0.6, distort=0.3, vec=mp.outputs['Vector'], w=1.0)
    furrow = _maprange(nt, _math(nt, 'ABSOLUTE', _math(nt, 'SUBTRACT', n, 0.5)), 0.0, 0.09, 1.0, 0.0)
    plate = g.noise(1.0, detail=2.0, vec=mp.outputs['Vector'], w=5.0)
    patch = g.noise(6.0, detail=5.0, w=2.0)
    fine = g.noise(60.0, detail=4.0, w=3.0)
    c1 = g.col(color, 'wood')
    col = _mix(nt, 'MULTIPLY', c1, _maprange(nt, plate, 0.25, 0.75, 0.6, 1.3))
    col = _mix(nt, 'MULTIPLY', col, _maprange(nt, patch, 0.3, 0.7, 0.75, 1.15))
    if pale:
        bare = _maprange(nt, g.noise(1.0, detail=3.0, vec=g.stretched(3.0, 3.0, 0.6), w=6.0), 0.5, 0.56)
        pc = _mix(nt, 'MULTIPLY', g.col(pale, 'wood'), _maprange(nt, fine, 0.3, 0.7, 0.8, 1.15))
        col = _mix(nt, 'MIX', col, pc, bare)
        furrow = _math(nt, 'MULTIPLY', furrow, _math(nt, 'SUBTRACT', 1.0, _math(nt, 'MULTIPLY', bare, 0.7)))
    col = _mix(nt, 'MIX', col, g.col('#0f0c09', 'wood'), _math(nt, 'MULTIPLY', furrow, 0.85))
    col = _mix(nt, 'MIX', col, g.col(COL['grime'], 'earth'), _math(nt, 'MULTIPLY', g.cavity, 0.6))
    if lichen > 0:
        lm = _math(nt, 'MULTIPLY', _maprange(nt, g.noise(9.0, detail=8.0, rough=0.75, w=11.0), 0.66 - 0.1 * lichen, 0.69 - 0.1 * lichen),
                   _maprange(nt, fine, 0.3, 0.55))
        col = _mix(nt, 'MIX', col, g.col('#7e8270', 'stone'), _math(nt, 'MULTIPLY', lm, 0.75))
    mm = None
    if moss > 0:
        drive = _math(nt, 'ADD', _up(g), _math(nt, 'MULTIPLY', _math(nt, 'SUBTRACT', g.noise(7.0, detail=6.0, w=14.0), 0.5), 1.4))
        t = 1.2 - 0.8 * moss
        mm = _maprange(nt, drive, t, t + 0.2)
        col = _mix(nt, 'MIX', col, _mix(nt, 'MIX', g.col('#232a13', 'cloth'), g.col('#454d24', 'cloth'), _maprange(nt, fine, 0.3, 0.7)), mm)
    if mud > 0:
        col = _mix(nt, 'MIX', col, g.col(COL['mud'], 'earth'), g.mud(height=0.1, amount=mud))
    g.bump(furrow, -7.0)
    g.bump(plate, 4.0)
    g.bump(fine, 1.5)
    if mm is not None:
        g.bump(_math(nt, 'MULTIPLY', mm, g.noise(110.0, detail=3.0, w=15.0)), 3.0)
    g.bsdf.inputs['Specular IOR Level'].default_value = 0.25
    m = g.finish(col, 0.88, 0.0)
    _CACHE[key] = m
    return m


def foliage(name, color='#1d2a1d', tip='#34432a', seed=35, rough=0.6, dead=None, dead_share=0.0, thin=0.0):
    """Needles and leaves (blades()): each blade its own shade between `color` and `tip`, a share of them dead
    (`dead`, hex), darker where the mass is thick. thin: light let through the blade (0..1)."""
    hit, key = _key('t_foliage', name)
    if hit:
        return hit
    g = _G(name, seed, ao_dist=0.05)
    nt = g.nt
    isl = g.geo.outputs['Random Per Island']
    patch = g.noise(4.0, detail=4.0, w=1.0)
    t = _maprange(nt, _math(nt, 'ADD', _math(nt, 'MULTIPLY', isl, 0.7), _math(nt, 'MULTIPLY', patch, 0.6)), 0.35, 0.95)
    col = _mix(nt, 'MIX', g.col(color, 'cloth'), g.col(tip, 'cloth'), t)
    if dead and dead_share > 0:
        frac = g.N.new('ShaderNodeMath')
        frac.operation = 'FRACT'
        g.L.new(_math(nt, 'MULTIPLY', isl, 37.0), frac.inputs[0])
        dm = _maprange(nt, _math(nt, 'ADD', frac.outputs[0], _math(nt, 'MULTIPLY', _math(nt, 'SUBTRACT', g.noise(3.0, w=3.0), 0.5), 0.6)),
                       1.0 - dead_share - 0.02, 1.0 - dead_share + 0.02)
        col = _mix(nt, 'MIX', col, g.col(dead, 'cloth'), dm)
    col = _mix(nt, 'MULTIPLY', col, _maprange(nt, g.cavity, 0.0, 1.0, 1.0, 0.45))
    b = g.bsdf
    b.inputs['Specular IOR Level'].default_value = 0.35
    if thin > 0:
        try:
            b.inputs['Subsurface Weight'].default_value = thin
            b.inputs['Subsurface Radius'].default_value = (0.5, 0.8, 0.3)
            b.inputs['Subsurface Scale'].default_value = 0.01
        except KeyError:
            pass
    m = g.finish(col, rough, 0.0)
    _CACHE[key] = m
    return m


def bone(name='bone', color='#bdb39a', seed=37, mud=1.0, stain=0.6):
    """Old bone: yellowed, stained, pitted, dirt in every hollow."""
    hit, key = _key('t_bone', name)
    if hit:
        return hit
    g = _G(name, seed, ao_dist=0.02)
    nt = g.nt
    col = _mix(nt, 'MULTIPLY', g.col(color, 'bone'), _maprange(nt, g.noise(9.0, detail=6.0, w=1.0), 0.3, 0.7, 0.72, 1.1))
    col = _mix(nt, 'MIX', col, g.col('#6b5a3c', 'bone'), _maprange(nt, g.noise(4.0, detail=8.0, rough=0.7, w=2.0), 0.45, 0.75, 0.0, stain))
    col = _mix(nt, 'MIX', col, g.col(COL['grime'], 'earth'), _math(nt, 'MULTIPLY', g.cavity, 0.85))
    if mud > 0:
        col = _mix(nt, 'MIX', col, g.col(COL['mud'], 'earth'), g.mud(height=0.05, amount=mud))
    g.bump(g.noise(120.0, detail=3.0, w=3.0), 0.8)
    g.bump(g.noise(20.0, detail=3.0, w=4.0), 0.8)
    g.bsdf.inputs['Specular IOR Level'].default_value = 0.35
    m = g.finish(col, 0.6, 0.0)
    _CACHE[key] = m
    return m


def flesh(name, source, reach=0.4, glow=4.0, color='#4a3540', seed=39, light=BLIGHT, scale=1.0):
    """Blight-flesh (the nest): wet, bruised, ridged; veins of the Blight's light, brightest toward `source` (object
    space) and dying out `reach` from it."""
    hit, key = _key('t_flesh', name)
    if hit:
        return hit
    g = _G(name, seed, ao_dist=0.04)
    nt = g.nt
    dist = g.N.new('ShaderNodeVectorMath')
    dist.operation = 'DISTANCE'
    g.L.new(g.obj, dist.inputs[0])
    dist.inputs[1].default_value = tuple(source)
    wob = _math(nt, 'MULTIPLY', _math(nt, 'SUBTRACT', g.noise(7.0 * scale, w=91.0), 0.5), reach * 0.5)
    near = _maprange(nt, _math(nt, 'ADD', dist.outputs['Value'], wob), reach * 0.15, reach, 1.0, 0.0)
    mott = g.noise(6.0 * scale, detail=6.0, rough=0.65, w=1.0)
    col = _mix(nt, 'MIX', g.col(color, 'skin'), g.col('#2a1d26', 'skin'), _maprange(nt, mott, 0.3, 0.7))
    col = _mix(nt, 'MIX', col, g.col('#6b4a52', 'skin'), _maprange(nt, g.noise(14.0 * scale, detail=6.0, w=2.0), 0.55, 0.75, 0.0, 0.7))
    col = _mix(nt, 'MIX', col, g.col('#4a3358', 'skin'), _math(nt, 'MULTIPLY', near, 0.45))

    def net(sc, width, w):
        n = g.noise(sc * scale, detail=3.0, rough=0.55, distort=0.45, vec=g.stretched(1.0, 1.0, 0.45), w=w)
        d = _math(nt, 'ABSOLUTE', _math(nt, 'SUBTRACT', n, 0.5))
        return _maprange(nt, d, 0.0, width, 1.0, 0.0), _maprange(nt, d, 0.0, width * 0.4, 1.0, 0.0)
    big, big_c = net(3.2, 0.026, 93.0)
    fin, fin_c = net(9.0, 0.02, 95.0)
    fin_c = _math(nt, 'MULTIPLY', fin_c, near)
    veins = _math(nt, 'MAXIMUM', big, _math(nt, 'MULTIPLY', fin, near))
    col = _mix(nt, 'MIX', col, _mix(nt, 'MIX', g.col('#1d1420', 'skin'), g.col('#3a1650', 'skin'), near), _math(nt, 'MULTIPLY', veins, 0.85))
    col = _mix(nt, 'MIX', col, g.col('#120c0e', 'skin'), _math(nt, 'MULTIPLY', g.cavity, 0.7))
    col = _mix(nt, 'MIX', col, g.col(COL['mud'], 'earth'), g.mud(height=0.06, amount=0.8))
    core = _math(nt, 'MAXIMUM', big_c, fin_c)
    lit = _math(nt, 'MULTIPLY', near, near)
    em = _math(nt, 'ADD', _math(nt, 'MULTIPLY', _math(nt, 'MULTIPLY', core, lit), glow),
               _math(nt, 'MULTIPLY', _math(nt, 'MULTIPLY', lit, near), glow * 0.015))
    b = g.bsdf
    b.inputs['Emission Color'].default_value = (*hexlin(light), 1.0)
    g.L.new(em, b.inputs['Emission Strength'])
    b.inputs['Specular IOR Level'].default_value = 0.6
    b.inputs['Coat Weight'].default_value = 0.12
    b.inputs['Coat Roughness'].default_value = 0.25
    g.bump(veins, 5.0)
    g.bump(mott, 4.0)
    g.bump(g.noise(40.0 * scale, detail=4.0, w=97.0), 2.0)
    g.bump(g.noise(160.0 * scale, detail=3.0, w=98.0), 0.5)
    m = g.finish(col, _maprange(nt, g.noise(10.0 * scale, w=99.0), 0.3, 0.7, 0.3, 0.6), 0.0)
    _CACHE[key] = m
    return m


def gore(name='blood_pool', color='#3a0806', seed=41):
    """A pool of blood on the ground: near-black oxblood, wet in the middle, drying matte toward its edge."""
    hit, key = _key('t_gore', name)
    if hit:
        return hit
    g = _G(name, seed)
    nt = g.nt
    n = g.noise(9.0, detail=6.0, w=1.0)
    col = _mix(nt, 'MIX', g.col(color, 'cloth'), g.col('#140403', 'cloth'), _maprange(nt, n, 0.3, 0.7))
    g.bsdf.inputs['Specular IOR Level'].default_value = 0.25
    m = g.finish(col, _maprange(nt, n, 0.35, 0.65, 0.3, 0.6), 0.0)
    _CACHE[key] = m
    return m


def earth(name='earth', color='#2f271c', seed=43, moss=0.0):
    """Packed dirt and mortar-dust (a wall's core, the foot of a stump)."""
    hit, key = _key('t_earth', name)
    if hit:
        return hit
    g = _G(name, seed, ao_dist=0.04)
    nt = g.nt
    a = g.noise(9.0, detail=7.0, rough=0.7, w=1.0)
    bfine = g.noise(70.0, detail=4.0, w=2.0)
    col = _mix(nt, 'MULTIPLY', g.col(color, 'earth'), _maprange(nt, a, 0.25, 0.75, 0.6, 1.3))
    col = _mix(nt, 'MIX', col, g.col('#6b6558', 'stone'), _maprange(nt, bfine, 0.62, 0.72, 0.0, 0.6))     # grit and chips
    col = _mix(nt, 'MIX', col, g.col('#0f0d0a', 'earth'), _math(nt, 'MULTIPLY', g.cavity, 0.7))
    if moss > 0:
        drive = _math(nt, 'ADD', _up(g), _math(nt, 'MULTIPLY', _math(nt, 'SUBTRACT', g.noise(5.0, detail=6.0, w=14.0), 0.5), 1.4))
        t = 1.3 - 0.9 * moss
        mm = _maprange(nt, drive, t, t + 0.2)
        col = _mix(nt, 'MIX', col, _mix(nt, 'MIX', g.col('#252c14', 'cloth'), g.col('#4b5326', 'cloth'), _maprange(nt, bfine, 0.3, 0.7)), mm)
    g.bump(a, 6.0)
    g.bump(bfine, 3.0)
    g.bsdf.inputs['Specular IOR Level'].default_value = 0.2
    m = g.finish(col, 0.97, 0.0)
    _CACHE[key] = m
    return m


def timber(name, color='#4a3a2a', seed=45, axis='x', mud=1.0, mud_h=0.16, wear=0.5, moss=0.0, blood=0.0):
    """Worked wood left out in the weather: grain running along `axis` (object space), split and silvered, grime
    in the joints, mud climbing from the ground, moss on what faces up."""
    hit, key = _key('t_timber', name)
    if hit:
        return hit
    g = _G(name, seed, ao_dist=0.03)
    nt = g.nt
    st = {'x': (0.06, 1.0, 1.0), 'y': (1.0, 0.06, 1.0), 'z': (1.0, 1.0, 0.06)}[axis]
    grain = g.noise(38.0, detail=6.0, vec=g.stretched(*st), w=1.0)
    split = _maprange(nt, _math(nt, 'ABSOLUTE', _math(nt, 'SUBTRACT', g.noise(14.0, detail=2.0, vec=g.stretched(*st), w=2.0), 0.5)),
                      0.0, 0.012, 1.0, 0.0)
    col = _mix(nt, 'MULTIPLY', g.col(color, 'wood'), _maprange(nt, grain, 0.3, 0.7, 0.6, 1.25))
    grey = _maprange(nt, g.noise(3.0, detail=6.0, w=3.0), 0.4, 0.7, 0.0, wear)
    col = _mix(nt, 'MIX', col, _mix(nt, 'MULTIPLY', g.col('#6f6a60', 'wood'), _maprange(nt, grain, 0.3, 0.7, 0.7, 1.15)), grey)
    col = _mix(nt, 'MIX', col, tuple(min(1.0, c * 2.2) for c in g.col(color, 'wood')), _math(nt, 'MULTIPLY', g.edge, 0.3))
    col = _mix(nt, 'MIX', col, g.col('#0f0c09', 'wood'), _math(nt, 'MULTIPLY', split, 0.8))
    col = _mix(nt, 'MIX', col, g.col(COL['grime'], 'earth'), _math(nt, 'MULTIPLY', g.cavity, 0.75))
    bm = g.blood(blood)
    if bm is not None:
        col = _mix(nt, 'MIX', col, g.col(COL['oxblood_dry'], 'cloth'), bm)
    if moss > 0:
        drive = _math(nt, 'ADD', _up(g), _math(nt, 'MULTIPLY', _math(nt, 'SUBTRACT', g.noise(7.0, detail=6.0, w=14.0), 0.5), 1.4))
        t = 1.25 - 0.85 * moss
        col = _mix(nt, 'MIX', col, _mix(nt, 'MIX', g.col('#232a13', 'cloth'), g.col('#454d24', 'cloth'), _maprange(nt, g.noise(60.0, w=15.0), 0.3, 0.7)),
                   _maprange(nt, drive, t, t + 0.2))
    if mud > 0:
        col = _mix(nt, 'MIX', col, g.col(COL['mud'], 'earth'), g.mud(height=mud_h, amount=mud))
    g.bump(grain, 1.5)
    g.bump(split, -3.0)
    g.bsdf.inputs['Specular IOR Level'].default_value = 0.3
    m = g.finish(col, 0.82, 0.0)
    _CACHE[key] = m
    return m


def ellipsoid(c, r, seg=20, rings=12, nz=None, rough=0.0, scale=8.0):
    """An ellipsoid (centre c, radii r), optionally lumpy: (V, F)."""
    th = np.linspace(0.0, 2.0 * math.pi, seg + 1)
    ph = np.linspace(0.0, math.pi, rings + 1)
    TH, PH = np.meshgrid(th, ph, indexing='ij')
    D = np.stack((np.cos(TH) * np.sin(PH), np.sin(TH) * np.sin(PH), np.cos(PH)), axis=-1).reshape(-1, 3)
    k = np.ones(len(D))
    if nz is not None and rough:
        k = 1.0 + (nz(D * np.asarray(r) + np.asarray(c), scale, 3) - 0.5) * 2.0 * rough
    V = D * np.asarray(r) * k[:, None] + np.asarray(c)
    m = rings + 1
    i, j = np.meshgrid(np.arange(seg), np.arange(rings), indexing='ij')
    q0 = (i * m + j).ravel()
    F = np.concatenate((np.column_stack((q0, q0 + m, q0 + m + 1))[j.ravel() > 0],          # no slivers at the poles
                        np.column_stack((q0, q0 + m + 1, q0 + 1))[j.ravel() < rings - 1]))
    pole = F % m
    F = np.where(pole == 0, 0, np.where(pole == rings, rings, F))                           # one vertex a pole
    return V, F


def lathe(profile, seg=32, nz=None, rough=0.0, scale=10.0, cap0=True, cap1=True):
    """A surface of revolution about z from a profile [(r, z), ...] bottom to top: (V, F, UV)."""
    pr = np.asarray(profile, np.float64)
    a = np.linspace(0.0, 2.0 * math.pi, seg + 1)
    R = pr[:, 0][:, None] * np.ones(seg + 1)[None, :]
    V = np.stack((R * np.cos(a)[None, :], R * np.sin(a)[None, :], pr[:, 1][:, None] * np.ones(seg + 1)[None, :]), axis=-1).reshape(-1, 3)
    if nz is not None and rough:
        d = (nz(V, scale, 3) - 0.5) * 2.0 * rough
        V = V + unit(V * (1.0, 1.0, 0.0) + 1e-9) * d[:, None]
        Vg = V.reshape(len(pr), seg + 1, 3)
        Vg[:, -1] = Vg[:, 0]
        V = Vg.reshape(-1, 3)
    UV = np.stack(np.broadcast_arrays((a / (2.0 * math.pi))[None, :], pr[:, 1][:, None]), axis=-1).reshape(-1, 2)
    n, m = len(pr), seg + 1
    i, k = np.meshgrid(np.arange(n - 1), np.arange(seg), indexing='ij')
    q0 = (i * m + k).ravel()
    F = np.concatenate((np.column_stack((q0, q0 + 1, q0 + m + 1)), np.column_stack((q0, q0 + m + 1, q0 + m))))
    for end, on in ((0, cap0), (n - 1, cap1)):
        if on:
            c = len(V)
            V = np.vstack((V, [[0.0, 0.0, pr[end, 1]]]))
            UV = np.vstack((UV, [[0.5, pr[end, 1]]]))
            ks = np.arange(seg)
            F = np.vstack((F, np.column_stack((np.full(seg, c), end * m + ks, end * m + ks + 1))))
    return V, F, UV


# ================================================================ staging helpers
def no_ground_shadow():
    """Drop the stage's shadow catcher (a wall block fills its tile: a shadow thrown past it would fall on its
    neighbours' sprites)."""
    ob = bpy.data.objects.get('shadow_catcher')
    if ob:
        ob.hide_render = True


def root(name='prop'):
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    return e


def parent(parts, par):
    for p in parts:
        if p is not None and p.parent is None:
            p.parent = par
    return par


# ================================================================ plants
def conifer(wood, needles, rnd, nz, base=(0.0, 0.0), H=1.2, R=0.36, lean=(0.0, 0.0), bare=0.16, gap=0.12,
            trunk_r=0.05, dead_low=0.25, density=2.4):
    """A ragged northern conifer: a straight tapering trunk, whorls of drooping boughs shortening to the leader, each
    bough feathered with sprigs of needles. Boughs go missing and come up short (gap), the lowest hang bare
    (dead_low: the height share below which boughs carry few needles). Adds to the Accs `wood` and `needles`."""
    bx, by = base
    n = 16
    t = np.linspace(0.0, 1.0, n)
    wob = nz.vec(np.column_stack((t * 3.0, np.full(n, bx * 7.0 + 1.0), np.full(n, by * 5.0))), 1.0, 2) * 0.05 * t[:, None]
    TP = np.column_stack((bx + lean[0] * t + wob[:, 0], by + lean[1] * t + wob[:, 1], H * t))
    TR = trunk_r * (1.0 - t) ** 1.15 + 0.004 + trunk_r * 0.7 * np.clip(1.0 - t / 0.07, 0.0, 1.0) ** 2
    wood.add(*tube(TP, TR, seg=10, nz=nz, rough=0.18, rough_scale=30.0))

    def trunk_at(z):
        f = np.clip(z / H, 0.0, 1.0) * (n - 1)
        i = min(int(f), n - 2)
        return TP[i] + (TP[i + 1] - TP[i]) * (f - i), TR[i] + (TR[i + 1] - TR[i]) * (f - i)

    BP, BD, BN, BL, BW = [], [], [], [], []
    up = np.array((0.0, 0.0, 1.0))

    def sprig(p, d, ln, full):
        """Needles feathered along a sprig from p along d."""
        k = max(2, int(ln / 0.011 * density))
        s = (np.arange(k) + rnd.uniform(0.0, 1.0, k)) / k
        side = unit(np.cross(d, up) + 1e-6)
        sg = np.where(np.arange(k) % 2 == 0, 1.0, -1.0)[:, None]
        hang = rnd.uniform(-0.9, 0.15, k)[:, None]
        dd = unit(d[None, :] * rnd.uniform(0.5, 1.0, k)[:, None] + side[None, :] * sg * rnd.uniform(0.4, 1.0, k)[:, None]
                  + up[None, :] * hang)
        keep = rnd.uniform(0.0, 1.0, k) < full
        BP.append((p[None, :] + d[None, :] * (s * ln)[:, None])[keep])
        BD.append(dd[keep])
        BN.append((up[None, :] + rnd.normal(0.0, 0.55, (k, 3)))[keep])
        BL.append(rnd.uniform(0.024, 0.042, k)[keep])
        BW.append(rnd.uniform(0.0045, 0.0075, k)[keep])

    z = bare * H
    while z < H * 0.965:
        fr = z / H
        L0 = R * (1.0 - fr) ** 0.8 + 0.025
        k = int(rnd.integers(4, 7))
        a0 = rnd.uniform(0.0, 2.0 * math.pi)
        o, tr = trunk_at(z)
        full = 1.0 if fr > dead_low else 0.25 + 0.75 * (fr - bare) / max(dead_low - bare, 1e-3)
        for j in range(k):
            if rnd.uniform() < gap:
                continue
            a = a0 + 2.0 * math.pi * j / k + rnd.uniform(-0.4, 0.4)
            L = L0 * rnd.uniform(0.55, 1.1)
            d = np.array((math.cos(a), math.sin(a), 0.0))
            m = 7
            s = np.linspace(0.0, 1.0, m)
            rise = 0.35 * fr ** 2 - 0.05          # the top boughs reach up, the low ones sag
            droop = rnd.uniform(0.3, 0.55) * (1.0 - 0.6 * fr)
            Pb = o[None, :] + d[None, :] * (L * s)[:, None]
            Pb[:, 2] += L * (rise * s - droop * s ** 2 + 0.12 * s ** 3) + rnd.uniform(-0.01, 0.01)
            Pb += nz.vec(Pb, 6.0, 2) * 0.03 * s[:, None]
            wood.add(*tube(Pb, np.linspace(max(0.006, tr * 0.32), 0.002, m), seg=5), mi=0)
            Tb = unit(np.gradient(Pb, axis=0))
            side = unit(np.cross(Tb, up))
            step = 0.034 / max(L, 0.05) / max(density, 0.3) ** 0.5
            for ss in np.arange(0.12, 1.0, step):
                f = ss * (m - 1)
                i = min(int(f), m - 2)
                p = Pb[i] + (Pb[i + 1] - Pb[i]) * (f - i)
                tb, sd = Tb[i], side[i]
                ln = L * 0.42 * (1.0 - 0.8 * ss) + 0.035
                for sgn in (-1.0, 1.0):
                    if rnd.uniform() > full:
                        continue
                    dsp = unit(tb * 0.75 + sd * sgn * rnd.uniform(0.7, 1.1) + up * rnd.uniform(-0.45, -0.05))
                    sprig(p, dsp, ln * rnd.uniform(0.7, 1.15), full)
            sprig(Pb[-1], Tb[-1], 0.06, full)
        z += H * rnd.uniform(0.04, 0.07) * (1.0 - 0.35 * fr)
    # the leader: needles close round the top of the trunk
    for zz in np.linspace(H * 0.9, H * 0.995, 6):
        o, _ = trunk_at(zz)
        a = rnd.uniform(0.0, 2.0 * math.pi)
        for j in range(4):
            d = unit(np.array((math.cos(a + j * 1.6), math.sin(a + j * 1.6), rnd.uniform(0.6, 1.4))))
            sprig(o, d, 0.045, 1.0)
    if BP:
        needles.add(*blades(np.concatenate(BP), np.concatenate(BD), np.concatenate(BN), np.concatenate(BL),
                            np.concatenate(BW), bend=0.25))


def branching(wood, rnd, nz, p0, d0, L, r0, depth, gnarl=0.35, lift=0.12, shrink=0.72, kids=(2, 3), seg=8,
              twigs=None, tips=None, snap=0.0):
    """A limb that wanders and forks, `depth` times: adds its tubes to `wood`; ends are appended to `tips` as
    (point, direction); snap: the chance a limb ends broken short (a dead tree)."""
    up = np.array((0.0, 0.0, 1.0))
    m = max(4, int(L / 0.035))
    P = [np.asarray(p0, np.float64)]
    d = unit(np.asarray(d0, np.float64))
    for i in range(m):
        d = unit(d + rnd.normal(0.0, gnarl, 3) * (0.5 + 0.5 * i / m) + up * lift)
        P.append(P[-1] + d * L / m)
    P = np.array(P)
    broken = depth > 0 and rnd.uniform() < snap
    r1 = r0 * shrink if depth > 0 else 0.0025
    Rr = np.linspace(r0, r1, m + 1)
    wood.add(*tube(P, Rr, seg=max(4, seg), nz=nz, rough=0.22, rough_scale=26.0, cap1=broken or depth == 0))
    if depth == 0 or broken:
        if tips is not None and not broken:
            tips.append((P[-1], d))
        return
    nk = int(rnd.integers(kids[0], kids[1] + 1))
    a0 = rnd.uniform(0.0, 2.0 * math.pi)
    for j in range(nk):
        tpos = 1.0 if j == 0 else rnd.uniform(0.45, 0.95)
        f = tpos * m
        i = min(int(f), m - 1)
        p = P[i] + (P[i + 1] - P[i]) * (f - i)
        tang = unit(P[i + 1] - P[i])
        e1 = unit(np.cross(tang, up + 1e-3))
        e2 = np.cross(tang, e1)
        a = a0 + 2.0 * math.pi * j / nk + rnd.uniform(-0.5, 0.5)
        spread = rnd.uniform(0.45, 0.85) if j else rnd.uniform(0.15, 0.4)
        dk = unit(tang + (e1 * math.cos(a) + e2 * math.sin(a)) * spread)
        rk = (Rr[i] if j else r1) * (shrink if j else 1.0)
        branching(wood, rnd, nz, p, dk, L * rnd.uniform(0.6, 0.82), rk, depth - 1, gnarl, lift, shrink, kids,
                  seg - 1, twigs, tips, snap)


def roots(wood, rnd, nz, base, r, n=5, reach=0.16):
    """Root flare: short limbs running out from the foot of a trunk and into the ground."""
    bx, by = base
    a0 = rnd.uniform(0.0, 2.0 * math.pi)
    for j in range(n):
        a = a0 + 2.0 * math.pi * j / n + rnd.uniform(-0.3, 0.3)
        L = reach * rnd.uniform(0.7, 1.2)
        s = np.linspace(0.0, 1.0, 6)
        P = np.column_stack((bx + np.cos(a) * L * s, by + np.sin(a) * L * s, r * 1.6 * (1.0 - s) ** 2 - 0.012 * s))
        P[:, :2] += nz.vec(P, 9.0, 2)[:, :2] * 0.04 * s[:, None]
        wood.add(*tube(P, np.linspace(r * 0.62, r * 0.12, 6), seg=7, nz=nz, rough=0.2, rough_scale=30.0))


def leaf_cluster(leaves, rnd, at, n=40, spread=(0.1, 0.1, 0.06), size=(0.03, 0.05), width=0.55, droop=0.3):
    """Leaves in a loose clump round a point."""
    P = np.asarray(at)[None, :] + rnd.normal(0.0, 1.0, (n, 3)) * np.asarray(spread) * 0.6
    D = unit(rnd.normal(0.0, 1.0, (n, 3)) + np.array((0.0, 0.0, -droop)))
    Nn = rnd.normal(0.0, 0.6, (n, 3)) + np.array((0.0, 0.0, 1.0))
    L = rnd.uniform(size[0], size[1], n)
    leaves.add(*blades(P, D, Nn, L, L * width, bend=0.2))


def fit(accs, h_max=None, r_max=None, about=(0.0, 0.0)):
    """Scale Accs together (about a ground point) so their geometry stays under a height and inside a radius."""
    P = np.concatenate([a.points() for a in accs if not a.empty()])
    k = 1.0
    if h_max:
        k = min(k, h_max / max(P[:, 2].max(), 1e-6))
    if r_max:
        rr = np.hypot(P[:, 0] - about[0], P[:, 1] - about[1]).max()
        k = min(k, r_max / max(rr, 1e-6))
    if k < 1.0:
        for a in accs:
            a.V = [(v - (about[0], about[1], 0.0)) * k + (about[0], about[1], 0.0) for v in a.V]
    return k
