"""Painted-miniature materials.

Every surface is built the way a tabletop mini is painted: a base coat, a dark wash pooled in the recesses
(ambient occlusion), a highlight drybrushed onto convex edges (Cycles pointiness), and some grime. At 26px that
edge/recess contrast is the difference between a solid painted object and a smooth CG blob.

Colours are authored as the game's sRGB hex values so renders stay on the index.html palette.

Revenant mode (set_mode(revenant=True)) corrupts every material the same way the game's SVG revenants are
corrupted: colour drained toward a cold grave-grey, skin gone pale, blight-violet light leaking from cracks.
"""
import bpy

MODE = {'revenant': False}
_CACHE = {}

# the game's palette (index.html :root and the battle-token colours)
PAL = {
    'gold': '#c9a227', 'blood': '#a33b2e', 'blight': '#7a4fa3', 'blight_hi': '#b08bc9', 'green': '#5f7a3a',
    'steel': '#7d93a3', 'ink': '#d8cdb8', 'line': '#3a3226', 'ground': '#28241b', 'road': '#37301f',
    # base-rim team colours: company / living foe / undead foe / revenant / charge (ally)
    'team_company': '#4f6578', 'team_foe': '#8e3b24', 'team_undead': '#56693f', 'team_rev': '#7a4fa3',
    'team_ally': '#8f7a4c',
}


def set_mode(revenant=False):
    MODE['revenant'] = revenant
    _CACHE.clear()


def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hexlin(h):
    h = h.lstrip('#')
    return tuple(srgb_to_lin(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4))


def _corrupt(lin, kind):
    """Revenant palette shift: drain toward a cold grave-grey. Skin goes the game's revenant pale."""
    if kind == 'skin':   # grave-pale, but keeping each colour's lightness: sockets, lips and creases stay dark
        pale = hexlin('#8e988c')
        lum = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
        k = min(1.25, max(0.12, lum / 0.2))
        return tuple(c * k for c in pale)
    grave = hexlin('#5d6460')
    k = 0.55 if kind != 'metal' else 0.35
    return tuple((1 - k) * c + k * g for c, g in zip(lin, grave))


def _sock(node, ident):
    for s in node.inputs:
        if s.identifier == ident:
            return s
    raise KeyError(ident)


def _mix(nt, blend, a, b, fac=1.0):
    m = nt.nodes.new('ShaderNodeMix')
    m.data_type = 'RGBA'
    m.blend_type = blend
    if isinstance(fac, (int, float)):
        _sock(m, 'Factor_Float').default_value = float(fac)
    else:
        nt.links.new(fac, _sock(m, 'Factor_Float'))
    for ident, v in (('A_Color', a), ('B_Color', b)):
        if isinstance(v, tuple):
            _sock(m, ident).default_value = (*v, 1.0)
        else:
            nt.links.new(v, _sock(m, ident))
    return next(s for s in m.outputs if s.identifier == 'Result_Color')


def _maprange(nt, src, a, b, c=0.0, d=1.0):
    m = nt.nodes.new('ShaderNodeMapRange')
    m.clamp = True
    m.inputs['From Min'].default_value = a
    m.inputs['From Max'].default_value = b
    m.inputs['To Min'].default_value = c
    m.inputs['To Max'].default_value = d
    nt.links.new(src, m.inputs['Value'])
    return m.outputs['Result']


def _math(nt, op, a, b=0.0):
    m = nt.nodes.new('ShaderNodeMath')
    m.operation = op
    for i, v in enumerate((a, b)):
        if isinstance(v, (int, float)):
            m.inputs[i].default_value = v
        else:
            nt.links.new(v, m.inputs[i])
    return m.outputs[0]


def _pattern_mask(nt, tco, pattern):
    """Heraldic charge mask in object space (x across, z up, origin at the device centre)."""
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tco.outputs['Object'], sep.inputs[0])
    x, z = sep.outputs['X'], sep.outputs['Z']
    if pattern == 'chevron':      # an inverted-V band
        v = _math(nt, 'ADD', z, _math(nt, 'MULTIPLY', _math(nt, 'ABSOLUTE', x), 1.15))
        d = _math(nt, 'ABSOLUTE', _math(nt, 'SUBTRACT', v, 0.045))
        return _maprange(nt, d, 0.026, 0.031, 1.0, 0.0)
    if pattern == 'roundel':
        r = _math(nt, 'SQRT', _math(nt, 'ADD', _math(nt, 'MULTIPLY', x, x), _math(nt, 'MULTIPLY', z, z)))
        return _maprange(nt, r, 0.040, 0.045, 1.0, 0.0)
    if pattern == 'pale':
        return _maprange(nt, _math(nt, 'ABSOLUTE', x), 0.022, 0.027, 1.0, 0.0)
    raise ValueError(pattern)


