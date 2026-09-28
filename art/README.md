# art/ — the Blender pipeline

Everything here is source for the graphics overhaul. Nothing in `art/` ships in the page; approved sprites are
copied to `assets/` when they are wired into `index.html`. The review order and status live in
[`ASSETS.md`](ASSETS.md).

Every asset is **built by a Python script**, not sculpted by hand: proportions, pose, kit and palette are numbers
in `blender/assets/<name>.py`, so any render can be reproduced, and a change (a darker surcoat, a longer blade)
is a one-line edit followed by a re-render.

## Setup (once)

Blender runs headless as the `bpy` Python module (Blender 4.5 LTS; needs Python 3.11):

    python3.11 -m venv .bvenv && .bvenv/bin/pip install "bpy==4.5.*" pillow

## Render → review → ship

    .bvenv/bin/python art/blender/render.py fighter            # all variants → art/renders/fighter/*.png
    .bvenv/bin/python art/blender/render.py fighter --draft    # 384px / 24 samples, ~15s each, for iterating
    .bvenv/bin/python art/blender/render.py fighter --portrait # head-and-shoulders portraits (face review, unit card)
    .bvenv/bin/python art/tools/post.py sheet art/renders/fighter/*.png --out review.png   # at real game sizes
    .bvenv/bin/python art/tools/post.py ship  art/renders/fighter/*.png --out art/sprites  # 384px WebP
    python3 -m http.server 8931 --directory . &
    node art/tools/ingame.mjs --sprites art/sprites --out /tmp/review    # the real game, before/after

`ingame.mjs` swaps sprites in at runtime and screenshots the same board state before and after, on desktop and
phone (like `test/`, it needs `playwright` resolvable from Node, or `PW_MODULE=/path/to/playwright/index.mjs`).
`index.html` is not modified until an asset is approved.

## Every soldier's own face (`blender/gb/looks.py`)

A soldier is dealt a **look** when the game creates them: one of `looks.POOL` heads per form, rolled from a seeded
genome (face shape on the male-female dial moved by build, length, lean and age; hair and beard; skin, hair and eye
colour; greying, a receding hairline, scars, a broken nose). `looks.roll(form, n)` is deterministic, so the save
stores only the id (`'f07'`) and the pipeline re-renders exactly that head. The game deals from `LOOKS` in
`index.html`, which must equal `sprites/heads/looks.json` (`test/spine.mjs` checks).

A soldier's sprite is two layers on the same canvas, so each kit is rendered once and each face once:

    .bvenv/bin/python art/blender/render.py fighter --looks      # layers/<variant>.png + heads/<asset>_<id>[_revenant].png
    .bvenv/bin/python art/tools/post.py ship art/renders/fighter/layers/*.png --out art/sprites/body
    .bvenv/bin/python art/tools/post.py ship art/renders/fighter/heads/*.png art/renders/fighter/heads/looks.json --out art/sprites/heads

The body layer is the variant with its head hidden from the camera (still casting its shadow); the head layer is a
look's head on the base kit held out, so the scarf and collar still cut it, rendered in a border round the head.
The head goes over the body. To review faces rather than sprites:

    .bvenv/bin/python art/blender/review_heads.py views    # both anchors: front, both three-quarters, profile, perspective neck
    .bvenv/bin/python art/blender/review_heads.py styles   # every hairstyle and beard on each anchor
    .bvenv/bin/python art/blender/review_heads.py looks    # the pool, one three-quarter each, labelled with its genes
    .bvenv/bin/python art/blender/review_bodies.py         # bare bodies (head counts), the kit on them, silhouettes

Master renders (`art/renders/`) are not committed: they are reproducible from the scripts. The shippable
`art/sprites/*.webp` are.

## The house contract (`blender/gb/rig.py`)

Every sprite obeys the same rules, so sprites drop into the battle grid with no per-asset tuning:

| | |
|---|---|
| Scale | 1 Blender unit = 1 battle tile; tile centre = world origin; +Y north; +Z up |
| Camera | orthographic, looking north, pitched 45° down |
| Canvas | 1.5 × 1.5 tiles; the tile centre lands at 50% across, 74% down |
| Placement in CSS | `width: 1.5·TS; left: −0.25·TS; top: −0.61·TS` relative to the tile |
| Light | warm key from upper-left front (the only shadow-caster), cool fill right, cold rim behind, soft overhead contact |
| Grade | the `grit` look: AgX High Contrast under a dim overcast dome (`rig.LOOKS`) |
| Facing | figures face the camera (−Y), turned 4° |
| Scale | humanoids are modelled in metres; `FIG_SCALE = 0.6` makes a 1.85 m mercenary ~1.1 tiles tall |

## Materials (`blender/gb/grit.py`)

Battle-worn realism, per the art direction in `ASSETS.md`. Every surface is a base material plus the damage a
campaign leaves, in order: scratches and pitting → worn-bright edges → grime packed in recesses → rust or
tarnish → oxblood smears → mud climbing from the ground (in world space, so it rises from the same ground line
on every part). Library: `steel`, `paint_over_steel` (the bone-white shield), `maille`, `brass` (tarnished),
`cloth` (with an optional painted device), `leather`, `skin` (windburn, dirt, stubble; with `face=face.marks(...)`:
lips, sockets, dark circles, shadowed lid margins and eye corners, the undercut's stubble, a sunken scar), `hair`,
`wood`.

**Revenant mode** (`mat.set_mode`) re-renders any asset corrupted: palette drained toward grave-grey, skin gone
pale, sparse blight-violet fissures, violet back-light and glowing eyes. (`gb/mat.py` also keeps the first,
painted-miniature materials.)

## Layout

    blender/gb/rig.py       camera, lights, world, grade presets, render settings, shadow catcher
    blender/gb/grit.py      battle-worn materials (the house look)
    blender/gb/mat.py       palette, colour helpers, revenant corruption, the first painted materials
    blender/gb/kit.py       primitives: skin-modifier limbs, lathes, tubes, blades, hafted weapons
    blender/gb/armor.py     humanoid kit: plate shells, pauldrons, cops, gauntlets, straps, torn cloth,
                            the great shield, the broadsword
    blender/gb/face.py      heads carved from one skull: a signed-distance field of anatomical masses about
                            one centreline, meshed (numpy surface nets) and decimated to readable planes;
                            eyes in carved sockets, hair/beard/brows as shells of the same field; marks()
                            gives the skin shader its landmarks (lips, sockets, lids and eye corners, scar)
    blender/gb/looks.py     the appearance genome: roll(form, n) -> a soldier's look; build_head(look)
    blender/gb/body.py      bodies: male and female anchors on one dial, Frame (the dimensions kits are laid on),
                            and a bare review body (a field of anatomical masses, like the heads)
    blender/assets/*.py     one script per asset: build(variant) + VARIANTS
    blender/render.py       CLI renderer (--looks: body and head layers)
    blender/review_heads.py head review sheets: views, hairstyles, the look pool
    blender/review_bodies.py body review sheets: bare bodies with head counts, the kit on them, silhouettes
    tools/post.py           review sheets at real display sizes; WebP export
    tools/ingame.mjs        before/after screenshots inside the running game
    renders/                master renders (768px PNG, 1.5 tiles square) — gitignored, reproducible
    sprites/                shippable 384px WebP, named <class>[_commander|_veteran][_revenant]_<m|f>.webp
    sprites/body/           the same variants with the head left off (the looks' bodies)
    sprites/heads/          <class>_<look>[_revenant].webp, one per look, and looks.json (the pool the game deals)
