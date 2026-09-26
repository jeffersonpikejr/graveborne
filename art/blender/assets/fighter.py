"""FIGHTER — asset #1 and the style anchor.

Every campaign opens on a Fighter who carries the banner, so this is the first figure every player sees.
Design carried over from the SVG token (v0.41/v0.45): steel nasal helm, red surcoat over mail, kite shield,
arming sword; the Commander flies the company's red-and-gold banner; a Revenant rises in exactly the same kit.

Reads at 26px by: steel helm cap (top), red surcoat (centre mass), pale kite shield (right), upright blade (left).
Heroic-scale proportions (big head, hands and weapon) on purpose: that is what survives the trip down to 26px.
"""
import math
from mathutils import Matrix, Vector

from gb import kit as K
from gb import mat as M
from gb.rig import BASE_H

FIG_SCALE = 1.22   # the figure against its base; the base itself stays one tile's worth of footprint

VARIANTS = {
    'fighter':                    {},
    'fighter_commander':          {'commander': True},
    'fighter_revenant':           {'revenant': True},
    'fighter_commander_revenant': {'commander': True, 'revenant': True},
    # weapon families a Fighter can carry (CLASSES.fighter.wpns); tier-2 upgrades share their family's look
    'fighter_axe':                {'weapon': 'axe'},
    'fighter_mace':               {'weapon': 'mace'},
    'fighter_spear':              {'weapon': 'spear'},
}


