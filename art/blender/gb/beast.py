"""Beasts and brutes: the pieces the Blight-hound, the Hound-Rider and the Blight-Troll share (ASSETS.md, the enemy
plan: the quadruped rig, the brute anchor, the seat).

Built the way body.py builds a body: a signed-distance field of anatomical masses (face._cap, _ell, _smin), sampled
on a grid and meshed like the heads and the bodies (face._Grid, _nets, _mesh), wearing the same materials (grit.skin
with rot, in corpse mode).

  Quad            the hound: a deep ribbed chest, a tucked waist, digitigrade legs posed by two-bone IK, a muzzle,
                  pricked ears, a tail; hound() meshes it and adds mangy fur, bone spines, an open flank's ribs, fangs
                  and the two violet eye points. Hound space: metres, paws on z = 0, facing -Y, its left on +X.
  BRUTE, brute()  a third end on the body dial (body.ANCHORS): wide, a huge back, huge hands, a small head
  legs(), Posed   a figure whose legs are posed freely (short and bent under a brute; astride a mount), with its
                  feet where its ankles are (body.field plants every foot on z = 0), and the Dressed body
                  (garb.Dressed) for such a figure, so clothes are laid on it as on any other
  crystal(s)      Blight crystals: faceted prisms that carry the Blight's violet light
  greataxe        a brute's axe: one great bearded blade, a spike behind it
"""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from . import body as BD
from . import face as F
from . import garb as GB
from . import grit as G
from . import kit as K
from . import mat as M


def _v(*a):
    return np.array(a, np.float32)


def ik(a, c, l1, l2, pole):
    """Two bones (lengths l1, l2) from a toward c, the joint between them bending toward `pole`: (joint, end)."""
    a, c = np.asarray(a, np.float32), np.asarray(c, np.float32)
    d = c - a
    n = float(np.linalg.norm(d))
    L = min(n, (l1 + l2) * 0.999)
    u = d / n
    x = (l1 * l1 - l2 * l2 + L * L) / (2.0 * L)
    h = math.sqrt(max(l1 * l1 - x * x, 0.0))
    p = np.asarray(pole, np.float32)
    p = p - u * float(p @ u)
    p = p / np.linalg.norm(p)
    return (a + u * x + p * h).astype(np.float32), (a + u * L).astype(np.float32)


def _rot(axis, deg):
    return np.array(Matrix.Rotation(math.radians(deg), 3, axis), np.float32)


# ------------------------------------------------------------------------------------------------ the quadruped
CHEST_C, CHEST_R = _v(0.0, -0.20, 0.585), _v(0.125, 0.25, 0.185)
RIB_SLANT, RIB_PITCH = 0.35, 0.068


