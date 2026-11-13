"""Render Graveborne sprites headless (Blender as a Python module — see art/README.md).

    python art/blender/render.py fighter                          # every variant of an asset
    python art/blender/render.py fighter --only fighter_commander  # one variant
    python art/blender/render.py fighter --elev 45 --suffix _e45   # camera-angle study
    python art/blender/render.py fighter --looks                   # layers for every soldier's own face (below)
    python art/blender/render.py fighter --looks --layers-only     # just the body layers (--heads-only: just the heads)

Writes art/renders/<asset>/<variant>.png: a master render CANVAS (1.5) tiles square with the tile centre at
50% across / ANCHOR_Y (70%) down. art/tools/post.py turns masters into shippable sprites and review sheets.

--looks renders a soldier's sprite as two layers on the same canvas, so each kit is rendered once and each face once,
not every face in every kit:
  layers/<variant>.png     the variant with its head hidden from the camera (it still casts its shadow)
  heads/<asset>_<id>.png   each look's head (gb/looks.py) on the base kit, which is held out: whatever of the body
                           stands in front of the head (the Fighter's scarf and collar, the Ranger's hood and capelet,
                           the Acolyte's hood and collar) cuts it, and its lights still fall on it (the ashfire's);
                           rendered in a border round the head only. _revenant: the same head in the revenant's
                           materials and light. The asset seats the head (add_head): under a hood a head's hair is
                           fitted to it.
A sprite is the head layer over the body layer. Whatever covers a head is the same in every kit of a class (a
Commander's banner and a Veteran's mail stay clear of it), so one head layer serves every kit of its form and class.
"""
import argparse
import importlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, 'assets')]

import bpy  # noqa: E402
from gb import face as F, looks as LK, rig  # noqa: E402

REV_RIM = (0.72, 0.45, 1.0)   # a revenant is back-lit in blight violet


def portrait_camera(elev=6.0, azimuth=28.0, scale=0.235, res=512):
    """Re-aim the house camera for a portrait: a three-quarter bust (head, neck and the top of the shoulders),
    nearly level, the face turned toward the image's left (the convention of the portrait reference sheet)."""
    import math
    from mathutils import Vector
    sc = bpy.context.scene
    head = bpy.data.objects.get('head_root')
    bpy.context.view_layer.update()
    target = head.matrix_world.translation.copy() + Vector((0.0, 0.0, -0.024)) if head else Vector((0, 0, 0.9))
    th, az = math.radians(elev), math.radians(azimuth)
    d = Vector((-math.sin(az) * math.cos(th), math.cos(az) * math.cos(th), -math.sin(th)))
    cam = sc.camera
    cam.data.ortho_scale = scale
    cam.location = target - d * 10.0
    cam.rotation_euler = (math.pi / 2 - th, 0.0, az)
    sc.render.resolution_x = sc.render.resolution_y = res


def head_border(objs, pad=0.015):
    """Limit the render to the region round these objects (the image stays full size, transparent outside)."""
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    sc = bpy.context.scene
    bpy.context.view_layer.update()
    xs, ys = [], []
    for ob in objs:
        if ob.type == 'MESH':
            for c in ob.bound_box:
                co = world_to_camera_view(sc, sc.camera, ob.matrix_world @ Vector(c))
                xs.append(co.x)
                ys.append(co.y)
    r = sc.render
    r.use_border, r.use_crop_to_border = True, False
    r.border_min_x, r.border_max_x = max(0.0, min(xs) - pad), min(1.0, max(xs) + pad)
    r.border_min_y, r.border_max_y = max(0.0, min(ys) - pad), min(1.0, max(ys) + pad)


def head_objects():
    root = bpy.data.objects.get('head_root')
    return [root] + list(root.children_recursive) if root else []


