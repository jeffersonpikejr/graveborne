"""Grit materials — battle-worn realism for the grimdark look.

Every surface is a base material plus the damage a campaign leaves on it, applied in this order:
  scratches and pitting -> polished edge wear -> grime packed into the recesses -> rust or tarnish ->
  oxblood smears -> mud climbing from the ground.
Masks are procedural in object space, so no two plates wear alike. Mud is measured in world space, so it climbs
every part of a figure from the same ground line.

The company palette (from the Line-Breaker brief): bone-white, cold ash-grey, oxblood, dull steel, muted earth;
tarnished gold only as rivets, repairs and mismatched trim.

Revenant mode (mat.set_mode) drains every colour toward grave-grey and lets blight-violet light leak through
cracks, exactly as the painted materials did.
"""
import bpy
from mathutils import Vector

from .mat import MODE, _CACHE, _corrupt, _mix, _maprange, _math, hexlin

COL = {
    'steel': '#6d6f71', 'steel_dark': '#434548', 'steel_edge': '#bfc1c2',
    'bone': '#c8bfa7', 'ash': '#6d6a66', 'oxblood': '#3c0c09', 'oxblood_dry': '#1c0605',
    'earth': '#3a2e22', 'mud': '#2b2218', 'grime': '#211c16', 'rust': '#5c2d13',
    'brass': '#7f6433', 'tarnish': '#2f2b1b', 'leather': '#3b2a1d', 'hair': '#1f1812',
}


