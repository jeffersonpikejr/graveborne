"""Faces — heads carved from one skull, readable from a battle sprite up to a portrait.

A face is not a set of features stuck on an egg. The head is one signed-distance field built from about a dozen
anatomical masses — cranium, brow ridge, orbital sockets, cheekbones and their arches, a three-part nose (bridge,
wedge tip, alar base), the muzzle and lips, mandible and chin, the neck with its sternomastoids, the ears — all
built about one facial centreline and blended into each other, then meshed and decimated to large readable
planes: the Old School RuneScape / Project Zomboid register, grounded and slightly stylised, legible at 64-128 px.
Eyes sit in carved sockets behind lids that are part of the skin. Hair, beard and brows are shells offset from the
same field, so they wrap the skull instead of sitting on it.

Proportions follow classical construction, the face a little shortened for the style: eyes at mid-head, one eye
width apart; brow, nose base and chin divide the face in thirds; the nose about as wide at its base as the gap
between the eyes; the mouth about as wide as the pupils are apart; ears from the brow to the nose base; the neck
rising from under the back of the skull, not hanging under the jaw.

Everything is built in the head's own frame (metres, origin at the skull centre, face toward -Y, up +Z). head()
returns an empty the caller places: tilt, scale and position move the whole head as one.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

from . import kit as K

# per-form scales on one construction. Female: a narrower, slightly smaller skull, a softer brow, a narrower jaw
# and chin, a smaller nose, fuller lips, a slimmer neck, no larynx.
FORMS = {
    'male':   dict(sx=1.0, sy=1.0, sz=1.0, brow=1.0, brow_y=0.0, jaw=1.0, chin=1.0, chin_round=0.0, nose=1.0, lip=1.0,
                   eye=1.0, gaunt=1.0, ear=1.0, neck=1.0, scm=1.0, adam=1.0, muzzle=1.0, cheek_z=0.0, brow_w=1.0,
                   fold=1.0, chin_y=0.0, chin_z=0.0, lower_y=0.0),
    'female': dict(sx=0.94, sy=0.965, sz=0.95, brow=0.15, brow_y=0.0025, jaw=0.8, chin=0.62, chin_round=0.35, nose=0.78,
                   lip=1.3, eye=1.12, gaunt=0.55, ear=0.88, neck=0.78, scm=0.8, adam=0.0, muzzle=0.82,
                   cheek_z=0.002, brow_w=0.75, fold=0.25, chin_y=0.001, chin_z=0.004, lower_y=0.006),
}
EYE_R = 0.0125          # eyeball radius; the same for both forms, so the female eye reads a touch larger
GRID = 0.0014           # meshing resolution (m): fine enough for the lid margin and the mouth line
LOWPOLY = dict(skin=4200, hair=1800, beard=1500, brow=400)     # triangles after decimation: large readable planes


# ------------------------------------------------------------------------------------------------ distance field
def _R(rx=0.0, ry=0.0, rz=0.0):
    """A rotation (degrees) as a numpy matrix M whose columns are the local axes: local = (p - c) @ M."""
    m = (Matrix.Rotation(math.radians(rz), 3, 'Z') @ Matrix.Rotation(math.radians(ry), 3, 'Y')
         @ Matrix.Rotation(math.radians(rx), 3, 'X'))
    return np.array(m, np.float32)


def _ell(P, c, r, M=None):
    """Ellipsoid (Quilez's bound): negative inside."""
    q = P - c
    if M is not None:
        q = q @ M
    q = q / r
    k0 = np.sqrt((q * q).sum(1))
    k1 = np.sqrt(((q / r) ** 2).sum(1))
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-12)


def _cap(P, a, b, ra, rb=None):
    """Capsule a->b whose radius runs ra->rb."""
    rb = ra if rb is None else rb
    pa = P - a
    ba = np.asarray(b) - a
    h = np.clip((pa @ ba) / float(ba @ ba), 0.0, 1.0)
    return np.sqrt(((pa - h[:, None] * ba) ** 2).sum(1)) - (ra + (rb - ra) * h)


def _rbox(P, c, half, rnd, M=None):
    q = P - c
    if M is not None:
        q = q @ M
    q = np.abs(q) - (np.asarray(half) - rnd)
    return np.sqrt((np.maximum(q, 0.0) ** 2).sum(1)) + np.minimum(q.max(1), 0.0) - rnd


def _both(fn, P, k=0.008):
    """A mass built on the +X side and mirrored, smoothly joined across the centreline."""
    return _smin(fn(P), fn(P * np.array((-1.0, 1.0, 1.0), np.float32)), k)


def _smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def _smax(a, b, k):
    return -_smin(-a, -b, k)


