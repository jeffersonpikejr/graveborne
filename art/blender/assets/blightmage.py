"""BLIGHT-MAGE. Wave 2, asset #17: the Conclave's caster.

Brief: the Conclave robe, the hood deep over a bone mask, and both sleeves cut away at the shoulder: both arms grafted,
ash-grey and bruised violet, veined in violet light from the palms up. A staff of bone taller than its bearer, planted
upright in the right fist, a claw of ribs at its head cradling an ashfire; the left hand raised open before the body.
At 26 px a Mage is the grey hooded robe and a pale staff crowned with violet fire.

Built on the Conclave kit (gb/conclave.py). Both forms, two looks: 1 an ash-grey robe and an oval mask, 2 a
cinder-dark robe under a paler mantle and a long mask.
"""
import math

from mathutils import Vector

from gb import body as BD
from gb import conclave as CC
from gb import garb as GB
from gb import kit as K
from gb import mat as M

FIG_SCALE = 0.6

VARIANTS = {}
for _f, _sex in (('m', 'male'), ('f', 'female')):
    for _n in (1, 2):
        VARIANTS[f'foe_blightmage_{_n}_{_f}'] = dict(sex=_sex, n=_n)

STAFF_UP = (-0.05, -0.02, 1.0)


def pose(sex):
    """The staff upright in the right fist, held high; the left forearm raised, the palm open and turned up."""
    fr = BD.Frame(sex)
    hf, f = fr.hf, fr.f
    fr.reach('r', (-(f['shoulder'] + 0.12), -0.22 * hf, 1.24 * hf), pole=(-0.5, 0.45, -1.0), grip=STAFF_UP)
    fr.reach('l', (f['shoulder'] + 0.2, -0.24 * hf, 1.16 * hf), pole=(0.4, 0.45, -1.0))
    fr.open_hand('l', (0.45, -1.0, 0.1), (0.0, 0.0, 1.0))
    return fr


def head_frame(sex, portrait=False):
    return BD.Frame(sex).head_frame(portrait)


def build(v, seed=7, turn=-4.0, look=None, head=True):
    sex = v.get('sex', 'male')
    n = v.get('n', 1)
    form = 'm' if sex == 'male' else 'f'
    M.set_mode(revenant=False)
    fr = pose(sex)
    hf = fr.hf
    D = GB.dressed(fr)
    H = fr.head_frame(v.get('portrait') or v.get('level'))
    seed = seed + 37 * n + (5 if form == 'f' else 0)
    mt = CC.materials(n)
    fig = K.root('figure')
    parts = []

    CC.robe(D, fr, mt, parts, seed=seed, grafts=('l', 'r'), cut=0.16, glow=2.4)
    CC.mantle_hood(D, fr, H, mt, parts, seed=seed, low=1.3)

    sp, fire = CC.bone_staff('staff', Vector(fr.fist('r')), STAFF_UP, 2.0 * (0.4 + 0.6 * hf), mt['bone'],
                             mt['old_bone'], mt['wraps'], seed=seed)
    parts += sp
    parts += GB.ashfire('ashfire', fire, energy=1.4, seed=seed)

    if head:
        parts.append(CC.masked_head(H, mt, kind=('oval', 'long')[n - 1]))

    K.parent(parts, fig)
    fig.scale = (FIG_SCALE,) * 3
    fig.rotation_euler.z = math.radians(turn)
    return fig
