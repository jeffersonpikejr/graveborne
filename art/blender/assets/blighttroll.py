"""BLIGHT-TROLL. Wave 2, asset #19 (step 7 of the enemy plan): the Warhost's brute, 34 HP of it.

Brief (in the Line-Breaker's register): something the Blight grew out of a corpse and kept growing. Hunched from the
small of the back under a hump of shoulder, wider than two men, its arms hanging to the ground and ending in hands
like shovels, its head small and sunk between the shoulders; a hide the green of a drowned corpse, livid and split;
violet Blight crystals burst through the back in clusters, lighting the hump; a hide kilt on a rope; a greataxe of
black corroded iron held upright in one fist. At 26 px a Troll is its size (it fills the sprite's canvas, over its
neighbours' tiles), the crystals on its back and the axe.

Built on the brute anchor (gb/beast.py: brute(), a third end on the body dial), posed with the company's Frame (hunch,
reach) and beast.legs (short legs bent under it), dressed as any body (beast.Posed), in corpse mode, with a head from
the enemy pool, shaved, its eyes two violet points. One form, two seeds. No revenant flag: no violet back-light.
"""
import math

import numpy as np
from mathutils import Matrix, Vector

from gb import beast as BE
from gb import body as BD
from gb import face as F
from gb import garb as GB
from gb import grit as G
from gb import kit as K
from gb import looks as LK
from gb import mat as M

SCALE = 0.75            # tiles per metre of the brute: as large as the house canvas holds (a man's is 0.6)
FOOT = 1.5
SHIFT = -0.05           # (tiles) its mass a little to the left, so its long shadow stays inside the canvas
HIP = 0.50              # the hips' height (m): short legs, bent
HEAD_AT = (0.0, -0.02, 1.63)

VARIANTS = {'foe_blighttroll_1': dict(n=1), 'foe_blighttroll_2': dict(n=2)}

AXE_DIR = (0.10, 0.18, 0.97)
SEEDS = {1: dict(bend=34.0, stride=0.10, turn=-5.0, hide='#5f7048'),
         2: dict(bend=38.0, stride=-0.08, turn=5.0, hide='#566a4c')}
# the crystals: (angle round the back, height on the upright body, length, radius, lesser ones round its foot)
CRYSTALS = [(92.0, 1.37, 0.36, 0.06, 3), (60.0, 1.42, 0.27, 0.048, 2), (122.0, 1.41, 0.3, 0.05, 2),
            (78.0, 1.22, 0.22, 0.04, 2), (110.0, 1.17, 0.18, 0.036, 1), (36.0, 1.34, 0.16, 0.03, 1),
            (146.0, 1.3, 0.15, 0.03, 1)]


def pose(n=1):
    """Hunched under its own back, the knees bent out over wide feet; the left arm hanging to the ground, the right
    fist round the greataxe's haft, the axe upright beside it."""
    sd = SEEDS[n]
    fr = BD.Frame(BE.brute())
    fr.sex = 'male'
    J = fr.joints
    for s in 'lr':          # arms that reach the ground
        sh, el, wr = J['sh_' + s], J['el_' + s], J['wr_' + s]
        el2 = sh + (el - sh) * 1.3
        J['el_' + s], J['wr_' + s] = el2.astype(np.float32), (el2 + (wr - el) * 1.4).astype(np.float32)
    fr.hunch(bend=sd['bend'], pivot=1.0, drop=0.965 - HIP)
    for s, side, st in ((1.0, 'l', sd['stride']), (-1.0, 'r', 0.0)):
        hp = J['hp_' + side]
        an = np.array((s * 0.28, hp[1] + 0.03 - st, 0.085 * FOOT), np.float32)
        J['kn_' + side], J['an_' + side] = BE.ik(hp, an, 0.27, 0.25, (s * 0.55, -1.0, 0.0))
    sh_l, sh_r = J['sh_l'], J['sh_r']
    fr.reach('l', (sh_l[0] + 0.0, sh_l[1] - 0.12, 0.36), pole=(0.7, 0.6, -0.2))
    ax = np.array(AXE_DIR, np.float32) / np.linalg.norm(AXE_DIR)
    fr.reach('r', (sh_r[0] + 0.03, sh_r[1] - 0.1, 0.5), pole=(-0.8, 0.5, -0.2), grip=ax)
    return fr


def _spine(fr):
    bend, pv, drop = fr.spine
    return (Matrix.Translation(Vector((pv[0], pv[1], pv[2] - drop))) @ Matrix.Rotation(math.radians(bend), 4, 'X')
            @ Matrix.Translation(-Vector(pv)))