class _G:
    """One material's node tree plus the shared inputs every damage layer reads."""

    def __init__(self, name, seed):
        rev = MODE['revenant']
        self.rev = rev
        self.m = bpy.data.materials.new(name + ('_rev' if rev else ''))
        self.m.use_nodes = True
        self.nt = self.m.node_tree
        self.N, self.L = self.nt.nodes, self.nt.links
        self.bsdf = self.N['Principled BSDF']
        self.geo = self.N.new('ShaderNodeNewGeometry')
        self.tco = self.N.new('ShaderNodeTexCoord')
        self.obj = self.tco.outputs['Object']
        self.seed = float(seed)
        ao = self.N.new('ShaderNodeAmbientOcclusion')
        ao.only_local = True
        ao.samples = 8
        ao.inputs['Distance'].default_value = 0.025
        self.cavity = _maprange(self.nt, ao.outputs['AO'], 0.35, 1.0, 1.0, 0.0)      # 1 deep in a recess
        self.edge = _maprange(self.nt, self.geo.outputs['Pointiness'], 0.515, 0.585)   # 1 on a convex edge
        sep = self.N.new('ShaderNodeSeparateXYZ')
        self.L.new(self.geo.outputs['Position'], sep.inputs[0])
        self.wz = sep.outputs['Z']                                                      # world height (tiles)
        self.bumps = []

    # ---- building blocks
    def col(self, h, kind='metal'):
        c = hexlin(h)
        return _corrupt(c, kind) if self.rev else c

    def noise(self, scale, detail=6.0, rough=0.6, distort=0.0, vec=None, w=0.0):
        n = self.N.new('ShaderNodeTexNoise')
        n.noise_dimensions = '4D'
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = rough
        n.inputs['Distortion'].default_value = distort
        n.inputs['W'].default_value = self.seed * 7.13 + w
        self.L.new(vec if vec is not None else self.obj, n.inputs['Vector'])
        return n.outputs['Fac']

    def stretched(self, sx, sy, sz, rot=(0.0, 0.0, 0.0)):
        mp = self.N.new('ShaderNodeMapping')
        mp.inputs['Rotation'].default_value = rot
        mp.inputs['Scale'].default_value = (sx, sy, sz)
        self.L.new(self.obj, mp.inputs['Vector'])
        return mp.outputs['Vector']

    def scratches(self, density=1.0, scale=18.0):
        """Thin long scores: iso-lines of a noise field stretched along one axis, two crossing layers."""
        out = None
        for i, rot in enumerate(((0.0, 0.0, 0.35), (0.6, 0.2, -0.9))):
            v = self.stretched(1.0, 22.0, 1.0, rot)
            n = self.noise(scale, detail=2.0, rough=0.5, vec=v, w=3.1 * i)
            line = _maprange(self.nt, _math(self.nt, 'ABSOLUTE', _math(self.nt, 'SUBTRACT', n, 0.5)), 0.0, 0.006, 1.0, 0.0)
            region = _maprange(self.nt, self.noise(3.0, w=9.0 + i), 0.45, 0.6, 0.0, density)
            layer = _math(self.nt, 'MULTIPLY', line, region)
            out = layer if out is None else _math(self.nt, 'MAXIMUM', out, layer)
        return out

    def pits(self, density=1.0, scale=260.0):
        vo = self.N.new('ShaderNodeTexVoronoi')
        vo.inputs['Scale'].default_value = scale
        self.L.new(self.obj, vo.inputs['Vector'])
        dots = _maprange(self.nt, vo.outputs['Distance'], 0.0, 0.18, 1.0, 0.0)
        region = _maprange(self.nt, self.noise(4.0, w=21.0), 0.4, 0.62, 0.0, density)
        return _math(self.nt, 'MULTIPLY', dots, region)

    def blood(self, amount):
        """Oxblood smears and drips: blotches, streaked downward, heavier low on the figure."""
        if amount <= 0:
            return None
        blotch = self.noise(2.2, detail=10.0, rough=0.62, distort=0.6, w=41.0)
        drip = self.noise(6.0, detail=4.0, vec=self.stretched(1.0, 1.0, 0.12), w=43.0)
        m = _math(self.nt, 'ADD', _math(self.nt, 'MULTIPLY', blotch, 0.75), _math(self.nt, 'MULTIPLY', drip, 0.35))
        lo = 0.66 - 0.1 * amount
        return _maprange(self.nt, m, lo, lo + 0.035)

    def mud(self, height=0.16, amount=1.0):
        """Mud climbing from the ground: world height gradient broken up by noise."""
        g = _maprange(self.nt, self.wz, 0.0, height, 1.0, 0.0)
        n = self.noise(5.0, detail=8.0, w=61.0)
        return _math(self.nt, 'MULTIPLY', _maprange(self.nt, _math(self.nt, 'ADD', g, _math(self.nt, 'MULTIPLY', n, 0.6)), 0.75, 1.05), amount)

    def bump(self, height, strength):
        self.bumps.append((height, strength))

    def cracks(self, amt):
        """Revenant: blight-violet light leaking through fissures."""
        if not self.rev or amt <= 0:
            return
        vo = self.N.new('ShaderNodeTexVoronoi')
        vo.feature = 'DISTANCE_TO_EDGE'
        vo.inputs['Scale'].default_value = 5.0
        vm = self.N.new('ShaderNodeVectorMath')
        vm.operation = 'MULTIPLY_ADD'
        warp = self.N.new('ShaderNodeTexNoise')
        warp.inputs['Scale'].default_value = 4.0
        self.L.new(self.obj, warp.inputs['Vector'])
        vm.inputs[1].default_value = (0.25, 0.25, 0.25)
        self.L.new(warp.outputs['Color'], vm.inputs[0])
        self.L.new(self.obj, vm.inputs[2])
        self.L.new(vm.outputs[0], vo.inputs['Vector'])
        crack = _maprange(self.nt, vo.outputs['Distance'], 0.0, 0.016, 1.0, 0.0)
        patch = _maprange(self.nt, self.noise(3.0, w=77.0), 0.56, 0.66)
        self.bsdf.inputs['Emission Color'].default_value = (*hexlin('#b98cf0'), 1.0)
        self.L.new(_math(self.nt, 'MULTIPLY', _math(self.nt, 'MULTIPLY', crack, patch), 3.5 * amt),
                   self.bsdf.inputs['Emission Strength'])

    def finish(self, color, rough, metal, bevel=0.0):
        self.L.new(color, self.bsdf.inputs['Base Color'])
        if isinstance(rough, (int, float)):
            self.bsdf.inputs['Roughness'].default_value = rough
        else:
            self.L.new(rough, self.bsdf.inputs['Roughness'])
        if isinstance(metal, (int, float)):
            self.bsdf.inputs['Metallic'].default_value = metal
        else:
            self.L.new(metal, self.bsdf.inputs['Metallic'])
        nrm = None
        if bevel > 0:
            bv = self.N.new('ShaderNodeBevel')
            bv.samples = 4
            bv.inputs['Radius'].default_value = bevel
            nrm = bv.outputs['Normal']
        if self.bumps:
            h = None
            for src, k in self.bumps:
                t = _math(self.nt, 'MULTIPLY', src, k)
                h = t if h is None else _math(self.nt, 'ADD', h, t)
            bp = self.N.new('ShaderNodeBump')
            bp.inputs['Strength'].default_value = 1.0
            bp.inputs['Distance'].default_value = 0.0015
            self.L.new(h, bp.inputs['Height'])
            if nrm is not None:
                self.L.new(nrm, bp.inputs['Normal'])
            nrm = bp.outputs['Normal']
        if nrm is not None:
            self.L.new(nrm, self.bsdf.inputs['Normal'])
        return self.m


def _lerp(nt, a, b, t):
    """Scalar lerp a->b by mask t (a, b floats or sockets)."""
    one_minus = _math(nt, 'SUBTRACT', 1.0, t)
    return _math(nt, 'ADD', _math(nt, 'MULTIPLY', a, one_minus), _math(nt, 'MULTIPLY', b, t))


def _cached(key):
    k = (key, MODE['revenant'])
    return _CACHE.get(k), k


