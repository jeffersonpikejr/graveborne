"""The Risen's iron: what the Graveguard wears and carries over the Fighter's plate shells (ASSETS.md, the enemy plan).

great_helm(): a great helm closed over the whole head, its eye slit lit blight-violet from within (the Risen's eyes
are violet points; here the slit is the only light on the figure), a bar down its front, in two cuts: 'sugarloaf'
(a rounded point) and 'barrel' (flat-topped). halberd(): a hafted axe blade, a beak behind it and a long spike, held
upright with its butt on the ground. iron(): the black, corroded plate materials (use them under
mat.set_mode(corpse=True), which sinks them further toward black iron).
"""
import math

from mathutils import Matrix, Vector

from . import armor as A
from . import grit as G
from . import kit as K
from . import mat as M

SLIT = (-0.006, 0.016)          # the eye slit's lower and upper edge (head space, an unscaled head)
HELM_AXIS = 0.012               # the helm's axis (y), and its half-width and half-depth at the slit
HELM_RX, HELM_RY = 0.1, 0.12
VIOLET = '#b98cf0'


def iron(n=1):
    """Black corroded plate (look 2 rustier): plate, lames, maille, rivets, the halberd's steel."""
    r = 0.25 * (n - 1)
    return dict(
        plate=G.steel(f'grave_plate{n}', color='#414245', rough=0.5, rust=1.0 + r, blood=0.12, seed=1 + n, edge=1.2,
                      dents=1.1, dirt=0.75, pits=1.6),
        lames=G.steel(f'grave_lames{n}', color='#37383b', rough=0.52, rust=1.2 + r, blood=0.15, seed=2 + n, edge=1.1,
                      dents=1.0, dirt=0.8, pits=1.6),
        helm=G.steel(f'grave_helm{n}', color='#48494c', rough=0.46, rust=0.9 + r, blood=0.05, seed=5 + n, edge=1.3,
                     dents=0.9, dirt=0.6, pits=1.4),
        mail=G.maille('grave_maille', color='#3a3b3d', rust=0.9),
        rivet=G.steel('grave_rivet', color='#5a4a3c', rough=0.6, rust=1.4, blood=0.0, seed=14, edge=0.8),
        blade=G.steel('grave_blade', color='#5b5d60', rough=0.4, rust=0.9, blood=0.5, grime=0.8, seed=8, dents=0.4,
                      edge=1.3),
    )


