"""The Conclave's kit: what its Acolytes, Blight-Mages and Blight-Sorcerers share (ASSETS.md, the enemy plan).

The uniform is the robe the company's runaway threw off (the Ash Acolyte's revision 1, git 26d1aca): a hooded robe of
undyed wool gone ash-grey, a mantle over the shoulders, the hood worn low; the sleeve cut away from a grafted arm, the
flesh under it ash-grey and bruised violet and split by veins of violet light (grit.graft). Where the runaway shows a
face, the Conclave wears a bone mask in the hood's shadow, so no head is carved for them: the hood holds a dark coif
and the mask. Rank is worn in the flesh and in bone: the Acolyte one grafted arm and a bow, the Mage both arms and a
bone staff crowned with ashfire, the Sorcerer a crown of bone horns, three ashfires turning about them and a robe that
trails.

Pieces: materials(), robe() (boots, the robe laid on the body with its grafts, the skirt hanging from a cord girdle),
mantle_hood(), masked_head() (bone_mask: 'oval' or 'long'), bone_staff(), horn_crown(), bone_circlet() (the Elder's
crown), train() (a robe's trailing hem), ember() (a small ashfire: a lit arrowhead), orbit() (ashfires turning on a
ring, their embers trailing). Figure space as in body.py and garb.py.
"""
import math
import random

import bmesh
import numpy as np
from mathutils import Matrix, Vector

from . import armor as A
from . import body as BD
from . import face as F
from . import garb as GB
from . import grit as G
from . import kit as K
from . import mat as M

# ash-grey robes, bone, violet (the Blight's light alone)
PAL = dict(ash='#7d7a75', cinder='#5a5753', pale='#8f8c86', soot='#1d1c1f', bone='#c8bfa7', old_bone='#a2977c',
           cord='#8d8672')
ROBES = {1: ('#7d7a75', '#6a6763'), 2: ('#57544f', '#75726c')}      # (robe, mantle and hood) per look
LIGHT = GB.ASHFIRE[False][4]


def bone(name, color=None):
    """Old bone: pale, pitted, grime in every hollow."""
    return M.painted(name, color or PAL['bone'], rough=0.6, edge=0.25, wash=0.7, grime=0.4, kind='bone', bump=0.35,
                     bump_scale=85.0, cracks=0.0)


def materials(n=1):
    """The Conclave kit's materials (look n: 1 ash-grey under a darker mantle, 2 cinder-dark under a paler one)."""
    robe_c, mantle_c = ROBES[n]
    return dict(
        robe=G.cloth(f'conclave_robe{n}', color=robe_c, blood=0.1, mud=0.9, grime=0.75, seed=71, ash=0.3,
                     char=(0.15, 0.9)),
        mantle=G.cloth(f'conclave_mantle{n}', color=mantle_c, blood=0.06, mud=0.4, grime=0.75, seed=73, ash=0.55),
        coif=G.cloth('conclave_coif', color=PAL['soot'], blood=0.0, mud=0.0, grime=0.4, seed=74),
        wraps=G.cloth('conclave_wraps', color='#3d3a36', blood=0.1, mud=0.2, grime=0.7, seed=76),
        cord=G.cloth('conclave_cord', color=PAL['cord'], blood=0.0, mud=0.3, grime=0.7, seed=77),
        boots=G.leather('conclave_boots', color='#241a14', mud=2.4, seed=12),
        leather=G.leather('conclave_leather', color='#2d2119', mud=1.0, seed=83),
        iron=G.steel('conclave_iron', color='#2c2d2f', rust=0.7, blood=0.2, seed=6, edge=0.35, scratch=0.6, dirt=0.8),
        bone=bone('conclave_bone'),
        old_bone=bone('conclave_old_bone', PAL['old_bone']),
        void=G.flat('conclave_void', '#09080a'),
        skin=G.skin('conclave_skin', '#8a7466', windburn=0.1, dirt=0.6),
    )