def _metal_damage(g, col, rough, metal, rust, blood, grime, mud, kind='metal'):
    """The shared ruin applied to any metal: grime, rust, blood, mud. Returns (col, rough, metal)."""
    nt = g.nt
    grime_m = _math(nt, 'MULTIPLY', g.cavity, grime)
    col = _mix(nt, 'MIX', col, g.col(COL['grime'], 'earth'), grime_m)
    rough = _lerp(nt, rough, 0.78, grime_m)
    metal = _lerp(nt, metal, 0.35, grime_m)
    if rust > 0:
        rm = _math(nt, 'MULTIPLY', _maprange(nt, g.noise(7.0, w=31.0), 0.6 - 0.08 * rust, 0.68 - 0.08 * rust),
                   _math(nt, 'ADD', g.cavity, 0.35))
        rm = _math(nt, 'MINIMUM', rm, 1.0)
        rust_col = _mix(nt, 'MIX', g.col(COL['rust'], 'earth'), g.col('#7a3f1a', 'earth'), g.noise(30.0, w=33.0))
        col = _mix(nt, 'MIX', col, rust_col, rm)
        rough = _lerp(nt, rough, 0.92, rm)
        metal = _lerp(nt, metal, 0.0, rm)
        g.bump(rm, 0.25)
    bm = g.blood(blood)
    if bm is not None:
        bcol = _mix(nt, 'MIX', g.col(COL['oxblood'], 'cloth'), g.col(COL['oxblood_dry'], 'cloth'), g.noise(9.0, w=47.0))
        col = _mix(nt, 'MIX', col, bcol, bm)
        rough = _lerp(nt, rough, 0.42, bm)
        metal = _lerp(nt, metal, 0.0, bm)
    if mud > 0:
        mm = g.mud(amount=mud)
        col = _mix(nt, 'MIX', col, g.col(COL['mud'], 'earth'), mm)
        rough = _lerp(nt, rough, 0.95, mm)
        metal = _lerp(nt, metal, 0.0, mm)
    return col, rough, metal


def steel(name, color=None, rough=0.46, rust=0.25, blood=0.2, grime=0.85, scratch=1.4, pits=1.0, mud=1.0,
          dents=0.6, seed=1, edge=1.0, dirt=0.5):
    """Dull, pitted, scratched plate, filmed with old dirt. Edges and scores worn brighter; recesses packed black.
    Deliberately rough: campaign steel is never mirror-polished."""
    hit, key = _cached(('steel', name))
    if hit:
        return hit
    g = _G(name, seed)
    nt = g.nt
    base = g.col(color or COL['steel'])
    var = g.noise(6.0, w=2.0)
    col = _mix(nt, 'MULTIPLY', base, _maprange(nt, var, 0.3, 0.7, 0.72, 1.05))
    rgh = _maprange(nt, g.noise(11.0, w=5.0), 0.3, 0.75, rough - 0.1, rough + 0.16)
    # a film of dirt over everything, thickest in blotches
    film = _maprange(nt, g.noise(4.0, detail=10.0, rough=0.65, w=24.0), 0.4, 0.75, 0.0, dirt)
    col = _mix(nt, 'MIX', col, g.col(COL['grime'], 'earth'), film)
    rgh = _lerp(nt, rgh, 0.85, film)
    sc = g.scratches(scratch)
    col = _mix(nt, 'MIX', col, g.col(COL['steel_edge']), _math(nt, 'MULTIPLY', sc, 0.45))
    rgh = _lerp(nt, rgh, 0.3, sc)
    em = _math(nt, 'MULTIPLY', g.edge, edge)
    col = _mix(nt, 'MIX', col, g.col(COL['steel_edge']), _math(nt, 'MULTIPLY', em, 0.5))
    rgh = _lerp(nt, rgh, 0.3, em)
    col, rgh, met = _metal_damage(g, col, rgh, 1.0, rust, blood, grime, mud)
    g.bump(g.pits(pits), -0.6)
    g.bump(sc, -0.25)
    g.bump(g.noise(3.0, detail=3.0, w=13.0), dents)
    g.cracks(0.35)
    m = g.finish(col, rgh, met, bevel=0.002)
    _CACHE[key] = m
    return m


def paint_over_steel(name, paint=None, steel_color=None, chip=0.5, blood=0.55, grime=0.8, mud=1.0, seed=3):
    """Bone-white paint scraped down to dull steel. The damage is scars, not blobs: long scores and scrapes cut
    through the coat, chipping gathers at the edges, and grime darkens the paint toward the ground."""
    hit, key = _cached(('paint', name))
    if hit:
        return hit
    g = _G(name, seed)
    nt = g.nt
    # the metal underneath
    steel_c = _mix(nt, 'MULTIPLY', g.col(steel_color or '#6a6c6e'), _maprange(nt, g.noise(8.0, w=4.0), 0.3, 0.7, 0.7, 1.0))
    # the paint: bone-white, stained unevenly, darker toward the bottom where the mud splashes
    paint_c = _mix(nt, 'MULTIPLY', g.col(paint or COL['bone'], 'bone'), _maprange(nt, g.noise(3.5, detail=10.0, w=6.0), 0.3, 0.75, 0.62, 1.0))
    stain = _maprange(nt, g.noise(2.0, detail=6.0, vec=g.stretched(1.0, 1.0, 0.25), w=26.0), 0.45, 0.75, 0.0, 0.55)
    paint_c = _mix(nt, 'MIX', paint_c, g.col('#5d5244', 'earth'), stain)
    # where the paint is gone: scores (long scratches), scrapes (smeared bands), chipping at the edges
    scores = g.scratches(3.0, scale=10.0)
    scr = _maprange(nt, g.noise(6.0, detail=12.0, rough=0.7, vec=g.stretched(1.0, 1.0, 0.18), w=8.0),
                    0.62 - 0.1 * chip, 0.66 - 0.1 * chip)
    chipping = _math(nt, 'MULTIPLY', _maprange(nt, g.noise(40.0, detail=6.0, w=9.0), 0.52, 0.56), _math(nt, 'ADD', g.edge, 0.12))
    worn = _math(nt, 'MINIMUM', _math(nt, 'MAXIMUM', _math(nt, 'MAXIMUM', scores, scr), _math(nt, 'MULTIPLY', chipping, 1.6)), 1.0)
    col = _mix(nt, 'MIX', paint_c, steel_c, worn)
    rgh = _lerp(nt, 0.8, 0.4, worn)
    met = _lerp(nt, 0.0, 0.9, worn)
    col, rgh, met = _metal_damage(g, col, rgh, met, 0.2, blood, grime, mud)
    g.bump(worn, 0.35)      # paint has thickness: the scraped areas sit lower
    g.bump(scores, -0.4)
    g.bump(g.noise(2.5, detail=3.0, w=14.0), 0.5)
    g.cracks(0.5)
    m = g.finish(col, rgh, met)
    _CACHE[key] = m
    return m


