"""Bodies: one construction for every humanoid, a male and a female anchor on one dial.

As with the faces (face.form), sex is the settings' ends, not two models. Following the body dimorphism guide:
  him: shoulders significantly wider, with more trapezius; a deeper, wider rib cage; a waist that tapers less;
       narrower hips and a flatter seat; a larger upper back; thicker arms and legs; larger hands and feet
  her: shoulders narrower and sloping; a shallower, narrower rib cage; a defined waist; a wider pelvis with more mass
       at the hip; more lumbar curve and a fuller seat; slimmer limbs with softer transitions; knees a touch closer
       together; smaller hands and feet; 92% of his height, her head 97% of his: 7.6 of her heads to his 8
Widths are absolute (m): adult averages pushed a little toward the strong end, as a mercenary's would be.

A Frame is one body: its settings, its height, its torso's cross-sections at each level, its joints in a pose, and
where its head sits. Kits are built on it. fighter.py lays the Line-Breaker's armour on the male anchor's dimensions
plus the difference a body makes at each level (Frame.dw, and friends), so the plate keeps its clearance over any
body and his armour never moves. A Frame can be posed: reach() bends an arm so its hand lands where a kit needs it
(on a bow's grip, a spear's shaft), and a gripping hand closes into a fist round what it holds. gb/garb.py lays
clothes over the posed body itself (the Ranger).

For review, bare() builds the body itself: a signed-distance field of anatomical masses (a torso lofted through the
cross-sections; pecs or bust, seat, hip, back, traps and deltoids on it; limbs as capsules with their muscle bellies;
hands and feet), meshed like the heads (face._Grid), with the head plugged in by its own neck (its shoulders left
to the body), and dressed as on the reference sheet, in a chest wrap and shorts.

Figure space: metres, feet on z = 0, facing -Y, the figure's left on +X. Heights are given on the male anchor; a body
puts each at that height times its own (Frame.hf).
"""
import math

import numpy as np
from mathutils import Matrix, Vector

from . import face as F

# the torso's measured levels (m, on the male anchor): the seat, the hips (greater trochanters), the iliac crest,
# the lower belly, the natural waist, the lower ribs, the mid chest, the armpits, the upper chest, the shoulder
# girdle, the base of the neck
U = [0.90, 0.95, 1.02, 1.10, 1.17, 1.24, 1.32, 1.38, 1.43, 1.48, 1.52]