# ------------------------------------------------------------------------------------------------ the robe
def hand_region(fr, side, cuff=0.012, grow=1.0):
    """Within one hand, from `cuff` short of its wrist (a rough signed distance)."""
    wr = fr.joints['wr_' + side]
    el = fr.joints['el_' + side]
    fa = (wr - el) / np.linalg.norm(wr - el)
    hd = fr.hand_dir(side)
    return lambda P: np.minimum(F._cap(P, wr - fa * cuff, wr + fa * 0.01, fr.f['hand'][1] * 0.6 * grow),
                                F._cap(P, wr, wr + hd * fr.f['hand'][0] * 0.92, fr.f['hand'][1] * 0.62 * grow))


def graft_region(fr, side, cut=0.42):
    """One arm from where its sleeve is cut away (`cut` of the way down the upper arm, torn unevenly) to the
    fingertips: a rough signed distance, negative on the arm. Returns (region, distance past the cut)."""
    J = fr.joints
    sh, el, wr = J['sh_' + side], J['el_' + side], J['wr_' + side]
    tip = wr + fr.hand_dir(side) * fr.f['hand'][0]
    u = (el - sh) / np.linalg.norm(el - sh)
    at = sh + (el - sh) * cut
    o1 = np.cross(u, (0.0, 1.0, 0.0))
    if np.linalg.norm(o1) < 0.2:
        o1 = np.cross(u, (0.0, 0.0, 1.0))
    o1 /= np.linalg.norm(o1)
    o2 = np.cross(u, o1)
    a0, a1, a2, a3 = fr.f['arm']

    def past(P):
        q = P - at
        ph = np.arctan2(q @ o2, q @ o1)
        return q @ u + 0.011 * np.sin(3.0 * ph + 0.7) + 0.006 * np.sin(7.0 * ph + 2.0)

    def region(P):
        fore = np.minimum(GB.seg_dist(P, el, wr) - (a2 + 0.012), GB.seg_dist(P, wr, tip) - 0.065)
        upper = np.maximum(GB.seg_dist(P, sh, el) - (a0 + 0.015), -past(P))
        return np.minimum(fore, upper)
    return region, past