def great_helm(name, H, iron_mat, rivet_mat, kind='sugarloaf', seed=0, glow=3.2, bloom=True):
    """A great helm on a head placed by H (the head's frame, its scale in it): a barrel of plate from the collar to
    over the crown, a prow down its front, the eye slit across the face lit violet from within and crossed by an iron
    bar. Returns the parts."""
    rx, sy = HELM_RX, HELM_RY / HELM_RX
    LOC = (0.0, HELM_AXIS, 0.0)

    def prow(i, a):
        return (0.011 * max(0.0, -math.sin(a)) ** 6, 0.0)

    lower = K.lathe(name + '_face', [(rx * 0.99, -0.168), (rx * 1.0, -0.16), (rx * 1.02, -0.09), (rx * 1.03, SLIT[0])],
                    iron_mat, seg=44, sy=sy, loc=LOC, cap_bottom=False, cap_top=False, jitter=prow)
    if kind == 'barrel':
        top = [(rx * 1.03, SLIT[1]), (rx * 1.02, 0.06), (rx * 1.0, 0.106), (rx * 0.94, 0.12), (rx * 0.6, 0.127),
               (0.002, 0.13)]
    else:
        top = [(rx * 1.03, SLIT[1]), (rx * 1.0, 0.065), (rx * 0.9, 0.11), (rx * 0.68, 0.148), (rx * 0.36, 0.172),
               (0.002, 0.182)]
    upper = K.lathe(name + '_skull', top, iron_mat, seg=44, sy=sy, loc=LOC, cap_bottom=False, cap_top=False, jitter=prow)
    back = K.lathe(name + '_nape', [(rx * 1.03, SLIT[0] - 0.002), (rx * 1.03, SLIT[1] + 0.002)], iron_mat, seg=36,
                   sy=sy, loc=LOC, arc=(-24.0, 204.0), cap_bottom=False, cap_top=False)
    for ob in (lower, upper, back):
        A.solid(ob, 0.005, -1.0)
    slit = K.lathe(name + '_slit', [(rx * 1.0, SLIT[0] - 0.004), (rx * 1.0, SLIT[1] + 0.004)],
                   M.emissive('grave_slit', VIOLET, glow), seg=36, sy=sy, loc=LOC, arc=(-158.0, -22.0), cap_bottom=False,
                   cap_top=False, jitter=prow)
    slit.visible_shadow = False
    parts = [lower, upper, back, slit]
    yf = HELM_AXIS - HELM_RY * 1.03 - 0.011
    parts.append(K.rbox(name + '_bar', (0.02, 0.008, 0.2), (0.0, yf - 0.002, -0.02), iron_mat, bev=0.003))
    rp = []
    for k in range(18):         # rivets round the brow and the collar
        a = 2.0 * math.pi * (k + 0.5) / 18.0
        pr = 0.011 * max(0.0, -math.sin(a)) ** 6
        for z, g in ((SLIT[1] + 0.014, 1.045), (-0.15, 1.02)):
            rp.append(Vector(((rx * g + pr) * math.cos(a), HELM_AXIS + (rx * g + pr) * sy * math.sin(a), z)))
    for k in range(6):          # the breaths, down the right of the face
        rp.append(Vector((-0.03 - 0.012 * (k % 2), yf + 0.012 + 0.004 * (k % 2), -0.05 - 0.016 * (k // 2))))
    parts.append(A.rivets(name + '_rivets', rp, 0.0042, rivet_mat))
    if kind == 'barrel':        # a cross of iron straps over the flat crown
        for rot in (0.0, math.pi / 2.0):
            parts.append(K.rbox(name + '_strap', (0.19, 0.022, 0.006), (0.0, HELM_AXIS, 0.129), iron_mat,
                                rot=Matrix.Rotation(rot, 4, 'Z'), bev=0.002))
    if bloom:                   # two blooms before the slit, so the violet holds at the game's sizes
        halo = M.halo('grave_eye_bloom', '#c69cf0', 2.2, 0.7, 1.4)
        for s in (-1.0, 1.0):
            ob = K.sphere(name + '_bloom', (0.036 * s, yf + 0.006, 0.005), 0.021, halo, seg=16, rings=10)
            ob.visible_shadow = False
            parts.append(ob)
    for ob in parts:
        ob.matrix_world = H @ ob.matrix_world
    return parts


def halberd(name, grip, up, length, shaft, steel, wrap, out=(-1.0, 0.0, 0.0), butt_z=0.03):
    """A halberd held upright in a fist at `grip`, its butt on the ground: an ash haft `length` long, langets, a broad
    axe blade toward `out`, a beak behind it, and a long spike above. Returns the parts."""
    d, o, n = K._basis(up, out)
    G_ = Vector(grip)
    butt = G_ - d * ((G_.z - butt_z) / max(d.z, 1e-3))
    top = butt + d * length
    parts = [K.tube(name + '_haft', butt, top, 0.0175, 0.016, shaft, seg=12),
             K.tube(name + '_wrap', G_ - d * 0.09, G_ + d * 0.09, 0.0195, 0.0195, wrap, seg=12),
             K.tube(name + '_socket', top - d * 0.36, top + d * 0.02, 0.021, 0.019, steel, seg=10),
             K.tube(name + '_shoe', butt - d * 0.02, butt + d * 0.07, 0.012, 0.02, steel, seg=10)]
    at = top - d * 0.32
    blade = [(0.014, 0.0), (0.06, -0.035), (0.15, -0.075), (0.185, 0.03), (0.19, 0.15), (0.165, 0.265), (0.07, 0.215),
             (0.014, 0.2)]
    parts.append(K.plate(name + '_blade', blade, at, d, o, 0.012, steel))
    beak = [(-0.014, 0.15), (-0.07, 0.14), (-0.15, 0.075), (-0.085, 0.092), (-0.014, 0.08)]
    parts.append(K.plate(name + '_beak', beak, at, d, o, 0.012, steel))
    spike = K.blade(name + '_spike', 0.3, 0.04, 0.013, steel, secs=[(0.0, 0.7), (0.15, 1.0), (0.6, 0.6), (1.0, 0.0)])
    x = o
    M3 = Matrix((x, d.cross(x), d)).transposed().to_4x4()
    A.place(spike, top, M3)
    parts.append(spike)
    return parts
