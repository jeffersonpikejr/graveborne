"""HUSK. Wave 2, asset #6: the Blight-risen dead, the most common foe on the board (seven of the eight contract pools,
four doctrines).

Brief (in the Line-Breaker's register): the dead the Blight gets up again before it has made anything of them. A
corpse in what it was buried or killed in, hunched from the small of the back, head hanging, one foot dragged after
the other; a war axe trailing from one hand, its head on the ground behind. Flesh gone the grey-green of rot, livid
where the blood pooled, split to the bone in places; eyes burning blight-violet. Rags of a shirt torn open down the
breast and breeches torn off below the knee, a burial shroud hanging in tatters from the shoulders, bare feet black
with grave dirt. At 26 px a Husk is the hunch, the dragging axe and two violet points.

A foe ships whole sprites (ASSETS.md, the enemy plan): both forms, two looks each (a corpse's look: its head from the
enemy pool, its wounds, its rags), and the tier looks of TIER_UPGRADES: Ironbound (scrap plate lashed on: a rusted
breastplate, a pauldron) and Bloated (swollen on the body dial, the belly split and glowing). Everything is the
company's kit: the body posed (Frame.hunch), clothes laid on it and draped over it (gb/garb.py), a look's head with a
corpse's face (grit.skin rot), and the corpse materials (mat.set_mode corpse: grave-earth and rot, violet in the
flesh's fissures and the eyes).
"""
import math

import numpy as np
from mathutils import Matrix, Vector

from gb import armor as A
from gb import body as BD
from gb import face as F
from gb import garb as GB
from gb import grit as G
from gb import kit as K
from gb import looks as LK
from gb import mat as M

FIG_SCALE = 0.6

# Corpse mode throughout (build sets it), but no revenant flag: the violet back-light is the company's risen, whose
# ring is violet; a foe's side is its ring (green for the undead), and its Blight is in its eyes and its flesh.
VARIANTS = {}
for _f, _sex in (('m', 'male'), ('f', 'female')):
    for _n in (1, 2):
        VARIANTS[f'foe_husk_{_n}_{_f}'] = dict(sex=_sex, n=_n)
    for _tag in ('ironbound', 'bloated'):
        VARIANTS[f'foe_husk_{_tag}_1_{_f}'] = dict(sex=_sex, n=1, tag=_tag)

AXE_DIR = (-0.12, 0.52, -0.85)      # from the fist down and back to the ground: the axe dragged behind

BLOAT = dict(tw=[0.02, 0.04, 0.06, 0.08, 0.09, 0.08, 0.05, 0.025, 0.01, 0.0, 0.0],      # body.U levels, m
             tf=[0.03, 0.06, 0.1, 0.14, 0.16, 0.13, 0.07, 0.03, 0.0, 0.0, 0.0],
             tb=[0.01, 0.02, 0.03, 0.03, 0.03, 0.03, 0.02, 0.01, 0.0, 0.0, 0.0],
             arm=[0.014, 0.012, 0.012, 0.007], leg=[0.024, 0.02, 0.014, 0.014, 0.007], neck=0.012)

# (shirt, breeches) per look, dark against the grey-green flesh: brown wool over near-black; peat-dark over grey-black
RAGS = {1: ('#4d3f30', '#2b2723'), 2: ('#453b2a', '#2a2a28')}
DROOP = 14.0                        # degrees the head hangs, about the base of its neck
DROOP_AT = (0.0, 0.03, -0.17)       # (head space)
LOOSE = {'m': {'knot': 'crop', 'tail': 'crop'},                     # the dead's hair: whatever tied it has rotted
         'f': {'knot': 'long', 'bun': 'long', 'tail': 'long'}}


def pose(sex, n=1, tag=None):
    """The shamble: hunched from the small of the back, the hips sunk, the left foot dragged ahead; the axe trailing
    from the right fist; the left arm hanging from its shoulder, loose."""
    f = BD.form(0.0 if sex == 'male' else 1.0, BLOAT if tag == 'bloated' else None)
    fr = BD.Frame(f)
    fr.sex = sex
    hf = fr.hf
    fr.hunch(bend=26.0 + 4.0 * (n - 1), pivot=1.0, drop=0.045 * hf, stride=0.13 * hf)
    J = fr.joints
    sh_r, sh_l = J['sh_r'], J['sh_l']
    fr.reach('r', (sh_r[0] - 0.08, sh_r[1] + 0.1 * hf, 0.66 * hf), pole=(-0.3, 0.6, -1.0),
             grip=np.array(AXE_DIR, np.float32))
    fr.reach('l', (sh_l[0] + 0.035, sh_l[1] - 0.05 * hf, sh_l[2] - 0.52 * hf), pole=(0.3, 0.8, -1.0))
    return fr