class _Noise:
    """Smooth 3D value noise in [0, 1] (numpy): the clumps of hair, the wobble of a hairline."""

    def __init__(self, seed):
        rng = np.random.default_rng(seed)
        self.perm = np.concatenate([rng.permutation(256)] * 2)
        self.vals = rng.random(256)

    def __call__(self, P, scale):
        q = P * scale
        i = np.floor(q).astype(np.int64)
        t = q - i
        u = t * t * (3.0 - 2.0 * t)
        i &= 255
        p = self.perm

        def v(dx, dy, dz):
            return self.vals[p[p[p[i[:, 0] + dx] + i[:, 1] + dy] + i[:, 2] + dz] & 255]

        x0 = v(0, 0, 0) + (v(1, 0, 0) - v(0, 0, 0)) * u[:, 0]
        x1 = v(0, 1, 0) + (v(1, 1, 0) - v(0, 1, 0)) * u[:, 0]
        x2 = v(0, 0, 1) + (v(1, 0, 1) - v(0, 0, 1)) * u[:, 0]
        x3 = v(0, 1, 1) + (v(1, 1, 1) - v(0, 1, 1)) * u[:, 0]
        y0 = x0 + (x1 - x0) * u[:, 1]
        y1 = x2 + (x3 - x2) * u[:, 1]
        return y0 + (y1 - y0) * u[:, 2]


class Layout:
    """Landmarks for one head: every mass and feature position, scaled for the form."""

    def __init__(self, sex, crooked=0.0):
        self.f = f = FORMS[sex]
        self.sex = sex
        self.k = np.array((f['sx'], f['sy'], f['sz']), np.float32)
        self.crooked = crooked
        self.eye = self.S(0.03, -0.066, 0.0)                        # the +x eyeball's centre: 6 mm behind the brow
        self.hw = 0.0145                                           # half the eye opening's width

    def S(self, x, y, z):
        return np.array((x, y, z), np.float32) * self.k

    def eyes(self):
        return [self.eye * (s, 1, 1) for s in (-1, 1)]


