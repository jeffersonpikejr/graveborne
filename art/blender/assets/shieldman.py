"""SHIELDMAN. Wave 2, asset #8 (step 3 of the enemy plan, the Karsk deserters): the Shieldwall's anchor.

Brief: one of the Crown's levies who walked off with the kit and kept the drill. A mail hauberk under the slate tabard,
its badge unpicked to a darker ghost; plate on the arms; a mail coif worn up under a kettle hat (bare iron, or painted
slate); a tall slate heater, the Crown's device scraped off it back to the iron, set before the body on the left arm;
a flanged mace raised behind it. At 26 px a Shieldman is the tall slate shield under the brim of a kettle hat.

Built on the Karsk kit (gb/karsk.py) and the brigand kit's belt and look pool (brigand.py). Both forms, two looks each.
"""
import math

import numpy as np
from mathutils import Matrix, Vector

from gb import body as BD
from gb import garb as GB
from gb import grit as G
from gb import karsk as KK
from gb import kit as K
from gb import looks as LK
from gb import mat as M

import brigand as BR

FIG_SCALE = BR.FIG_SCALE

VARIANTS = {}
for _f, _sex in (('m', 'male'), ('f', 'female')):
    for _n in (1, 2):
        VARIANTS[f'foe_shieldman_{_n}_{_f}'] = dict(sex=_sex, n=_n)

MACE_DIR = (-0.1, -0.22, 0.97)      # raised: its head up over the shield's rim, a little forward
SHIELD = (0.62, 1.06)               # the heater's width and height (m)


def pose(sex):
    """The shield set: the knees bent, the left foot forward, the body braced; the left fist before the body at the
    waist (behind the heater), the right fist cocked beside the head, the mace up."""
    fr = BD.Frame(sex)
    fr.sex = sex
    hf = fr.hf
    fr.hunch(bend=6.0, pivot=1.0, drop=0.04 * hf, stride=0.14 * hf, spread=0.12)
    J = fr.joints
    sh_l, sh_r = J['sh_l'], J['sh_r']
    fr.reach('l', (sh_l[0] - 0.05, sh_l[1] - 0.31 * hf, sh_l[2] - 0.33 * hf), pole=(0.6, 0.2, -1.0),
             grip=np.array((1.0, 0.0, 0.0), np.float32))
    fr.reach('r', (sh_r[0] - 0.13, sh_r[1] - 0.08 * hf, sh_r[2] + 0.2 * hf), pole=(-1.0, 0.15, -0.9),
             grip=np.array(MACE_DIR, np.float32) / np.linalg.norm(MACE_DIR))
    return fr


def head_frame(sex, portrait=False):
    return pose(sex).head_frame(portrait)


def coifed(look):
    """A look as it is worn under a coif: the hair cut close, a full beard clipped."""
    return dict(look, style='buzz', recede=0.0, beard='stubble' if look['beard'] == 'full' else look['beard'])


