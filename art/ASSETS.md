# Graphics overhaul — asset priority list

Source of truth for the Blender overhaul. One asset at a time goes through review (render → in-game preview →
feedback → approval); only approved assets get wired into `index.html`.

## Art direction (set on the Fighter review)

The first pass (painted tabletop miniature) was rejected as too clean and toy-like. The direction now follows
the Line-Breaker concept art and briefs:

- **Grimdark realism, battle-worn.** Dull, dented, pitted steel with grime packed in every recess; old oxblood
  smears; rust; mud climbing from the ground. Nothing new, nothing polished.
- **Company palette:** bone-white, cold ash-grey, oxblood, dull steel, muted earth. **Tarnished gold only** as
  rivets, repairs and mismatched trim, never ornament.
- **Weight.** Figures are broad and planted; gear is heavy, practical, inherited from dead campaigns.
- **Every humanoid model has a male and a female form.**
- **Faces at the RuneScape / Project Zomboid level at minimum** (set on revision 3), **carved from one skull**
  (set on revision 5): a head is built from about a dozen readable masses — cranium, brow ridge over clear eye
  sockets, cheekbone planes running back to the ear, a three-part nose (bridge, wedge tip, alar base), muzzle and
  lips, a mandible with a flat-bottomed chin, a neck that rises behind the jaw — about one facial centreline, and
  decimated to large planes that stay legible at 64–128 px. Not handsome, not grotesque: structurally believable.
- **Readability at portrait scale** (set on revision 6): test every head at 64×64 and 96×96. The read runs hair
  silhouette → eyes and brow → nose → jaw and beard → scars and age; both eyes must stay shapes, never black
  sockets. Rugged human, not heroic or orcish: the brow follows the skull and fades into the temples, the cheek
  turns back into the temple without a flange, ears sit tucked, the neck is short and flows into the shoulders.
- **Male and female are two ends of one dial** (set on revision 7, from the dimorphism guide): one skull and one
  proportional framework (hers 5% smaller), his features larger and heavier within it. Male: rectangular, angular —
  defined jaw corners, a squarer chin, a forehead sloping back from a firmer brow, deeper-set eyes under heavier,
  straighter lids, lower, flatter cheekbones, a larger, longer, crisper nose, thinner, straighter lips, more mass under
  the chin, crisper shading. Female: oval-to-heart — a jaw tapering from higher cheekbones to a rounder, narrower chin,
  a soft cheek, an upright forehead, a light brow with a subtle arch, rounder lids, a shorter nose with a narrower
  bridge and softer tip, fuller lips, ears closer to the head, softer shading; her neck slimmer but substantial. Every
  setting blends along the dial, so a softer man or a stronger-jawed woman is a position on it, not a new model.
- **The nose is one attached structure; the female lower face reads oval** (set on revision 8). Sidewalls run from
  the dorsum back into the cheeks along the nose's whole length, into the tip and the alae: never a bridge over a
  see-through gap. The alae grow out of the sidewalls, not off them like a crossbar; the nostrils are small ovals in
  the base's underside. An average male nose, not a heroic one. On the female, the neck rises clear of the jaw (the
  trapezius starts below mid-neck, so nothing flares wider than the jaw just under it); the muzzle under the lips is
  narrow and blended so the cheek runs into the mouth with no bar; the chin sits about 1 mm behind the lower lip.
  Calibrated to the female average-head reference: a full forehead (hairline about 45 mm above the brow, not 36),
  a shorter chin (about 45 mm from the mouth line to the chin, not 48), her upper lip no longer than his.
- **Next: the face morph system.** The approved base head becomes the one every face is rolled from — face length,
  jaw, chin, cheekbones, brow, eyes, nose, lips, ears, age, hair, beard, skin and scars as bounded parameters — so
  each soldier keeps one face across battle sprite, unit card and roster.
- **Proportions** (revisions 4–5): eyes at mid-head, hooded but open, one eye-width apart; the midface short;
  the nose about as wide at its base as the gap between the eyes; a mouth about as wide as the pupils are apart,
  thin-lipped and neutral; ears from the brow to the nose base. Exhaustion comes from the brow, the sockets, the
  under-eye planes and the skin, not from a deformed face; deformation is saved for Blight, disease and wounds.
  Scars are darker and desaturated, uneven and broken, sunk into the skin. Heads run 8% large and tilt chin-up
  toward the camera in battle; portraits are level three-quarter busts, and can take a pixel-art finish (64px,
  28 colours, no dither).