def field(P, L, scar=None):
    """Signed distance to the skin (m, negative inside) at points P (N, 3)."""
    f, S = L.f, L.S
    x = P[:, 0]
    Pm = np.column_stack((np.abs(x), P[:, 1], P[:, 2]))           # mirrored: one side built, both sides agree
    # cranium: broad at the temples, a forehead that curves back, flat temple planes
    d = _ell(P, S(0.0, 0.014, 0.025), S(0.072, 0.096, 0.081))
    d = _smax(d, np.abs(x) - 0.0695 * f['sx'], 0.016)
    # the face's mass (maxilla, the volume of the cheeks)
    ly = f['lower_y']        # how far the lower face (maxilla, mouth, chin) sits back under the brow
    d = _smin(d, _ell(P, S(0.0, -0.034 + ly, -0.032), S(0.058 * (0.9 + 0.1 * f['muzzle']), 0.058, 0.056)), 0.02)
    # brow ridge: a horizontal bar with a flat front, the glabella between the brows
    br = f['brow']
    d = _smin(d, _both(lambda Q: _ell(Q, S(0.027, -0.0785 + f['brow_y'], 0.0165), S(0.027, 0.0055 + 0.0025 * br, 0.0068 + 0.002 * br),
                                     M=_R(rz=18)), P), 0.008)
    d = _smin(d, _ell(P, S(0.0, -0.08 + f['brow_y'], 0.012), S(0.012, 0.0068, 0.01)), 0.008)
    # cheekbones and their arches back to the ear; the gaunt plane under them
    d = _smin(d, _ell(Pm, S(0.046, -0.068, -0.019 + f['cheek_z']), S(0.02, 0.015, 0.012), M=_R(rz=30)), 0.01)
    d = _smin(d, _cap(Pm, S(0.05, -0.056, -0.018), S(0.066, -0.004, -0.013), 0.0055), 0.012)
    d = _smax(d, -_ell(Pm, S(0.051, -0.086 + 0.006 * (1 - f['gaunt']), -0.052), S(0.018, 0.013, 0.02) * f['gaunt'] ** 0.5),
              0.012)
    # the muzzle the lips sit on
    d = _smin(d, _ell(P, S(0.0, -0.071 + ly + 0.025 * (1 - f['muzzle']), -0.056), S(0.036, 0.025 * f['muzzle'], 0.021)),
              0.012)
    # mandible: ramus under the ear, the body along the jaw line, a chin with a flat lower plane
    jw, ch = f['jaw'], f['chin']
    A, C, Rm = S(0.056 * jw, 0.022, -0.062), S(0.017 * ch, -0.077 + ly, -0.092), S(0.061 * jw, 0.02, -0.022)
    rj = 0.011 * jw ** 1.2
    d = _smin(d, _both(lambda Q: _cap(Q, A, C, rj, rj * 0.9), P, 0.012), 0.014)
    d = _smin(d, _cap(Pm, Rm, A, rj * 0.9, rj), 0.012)
    # the chin: a broad form with a flat lower plane, set back a few millimetres behind the lower lip
    cz = 0.0105 * (0.8 + 0.2 * ch)
    cc = S(0.0, -0.08 + ly + f['chin_y'], -0.091 + f['chin_z'])
    chin = _rbox(P, cc, S(0.02 * ch ** 1.5 + 0.002, 0.011, cz), 0.006)
    if f['chin_round']:
        chin = chin + (_ell(P, cc, S(0.0125, 0.0100, cz + 0.001)) - chin) * f['chin_round']
    d = _smin(d, chin, 0.012)
    # the neck rises from under the back of the skull; sternomastoids from behind the ears to the notch; trapezius
    nk = f['neck']
    sq = np.array((1.0, 1.0 / 0.92, 1.0), np.float32)
    d = _smin(d, _cap(P * sq, S(0.0, 0.024, -0.035) * sq, S(0.0, 0.013, -0.235) * sq, 0.05 * nk, 0.058 * nk), 0.02)
    d = _smin(d, _cap(Pm, S(0.05, 0.034, -0.04), S(0.017, -0.027, -0.2), 0.0105 * nk * f['scm']), 0.016)   # a notch between
    d = _smin(d, _both(lambda Q: _cap(Q, S(0.022, 0.056, -0.085), S(0.125, 0.03, -0.235), 0.024 * nk * f['scm'] ** 0.5),
                       P, 0.02), 0.02)
    if f['adam']:
        d = _smin(d, _ell(P, S(0.0, -0.043, -0.104), S(0.0075, 0.0075, 0.012)), 0.008)
    # eye sockets, carved under the brow; the under-eye plane that carries the tiredness
    d = _smax(d, -_ell(Pm, S(0.03, -0.081, -0.001), S(0.019, 0.012, 0.0135)), 0.006)
    d = _smin(d, _ell(Pm, S(0.03, -0.0775, -0.013), S(0.015, 0.0055, 0.005)), 0.004)
    # nose in three masses: a bridge from the root between the brows, a wedge-shaped tip projecting forward, the
    # alar base; nostrils cut under it. A once-broken nose kinks sideways.
    ns, kx = f['nose'], L.crooked

    def ny(y):          # a nose's parts stand off the face in proportion to its size
        return -0.079 + (y + 0.079) * ns
    d = _smin(d, _cap(P, S(0.0, -0.079, 0.005), S(kx, ny(-0.1085), -0.024), 0.006 * ns, 0.0082 * ns), 0.006)
    d = _smin(d, _rbox(P, S(kx * 0.8, ny(-0.1115), -0.0305), S(0.0088, 0.0082, 0.0078) * ns, 0.0042 * ns,
                       M=_R(rx=-28 + 14 * (1 - ns) / 0.22)), 0.005)
    d = _smin(d, _ell(Pm, S(0.0105 * ns, ny(-0.1015) + 0.5 * f['lower_y'], -0.0348), S(0.0068, 0.0086, 0.0068) * ns),
              0.004)
    d = _smin(d, _ell(P, S(kx * 0.6, ny(-0.1045) + 0.5 * f['lower_y'], -0.0378), S(0.0055, 0.008, 0.0042) * ns), 0.004)
    d = _smax(d, -_both(lambda Q: _ell(Q, S(0.0058 * ns, ny(-0.1058), -0.0405), S(0.0036, 0.0048, 0.0026) * ns), P, 0.002),
              0.0015)
    # lips: a thin upper lip, a slightly fuller lower one, the mouth line cut between them (level: a neutral
    # mouth), the corners dimpled, the fold under the lower lip
    lp = f['lip']
    lb = 0.02 * (1 - f['muzzle']) + f['lower_y']          # lips sit back with a smaller muzzle, a receding lower face
    d = _smin(d, _ell(P, S(0.0, -0.093 + lb, -0.0532), S(0.025, 0.005, 0.0042 * lp)), 0.004)
    d = _smin(d, _ell(P, S(0.0, -0.0915 + lb, -0.0616), S(0.021, 0.0048 * f['muzzle'], 0.0045 * lp ** 0.7)), 0.004)
    slit = np.minimum(_cap(Pm, S(0.0, -0.0985 + lb, -0.0572), S(0.014, -0.0962 + lb, -0.0572), 0.0009),
                      _cap(Pm, S(0.014, -0.0962 + lb, -0.0572), S(0.0285, -0.0885 + lb, -0.0576), 0.0009, 0.0007))
    d = _smax(d, -slit, 0.0008)
    d = _smax(d, -_ell(Pm, S(0.0285, -0.0885 + lb, -0.0577), np.full(3, 0.0022, np.float32)), 0.0012)
    d = _smax(d, -_ell(P, S(0.0, -0.0955 + lb + 0.003 * (1 - f['fold']), -0.0705), S(0.013, 0.003, 0.003) * f['fold'] ** 0.5),
              0.006)
    # ears, from the brow down to the nose base, tilted back and flared: the rim (helix), the hollow, the lobe
    E = _R(rx=-15, rz=-11)
    er = f['ear']
    e = _ell(Pm, S(0.0745, 0.014, -0.013), S(0.0072, 0.0172 * er, 0.0305 * er), M=E)
    e = _smin(e, _ell(Pm, S(0.0728, 0.009, -0.013 - 0.027 * er), S(0.0058, 0.0078 * er, 0.009 * er)), 0.004)
    e = _smax(e, -_ell(Pm, S(0.0802, 0.01, -0.015), S(0.0052, 0.009 * er, 0.013 * er), M=E), 0.002)
    e = _smax(e, -_ell(Pm, S(0.0815, 0.019, -0.003), S(0.0038, 0.011 * er, 0.02 * er), M=E), 0.0015)
    d = _smin(d, e, 0.004)
    # the founding scar: a shallow, uneven groove
    if scar:
        for a, b, w in scar:
            d = _smax(d, -_cap(P, a, b, w * 0.5), 0.0006)
    # eyes: a shell of lid around each eyeball, the eyeball's own room, and the hooded almond opening cut through
    c = L.eye
    lid = _ell(Pm, c, np.full(3, EYE_R + 0.0026, np.float32))
    lid = _smax(lid, Pm[:, 1] - (c[1] + 0.003), 0.001)
    d = _smin(d, lid, 0.003)
    d = _smax(d, -_ell(Pm, c, np.full(3, EYE_R + 0.0002, np.float32)), 0.0005)
    q = Pm - c
    t = np.clip(q[:, 0] / L.hw, -1.0, 1.0)
    w = np.maximum(0.0, 1.0 - t * t)
    up = 0.0042 * f['eye'] * w ** 0.6 + 0.0008 * t
    lo = -0.0045 * f['eye'] * w ** 0.8 + 0.0008 * t
    ap = np.maximum(np.maximum(q[:, 2] - up, lo - q[:, 2]), np.maximum(np.abs(q[:, 0]) - L.hw, q[:, 1]))
    return _smax(d, -ap, 0.0006)