def looks(mod, asset, a, out):
    """Body layers for every variant, then a head layer per look and form, base and revenant (see the docstring)."""
    forms = a.forms or list(LK.FORMS)
    F.CACHE_MAX = max(F.CACHE_MAX, a.count + 1)     # each head is built once, for its base and its revenant layer
    os.makedirs(os.path.join(out, 'layers'), exist_ok=True)
    os.makedirs(os.path.join(out, 'heads'), exist_ok=True)
    if not a.heads_only:
        for name, v in mod.VARIANTS.items():
            if LK.FORMS.get(name[-1]) is None or name[-1] not in forms or (a.only and name not in a.only):
                continue
            rev = v.get('revenant', False)
            rig.stage(elev=a.elev, res=a.res, samples=a.samples, rim_color=REV_RIM if rev else None,
                      rim_energy=5.0 if rev else None, look=a.look)
            mod.build(v)
            for ob in head_objects():
                ob.visible_camera = False
            t = time.time()
            path = os.path.join(out, 'layers', f'{name}.png')
            rig.render(path)
            print(f'[layer] {name}: {time.time() - t:.1f}s -> {os.path.relpath(path)}', flush=True)
    with open(os.path.join(out, 'heads', 'looks.json'), 'w') as fh:     # what the game deals from (LOOKS in index.html)
        json.dump(LK.manifest(), fh, separators=(',', ':'))
    for form in (forms if not a.layers_only else ()):
        sex = LK.FORMS[form]
        for rev in (False, True):
            rig.stage(elev=a.elev, res=a.res, samples=a.samples, rim_color=REV_RIM if rev else None,
                      rim_energy=5.0 if rev else None, look=a.look)
            fig = mod.build({'sex': sex, 'revenant': rev}, head=False)
            for ob in bpy.context.scene.objects:
                ob.is_holdout = True
            for n in range(a.first, a.first + a.count):
                look = LK.roll(form, n)
                t = time.time()
                root = mod.add_head(fig, look, sex)
                head_border(head_objects())
                path = os.path.join(out, 'heads', f"{asset}_{look['id']}{'_revenant' if rev else ''}.png")
                rig.render(path)
                for ob in head_objects():
                    bpy.data.objects.remove(ob)
                for me in list(bpy.data.meshes):     # free the head's geometry (materials stay: grit caches them)
                    if me.users == 0:
                        bpy.data.meshes.remove(me)
                print(f"[head] {look['id']}{' revenant' if rev else ''}: {time.time() - t:.1f}s -> {os.path.relpath(path)}",
                      flush=True)


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
    ap.add_argument('--look', default='grit', choices=['grit', 'portrait', 'painted'],
                    help='house render look (gb/rig.py LOOKS); --portrait switches grit to portrait')
    ap.add_argument('--base', action='store_true', help='stand figures on a painted miniature base (else bare, '
                                                         'with the team ring drawn by the game in CSS)')
    ap.add_argument('--portrait', action='store_true', help='frame the head and shoulders from a low angle '
                                                             '(face review; later the unit card and roster)')
    ap.add_argument('--looks', action='store_true', help='body layers per variant and a head layer per look')
    ap.add_argument('--forms', nargs='*', choices=list(LK.FORMS), help='--looks: forms to render (default both)')
    ap.add_argument('--count', type=int, default=LK.POOL, help='--looks: looks per form')
    ap.add_argument('--first', type=int, default=0, help='--looks: the first look number')
    ap.add_argument('--heads-only', action='store_true', help='--looks: skip the body layers')
    ap.add_argument('--layers-only', action='store_true', help='--looks: skip the head layers')
    a = ap.parse_args()
    if a.draft:
        a.res, a.samples = 384, 24

    mod = importlib.import_module(a.asset)
    out = os.path.normpath(os.path.join(a.out, a.asset))
    os.makedirs(out, exist_ok=True)
    if a.looks:
        looks(mod, a.asset, a, out)
        return
    for name, v in mod.VARIANTS.items():
        if a.only and name not in a.only:
            continue
        rev = v.get('revenant', False)
        rig.stage(elev=a.elev, res=a.res, samples=a.samples,
                  rim_color=REV_RIM if rev else None, rim_energy=5.0 if rev else None,
                  look='portrait' if a.portrait and a.look == 'grit' else a.look)
        mod.build({**v, 'base': a.base, 'portrait': a.portrait})
        suffix = a.suffix
        if a.portrait:
            portrait_camera()
            suffix += '_portrait'
        path = os.path.join(out, f'{name}{suffix}.png')
        t = time.time()
        rig.render(path)
        print(f'[render] {name}{a.suffix}: {time.time() - t:.1f}s -> {os.path.relpath(path)}', flush=True)
        if a.blend:
            bpy.ops.wm.save_as_mainfile(filepath=path[:-4] + '.blend')


if __name__ == '__main__':
    main()