def _droop(H):
    """A head frame with the head hung forward about the base of its neck."""
    return (H @ Matrix.Translation(Vector(DROOP_AT)) @ Matrix.Rotation(math.radians(DROOP), 4, 'X')
            @ Matrix.Translation(-Vector(DROOP_AT)))


def head_frame(sex, portrait=False):
    return _droop(pose(sex).head_frame(portrait))


def corpse_look(look):
    """A look as the dead wear it: hair come loose where it was tied."""
    loose = LOOSE[look['form']].get(look['style'])
    return dict(look, style=loose) if loose else look


def _holes(seed, scale, cut):
    """Rot and tears through a garment: a region test, positive (no cloth) where the noise runs over `cut`."""
    nz = F._Noise(seed)
    return lambda P: ((nz(P, scale) - cut) * 0.08).astype(np.float32)


def _near(P, a, b, r):
    """Within r of the segment a-b."""
    ab = b - a
    t = np.clip(((P - a) @ ab) / float(ab @ ab), 0.0, 1.0)
    return np.linalg.norm(P - (a + t[:, None] * ab), axis=1) < r


def _spine(fr):
    """The hunch as a matrix: the upright upper body carried into the posed figure (as Frame.head_frame does)."""
    bend, pv, drop = fr.spine
    return (Matrix.Translation(Vector((pv[0], pv[1], pv[2] - drop))) @ Matrix.Rotation(math.radians(bend), 4, 'X')
            @ Matrix.Translation(-Vector(pv)))


def _ring(D, fr, zu, clear, n=40):
    """A closed path round the hunched trunk at height zu of the upright body (a strap lashed round it), `clear` off
    the skin: (points, outward normals) in the posed figure."""
    a = np.radians(np.arange(n) * 360.0 / n)
    R = fr._spine_R()
    dirs = (np.column_stack((np.cos(a), np.sin(a), np.zeros(n))) @ R.T).astype(np.float32)
    O = np.tile(fr.from_upper(np.array((0.0, 0.02, zu), np.float32)), (n, 1))
    r = D.outer(O, dirs, clear, arms=False)
    return [Vector(O[i] + dirs[i] * r[i]) for i in range(n)], [Vector(dv) for dv in dirs]