def maille(name, color='#4c4e51', rust=0.35, blood=0.15, mud=1.0, seed=5):
    """Dark riveted rings: a cell pattern in the bump, rust in the gaps."""
    hit, key = _cached(('maille', name))
    if hit:
        return hit
    g = _G(name, seed)
    nt = g.nt
    vo = g.N.new('ShaderNodeTexVoronoi')
    vo.inputs['Scale'].default_value = 170.0
    g.L.new(g.obj, vo.inputs['Vector'])
    ring = _maprange(nt, vo.outputs['Distance'], 0.15, 0.5)
    col = _mix(nt, 'MULTIPLY', g.col(color), _maprange(nt, ring, 0.0, 1.0, 1.25, 0.55))
    rgh = _lerp(nt, 0.4, 0.62, ring)
    col = _mix(nt, 'MIX', col, g.col(COL['steel_edge']), _math(nt, 'MULTIPLY', g.edge, 0.35))
    col, rgh, met = _metal_damage(g, col, rgh, 0.9, rust, blood, 0.8, mud)
    g.bump(ring, -0.9)
    g.cracks(0.4)
    m = g.finish(col, rgh, met)
    _CACHE[key] = m
    return m


def brass(name, color=None, tarnish=0.95, blood=0.1, mud=1.0, seed=7, film=0.55):
    """Tarnished gold: dark and green-brown in every recess, filmed over everywhere else, bright only where hands
    and blows polished it. film = how much of the open surface the tarnish has taken."""
    hit, key = _cached(('brass', name))
    if hit:
        return hit
    g = _G(name, seed)
    nt = g.nt
    gold = _mix(nt, 'MULTIPLY', g.col(color or COL['brass']), _maprange(nt, g.noise(9.0, w=3.0), 0.3, 0.7, 0.8, 1.15))
    # the film is a crust in hard-edged patches, and every recess is full of it. A soft blend of gold and tarnish
    # reads as one clean mustard, so the mask is binary. Patches are noise-warped Voronoi cells, each with a uniform
    # random value: `film` is then the true share crusted even on a part only a few cells wide, where a noise
    # threshold would land wherever the noise happens to sit.
    warp = g.N.new('ShaderNodeTexNoise')
    warp.noise_dimensions = '4D'
    warp.inputs['Scale'].default_value = 30.0
    warp.inputs['W'].default_value = g.seed * 3.7
    g.L.new(g.obj, warp.inputs['Vector'])
    wv = g.N.new('ShaderNodeVectorMath')
    wv.operation = 'MULTIPLY_ADD'
    wv.inputs[1].default_value = (0.02, 0.02, 0.02)
    g.L.new(warp.outputs['Color'], wv.inputs[0])
    g.L.new(g.obj, wv.inputs[2])
    cells = g.N.new('ShaderNodeTexVoronoi')
    cells.voronoi_dimensions = '4D'
    cells.inputs['Scale'].default_value = 45.0
    cells.inputs['W'].default_value = g.seed * 1.9
    g.L.new(wv.outputs[0], cells.inputs['Vector'])
    rnd = g.N.new('ShaderNodeSeparateColor')
    g.L.new(cells.outputs['Color'], rnd.inputs[0])
    cover = _math(nt, 'LESS_THAN', rnd.outputs[0], film)
    tm = _math(nt, 'MINIMUM', _math(nt, 'ADD', _math(nt, 'MULTIPLY', g.cavity, tarnish * 1.2), cover), 1.0)
    crust = _mix(nt, 'MIX', g.col(COL['tarnish'], 'earth'), g.col('#1d1a12', 'earth'), g.noise(30.0, w=16.0))
    col = _mix(nt, 'MIX', gold, crust, tm)
    rgh = _lerp(nt, 0.45, 0.9, tm)
    met = _lerp(nt, 1.0, 0.1, tm)
    # polished back to the gold only where hands and blows wore it: scores, and a little on the edges. Small parts
    # are curved all over, so pointiness is high everywhere on them and edge wear has to stay light.
    sc = g.scratches(1.0, scale=26.0)
    wear = _math(nt, 'MAXIMUM', _math(nt, 'MULTIPLY', g.edge, 0.15), _math(nt, 'MULTIPLY', sc, 0.8))
    col = _mix(nt, 'MIX', col, gold, wear)
    rgh = _lerp(nt, rgh, 0.35, wear)
    met = _lerp(nt, met, 1.0, wear)
    col, rgh, met = _metal_damage(g, col, rgh, met, 0.0, blood, 0.5, mud)
    g.bump(tm, 0.15)        # the tarnish is a crust, standing a little proud of the metal
    g.bump(sc, -0.25)
    g.bump(g.pits(0.8, 200.0), -0.5)
    g.cracks(0.3)
    m = g.finish(col, rgh, met, bevel=0.0015)
    _CACHE[key] = m
    return m


