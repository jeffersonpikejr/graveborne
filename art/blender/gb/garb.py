"""Garb: what a lightly armed soldier wears and carries, laid over the body (gb/body.py).

Clothes are layers offset from the posed body's own surface (Dressed.layer), the way the heads' hair lies over the
skull, so every garment follows its wearer: his barrel chest and heavy arms, her waist, hips and seat, with nothing
redrawn per body. What hangs free is draped (Drape): a capelet or a cloak falls from its top edge, rests on whatever
of the body stands out beneath it, and hangs on, flaring toward the hem. The hood is its own shell round the head
(hood), pulled back off the brow (face.HOOD_*: the head fits its hair under the same shape). And a skirmisher's gear:
a yew longbow, arrows and a quiver, a boar spear, a long knife.

Figure space as in body.py: metres, feet on z = 0, facing -Y, the figure's left on +X. Angles round the body are
degrees from the figure's left (+X, 0) through the back (+Y, 90) to the right (180) and the front (270, or -90).
"""
import math
import random

import bmesh
import numpy as np
from mathutils import Matrix, Vector

from . import armor as A
from . import body as BD
from . import face as F
from . import kit as K

_DRESSED = {}


def dressed(fr, grid=0.004):
    """The Dressed body for a Frame, kept per body and pose: a figure's variants (base, Commander, Veteran, risen) all
    wear the same clothes, so the body is sampled and each garment meshed once."""
    key = (tuple(sorted((k, tuple(v) if isinstance(v, list) else v) for k, v in fr.f.items())),
           tuple((k, tuple(np.round(v, 5))) for k, v in sorted(fr.joints.items())),
           tuple((k, tuple(np.round(v, 4))) for k, v in sorted(fr.grip.items())),
           tuple((k, tuple(np.round(np.concatenate(v), 4))) for k, v in sorted(fr.open.items())), grid)
    if key not in _DRESSED:
        while len(_DRESSED) >= 4:
            _DRESSED.pop(next(iter(_DRESSED)))
        _DRESSED[key] = Dressed(fr, grid)
    return _DRESSED[key]


