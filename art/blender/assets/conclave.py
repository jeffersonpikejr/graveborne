"""CONCLAVE ACOLYTE (game key `acolyte`). Wave 2, asset #12: the Conclave's bow.

Brief: the robe the company's runaway threw off, still worn: ash-grey wool, a mantle, the hood deep over a bone mask,
no face. One arm grafted (the bow arm, bare from mid upper arm, veined in violet light). A longbow at half-draw, the
arrow's head lit with ashfire; a quiver at the hip. At 26 px: a grey hooded robe, a pale mask, a bow held out and
drawn.

Built on the Conclave kit (gb/conclave.py). Both forms, two looks: 1 an ash-grey robe and an oval mask, 2 a
cinder-dark robe under a paler mantle and a long mask.
"""
import math

import numpy as np
from mathutils import Vector

from gb import body as BD
from gb import conclave as CC
from gb import garb as GB
from gb import grit as G
from gb import kit as K
from gb import mat as M

import brigand as BR

FIG_SCALE = BR.FIG_SCALE

VARIANTS = {}
for _f, _sex in (('m', 'male'), ('f', 'female')):
    for _n in (1, 2):
        VARIANTS[f'foe_acolyte_{_n}_{_f}'] = dict(sex=_sex, n=_n)

CANT = (0.3, -0.12, 0.94)       # the stave's lean: out to the left and a little toward the camera


def pose(sex):
    """The half-draw (as the Brigand Archer's): the bow arm out to the left, the draw hand back before the chest."""
    fr = BD.Frame(sex)
    fr.sex = sex
    hf = fr.hf
    fr.hunch(bend=4.0, pivot=1.0, drop=0.02 * hf, stride=0.12 * hf, spread=0.06)
    J = fr.joints
    sh_l = J['sh_l']
    up = np.array(CANT, np.float32) / np.linalg.norm(CANT)
    bow = np.array((sh_l[0] + 0.42, sh_l[1] - 0.26 * hf, sh_l[2] - 0.03), np.float32)
    draw = bow + np.array((-0.45, 0.07, -0.03), np.float32)
    fr.reach('l', bow, pole=(0.1, 0.6, -1.0), grip=up)
    fr.reach('r', draw, pole=(-1.0, 0.4, 0.15), grip=np.array((0.05, 0.1, 1.0), np.float32))
    fr.bow_up = up
    return fr


def head_frame(sex, portrait=False):
    return pose(sex).head_frame(portrait)


def build(v, seed=7, turn=-4.0, look=None, head=True):
    sex = v.get('sex', 'male')
    n = v.get('n', 1)
    form = 'm' if sex == 'male' else 'f'
    M.set_mode(revenant=False)
    fr = pose(sex)
    hf = fr.hf
    D = GB.dressed(fr)
    H = fr.head_frame(v.get('portrait') or v.get('level'))
    seed = seed + 31 * n + (5 if form == 'f' else 0)
    mt = CC.materials(n)
    bowwood = G.wood('conclave_bow', color='#a39a84', seed=44)       # a pale stave: it has to read on dark ground
    string = G.flat('bowstring', '#b3a88c')
    shaft = G.wood('shaft', color='#6f6250', seed=47)
    point = G.steel('arrowhead', color='#3a3b3e', rust=0.5, blood=0.2, seed=52, edge=0.6)
    fletch = G.cloth('fletch_ash', color='#8d897e', blood=0.0, mud=0.0, grime=0.2, seed=53)
    cock = G.cloth('fletch_bone', color=CC.PAL['bone'], blood=0.0, mud=0.0, grime=0.2, seed=54)
    fig = K.root('figure')
    parts = []

    rb = CC.robe(D, fr, mt, parts, seed=seed, grafts=('l',), cut=0.38, glow=2.2, band=BR.band(fr, D, 0.86, 1.545))
    CC.mantle_hood(D, fr, H, mt, parts, seed=seed, low=1.36)

    # the quiver at the right hip
    B = D.on(200.0, 0.62 * hf, 0.09)[0] + Vector((0.0, 0.03, 0.0))
    T = D.on(190.0, 1.03 * hf, 0.1)[0] + Vector((0.0, -0.02, 0.0))
    parts += GB.quiver('quiver', B, T, mt['leather'], mt['cord'], fletch, cock, shaft, point, n=8, r_top=0.045,
                       r_bot=0.034, seed=seed)

    # the bow at half-draw, an arrow on the string, its head lit
    grip = Vector(fr.fist('l'))
    hand = Vector(fr.fist('r'))
    up = Vector(fr.bow_up)
    nock = hand + (grip - hand).normalized() * 0.03
    side = (nock - grip)
    side = (side - up * side.dot(up)).normalized()
    bp_, _, _ = GB.longbow('bow', grip, up, side, 1.5 * hf, bowwood, mt['wraps'], mt['bone'], string, brace=0.15,
                           draw=nock)
    parts += bp_
    rest = grip - side * 0.012 + up.cross(side).normalized() * 0.018
    d = (rest - nock).normalized()
    parts += GB.arrow('arrow', nock, d, fletch, cock, shaft, point, length=0.74)
    parts += CC.ember('arrow_fire', nock + d * 0.72, r=0.012, energy=0.25)

    if head:
        parts.append(CC.masked_head(H, mt, kind=('oval', 'long')[n - 1]))

    K.parent(parts, fig)
    fig.scale = (FIG_SCALE,) * 3
    fig.rotation_euler.z = math.radians(turn)
    return fig