class Quad:
    """One hound in a pose. stride: how far each paw is set forward (m; front left, front right, hind left, hind
    right); head: the skull's centre; pitch, yaw: the head's nose-down and its turn to the hound's left (degrees);
    jaw: how far the mouth hangs open; tail: (sway, lift) of its tip; wound: the flank laid open (+1 left, -1 right,
    0 neither); torn: the ear torn short (+1, -1 or 0)."""

    def __init__(self, stride=(0.07, -0.05, -0.06, 0.07), head=(0.0, -0.60, 0.69), pitch=20.0, yaw=0.0, jaw=16.0,
                 tail=(0.04, 0.0), wound=1, torn=-1):
        self.wound, self.torn, self.jaw = wound, torn, jaw
        J = {}
        for s, side, k in ((1.0, 'l', 0), (-1.0, 'r', 1)):
            S = _v(s * 0.105, -0.35, 0.50)                      # the point of the shoulder
            paw = _v(s * 0.12, -0.36 - stride[k], 0.0)
            el, cp = ik(S, paw + _v(0.0, 0.035, 0.12), 0.16, 0.29, (0.0, 1.0, 0.2))
            J['fs_' + side], J['fe_' + side], J['fc_' + side] = S, el, cp
            J['fp_' + side] = cp + _v(0.0, -0.035, -0.12)
            H = _v(s * 0.085, 0.36, 0.60)                       # the hip
            paw = _v(s * 0.12, 0.44 - stride[k + 2], 0.0)
            st, hk = ik(H, paw + _v(0.0, 0.075, 0.20), 0.25, 0.33, (0.0, -1.0, 0.1))
            J['hh_' + side], J['hs_' + side], J['hk_' + side] = H, st, hk
            J['hp_' + side] = hk + _v(0.0, -0.075, -0.20)
        self.joints = J
        self.O = _v(*head)
        self.Rh = (_rot('Z', yaw) @ _rot('X', pitch)).astype(np.float32)     # columns: the head's axes in hound space
        t0 = _v(0.0, 0.47, 0.68)
        self.tail = [t0, t0 + _v(tail[0] * 0.4, 0.15, -0.13 + tail[1] * 0.4),
                     t0 + _v(tail[0], 0.27, -0.30 + tail[1])]

    def head_pt(self, q):
        """A point of the head's own space (skull centre the origin, the muzzle along -Y) in hound space."""
        return self.O + self.Rh @ np.asarray(q, np.float32)

    def field(self, P):
        """Signed distance to the hound's hide (m) at points P (N, 3)."""
        J = self.joints
        x, y, z = P[:, 0], P[:, 1], P[:, 2]
        Pm = np.column_stack((np.abs(x), y, z))
        # the chest, its ribs standing out of it
        d = F._ell(P, CHEST_C, CHEST_R)
        t = (y + RIB_SLANT * (z - CHEST_C[2]) + 0.40) / RIB_PITCH
        ridge = (0.5 + 0.5 * np.cos(2.0 * np.pi * t)) ** 2
        mask = (np.clip((np.abs(x) - 0.03) / 0.04, 0.0, 1.0) * np.clip((y + 0.39) / 0.04, 0.0, 1.0)
                * np.clip((0.05 - y) / 0.05, 0.0, 1.0) * np.clip((0.72 - z) / 0.04, 0.0, 1.0)
                * np.clip((z - 0.41) / 0.04, 0.0, 1.0))
        d = d - 0.015 * ridge * mask
        # the tucked waist, the pelvis, the backbone standing out along the top, the hip bones, the withers, the
        # shoulder blades
        d = F._smin(d, F._cap(P, _v(0.0, -0.10, 0.62), _v(0.0, 0.30, 0.655), 0.135, 0.088), 0.05)
        d = F._smin(d, F._ell(P, _v(0.0, 0.37, 0.64), _v(0.10, 0.14, 0.115)), 0.04)
        d = F._smin(d, F._cap(P, _v(0.0, -0.30, 0.755), _v(0.0, 0.44, 0.715), 0.028), 0.03)
        d = F._smin(d, F._ell(P, _v(0.0, -0.28, 0.72), _v(0.06, 0.10, 0.07)), 0.03)
        d = F._smin(d, F._ell(Pm, _v(0.07, 0.32, 0.725), _v(0.03, 0.045, 0.03)), 0.02)
        d = F._smin(d, F._ell(Pm, _v(0.108, -0.30, 0.63), _v(0.035, 0.075, 0.14), M=F._R(rx=-18.0)), 0.025)
        # the neck and the head
        d = F._smin(d, F._cap(P, _v(0.0, -0.36, 0.665), self.head_pt((0.0, 0.06, -0.015)), 0.10, 0.062), 0.04)
        d = F._smin(d, self._head(P), 0.02)
        # the legs
        for s, side in ((1.0, 'l'), (-1.0, 'r')):
            S, el, cp, fp = (J[k + side] for k in ('fs_', 'fe_', 'fc_', 'fp_'))
            g = F._cap(P, S, el, 0.055, 0.042)
            g = F._smin(g, F._cap(P, el, cp, 0.045, 0.03), 0.02)
            g = F._smin(g, F._cap(P, cp, fp + _v(0.0, -0.005, 0.03), 0.026, 0.03), 0.012)
            g = F._smin(g, F._ell(P, fp + _v(0.0, -0.03, 0.028), _v(0.04, 0.06, 0.03)), 0.015)
            d = F._smin(d, g, 0.03)
            H, st, hk, hp = (J[k + side] for k in ('hh_', 'hs_', 'hk_', 'hp_'))
            g = F._cap(P, H, st, 0.085, 0.05)
            g = F._smin(g, F._ell(P, (H + st) / 2.0 + _v(s * 0.012, 0.03, 0.02), _v(0.055, 0.10, 0.13)), 0.03)
            g = F._smin(g, F._cap(P, st, hk, 0.045, 0.022), 0.02)
            g = F._smin(g, F._cap(P, hk, hp + _v(0.0, 0.0, 0.035), 0.021, 0.027), 0.012)
            g = F._smin(g, F._ell(P, hp + _v(0.0, -0.03, 0.026), _v(0.038, 0.058, 0.028)), 0.015)
            d = F._smin(d, g, 0.03)
        # the tail
        t0, t1, t2 = self.tail
        d = F._smin(d, F._cap(P, t0 + _v(0.0, -0.05, 0.0), t1, 0.034, 0.021), 0.03)
        d = F._smin(d, F._cap(P, t1, t2, 0.021, 0.009), 0.012)
        if self.wound:      # the flank laid open
            pit = F._ell(P, CHEST_C + _v(self.wound * 0.125, 0.07, 0.0), _v(0.045, 0.10, 0.085))
            d = F._smax(d, -pit, 0.008)
        return F._smax(d, 0.002 - z, 0.004)

    def _head(self, P):
        Q = ((P - self.O) @ self.Rh).astype(np.float32)
        Qm = np.column_stack((np.abs(Q[:, 0]), Q[:, 1], Q[:, 2]))
        h = F._ell(Q, _v(0.0, 0.0, 0.0), _v(0.07, 0.09, 0.064))
        h = F._smin(h, F._ell(Q, _v(0.0, -0.07, 0.012), _v(0.055, 0.045, 0.036)), 0.02)             # the brow
        h = F._smin(h, F._cap(Q, _v(0.0, -0.07, -0.012), _v(0.0, -0.235, -0.03), 0.046, 0.031), 0.02)   # the muzzle
        h = F._smin(h, F._ell(Q, _v(0.0, -0.262, -0.02), _v(0.022, 0.02, 0.018)), 0.008)            # the nose
        h = F._smin(h, F._ell(Qm, _v(0.048, -0.01, -0.028), _v(0.03, 0.05, 0.04)), 0.02)            # the cheeks
        Qj = ((Q - self.JAW) @ _rot('X', self.jaw)).astype(np.float32)                              # the jaw, hung open
        h = F._smin(h, F._cap(Qj, _v(0.0, -0.01, -0.008), _v(0.0, -0.215, -0.03), 0.027, 0.019), 0.012)
        for s in (1.0, -1.0):                                                                       # the ears
            k = 0.55 if s == self.torn else 1.0
            a = _v(s * 0.05, 0.035, 0.045)
            h = F._smin(h, F._cap(Q, a, a + _v(s * 0.028, 0.04, 0.095) * k, 0.026, 0.005 + 0.012 * (1.0 - k)), 0.012)
        sock = np.linalg.norm(Qm - self.EYE, axis=1) - 0.015
        return F._smax(h, -sock, 0.004)

    JAW = _v(0.0, -0.005, -0.045)
    EYE = _v(0.036, -0.088, 0.03)

    def top(self, y, x=0.0):
        """The height of the back at (x, y)."""
        zs = np.arange(1.1, 0.2, -0.004, dtype=np.float32)
        d = self.field(np.column_stack((np.full(len(zs), x), np.full(len(zs), y), zs)).astype(np.float32))
        hit = np.nonzero(d < 0.0)[0]
        return float(zs[hit[0]]) if len(hit) else 0.7

    def side(self, y, z):
        """Half the hound's width at (y, z)."""
        xs = np.arange(0.5, 0.0, -0.004, dtype=np.float32)
        d = self.field(np.column_stack((xs, np.full(len(xs), y), np.full(len(xs), z))).astype(np.float32))
        hit = np.nonzero(d < 0.0)[0]
        return float(xs[hit[0]]) if len(hit) else 0.1