- **Commander** (any class): company banner strapped to the back, one tarnished mark of rank, a founding scar,
  fewer loose pieces. **Veteran** (level 5, the game's veterancy capstone): gear assembled from dead men's
  armour — a foreign gilt pauldron, a mismatched greave, a patched cuirass.

Each class therefore ships as a matrix: {base, Commander, Veteran} × {living, Revenant} × {male, female}.

## How the order was set

**Priority = screen time × gap × leverage**, each scored 1–3:

| Factor | 3 | 2 | 1 |
|---|---|---|---|
| **Screen time** | on screen every battle turn | every session, not constantly | occasional |
| **Gap** | missing or wrong art today | works, but off-style or illegible at 20–26px | serviceable |
| **Leverage** | a style anchor, or a rig/kit many later assets reuse, or carries friend/foe legibility | shared by a few assets | standalone |

Within a wave, dependency order wins: the first humanoid proves the rig every later humanoid reuses.

Screen-time evidence comes from the code: every campaign opens on a Fighter-Commander (`newGame`, roster[0]);
enemy frequency comes from `CONTRACT_TYPES[*].pool` and `POD_DOCTRINES[*].comp`.

## Findings from the audit that shaped the list

- **Enemies and your company are drawn in two different styles on the same board.** Soldiers are top-down
  bodies (`pcTopDown`); every enemy is a front-facing face icon (`enemyFace`).
- **Three enemies have no art at all.** `cutthroat`, `shieldman` and `pikeman` have no `enemyFace` case and
  silently render as brigands — across five of the eight contract pools and two doctrines.
- **The Blight-menhir renders as a Blight-nest** (both are `prop` foes; only `nestSvg` exists).
- **A fallen soldier is a ☠ glyph**, in a game whose central mechanic is what you do with the bodies.
- **Units render at ~26px (desktop) / ~20px (phone)** at 1× zoom, as figures inside coloured chips. Legibility at
  that size is the constraint every model is designed against.

## The list

Status: ✅ approved · 🔍 in review · ⏳ queued

### Wave 1 — The Company (style anchor + every unit you control)
| # | Asset | Variants | Score | Status |
|---|---|---|---|---|
| 1 | **Fighter — the Line-Breaker**: half-plate over maille, bone-white scraped shield with an iron cross, broadsword held low, bareheaded, the head carved from one skull (rev. 6) | base · Commander · Veteran, each living + Revenant, male + female; plus portraits | 3×2×3 = 18 | 🔍 |
| 2 | Ranger — hood & cloak, longbow, quiver | same matrix | 3×2×3 = 18 | ⏳ |
| 3 | Cleric — white tabard with red cross, mail coif, flanged mace | same matrix | 3×2×3 = 18 | ⏳ |
| 4 | Ash Acolyte — hooded ash-robe, blight veins, floating ashfire | same matrix | 3×2×3 = 18 | ⏳ |
| 5 | Underkingdom Shade — black leathers, twin daggers (rare Cinderling recruit) | same matrix | 2×2×2 = 8 | ⏳ |

### Wave 2 — The Enemy (one style for the whole board; fill the three missing designs)
Ordered by how often each appears across contract pools and pod doctrines, with missing art weighted up.
| # | Asset | Why here | Score | Status |
|---|---|---|---|---|
| 6 | Husk | in 7 of 8 contract pools + 4 doctrines — the most common foe | 3×2×3 = 18 | ⏳ |
| 7 | Cutthroat | **no art today**; patrol + hunt pools, Warband | 3×3×2 = 18 | ⏳ |
| 8 | Shieldman | **no art today**; purge/hold/reclaim pools, Shieldwall | 3×3×2 = 18 | ⏳ |
| 9 | Blight-hound | hunt/purge/hold/delve pools, Outriders; first quadruped rig | 3×2×3 = 18 | ⏳ |
| 10 | Brigand | patrol pool ×2, Warband | 3×2×2 = 12 | ⏳ |
| 11 | Graveguard | hold/delve/reclaim, Risen/Conclave/Warhost | 3×2×2 = 12 | ⏳ |
| 12 | Conclave Acolyte | six contract pools | 3×2×2 = 12 | ⏳ |
| 13 | Levy Pikeman | **no art today**; hold pool, Shieldwall | 2×3×2 = 12 | ⏳ |
| 14 | Brigand Archer | patrol pool, Warband | 2×2×2 = 8 | ⏳ |
| 15 | Deserter | patrol pool | 2×2×2 = 8 | ⏳ |
| 16 | Hound-Rider | Outriders (reuses hound + humanoid rigs) | 2×2×2 = 8 | ⏳ |
| 17 | Blight-Mage | Ebon Coven VIP | 1×2×2 = 4 | ⏳ |
| 18 | Blight-Sorcerer | Conclave Circle VIP | 1×2×2 = 4 | ⏳ |
| 19 | Blight-Troll | Warhost VIP, 34 HP — should look it (overflows its tile) | 1×2×2 = 4 | ⏳ |

### Wave 3 — Bodies & objective props (what the fight is about)
| # | Asset | Why | Score | Status |
|---|---|---|---|---|
| 20 | **Fallen soldier**, per class | today a ☠ glyph; bodies are the game's core loop | 2×3×3 = 18 | ⏳ |
| 21 | Blight-menhir | **wrong art today** (draws as a nest); menhir-field objective | 2×3×2 = 12 | ⏳ |
| 22 | Blight-nest | Burn the Nest objective | 2×2×2 = 8 | ⏳ |
| 23 | Escort wagon | Escort objective | 2×2×2 = 8 | ⏳ |
| 24 | Villager charge | Protect objective (today a face) | 2×2×1 = 4 | ⏳ |
| 25 | Objective ground / rite shrine | Seize the Ground, Hold the Rite | 2×2×1 = 4 | ⏳ |

### Wave 4 — The Battlefield (largest area on screen)
| # | Asset | Notes | Score | Status |
|---|---|---|---|---|
| 26 | Ground set: grass-mud, road, mire, blighted | tileable, 3–4 variants each to kill repetition | 3×2×3 = 18 | ⏳ |
| 27 | Ruined walls — 16-piece autotile | matches `wallArt`'s N/S/E/W exposure logic | 3×2×2 = 12 | ⏳ |
| 28 | Trees & brush | cover reads as cover | 3×2×2 = 12 | ⏳ |
| 29 | Boulders, standing stones, fallen columns | line-of-sight blockers | 3×2×2 = 12 | ⏳ |
| 30 | Water, chasm edge, bridge | river / cliffs maps | 2×2×2 = 8 | ⏳ |
| 31 | Elevation: cliff faces & slope lips | restyle the z-level overlay to match | 3×1×2 = 6 | ⏳ |
| 32 | Deco scatter kit (15 props) | bones, skulls, barrels, carts, reeds, blood… | 3×1×1 = 3 | ⏳ |

### Wave 5 — The March (world map)
| # | Asset | Notes | Score | Status |
|---|---|---|---|---|
| 33 | Hex terrain: plains, forest, hills, marsh, mountain + blight | fogged/rumoured provinces reuse them desaturated | 2×2×3 = 12 | ⏳ |
| 34 | Map tokens: caravan, Karsk column, horde, revenant, brigands, hunters | emoji today (⛺ ♞ ☠ ⚰ ⚑ ⚚) | 2×2×2 = 8 | ⏳ |
| 35 | Settlements & Karsk Gate | | 2×2×1 = 4 | ⏳ |
| 36 | Features: ruin, shrine, barrow, battlefield, watchtower | | 2×1×1 = 2 | ⏳ |
| 37 | Chokepoint markers (8 crossings) | | 2×1×1 = 2 | ⏳ |

### Wave 6 — Faces
| # | Asset | Notes | Score | Status |
|---|---|---|---|---|
| 38 | Soldier portrait busts + revenant variant | **highest-risk item**: faces are where procedural modeling is weakest. Prototype before committing; a painted 2D route may win here | 2×2×2 = 8 | ⏳ |
| 39 | Enemy inspector portraits | reuse battle models with a portrait camera | 1×2×1 = 2 | ⏳ |

### Wave 7 — FX & chrome
| # | Asset | Notes | Score | Status |
|---|---|---|---|---|
| 40 | UI kit: panel frames, banner emblem, button plates (9-slice) | | 2×1×1 = 2 | ⏳ |
| 41 | Spell FX flipbooks | CSS/SVG may stay the better tool here | 1×1×1 = 1 | ⏳ |
| 42 | Palace stealth tileset | | 1×1×1 = 1 | ⏳ |

## Integration plan (after approvals, not before)

- Sprites ship as WebP files in `assets/` next to `index.html` (GitHub Pages serves them; a local `file://` open
  still loads `<img>`), about 20–30 KB each.
- Every sprite has its procedural SVG as a fallback, so the overhaul lands one approved asset at a time and a
  missing file never breaks a battle.
- Units stop being coloured chips; a team ring drawn in CSS under the feet carries friend/foe and the live
  states (gold = the soldier you're commanding, violet = revenant, red = target).
- Soldiers have no sex field today (the game calls every soldier "her"). Male/female sprites need a `form`
  field rolled at hire, plus a save migration that assigns one to existing soldiers and graves.