class Dressed:
    """A posed body sampled once on a grid (face._Grid of body.field), and the garments laid over it."""

    def __init__(self, fr, grid=0.004):
        self.fr = fr
        J = np.array(list(fr.joints.values()))
        lo = np.minimum(J.min(0) - 0.25, (-0.42, -0.3, 0.0)).astype(float)
        hi = np.maximum(J.max(0) + 0.25, (0.42, 0.26, 0.0)).astype(float)
        lo[2], hi[2] = -0.01, 1.58 * fr.hf
        self.g = F._Grid(None, None, tuple(lo), tuple(hi), band=(-0.012, 0.04), h=grid, m=4,
                         fn=lambda Q: BD.field(Q, fr))
        self._nets = {}

    # ---- meshes
    def _mesh(self, name, mat, make, tris, smooth):
        if name not in self._nets:
            self._nets[name] = F._nets(make(), self.g.lo, self.g.h)
        return F._mesh(name, *self._nets[name], mat, tris, smooth_angle=smooth)

    def skin(self, name, mat, tris=12000):
        """The body itself (under the clothes it shows only where they end)."""
        return self._mesh(name, mat, lambda: self.g.D, tris, 55)

    def layer(self, name, mat, t, region, inner=0.003, feather=0.002, floor=0.85, tris=9000, smooth=50):
        """A garment: from `inner` under the skin (negative: that far out over it) out to thickness t(P) (m),
        where region(P) < 0."""
        return self._mesh(name, mat, lambda: self.g.shell(t, region, inner, feather, floor), tris, smooth)

    # ---- regions (rough signed distances, negative inside)
    def heights(self, z0, z1):
        """Between two heights, given on the male anchor's scale."""
        hf = self.fr.hf
        return lambda P: np.maximum(z0 * hf - P[:, 2], P[:, 2] - z1 * hf)

    def arms(self, grow=1.15):
        """Within the arms and hands (their capsules, inflated)."""
        return lambda P: BD._arms(P, self.fr, grow)

    def trunk(self, margin=0.0):
        """Nearer the trunk than an arm (a sleeveless garment's region: its armholes fall where the arm takes over)."""
        return lambda P: BD._torso(P, self.fr) - BD._arms(P, self.fr, 1.0) - margin

    def hands(self, grow=1.0, cuff=0.012):
        """Within the hands, from `cuff` short of each wrist."""
        fr = self.fr

        def region(P):
            out = None
            for s in 'lr':
                wr, el = fr.joints['wr_' + s], fr.joints['el_' + s]
                hd = (wr - el) / np.linalg.norm(wr - el)
                d = F._cap(P, wr - hd * cuff, wr + hd * fr.f['hand'][0] * 0.9, fr.f['hand'][1] * 0.62 * grow)
                out = d if out is None else np.minimum(out, d)
            return out
        return region

    def forearm(self, side, t0, t1, radius=0.1):
        """A length of one forearm: from t0 to t1 of the way from the elbow to the wrist, within `radius` of it."""
        el, wr = self.fr.joints['el_' + side], self.fr.joints['wr_' + side]
        L = float(np.linalg.norm(wr - el))
        u = (wr - el) / L

        def region(P):
            q = P - el
            s = q @ u
            rad = np.sqrt(np.maximum((q * q).sum(1) - s * s, 0.0))
            return np.maximum(rad - radius, np.maximum(t0 * L - s, s - t1 * L))
        return region

    # ---- where the surface is
    def outer(self, O, dirs, clear, arms=True):
        """Along rays from O (N, 3) in directions dirs (N, 3): how far out the body's surface offset by `clear` is
        last crossed, marching in from outside (0 where the ray misses the body)."""
        fr = self.fr
        O = np.asarray(O, np.float32)
        dirs = np.asarray(dirs, np.float32)
        r = np.full(len(O), 0.95, np.float32)
        hit = np.zeros(len(O), bool)
        live = np.ones(len(O), bool)
        for _ in range(200):
            idx = np.nonzero(live)[0]
            if not len(idx):
                break
            d = BD.field(O[idx] + dirs[idx] * r[idx, None], fr, arms=arms) - clear
            h = d < 5e-4
            hit[idx[h]] = True
            rr = r[idx] - np.maximum(d * 0.8, 0.0015)
            r[idx] = np.where(h, r[idx], rr)
            live[idx[h | (rr <= 0.0)]] = False
        return np.where(hit, r, 0.0)

    def ring(self, z, clear, n=48, oy=0.0, arms=False):
        """A closed path round the trunk at height z (m), `clear` off the skin: where a belt lies. Returns (points,
        outward normals)."""
        a = np.radians(np.arange(n) * 360.0 / n)
        dirs = np.column_stack((np.cos(a), np.sin(a), np.zeros(n))).astype(np.float32)
        O = np.tile(np.array((0.0, oy, z), np.float32), (n, 1))
        r = self.outer(O, dirs, clear, arms=arms)
        return [Vector(O[i] + dirs[i] * r[i]) for i in range(n)], [Vector(dv) for dv in dirs]

    def on(self, a_deg, z, clear, oy=0.0, arms=False):
        """One point on the trunk at angle a (degrees) and height z, `clear` off the skin, and its outward normal."""
        a = math.radians(a_deg)
        dv = np.array([[math.cos(a), math.sin(a), 0.0]], np.float32)
        r = float(self.outer(np.array([[0.0, oy, z]], np.float32), dv, clear, arms=arms)[0])
        return Vector((r * math.cos(a), oy + r * math.sin(a), z)), Vector(dv[0])