def _cone(name, base, axis, length, r, mat, seg=6):
    ob = K.tube(name, Vector(base) - Vector(axis) * (0.25 * length), Vector(base) + Vector(axis) * length, r, 0.0015,
                mat, seg=seg)
    ob.data.shade_flat()
    return ob


def hound(name, q, hide, fur, bone, seed=0, spines=1.0, eye='#9a5cf0', glow=1.0, grid=0.004, patch=0.5):
    """Mesh a Quad and dress it: mangy fur in patches (heaviest on the neck and along the back), bone spines down the
    spine (spines: their length; 0 for none), the bared ribs of an open flank, fangs, and two violet eye points.
    Returns (parts, info): info['eyes'], the eyes in hound space."""
    rnd = np.random.default_rng(seed)
    g = F._Grid(None, None, (-0.36, -0.98, -0.01), (0.36, 0.92, 1.0), band=(-0.012, 0.03), h=grid, m=4, fn=q.field)
    parts = [F._mesh(name, *F._nets(g.D, g.lo, g.h), hide, 16000, smooth_angle=50)]
    nz, nz2 = F._Noise(seed + 3), F._Noise(seed + 4)

    def fur_region(P):
        z, y = P[:, 2], P[:, 1]
        mane = np.clip((z - 0.52) / 0.2, 0.0, 1.0) * (0.12 + 0.4 * np.clip((-0.2 - y) / 0.15, 0.0, 1.0))
        r = (patch + 0.12) - nz(P, 6.0) - mane
        Q = (P - q.O) @ q.Rh
        r = np.maximum(r, (-0.04 - Q[:, 1]) * 3.0)          # none on the face
        r = np.maximum(r, (0.635 - z) * 3.0)                # nor on the flanks and legs: the ribs and the hide show
        return (r * 0.1).astype(np.float32)
    sh = g.shell(lambda P: (0.008 + 0.016 * nz2(P, 38.0)).astype(np.float32), fur_region, inner=0.003, feather=0.006,
                 floor=0.25)
    parts.append(F._mesh(name + '_fur', *F._nets(sh, g.lo, g.h), fur, 9000, smooth_angle=40))

    if spines > 0:          # bone spines burst through along the spine, longest over the withers
        ys = np.linspace(-0.44, 0.40, 10)
        for i, y in enumerate(ys):
            y = float(y + rnd.uniform(-0.015, 0.015))
            L = spines * (0.05 + 0.1 * math.exp(-((y + 0.2) / 0.22) ** 2)) * rnd.uniform(0.75, 1.2)
            ax = Vector((rnd.uniform(-0.18, 0.18), 0.45 + rnd.uniform(-0.1, 0.15), 1.0)).normalized()
            parts.append(_cone('spine', (0.0, y, q.top(y) - 0.01), ax, L, 0.012 + 0.09 * L, bone))
    if q.wound:             # the ribs bared in the open flank, the dark of the chest behind them
        dark = G.flat('hound_gore', '#1a0d0e')
        parts.append(K.sphere(name + '_gore', tuple(CHEST_C), 1.0, dark, scale=tuple(CHEST_R * 0.87)))
        for k in range(4):
            yk = -0.215 + RIB_PITCH * k
            path = []
            for ph in np.linspace(-48.0, 44.0, 9):
                zz = CHEST_C[2] + CHEST_R[2] * 0.97 * math.sin(math.radians(ph))
                yy = yk - RIB_SLANT * (zz - CHEST_C[2])
                sc = math.sqrt(max(1.0 - ((yy - CHEST_C[1]) / CHEST_R[1]) ** 2, 0.05))
                path.append((q.wound * CHEST_R[0] * 0.97 * sc * math.cos(math.radians(ph)), yy,
                             CHEST_C[2] + (zz - CHEST_C[2]) * sc))
            parts.append(GB.cord('rib', path, 0.011, bone))
    for s in (1.0, -1.0):   # fangs
        parts.append(_cone('fang', q.head_pt((s * 0.021, -0.222, -0.05)), Vector(q.Rh @ _v(0.0, -0.1, -1.0)).normalized(),
                           0.034, 0.008, bone, seg=5))
        low = q.JAW + _rot('X', q.jaw) @ _v(s * 0.016, -0.2, -0.012)
        parts.append(_cone('fang', q.head_pt(low), Vector(q.Rh @ _rot('X', q.jaw) @ _v(0.0, -0.1, 1.0)).normalized(),
                           0.026, 0.0065, bone, seg=5))
    eyes = []
    em = M.emissive(name + '_eye', eye, 3.2 * glow)
    bloom = M.halo(name + '_eye_bloom', eye, 1.3 * glow, 0.6, 1.6)
    for s in (1.0, -1.0):
        e = Vector(q.head_pt(q.EYE * _v(s, 1.0, 1.0)))
        eyes.append(e)
        parts.append(K.sphere('eye', tuple(e), 0.012, em, seg=12, rings=8))
        b = K.sphere('eye_bloom', tuple(e + Vector(q.Rh @ _v(0.0, -0.008, 0.006))), 0.022, bloom, seg=16, rings=10)
        b.visible_shadow = False
        parts.append(b)
    parts.append(K.glow('eye_glow', Vector(q.head_pt((0.0, -0.16, 0.08))), eye, 0.06 * glow, radius=0.012))
    return parts, dict(eyes=eyes)