def cloth(name, color=None, blood=0.35, mud=1.4, grime=0.6, seed=9, kind='cloth', device=None):
    """Heavy wool gone dark with weather: fibre, folds full of dirt, blood worked in, a mud-soaked hem.
    device=(cx, cz, radius, hex): a painted roundel in object space (the company's mark on a banner)."""
    hit, key = _cached(('cloth', name))
    if hit:
        return hit
    g = _G(name, seed)
    nt = g.nt
    col = _mix(nt, 'MULTIPLY', g.col(color or COL['oxblood'], kind), _maprange(nt, g.noise(5.0, detail=8.0, w=1.0), 0.3, 0.75, 0.7, 1.12))
    if device:
        cx, cz, rad, hexc = device
        sep = g.N.new('ShaderNodeSeparateXYZ')
        g.L.new(g.obj, sep.inputs[0])
        dx = _math(nt, 'SUBTRACT', sep.outputs['X'], cx)
        dz = _math(nt, 'SUBTRACT', sep.outputs['Z'], cz)
        r = _math(nt, 'SQRT', _math(nt, 'ADD', _math(nt, 'MULTIPLY', dx, dx), _math(nt, 'MULTIPLY', dz, dz)))
        ring = _maprange(nt, _math(nt, 'ABSOLUTE', _math(nt, 'SUBTRACT', r, rad * 0.8)), rad * 0.16, rad * 0.2, 1.0, 0.0)
        dot = _maprange(nt, r, rad * 0.36, rad * 0.4, 1.0, 0.0)
        mark = _math(nt, 'MAXIMUM', ring, dot)
        worn = _maprange(nt, g.noise(9.0, detail=8.0, w=19.0), 0.35, 0.55, 0.35, 1.0)   # paint flaked off the weave
        col = _mix(nt, 'MIX', col, g.col(hexc, kind), _math(nt, 'MULTIPLY', mark, worn))
    col = _mix(nt, 'MIX', col, g.col(COL['grime'], 'earth'), _math(nt, 'MULTIPLY', g.cavity, grime))
    bm = g.blood(blood)
    if bm is not None:
        col = _mix(nt, 'MIX', col, g.col(COL['oxblood_dry'], kind), bm)
    if mud > 0:
        col = _mix(nt, 'MIX', col, g.col(COL['mud'], 'earth'), g.mud(height=0.22, amount=mud))
    g.bump(g.noise(260.0, detail=2.0, w=15.0), 0.25)
    g.bump(g.noise(40.0, detail=4.0, w=16.0), 0.2)
    g.bsdf.inputs['Sheen Weight'].default_value = 0.08       # more sheen and wool reads as pink velvet
    g.bsdf.inputs['Sheen Roughness'].default_value = 0.6
    g.cracks(0.7)
    m = g.finish(col, 0.95, 0.0)
    _CACHE[key] = m
    return m


def leather(name, color=None, blood=0.15, mud=1.2, seed=11):
    """Oiled leather scuffed pale where it rubs, cracked where it bends."""
    hit, key = _cached(('leather', name))
    if hit:
        return hit
    g = _G(name, seed)
    nt = g.nt
    col = _mix(nt, 'MULTIPLY', g.col(color or COL['leather'], 'leather'), _maprange(nt, g.noise(7.0, w=2.0), 0.3, 0.7, 0.75, 1.1))
    scuff = _maprange(nt, g.noise(14.0, detail=8.0, w=4.0), 0.58, 0.68)
    scuff = _math(nt, 'MINIMUM', _math(nt, 'ADD', scuff, _math(nt, 'MULTIPLY', g.edge, 0.9)), 1.0)
    col = _mix(nt, 'MIX', col, g.col('#6a5541', 'leather'), _math(nt, 'MULTIPLY', scuff, 0.55))
    col = _mix(nt, 'MIX', col, g.col(COL['grime'], 'earth'), _math(nt, 'MULTIPLY', g.cavity, 0.6))
    rgh = _lerp(nt, 0.55, 0.8, scuff)
    bm = g.blood(blood)
    if bm is not None:
        col = _mix(nt, 'MIX', col, g.col(COL['oxblood_dry'], 'cloth'), bm)
    if mud > 0:
        col = _mix(nt, 'MIX', col, g.col(COL['mud'], 'earth'), g.mud(amount=mud))
    vo = g.N.new('ShaderNodeTexVoronoi')
    vo.feature = 'DISTANCE_TO_EDGE'
    vo.inputs['Scale'].default_value = 60.0
    g.L.new(g.obj, vo.inputs['Vector'])
    g.bump(_maprange(nt, vo.outputs['Distance'], 0.0, 0.05, -1.0, 0.0), 0.3)
    g.cracks(0.7)
    m = g.finish(col, rgh, 0.0)
    _CACHE[key] = m
    return m


