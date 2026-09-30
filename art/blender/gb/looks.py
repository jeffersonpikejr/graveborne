"""Looks: a face of their own for every soldier. Each look is a seeded roll over the head's construction, its hair
and beard, its colouring, its age and its marks.

A look is a small JSON-safe dict of genes. roll(form, n) is deterministic: the same form and number give the same
genes on any machine. A look therefore travels in a save as one short id ('f07'), and the art pipeline rebuilds
exactly that head. Each form has a pool of POOL looks. The game deals them out as soldiers are created, and never
gives two living soldiers the same one (index.html: makeLook).

Every face is a point near its form's anchor on the male-female dial (face.form). Four broad factors move it, plus a
little independent noise per feature, all inside the ranges the construction was built for:

  build    narrow and light <-> broad and heavy: head width, jaw, chin, neck, masseter
  length   a short, wide face <-> a long one: face height, nose length, chin height
  lean     full-cheeked <-> gaunt: the cheek's soft tissue, the hollow under the cheekbone, the fat under the jaw
  age      young <-> weathered (0-1): heavier lids, a lower brow, thinner lips, creases, greying, a receding hairline

These are the axes of the reference sheet's variation row (younger, weathered, leaner, fuller-cheeked).

Hair and beard are dealt by form:
  - hers from the reference's six styles: undercut topknot, centre-parted shoulder length, low bun, braided crown,
    loose ponytail and cropped bob;
  - his from crop, buzz, shaved, topknot and ponytail, with a full, short, stubbled or no beard.

Colouring comes from palettes in the game's own order (SKINS and HAIRC in index.html), so a soldier's rendered head
and their procedural portrait agree on skin and hair.

Every draw goes through random.Random.random(), whose stream Python keeps fixed across versions, so a pool never
changes under an upgrade. The pool is stratified: hairstyles, beards, skin tones and hair colours are dealt from
shuffled decks, so any stretch of the pool is varied, not just the whole of it.
"""
import math
import random

from . import face as F

POOL = 24          # looks per form
FOUNDERS = 2       # the first looks of each form carry the founding scar: only a founding Commander is dealt one
FORMS = {'m': 'male', 'f': 'female'}

# Skin, in the game's SKINS order: 0 light-medium, 1 olive, 2 brown, 3 pale. These are the anchors' grounded, sallow
# tones (the male anchor's '#94796a' is tone 0). Hers sit a shade lighter, as on the anchors.
SKIN_TONES = ['#94796a', '#806350', '#654a3a', '#a68d7f']
SKIN_DECK = [(0, 5), (1, 3), (2, 3), (3, 2)]
FEMALE_LIFT = (10, 11, 12)                      # '#9e8476' - '#94796a'
LIP_MULT = {'m': (0.66, 0.53, 0.55), 'f': (0.8, 0.56, 0.62)}    # the anchors' lips over their skin
# Hair, in the game's HAIRC order: 0 near-black, 1 dark brown, 2 brown (chestnut, auburn or dark blond), 3 grey
# (age deals it, not the deck), 4 ash-black. Darker and duller than the game's swatches: the hair shader and the
# grade lift and saturate them (auburn at the game's value renders orange).
HAIR_COLOURS = [['#2b2118', '#241a13'], ['#43301f', '#3d2b1d'], ['#553b25', '#4a2a1b', '#62533f'], ['#8a8578'],
                ['#333236', '#2b2a2e']]
HAIR_DECK = [(0, 5), (1, 4), (2, 4), (4, 2)]
GREY, BEARD_GREY = '#8a8578', '#77716a'
# Eyes, weighted by skin tone (darker skin, darker eyes): dark brown, brown, hazel, grey, blue-grey, green-grey
IRIS = ['#3b2c20', '#4a3526', '#5a4a2e', '#4a5358', '#44525c', '#4b5a48']
IRIS_W = {0: (3, 3, 2, 2, 2, 1), 1: (4, 3, 2, 1, 0, 1), 2: (6, 3, 1, 0, 0, 0), 3: (1, 2, 2, 3, 3, 2)}
STYLE_DECK = {'f': [('knot', 4), ('long', 4), ('bun', 4), ('braids', 3), ('tail', 4), ('bob', 3)],
              'm': [('crop', 7), ('buzz', 4), ('shaved', 3), ('knot', 3), ('tail', 3)]}