ANCHORS = {
    'male': dict(
        height=1.0,
        tw=[0.150, 0.165, 0.155, 0.148, 0.145, 0.155, 0.170, 0.180, 0.180, 0.160, 0.090],   # half-width at each level
        tf=[0.080, 0.095, 0.100, 0.105, 0.105, 0.110, 0.120, 0.125, 0.115, 0.085, 0.060],   # depth in front of the axis
        tb=[0.100, 0.110, 0.095, 0.088, 0.088, 0.092, 0.100, 0.105, 0.100, 0.085, 0.070],   # depth behind it
        pecs=1.0, bust=0.0, seat=0.0, hipmass=0.0, back=1.0, traps=1.0,
        shoulder=0.19,                          # the head of the humerus, off the midline
        deltoid=0.064,
        arm=[0.056, 0.042, 0.049, 0.031],       # radii: upper arm, elbow, forearm, wrist
        hand=[0.19, 0.088],                     # length, breadth
        hip=0.09,                               # the head of the femur, off the midline
        leg=[0.085, 0.070, 0.052, 0.058, 0.034],    # radii: top of the thigh, mid-thigh, knee, calf, ankle
        foot=[0.27, 0.10],                      # length, breadth
        neck=0.058, knee_in=0.0,                # knee_in: how far the knees sit inside the hip-to-ankle line
        head=1.0),                              # the head's size on the body (her head is a shade larger for her body)
    'female': dict(
        height=0.92,
        tw=[0.155, 0.178, 0.162, 0.136, 0.120, 0.130, 0.143, 0.152, 0.150, 0.130, 0.075],
        tf=[0.080, 0.095, 0.098, 0.095, 0.088, 0.090, 0.095, 0.100, 0.095, 0.070, 0.050],
        tb=[0.110, 0.120, 0.100, 0.080, 0.078, 0.080, 0.088, 0.090, 0.085, 0.070, 0.060],
        pecs=0.0, bust=1.0, seat=1.0, hipmass=1.0, back=0.55, traps=0.55,
        shoulder=0.158, deltoid=0.048, arm=[0.044, 0.034, 0.038, 0.025], hand=[0.17, 0.076],
        hip=0.095, leg=[0.088, 0.070, 0.048, 0.053, 0.030], foot=[0.24, 0.088], neck=0.047, knee_in=0.02, head=1.05),
}
# The guide's variation row, as offsets on either anchor (form(dial, offsets)): the same construction, a different
# build. Fat goes where the guide puts it: his to the belly and chest, hers to the hips, thighs and lower belly.
VARIATIONS = {
    'lean':  {'m': dict(tw=[-0.01, -0.01, -0.014, -0.016, -0.016, -0.012, -0.006, -0.002, 0, 0, 0], tf=[0, 0, -0.012, -0.014, -0.014, -0.008, 0, 0, 0, 0, 0],
                        arm=[-0.008, -0.005, -0.006, -0.003], leg=[-0.012, -0.01, -0.004, -0.007, -0.003], deltoid=-0.006, neck=-0.004),
              'f': dict(tw=[-0.012, -0.014, -0.012, -0.01, -0.008, -0.005, 0, 0, 0, 0, 0], tf=[0, 0, -0.01, -0.01, -0.008, 0, 0, 0, 0, 0, 0],
                        arm=[-0.006, -0.004, -0.005, -0.003], leg=[-0.014, -0.012, -0.004, -0.007, -0.003], neck=-0.003, hipmass=-0.5, seat=-0.4)},
    'heavy': {'m': dict(tw=[0.016, 0.022, 0.032, 0.042, 0.046, 0.04, 0.028, 0.018, 0.014, 0.008, 0.004],
                        tf=[0.006, 0.016, 0.038, 0.05, 0.048, 0.036, 0.024, 0.016, 0.008, 0, 0], tb=[0.008, 0.008, 0.01, 0.012, 0.012, 0.012, 0.01, 0.008, 0.006, 0, 0],
                        arm=[0.012, 0.007, 0.009, 0.004], leg=[0.018, 0.016, 0.007, 0.011, 0.004], neck=0.01, deltoid=0.008),
              'f': dict(tw=[0.018, 0.024, 0.022, 0.018, 0.014, 0.012, 0.01, 0.008, 0.006, 0.004, 0.002],
                        tf=[0.006, 0.014, 0.022, 0.02, 0.014, 0.01, 0.008, 0.006, 0.004, 0, 0], tb=[0.012, 0.014, 0.01, 0.006, 0.006, 0.006, 0.006, 0.004, 0.002, 0, 0],
                        arm=[0.006, 0.003, 0.004, 0.002], leg=[0.016, 0.014, 0.005, 0.008, 0.003], neck=0.004, hipmass=0.3, seat=0.2)},
    'tall':  {'m': dict(height=0.06), 'f': dict(height=0.06)},
    'short': {'m': dict(height=-0.06), 'f': dict(height=-0.06)},
}
HEAD_C = (0.0, -0.012, 1.715)      # where the head's centre sits on the male anchor
HEAD_SCALE = 1.08                  # heads a touch large, so faces read on the board
HEAD_TILT = -10.0                  # in battle, chin up: unflinching, and it turns the face toward the camera


def form(dial, offsets=None):
    """The settings for one body on the dial between the anchors (0 male, 1 female), plus per-setting offsets."""
    m, w = ANCHORS['male'], ANCHORS['female']
    f = {}
    for k in m:
        if isinstance(m[k], list):
            f[k] = [a + (b - a) * dial for a, b in zip(m[k], w[k])]
        else:
            f[k] = m[k] + (w[k] - m[k]) * dial
    for k, v in (offsets or {}).items():
        f[k] = [a + b for a, b in zip(f[k], v)] if isinstance(f[k], list) else f[k] + v
    return f