# ------------------------------------------------------------------------------------------------ the brute anchor
# A third end on the body dial (body.ANCHORS' keys): wide and deep, a huge upper back, a gut, shoulders half as wide
# again, arms like thighs, huge hands and feet, a thick neck, and a small head for its body.
BRUTE = dict(
    height=1.0,
    tw=[0.215, 0.235, 0.24, 0.245, 0.25, 0.27, 0.305, 0.33, 0.335, 0.30, 0.165],
    tf=[0.11, 0.14, 0.17, 0.19, 0.19, 0.185, 0.18, 0.17, 0.15, 0.11, 0.075],
    tb=[0.13, 0.14, 0.13, 0.125, 0.13, 0.15, 0.175, 0.195, 0.195, 0.16, 0.10],
    pecs=1.0, bust=0.0, seat=0.0, hipmass=0.0, back=1.0, traps=2.2,
    shoulder=0.36, deltoid=0.115, arm=[0.105, 0.082, 0.10, 0.07], hand=[0.36, 0.17],
    hip=0.14, leg=[0.15, 0.13, 0.095, 0.10, 0.066], foot=[0.27, 0.10],
    neck=0.09, knee_in=0.0, head=0.82)


def brute(amount=1.0):
    """The settings of a body `amount` of the way from the male anchor to the brute (body.form's kind of dict)."""
    m = BD.ANCHORS['male']
    f = {}
    for k in m:
        if isinstance(m[k], list):
            f[k] = [a + (b - a) * amount for a, b in zip(m[k], BRUTE[k])]
        else:
            f[k] = m[k] + (BRUTE[k] - m[k]) * amount
    return f