def build(v, seed=7, turn=None, look=None, head=True):
    """One variant (VARIANTS)."""
    n = v.get('n', 1)
    sd = SEEDS[n]
    M.set_mode(revenant=True, corpse=True)
    seed = seed + 31 * n
    fr = pose(n)
    J = fr.joints
    D = BE.Posed(fr, BE.figure_field(fr, foot=FOOT), (-0.85, -0.8, -0.01), (0.85, 0.48, 1.3), grid=0.005)
    if look is None:
        look = dict(LK.foe('m', 40 + n, rough=False), style='shaved', beard=None)

    hide = G.skin(f'troll_hide{n}', sd['hide'], windburn=0.0, dirt=1.0, rot=1.0, seed=seed)
    kilt = G.leather('troll_kilt', color='#3d3023', mud=2.0, seed=seed + 1)
    rope = G.cloth('troll_rope', color='#6e6250', blood=0.1, mud=1.2, grime=0.6, seed=61)
    iron = G.steel('troll_iron', color='#34312e', rust=1.3, blood=0.6, seed=seed + 3, edge=0.3, scratch=0.5, dirt=0.9,
                   dents=1.0)
    wood = G.wood('troll_haft', color='#3a2c1f', seed=48)
    wrap = G.leather('troll_wrap', color='#2e2219', seed=41)
    xtal = BE.crystal_mat()

    fig = K.root('figure')
    parts = [D.skin('troll_body', hide, tris=18000)]

    # ---------------------------------------------------------------- a hide kilt on a rope
    ragged = F._Noise(seed + 13)

    def kilt_region(P):
        low = HIP - 0.2 + 0.1 * (ragged(P, 7.0) - 0.5)
        return np.maximum(np.maximum(low - P[:, 2], P[:, 2] - (HIP + 0.13)), -D.arms(1.15)(P))
    parts.append(D.layer('kilt', kilt, lambda P: np.full(len(P), 0.016, np.float32), kilt_region, inner=0.003,
                         tris=7000, smooth=45))
    bp, _ = D.ring(HIP + 0.1, 0.03, n=48, oy=0.03)
    parts.append(GB.cord('rope_belt', bp, 0.02, rope, closed=True))

    # ---------------------------------------------------------------- the crystals through the back
    R = fr._spine_R()
    rnd = np.random.default_rng(seed)
    big = None
    for i, (a, zu, ln, r, k) in enumerate(CRYSTALS):
        a = math.radians(a + rnd.uniform(-7.0, 7.0))
        dv = np.array((math.cos(a), math.sin(a), 0.3), np.float32)
        dv = (dv / np.linalg.norm(dv)) @ R.T
        O = fr.from_upper(np.array((0.0, 0.03, zu), np.float32))
        rr = float(D.outer(O[None, :], dv[None, :], 0.0, arms=False)[0])
        base = Vector(O + dv * rr)
        axis = (Vector(dv) * 0.55 + Vector((rnd.uniform(-0.15, 0.15), 0.1, 0.85))).normalized()
        parts += BE.crystals('crystal', base, axis, ln * rnd.uniform(0.9, 1.12), r, xtal, n=k, seed=seed + i)
        if big is None:
            big = base + axis * 0.15
    parts.append(K.glow('crystal_glow', big + Vector((0.0, -0.1, 0.12)), '#9a5cf0', 0.7, radius=0.06))

    # ---------------------------------------------------------------- the greataxe
    parts += BE.greataxe('greataxe', Vector(fr.fist('r')), AXE_DIR, (iron, wood, wrap), haft=1.3, below=0.3)

    # ---------------------------------------------------------------- the head, small, sunk between the shoulders
    H = (_spine(fr) @ Matrix.Translation(Vector(HEAD_AT)) @ Matrix.Rotation(math.radians(10.0 - sd['bend']), 4, 'X')
         @ Matrix.Scale(fr.head_scale, 4))
    if head:
        hroot, info = LK.build_head(look, tag=f'troll_{look["id"]}', yoke=False, rot=1.0)
        hroot.matrix_world = H
        parts.append(hroot)
        bloom = M.halo('troll_eye_bloom', '#9a5cf0', 2.0, 0.7, 1.4)
        for e in info['eyes']:
            ob = K.sphere('eye_bloom', tuple(H @ (e + Vector((0.0, -0.012, 0.0)))), 0.022, bloom, seg=16, rings=10)
            ob.visible_shadow = False
            parts.append(ob)
    parts.append(K.glow('face_glow', H @ Vector((0.0, -0.1, 0.01)), '#b98cf0', 0.2, radius=0.012))

    K.parent(parts, fig)
    fig.scale = (SCALE,) * 3
    fig.location.x = SHIFT
    fig.rotation_euler.z = math.radians(sd['turn'] if turn is None else turn)
    return fig