def painted(name, color, rough=0.65, metal=0.0, edge=0.35, wash=0.55, grime=0.18, bevel=0.0,
            hi=None, kind='cloth', bump=0.0, bump_scale=120.0, emit=None, emit_strength=0.0, cracks=None,
            pattern=None, charge=None, hem=None, corrupt=True):
    """A painted surface.

    kind:    'cloth' | 'leather' | 'metal' | 'skin' | 'wood' | 'stone' | 'earth' | 'bone' (drives the revenant
             corruption and default crack glow).
    pattern: optional heraldic charge painted in `charge` colour ('chevron' | 'roundel' | 'pale').
    hem:     optional (z_low, z_high) object-space band where the cloth is darkened with mud.
    corrupt: False exempts a surface from revenant mode (team-colour base rims must stay pure).
    """
    key = (name, MODE['revenant'])
    if key in _CACHE:
        return _CACHE[key]
    rev = MODE['revenant'] and corrupt
    base = hexlin(color)
    if rev:
        base = _corrupt(base, kind)

    m = bpy.data.materials.new(name + ('_rev' if rev else ''))
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N['Principled BSDF']

    geo = N.new('ShaderNodeNewGeometry')
    tco = N.new('ShaderNodeTexCoord')
    ao = N.new('ShaderNodeAmbientOcclusion')
    ao.only_local = True
    ao.samples = 16
    ao.inputs['Distance'].default_value = 0.035

    # base coat (optionally carrying a painted device)
    if pattern:
        ch = hexlin(charge)
        if rev:
            ch = _corrupt(ch, kind)
        base_col = _mix(nt, 'MIX', base, ch, _pattern_mask(nt, tco, pattern))
    else:
        base_col = base
    if hi:
        hic = _corrupt(hexlin(hi), kind) if rev else hexlin(hi)
    else:
        # a highlight RELATIVE to the base coat: dark cloth gets a dark lift, not a pale sheen
        lift = N.new('ShaderNodeVectorMath')
        lift.operation = 'MULTIPLY_ADD'
        if isinstance(base_col, tuple):
            lift.inputs[0].default_value = base_col
        else:
            L.new(base_col, lift.inputs[0])
        lift.inputs[1].default_value = (1.9, 1.9, 1.9)
        lift.inputs[2].default_value = (0.012, 0.011, 0.01)
        hic = lift.outputs[0]

    # edge highlight (convex) and wash (concave / occluded)
    edge_f = _math(nt, 'MULTIPLY', _maprange(nt, geo.outputs['Pointiness'], 0.52, 0.6), edge)
    wash_f = _maprange(nt, ao.outputs['AO'], 0.0, 1.0, 1.0 - wash, 1.0)

    # grime: soft blotches in object space
    nz = N.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 9.0
    nz.inputs['Detail'].default_value = 6.0
    nz.inputs['Roughness'].default_value = 0.6
    L.new(tco.outputs['Object'], nz.inputs['Vector'])
    grime_f = _maprange(nt, nz.outputs['Fac'], 0.35, 0.72, 1.0 - grime, 1.0)

    col = _mix(nt, 'MULTIPLY', base_col, wash_f)
    col = _mix(nt, 'MIX', col, hic, edge_f)
    col = _mix(nt, 'MULTIPLY', col, grime_f)
    if hem:   # mud creeping up a hem
        sep = N.new('ShaderNodeSeparateXYZ')
        L.new(tco.outputs['Object'], sep.inputs[0])
        mud = _maprange(nt, sep.outputs['Z'], hem[0], hem[1], 0.7, 0.0)
        col = _mix(nt, 'MIX', col, hexlin('#211a12'), _math(nt, 'MULTIPLY', mud, _maprange(nt, nz.outputs['Fac'], 0.3, 0.6, 0.6, 1.0)))
    L.new(col, bsdf.inputs['Base Color'])

    # roughness varies with the grime (dirty = duller)
    L.new(_maprange(nt, nz.outputs['Fac'], 0.3, 0.8, rough - 0.08, min(1.0, rough + 0.12)), bsdf.inputs['Roughness'])
    bsdf.inputs['Metallic'].default_value = metal
    bsdf.inputs['Specular IOR Level'].default_value = 0.5 if kind in ('metal', 'leather', 'skin') else 0.3

    normal_src = None
    if bevel > 0:
        bv = N.new('ShaderNodeBevel')
        bv.samples = 8
        bv.inputs['Radius'].default_value = bevel
        normal_src = bv.outputs['Normal']
    if bump > 0:
        if kind == 'metal':
            tex = N.new('ShaderNodeTexVoronoi')
            h_out = tex.outputs['Distance']
        else:
            tex = N.new('ShaderNodeTexNoise')
            tex.inputs['Detail'].default_value = 2.0
            h_out = tex.outputs['Fac']
        tex.inputs['Scale'].default_value = bump_scale
        L.new(tco.outputs['Object'], tex.inputs['Vector'])
        bp = N.new('ShaderNodeBump')
        bp.inputs['Strength'].default_value = bump
        bp.inputs['Distance'].default_value = 0.002
        L.new(h_out, bp.inputs['Height'])
        if normal_src is not None:
            L.new(normal_src, bp.inputs['Normal'])
        normal_src = bp.outputs['Normal']
    if normal_src is not None:
        L.new(normal_src, bsdf.inputs['Normal'])

    # emission: authored glow (eyes, ashfire) and, for revenants, blight light leaking from cracks
    if emit:
        bsdf.inputs['Emission Color'].default_value = (*hexlin(emit), 1.0)
        bsdf.inputs['Emission Strength'].default_value = emit_strength
    crack_amt = cracks if cracks is not None else {'skin': 1.0, 'cloth': 0.7, 'leather': 0.7, 'metal': 0.35,
                                                    'wood': 0.5, 'bone': 0.8}.get(kind, 0.0)
    if rev and crack_amt > 0 and not emit:
        vo = N.new('ShaderNodeTexVoronoi')
        vo.feature = 'DISTANCE_TO_EDGE'
        vo.inputs['Scale'].default_value = 5.0
        wv = N.new('ShaderNodeTexNoise')          # warp the cells so the cracks meander
        wv.inputs['Scale'].default_value = 4.0
        wv.inputs['Detail'].default_value = 3.0
        L.new(tco.outputs['Object'], wv.inputs['Vector'])
        vm = N.new('ShaderNodeVectorMath')
        vm.operation = 'MULTIPLY_ADD'
        vm.inputs[1].default_value = (0.25, 0.25, 0.25)
        L.new(wv.outputs['Color'], vm.inputs[0])
        L.new(tco.outputs['Object'], vm.inputs[2])
        L.new(vm.outputs[0], vo.inputs['Vector'])
        crack = _maprange(nt, vo.outputs['Distance'], 0.0, 0.018, 1.0, 0.0)
        patch = _maprange(nt, nz.outputs['Fac'], 0.56, 0.66)      # sparse: fissures in a few places, not a web
        bsdf.inputs['Emission Color'].default_value = (*hexlin('#b98cf0'), 1.0)
        L.new(_math(nt, 'MULTIPLY', _math(nt, 'MULTIPLY', crack, patch), 3.5 * crack_amt),
              bsdf.inputs['Emission Strength'])

    _CACHE[key] = m
    return m