def surface(L, x, z, scar=None, lift=0.0):
    """The front surface point at (x, z) (ray-marched along +Y), pushed `lift` out along the normal."""
    p = np.array([[x, -0.2, z]])
    for _ in range(200):
        dd = field(p, L, scar)[0]
        if dd < 1e-5:
            break
        p[0, 1] += max(dd, 2e-5)
    e = 1e-4
    g = np.array([field(p + o, L, scar)[0] - field(p - o, L, scar)[0] for o in np.eye(3) * e])
    n = g / max(np.linalg.norm(g), 1e-12)
    return p[0] + n * lift, n


# ------------------------------------------------------------------------------------------------ meshing
class _Grid:
    """The field sampled on a regular grid: exact within a band around the skin (where the skin and the shells
    offset from it lie), interpolated from a coarse pass elsewhere."""

    def __init__(self, L, scar, lo, hi, band=(-0.0075, 0.0125), h=GRID, m=4, chunk=250_000):
        self.lo, self.h = np.asarray(lo, np.float32), h
        n = np.ceil((np.asarray(hi) - np.asarray(lo)) / h).astype(int) + 1
        self.shape = tuple(n)
        nc = (n - 1) // m + 2
        axes = [np.float32(lo[i]) + np.arange(nc[i], dtype=np.float32) * np.float32(h * m) for i in range(3)]
        C = np.stack(np.meshgrid(*axes, indexing='ij'), -1).reshape(-1, 3)
        Dc = np.concatenate([field(C[i:i + chunk], L, scar) for i in range(0, len(C), chunk)]).reshape(nc)
        D = Dc.astype(np.float32)
        for ax in range(3):                                   # trilinear, one axis at a time
            u = np.arange(n[ax], dtype=np.float32) / m
            i0 = np.minimum(np.floor(u).astype(int), nc[ax] - 2)
            w = (u - i0).reshape([-1 if k == ax else 1 for k in range(3)])
            D = np.take(D, i0, axis=ax) * (1 - w) + np.take(D, i0 + 1, axis=ax) * w
        slack = 0.35 * h * m
        idx = np.nonzero((D > band[0] - slack) & (D < band[1] + slack))
        self.idx = idx
        self.P = self.lo + np.column_stack(idx).astype(np.float32) * np.float32(h)
        exact = np.concatenate([field(self.P[i:i + chunk], L, scar) for i in range(0, len(self.P), chunk)])
        D[idx] = exact
        self.D = D
        self.exact = exact

    def shell(self, t, region, inner=0.006, feather=0.005):
        """A shell from `inner` under the skin out to thickness t(P), kept where region(P) < 0; region is a rough
        distance (m), and the shell thins toward its edge so hair and beard feather into the skin."""
        H = np.ones(self.shape, np.float32)
        d = self.exact
        r = region(self.P)
        th = t(self.P) * np.clip(-r / feather, 0.3, 1.0)
        s = _smax(_smax(d - th, -(d + inner), 0.001), r, 0.0015)
        H[self.idx] = s
        return H