BEARD_DECK = [('full', 3), ('short', 3), ('stubble', 4), (None, 3)]
# the game's procedural faces (faceInner's HAIR list): 0 cropped, 1 to the jaw, 2 swept back, 3 bald, 4 topknot,
# 5 hair and a beard
FACE_HAIR = dict(crop=0, buzz=0, shaved=3, knot=4, tail=2, bun=4, braids=0, bob=1, long=1)

# What each factor does per unit (build, length and lean are drawn about 0 and clipped to +-2; age runs 0-1 and
# acts about 0.4). Settings absent from the table are left where the dial puts them.
LOADINGS = {
    'build':  dict(sx=0.019, sy=0.005, jaw=0.065, chin=0.065, neck=0.02, scm=0.05, masseter=0.1, muzzle=0.03,
                   ear_t=0.03),
    'length': dict(sz=0.026, sx=-0.008, nose_len=0.038, chin_z=-0.002, menton_z=-0.0013),
    'lean':   dict(gaunt=0.2, cheek_pad=-0.38, submental=-0.1, cheek_up=0.09, masseter=-0.05),
    'age':    dict(lid_h=-0.07, brow_lift=-0.0012, gaunt=0.14, cheek_pad=-0.2, lip_hu=-0.0012, lip_hl=-0.0016,
                   lip_pu=-0.0008, lip_pl=-0.0006, eye_depth=0.0005, nose=0.025, ear=0.03),
}
NOISE = dict(nose=0.055, bridge=0.08, tip_round=0.14, nose_proj=0.035, nose_len=0.025,
             lip_hu=0.0006, lip_hl=0.0009, lip_pu=0.0004, lip_pl=0.0004, bow=0.05,
             brow=0.1, brow_arch=0.15, brow_lift=0.0005, brow_w=0.1, glabella=0.05,
             eye=0.025, lid_h=0.025, lid_round=0.05, eye_depth=0.0003,
             ear=0.04, ear_yaw=2.5,
             chin=0.06, chin_round=0.1, chin_y=0.001, jaw_y=0.0012, jaw_z=0.0012,
             cheek_up=0.1, cheek_z=0.001, forehead=0.12, lower_y=0.001, muzzle_w=0.03, taper=0.03)
# the construction's safe ranges: a look never leaves them, however the draws fall
LIMITS = dict(sx=(0.9, 1.04), sz=(0.92, 1.05), jaw=(0.66, 1.1), chin=(0.45, 1.18), chin_round=(0.0, 1.0),
              neck=(0.8, 1.05), gaunt=(0.15, 1.3), cheek_pad=(0.0, 1.4), cheek_up=(0.6, 1.4), taper=(0.0, 0.3),
              brow=(0.05, 1.25), brow_arch=(0.0, 1.5), forehead=(-0.1, 1.2), nose=(0.7, 1.12), bridge=(0.7, 1.15),
              tip_round=(0.6, 1.6), nose_len=(0.86, 1.1), lid_h=(0.85, 1.1), lid_round=(0.35, 0.85),
              eye=(0.94, 1.18), eye_depth=(-0.0002, 0.0016), masseter=(0.4, 1.0), submental=(0.7, 1.3),
              lip_hu=(0.003, 0.0075), lip_hl=(0.0045, 0.0115))


