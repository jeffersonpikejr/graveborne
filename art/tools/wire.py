#!/usr/bin/env python3
"""Wire approved (or in-review) company sprites into the game.

    python3 art/tools/wire.py fighter ranger cleric acolyte     # copy those classes to assets/sprites and rewrite the manifest
    python3 art/tools/wire.py --check                           # verify index.html's manifest matches assets/sprites exactly

Copies each named class's whole sprites, body layers and head layers from art/sprites to assets/sprites (the only
sprite folder the page reads), then regenerates the SPR_MAN block in index.html from what is actually on disk, so the
game never asks for a file that is not there. A class that is not named keeps the hand-drawn SVG. Needs no Blender.
"""
import json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC, DST, PAGE = os.path.join(ROOT, 'art', 'sprites'), os.path.join(ROOT, 'assets', 'sprites'), os.path.join(ROOT, 'index.html')


def manifest():
    names = lambda sub: sorted(f[:-5] for f in os.listdir(os.path.join(DST, sub)) if f.endswith('.webp')) if os.path.isdir(os.path.join(DST, sub)) else []
    heads = {}
    for h in names('heads'):
        parts = h.split('_')
        heads.setdefault(parts[0], {'l': [], 'r': []})['r' if len(parts) > 2 else 'l'].append(parts[1])
    dump = lambda o: json.dumps(o, separators=(',', ':'))
    return 'const SPR_MAN={whole:' + dump(names('')) + ',\n  body:' + dump(names('body')) + ',\n  heads:' + dump(heads) + '};\n'


def block(page):
    m = re.search(r'(/\*SPR_MAN:begin[^\n]*\*/\n)(.*?)(/\*SPR_MAN:end\*/)', page, re.S)
    if not m:
        sys.exit('index.html has no SPR_MAN block')
    return m


def main(argv):
    page = open(PAGE, encoding='utf-8').read()
    if argv == ['--check']:
        ok = block(page).group(2) == manifest()
        print('manifest matches assets/sprites' if ok else 'MISMATCH: run art/tools/wire.py <classes> to rewrite the manifest')
        sys.exit(0 if ok else 1)
    if not argv:
        sys.exit(__doc__)
    shutil.rmtree(DST, ignore_errors=True)
    for sub in ('', 'body', 'heads'):
        os.makedirs(os.path.join(DST, sub), exist_ok=True)
        for f in sorted(os.listdir(os.path.join(SRC, sub))):
            if f.endswith('.webp') and f.split('_')[0] in argv:
                shutil.copy2(os.path.join(SRC, sub, f), os.path.join(DST, sub, f))
    shutil.copy2(os.path.join(SRC, 'heads', 'looks.json'), os.path.join(DST, 'heads', 'looks.json'))
    m = block(page)
    open(PAGE, 'w', encoding='utf-8').write(page[:m.start(2)] + manifest() + page[m.end(2):])
    n = sum(len(fs) for _, _, fs in os.walk(DST))
    print(f'wired {", ".join(argv)}: {n} files in assets/sprites, manifest rewritten')


if __name__ == '__main__':
    main(sys.argv[1:])