def _settings(sex_or_form):
    return form(0.0 if sex_or_form == 'male' else 1.0) if isinstance(sex_or_form, str) else sex_or_form


class Frame:
    """One body: settings, height, torso sections, joints (the reference sheet's standing pose) and head placement."""

    def __init__(self, sex):
        self.sex = sex if isinstance(sex, str) else None
        self.f = f = _settings(sex)
        self.hf = f['height']
        sh, hp, kin = f['shoulder'], f['hip'], f['knee_in']
        J = {}
        for s, side in ((1.0, 'l'), (-1.0, 'r')):       # arms a little away from the body, feet a little apart
            J['sh_' + side] = (s * sh, 0.005, 1.44)
            J['el_' + side] = (s * (sh + 0.045), 0.025, 1.155)
            J['wr_' + side] = (s * (sh + 0.07), 0.0, 0.905)
            J['hp_' + side] = (s * hp, 0.01, 0.965)
            J['kn_' + side] = (s * (hp + 0.012 - kin), -0.005, 0.5)
            J['an_' + side] = (s * (hp + 0.02), 0.02, 0.085)
        self.joints = {k: np.array((x, y, z * self.hf), np.float32) for k, (x, y, z) in J.items()}
        self.grip = {}      # side -> the direction of what that hand holds (a bow's stave, a spear): a fist round it

    def reach(self, side, wrist, pole=(0.0, 0.3, -1.0), grip=None):
        """Pose an arm ('l' or 'r') so its wrist lands on `wrist` (figure space; pulled in along the line if out of
        reach), keeping the arm's own lengths, the elbow bending toward `pole`. grip: the direction of a shaft the
        hand closes round."""
        J = self.joints
        sh = J['sh_' + side]
        lu = float(np.linalg.norm(J['el_' + side] - sh))
        lf = float(np.linalg.norm(J['wr_' + side] - J['el_' + side]))
        d = np.asarray(wrist, np.float32) - sh
        L = min(float(np.linalg.norm(d)), (lu + lf) * 0.999)
        u = d / np.linalg.norm(d)
        a = (lu * lu - lf * lf + L * L) / (2.0 * L)          # the elbow's foot on the shoulder-wrist line
        h = math.sqrt(max(lu * lu - a * a, 0.0))
        p = np.asarray(pole, np.float32)
        p = p - u * float(p @ u)
        p = p / np.linalg.norm(p)
        J['el_' + side] = (sh + u * a + p * h).astype(np.float32)
        J['wr_' + side] = (sh + u * L).astype(np.float32)
        if grip is not None:
            self.grip[side] = np.asarray(grip, np.float32) / np.linalg.norm(grip)
        return J['wr_' + side]

    def fist(self, side):
        """Where a gripping hand's fist closes (the centre of what it holds), figure space."""
        J = self.joints
        wr, el = J['wr_' + side], J['el_' + side]
        hd = (wr - el) / np.linalg.norm(wr - el)
        hl, hb = self.f['hand']
        return wr + hd * hl * 0.36 + self._palm(side, hd) * hb * 0.2

    def _palm(self, side, hd):
        """The direction the palm faces on a gripping hand: toward the body's midline, square to the forearm."""
        g = self.grip.get(side, np.array((0.0, 0.0, 1.0), np.float32))
        n = np.cross(g, hd) * (-1.0 if side == 'l' else 1.0)
        return n / max(np.linalg.norm(n), 1e-6)

    def torso(self, u):
        """Half-width, front depth and back depth of the torso at level u (on the male anchor's scale)."""
        f = self.f
        return np.interp(u, U, f['tw']), np.interp(u, U, f['tf']), np.interp(u, U, f['tb'])

    def hips(self):
        """Half the width across the hips: the greater trochanters, with the lateral hip mass over them."""
        f = self.f
        return max(float(np.interp(0.95, U, f['tw'])), f['hip'] + f['leg'][0]) + 0.012 * f['hipmass']

    def dw(self, u):
        """How much wider (half-width, m) this torso is than the male anchor's at level u."""
        return float(self.torso(u)[0] - _male().torso(u)[0])

    def dd(self, u, side='both'):
        """How much deeper this torso is than the male anchor's at level u: in front, behind, or half the two."""
        a, m = self.torso(u), _male().torso(u)
        if side == 'front':
            return float(a[1] - m[1])
        if side == 'back':
            return float(a[2] - m[2])
        return float((a[1] + a[2] - m[1] - m[2]) / 2.0)

    def d(self, key, i=None):
        """How much larger a setting (or its i-th value) is than on the male anchor."""
        a, m = self.f[key], _male().f[key]
        return (a[i] - m[i]) if i is not None else (a - m)

    def ratio(self, key, i=0):
        a, m = self.f[key], _male().f[key]
        return (a[i] / m[i]) if isinstance(a, list) else a / m

    @property
    def head_scale(self):
        return HEAD_SCALE * self.f['head']

    def head_frame(self, portrait=False):
        """Where the head sits (figure space): on the neck, chin a touch up in battle, level in portraits."""
        x, y, z = HEAD_C
        return (Matrix.Translation(Vector((x, y, z * self.hf)))
                @ Matrix.Rotation(math.radians(0.0 if portrait else HEAD_TILT), 4, 'X') @ Matrix.Scale(self.head_scale, 4))


