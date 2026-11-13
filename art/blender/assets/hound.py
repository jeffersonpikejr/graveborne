"""BLIGHT-HOUND. Wave 2, asset #9 (step 6 of the enemy plan, the Beasts): the Outriders' pack.

Brief (in the Line-Breaker's register): a dog the Blight got up again. A deep chest gone to ribs, one flank laid open
to the bone; the waist tucked up to nothing, the backbone and the hip bones standing out of a mangy grey-green hide
that keeps its fur only in patches along the neck and the back; bone spines burst through down the spine, longest over
the withers; the head carried low on a prowl, the jaw hung open on its fangs, two violet eye points. At 26 px a hound
is the dog (low, long, four legs and a tail, turned so its length shows), its spines and its eyes.

A beast ships two seeds and no forms (ASSETS.md): foe_hound_1 prowls with its head low, foe_hound_2 stands with its
head up and turned. The quadruped rig is gb/beast.py's (Quad, hound), which houndrider.py mounts at x1.4. Corpse mode
throughout, with no revenant flag: no violet back-light.
"""
import math

from gb import beast as BE
from gb import grit as G
from gb import kit as K
from gb import mat as M

FIG_SCALE = 0.6
SIZE = 1.15         # a hound the size of a small pony: it has to read as the dog at 26 px

VARIANTS = {'foe_hound_1': dict(n=1), 'foe_hound_2': dict(n=2)}

# per seed: the pose (beast.Quad), the turn that shows its length, the hide and the fur
SEEDS = {
    1: dict(pose=dict(stride=(0.09, -0.06, -0.07, 0.08), head=(0.0, -0.61, 0.64), pitch=24.0, yaw=16.0, jaw=18.0,
                      tail=(0.05, 0.0), wound=1, torn=-1), turn=-34.0, hide='#6f7a5e', fur='#4f4a3c'),
    2: dict(pose=dict(stride=(-0.05, 0.08, 0.07, -0.06), head=(0.0, -0.57, 0.80), pitch=10.0, yaw=20.0, jaw=12.0,
                      tail=(-0.06, 0.1), wound=1, torn=1), turn=-26.0, hide='#687458', fur='#45413a'),
}


def materials(n, seed, hide, fur):
    return (G.skin(f'hound_hide{n}', hide, windburn=0.0, dirt=1.0, rot=1.0, seed=seed),
            G.hair(f'hound_fur{n}', fur, seed=seed + 1, flow='back'),
            G.cloth('hound_bone', color='#b9ae95', blood=0.25, mud=0.3, grime=0.7, kind='bone', seed=seed + 2))


def build(v, seed=7, turn=None, look=None, head=True):
    """One variant (VARIANTS)."""
    n = v.get('n', 1)
    sd = SEEDS[n]
    M.set_mode(revenant=True, corpse=True)
    seed = seed + 23 * n
    hide, fur, bone = materials(n, seed, sd['hide'], sd['fur'])
    q = BE.Quad(**sd['pose'])
    parts, _ = BE.hound('hound', q, hide, fur, bone, seed=seed, spines=1.0)
    fig = K.root('figure')
    K.parent(parts, fig)
    fig.scale = (FIG_SCALE * SIZE,) * 3
    fig.rotation_euler.z = math.radians(sd['turn'] if turn is None else turn)
    return fig
