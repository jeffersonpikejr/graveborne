"""BLIGHT-SORCERER. Wave 2, asset #18: the Conclave's highest rank in the field.

Brief: the Conclave robe grown long, its hem trailing behind over the ground; the hood deep over a bone mask and
crowned with bone horns, the two at the temples sweeping out past the shoulders; both arms grafted to the shoulder and
raised open at the sides, and three ashfires turning about the figure on a tilted ring, embers trailing behind each.
At 26 px a Sorcerer is the horned hood and three violet fires round a long grey robe.

Built on the Conclave kit (gb/conclave.py). Both forms, two looks: 1 an ash-grey robe and an oval mask, 2 a
cinder-dark robe under a paler mantle and a long mask, the ring of fires turned the other way.
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
        VARIANTS[f'foe_blightsorc_{_n}_{_f}'] = dict(sex=_sex, n=_n)

# where the three fires hang (x, y, z on the male anchor's scale): low by the left hand, high by the right shoulder,
# over and behind the crown
FIRES = ((0.56, -0.14, 1.0), (-0.5, -0.1, 1.52), (0.1, 0.36, 1.98))


def pose(sex):
    """Both forearms raised out at the sides, the palms open and turned up."""
    fr = BD.Frame(sex)
    hf, f = fr.hf, fr.f
    fr.reach('l', (f['shoulder'] + 0.22, -0.2 * hf, 1.14 * hf), pole=(0.5, 0.45, -1.0))
    fr.open_hand('l', (0.6, -0.8, 0.12), (0.0, 0.0, 1.0))
    fr.reach('r', (-(f['shoulder'] + 0.22), -0.2 * hf, 1.2 * hf), pole=(-0.5, 0.45, -1.0))
    fr.open_hand('r', (-0.6, -0.8, 0.12), (0.0, 0.0, 1.0))
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
    seed = seed + 41 * n + (5 if form == 'f' else 0)
    mt = CC.materials(n)
    fig = K.root('figure')
    parts = []

    rb = CC.robe(D, fr, mt, parts, seed=seed, grafts=('l', 'r'), cut=0.12, glow=2.8, hem=0.035, flare=0.13)
    parts.append(CC.train('train', rb['skirt'], mt['robe'], 0.16 * hf, length=0.62, seed=seed,
                          **(dict(a0=-25.0, a1=140.0, peak=50.0) if n == 1 else dict(a0=40.0, a1=205.0, peak=130.0))))
    CC.mantle_hood(D, fr, H, mt, parts, seed=seed, low=1.24, ragged=0.035)
    parts += CC.horn_crown('crown', H, mt['bone'], mt['old_bone'], seed=seed)

    s = -1.0 if n == 2 else 1.0
    parts += CC.orbit('ashfire', [Vector((x * s, y, z * hf)) for x, y, z in FIRES], seed=seed)

    if head:
        parts.append(CC.masked_head(H, mt, kind=('oval', 'long')[n - 1]))

    K.parent(parts, fig)
    fig.scale = (FIG_SCALE,) * 3
    fig.rotation_euler.z = math.radians(turn)
    return fig