def robe(D, fr, mt, parts, seed=7, grafts=('l',), cut=0.42, glow=1.3, hem=0.075, flare=0.09, band=None):
    """The Conclave robe on a posed body: the body, soft boots, the robe's body and sleeves as a layer (a bell cuff on a
    whole sleeve; the sleeve of a grafted arm cut away `cut` down the upper arm, the graft's flesh bare from there to
    the fingertips), wraps on a hand that isn't grafted, the skirt draped from a cord girdle and hanging to `hem`
    (heights on the male anchor's scale), and the girdle with its knot and ends. band: the robe's region between its
    hem at the hips and its collar (default Dressed.heights(0.86, 1.545)). Returns dict(skirt, zb)."""
    hf, f, J = fr.hf, fr.f, fr.joints
    M0 = BD.Frame('male')
    wdef = (fr.hips() - float(fr.torso(1.17)[0])) - (M0.hips() - float(M0.torso(1.17)[0]))
    parts.append(D.skin('conclave_body', mt['skin']))

    def boot_t(P):
        cuff = np.exp(-((P[:, 2] - 0.24 * hf) / 0.018) ** 2)
        return (0.0055 + 0.004 * cuff).astype(np.float32)
    parts.append(D.layer('softboots', mt['boots'], boot_t,
                         lambda P: np.maximum(D.heights(-0.02, 0.25)(P), -D.arms(1.2)(P)), inner=-0.001, tris=7000,
                         smooth=40))
    gr = {s: graft_region(fr, s, cut) for s in grafts}
    whole = [s for s in 'lr' if s not in grafts]
    hands = [hand_region(fr, s) for s in whole]
    between = band or D.heights(0.86, 1.545)

    def robe_t(P):
        th = np.arctan2(P[:, 0], -P[:, 1])
        folds = 0.5 + 0.5 * np.sin(th * 9.0 + 1.3 * np.sin(P[:, 2] * 23.0))
        on_arm = np.clip(1.0 - BD._arms(P, fr, 1.0) / 0.02, 0.0, 1.0)
        t = 0.0085 + 0.003 * folds * (1.0 - on_arm)
        for s in 'lr':
            sh, el, wr = J['sh_' + s], J['el_' + s], J['wr_' + s]
            if s in gr:         # the torn sleeve's edge, rolled
                t = t + 0.005 * np.exp(-(gr[s][1](P) / 0.012) ** 2) * (GB.seg_dist(P, sh, el) < 0.09)
            else:               # the sleeve's bell
                lf = float(np.linalg.norm(wr - el))
                u = (wr - el) / lf
                along = np.clip(((P - el) @ u) / lf, 0.0, 1.0) * (GB.seg_dist(P, el, wr) < 0.1)
                t = t + 0.013 * np.clip((along - 0.55) / 0.45, 0.0, 1.0) ** 1.5 * on_arm
        return t.astype(np.float32)

    def robe_region(P):
        r = between(P)
        for h in hands:
            r = np.maximum(r, -h(P))
        for s in gr:
            r = np.maximum(r, -gr[s][0](P))
        return r
    parts.append(D.layer('robe', mt['robe'], robe_t, robe_region, inner=0.003, tris=15000, smooth=45))
    for s in gr:
        wr = J['wr_' + s]
        src = wr + fr.hand_dir(s) * f['hand'][0] * 0.38
        gm = G.graft(f'conclave_graft_{s}', '#8a7466', tuple(float(x) for x in src), reach=0.36 * hf * (1.0 + 0.6 * (0.42 - cut)),
                     glow=glow, light=LIGHT)
        parts.append(D.layer(f'graft_{s}', gm, lambda P: np.full(len(P), 0.003, np.float32), gr[s][0], inner=0.004,
                             feather=0.0015, floor=1.0, tris=8000, smooth=40))
    for s in whole:
        parts.append(D.layer(f'wraps_{s}', mt['wraps'], lambda P: np.full(len(P), 0.0032, np.float32),
                             hand_region(fr, s, cuff=0.04), inner=0.002, tris=3000, smooth=45))

    # the skirt, hanging from the girdle (his at the hips, hers cinched at her natural waist)
    zb = (1.05 + 1.5 * wdef) * hf - (fr.spine[2] if fr.spine is not None else 0.0)
    skirt = GB.Drape(D, zb + 0.035 * hf, hem * hf, [a * 5.0 for a in range(72)], 0.024, rows=36, oy=0.01,
                     flare=flare, folds=0.016, fold_n=10, ragged=0.03, seed=seed, arms=False, closed=True,
                     cinch=(zb, 0.022))
    parts.append(skirt.mesh('robe_skirt', mt['robe'], thick=0.005))
    ring = [skirt.point(a, zb, lift=0.011) for a in range(0, 360, 6)]
    parts += A.strap('girdle', [p for p, _ in ring], [n for _, n in ring], 0.034, 0.012, mt['cord'], closed=True)
    knot, _ = skirt.point(-112.0, zb, lift=0.028)
    parts.append(K.sphere('girdle_knot', tuple(knot), 0.024, mt['cord'], scale=(1.2, 0.7, 1.0), seg=14, rings=10))
    for k, (da, ln) in enumerate(((-4.0, 0.34), (5.0, 0.27))):
        top, out = [], []
        for j in range(3):
            p, n = skirt.point(-112.0 + da + (j - 1) * 2.4, zb - 0.02, lift=0.03 + 0.004 * k)
            top.append(p)
            out.append(n)
        parts.append(A.cloth_panel('girdle_end', top, out, ln * hf, mt['cord'], rows=8, tatter=0.1, slits=0,
                                   fold=0.005, seed=seed + 20 + k, thick=0.006))
    return dict(skirt=skirt, zb=zb, wdef=wdef)


def mantle_hood(D, fr, H, mt, parts, seed=7, low=1.27, ragged=0.02):
    """The mantle over the shoulders (to `low`, on the male anchor's scale; shorter in front) and the hood worn low
    round the head placed by H. Returns the mantle's Drape."""
    hf = fr.hf
    if fr.spine is None:
        ztop, oy = 1.58 * hf, 0.02
        ref = Vector((0.0, 0.02, ztop))
    else:
        ztop = 1.58 * hf - fr.spine[2]
        oy = float(fr.from_upper(np.array((0.0, 0.02, 1.53 * hf), np.float32))[1])
        ref = Vector((0.0, oy + 0.02, ztop))
    cape = GB.Drape(D, ztop, low * hf, [a * 5.0 for a in range(72)], 0.044, rows=20, oy=oy,
                    collar=(0.1 * fr.head_scale + 0.012, 0.5), flare=0.03, folds=0.012, fold_n=9, ragged=ragged,
                    seed=seed, closed=True, arms=False,
                    hem=lambda a: 0.055 * hf * max(0.0, -math.sin(math.radians(a))) ** 1.5)
    parts.append(cape.mesh('mantle', mt['mantle'], thick=0.006))
    z_bot = (Vector(H.inverted() @ ref).z) - 0.03
    parts.append(GB.hood('hood', H, z_bot, mt['mantle'], seed=seed))
    return cape