def legs(P, fr, feet=None, foot=1.0):
    """The legs of a posed figure, from its joints as they are (hp, kn, an: set them freely, e.g. by ik()), each foot
    at its own ankle. feet: side -> (toe direction, up) of a foot not flat on the ground (a rider's); foot: the feet's
    size (the ankle stands 0.085 * foot over the sole)."""
    f, J = fr.f, fr.joints
    l0, l1, l2, l3, l4 = f['leg']
    out = None
    for side, s in (('l', 1.0), ('r', -1.0)):
        hp, kn, an = J['hp_' + side], J['kn_' + side], J['an_' + side]
        th, sk = kn - hp, an - kn
        lt, ls = float(np.linalg.norm(th)), float(np.linalg.norm(sk))
        ha = an - hp
        fwd = kn - (hp + ha * float(th @ ha) / float(ha @ ha))        # the way the knee bends: the leg's front
        fwd = fwd / np.linalg.norm(fwd) if np.linalg.norm(fwd) > 1e-3 else _v(0.0, -1.0, 0.0)
        Mt, Ms = BD._axes(th), BD._axes(sk)
        d = F._cap(P, hp, kn, l0, l2 * 1.05)
        d = F._smin(d, F._ell(P, hp + th * 0.42 + fwd * l1 * 0.28, _v(l1 * 0.92, l1 * 0.92, lt * 0.33), M=Mt), 0.02)
        d = F._smin(d, F._ell(P, hp + th * 0.4 - fwd * l1 * 0.32, _v(l1 * 0.8, l1 * 0.8, lt * 0.34), M=Mt), 0.02)
        d = F._smin(d, F._cap(P, kn, an, l2 * 0.92, l4), 0.02)
        d = F._smin(d, F._ell(P, kn + sk * 0.28 - fwd * l3 * 0.38, _v(l3 * 0.9, l3 * 0.9, ls * 0.3), M=Ms), 0.02)
        toe, up = (feet or {}).get(side, (_v(0.0, -1.0, 0.0), _v(0.0, 0.0, 1.0)))
        toe, up = np.asarray(toe, np.float32), np.asarray(up, np.float32)
        up = up / np.linalg.norm(up)
        toe = toe - up * float(toe @ up)
        toe = toe / np.linalg.norm(toe)
        Rf = np.column_stack((np.cross(-toe, up), -toe, up)).astype(np.float32)
        Q = ((P - an) @ Rf / foot + _v(0.0, 0.0, 0.085)).astype(np.float32)
        ft = BD._foot(Q, _v(0.0, 0.0, 0.085), s, f['foot'][0], f['foot'][1]) * foot
        d = F._smin(d, ft, 0.02 * foot)
        out = d if out is None else np.minimum(out, d)
    return out