def _nets(D, lo, h):
    """Surface nets: one vertex per cell the surface crosses, one quad per grid edge it crosses."""
    s = D < 0
    nx, ny, nz = D.shape
    cs = [s[a:nx - 1 + a, b:ny - 1 + b, c:nz - 1 + c] for a in (0, 1) for b in (0, 1) for c in (0, 1)]
    act = np.argwhere(np.logical_or.reduce(cs) & ~np.logical_and.reduce(cs))
    del cs
    vid = np.full((nx - 1, ny - 1, nz - 1), -1, np.int64)
    vid[act[:, 0], act[:, 1], act[:, 2]] = np.arange(len(act))
    corners = np.array([(a, b, c) for a in (0, 1) for b in (0, 1) for c in (0, 1)], float)
    vals = np.stack([D[act[:, 0] + int(o[0]), act[:, 1] + int(o[1]), act[:, 2] + int(o[2])] for o in corners], 1)
    acc = np.zeros((len(act), 3))
    cnt = np.zeros(len(act))
    for a, b in ((0, 4), (1, 5), (2, 6), (3, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 1), (2, 3), (4, 5), (6, 7)):
        va, vb = vals[:, a], vals[:, b]
        m = (va < 0) != (vb < 0)
        t = va[m] / (va[m] - vb[m])
        acc[m] += corners[a] + t[:, None] * (corners[b] - corners[a])
        cnt[m] += 1
    verts = lo + (act + acc / cnt[:, None]) * h
    quads = []
    e = np.argwhere(s[:-1, 1:-1, 1:-1] != s[1:, 1:-1, 1:-1])
    i, j, k = e[:, 0], e[:, 1] + 1, e[:, 2] + 1
    quads.append((np.stack([vid[i, j - 1, k - 1], vid[i, j, k - 1], vid[i, j, k], vid[i, j - 1, k]], 1), s[i, j, k]))
    e = np.argwhere(s[1:-1, :-1, 1:-1] != s[1:-1, 1:, 1:-1])
    i, j, k = e[:, 0] + 1, e[:, 1], e[:, 2] + 1
    quads.append((np.stack([vid[i - 1, j, k - 1], vid[i - 1, j, k], vid[i, j, k], vid[i, j, k - 1]], 1), s[i, j, k]))
    e = np.argwhere(s[1:-1, 1:-1, :-1] != s[1:-1, 1:-1, 1:])
    i, j, k = e[:, 0] + 1, e[:, 1] + 1, e[:, 2]
    quads.append((np.stack([vid[i - 1, j - 1, k], vid[i, j - 1, k], vid[i, j, k], vid[i - 1, j, k]], 1), s[i, j, k]))
    out = []
    for q, inside in quads:
        q = q.copy()
        q[~inside] = q[~inside][:, ::-1]
        out.append(q)
    return verts, np.concatenate(out)


def _mesh(name, verts, quads, mat, tris, smooth_angle=None):
    """A Blender object from surface-nets output, smoothed a touch and decimated to `tris` triangles."""
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(verts))
    me.vertices.foreach_set('co', verts.astype(np.float32).ravel())
    me.loops.add(len(quads) * 4)
    me.loops.foreach_set('vertex_index', quads.astype(np.int32).ravel())
    me.polygons.add(len(quads))
    me.polygons.foreach_set('loop_start', np.arange(0, len(quads) * 4, 4, dtype=np.int32))
    me.update(calc_edges=True)
    me.validate()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.append(mat)
    sm = ob.modifiers.new('smooth', 'SMOOTH')
    sm.factor, sm.iterations = 0.5, 2
    dm = ob.modifiers.new('lowpoly', 'DECIMATE')
    dm.ratio = min(1.0, tris / max(1, 2 * len(quads)))
    dg = bpy.context.evaluated_depsgraph_get()
    baked = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.clear()
    ob.data = baked
    bpy.data.meshes.remove(me)
    if not baked.materials:
        baked.materials.append(mat)
    if smooth_angle is None:
        baked.shade_flat()
    else:
        baked.shade_smooth()
        baked.set_sharp_from_angle(angle=math.radians(smooth_angle))
    return ob