# ------------------------------------------------------------------------------------------------ the bone mask
MASK_C, MASK_R = (0.0, -0.004, -0.04), (0.071, 0.101, 0.108)      # head space, an unscaled head
MASK_TOP = 0.03
MASKS = {'oval': dict(bottom=-0.128, chin=None),                   # a plain oval face of bone
         'long': dict(bottom=-0.185, chin=-0.085)}                 # drawn down past the jaw to a blunt point


def _mask_k(kind, z):
    """A mask's (width, depth) factors at height z."""
    cz, rz = MASK_C[2], MASK_R[2]
    m = MASKS[kind]
    zz = max(z, m['chin']) if m['chin'] is not None else z
    k = math.sqrt(max(1.0 - ((zz - cz) / rz) ** 2, 0.04))
    if m['chin'] is not None and z < m['chin']:
        s = (m['chin'] - z) / (m['chin'] - m['bottom'])
        return k * max(1.0 - s, 0.0) ** 0.75 + 0.1 * (1.0 - s) + 0.06, k * (1.0 - 0.3 * s)
    return k, k


def mask_point(kind, x, z, lift=0.0):
    """A point on the mask's face at (x, z), head space, lifted off it toward the front."""
    kw, kd = _mask_k(kind, z)
    s = max(-0.95, min(0.95, x / (MASK_R[0] * kw)))
    return Vector((x, MASK_C[1] - MASK_R[1] * kd * math.sqrt(1.0 - s * s) - lift, z))


def bone_mask(name, kind, bone_mat, dark, rows=16, cols=14, half=60.0):
    """A bone mask (head space, an unscaled head; the face toward -Y): the front of an ovoid of bone from under the
    hood's brow to below the chin, two eye holes, a nasal hole, slits over the mouth. Returns the parts."""
    m = MASKS[kind]
    bm = bmesh.new()
    grid = []
    for j in range(rows + 1):
        z = MASK_TOP + (m['bottom'] - MASK_TOP) * j / rows
        kw, kd = _mask_k(kind, z)
        row = []
        for i in range(cols + 1):
            th = math.radians(-half + 2.0 * half * i / cols)
            row.append(bm.verts.new((MASK_R[0] * kw * math.sin(th), MASK_C[1] - MASK_R[1] * kd * math.cos(th), z)))
        grid.append(row)
    for j in range(rows):
        for i in range(cols):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if sum(f.normal.y for f in bm.faces) > 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    plate = K._obj(name, bm, bone_mat)
    A.solid(plate, 0.006, -1.0)
    K.subsurf(plate, 1)
    parts = [plate]
    for s in (-1.0, 1.0):          # the eye holes, their outer corners drawn down
        parts.append(GB._blob(name + '_eye', mask_point(kind, 0.031 * s, -0.012, -0.001), 1.0, (0.0165, 0.007, 0.0115),
                              (0.0, 0.32 * s), dark))
    parts.append(GB._blob(name + '_nose', mask_point(kind, 0.0, -0.05, -0.001), 1.0, (0.0065, 0.006, 0.013), (0.0, 0.0),
                          dark))
    if kind == 'long':             # three long slits down the chin
        for x, z0, ln in ((0.0, -0.105, 0.03), (-0.014, -0.098, 0.022), (0.014, -0.098, 0.022)):
            parts.append(GB._blob(name + '_slit', mask_point(kind, x, z0, -0.001), 1.0, (0.0028, 0.006, ln), (0.0, 0.0),
                                  dark))
    else:                          # a row of short slits: its teeth
        for k in range(5):
            x = -0.022 + 0.011 * k
            parts.append(GB._blob(name + '_slit', mask_point(kind, x, -0.092 + 0.004 * abs(k - 2), -0.001), 1.0,
                                  (0.0024, 0.006, 0.0105), (0.0, 0.0), dark))
    return parts