def figure_field(fr, feet=None, foot=1.0):
    """The field of a figure posed with legs(): body.field without its legs, and these."""
    def fn(P, arms=True):
        return F._smin(BD.field(P, fr, arms=arms, legs=False), legs(P, fr, feet, foot), 0.03)
    return fn


class Posed(GB.Dressed):
    """garb.Dressed for a figure with a field of its own (figure_field): the same garments, belts and drapes."""

    def __init__(self, fr, fn, lo, hi, grid=0.004):
        self.fr, self.fn = fr, fn
        self.g = F._Grid(None, None, tuple(lo), tuple(hi), band=(-0.012, 0.04), h=grid, m=4, fn=fn)
        self._nets = {}

    def outer(self, O, dirs, clear, arms=True):
        O = np.asarray(O, np.float32)
        dirs = np.asarray(dirs, np.float32)
        r = np.full(len(O), 1.4, np.float32)
        hit = np.zeros(len(O), bool)
        live = np.ones(len(O), bool)
        for _ in range(400):
            idx = np.nonzero(live)[0]
            if not len(idx):
                break
            d = self.fn(O[idx] + dirs[idx] * r[idx, None], arms=arms) - clear
            h = d < 5e-4
            hit[idx[h]] = True
            rr = r[idx] - np.maximum(d * 0.8, 0.0015)
            r[idx] = np.where(h, r[idx], rr)
            live[idx[h | (rr <= 0.0)]] = False
        return np.where(hit, r, 0.0)


# ------------------------------------------------------------------------------------------------ Blight crystals
def crystal_mat(name='blight_crystal', color='#8a4ae8', strength=0.95):
    """A Blight crystal: dark violet glass lit from within, each facet at its own brightness (brightest face-on), and
    kept below the point where it burns to white."""
    key = (name, 'crystal')
    hit = M._CACHE.get(key)
    if hit:
        return hit
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*M.hexlin('#3a1f66'), 1.0)
    b.inputs['Roughness'].default_value = 0.22
    b.inputs['Emission Color'].default_value = (*M.hexlin(color), 1.0)
    lw = nt.nodes.new('ShaderNodeLayerWeight')
    lw.inputs['Blend'].default_value = 0.5
    nt.links.new(M._maprange(nt, lw.outputs['Facing'], 0.05, 0.7, strength * 1.3, strength * 0.28),
                 b.inputs['Emission Strength'])
    M._CACHE[key] = m
    return m