def _blob(g, center, sigma):
    """exp(-|p - c|^2 / sigma^2) in object space: a soft spot of colour on a face."""
    nt = g.nt
    d = g.N.new('ShaderNodeVectorMath')
    d.operation = 'DISTANCE'
    g.L.new(g.obj, d.inputs[0])
    d.inputs[1].default_value = center
    dd = _math(nt, 'MULTIPLY', d.outputs['Value'], d.outputs['Value'])
    return _math(nt, 'EXPONENT', _math(nt, 'MULTIPLY', dd, -1.0 / (sigma * sigma)))


def _eblob(g, center, radii):
    """exp(-|(p - c) / r|^2) in object space: an elliptical soft spot (lips, a shaved patch)."""
    nt = g.nt
    sub = g.N.new('ShaderNodeVectorMath')
    sub.operation = 'SUBTRACT'
    g.L.new(g.obj, sub.inputs[0])
    sub.inputs[1].default_value = center
    div = g.N.new('ShaderNodeVectorMath')
    div.operation = 'DIVIDE'
    g.L.new(sub.outputs['Vector'], div.inputs[0])
    div.inputs[1].default_value = radii
    dot = g.N.new('ShaderNodeVectorMath')
    dot.operation = 'DOT_PRODUCT'
    g.L.new(div.outputs['Vector'], dot.inputs[0])
    g.L.new(div.outputs['Vector'], dot.inputs[1])
    return _math(nt, 'EXPONENT', _math(nt, 'MULTIPLY', dot.outputs['Value'], -1.0))


def _segment_dist3(g, a, b):
    """Distance in object space from the shading point to the 3D segment a-b (a scar lying on the skin)."""
    nt = g.nt
    A, AB = Vector(a), Vector(b) - Vector(a)
    pa = g.N.new('ShaderNodeVectorMath')
    pa.operation = 'SUBTRACT'
    g.L.new(g.obj, pa.inputs[0])
    pa.inputs[1].default_value = A
    dot = g.N.new('ShaderNodeVectorMath')
    dot.operation = 'DOT_PRODUCT'
    g.L.new(pa.outputs['Vector'], dot.inputs[0])
    dot.inputs[1].default_value = AB
    t = _maprange(nt, _math(nt, 'MULTIPLY', dot.outputs['Value'], 1.0 / max(1e-12, AB.length_squared)), 0.0, 1.0)
    sc = g.N.new('ShaderNodeVectorMath')
    sc.operation = 'SCALE'
    sc.inputs[0].default_value = AB
    g.L.new(t, sc.inputs['Scale'])
    cp = g.N.new('ShaderNodeVectorMath')
    cp.operation = 'ADD'
    g.L.new(sc.outputs['Vector'], cp.inputs[0])
    cp.inputs[1].default_value = A
    dd = g.N.new('ShaderNodeVectorMath')
    dd.operation = 'DISTANCE'
    g.L.new(g.obj, dd.inputs[0])
    g.L.new(cp.outputs['Vector'], dd.inputs[1])
    return dd.outputs['Value']


def _segment_dist(g, a, b):
    """Distance in the object's X-Z plane from the shading point to the segment a-b (a face-front line)."""
    nt = g.nt
    sep = g.N.new('ShaderNodeSeparateXYZ')
    g.L.new(g.obj, sep.inputs[0])
    p = g.N.new('ShaderNodeCombineXYZ')
    g.L.new(sep.outputs['X'], p.inputs['X'])
    g.L.new(sep.outputs['Z'], p.inputs['Z'])
    A = Vector((a[0], 0.0, a[1]))
    AB = Vector((b[0] - a[0], 0.0, b[1] - a[1]))
    pa = g.N.new('ShaderNodeVectorMath')
    pa.operation = 'SUBTRACT'
    g.L.new(p.outputs['Vector'], pa.inputs[0])
    pa.inputs[1].default_value = A
    dot = g.N.new('ShaderNodeVectorMath')
    dot.operation = 'DOT_PRODUCT'
    g.L.new(pa.outputs['Vector'], dot.inputs[0])
    dot.inputs[1].default_value = AB
    t = _maprange(nt, _math(nt, 'MULTIPLY', dot.outputs['Value'], 1.0 / max(1e-9, AB.length_squared)), 0.0, 1.0)
    sc = g.N.new('ShaderNodeVectorMath')
    sc.operation = 'SCALE'
    sc.inputs[0].default_value = AB
    g.L.new(t, sc.inputs['Scale'])
    cp = g.N.new('ShaderNodeVectorMath')
    cp.operation = 'ADD'
    g.L.new(sc.outputs['Vector'], cp.inputs[0])
    cp.inputs[1].default_value = A
    dd = g.N.new('ShaderNodeVectorMath')
    dd.operation = 'DISTANCE'
    g.L.new(p.outputs['Vector'], dd.inputs[0])
    g.L.new(cp.outputs['Vector'], dd.inputs[1])
    return dd.outputs['Value']