def masked_head(H, mt, kind='oval', name='head'):
    """What a Conclave hood holds, placed by the head's frame H: darkness (no face is carved), a soot-black coif down
    the neck, and the bone mask. Returns the parts; the first is a root named '<name>_root'."""
    parts = [K.sphere(name + '_void', (0.0, 0.012, 0.012), 1.0, mt['void'], scale=(0.084, 0.104, 0.101), seg=24, rings=14),
             K.tube(name + '_coif', (0.0, 0.03, -0.045), (0.0, 0.03, -0.28), 0.064, 0.078, mt['coif'], seg=20)]
    parts += bone_mask(name + '_mask', kind, mt['bone'], mt['void'])
    root = K.root(name + '_root')
    K.parent(parts, root)
    root.matrix_world = H
    return root


# ------------------------------------------------------------------------------------------------ bone: horns, staff
def horn(name, base, d0, bend, length, curl, r0, r1, mat, n=10, seg=8, flat=1.0):
    """A horn (a rib, a tine): from `base` along d0, curling `curl` radians toward `bend` over its `length`, tapering
    from r0 to r1."""
    b = Vector(base)
    d = Vector(d0).normalized()
    bd = Vector(bend)
    bd = (bd - d * bd.dot(d)).normalized()
    R = length / max(curl, 1e-3)
    pts, secs = [], []
    for i in range(n):
        t = i / (n - 1)
        phi = curl * t
        pts.append(b + d * (R * math.sin(phi)) + bd * (R * (1.0 - math.cos(phi))))
        r = r0 + (r1 - r0) * t ** 0.85
        secs.append((r, r * flat))
    return GB._loft(name, pts, [bd.cross(d)] * n, secs, mat, n=seg)


def horn_crown(name, H, bone_mat, band_mat, size=1.0, seed=0):
    """A crown of bone horns over a hood, placed by the head's frame H: a band of bone round the hood's brow and seven
    horns rising from it, the two at the temples sweeping out and up over the shoulders' width, the rest shorter,
    ranked round the back. Returns the parts."""
    rnd = random.Random(seed)
    c = Vector((0.0, 0.009, 0.052))
    T = Matrix.Rotation(math.radians(F.HOOD_TILT), 4, 'X')
    band = A.torus(name + '_band', (0.0, 0.0, 0.0), 0.1, 0.0085, band_mat, sx=0.99, sy=1.2, seg=40, rseg=8, rz=0.013,
                   lumpy=0.12, seed=seed)
    band.matrix_world = Matrix.Translation(c) @ T
    parts = [band]
    #        angle, length, base radius, curl, how far it leans out
    horns = [(0.0, 0.31, 0.022, 1.25, 1.0), (180.0, 0.31, 0.022, 1.25, 1.0),
             (48.0, 0.2, 0.017, 1.0, 0.75), (132.0, 0.2, 0.017, 1.0, 0.75),
             (90.0, 0.25, 0.018, 0.8, 0.5),
             (-52.0, 0.13, 0.014, 0.9, 0.8), (232.0, 0.13, 0.014, 0.9, 0.8)]
    for k, (a, ln, r0, curl, lean) in enumerate(horns):
        ar = math.radians(a)
        rad = Vector((math.cos(ar), math.sin(ar), 0.0))
        base = c + Vector((rad.x * 0.086, rad.y * 0.106, 0.0))
        d0 = (rad * lean + Vector((0.0, 0.0, 0.55))).normalized()
        ob = horn(f'{name}_horn{k}', base, d0, Vector((0.0, 0.0, 1.0)) - rad * 0.15, ln * size * rnd.uniform(0.94, 1.06),
                  curl, r0 * size, 0.0025, bone_mat, n=12, seg=8, flat=0.85)
        ob.matrix_world = Matrix.Translation(c) @ T @ Matrix.Translation(-c) @ ob.matrix_world
        parts.append(ob)
    for ob in parts:
        ob.matrix_world = H @ ob.matrix_world
    return parts