def crystal(name, base, axis, length, r, mat, sides=6, twist=0.0):
    """One crystal: a prism of `sides` faces from under `base` along `axis`, cut to a point."""
    rot = K.z_to(axis)
    bm = bmesh.new()
    rings = []
    for z, k in ((-0.3 * length, 0.85), (0.0, 1.0), (0.72 * length, 0.8)):
        rings.append([bm.verts.new((r * k * math.cos(twist + 2.0 * math.pi * i / sides),
                                    r * k * math.sin(twist + 2.0 * math.pi * i / sides), z)) for i in range(sides)])
    tip = bm.verts.new((r * 0.12, 0.0, length))
    for a, b in zip(rings, rings[1:]):
        for i in range(sides):
            bm.faces.new((a[i], a[(i + 1) % sides], b[(i + 1) % sides], b[i]))
    for i in range(sides):
        bm.faces.new((rings[-1][i], rings[-1][(i + 1) % sides], tip))
    bm.faces.new(list(reversed(rings[0])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(base)) @ rot, verts=bm.verts)
    return K._obj(name, bm, mat, smooth=False)


def crystals(name, base, axis, length, r, mat, n=3, seed=0):
    """A cluster: one great crystal along `axis` and n lesser ones splayed round its foot."""
    rnd = np.random.default_rng(seed)
    axis = Vector(axis).normalized()
    parts = [crystal(name, base, axis, length, r, mat, twist=float(rnd.uniform(0.0, 1.0)))]
    side = axis.orthogonal().normalized()
    for k in range(n):
        a = 2.0 * math.pi * (k + rnd.uniform(-0.25, 0.25)) / n
        lean = Matrix.Rotation(a, 3, axis) @ side
        ax = (axis + lean * rnd.uniform(0.45, 0.8)).normalized()
        parts.append(crystal(name, Vector(base) + lean * r * 0.7, ax, length * rnd.uniform(0.35, 0.62),
                             r * rnd.uniform(0.45, 0.65), mat, twist=float(rnd.uniform(0.0, 1.0))))
    return parts


# ------------------------------------------------------------------------------------------------ the greataxe
def greataxe(prefix, hand, direction, mats, haft=1.45, below=0.45, scale=1.0, outward=(-1.0, 0.0, 0.0)):
    """A brute's greataxe gripped at `hand`, its haft along `direction` (`below` of it under the fist): one great
    bearded blade toward `outward`, a spike behind it, iron langets down the haft. mats = (iron, wood, leather)."""
    iron, wood, leather = mats
    d, o, n = K._basis(direction, outward)
    hand = Vector(hand)
    butt = hand - d * below
    top = butt + d * haft
    s = scale
    parts = [K.tube(prefix + '_haft', butt, top, 0.024, 0.022, wood, seg=10),
             K.tube(prefix + '_wrap', hand - d * 0.09, hand + d * 0.09, 0.027, 0.027, leather, seg=10),
             K.tube(prefix + '_shoe', butt - d * 0.02, butt + d * 0.06, 0.028, 0.027, iron, seg=10)]
    at = top - d * (0.2 * s)
    blade = [(0.0, 0.10), (0.07, 0.115), (0.17, 0.2), (0.25, 0.17), (0.285, 0.06), (0.29, -0.06), (0.25, -0.2),
             (0.17, -0.26), (0.09, -0.14), (0.0, -0.11)]
    parts.append(K.plate(prefix + '_blade', [(u * s, z * s) for u, z in blade], at, d, o, 0.024, iron))
    spike = [(0.0, 0.05), (-0.06, 0.055), (-0.16, 0.0), (-0.06, -0.055), (0.0, -0.05)]
    parts.append(K.plate(prefix + '_spike', [(u * s, z * s) for u, z in spike], at, d, o, 0.03, iron))
    parts.append(K.tube(prefix + '_socket', at - d * (0.13 * s), at + d * (0.13 * s), 0.034, 0.032, iron, seg=10))
    parts.append(K.tube(prefix + '_langet', at - d * (0.36 * s), at - d * (0.13 * s), 0.0265, 0.03, iron, seg=10))
    return parts