def halo(name, color, strength=2.0, opacity=0.5, falloff=2.0, hollow=False):
    """A soft glow round a light (the ashfire): an emitting shell, densest where it is seen face-on and clear toward
    its rim, so on a transparent sprite it reads as the light's bloom. hollow: clear in the middle too, a ring round
    whatever burns inside it, so it adds its glow without veiling it. Give its object no shadow (visible_shadow)."""
    key = (name, MODE['revenant'])
    if key in _CACHE:
        return _CACHE[key]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    N.remove(N['Principled BSDF'])
    em = N.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*hexlin(color), 1.0)
    em.inputs['Strength'].default_value = strength
    tr = N.new('ShaderNodeBsdfTransparent')
    lw = N.new('ShaderNodeLayerWeight')
    lw.inputs['Blend'].default_value = 0.5
    face_on = _math(nt, 'POWER', _math(nt, 'SUBTRACT', 1.0, lw.outputs['Facing']), falloff)
    if hollow:
        face_on = _math(nt, 'MULTIPLY', face_on, _maprange(nt, lw.outputs['Facing'], 0.05, 0.45, 0.12, 1.0))
    mix = N.new('ShaderNodeMixShader')
    L.new(_math(nt, 'MULTIPLY', face_on, opacity), mix.inputs['Fac'])
    L.new(tr.outputs[0], mix.inputs[1])
    L.new(em.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], N['Material Output'].inputs['Surface'])
    _CACHE[key] = m
    return m


def emissive(name, color, strength=8.0):
    key = (name, MODE['revenant'])
    if key in _CACHE:
        return _CACHE[key]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (*hexlin(color), 1.0)
    bsdf.inputs['Emission Color'].default_value = (*hexlin(color), 1.0)
    bsdf.inputs['Emission Strength'].default_value = strength
    _CACHE[key] = m
    return m