def build(v, seed=7, turn=-4.0, look=None, head=True):
    """One variant (VARIANTS). look: the head's look; by default the variant's own, from the enemy pool."""
    sex = v.get('sex', 'male')
    n, tag = v.get('n', 1), v.get('tag')
    form = 'm' if sex == 'male' else 'f'
    M.set_mode(revenant=True, corpse=True)
    fr = pose(sex, n, tag)
    hf = fr.hf
    D = GB.dressed(fr)
    H = _droop(fr.head_frame(v.get('portrait') or v.get('level')))
    seed = seed + 17 * n + (5 if form == 'f' else 0)
    if look is None:
        look = LK.foe(form, 3 * n + (1 if tag else 0), rough=False)     # the dead are dealt as rolled
    look = corpse_look(look)

    def up(P):          # posed points in the upright upper body's own space
        return fr.to_upper(P)

    # ---------------------------------------------------------------- materials
    skin = G.skin(f'husk_skin_{look["id"]}', look['skin_hex'], windburn=0.0, dirt=1.0, rot=1.0, seed=seed)
    shirt_c, breech_c = RAGS[n]
    shirt = G.cloth(f'husk_shirt{n}', color=shirt_c, blood=0.5, mud=2.2, grime=0.9, seed=seed + 1)
    breech = G.cloth(f'husk_breech{n}', color=breech_c, blood=0.4, mud=3.0, grime=0.9, seed=seed + 6)
    shroud = G.cloth('shroud', color='#b0a78e', blood=0.3, mud=2.6, grime=1.0, seed=seed + 2)
    rope = G.cloth('rope', color='#6e6250', blood=0.1, mud=1.2, grime=0.6, seed=61)
    axehead = G.steel('axehead', color='#4a4642', rust=1.3, blood=0.7, seed=seed + 3, edge=0.3, scratch=0.5, dirt=0.9)
    haft = G.wood('haft', color='#4a3a2a', seed=48)
    wrap = G.leather('wrap', color='#2e2219', seed=41)
    scrap = G.steel('scrap', color='#4f4d4a', rust=1.4, blood=0.4, seed=seed + 4, edge=0.4, dents=1.2, dirt=0.9)
    old_gilt = G.brass('old_gilt', color='#4c3b1c', tarnish=1.0, blood=0.25, seed=14, film=0.6)

    fig = K.root('figure')
    parts = [D.skin('husk_body', skin)]

    # ---------------------------------------------------------------- rags on the body, torn and rotted through
    hands = D.hands(cuff=0.03)
    holes = _holes(seed + 11, 5.0, 0.78)        # rarely: rags read by their torn edges, not by holes
    ragged = F._Noise(seed + 13)
    belly = None
    if tag == 'bloated':        # the shirt burst open over the belly, its edges torn
        belly = lambda P: (0.1 + 0.03 * (ragged(P, 26.0) - 0.5)                                         # noqa: E731
                           - np.sqrt((P[:, 0] / 1.15) ** 2 + ((P[:, 2] - 1.1 * hf) / 1.35) ** 2)
                           - 10.0 * np.maximum(P[:, 1], 0.0))
    J = fr.joints
    # sleeves: the left torn at mid-forearm, the right torn off above the elbow (each: the cut along a -> b, and the
    # lengths of arm it applies to)
    tears = [(J['el_l'], J['wr_l'], 0.45, [(J['el_l'], J['wr_l'])]),
             (J['sh_r'], J['el_r'], 0.62, [(J['sh_r'], J['el_r']), (J['el_r'], J['wr_r'])])]

    def shirt_region(P):
        U = up(P)
        rho = np.sqrt(U[:, 0] ** 2 + 1.3 * (U[:, 1] - 0.005) ** 2)
        r = np.maximum(np.minimum(0.085 - rho, U[:, 2] - 1.46 * hf), U[:, 2] - 1.56 * hf)   # the collar
        r = np.maximum(r, -hands(P))
        r = np.maximum(r, 0.86 * hf + 0.07 * hf * (ragged(P, 8.0) - 0.5) - P[:, 2])     # a ragged hem at the hips
        r = np.maximum(r, holes(P))
        # torn open down the breast: a ragged V from the collar, a little off the centre line
        z0 = 1.2 * hf
        w = 0.09 * np.clip((U[:, 2] - z0) / (0.29 * hf), 0.0, 1.0) + 0.02 * (ragged(U, 24.0) - 0.5)
        rip = np.where((U[:, 1] < -0.02) & (U[:, 2] > z0), w - np.abs(U[:, 0] - 0.02), -1.0)
        r = np.maximum(r, rip)
        for a, b, t, segs in tears:
            L = float(np.linalg.norm(b - a))
            u = (b - a) / L
            past = (P - a) @ u - t * L + 0.025 * (ragged(P, 30.0) - 0.5)
            arm = np.zeros(len(P), bool)
            for s0, s1 in segs:
                arm |= _near(P, s0, s1, 0.085)
            r = np.where(arm & (past > 0), np.maximum(r, past), r)
        if belly is not None:
            r = np.maximum(r, belly(P))
        return r
    parts.append(D.layer('rags_shirt', shirt, lambda P: np.full(len(P), 0.0065, np.float32), shirt_region, inner=0.003,
                         tris=10000, smooth=45))     # over the breeches where they meet

    def breech_region(P):
        side = np.where(P[:, 0] < 0.0, 0.52, 0.38) * hf         # the right leg torn off above the knee
        low = side + 0.06 * hf * (ragged(P, 9.0) - 0.5)
        return np.maximum(np.maximum(low - P[:, 2], P[:, 2] - 1.0 * hf), -D.arms(1.2)(P))
    parts.append(D.layer('rags_breeches', breech, lambda P: np.full(len(P), 0.0045, np.float32), breech_region,
                         inner=0.003, tris=9000, smooth=45))
    zb = 1.0 * hf - 0.045 * hf
    bp, bn = D.ring(zb, 0.012, n=40)
    parts.append(GB.cord('rope_belt', bp, 0.008, rope, closed=True))

    # ---------------------------------------------------------------- the shroud, hanging in tatters from the shoulders
    oy = float(J['sh_l'][1] + J['sh_r'][1]) / 2.0            # its axis down the hunched shoulders, not the hips
    top = float(fr.from_upper(np.array((0.0, 0.08, 1.5 * hf), np.float32))[2])
    sh = GB.Drape(D, top, 0.5 * hf, [22.0 + 4.0 * k for k in range(35)], 0.022, rows=24, oy=oy, collar=(0.075, 0.0),
                  flare=0.05, folds=0.018, fold_n=8, ragged=0.09, seed=seed + 5)
    parts.append(sh.mesh('shroud', shroud, thick=0.004))

    # ---------------------------------------------------------------- the axe, dragged
    parts += K.axe('axe', Vector(fr.fist('r')), AXE_DIR, (axehead, haft, wrap), haft=0.76, head_scale=2.0)

    # ---------------------------------------------------------------- tier looks
    if tag == 'ironbound':          # scrap plate lashed on: a rusted breastplate over the rags, a pauldron
        def plate_region(P):
            U = up(P)
            r = np.maximum(np.maximum(1.1 * hf - U[:, 2], U[:, 2] - 1.42 * hf), U[:, 1] + 0.02)
            return np.maximum(r, -D.arms(1.15)(P))
        parts.append(D.layer('scrap_plate', scrap, lambda P: np.full(len(P), 0.011, np.float32), plate_region,
                             inner=-0.008, feather=0.002, floor=0.95, tris=6000, smooth=35))
        shl = Vector(fr.upright().joints['sh_l']) + Vector((0.01, 0.0, 0.03 * hf))
        pd = A.pauldron('pauldron', shl, 1, scrap, old_gilt, size=0.9, lames=2, seed=seed)
        S = _spine(fr)
        for ob in pd:
            ob.matrix_world = S @ ob.matrix_world
        parts += pd
        for zu in (1.2, 1.36):
            rp, rn = _ring(D, fr, zu * hf, 0.024)
            parts += A.strap('lashing', rp, rn, 0.022, 0.004, wrap, closed=True)
    if tag == 'bloated':            # split open down the belly, the Blight glowing in the split and the boils
        glow = M.emissive('bloat_glow', '#b98cf0', 3.0)
        rnd = np.random.default_rng(seed)
        for k in range(7):
            a = math.radians(-90.0 + rnd.uniform(-55.0, 55.0))
            p, nrm = D.on(math.degrees(a), rnd.uniform(1.0, 1.22) * hf, 0.002)
            parts.append(K.sphere('boil', tuple(p), rnd.uniform(0.008, 0.016), glow, scale=(1.0, 0.6, 1.2), seg=10,
                                  rings=6))
        sp, sn = D.on(-96.0, 1.08 * hf, -0.006)
        parts.append(K.sphere('split', tuple(sp), 0.03, glow, scale=(0.3, 0.55, 1.6), seg=12, rings=8))
        bp_, bn_ = D.on(-90.0, 1.1 * hf, 0.02)
        parts.append(K.glow('belly_light', bp_, '#b98cf0', 0.35, radius=0.02))

    # ---------------------------------------------------------------- the head
    if head:
        # the neck alone, no yoke: hanging, the head would lift one out of the back
        hroot, info = LK.build_head(look, tag=f'husk_{look["id"]}', yoke=False, rot=1.0)
        hroot.matrix_world = H
        parts.append(hroot)
        bloom = M.halo('husk_eye_bloom', '#c69cf0', 2.2, 0.7, 1.4)
        for e in info['eyes']:      # the two violet points: a bloom round each eye, so they hold at the game's sizes
            ob = K.sphere('eye_bloom', tuple(H @ (e + Vector((0.0, -0.012, 0.0)))), 0.02, bloom, seg=16, rings=10)
            ob.visible_shadow = False
            parts.append(ob)
    parts.append(K.glow('face_glow', H @ Vector((0.0, -0.1, 0.01)), '#b98cf0', 0.22, radius=0.012))

    K.parent(parts, fig)
    fig.scale = (FIG_SCALE,) * 3
    fig.rotation_euler.z = math.radians(turn)
    return fig