# ------------------------------------------------------------------------------------------------ hair regions
def _theta(P):
    """Angle round the head from the front of the face (0) through the side (90) to the back (180), degrees."""
    return np.degrees(np.arctan2(np.abs(P[:, 0]), -P[:, 1]))


def hairline(P, style, L, noise):
    """Height of the hairline over the skull at each point's angle round the head (head frame, m)."""
    th = _theta(P)
    if style == 'crop':   # a man's crop: a slightly receding front, down to the nape at the back
        z = np.interp(th, [0, 28, 40, 58, 90, 118, 150, 180], [0.056, 0.058, 0.063, 0.044, 0.026, 0.0, -0.036, -0.056])
    else:                 # the undercut: sides and back shaved up to a line under the knot's mass
        z = np.interp(th, [0, 30, 50, 75, 110, 150, 180], [0.057, 0.055, 0.05, 0.047, 0.046, 0.043, 0.038])
    return z * L.k[2] + 0.003 * (noise(P, 140.0) - 0.5) + 0.001 * (noise(P, 400.0) - 0.5)


def _region_hair(style, L, noise):
    def region(P):
        return hairline(P, style, L, noise) - P[:, 2]
    return region


def _thick_hair(style, L, noise):
    def t(P):
        depth = np.clip((P[:, 2] - hairline(P, style, L, noise)) / 0.014, 0.3, 1.0)
        top = np.clip((P[:, 2] - 0.02) / 0.06, 0.0, 1.0)            # fuller on the crown than over the ears
        if style == 'crop':
            return (0.003 + 0.0025 * top) * depth + 0.003 * (noise(P, 70.0) - 0.4) + 0.0012 * noise(P, 190.0)
        return 0.0048 * depth + 0.0014 * (noise(P * (1.0, 0.25, 1.0), 150.0) - 0.3)   # pulled back hard: ridged
    return t


def _region_beard(L, noise):
    def region(P):
        th = _theta(P)
        top = np.interp(th, [0, 18, 30, 45, 60, 72, 80, 88], [-0.042, -0.043, -0.046, -0.037, -0.024, -0.01, 0.006,
                                                              0.03])
        top = top * L.k[2] + 0.004 * (noise(P, 120.0) - 0.5)
        low = np.interp(th, [0, 40, 70, 95], [-0.118, -0.112, -0.088, -0.06]) * L.k[2] + 0.004 * (noise(P, 90.0) - 0.5)
        r = np.maximum(P[:, 2] - top, low - P[:, 2])
        r = np.maximum(r, (th - 86.0) * 0.0005)                    # stops in front of the ear
        # the mouth stays clear: an almond round both lips
        mx = np.clip(P[:, 0] / 0.0295, -1.0, 1.0)
        mouth = np.maximum(np.abs(P[:, 2] + 0.0578 * L.k[2]) - 0.0082 * np.sqrt(1.0 - mx * mx), np.abs(P[:, 0]) - 0.0295)
        mouth = np.maximum(mouth, P[:, 1] + 0.075)
        return np.maximum(r, -mouth)
    return region


def _thick_beard(L, noise):
    def t(P):
        chin = np.exp(-(P[:, 0] / 0.03) ** 2) * np.clip((-0.066 * L.k[2] - P[:, 2]) / 0.03, 0.0, 1.0)
        side = np.clip((_theta(P) - 60.0) / 25.0, 0.0, 1.0)            # thinner up the sideburns
        tash = np.exp(-((P[:, 2] + 0.047 * L.k[2]) / 0.005) ** 2) * (np.abs(P[:, 0]) < 0.034)
        base = 0.0038 + 0.0062 * chin - 0.0012 * tash - 0.0016 * side
        return base + 0.0032 * (noise(P * (1.0, 1.0, 0.5), 75.0) - 0.4) + 0.0012 * noise(P, 210.0)
    return t