_MALE = []


def _male():
    if not _MALE:
        _MALE.append(Frame('male'))
    return _MALE[0]


# ------------------------------------------------------------------------------------------------ the bare body
def _axes(z):
    """A rotation (numpy, local = (p - c) @ M) whose local Z is the unit vector z."""
    z = z / np.linalg.norm(z)
    x = np.cross((0.0, 1.0, 0.0), z) if abs(z[1]) < 0.9 else np.cross((1.0, 0.0, 0.0), z)
    x /= np.linalg.norm(x)
    return np.column_stack((x, np.cross(z, x), z)).astype(np.float32)


def _hand(P, wr, hd, s, hl, hb):
    """A relaxed hand hanging palm-in: the palm, the fingers curled a little in toward the thigh, the thumb in front."""
    k = hl / 0.19
    M = _axes(hd)
    inward = np.array((-s, 0.0, 0.0), np.float32)
    d = F._rbox(P, wr + hd * hl * 0.25, (0.017 * k, hb * 0.5, hl * 0.26), 0.014 * k, M=M)
    d = F._smin(d, F._rbox(P, wr + hd * hl * 0.7 + inward * 0.007 * k, (0.013 * k, hb * 0.46, hl * 0.22), 0.011 * k, M=M),
                0.01)
    front = np.array((0.0, -1.0, 0.0), np.float32)
    return F._smin(d, F._cap(P, wr + hd * 0.03 * k + front * hb * 0.42, wr + hd * 0.1 * k + front * hb * 0.52 + inward * 0.012 * k,
                             0.011 * k, 0.009 * k), 0.008)


def _fist(P, fr, side):
    """A hand closed round a shaft (Frame.grip): the palm and the rolled fingers as one rounded block across the
    shaft, the thumb wrapped over the front of the fingers."""
    J, f = fr.joints, fr.f
    wr, el = J['wr_' + side], J['el_' + side]
    hd = (wr - el) / np.linalg.norm(wr - el)
    hl, hb = f['hand']
    k = hl / 0.19
    g = fr.grip[side]
    a = g - hd * float(g @ hd)
    a = a / np.linalg.norm(a)
    palm = fr._palm(side, hd)
    M = np.column_stack((a, np.cross(hd, a), hd)).astype(np.float32)     # local X along the shaft, Z along the hand
    d = F._rbox(P, wr + hd * hl * 0.3, (hb * 0.5, 0.025 * k, hl * 0.22), 0.016 * k, M=M)
    up = a if float(a[2]) >= 0.0 else -a                                  # the thumb closes over the top of the fist
    t0 = wr + hd * hl * 0.12 + palm * 0.018 * k + up * hb * 0.42
    return F._smin(d, F._cap(P, t0, t0 + hd * hl * 0.26 + palm * 0.012 * k, 0.011 * k, 0.009 * k), 0.008)