def bone_circlet(name, H, bone_mat, band_mat, n=9, seed=0):
    """The Elder's crown: a band of bone round the hood's brow set with short upright tines (finger bones), taller at
    the front. Returns the parts."""
    rnd = random.Random(seed)
    c = Vector((0.0, 0.009, 0.052))
    T = Matrix.Rotation(math.radians(F.HOOD_TILT), 4, 'X')
    band = A.torus(name + '_band', (0.0, 0.0, 0.0), 0.1, 0.009, band_mat, sx=0.99, sy=1.2, seg=40, rseg=8, rz=0.015,
                   lumpy=0.12, seed=seed)
    band.matrix_world = Matrix.Translation(c) @ T
    parts = [band]
    for k in range(n):
        a = math.radians(-90.0 + 360.0 * k / n)
        rad = Vector((math.cos(a), math.sin(a), 0.0))
        base = c + Vector((rad.x * 0.097, rad.y * 0.118, 0.0))
        front = 0.5 + 0.5 * max(0.0, -math.sin(a))
        ob = horn(f'{name}_tine{k}', base, (rad * 0.35 + Vector((0.0, 0.0, 1.0))).normalized(), -rad,
                  (0.075 + 0.05 * front) * rnd.uniform(0.9, 1.1), 0.35, 0.011, 0.003, bone_mat, n=6, seg=6)
        ob.matrix_world = Matrix.Translation(c) @ T @ Matrix.Translation(-c) @ ob.matrix_world
        parts.append(ob)
    for ob in parts:
        ob.matrix_world = H @ ob.matrix_world
    return parts


def bone_staff(name, grip, up, length, bone_mat, old_bone, cord, butt_z=0.03, seed=0):
    """A staff of bone held upright in a fist at `grip`, its butt on the ground: three long bones lashed end to end,
    knuckled at every joint, and at its head a claw of five ribs curling up round the place its ashfire burns. Returns
    (parts, where the ashfire floats)."""
    u = Vector(up).normalized()
    G_ = Vector(grip)
    butt = G_ - u * ((G_.z - butt_z) / max(u.z, 1e-3))
    top = butt + u * length
    R = A.frame(u)
    side = (R @ Vector((1.0, 0.0, 0.0, 0.0))).to_3d()
    fwd = (R @ Vector((0.0, 1.0, 0.0, 0.0))).to_3d()
    rnd = random.Random(seed)
    parts = []
    n = 3
    seg = length / n
    for k in range(n):
        a, b = butt + u * (seg * k), butt + u * (seg * (k + 1))
        parts.append(K.tube(f'{name}_shaft{k}', a, b, 0.0175, 0.0155, bone_mat if k != 1 else old_bone, seg=10))
        for e, r in ((a + u * 0.018, 0.027), (b - u * 0.018, 0.025)):
            for sx in (-1.0, 1.0):      # each end's two condyles
                parts.append(K.sphere(name + '_knuckle', tuple(e + side * (0.011 * sx)), r * 0.78,
                                      bone_mat if k != 1 else old_bone, scale=(1.0, 1.0, 1.15), seg=10, rings=7))
        if k:
            lash = A.torus(name + '_lash', (0.0, 0.0, 0.0), 0.024, 0.009, cord, seg=18, rseg=6, lumpy=0.3, seed=seed + k,
                           rz=0.02)
            A.place(lash, a, R)
            parts.append(lash)
    parts.append(K.tube(name + '_wrap', G_ - u * 0.075, G_ + u * 0.075, 0.0195, 0.0195, cord, seg=12))
    fire = top + u * 0.13
    for k in range(5):
        a = 2.0 * math.pi * (k + 0.3) / 5.0
        o = side * math.cos(a) + fwd * math.sin(a)
        parts.append(horn(f'{name}_rib{k}', top - u * 0.03 + o * 0.012, (o * 1.0 + u * 0.55).normalized(), u - o * 0.25,
                          0.27 * rnd.uniform(0.9, 1.08), 1.75, 0.0125, 0.003, bone_mat, n=11, seg=7))
    lash = A.torus(name + '_head_lash', (0.0, 0.0, 0.0), 0.027, 0.011, cord, seg=18, rseg=6, lumpy=0.3, seed=seed, rz=0.03)
    A.place(lash, top - u * 0.035, R)
    parts.append(lash)
    return parts, fire