def _region_brow(L, scar_side, noise):
    def region(P):
        Q = np.column_stack((np.abs(P[:, 0]), P[:, 2]))
        a, b = np.array(L.S(0.0125, 0, 0.0158))[[0, 2]], np.array(L.S(0.0505, 0, 0.0186))[[0, 2]]
        ba = b - a
        h = np.clip(((Q - a) @ ba) / float(ba @ ba), 0.0, 1.0)
        r = (np.sqrt(((Q - a - h[:, None] * ba) ** 2).sum(1)) - (0.0032 - 0.0017 * h) * L.f['brow_w']
             + 0.0012 * (noise(P, 520.0) - 0.5))
        r = np.maximum(r, P[:, 1] + 0.05)
        if scar_side:   # the scar cuts the brow in two
            gap = 0.0024 - np.abs(P[:, 0] - scar_side * 0.0438 * L.k[0])
            r = np.maximum(r, gap)
        return r
    return region


# ------------------------------------------------------------------------------------------------ the scar
def scar_path(L, side):
    """The founding scar: from the forehead through the brow, past the eye's outer corner, down the cheek. Broken
    in two places, its width uneven. Returns 3D segments (a, b, width) on the skin."""
    xz = [(0.034, 0.052), (0.039, 0.036), (0.0445, 0.022), (0.049, 0.012), (0.0525, 0.001), (0.0535, -0.012),
          (0.0525, -0.026), (0.051, -0.04), (0.048, -0.052)]
    widths = [0.0024, 0.003, 0.0021, 0.0026, 0.0032, 0.0028, 0.0023, 0.0019]
    gaps = {3, 6}                                        # skip: a break by the eye corner and one on the cheek
    pts = [surface(L, side * x * L.k[0], z * L.k[2])[0] for x, z in xz]
    return [(pts[i], pts[i + 1], widths[i]) for i in range(len(pts) - 1) if i not in gaps]


# ------------------------------------------------------------------------------------------------ shader landmarks
def marks(sex, scar=None, crooked=0.0, style='crop'):
    """Where the skin shader paints: weather on the cheeks and nose, the sockets and the dark circles, the lips,
    the scar. (The undercut's stubble is a vertex attribute the head writes: see _stubble.)"""
    L = Layout(sex, crooked)
    S = L.S
    out = dict(
        red=[(tuple(S(s * 0.045, -0.082, -0.026)), 0.02, 0.45) for s in (-1, 1)] +
            [(tuple(S(0.0, -0.079 + (-0.118 + 0.079) * FORMS[sex]['nose'], -0.031)), 0.012, 0.5)] +
            [(tuple(S(s * 0.078, 0.012, -0.012)), 0.016, 0.35) for s in (-1, 1)],
        sock=[(tuple(S(s * 0.03, -0.084, 0.002)), 0.016, 0.5) for s in (-1, 1)],
        bags=[(tuple(S(s * 0.03, -0.087, -0.0125)), 0.0095, 0.55) for s in (-1, 1)],
        lip_amount=0.45 if sex == 'male' else 0.72,
        lash=[] if sex == 'male' else [(tuple(L.eye * (s, 1, 1) + S(0.0, -EYE_R - 0.0015, 0.0044)),
                                        tuple(S(0.0125, 0.004, 0.0013))) for s in (-1, 1)],
        lips=[(tuple(S(0.0, -0.095 + FORMS[sex]['lower_y'], -0.0532)), tuple(S(0.029, 0.012, 0.0045 * FORMS[sex]['lip']))),
              (tuple(S(0.0, -0.095 + FORMS[sex]['lower_y'], -0.0618)), tuple(S(0.025, 0.012, 0.0052 * FORMS[sex]['lip'])))],
        creases=[[tuple(np.array(S(s * x, 0, z))[[0, 2]]) for x, z in ((0.0175, -0.034), (0.025, -0.046), (0.0305, -0.061))]
                 for s in (-1, 1)],
        forehead=[[tuple(np.array(S(x, 0, z))[[0, 2]]) for x, z in ((-0.028, zz - 0.003), (0.0, zz), (0.028, zz - 0.003))]
                  for zz in (0.036, 0.046)],
        scar=None)
    if scar:
        out['scar'] = [(tuple(a), tuple(b), w) for a, b, w in scar_path(L, scar)]
    return out


# ------------------------------------------------------------------------------------------------ the head
_CACHE = {}


