"""Render Graveborne sprites headless (Blender as a Python module — see art/README.md).

    python art/blender/render.py fighter                          # every variant of an asset
    python art/blender/render.py fighter --only fighter_commander  # one variant
    python art/blender/render.py fighter --elev 45 --suffix _e45   # camera-angle study

Writes art/renders/<asset>/<variant>.png: a master render CANVAS (1.5) tiles square with the tile centre at
50% across / ANCHOR_Y (70%) down. art/tools/post.py turns masters into shippable sprites and review sheets.
"""
import argparse
import importlib
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, 'assets')]

import bpy  # noqa: E402
from gb import rig  # noqa: E402

REV_RIM = (0.72, 0.45, 1.0)   # a revenant is back-lit in blight violet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('asset')
    ap.add_argument('--only', nargs='*')
    ap.add_argument('--elev', type=float, default=45.0)
    ap.add_argument('--res', type=int, default=768)
    ap.add_argument('--samples', type=int, default=96)
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'renders'))
    ap.add_argument('--suffix', default='')
    ap.add_argument('--blend', action='store_true', help='also save the .blend for inspection')
    ap.add_argument('--draft', action='store_true', help='quick look: 384px, 24 samples')
    ap.add_argument('--look', default='grit', choices=['grit', 'painted'], help='house render look (gb/rig.py LOOKS)')
    ap.add_argument('--base', action='store_true', help='stand figures on a painted miniature base (else bare, '
                                                         'with the team ring drawn by the game in CSS)')
    a = ap.parse_args()
    if a.draft:
        a.res, a.samples = 384, 24

    mod = importlib.import_module(a.asset)
    out = os.path.normpath(os.path.join(a.out, a.asset))
    os.makedirs(out, exist_ok=True)
    for name, v in mod.VARIANTS.items():
        if a.only and name not in a.only:
            continue
        rev = v.get('revenant', False)
        rig.stage(elev=a.elev, res=a.res, samples=a.samples,
                  rim_color=REV_RIM if rev else None, rim_energy=5.0 if rev else None, look=a.look)
        mod.build({**v, 'base': a.base})
        path = os.path.join(out, f'{name}{a.suffix}.png')
        t = time.time()
        rig.render(path)
        print(f'[render] {name}{a.suffix}: {time.time() - t:.1f}s -> {os.path.relpath(path)}', flush=True)
        if a.blend:
            bpy.ops.wm.save_as_mainfile(filepath=path[:-4] + '.blend')


if __name__ == '__main__':
    main()