# ------------------------------------------------------------------------------------------------ a trailing hem
def train(name, skirt, mat, z_from, length=0.6, a0=-25.0, a1=140.0, peak=55.0, cols=34, rows=14, seed=0, thick=0.005):
    """A robe's train: from the skirt (a closed Drape) at height z_from, between the angles a0 and a1, the cloth runs
    out along the ground behind the wearer, longest toward `peak` (degrees), rippled and torn at its end."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    grid = []
    for i in range(cols + 1):
        a = a0 + (a1 - a0) * i / cols
        p0, n = skirt.point(a, z_from, lift=-0.004)
        w = max(0.0, math.cos(math.radians(a - peak) * 180.0 / (a1 - a0)))      # 1 at the peak, 0 at both ends
        ln = length * (0.12 + 0.88 * w ** 1.2) * rnd.uniform(0.88, 1.08)
        pk = math.radians(peak)
        out = (n * 0.55 + Vector((math.cos(pk), math.sin(pk), 0.0)) * 0.45).normalized()
        col = []
        for j in range(rows + 1):
            t = j / rows
            z = 0.012 + (z_from - 0.012) * (1.0 - t) ** 2.4 + 0.011 * t * math.sin(a * 0.19 + 5.0 * t + seed)
            col.append(bm.verts.new((p0.x + out.x * ln * t, p0.y + out.y * ln * t, max(z, 0.006))))
        grid.append(col)
    for i in range(cols):
        for j in range(rows):
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = K._obj(name, bm, mat)
    A.solid(ob, thick)
    K.subsurf(ob, 1)
    return ob


# ------------------------------------------------------------------------------------------------ ashfire
def ember(name, at, r=0.011, energy=0.2):
    """A small ashfire (a lit arrowhead): a white heart, a violet flame round it, its bloom and its light."""
    core_c, inner_c, outer_c, halo_c, light_c = GB.ASHFIRE[False]
    C = Vector(at)
    parts = [K.sphere(name + '_heart', tuple(C), r * 0.6, M.emissive('ashfire_heart', core_c, 5.0), seg=10, rings=8),
             GB._blob(name + '_flame', C + Vector((0.0, 0.0, r * 0.7)), r, (1.0, 1.0, 2.0), (0.15, 0.1),
                      M.emissive('ashfire_inner', inner_c, 1.6)),
             K.sphere(name + '_halo', tuple(C), r * 3.6, M.halo('ember_halo', halo_c, 1.4, 0.8, hollow=True), seg=18,
                      rings=10)]
    for ob in parts:
        ob.visible_shadow = False
    parts.append(K.glow(name + '_light', C, light_c, energy, radius=0.02))
    return parts


def orbit(name, points, tail=70.0, n=11, seed=0, energy=0.55):
    """Ashfires turning about their bearer: one at each of three `points` (figure space), which fix the ring they turn
    on, each trailing embers back along it over `tail` degrees. Returns the parts."""
    P = [Vector(p) for p in points]
    a, b, c = P
    ab, ac = b - a, c - a
    nrm = ab.cross(ac)
    # the circumcentre of the three
    centre = a + (ac.length_squared * nrm.cross(ab) + ab.length_squared * ac.cross(nrm)) / (2.0 * nrm.length_squared)
    nrm.normalize()
    inner = M.emissive('ashfire_ember', GB.ASHFIRE[False][1], 3.0)
    parts = []
    for k, p in enumerate(P):
        parts += GB.ashfire(f'{name}{k}', p, energy=energy, seed=seed + 3 * k)
        bm = bmesh.new()
        arm = p - centre
        for j in range(1, n + 1):
            t = j / n
            q = centre + Matrix.Rotation(-math.radians(tail) * t, 3, nrm) @ arm
            g = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.0105 * (1.0 - t) ** 0.8 + 0.002)
            bmesh.ops.translate(bm, vec=q, verts=g['verts'])
        ob = K._obj(f'{name}{k}_tail', bm, inner)
        ob.visible_shadow = False
        parts.append(ob)
    return parts
