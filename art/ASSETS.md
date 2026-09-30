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
- **Every soldier has a face of their own** (revision 9, `gb/looks.py`): a seeded genome rolls each head from the
  base (build, length, lean and age, hair, beard, colouring, scars) into a pool the game deals from, never doubled
  among the living.
- **Bodies are the two ends of one construction too** (revision 10, from the body dimorphism guide; `gb/body.py`).
  Him: shoulders significantly wider with more trapezius, a deeper and wider rib cage, a waist that tapers less,
  narrower hips and a flatter seat, a larger upper back, heavier limbs, larger hands and feet. Her: narrower, sloping
  shoulders, a shallower and narrower rib cage, a defined waist, a wider pelvis with mass at the hip, more lumbar
  curve and a fuller seat, slimmer limbs, knees a touch closer together, smaller hands and feet; 92% of his height,
  her head a shade larger for her body (7.6 of her heads to his 8). **Armour is laid on the body**: every plate
  dimension is his plus the difference her body makes at that point, so his kit never moves and hers closes in at
  her waist, is cinched there by the belt, flares over her hips, and carries pauldrons sized to her deltoids.
- **Proportions** (revisions 4–5): eyes at mid-head, hooded but open, one eye-width apart; the midface short;
  the nose about as wide at its base as the gap between the eyes; a mouth about as wide as the pupils are apart,
  thin-lipped and neutral; ears from the brow to the nose base. Exhaustion comes from the brow, the sockets, the
  under-eye planes and the skin, not from a deformed face; deformation is saved for Blight, disease and wounds.
  Scars are darker and desaturated, uneven and broken, sunk into the skin. Heads run 8% large and tilt chin-up
  toward the camera in battle; portraits are level three-quarter busts, and can take a pixel-art finish (64px,
  28 colours, no dither).
- **Light kit is laid on the body too** (the Ranger, `gb/garb.py`): garments are layers offset from the posed body's
  own surface, so a jack, a jerkin or breeches show his barrel chest and her waist, hips and seat with nothing redrawn;
  capes and cloaks drape from their top edge over whatever of the body stands out and flare toward a ragged hem; a
  surcoat or a robe is belted, pulled in to the waist and hanging afresh below it (so hers flares over her hips). A
  hood is worn **low** (set on the Acolyte review, for every hooded class): close over the skull, not standing off
  it, its front coming out over the brow like a visor to a soft point, so the eyes sit in its shadow and the jaw, the
  mouth and the beard carry the soldier; hair keeps only what fits under it or falls out through the opening, and a
  ponytail comes out under the jaw and forward over the shoulder. A class that rolls more than one weapon
  gets a kit per weapon (`ranger_spear_*`); its silhouette weapon is the default.