class Drape:
    """Cloth hanging round the body from a top edge at z_top down to a hem at z_bot, over the angles given (degrees,
    see the module docstring): at each height it stands `clear` off whatever of the body is widest at or above that
    height along its line, so it rests on the shoulders, falls clear of an elbow or a seat, and hangs on below.
    collar=(r, spread): it leaves a collar of radius r, spreading by `spread` per metre of fall. flare widens it toward
    the hem; folds ripple it (fold_n of them round a full circle); ragged tears the hem."""

    def __init__(self, D, z_top, z_bot, angles, clear, rows=26, oy=0.02, collar=None, flare=0.0, folds=0.0, fold_n=9,
                 ragged=0.0, seed=0, arms=True, closed=False, hem=None, cinch=None):
        """closed: the angles run the whole way round (without repeating the first at the end). hem(a): how much
        higher the hem is at angle a (m), shaping it (a capelet shorter in front). cinch=(z, clear): a belt at height
        z pulls the cloth in to `clear` off the body there, and it hangs afresh below it (a belted tabard or robe)."""
        self.oy = oy
        A_ = np.asarray(angles, np.float32)
        a = np.radians(A_)
        nr, nc = rows + 1, len(A_)
        lift = np.array([hem(float(x)) for x in A_], np.float32) if hem else np.zeros(nc, np.float32)
        frac = np.linspace(0.0, 1.0, nr).astype(np.float32)[:, None]
        Zg = (z_top + (z_bot + lift[None, :] - z_top) * frac).astype(np.float32)       # each column's own heights
        Z = Zg[:, 0].copy() if not hem else np.linspace(z_top, z_bot, nr).astype(np.float32)
        dirs = np.column_stack((np.cos(a), np.sin(a), np.zeros(nc))).astype(np.float32)
        O = np.column_stack((np.zeros(nr * nc), np.full(nr * nc, oy), Zg.ravel())).astype(np.float32)
        R = D.outer(O, np.tile(dirs, (nr, 1)), clear, arms=arms).reshape(nr, nc)
        if collar:
            R = np.maximum(R, collar[0] + collar[1] * (z_top - Zg))
        kc = None
        if cinch:           # the belt's row: the cloth pulled in to the body there
            kc = int(np.argmin(np.abs(Zg[:, 0] - cinch[0])))
            Oc = np.column_stack((np.zeros(nc), np.full(nc, oy), Zg[kc])).astype(np.float32)
            belt = D.outer(Oc, dirs, cinch[1], arms=arms)

        raw = R.copy()
        if kc is None:
            R = np.maximum.accumulate(R, axis=0)             # it hangs from whatever stands out above
        else:               # above the belt it hangs, then bloused in to it; below, it hangs afresh from the belt
            R[:kc] = np.maximum.accumulate(R[:kc], axis=0)
            w = np.clip(1.0 - (Zg[:kc] - Zg[kc]) / 0.08, 0.0, 1.0) ** 2
            R[:kc] = np.maximum(R[:kc] * (1.0 - w) + belt[None, :] * w, raw[:kc])
            R[kc] = belt
            R[kc:] = np.maximum.accumulate(R[kc:], axis=0)
            self.belt_row = kc
        for _ in range(2):                                   # smooth round, then down
            if closed:
                R = 0.25 * np.roll(R, 1, 1) + 0.5 * R + 0.25 * np.roll(R, -1, 1)
            else:
                R[:, 1:-1] = 0.25 * R[:, :-2] + 0.5 * R[:, 1:-1] + 0.25 * R[:, 2:]
        R[1:-1] = 0.25 * R[:-2] + 0.5 * R[1:-1] + 0.25 * R[2:]
        R = np.maximum.accumulate(R, axis=0) if kc is None else np.maximum(R, raw)
        t = np.repeat(frac, nc, 1)
        rnd = random.Random(seed)
        ph = [rnd.random() * 6.283 for _ in range(4)]
        wave = np.sin(a * fold_n + ph[0] + 1.3 * t) + 0.5 * np.sin(a * (fold_n * 1.7) + ph[1] - 0.8 * t)
        R = R + flare * t ** 1.3 + folds * t * wave
        if ragged:
            rag = np.array([math.sin(x * 5.0 + ph[2]) * 0.6 + math.sin(x * 13.0 + ph[3]) * 0.4 for x in a], np.float32)
            Zg[-1] += ragged * (rag + np.array([rnd.random() - 0.5 for _ in a], np.float32) * 0.8)
            Zg[-2] += ragged * 0.4 * rag
        self.A, self.Z, self.R, self.Zg, self.closed = A_, Z, R, Zg, closed
        self.dirs = dirs

    def grid(self):
        """The cloth's points, rows top to bottom."""
        X = self.dirs[None, :, 0] * self.R
        Y = self.oy + self.dirs[None, :, 1] * self.R
        return np.stack((X, Y, self.Zg), -1)

    def point(self, a_deg, z, lift=0.0):
        """A point on the cloth at angle a (degrees, inside the drape's range) and height z, lifted off it along its
        outward normal, and that normal."""
        A_, Rg, Zg = self.A, self.R, self.Zg
        if self.closed:
            a = a_deg % 360.0
            A_ = np.append(A_, A_[0] + 360.0)
            Rg = np.concatenate((Rg, Rg[:, :1]), 1)
            Zg = np.concatenate((Zg, Zg[:, :1]), 1)
        else:
            a = min(max(a_deg, float(A_[0])), float(A_[-1]))
        col_r = np.array([np.interp(a, A_, row) for row in Rg], np.float32)
        col_z = np.array([np.interp(a, A_, row) for row in Zg], np.float32)
        r = float(np.interp(-z, -col_z, col_r)) + lift
        ar = math.radians(a)
        n = Vector((math.cos(ar), math.sin(ar), 0.0))
        return Vector((r * math.cos(ar), self.oy + r * math.sin(ar), z)), n

    def mesh(self, name, mat, thick=0.005, levels=1):
        G = self.grid()
        nr, nc = G.shape[:2]
        bm = bmesh.new()
        V = [[bm.verts.new(tuple(map(float, G[k, i]))) for i in range(nc)] for k in range(nr)]
        span = nc if self.closed else nc - 1
        for k in range(nr - 1):
            for i in range(span):
                j = (i + 1) % nc
                bm.faces.new((V[k][i], V[k][j], V[k + 1][j], V[k + 1][i]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        ob = K._obj(name, bm, mat)
        A.solid(ob, thick)
        if levels:
            K.subsurf(ob, levels)
        return ob


# ------------------------------------------------------------------------------------------------ the hood
def hood(name, H, z_bot, mat, thick=0.0065, grid=0.0025, seed=0, tris=9000):
    """A hood pulled back off the brow round a head placed by H (the head's frame, figure space, its scale in it:
    body.Frame.head_frame): roomy over the skull, its opening's edge over the crown, behind the ears and round to the
    throat (face.HOOD_*), a rolled hem along it, soft folds hanging from the crown; it ends at z_bot (head space),
    tucked into whatever is worn over the shoulders."""
    Hm = np.array(H, np.float32)
    Hi = np.linalg.inv(Hm)
    s = float(np.cbrt(abs(np.linalg.det(Hm[:3, :3]))))
    R3, t3 = Hi[:3, :3], Hi[:3, 3]
    noise = F._Noise(seed + 311)

    def to_head(Q):
        return Q @ R3.T + t3

    def env(Q):
        P = to_head(Q)
        th = np.arctan2(P[:, 0], P[:, 1] - 0.02)
        fall = np.clip((0.07 - P[:, 2]) / 0.2, 0.0, 1.0)
        d = F.hood_inner(P) + (0.0035 * np.sin(th * 7.0 + 2.5 * noise(P, 16.0)) * fall
                               + 0.0018 * (noise(P, 32.0) - 0.5))
        return d * s

    def t(Q):
        P = to_head(Q)
        hem = np.exp(-(F.hood_front(P) / 0.009) ** 2)
        return (thick + 0.0045 * hem).astype(np.float32)

    def region(Q):
        P = to_head(Q)
        return np.maximum(-F.hood_front(P), z_bot - P[:, 2]) * s

    c = Hm[:3, 3]
    lo = c + np.array((-0.21, -0.22, -0.38)) * s / 1.08
    hi = c + np.array((0.21, 0.27, 0.23)) * s / 1.08
    g = F._Grid(None, None, tuple(lo), tuple(hi), band=(-0.004, 0.016), h=grid, m=4, fn=env)
    return F._mesh(name, *F._nets(g.shell(t, region, inner=0.0, feather=0.002, floor=1.0), g.lo, g.h), mat, tris,
                   smooth_angle=60)


# ------------------------------------------------------------------------------------------------ gear
def _loft(name, centres, across, sections, mat, n=10, back=None, caps=True):
    """A rod through `centres`: section i an ellipse of half-sizes (a, b), a along across[i]; back=(direction, k)
    flattens the side facing that direction by k (a longbow's flat back)."""
    bm = bmesh.new()
    rings = []
    m = len(centres)
    for i in range(m):
        c = Vector(centres[i])
        t = (Vector(centres[min(i + 1, m - 1)]) - Vector(centres[max(i - 1, 0)])).normalized()
        u = Vector(across[i])
        u = (u - t * u.dot(t)).normalized()
        v = t.cross(u)
        a, b = sections[i]
        ring = []
        for k in range(n):
            ang = 2 * math.pi * k / n
            x, y = math.cos(ang) * a, math.sin(ang) * b
            if back is not None and v.dot(Vector(back[0])) * y > 0:
                y *= back[1]
            ring.append(bm.verts.new(c + u * x + v * y))
        rings.append(ring)
    for i in range(m - 1):
        for k in range(n):
            bm.faces.new((rings[i][k], rings[i][(k + 1) % n], rings[i + 1][(k + 1) % n], rings[i + 1][k]))
    if caps:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return K._obj(name, bm, mat)


def longbow(name, grip, up, string_side, length, wood, grip_mat, horn, string_mat, brace=0.155):
    """A braced yew self longbow held at `grip`: the stave runs along `up`, its limbs bending back toward the string
    (on the `string_side`) in a deep, even arc from a stiff handle; a D section (flat back, round belly) 32 mm wide at
    the handle tapering to horn nocks. Returns (parts, top nock, bottom nock)."""
    u = Vector(up).normalized()
    n = Vector(string_side)
    n = (n - u * n.dot(u)).normalized()
    w = u.cross(n)
    l = length / 2.0
    G = Vector(grip)
    N = 45

    def centre(s):
        a = abs(s)
        return G + u * (s * l * (1.0 - 0.045 * a * a)) + n * (brace * max(0.0, (a - 0.08) / 0.92) ** 1.75)
    ss = [-1.0 + 2.0 * i / (N - 1) for i in range(N)]
    cs = [centre(s) for s in ss]
    secs = [(0.016 * (1.0 - 0.6 * abs(s) ** 1.15), 0.0175 * (1.0 - 0.66 * abs(s) ** 1.1)) for s in ss]
    parts = [_loft(name + '_stave', cs, [w] * N, secs, wood, n=10, back=(-n, 0.45))]
    gs = [s for s in ss if abs(s) <= 0.075] or [-0.07, 0.0, 0.07]
    gs = [-0.075] + gs + [0.075]
    parts.append(_loft(name + '_grip', [centre(s) for s in gs], [w] * len(gs),
                       [(0.0185, 0.02)] * len(gs), grip_mat, n=10, back=(-n, 0.5)))
    nocks = []
    for sgn in (1.0, -1.0):
        a, b = centre(0.965 * sgn), centre(sgn)
        tip = b + (b - a).normalized() * 0.03
        parts.append(K.tube(name + '_nock', a, tip, 0.0075, 0.0028, horn, seg=8))
        nocks.append(b + (b - a).normalized() * 0.008 + n * 0.004)
    parts.append(K.tube(name + '_string', nocks[1], nocks[0], 0.0016, 0.0016, string_mat, seg=6))
    return parts, nocks[0], nocks[1]


def arrow(name, nock, direction, fletch, cock, shaft, head, length=0.76, spin=0.0):
    """An arrow from its nock along `direction`: an ash shaft, a slim bodkin point, three fletchings 12 cm long (the
    cock feather in its own colour)."""
    d = Vector(direction).normalized()
    Nk = Vector(nock)
    tip = Nk + d * length
    parts = [K.tube(name + '_shaft', Nk, tip - d * 0.045, 0.0042, 0.004, shaft, seg=6, caps=False),
             K.tube(name + '_head', tip - d * 0.05, tip, 0.0055, 0.0006, head, seg=4)]
    p = d.cross(Vector((0.0, 0.0, 1.0)) if abs(d.z) < 0.9 else Vector((1.0, 0.0, 0.0))).normalized()
    p = Matrix.Rotation(spin, 3, d) @ p
    for k in range(3):
        o = Matrix.Rotation(2 * math.pi * k / 3, 3, d) @ p
        parts.append(K.plate(name + '_vane', [(0.0, 0.0), (0.011, 0.018), (0.013, 0.095), (0.004, 0.12), (0.0, 0.12)],
                             Nk + d * 0.022 + o * 0.0035, d, o, 0.0012, cock if k == 0 else fletch))
    return parts


def quiver(name, bottom, top, leather, rim, fletch, cock, shaft, head, n=12, r_top=0.05, r_bot=0.036, seed=0):
    """A stiff leather quiver from `bottom` to its open `top`, a rolled rim and a laced seam, holding arrows fletching
    up, leaning a little every way in it."""
    B, T = Vector(bottom), Vector(top)
    ax = (T - B).normalized()
    L = (T - B).length
    R = A.frame(ax)
    body = K.lathe(name, [(r_bot * 0.8, 0.0), (r_bot, 0.02), (r_bot * 1.04, 0.3 * L), ((r_bot + r_top) / 2, 0.65 * L),
                          (r_top, L)], leather, seg=20, cap_bottom=True, cap_top=False)
    A.place(body, B, R)
    A.solid(body, 0.004)
    parts = [body, A.place(A.torus(name + '_rim', (0.0, 0.0, 0.0), r_top + 0.002, 0.0055, rim, seg=24, rseg=8), T, R)]
    seam = [B + (R @ Vector((0.0, (r_bot + (r_top - r_bot) * t) * 1.02, t * L)).to_4d()).to_3d() for t in np.linspace(0.05, 0.95, 9)]
    parts.append(A.rivets(name + '_lacing', seam, 0.004, rim))
    rnd = random.Random(seed)
    x_ax = (R @ Vector((1.0, 0.0, 0.0, 0.0))).to_3d()
    y_ax = (R @ Vector((0.0, 1.0, 0.0, 0.0))).to_3d()
    for k in range(n):
        ang, rad = rnd.random() * 6.283, math.sqrt(rnd.random()) * r_top * 0.62
        off = x_ax * math.cos(ang) * rad + y_ax * math.sin(ang) * rad
        lean = (x_ax * (rnd.random() - 0.5) + y_ax * (rnd.random() - 0.5)) * 0.16 + off * 1.2
        d = -(ax + lean).normalized()
        nock = T + off - d * (0.2 + 0.035 * rnd.random())
        parts += arrow(f'{name}_arrow{k}', nock, d, fletch, cock, shaft, head, length=0.74, spin=rnd.random() * 6.0)
    return parts


def boar_spear(name, grip, up, length, shaft, steel, leather, butt_z=0.03, lugs=True):
    """A hunting spear held upright in a fist at `grip`, its butt on the ground: an ash shaft, a leather grip, a broad
    leaf head on a long socket and (lugs) the crossbar that stops a boar on the blade; without it, a war spear."""
    u = Vector(up).normalized()
    G = Vector(grip)
    butt = G - u * ((G.z - butt_z) / max(u.z, 1e-3))
    top = butt + u * length
    parts = [K.tube(name + '_shaft', butt, top, 0.0145, 0.0135, shaft, seg=12),
             K.tube(name + '_wrap', G - u * 0.07, G + u * 0.07, 0.0165, 0.0165, leather, seg=12),
             K.tube(name + '_socket', top - u * 0.02, top + u * 0.1, 0.017, 0.013, steel, seg=10)]
    if lugs:
        lug = K.rbox(name + '_lugs', (0.13, 0.016, 0.016), (0, 0, 0), steel, bev=0.004)
        A.place(lug, top + u * 0.065, A.frame(u, back=(0.0, 1.0, 0.0)))
        parts.append(lug)
    bl = K.blade(name + '_head', 0.3, 0.078, 0.014, steel,
                 secs=[(0.0, 0.3), (0.18, 0.9), (0.38, 1.0), (0.66, 0.72), (1.0, 0.0)])
    A.place(bl, top + u * 0.1, A.frame(u, back=(0.0, 1.0, 0.0)))
    parts.append(bl)
    return parts


def long_knife(name, at, down, leather, wood, steel, brass):
    """A long knife in its sheath, hung from the belt at `at`: the sheath running `down`, the grip and a small brass
    pommel standing above the belt."""
    d = Vector(down).normalized()
    P = Vector(at)
    R = A.frame(d, back=(0.0, 1.0, 0.0))
    sheath = K.lathe(name + '_sheath', [(0.004, 0.3), (0.017, 0.24), (0.021, 0.05), (0.02, 0.0)], leather, seg=12,
                     sx=1.0, sy=0.42, cap_bottom=True, cap_top=True)
    A.place(sheath, P - d * 0.02, R)
    return [sheath, K.tube(name + '_grip', P - d * 0.02, P - d * 0.13, 0.0145, 0.013, wood, seg=10),
            K.sphere(name + '_pommel', P - d * 0.14, 0.017, brass, scale=(1.0, 1.0, 0.8), seg=12, rings=8)]


def lantern(name, bail, iron, horn, flame, light_color, energy=2.2, cross=True):
    """A chapel lantern hanging from a fist at `bail`: a hexagonal iron cage with horn panels lit from within, a
    pierced cone of a cap and a ring to carry it by, a small iron cross on top; a flame and the light it throws.
    horn: the panels' (glowing) material; flame: the flame's. Returns the parts."""
    B = Vector(bail)
    top = B - Vector((0.0, 0.0, 0.045))
    h, r = 0.15, 0.052
    base = top - Vector((0.0, 0.0, h))
    parts = [A.torus(name + '_ring', (0.0, 0.0, 0.0), 0.028, 0.0045, iron, seg=20, rseg=8)]
    A.place(parts[-1], B + Vector((0.0, 0.0, -0.012)), A.frame((1.0, 0.0, 0.0)))
    parts.append(K.tube(name + '_stem', B - Vector((0.0, 0.0, 0.03)), top + Vector((0.0, 0.0, 0.035)), 0.005, 0.005,
                        iron, seg=8))
    parts.append(K.lathe(name + '_cap', [(r * 1.12, 0.0), (r * 0.9, 0.012), (r * 0.35, 0.04), (0.008, 0.05)], iron,
                         seg=6, loc=tuple(top), cap_bottom=True, cap_top=True, smooth=False))
    parts.append(K.lathe(name + '_panes', [(r * 0.96, 0.0), (r, 0.02), (r, h - 0.02), (r * 0.96, h)], horn, seg=6,
                         loc=tuple(base), cap_bottom=True, cap_top=True, smooth=False))
    parts.append(K.lathe(name + '_foot', [(r * 1.1, -0.018), (r * 1.14, -0.006), (r * 1.08, 0.004)], iron, seg=6,
                         loc=tuple(base), cap_bottom=True, cap_top=True, smooth=False))
    for k in range(6):                       # the cage's posts at the corners
        a = math.radians(60.0 * k)
        c = Vector((math.cos(a), math.sin(a), 0.0)) * (r * 1.04)
        parts.append(K.tube(name + '_post', base + c, top + c, 0.0042, 0.0042, iron, seg=6))
    for z in (0.006, h - 0.006):
        parts.append(K.lathe(name + '_band', [(r * 1.06, -0.005), (r * 1.08, 0.0), (r * 1.06, 0.005)], iron, seg=6,
                             loc=tuple(base + Vector((0.0, 0.0, z))), cap_bottom=False, cap_top=False, smooth=False))
    if cross:
        c0 = top + Vector((0.0, 0.0, 0.05))
        parts.append(K.rbox(name + '_cross', (0.009, 0.009, 0.05), tuple(c0 + Vector((0.0, 0.0, 0.025))), iron, bev=0.002))
        parts.append(K.rbox(name + '_crossbar', (0.032, 0.009, 0.009), tuple(c0 + Vector((0.0, 0.0, 0.034))), iron,
                            bev=0.002))
    parts.append(K.sphere(name + '_flame', tuple(base + Vector((0.0, 0.0, h * 0.42))), 0.011, flame,
                          scale=(1.0, 1.0, 1.9), seg=10, rings=8))
    parts.append(K.glow(name + '_light', base + Vector((0.0, 0.0, h * 0.45)), light_color, energy, radius=0.02))
    return parts


ASHFIRE = {       # (core, inner flame, outer flame, halo, light): the living Blight burns violet; a revenant's colder
    False: ('#f3e4ff', '#b77ef7', '#8a45e0', '#7f3fd6', '#b584f5'),
    True: ('#f4f2ff', '#a99af7', '#6a58dc', '#5c4dd0', '#a393f5'),
}


def _blob(name, loc, r, scale, tilt, mat, seg=12, rings=8):
    """An ellipsoid (radius r, scaled) tilted by the Euler angles `tilt` (radians), centred at loc."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    bmesh.ops.scale(bm, vec=scale, verts=bm.verts)
    bmesh.ops.rotate(bm, cent=(0.0, 0.0, 0.0), matrix=Matrix.Rotation(tilt[0], 3, 'X') @ Matrix.Rotation(tilt[1], 3, 'Y'),
                     verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(loc), verts=bm.verts)
    return K._obj(name, bm, mat)


def ashfire(name, at, revenant=False, energy=3.0, seed=0):
    """The Ash Acolyte's ashfire, floating at `at`: a white heart in a knot of violet flame licking upward, a bloom of
    its light round it, embers and flakes of ash turning about it, and the light it throws. Nothing of it casts a
    shadow, so its light reaches the palm under it. Returns the parts."""
    from . import mat as M
    core_c, inner_c, outer_c, halo_c, light_c = ASHFIRE[revenant]
    sfx = '_rev' if revenant else ''
    C = Vector(at)
    rnd = random.Random(seed)
    inner = M.emissive('ashfire_inner' + sfx, inner_c, 1.6)      # kept low enough that the violet doesn't burn to white
    outer = M.emissive('ashfire_outer' + sfx, outer_c, 1.35)
    parts = [K.sphere(name + '_heart', tuple(C), 0.013, M.emissive('ashfire_heart' + sfx, core_c, 5.0), seg=14, rings=10)]
    for k in range(11):         # the flame: narrow tongues close round the heart, broader ones outside, all licking up
        a = 2.0 * math.pi * k / (4 if k < 4 else 7) + rnd.uniform(-0.3, 0.3) + (0.0 if k < 4 else 0.45)
        rr = rnd.uniform(0.004, 0.009) if k < 4 else rnd.uniform(0.014, 0.02)
        off = Vector((math.cos(a) * rr, math.sin(a) * rr, rnd.uniform(0.004, 0.016) if k < 4 else rnd.uniform(-0.008, 0.01)))
        lean = (math.sin(a) * rnd.uniform(0.2, 0.45), -math.cos(a) * rnd.uniform(0.2, 0.45))
        r = rnd.uniform(0.009, 0.012) if k < 4 else rnd.uniform(0.012, 0.017)
        parts.append(_blob(name + '_flame', C + off, r, (1.0, 1.0, rnd.uniform(2.4, 3.2) if k < 4 else rnd.uniform(1.6, 2.3)),
                           lean, inner if k < 4 else outer))
    for r, op, st, hollow in ((0.06, 0.85, 1.4, True), (0.11, 0.38, 1.1, False)):     # its bloom
        parts.append(K.sphere(name + '_halo', tuple(C + Vector((0.0, 0.0, 0.006))), r,
                              M.halo(f'ashfire_halo{r}' + sfx, halo_c, st, op, hollow=hollow), seg=24, rings=14))
    ember = M.emissive('ashfire_ember' + sfx, inner_c, 3.0)
    bm = bmesh.new()
    for k in range(16):         # embers rising off it
        a, rr = rnd.random() * 6.283, rnd.uniform(0.025, 0.075)
        p = C + Vector((math.cos(a) * rr, math.sin(a) * rr, rnd.uniform(-0.01, 0.13)))
        g = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=rnd.uniform(0.0016, 0.0028))
        bmesh.ops.translate(bm, vec=p, verts=g['verts'])
    parts.append(K._obj(name + '_embers', bm, ember))
    bm = bmesh.new()
    for k in range(12):         # and flakes of ash turning round it
        a, rr = rnd.random() * 6.283, rnd.uniform(0.045, 0.095)
        g = bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(rnd.uniform(0.005, 0.009), rnd.uniform(0.004, 0.007), 0.0008), verts=g['verts'])
        bmesh.ops.rotate(bm, cent=(0.0, 0.0, 0.0), matrix=Matrix.Rotation(rnd.random() * 3.0, 3, 'X')
                         @ Matrix.Rotation(rnd.random() * 3.0, 3, 'Z'), verts=g['verts'])
        bmesh.ops.translate(bm, vec=C + Vector((math.cos(a) * rr, math.sin(a) * rr, rnd.uniform(-0.03, 0.08))),
                            verts=g['verts'])
    from . import grit as G
    parts.append(K._obj(name + '_ash', bm, G.flat('ash_flake', '#3a3634')))
    for ob in parts:
        ob.visible_shadow = False
    parts.append(K.glow(name + '_light', C, light_c, energy, radius=0.03))
    return parts


def manacle(name, wrist, axis, iron, links=3, r_in=0.034):
    """A broken iron manacle still locked on a wrist at `wrist`, round the forearm's `axis`: a flat band with its hinge
    and lock, and the links of its chain hanging from it, the last one burst."""
    ax = Vector(axis).normalized()
    Wr = Vector(wrist)
    parts = [A.torus(name, (0.0, 0.0, 0.0), r_in + 0.004, 0.0045, iron, seg=28, rseg=8, rz=0.014, lumpy=0.05, seed=3)]
    A.place(parts[-1], Wr, A.frame(ax))
    down = Vector((0.0, 0.0, -1.0))
    down = down - ax * down.dot(ax)
    down = down.normalized() if down.length > 1e-3 else Vector((0.0, -1.0, 0.0))
    side = ax.cross(down).normalized()
    parts.append(K.rbox(name + '_lock', (0.022, 0.016, 0.03), (0, 0, 0), iron, bev=0.003))
    A.place(parts[-1], Wr + side * (r_in + 0.011), A.frame(ax, back=tuple(side)))
    top = Wr + down * (r_in + 0.011)
    for k in range(links):
        c = top + Vector((0.0, 0.0, -0.012 - 0.021 * k))
        link = A.torus(name + '_link', (0.0, 0.0, 0.0), 0.0085, 0.0028, iron, sy=1.5, seg=16, rseg=6)
        A.place(link, c, A.frame((1.0, 0.0, 0.0) if k % 2 else tuple(ax), back=(0.0, 0.0, 1.0)))
        if k == links - 1:      # the burst link, twisted open
            link.rotation_euler.rotate_axis('Z', 0.5)
        parts.append(link)
    return parts


def strips(name, drape, n, width, z_top, z_bot, mat, lift=0.0, offset=0.0, thick=0.006, jag=0.03, rows=8, seed=0,
           rivet_mat=None):
    """A skirt of hardened leather strips lying on a drape (a closed one, round the hips): n strips `width` wide from
    z_top down to about z_bot, each a little longer or shorter, their feet rounded, a rivet at each foot. `offset` turns
    the ring (degrees); a second ring lifted over the first and offset half a strip closes its gaps."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    rp = []
    for k in range(n):
        a = offset + 360.0 * k / n
        zb = z_bot + rnd.uniform(-jag, jag)
        p0, _ = drape.point(a, z_top, lift)
        hw = math.degrees(width / 2.0 / max(math.hypot(p0.x, p0.y - drape.oy), 0.05))
        grid = []
        for j in range(rows + 1):
            f = j / rows
            row = []
            for s in (-1.0, -0.5, 0.0, 0.5, 1.0):
                z = z_top + (zb - z_top) * f
                if j == rows:                 # a rounded foot
                    z += width * 0.3 * (1.0 - math.cos(s * math.pi / 2.0))
                row.append(bm.verts.new(drape.point(a + s * hw * (1.0 - 0.08 * f), z, lift)[0]))
            grid.append(row)
        for j in range(rows):
            for i in range(4):
                bm.faces.new((grid[j][i], grid[j + 1][i], grid[j + 1][i + 1], grid[j][i + 1]))
        p, nrm = drape.point(a, zb + width * 0.35, lift)
        rp.append(p + nrm * (thick + 0.003))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = K._obj(name, bm, mat)
    A.solid(ob, thick)
    K.bevel(ob, 0.002, 1)
    parts = [ob]
    if rivet_mat is not None:
        parts.append(A.rivets(name + '_rivets', rp, 0.0045, rivet_mat))
    return parts


def cord(name, path, r, mat, closed=False):
    """A rope along `path`: a girdle, a lanyard, a hanging end."""
    pts = [Vector(p) for p in path]
    extra = [(len(pts) - 1, 0)] if closed else ()
    return K.skin_chain(name, pts, [r] * len(pts), mat, levels=1, extra_edges=extra)


def book(name, at, facing, cover, pages, clasp, size=(0.1, 0.034, 0.135)):
    """A small girdle book hanging at `at`, its face turned toward `facing`: leather boards, the page block showing
    at the fore-edge, a clasp."""
    R = A.frame(Vector(facing), back=(0.0, 0.0, 1.0))
    w, t, hgt = size
    parts = [K.rbox(name + '_boards', (w, hgt, t), (0, 0, 0), cover, bev=0.006, segs=2),
             K.rbox(name + '_pages', (w * 0.9, hgt * 0.92, t * 0.78), (0.006, 0, 0), pages, bev=0.002),
             K.rbox(name + '_clasp', (0.014, 0.02, t * 1.08), (w * 0.5 - 0.004, 0, 0), clasp, bev=0.002)]
    for ob in parts:
        A.place(ob, at, R)
    return parts