def _foot(P, an, s, fl, fb):
    """A foot: the heel under the ankle, the instep falling to the toes, narrow at the heel, turned out a little."""
    t = math.radians(8.0) * s
    fwd = np.array((math.sin(t), -math.cos(t), 0.0), np.float32)
    side = np.array((math.cos(t), math.sin(t), 0.0), np.float32)
    heel = np.array((an[0], an[1] + 0.026, 0.036), np.float32)
    d = F._ell(P, heel, np.array((0.03, 0.04, 0.036), np.float32))
    M = np.column_stack((side, fwd, (0.0, 0.0, 1.0))).astype(np.float32)
    box = F._rbox(P, heel + fwd * (fl * 0.5 - 0.03) + np.array((0.0, 0.0, 0.008), np.float32), (fb * 0.5, fl * 0.5, 0.044),
                  0.022, M=M)
    along = np.clip(((P - heel) @ fwd) / fl, 0.0, 1.0)
    box = F._smax(box, P[:, 2] - (0.088 - 0.064 * np.clip(along / 0.85, 0.0, 1.0)), 0.016)          # the instep's slope
    box = F._smax(box, np.abs((P - heel) @ side) - fb * 0.5 * (0.62 + 0.38 * np.clip(along / 0.55, 0.0, 1.0)), 0.01)
    d = F._smin(d, box, 0.02)
    return F._smax(d, 0.002 - P[:, 2], 0.004)                           # the sole


def _torso(P, fr):
    """The torso alone: lofted through its measured sections, a little squarer than an ellipse, closed at both ends."""
    hf = fr.hf
    x, y = P[:, 0], P[:, 1]
    u = P[:, 2] / hf
    w, df, db = fr.torso(u)
    dy = np.where(y < 0.0, df, db)
    q = (np.abs(x / w) ** 2.5 + np.abs(y / dy) ** 2.5) ** 0.4
    d = (q - 1.0) * np.minimum(w, dy)
    return F._smax(d, np.maximum(U[0] + 0.012 - u, u - U[-1]) * hf, 0.03)


def _arms(P, fr, grow=1.0):
    """The arms and hands alone, as plain capsules (keeping cloth off them)."""
    J, f = fr.joints, fr.f
    a0, a1, a2, a3 = (r * grow for r in f['arm'])
    out = None
    for side in 'lr':
        sh, el, wr = J['sh_' + side], J['el_' + side], J['wr_' + side]
        fa = wr - el
        tip = wr + fa / np.linalg.norm(fa) * f['hand'][0]
        d = np.minimum(F._cap(P, sh, el, a0, a1), F._cap(P, el, tip, a2, a3))
        out = d if out is None else np.minimum(out, d)
    return out