def _stubble(ob, style, L, noise):
    """Write the 'stubble' attribute the skin shader reads: the clippered sides and back of an undercut, from just
    under the hairline down to the neckline, following the skull."""
    me = ob.data
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get('co', co)
    P = co.reshape(-1, 3)
    w = np.zeros(len(P), np.float32)
    if style != 'crop':
        th = _theta(P)
        low = np.interp(th, [50, 80, 110, 150, 180], [0.03, 0.012, 0.0, -0.04, -0.055]) * L.k[2]
        w = np.clip((hairline(P, style, L, noise) + 0.002 - P[:, 2]) / 0.004, 0.0, 1.0)
        w *= np.clip((P[:, 2] - low) / 0.012, 0.0, 1.0) * np.clip((th - 50.0) / 12.0, 0.0, 1.0)
        w *= np.clip((0.0745 * L.k[0] - np.abs(P[:, 0])) / 0.004, 0.0, 1.0)      # not on the ears
    at = me.attributes.new('stubble', 'FLOAT', 'POINT')
    at.data.foreach_set('value', w.astype(np.float32))


def _ball(name, r, mat, loc, rz=0.0, seg=24, rings=16):
    """An eyeball in its own object space (the eye material's iris sits on its local -Y)."""
    ob = K.sphere(name, (0.0, 0.0, 0.0), r, mat, seg=seg, rings=rings)
    ob.location = Vector(loc)
    ob.rotation_euler.z = math.radians(rz)
    return ob


def head(name, sex, skin, lips, hair, eye_mat, dark, beard=True, hair_style='crop', scar=None, crooked=0.0,
         greying=None, seed=0, gaze=0.0):
    """Build a head. Returns (root_empty, info). Place the root; everything else follows it.

    skin: the face material (grit.skin with face=marks(...)); lips: unused (the lips are painted on the skin);
    hair/eye_mat/dark: materials (dark: the knot's tie); scar: side (+1/-1) of the founding scar; crooked: a
    once-broken nose's sideways kink (m); greying: a second hair material for the beard (a veteran); gaze: degrees
    the eyes turn toward the viewer (+ toward the head's +X side)."""
    L = Layout(sex, crooked)
    sc = scar_path(L, scar) if scar else None
    key = (sex, bool(beard), hair_style, scar, round(crooked, 5), seed)
    if key not in _CACHE:
        g = _Grid(L, sc, lo=(-0.105, -0.145, -0.24), hi=(0.105, 0.16, 0.16))
        noise = _Noise(seed + 101)
        geo = {'skin': _nets(g.D, g.lo, g.h)}
        geo['hair'] = _nets(g.shell(_thick_hair(hair_style, L, noise), _region_hair(hair_style, L, noise)), g.lo, g.h)
        if beard:
            geo['beard'] = _nets(g.shell(_thick_beard(L, noise), _region_beard(L, noise)), g.lo, g.h)
        geo['brow'] = _nets(g.shell(lambda P: 0.0013 + 0.0007 * noise(P, 300.0), _region_brow(L, scar, noise), feather=0.0016), g.lo, g.h)
        _CACHE[key] = geo
    geo = _CACHE[key]
    parts = [_mesh(name, *geo['skin'], skin, LOWPOLY['skin'], smooth_angle=38)]
    _stubble(parts[0], hair_style, L, _Noise(seed + 101))
    parts.append(_mesh(f'{name}_hair', *geo['hair'], hair, LOWPOLY['hair'], smooth_angle=45))
    if hair_style != 'crop':     # the knot: hair pulled back hard into a bun bound at the crown
        kn = Vector(L.S(0.0, 0.056, 0.098))
        bun = K.sphere(f'{name}_knot', (0.0, 0.0, 0.0), 1.0, hair, scale=(0.02, 0.022, 0.017), seg=14, rings=9)
        bun.location = kn
        bun.rotation_euler = (math.radians(-25), 0.0, 0.0)
        bun.data.shade_flat()
        parts.append(bun)
        tie = K.lathe(f'{name}_tie', [(0.0135, -0.0035), (0.0152, 0.0), (0.0135, 0.0035)], dark, seg=12,
                      cap_bottom=False, cap_top=False)
        tie.location = kn + Vector((0.0, -0.007, -0.011))
        tie.rotation_euler = (math.radians(-40), 0.0, 0.0)
        parts.append(tie)
    if 'beard' in geo:
        parts.append(_mesh(f'{name}_beard', *geo['beard'], greying or hair, LOWPOLY['beard'], smooth_angle=45))
    parts.append(_mesh(f'{name}_brows', *geo['brow'], hair, LOWPOLY['brow'], smooth_angle=60))
    eyes = []
    for s in (-1, 1):
        c = L.eye * (s, 1, 1)
        eyes.append(Vector(c))
        parts.append(_ball(f'{name}_eye', EYE_R, eye_mat, c, rz=gaze))
    root = K.root(name + '_root')
    K.parent(parts, root)
    return root, dict(eyes=eyes, chin=Vector(surface(L, 0.0, -0.1 * L.k[2])[0]))