def build(v, skin='#a9825f', seed=7, turn=-8.0):
    rev = v.get('revenant', False)
    M.set_mode(revenant=rev)

    steel = M.painted('steel', '#6f767d', rough=0.42, metal=0.75, edge=0.7, wash=0.72, grime=0.32, bevel=0.003,
                      kind='metal')
    blade_steel = M.painted('blade', '#a2a7aa', rough=0.3, metal=0.85, edge=0.6, wash=0.5, grime=0.2, kind='metal')
    mail = M.painted('mail', '#4a4f55', rough=0.55, metal=0.75, edge=0.55, wash=0.8, grime=0.3, kind='metal',
                     bump=0.6, bump_scale=240.0)
    surcoat = M.painted('surcoat', '#6b231d', rough=0.92, edge=0.3, wash=0.65, grime=0.42, kind='cloth',
                        hem=(0.37, 0.48), bump=0.15, bump_scale=300.0)
    leather = M.painted('leather', '#35271a', rough=0.7, edge=0.4, wash=0.6, grime=0.25, kind='leather')
    boots = M.painted('boots', '#271d15', rough=0.75, edge=0.4, wash=0.6, grime=0.4, kind='leather')
    hose = M.painted('hose', '#2b2925', rough=0.9, edge=0.25, wash=0.6, grime=0.3, kind='cloth')
    skin_m = M.painted('skin', skin, rough=0.6, edge=0.25, wash=0.55, grime=0.12, kind='skin')
    brass = M.painted('brass', '#7d6230', rough=0.4, metal=0.85, edge=0.6, wash=0.55, grime=0.25, kind='metal')
    iron = M.painted('iron', '#34312d', rough=0.5, metal=0.7, edge=0.55, wash=0.5, grime=0.25, kind='metal')
    shield_face = M.painted('shield_face', '#8e846f', rough=0.82, edge=0.4, wash=0.6, grime=0.5, kind='wood',
                            pattern='chevron', charge='#5e1f1b')

    fig = K.root('figure')
    parts = []

    # ---- legs & boots (tall boots with a turned-down cuff)
    for sx, kz in ((-1, -0.012), (1, 0.012)):
        parts.append(K.skin_chain('leg', [(0.056 * sx, 0.0, 0.44), (0.07 * sx, kz, 0.27), (0.083 * sx, 0.01, 0.12)],
                                  [0.05, 0.041, 0.034], hose))
        parts.append(K.skin_chain('boot', [(0.075 * sx, 0.0, 0.23), (0.084 * sx, 0.01, 0.1),
                                           (0.088 * sx, -0.048, 0.062), (0.09 * sx, -0.088, 0.055)],
                                  [0.045, 0.041, 0.037, 0.029], boots))
        parts.append(K.lathe('cuff', [(0.047, 0.215), (0.052, 0.228), (0.05, 0.245)], leather, seg=20,
                             loc=(0.075 * sx, 0.0, 0.0), cap_bottom=False, cap_top=False))

    # ---- hauberk (mail, knee-length skirt) and the red surcoat over it
    parts.append(K.lathe('hauberk', [(0.108, 0.30), (0.101, 0.37), (0.093, 0.45), (0.089, 0.52), (0.106, 0.60),
                                     (0.113, 0.66), (0.1, 0.705), (0.06, 0.735), (0.04, 0.75)],
                         mail, seg=40, sx=1.0, sy=0.74, cap_bottom=False))

    def ragged(i, a):
        if i != 0:
            return (0.0, 0.0)
        return (0.004 * math.sin(a * 5), 0.014 * math.sin(a * 7 + 1.3) + 0.009 * math.sin(a * 13))
    parts.append(K.lathe('surcoat', [(0.117, 0.375), (0.108, 0.44), (0.099, 0.52), (0.115, 0.60),
                                     (0.121, 0.662), (0.107, 0.708), (0.072, 0.733)],
                         surcoat, seg=48, sx=1.0, sy=0.76, cap_bottom=False, cap_top=False, jitter=ragged))
    parts.append(K.lathe('belt', [(0.102, 0.502), (0.107, 0.509), (0.107, 0.531), (0.102, 0.538)],
                         leather, seg=40, sy=0.78, cap_bottom=False, cap_top=False))
    parts.append(K.rbox('buckle', (0.03, 0.012, 0.028), (0.0, -0.085, 0.52), brass, bev=0.003))

    # ---- arms (mail sleeves) and big gloved hands
    r_sh, r_el, r_wr = Vector((-0.12, 0.0, 0.672)), Vector((-0.162, -0.03, 0.545)), Vector((-0.152, -0.088, 0.45))
    l_sh, l_el, l_wr = Vector((0.12, 0.0, 0.672)), Vector((0.168, -0.05, 0.565)), Vector((0.107, -0.13, 0.55))
    parts.append(K.skin_chain('arm_r', [r_sh, r_el, r_wr], [0.045, 0.037, 0.031], mail))
    parts.append(K.skin_chain('arm_l', [l_sh, l_el, l_wr], [0.045, 0.037, 0.031], mail))
    hand_r = r_wr + Vector((0.002, -0.013, -0.024))
    parts.append(K.sphere('hand_r', hand_r, 0.035, leather, scale=(1.0, 1.1, 1.05)))
    parts.append(K.sphere('hand_l', l_wr + Vector((-0.012, -0.014, 0.0)), 0.033, leather, scale=(1.0, 1.1, 1.0)))
    for w in (r_wr, l_wr):     # leather bracers read as a darker band on the forearm
        parts.append(K.sphere('bracer', w + Vector((0, 0.004, 0.022)), 0.036, leather, scale=(1.0, 1.0, 1.3)))

    # ---- pauldrons: flat overlapping plates, tilted outward (plates, not balls)
    for sh, s in ((r_sh, -1), (l_sh, 1)):
        rot = Matrix.Rotation(math.radians(34 * s), 4, 'Y')
        top = K.lathe('pauldron', [(0.072, 0.0), (0.069, 0.011), (0.056, 0.024), (0.034, 0.033), (0.002, 0.036)],
                      steel, seg=32, sx=1.0, sy=0.92)
        top.matrix_world = Matrix.Translation(sh + Vector((0.014 * s, 0.0, -0.004))) @ rot
        lame = K.lathe('lame', [(0.074, 0.0), (0.073, 0.01), (0.066, 0.02)], steel, seg=32, sy=0.92,
                       cap_bottom=False, cap_top=False)
        lame.matrix_world = Matrix.Translation(sh + Vector((0.026 * s, 0.0, -0.036))) @ rot
        K.subsurf(top, 1)
        parts += [top, lame]

    # ---- head, mail coif (open at the face), conical nasal helm
    head_c = Vector((0.0, -0.004, 0.806))
    parts.append(K.sphere('head', head_c, 0.064, skin_m, scale=(0.95, 1.06, 1.06)))
    eye_m = (M.emissive('eyes_rev', '#c69cf0', 16.0) if rev
             else M.painted('eyes', '#120e0a', rough=0.4, kind='stone', cracks=0.0))
    for s in (-1, 1):
        parts.append(K.sphere('eye', head_c + Vector((0.021 * s, -0.058, 0.004)), 0.009 if rev else 0.0075,
                              eye_m, seg=10, rings=6))
    parts.append(K.lathe('coif', [(0.068, 0.80), (0.074, 0.772), (0.086, 0.748), (0.102, 0.724), (0.118, 0.705)],
                         mail, seg=36, sy=1.0, arc=(-58, 238)))
    parts.append(K.lathe('helm', [(0.075, 0.814), (0.075, 0.83), (0.069, 0.853), (0.057, 0.877), (0.037, 0.899),
                                  (0.015, 0.916), (0.002, 0.922)], steel, seg=40, sx=1.0, sy=1.08, cap_bottom=False))
    parts.append(K.lathe('helm_band', [(0.0775, 0.811), (0.0795, 0.817), (0.0795, 0.829), (0.0775, 0.833)],
                         iron, seg=40, sy=1.08, cap_bottom=False, cap_top=False))
    parts.append(K.rbox('nasal', (0.016, 0.012, 0.054), (0.0, -0.084, 0.793), steel, bev=0.003))

    # ---- weapon (right hand, held upright at guard) and kite shield (left arm)
    wood = M.painted('haft', '#4a3a26', rough=0.8, edge=0.4, wash=0.55, grime=0.25, kind='wood')
    weapon = v.get('weapon', 'sword')
    if weapon == 'axe':
        parts += K.axe('axe', hand_r, (-0.3, -0.14, 1.0), (blade_steel, wood, leather))
    elif weapon == 'mace':
        parts += K.mace('mace', hand_r, (-0.3, -0.14, 1.0), (steel, wood, leather))
    elif weapon == 'spear':
        parts += K.spear('spear', hand_r, (-0.1, -0.06, 1.0), (blade_steel, wood, leather))
    else:
        parts += K.sword('sword', hand_r, (-0.3, -0.14, 1.0), (blade_steel, leather, brass),
                         blade_len=0.34, blade_w=0.052, grip=0.06)
    sh = K.kite_shield('shield', 0.215, 0.34, shield_face, iron)
    sh.matrix_world = (Matrix.Translation((0.138, -0.182, 0.5)) @ Matrix.Rotation(math.radians(22), 4, 'Z')
                       @ Matrix.Rotation(math.radians(-7), 4, 'X'))
    parts.append(sh)

    # ---- the Commander's banner, slung across the back
    if v.get('commander'):
        wood = M.painted('pole', '#43341f', rough=0.8, edge=0.4, wash=0.55, grime=0.25, kind='wood')
        flag_m = M.painted('flag', '#6e2220', rough=0.95, edge=0.3, wash=0.6, grime=0.35, kind='cloth',
                           pattern='roundel', charge='#b8931f')
        foot, top = Vector((0.07, 0.085, 0.36)), Vector((0.112, 0.12, 1.1))
        parts.append(K.tube('pole', foot, top, 0.0105, 0.0095, wood, seg=10))
        parts.append(K.sphere('finial', top + Vector((0, 0, 0.012)), 0.015, brass, scale=(1, 1, 1.6), seg=12, rings=8))
        fl = K.banner('flag', 0.25, 0.15, flag_m, swallow=0.28)
        for vtx in fl.data.vertices:          # the roundel is drawn about the flag's origin: centre it
            vtx.co.x -= 0.1
            vtx.co.z += 0.075
        fl.location = top + Vector((0.108, 0.0, -0.095))
        parts.append(fl)

    if rev:   # blight light spilling out of the helm's face opening (the eyes themselves sit under the brim)
        parts.append(K.glow('face_glow', head_c + Vector((0.0, -0.075, -0.012)), '#b98cf0', 1.6, radius=0.015))

    K.parent(parts, fig)
    base = v.get('base', False)
    fig.scale = (FIG_SCALE,) * 3
    fig.location.z = (BASE_H if base else 0.0) - BASE_H * FIG_SCALE     # soles on the base top, or on the ground
    fig.rotation_euler.z = math.radians(turn)
    if base:
        K.mini_base(team='rev' if rev else 'company', seed=seed)
    return fig