def field(P, fr, arms=True):
    """Signed distance to the bare body's skin (m) at points P (N, 3). arms=False: the body without its arms (a belt
    or a strap goes round the trunk, not round a hanging arm)."""
    f, hf = fr.f, fr.hf
    Pm = np.column_stack((np.abs(P[:, 0]), P[:, 1], P[:, 2]))

    def S(xx, yy, uu):
        return np.array((xx, yy, uu * hf), np.float32)

    d = _torso(P, fr)
    # the neck's root (the head brings its own neck down into it), the traps sloping from it to the shoulders, the
    # deltoids capping them
    d = F._smin(d, F._cap(P, S(0.0, 0.012, 1.47), S(0.0, 0.006, 1.53), f['neck'] * 1.08, f['neck']), 0.03)
    tr = f['traps']
    d = F._smin(d, F._cap(Pm, S(0.03, 0.028, 1.535), S(f['shoulder'] - 0.025, 0.012, 1.472), 0.02 + 0.02 * tr,
                          0.016 + 0.012 * tr), 0.03)
    dl = f['deltoid']
    d = F._smin(d, F._ell(Pm, S(f['shoulder'] + 0.01, 0.0, 1.428), np.array((dl, dl * 1.08, dl * 1.35), np.float32)), 0.025)
    # his pecs; her bust (as the guide: in proportion, under a wrap); the upper back, larger on him
    if f['pecs'] > 0.02:
        front = float(np.interp(1.36, U, f['tf']))
        d = F._smin(d, F._ell(Pm, S(0.07, -front + 0.022, 1.36), np.array((0.075, 0.03, 0.058), np.float32)
                              * (0.6 + 0.4 * f['pecs']), M=F._R(ry=-14.0)), 0.025)
    if f['bust'] > 0.02:
        front = float(np.interp(1.3, U, f['tf']))
        d = F._smin(d, F._ell(Pm, S(0.058, -front + 0.018, 1.3), np.array((0.056, 0.048, 0.055), np.float32)
                              * (0.5 + 0.5 * f['bust']), M=F._R(rz=-8.0)), 0.03)
    back = float(np.interp(1.32, U, f['tb']))
    d = F._smin(d, F._ell(Pm, S(0.085, back - 0.04, 1.32), np.array((0.075, 0.045, 0.13), np.float32)
                          * (0.75 + 0.25 * f['back'])), 0.03)
    # the seat (fuller on her), and her hips' lateral mass over the trochanters
    sb = float(np.interp(0.93, U, f['tb']))
    d = F._smin(d, F._ell(Pm, S(0.062, sb - 0.04, 0.925),
                          np.array((0.075, 0.05 + 0.014 * f['seat'], 0.088 + 0.008 * f['seat']), np.float32)), 0.035)
    if f['hipmass'] > 0.02:
        hw = float(np.interp(0.95, U, f['tw']))
        d = F._smin(d, F._ell(Pm, S(hw - 0.035, 0.01, 0.94), np.array((0.05, 0.07, 0.09), np.float32)
                              * (0.6 + 0.4 * f['hipmass'])), 0.04)
    J = fr.joints
    a0, a1, a2, a3 = f['arm']
    l0, l1, l2, l3, l4 = f['leg']
    for side, s in (('l', 1.0), ('r', -1.0)):
        sh, el, wr = J['sh_' + side], J['el_' + side], J['wr_' + side]
        ua, fa = el - sh, wr - el
        lu, lf = float(np.linalg.norm(ua)), float(np.linalg.norm(fa))
        if arms:
            d = F._smin(d, F._cap(P, sh, el, a0, a1), 0.02)
            d = F._smin(d, F._ell(P, sh + ua * 0.48 + np.array((0.0, -a0 * 0.38, 0.0), np.float32),
                                  np.array((a0 * 0.72, a0 * 0.62, lu * 0.28), np.float32)), 0.015)      # biceps
            d = F._smin(d, F._ell(P, sh + ua * 0.38 + np.array((0.0, a0 * 0.42, 0.0), np.float32),
                                  np.array((a0 * 0.75, a0 * 0.62, lu * 0.32), np.float32)), 0.015)      # triceps
            d = F._smin(d, F._cap(P, el, wr, a2, a3), 0.018)
            d = F._smin(d, F._ell(P, el + fa * 0.2 + np.array((s * a2 * 0.15, 0.0, 0.0), np.float32),
                                  np.array((a2 * 0.85, a2 * 0.8, lf * 0.3), np.float32)), 0.015)       # the forearm's belly
            d = F._smin(d, _fist(P, fr, side) if side in fr.grip else _hand(P, wr, fa / lf, s, *f['hand']), 0.012)
        hp, kn, an = J['hp_' + side], J['kn_' + side], J['an_' + side]
        th, sk = kn - hp, an - kn
        lt, ls = float(np.linalg.norm(th)), float(np.linalg.norm(sk))
        d = F._smin(d, F._cap(P, hp, kn, l0, l2 * 1.05), 0.03)
        d = F._smin(d, F._ell(P, hp + th * 0.42 + np.array((0.0, -l1 * 0.28, 0.0), np.float32),
                              np.array((l1 * 0.95, l1 * 0.85, lt * 0.33), np.float32)), 0.02)       # quadriceps
        d = F._smin(d, F._ell(P, hp + th * 0.8 + np.array((-s * l2 * 0.45, -l2 * 0.3, 0.0), np.float32),
                              np.array((l2 * 0.75, l2 * 0.7, l2 * 1.4), np.float32)), 0.015)         # the inner vastus
        d = F._smin(d, F._ell(P, hp + th * 0.4 + np.array((0.0, l1 * 0.32, 0.0), np.float32),
                              np.array((l1 * 0.85, l1 * 0.72, lt * 0.34), np.float32)), 0.02)       # hamstrings
        d = F._smin(d, F._ell(P, hp + th * 0.2 + np.array((-s * l0 * 0.45, 0.0, 0.0), np.float32),
                              np.array((l0 * 0.6, l0 * 0.7, lt * 0.25), np.float32)), 0.02)         # adductors
        d = F._smin(d, F._ell(P, kn + np.array((0.0, -l2 * 0.9, 0.012 * hf), np.float32),
                              np.array((0.026, 0.016, 0.03), np.float32)), 0.01)                    # knee cap
        d = F._smin(d, F._cap(P, kn, an, l2 * 0.92, l4), 0.02)
        d = F._smin(d, F._ell(P, kn + sk * 0.28 + np.array((s * 0.004, l3 * 0.38, 0.0), np.float32),
                              np.array((l3 * 0.95, l3 * 0.82, ls * 0.3), np.float32)), 0.02)        # the calf
        d = F._smin(d, _foot(P, an, s, *f['foot']), 0.02)
    return d