def skin(name, tone, windburn=0.45, dirt=0.55, stubble=0.0, seed=13, face=None, creases=None):
    """Windburned, dirty skin. face = face.marks(...): paints the head's own frame — weather-red cheeks, nose and
    ears; shadowed sockets and dark circles; the lips; the stubble of a shaved undercut; the founding scar, darker
    and desaturated, uneven and broken, sunk into the skin. creases: (x, z) polylines of soft folds."""
    hit, key = _cached(('skin', name))
    if hit:
        return hit
    g = _G(name, seed)
    nt = g.nt
    col = g.col(tone, 'skin')
    col = _mix(nt, 'MIX', col, g.col('#9a4a36', 'skin'), _maprange(nt, g.noise(6.0, w=1.0), 0.4, 0.75, 0.0, windburn))

    def spots(items):
        out = None
        for c, s, a in items:
            b = _math(nt, 'MULTIPLY', _blob(g, c, s), a)
            out = b if out is None else _math(nt, 'MAXIMUM', out, b)
        return out

    def eblobs(items):
        out = None
        for c, r in items:
            b = _eblob(g, c, r)
            out = b if out is None else _math(nt, 'MAXIMUM', out, b)
        return out

    if face:
        col = _mix(nt, 'MIX', col, g.col('#94412f', 'skin'), spots(face['red']))
        col = _mix(nt, 'MIX', col, g.col('#3b2319', 'skin'), spots(face['sock']))
        # dark circles: the sleepless, haunted look every face in the company carries
        col = _mix(nt, 'MIX', col, g.col('#3a2420', 'skin'), spots(face['bags']))
        col = _mix(nt, 'MIX', col, g.col(face.get('lip_color', '#7b5550'), 'skin'),
                   _math(nt, 'MULTIPLY', eblobs(face['lips']), face.get('lip_amount', 0.45)))
        if face.get('lash'):     # a dark lash line along the upper lid
            col = _mix(nt, 'MIX', col, g.col('#1d1311', 'skin'), _math(nt, 'MULTIPLY', eblobs(face['lash']), 0.8))
    if creases:
        lines = None
        for poly in creases:
            for a, b in zip(poly, poly[1:]):
                m = _maprange(nt, _segment_dist(g, a, b), 0.0007, 0.0028, 1.0, 0.0)
                lines = m if lines is None else _math(nt, 'MAXIMUM', lines, m)
        col = _mix(nt, 'MIX', col, g.col('#3a2218', 'skin'), _math(nt, 'MULTIPLY', lines, 0.16))
        g.bump(lines, -0.08)
    col = _mix(nt, 'MIX', col, g.col(COL['grime'], 'earth'), _maprange(nt, g.noise(9.0, detail=8.0, w=3.0), 0.45, 0.75, 0.0, dirt))
    col = _mix(nt, 'MIX', col, g.col('#6e5a4c', 'skin'), _maprange(nt, g.noise(3.0, w=4.0), 0.3, 0.7, 0.35, 0.0))   # sallow
    mottle = _maprange(nt, g.noise(22.0, detail=6.0, rough=0.7, w=5.0), 0.3, 0.7, 0.0, 1.0)             # painterly blotching
    col = _mix(nt, 'MIX', col, g.col('#b89a86', 'skin'), _math(nt, 'MULTIPLY', mottle, 0.22))
    col = _mix(nt, 'MIX', col, g.col('#5e4336', 'skin'), _math(nt, 'MULTIPLY', _math(nt, 'SUBTRACT', 1.0, mottle), 0.18))
    speck = g.noise(400.0, detail=1.0, w=5.0)
    if stubble > 0:
        col = _mix(nt, 'MIX', col, g.col('#2a2019', 'skin'), _math(nt, 'MULTIPLY', speck, stubble))
    if face:     # the undercut's clippered sides: a 'stubble' vertex attribute written by face.head
        at = g.N.new('ShaderNodeAttribute')
        at.attribute_type = 'GEOMETRY'
        at.attribute_name = 'stubble'
        sh = _math(nt, 'MULTIPLY', at.outputs['Fac'], _maprange(nt, speck, 0.3, 0.7, 0.5, 0.85))
        col = _mix(nt, 'MIX', col, g.col('#2b221c', 'skin'), sh)
    if face and face.get('scar'):       # an old scar: darker and desaturated, its width uneven, sunk into the skin
        wob = _math(nt, 'MULTIPLY', _math(nt, 'SUBTRACT', g.noise(260.0, detail=2.0, w=11.0), 0.5), 0.0012)
        sm = None
        for a, b, w in face['scar']:
            d = _math(nt, 'ADD', _segment_dist3(g, a, b), wob)
            m = _maprange(nt, d, w * 0.3, w * 0.95, 1.0, 0.0)
            sm = m if sm is None else _math(nt, 'MAXIMUM', sm, m)
        col = _mix(nt, 'MIX', col, g.col('#5c4440', 'skin'), _math(nt, 'MULTIPLY', sm, 0.75))
        g.bump(sm, -0.3)
    col = _mix(nt, 'MIX', col, g.col('#2a1a12', 'skin'), _math(nt, 'MULTIPLY', g.cavity, 0.85))
    b = g.bsdf
    b.inputs['Subsurface Weight'].default_value = 0.12
    b.inputs['Subsurface Radius'].default_value = (0.9, 0.35, 0.2)
    b.inputs['Subsurface Scale'].default_value = 0.004
    g.bump(g.noise(180.0, detail=3.0, w=7.0), 0.25)
    g.bump(g.noise(900.0, detail=2.0, w=8.0), 0.12)          # pores: kills the plastic sheen
    g.cracks(1.0)
    m = g.finish(col, _maprange(nt, g.noise(12.0, w=9.0), 0.3, 0.7, 0.55, 0.75), 0.0)
    _CACHE[key] = m
    return m


