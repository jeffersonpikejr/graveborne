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
    .bvenv/bin/python art/blender/render.py fighter --draft    # 384px / 24 samples, ~8s each, for iterating
    .bvenv/bin/python art/tools/post.py sheet art/renders/fighter/*.png --out review.png   # at real game sizes
    .bvenv/bin/python art/tools/post.py ship  art/renders/fighter/*.png --out art/sprites  # 384px WebP
    python3 -m http.server 8931 --directory . &
    node art/tools/ingame.mjs --sprites art/sprites --out /tmp/review    # the real game, before/after

`ingame.mjs` swaps sprites in at runtime and screenshots the same board state before and after, on desktop and
phone (like `test/`, it needs `playwright` resolvable from Node, or `PW_MODULE=/path/to/playwright/index.mjs`).
`index.html` is not modified until an asset is approved.

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
| Facing | figures face the camera (−Y), turned 8° to show more of the shield side |

## Materials (`blender/gb/mat.py`)

Painted-miniature shading: base coat → dark wash in recesses (ambient occlusion) → highlight on convex edges
(Cycles pointiness, relative to the base coat) → grime. Colours are authored as the game's own sRGB hex values.
**Revenant mode** re-renders any asset corrupted: palette drained toward grave-grey, skin gone pale, sparse
blight-violet fissures, violet back-light and eyes.

## Layout

    blender/gb/rig.py       camera, lights, world, render settings, shadow catcher
    blender/gb/mat.py       painted materials, palette, revenant corruption
    blender/gb/kit.py       modeling vocabulary: skin-modifier limbs, lathes, kite shield, blade, banner, base
    blender/assets/*.py     one script per asset: build(variant) + VARIANTS
    blender/render.py       CLI renderer
    tools/post.py           review sheets at real display sizes; WebP export
    tools/ingame.mjs        before/after screenshots inside the running game
    renders/                master renders (768px PNG, 1.5 tiles square) — gitignored, reproducible
    sprites/                shippable 384px WebP, named <asset>[_commander][_revenant][_mini].webp