def bare(name, fr, look, skin, wrap, shorts, gaze=0.0, grid=0.004):
    """The bare body for review, dressed as on the reference sheet (a chest wrap, shorts), with a look's head level on
    its neck, as in a portrait. The head keeps its own neck and leaves its shoulders to the body. Returns the root."""
    from . import kit as K
    from . import looks as LK
    f, hf = fr.f, fr.hf
    g = F._Grid(None, None, (-0.42, -0.26, -0.01), (0.42, 0.22, 1.58 * hf), band=(-0.012, 0.014), h=grid, m=4,
                fn=lambda Q: field(Q, fr))
    parts = [F._mesh(name, *F._nets(g.D, g.lo, g.h), skin, 40000, smooth_angle=55)]

    def around(z0, z1, reach):
        """Cloth between two heights (on the male anchor's scale), within `reach` of the midline, on the trunk and
        legs but never on the arms (a little inside their inflated capsules is theirs)."""
        def region(P):
            r = np.maximum(np.maximum(z0 * hf - P[:, 2], P[:, 2] - z1 * hf), np.abs(P[:, 0]) - reach)
            return np.maximum(r, -_arms(P, fr, 1.15))
        return region
    top = 1.42 if f['bust'] < 0.5 else 1.385
    chest = g.shell(lambda P: np.full(len(P), 0.004, np.float32), around(1.25, top, float(np.interp(1.36, U, f['tw'])) + 0.02),
                    inner=0.003, feather=0.0015, floor=0.8)
    parts.append(F._mesh(name + '_wrap', *F._nets(chest, g.lo, g.h), wrap, 6000, smooth_angle=50))
    pants = g.shell(lambda P: np.full(len(P), 0.006, np.float32), around(0.74, 1.08, fr.hips() + 0.02),
                    inner=0.003, feather=0.0015, floor=0.8)
    parts.append(F._mesh(name + '_shorts', *F._nets(pants, g.lo, g.h), shorts, 9000, smooth_angle=50))
    root = K.root(name + '_root')
    K.parent(parts, root)
    hroot, _ = LK.build_head(look, gaze=gaze, tag=look.get('id') if not look.get('anchor') else None, yoke=False)
    hroot.matrix_world = fr.head_frame(portrait=True)
    hroot.parent = root
    return root