def hair(name, color=None, seed=17, flow='down'):
    """Hair and beards. flow = the way the strands run: 'down' (loose, beards) or 'back' (pulled back hard)."""
    hit, key = _cached(('hair', name))
    if hit:
        return hit
    g = _G(name, seed)
    nt = g.nt
    strands = g.noise(160.0, detail=4.0, vec=g.stretched(1.0, 0.1, 1.0) if flow == 'back' else g.stretched(1.0, 1.0, 0.1),
                      w=2.0)
    clumps = g.noise(30.0, detail=6.0, w=3.0)
    col = _mix(nt, 'MULTIPLY', g.col(color or COL['hair'], 'cloth'), _maprange(nt, strands, 0.25, 0.75, 0.45, 1.35))
    col = _mix(nt, 'MULTIPLY', col, _maprange(nt, clumps, 0.3, 0.7, 0.6, 1.1))
    col = _mix(nt, 'MIX', col, g.col(COL['grime'], 'earth'), _math(nt, 'MULTIPLY', g.cavity, 0.5))
    g.bump(strands, 0.9)
    g.bump(clumps, 0.6)
    g.bsdf.inputs['Specular IOR Level'].default_value = 0.25
    g.cracks(0.5)
    m = g.finish(col, 0.78, 0.0)
    _CACHE[key] = m
    return m


def wood(name, color='#3b2c1e', blood=0.1, seed=19):
    hit, key = _cached(('wood', name))
    if hit:
        return hit
    g = _G(name, seed)
    nt = g.nt
    grain = g.noise(40.0, detail=6.0, vec=g.stretched(1.0, 1.0, 0.06), w=1.0)
    col = _mix(nt, 'MULTIPLY', g.col(color, 'wood'), _maprange(nt, grain, 0.3, 0.7, 0.65, 1.2))
    col = _mix(nt, 'MIX', col, g.col(COL['grime'], 'earth'), _math(nt, 'MULTIPLY', g.cavity, 0.6))
    bm = g.blood(blood)
    if bm is not None:
        col = _mix(nt, 'MIX', col, g.col(COL['oxblood_dry'], 'cloth'), bm)
    g.bump(grain, 0.3)
    g.cracks(0.5)
    m = g.finish(col, 0.75, 0.0)
    _CACHE[key] = m
    return m


def eye(name, iris='#3b2c20'):
    """An eyeball in its own object space (face toward -Y): a dirty, faintly bloodshot white, an iris, a pupil,
    and a wet highlight. Revenant: the whites go dark and the iris burns blight-violet."""
    hit, key = _cached(('eye', name))
    if hit:
        return hit
    g = _G(name, 29)
    nt = g.nt
    nv = g.N.new('ShaderNodeVectorMath')
    nv.operation = 'NORMALIZE'
    g.L.new(g.obj, nv.inputs[0])
    sep = g.N.new('ShaderNodeSeparateXYZ')
    g.L.new(nv.outputs['Vector'], sep.inputs[0])
    fwd = _math(nt, 'MULTIPLY', sep.outputs['Y'], -1.0)            # cos of the angle off the gaze
    iris_m = _maprange(nt, fwd, 0.74, 0.77)
    pupil_m = _maprange(nt, fwd, 0.945, 0.96)
    if g.rev:
        white = hexlin('#26222b')
        ir = hexlin('#c69cf0')
    else:
        white = hexlin('#b3a893')         # dirty whites, bright enough to read against the socket
        ir = hexlin(iris)
    col = _mix(nt, 'MIX', white, hexlin('#9c6a5c'), _maprange(nt, fwd, 0.2, 0.6, 0.55, 0.0))   # bloodshot at the edges
    col = _mix(nt, 'MIX', col, ir, iris_m)
    col = _mix(nt, 'MIX', col, hexlin('#070505'), pupil_m)
    if g.rev:
        g.bsdf.inputs['Emission Color'].default_value = (*ir, 1.0)
        g.L.new(_math(nt, 'MULTIPLY', iris_m, 9.0), g.bsdf.inputs['Emission Strength'])
    g.bsdf.inputs['Specular IOR Level'].default_value = 0.6
    m = g.finish(col, 0.1, 0.0)
    _CACHE[key] = m
    return m


def flat(name, color, rough=0.9):
    """A plain dark matte (nostrils, the inner ear, a leather tie)."""
    hit, key = _cached(('flat', name))
    if hit:
        return hit
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*hexlin(color), 1.0)
    b.inputs['Roughness'].default_value = rough
    _CACHE[key] = m
    return m


def eyes(name='eyes'):
    hit, key = _cached(('eyes', name))
    if hit:
        return hit
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    if MODE['revenant']:
        b.inputs['Base Color'].default_value = (*hexlin('#c69cf0'), 1.0)
        b.inputs['Emission Color'].default_value = (*hexlin('#c69cf0'), 1.0)
        b.inputs['Emission Strength'].default_value = 18.0
    else:
        b.inputs['Base Color'].default_value = (*hexlin('#1a140f'), 1.0)
        b.inputs['Roughness'].default_value = 0.15
    _CACHE[key] = m
    return m