def build(v, seed=7, turn=-4.0, look=None, head=True):
    """One variant (VARIANTS). look: the head's look; by default the variant's own, from the enemy pool."""
    sex = v.get('sex', 'male')
    n = v.get('n', 1)
    form = 'm' if sex == 'male' else 'f'
    M.set_mode(revenant=False)
    fr = pose(sex)
    hf = fr.hf
    D = GB.dressed(fr)
    H = fr.head_frame(v.get('portrait') or v.get('level'))
    seed = seed + 23 * n + (5 if form == 'f' else 0)
    if look is None:
        look = BR.look_for(form, 30 + n)
    look = coifed(look)
    mt = KK.materials()
    skin = G.skin(f'shld_skin_{look["id"]}', look['skin_hex'], windburn=look['windburn'], dirt=look['dirt'])
    fig = K.root('figure')
    parts = [D.skin('shld_body', skin)]
    drop = fr.spine[2]

    # ---------------------------------------------------------------- breeches, boots, the hauberk
    parts.append(D.layer('breeches', mt['breeches'], lambda P: np.full(len(P), 0.0035, np.float32),
                         lambda P: np.maximum(D.heights(0.1, 1.0)(P), -D.arms(1.2)(P)), inner=0.002, tris=9000))
    parts.append(D.layer('boots', mt['shoes'], lambda P: np.full(len(P), 0.006, np.float32),
                         lambda P: np.maximum(D.heights(-0.02, 0.36)(P), -D.arms(1.2)(P)), inner=-0.0015, tris=8000,
                         smooth=40))
    parts.append(D.layer('hauberk', mt['mail'], lambda P: np.full(len(P), 0.008, np.float32),
                         lambda P: np.maximum(BR.band(fr, D, 0.6, 1.545)(P), -D.hands(cuff=0.03)(P)), inner=0.003,
                         tris=15000, smooth=45))
    parts.append(D.layer('gauntlets', mt['iron'], lambda P: np.full(len(P), 0.005, np.float32), D.hands(cuff=0.05),
                         inner=0.002, tris=5000, smooth=40))

    # ---------------------------------------------------------------- the tabard, its badge unpicked to a ghost
    wdef = 0.0 if sex == 'male' else 0.02
    zb = (1.04 + 1.3 * wdef) * hf - drop
    front, back = KK.tabard(D, fr, zb, seed=seed, z_hem=0.7)
    parts.append(front.mesh('tabard_front', mt['tabard'], thick=0.005))
    parts.append(back.mesh('tabard_back', mt['tabard'], thick=0.005))
    parts.append(KK.decal('ghost', KK.on_drape(front, -90.0, 1.3 * hf - drop, 17.0, 0.055 * hf), mt['ghost'], n=22,
                          seed=seed))
    BR.belt(D, fr, zb, mt['leather'], mt['iron'], parts, clear=0.03)

    # ---------------------------------------------------------------- plate on the arms
    for side in 'lr':
        parts += KK.arm_plate(fr, side, mt['iron'], mt['dark'], seed=seed + (0 if side == 'l' else 1), lames=2)

    # ---------------------------------------------------------------- the coif and the kettle hat
    cape, z_bot = KK.mantle(D, fr, H, mt['mail'], seed=seed, z_hem=1.41)
    parts.append(cape)
    parts.append(KK.coif('coif', H, z_bot, mt['mail'], seed=seed))
    parts += KK.kettle_hat('hat', H, mt['hat_iron'] if n == 1 else mt['hat_paint'], mt['dark'], seed=seed, grow=0.009,
                           bash=0.004)
    if head:
        hroot, _ = LK.build_head(look, tag=f'shld_{look["id"]}', helm=True)
        hroot.matrix_world = H
        parts.append(hroot)

    # ---------------------------------------------------------------- the heater on the left arm, the mace raised
    w, h = SHIELD[0], SHIELD[1] * (0.5 + 0.5 * hf)
    sp_, zc = KK.heater('heater', w, h, mt['heater'], mt['dark'], mt['iron'], scraped=mt['scraped'], seed=seed)
    sroot = K.root('shield_root')
    K.parent(sp_, sroot)
    fist = Vector(fr.fist('l'))
    sroot.matrix_world = (Matrix.Translation(fist + Vector((-0.02, -0.02, -0.07))) @ Matrix.Rotation(math.radians(13.0), 4, 'Z')
                          @ Matrix.Rotation(math.radians(-7.0), 4, 'X') @ Matrix.Translation((0.0, -0.05, -zc)))
    parts.append(sroot)
    parts += K.mace('mace', Vector(fr.fist('r')), MACE_DIR, (mt['blade'], mt['wood'], mt['leather']), haft=0.6)

    K.parent(parts, fig)
    fig.scale = (FIG_SCALE,) * 3
    fig.rotation_euler.z = math.radians(turn)
    return fig