class _Draw:
    """A seeded stream of draws that uses nothing but random(): its values never change across Python versions."""

    def __init__(self, *key):
        self.r = random.Random('/'.join(str(k) for k in key))

    def u(self):
        return self.r.random()

    def gauss(self, sd=1.0, lim=2.0):
        a, b = max(self.u(), 1e-12), self.u()
        return max(-lim, min(lim, math.sqrt(-2.0 * math.log(a)) * math.cos(2.0 * math.pi * b))) * sd

    def weighted(self, items):
        t = self.u() * sum(w for _, w in items)
        for v, w in items:
            t -= w
            if t < 0:
                return v
        return items[-1][0]

    def shuffled(self, xs):
        xs = list(xs)
        for i in range(len(xs) - 1, 0, -1):
            j = int(self.u() * (i + 1))
            xs[i], xs[j] = xs[j], xs[i]
        return xs


def _deal(deck, form, name, n):
    """The n-th card of a form's shuffled deck: every card comes up once per pass, each pass freshly shuffled."""
    cards = [v for v, w in deck for _ in range(w)]
    return _Draw('deck', form, name, n // len(cards)).shuffled(cards)[n % len(cards)]


def _rgb(h):
    h = h.lstrip('#')
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def _hex(c):
    return '#' + ''.join(f'{max(0, min(255, int(round(v)))):02x}' for v in c)


def _mix(a, b, t):
    return _hex([x + (y - x) * t for x, y in zip(_rgb(a), _rgb(b))])


def _lum(h):
    r, g, b = _rgb(h)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def anchor(form, commander=False, veteran=False):
    """The anchor head exactly as the Fighter's variants show it (fighter.BODY, and the Fighter's build seed): no
    roll, no offsets. The Commander carries the founding scar; the Veteran (male) a once-broken nose and a greying
    beard."""
    m = form in ('m', 'male')
    return dict(id='m' if m else 'f', form='m' if m else 'f', n=None, seed=7, dial=0.0 if m else 1.0, factors={},
                offsets={}, style='crop' if m else 'knot', beard='full' if m else None, recede=0.0,
                skin=0, skin_hex='#94796a' if m else '#9e8476', lips='#62403b' if m else '#7f4a4a',
                hc=0, hair_hex='#2b2118' if m else '#2a1c13', beard_hex=BEARD_GREY if (veteran and m) else None,
                iris='#3b2c20' if m else '#4a5358', age=0.4, grey=0.0, windburn=0.45, dirt=0.72,
                lines=2 if m else 1, scar=('founding', 1) if commander else None,
                crooked=0.003 if (veteran and m) else 0.0, anchor=True)


def roll(form, n):
    """Look n of a form ('m' or 'f'): a deterministic roll. Looks 0 .. FOUNDERS-1 are the founding Commanders': look
    0 is the anchor itself, and every founder carries the founding scar."""
    form = 'm' if form in ('m', 'male') else 'f'
    if n == 0:
        return dict(anchor(form, commander=True), id=f'{form}00', n=0, anchor=False)
    d = _Draw('look', form, n)
    male = form == 'm'
    dial = abs(d.gauss(0.07)) - 0.03 if male else 1.0 - abs(d.gauss(0.06)) + 0.03
    dial = max(-0.06, min(0.2, dial)) if male else max(0.8, min(1.05, dial))
    fac = dict(build=d.gauss(), length=d.gauss(), lean=d.gauss(), age=max(0.0, min(1.0, 0.42 + d.gauss(0.22, 2.5))))
    base = F.form(dial)
    off = {}
    for name, table in LOADINGS.items():
        amt = fac[name] - 0.4 if name == 'age' else fac[name]
        for k, v in table.items():
            off[k] = off.get(k, 0.0) + v * amt
    for k, sd in NOISE.items():
        off[k] = off.get(k, 0.0) + d.gauss(sd)
    for k, (lo, hi) in LIMITS.items():     # clip what the offsets would make of the setting, not the offset itself
        if k in off:
            off[k] = max(lo, min(hi, base[k] + off[k])) - base[k]
    off = {k: round(v, 6) for k, v in off.items()}
    age = fac['age']
    style = _deal(STYLE_DECK[form], form, 'style', n)
    beard = _deal(BEARD_DECK, form, 'beard', n) if male else None
    recede = 0.0
    if male and style in ('crop', 'buzz') and age > 0.45 and d.u() < 0.55 + 0.5 * (age - 0.45):
        recede = max(0.15, min(0.95, 0.25 + 1.6 * (age - 0.45) + d.gauss(0.15)))
    skin = _deal(SKIN_DECK, form, 'skin', n)
    tone = _rgb(SKIN_TONES[skin])
    if not male:
        tone = [c + l for c, l in zip(tone, FEMALE_LIFT)]
    lum, warm = 1.0 + d.gauss(0.035), d.gauss(0.012)
    tone = [tone[0] * lum * (1 + warm), tone[1] * lum, tone[2] * lum * (1 - warm)]
    lips = _hex([c * m for c, m in zip(tone, LIP_MULT[form])])
    hc = _deal(HAIR_DECK, form, 'hair', n)
    shades = HAIR_COLOURS[hc]
    hair_hex = shades[int(d.u() * len(shades))]
    grey = max(0.0, min(1.0, (age - 0.62) / 0.3))
    beard_hex = None
    if grey > 0.0:
        beard_hex = _mix(hair_hex, BEARD_GREY, min(1.0, 0.2 + 1.1 * grey)) if beard in ('full', 'short') else None
        hair_hex = _mix(hair_hex, GREY, 0.75 * grey)
        if grey >= 0.8:
            hc = 3
    iris = IRIS[_Draw('iris', form, n).weighted(list(enumerate(IRIS_W[skin])))]
    if n < FOUNDERS:
        scar = ('founding', 1)
    elif d.u() < 0.12:
        scar = ('cheek' if d.u() < 0.6 else 'chin', 1 if d.u() < 0.5 else -1)
    else:
        scar = None
    crooked = 0.0
    if d.u() < (0.09 if male else 0.04):
        crooked = (0.002 + 0.0015 * d.u()) * (1 if d.u() < 0.5 else -1)
    if male:
        lines = 2 if age > 0.35 else 1
    else:
        lines = 2 if age > 0.6 else (1 if age > 0.25 else 0)
    return dict(id=f'{form}{n:02d}', form=form, n=n, seed=(0 if male else 5000) + 17 * n, dial=round(dial, 4),
                factors={k: round(v, 4) for k, v in fac.items()}, offsets=off, style=style, beard=beard,
                recede=round(recede, 3), skin=skin, skin_hex=_hex(tone), lips=lips, hc=hc, hair_hex=hair_hex,
                beard_hex=beard_hex, iris=iris, age=round(age, 3), grey=round(grey, 3),
                windburn=round(0.4 + 0.12 * age + d.gauss(0.05), 3), dirt=round(0.72 + d.gauss(0.06), 3),
                lines=lines, scar=scar, crooked=round(crooked, 5), anchor=False)


def pool(form, count=POOL):
    return [roll(form, n) for n in range(count)]


FOE_LOOKS = 1000        # the enemy pool: foes roll their heads from n = 1000 on, so a foe never wears a soldier's face


def foe(form, n, rough=True):
    """Look n of the enemy pool (roll from FOE_LOOKS on). rough: the living of the road are dealt harder than the
    company: a scar three times as often, a broken nose twice, dirtier and more weathered, fewer clean-shaven; the dead
    (rough=False: the Husk) are dealt as rolled. A draw of its own, so the roll underneath is the same either way."""
    look = roll(form, FOE_LOOKS + n)
    if not rough:
        return look
    d = _Draw('foe', form, n)
    male = look['form'] == 'm'
    scar, crooked, beard = look['scar'], look['crooked'], look['beard']
    if scar is None and d.u() < 0.26:
        scar = ('cheek' if d.u() < 0.6 else 'chin', 1 if d.u() < 0.5 else -1)
    if not crooked and d.u() < (0.1 if male else 0.045):
        crooked = round((0.002 + 0.0015 * d.u()) * (1 if d.u() < 0.5 else -1), 5)
    if male and beard is None and d.u() < 0.6:
        beard = 'stubble'
    return dict(look, scar=scar, crooked=crooked, beard=beard, dirt=round(min(1.0, look['dirt'] + 0.15), 3),
                windburn=round(look['windburn'] + 0.08, 3))


def settings(look):
    """The face settings (face.form) for a look."""
    return F.form(look['dial'], look['offsets'])


def game_face(look):
    """What the game's procedural face shows for this look: its skin, hair colour and hair (index.html's SKINS,
    HAIRC and faceInner's HAIR)."""
    hair = FACE_HAIR[look['style']]
    if look['beard'] in ('full', 'short') and look['style'] != 'shaved':
        hair = 5
    return [look['skin'], look['hc'], hair]


def build_head(look, name='head', gaze=0.0, tag=None, bust=-0.195, yoke=True, hood=None, rot=0.0, helm=False,
               mask=None):
    """Materials and head for a look: face.head's (root, info). tag names the look's materials (None: the anchor's
    own names, so the Fighter's variants render exactly as before); bust, yoke: how much neck comes with it
    (face.field); hood, helm, mask: what the head wears (face.head); rot: a corpse's face (grit.skin)."""
    from . import grit as G
    f = settings(look) if not look.get('anchor') else FORMS[look['form']]
    scar = look['scar']
    style, beard = look['style'], look['beard']
    mk = F.marks(f, scar=scar[1] if scar else None, crooked=look['crooked'], style=style,
                 scar_kind=scar[0] if scar else 'founding')
    mk['lip_color'] = look['lips']
    if tag:     # clippered hair and stubble in the hair's own colour; fair hair shows less against the skin
        mk['stubble_color'] = look['hair_hex']
        mk['stubble_amount'] = max(0.45, min(1.0, 1.25 - _lum(look['hair_hex']) / _lum(look['skin_hex'])))
    sfx = f'_{tag}' if tag else ''
    creases = (mk['creases'] if look['lines'] >= 1 else []) + (mk['forehead'] if look['lines'] >= 2 else [])
    skin = G.skin('face' + sfx + ('_rot' if rot else ''), look['skin_hex'], face=mk, dirt=look['dirt'],
                  windburn=look['windburn'] * (1.0 - 0.9 * rot), rot=rot,
                  stubble={'full': 0.3, 'short': 0.3, 'stubble': 0.15}.get(beard, 0.0) if tag else
                  (0.3 if beard else 0.0), creases=creases or None)
    hair = G.hair('hair' + sfx, look['hair_hex'], flow='back' if style in F.PULLED + ('knot',) else 'down',
                  seed=17 + (look['n'] or 0))
    grey = G.hair('greying' + sfx, look['beard_hex'], seed=18) if look['beard_hex'] else None
    eye = G.eye('eye' + sfx, look['iris'])
    dark = G.flat('dark', '#140d0a')
    return F.head(name, f, skin, None, hair, eye, dark, beard=beard, hair_style=style,
                  scar=scar[1] if scar else None, scar_kind=scar[0] if scar else 'founding', crooked=look['crooked'],
                  greying=grey, seed=look['seed'], gaze=gaze, recede=look['recede'], bust=bust, yoke=yoke, hood=hood,
                  helm=helm, mask=mask)


def manifest(count=POOL):
    """The pool as the game needs it: per form, each look's [skin, hair colour, hair] for the procedural face."""
    return {'founders': FOUNDERS, **{form: [game_face(roll(form, n)) for n in range(count)] for form in FORMS}}