- **The Blight is worn in the flesh, and its light is kept violet** (the Ash Acolyte, `grit.graft`): a graft is flesh
  gone ash-grey and bruised violet, split by veins whose light dies away from the graft into the wearer's own skin. Blight
  light stays below the point where it burns to white, so it reads as violet at 26 px; on a living soldier it comes
  only from the graft and the ashfire, where a Revenant leaks it from every crack.
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
| 1 | **Fighter — the Line-Breaker**: half-plate over maille, bone-white scraped shield with an iron cross, broadsword held low, bareheaded, the head carved from one skull (rev. 6) | base · Commander · Veteran, each living + Revenant, male + female; plus portraits | 3×2×3 = 18 | ✅ |
| 2 | **Ranger — the Harrier**: hood pulled back over a capelet, a rain-dark cloak, quilted jack and laced jerkin laid on the body, a yew longbow held upright, a back quiver (or a boar spear) | same matrix, × bow / spear | 3×2×3 = 18 | 🔍 |
| 3 | **Cleric — the Chirurgeon**: a mail hauberk under a belted bone-white surcoat with an oxblood cross, the coif pushed back into a collar, a flanged mace held low, a chapel lantern | same matrix, × mace / spear / shortsword | 3×2×3 = 18 | 🔍 |
| 4 | **Ash Acolyte — the Grafted**: leather armour of their own (a boiled-leather cuirass scorched ash-black over a banded fauld, a skirt of hardened strips over the company's oxblood, a high standing collar, the hood pulled back, a leather spaulder on the sword arm); the left arm bare and Blight-grafted (ash-grey flesh split by violet veins, a strap harness, a broken Conclave manacle), the ashfire floating over the open palm, a shortsword held low | same matrix, × shortsword / spear | 3×2×3 = 18 | 🔍 |
| 5 | Underkingdom Shade — black leathers, twin daggers (rare Cinderling recruit) | same matrix | 2×2×2 = 8 | ⏳ |

### Wave 2 — The Enemy (one style for the whole board; fill the three missing designs)
Ordered by how often each appears across contract pools and pod doctrines, with missing art weighted up. The
[enemy plan](#the-enemy-plan-wave-2) below gives each one its signature and the shared kit it is built from, and
regroups them into a build order.
| # | Asset | Why here | Score | Status |
|---|---|---|---|---|
| 6 | Husk | in 7 of 8 contract pools + 4 doctrines — the most common foe | 3×2×3 = 18 | 🔍 |
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

## The enemy plan (Wave 2)

The company's quality, at a fraction of its cost per model: every foe is built from the kit the company already
proved (the body dial and its poses, clothes laid on the body, draped cloth, the hood, the plate shells and the great
shield, the grit materials, the looks genome), and new work goes into a few shared pieces that each unlock several
foes. Each foe still gets one signature of its own.

### What a foe sprite is

- **Whole sprites only.** Foes don't persist, so a foe needs no body and head layers and no 48 heads. It ships a
  few whole sprites, picked per unit from its id: two looks for each form of a humanoid (a corpse's look is its
  corruption), two seeds for a beast. That is about 4 renders a foe against 128 for a company class.
- **The company's contract.** The same camera, scale, canvas, anchor and grade. The team ring in CSS carries the
  side: red for the living, the game's green for the undead, violet for a revenant. Files are
  `foe_<key>[_<tag>]_<n>_<m|f>.webp`, and the procedural SVG stays the fallback.
- **One signature per foe, read at 26 px.** A silhouette element no other unit has comes first, and a faction palette
  second. No two foes share a signature, and no foe borrows the company's: the oxblood is the company's colour, and
  the violet belongs to the Blight.

### Five factions, each with a palette and a construction

| Faction | Foes | Palette | Built from | Faces |
|---|---|---|---|---|
| **Brigands** | Brigand, Brigand Archer, Cutthroat, Hound-Rider | faded ochre and mustard rags, raw leather, rust; no oxblood | the Ranger's garment layers, torn cloth panels, scavenged mismatched plate | shown, from an enemy look pool; masks on some |
| **Karsk** | Shieldman, Levy Pikeman; the Deserter is Karsk kit gone bad | slate blue and white livery, grey iron | the Fighter's plate shells and great shield, quilted levy jacks, kettle hats | helmeted, in shadow |
| **The Conclave** | Conclave Acolyte, Blight-Mage, Blight-Sorcerer, the Grey Envoy | ash-grey robes, bone, violet | the Acolyte's revision-1 robe, hood and mantle (the robe the company's runaway threw off is the Conclave's uniform), the graft and the ashfire, grafts growing with rank | bone masks |
| **The Risen** | Husk, Graveguard, Blight-Troll; the revenants' Still Sworn | corpse grey-green, rot, black corroded iron, violet light | a corpse material mode on the same bodies; the Fighter's plate corroded for the Graveguard | none: the eyes are violet points |
| **Beasts** | Blight-hound, the Hound-Rider's mount | mangy grey-green, bone, violet | a quadruped rig | none |

### Shared pieces to build (each unlocks several foes)

| Piece | Unlocks | Size |
|---|---|---|
| **Corpse material mode** (`mat.set_mode(corpse=True)`): rot-green, mottled skin, bone showing through, violet cracks in the flesh alone; the rest sinks to grave-earth and black iron. No violet back-light: that marks the company's risen, and a foe's side is its ring | Husk, Graveguard, Troll, hound | M |
| **Headgear and masks** (`armor.py`): kettle hat, nasal helm, sallet, great helm with a violet slit, face-wrap, bone mask. Covered faces read as enemies and save the face budget | every human foe, the Graveguard | M |
| **Weapons**: halberd, pike, greataxe, hunting bow, round shield, a Karsk heater (the axe, mace, spear, broadsword and longbow exist) | eight foes | S |
| **Poses** (`body.py`, beyond `reach`): a spine and knee bend for a hunched shamble, a crouch, an archer's half-draw, a shield set, a levelled pike, a casting stance, a seat for the rider | every humanoid foe | M |
| **Enemy look pool** (`looks.py`): its own seeded pool, so a foe never wears a soldier's face | the brigands, the Deserter | S |
| **Quadruped rig**: body.py's construction for a hound: a deep chest, digitigrade legs, a muzzle, the tail | Blight-hound, the Hound-Rider's mount (×1.4) | L |
| **Brute anchor**: a third end on the body dial: wide, hunched, huge hands, a small head | Blight-Troll, later bosses | M |
| **Leader kit**: one mark per faction for any ♛ leader (a brigand trophy standard, a Karsk captain's plume, a Conclave staff, the Risen's iron crown), and bespoke story leaders | Magister Vell, The Magister's Blade, The Grey Envoy | S each |
| **Tier looks** (one piece each, from `TIER_UPGRADES`): an Ironbound husk in scrap plates, a Bloated husk swollen on the dial, a Hardened brigand in a helmet, a Dread graveguard with a crest and a stronger glow, an Elder mage's bone crown, a Feral hound's spines | the late game | S each |

### Each foe: its signature, and what it's built from

| # | Foe | Signature at 26 px | Built from | New for it |
|---|---|---|---|---|
| 6 | Husk | a hunched corpse dragging an axe, two violet eye points | body dial (both forms), shamble, corpse mode, burial rags | corpse mode, the shamble |
| 7 | Cutthroat | a low crouch, a black face-wrap and a trailing scarf, blades reversed | brigand kit, masks | the crouch |
| 8 | Shieldman | a tall Karsk heater in slate and white, braced behind it, a kettle hat | the great shield re-liveried, plate shells, mail | Karsk livery, kettle hat |
| 9 | Blight-hound | the dog: ribs, spines, violet eyes | corpse mode | quadruped rig |
| 10 | Brigand | an ochre rag mask, a patched gambeson, a round shield and a shortsword | the Ranger's garments, torn panels | brigand kit, round shield |
| 11 | Graveguard | a black-iron knight: a great helm with a violet slit, a halberd | the Fighter's plate corroded, corpse mode | great helm, halberd |
| 12 | Conclave Acolyte | a grey robe, a deep hood over a bone mask, a violet graft, a bow at half-draw | the Acolyte's robe, hood, graft and ashfire; the Ranger's bow | bone mask, half-draw |
| 13 | Levy Pikeman | the pike, twice their height, levelled; a slate levy jack | Karsk kit | pike, the pike pose |
| 14 | Brigand Archer | a short ochre cowl, a hunting bow at half-draw (the Ranger's rests upright) | brigand kit, the hood | hunting bow |
| 15 | Deserter | Karsk kit gone bad: the device cut out of the slate tabard, a dented kettle hat, an axe | Karsk kit, torn panels | — |
| 16 | Hound-Rider | a bowman riding a great hound, over the edge of the tile | the hound rig, brigand kit, bow | the seat |
| 17 | Blight-Mage | a bone staff crowned with ashfire, both arms grafted | Conclave kit | the staff |
| 18 | Blight-Sorcerer | a crown of bone horns, three ashfires orbiting, a trailing robe | Conclave kit | the crown |
| 19 | Blight-Troll | its size: 1.8 tiles, hunched, Blight crystals through the back, a greataxe | brute anchor, corpse mode | the brute, crystals |
| 21 | Blight-menhir | a cracked standing stone veined in violet | the graft's vein material, the ashfire's glow | the stone |
| 22 | Blight-nest | a pulsing flesh pod split with violet | the same | the pod |

### Build order (shared piece first, then screen time)

1. **The contract and the Risen's base**: the foe sprite hook in the in-game preview, the corpse mode, the shamble,
   the **Husk** and its tier looks. The most common foe, and it unlocks the Risen.
2. **Brigands**: the brigand kit and the enemy look pool, then the **Brigand**, **Cutthroat** and **Archer**. The
   patrol contract and the Warband doctrine are complete. Planned in detail below
   ([Step 2: the brigand pass](#step-2-the-brigand-pass)).
3. **Karsk**: the livery, the kettle hat and the heater, then the **Shieldman**, **Pikeman** and **Deserter**. The
   Shieldwall doctrine.
4. **The Conclave**: the robe back from git (`26d1aca`), then the **Conclave Acolyte**, **Blight-Mage**,
   **Blight-Sorcerer** and the Grey Envoy.
5. **The Graveguard**, with Magister Vell and The Magister's Blade. The Risen Tide doctrine.
6. **Beasts**: the quadruped rig, the **Blight-hound**, then the **Hound-Rider**. The Outriders doctrine.
7. **The Blight-Troll**: the brute anchor. The Warhost doctrine.
8. **Props**: the Blight-menhir (drawn as a nest today) and the Blight-nest.

After each step, one review, as for the company: the doctrine staged in the game against the company, the 26-px
ladder of every foe so far beside the company, a board section, then approve and ship.

### Cost

- **Rendering:** about 5 whole sprites per foe, plus its leader and tier looks, at 3 to 4 minutes each (the Husk's
  took a minute to build and 2.5 to render). The wave is about 90 sprites, roughly 6 hours of rendering and 1.5 MB of
  WebP; one company class takes about 2.5 hours.
- **Building:** the effort sits in the shared pieces. The quadruped rig and the brute are the large ones, the corpse
  mode and the poses mid-sized; most foes after them are kit variants.
- **Pipeline:** unchanged: a script per foe in `blender/assets/`, `render.py`, `post.py ship`, the in-game preview
  and the board.

### Settled (as recommended)

1. **Faces**: masks and helmets on most foes; faces only on the brigands (the Deserter's shows under a dented
   kettle hat), from an enemy look pool so a foe never wears a soldier's face.
2. **Forms**: his and hers for every humanoid foe, the undead included; the Troll and the beasts as one.
3. **Variety**: two looks per form per foe, four sprites, plus its leader and tier looks.
4. **Karsk livery**: slate blue and white.
5. **The Troll**: 1.8 tiles, over its neighbours.

## Step 2: the brigand pass

Three foes: the **Brigand**, the **Cutthroat** and the **Brigand Archer**. With them come the Brigand's tier look
and a Captain for when a brigand leads. The pass completes the Warband doctrine (`brigand, cutthroat, archer,
brigand`, fought on patrol, hunt and hold contracts) and the Road Patrol pool, bar the Deserter (step 3). The
brigand kit it builds dresses the Hound-Rider in step 6.

### The faction read

- **Palette:** faded ochre and mustard rags, undyed raw leather (paler than the company's dark hide), rusted iron,
  dun. No oxblood and no violet. Scraps of Karsk slate blue show as loot, patched onto the Brigands' gambesons.
- **Ochre at the head is the brigand mark:** the Brigand's rag mask and the Archer's cowl. The Cutthroat's black wrap
  is the exception that marks the knife.
- **Living, and shown:** no corpse mode. Faces come from the enemy look pool, and masks cover some of them.

### The three foes

| Foe | In the game | Signature at 26 px | Kit | Pose | Looks |
|---|---|---|---|---|---|
| **Brigand** | 8 HP, shortsword; two in every Warband, two in five of the patrol pool | a **round shield** on the arm and an **ochre rag mask** | a quilted gambeson in mustard, patched with dun and looted Karsk slate, its skirts split; raw-leather belt and baldric; leg wraps; the company's shortsword; a planked round shield, iron boss and rim, painted ochre with a crude mark | on guard: the shield across the body, the sword back and low, knees bent | two per form: masked, and the mask pulled down to the neck, the face shown |
| **Cutthroat** | 8 HP, speed 6, flanks; the Warband, patrol and hunt | the **lowest living silhouette**, a **black face-wrap with a trailing tail**, blades reversed | a face-wrap over the nose and mouth, bound round the head, its tail trailing a forearm's length; a close dark jerkin, bare wrapped forearms, soft boots; the game's shortsword drawn as a pair of long knives | the crouch: a wide stance, the weight forward, the head up, both blades reversed along the forearms | two per form: hair and eyes over the wrap, black or soot-brown |
| **Brigand Archer** | 6 HP, the game's own Hunting Bow; the Warband and patrol | a **short ochre cowl** and a **bow at half-draw** | the company's hood cut (it fits every look's hair) in ochre, ending in a short cape at the shoulders, with no cloak where the Ranger's falls to the calves; a raw-leather jerkin over a mustard shirt, a bracer, a quiver at the hip; a short hunting bow with recurved tips | half-draw: the bow arm out, the stave canted, the string drawn to the chest, an arrow nocked | two per form |

### Tier and leader looks

- **Hardened Brigand** (tier 2, `Hardened`): a dented nasal helm, and mail showing under the gambeson's hem. 2
  sprites.
- **Brigand Captain** (the ♛ of Cut Off the Head when a brigand leads, a fifth of patrols): a trophy standard on the
  back, a fur-collared cloak, and the greataxe the game gives half its leaders, the Butchers. The other half, the
  Quarry, keep their sword, but the one look serves both and the unit card names the weapon. The standard is a
  crossbar hung with a Karsk kettle hat, bones and a strip of the company's oxblood. That strip is the only oxblood
  on any foe: it says they have killed yours. 2 sprites.
- **Not drawn:** the weapon upgrades (Arming Sword, War Bow) and the Cutthroat's speed tier. They carry no tag in the
  unit's name, and the unit card names the weapon.

### New pieces

| Piece | Where | Reused by | Size |
|---|---|---|---|
| **Enemy look pool** as an API: `looks.foe(form, n)`, rolled from 1000 as the Husk's are, the living roughened (scars three times as often, broken noses twice, dirtier, more stubble); the Husk's heads unchanged | `looks.py` | every human foe | S |
| **Masks**: the rag mask (the nose to the throat) and the face-wrap (with its tail), shells on the head's own field like the hood, knotted behind; the hair and a beard clipped under them | `face.py`, `garb.py` | the Conclave's bone mask builds on it | M |
| **The nasal helm**: an iron skullcap and nasal, fitted as the hood is (the hair under it), dented and rusted | `armor.py` | the Karsk kettle hat and the Deserter's (step 3) | M |
| **Round shield**: a planked disc, iron boss and rim, painted and chipped, strapped to the forearm | `armor.py` | brigands, the Hound-Rider | S |
| **Quilted and patched cloth**: `grit.cloth` quilting channels and sewn-on patches with stitched edges | `grit.py` | every gambeson and levy jack | M |
| **Three poses**: on guard, the crouch (`Frame.hunch` with the feet spread), the half-draw (both arms by `reach`) | `body.py` | the half-draw for the Conclave Acolyte, the Hound-Rider | S |
| **A bow at draw**: `garb.longbow(draw=)` bends the string to the draw hand and nocks an arrow; a short hunting bow with recurved tips | `garb.py` | the Conclave Acolyte, the Hound-Rider | S |
| **Trophy standard** | `garb.py` | brigand leaders | S |
| **The Warband in the preview**: `--foes warband` stages the doctrine's pod, a Hardened Brigand and the Captain (♛) before the mixed company, and deals the leader its look | `ingame.mjs` | every doctrine | S |

### Sprites and cost

- **16 whole sprites:** the Brigand 4, Hardened 2, the Captain 2, the Cutthroat 4, the Archer 4. About an hour of
  rendering and 250 KB of WebP.
- **Building:** the masks, the helm and the quilted cloth are mid-sized; the rest are kit variants and parameters.

### Order

1. **A kit sheet first:** the masks and the helm on two looks, the shield, the gambeson cloth, and the three poses,
   bare and dressed. One review render before any foe.
2. **The Brigand, the Cutthroat, the Archer** in turn, each tested at the battle camera beside the Husk and the
   company.
3. **Hardened and the Captain.**
4. **Production:** the Warband in the game before the company, the board section with the 26-px ladder, then
   commit.

### Risks

- **The crouch against the hunch:** the Cutthroat and the Husk are both low. The crouch must read coiled, not
  slumped: the head up, the stance wide, the blades forward, black against the Husk's pale shroud. The rings differ
  too (red and green).
- **Two hooded bowmen:** the Archer's ochre cowl and a canted bow at draw against the Ranger's moss hood, long cloak
  and upright bow.
- **Beards under masks:** a full beard is clipped under the rag mask as hair is under the hood; check it on the
  bearded looks.

### Open calls

1. **Masks:** the Brigand's two looks masked and unmasked (recommended), or both masked.
2. **The Captain:** built in this pass (recommended), or leaders left for a pass across the factions.
3. **Weapon upgrades:** not drawn (recommended), or drawn (8 more sprites).
4. **The oxblood trophy:** one strip on the Captain's standard (recommended), or none.

## Integration plan (after approvals, not before)

- Sprites ship as WebP files in `assets/` next to `index.html` (GitHub Pages serves them; a local `file://` open
  still loads `<img>`), about 20–30 KB each.
- Every sprite has its procedural SVG as a fallback, so the overhaul lands one approved asset at a time and a
  missing file never breaks a battle.
- Units stop being coloured chips; a team ring drawn in CSS under the feet carries friend/foe and the live
  states (gold = the soldier you're commanding, violet = revenant, red = target).
- A soldier's form comes from their look (v0.69): the game deals every soldier, sword and grave a head of their
  own at creation (`LOOKS` in `index.html`, rolled by `art/blender/gb/looks.py`), and the v0.69 migration deals
  existing records heads that match the faces they already wear. The text still calls every soldier "her":
  whether pronouns follow the form is an open call.
