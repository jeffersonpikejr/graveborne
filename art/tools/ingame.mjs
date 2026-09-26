// In-game preview: boots the real game headless, stages a battle, and screenshots the SAME board state
// before and after swapping Blender sprites in — without touching index.html. Used for every asset review.
//
//   python3 -m http.server 8931 --directory .            # serve the repo root
//   node art/tools/ingame.mjs --sprites art/sprites --out /tmp/review [--mode ring|mini|both]
//
// Sprite files follow <class>[_commander][_revenant][_mini].webp (see art/README.md). The override is the
// integration contract in miniature: a 1.5-tile sprite anchored at 50%/74% on the tile centre, a team ring
// drawn in CSS under the feet (mode "ring"), or a painted base baked into the sprite (mode "mini").
import fs from 'node:fs';
import path from 'node:path';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, arr) => (v.startsWith('--') ? a.concat([[v.slice(2), arr[i + 1]]]) : a), []));
const SPR = args.sprites || 'art/sprites';
const OUT = args.out || '.';
const MODE = args.mode || 'both';
const BASE = process.env.GB_URL || 'http://localhost:8931/';
const { chromium } = await import(process.env.PW_MODULE || 'playwright');   // PW_MODULE=/path/to/playwright/index.mjs if not installed locally
fs.mkdirSync(OUT, { recursive: true });

const sprites = {};
for (const f of fs.readdirSync(SPR)) if (f.endsWith('.webp')) sprites[f.slice(0, -5)] = 'data:image/webp;base64,' + fs.readFileSync(path.join(SPR, f)).toString('base64');

const CSS = `
#grid .unit:has(> img.spr){background:none!important;box-shadow:none!important;border-color:transparent!important;z-index:5;overflow:visible}
#grid .unit > img.spr{position:absolute;pointer-events:none;max-width:none;width:calc(var(--ts)*1.5);height:calc(var(--ts)*1.5);
  left:calc(var(--ts)*-0.25 - 4px);top:calc(var(--ts)*-0.61 - 4px);filter:drop-shadow(0 0 .7px rgba(0,0,0,.95))}
#grid.ringmode .unit:has(> img.spr)::before{content:'';position:absolute;left:50%;top:50%;width:calc(var(--ts)*.76);height:calc(var(--ts)*.5);
  transform:translate(-50%,-50%);border-radius:50%;--ring:#8fa6b8;border:2px solid var(--ring);
  box-shadow:0 0 0 1px rgba(0,0,0,.65),inset 0 0 0 1px rgba(0,0,0,.5);background:radial-gradient(closest-side,rgba(0,0,0,.3),transparent 85%)}
#grid.ringmode .unit.rev:has(> img.spr)::before{--ring:#a77fd6;box-shadow:0 0 0 1px rgba(0,0,0,.65),0 0 8px rgba(154,111,201,.85)}
#grid.ringmode .unit.current:has(> img.spr)::before{--ring:#d9b23a;box-shadow:0 0 0 1px rgba(0,0,0,.65),0 0 9px 1px rgba(201,162,39,.8)}
#grid.minimode .unit.current > img.spr{filter:drop-shadow(0 0 .7px #000) drop-shadow(0 0 3px rgba(201,162,39,.9))}
.spr-card{display:block;border:1px solid var(--line);border-radius:3px;background-color:#161310;background-repeat:no-repeat}
`;

function inject(page, mode) {
  return page.evaluate(({ sprites, CSS, mode }) => {
    if (!window.__origPc) window.__origPc = window.pcTopDown;
    let st = document.getElementById('sprcss');
    if (!st) { st = document.createElement('style'); st.id = 'sprcss'; document.head.appendChild(st); }
    st.textContent = CSS;
    window.__sprMode = mode;
    window.pcTopDown = function (s, size, o) {
      o = o || {};
      if (!window.__sprMode) return window.__origPc(s, size, o);
      const k = ((s && s.cls) || 'fighter') + (s && s.commander ? '_commander' : '') + (o.revenant ? '_revenant' : '');
      const src = sprites[k + (window.__sprMode === 'mini' ? '_mini' : '')] || sprites[k];
      if (!src) return window.__origPc(s, size, o);
      if (size >= 44) return `<div class="spr-card" style="width:${size}px;height:${size}px;background-image:url(${src});background-size:175%;background-position:50% 64%"></div>`;
      return `<img class="spr" src="${src}" alt="">`;
    };
    render();
    const g = document.getElementById('grid');
    if (g) { g.classList.toggle('ringmode', mode === 'ring'); g.classList.toggle('minimode', mode === 'mini'); }
  }, { sprites, CSS, mode });
}
async function unhook(page) { await page.evaluate(() => { window.__sprMode = null; render(); }); }
// render() rebuilds #grid, so the mode class has to be re-applied after any re-render
async function frame(page, zoom, mode) {
  await page.evaluate(({ zoom, mode }) => {
    const B = G.state.battle, vp = document.getElementById('viewport'), pz = document.getElementById('panzoom');
    const c = B.units.find(u => u.kind === 'pc' && u.hp > 0); const TS = battleGridPx(B);
    if (zoom) { B._cam.z = zoom; centerCamOn(B, vp, (c.x + 1.5) * TS, (c.y + 0.5) * TS); applyCam(B, pz, vp); B._camTouched = true; }
    const g = document.getElementById('grid');
    if (g) { g.classList.toggle('ringmode', mode === 'ring'); g.classList.toggle('minimode', mode === 'mini'); }
  }, { zoom, mode });
  await page.waitForTimeout(350);
}
async function dismiss(page) {
  for (let i = 0; i < 12; i++) {
    const c = await page.evaluate(() => { const m = document.querySelector('#modal button'); if (m) { m.click(); return true; } return false; });
    if (!c) break; await page.waitForTimeout(120);
  }
}
async function stage(page) {
  await page.goto(BASE, { waitUntil: 'load' });
  await page.waitForTimeout(500);
  await page.evaluate(() => { localStorage.clear(); G.newGame(); });
  await page.waitForTimeout(250); await dismiss(page);
  await page.evaluate(() => {
    const S = G.state, c = S.contracts.find(c => c.type === 'patrol') || S.contracts[0];
    startBattle(c, S.roster.slice(0, 4).map(s => s.id));
  });
  await page.waitForTimeout(400); await dismiss(page);
  // A fair comparison: clear weather (fog stripes muddy the art), the squad gathered mid-map on level ground so the
  // camera isn't pinned to an edge, and the founding grave raised as a Fighter revenant on the Commander's flank.
  await page.evaluate(() => {
    const S = G.state, B = S.battle, g = S.graves[0];
    B.weather = null; B.rain = false;
    const ok = (x, y, z) => { const t = tileAt(B, x, y); return t && !bImpass(t.t) && !t.blighted && !unitAt(B, x, y) && elevAt(B, x, y) === z; };
    let best = null;   // the most central open, level 6x3 patch
    for (let y = 2; y < GH - 4; y++) for (let x = 2; x < GW - 7; x++) {
      const z = elevAt(B, x, y); let fits = true;
      for (let dy = 0; dy < 3 && fits; dy++) for (let dx = 0; dx < 6 && fits; dx++) { const t = tileAt(B, x + dx, y + dy); fits = t && !bImpass(t.t) && !t.blighted && elevAt(B, x + dx, y + dy) === z; }
      const d = Math.abs(x + 3 - GW / 2) + Math.abs(y + 1 - GH / 2);
      if (fits && (!best || d < best.d)) best = { x, y, d };
    }
    const pcs = B.units.filter(u => u.kind === 'pc'), spots = [[0, 1], [1, 0], [1, 2], [0, 2]];
    const others = B.units.filter(u => u.kind !== 'pc');
    if (best) pcs.forEach((u, i) => { const [dx, dy] = spots[i % spots.length]; u.x = best.x + dx; u.y = best.y + dy; });
    for (const u of others) if (best && u.x >= best.x - 1 && u.x <= best.x + 6 && u.y >= best.y - 1 && u.y <= best.y + 3) {
      const p = nearOpen(B, Math.max(0, best.x - 5), u.y, 8); if (p) { u.x = p.x; u.y = p.y; }
    }
    g.snap.cls = 'fighter'; g.snap.commander = false;
    spawnRevenant(B, g);
    const rv = B.units.find(u => u.graveId === g.id), cmd = pcs[0];
    for (const [dx, dy] of [[3, 0], [3, 1], [4, 0], [3, -1], [2, 1]]) {
      const x = cmd.x + dx, y = cmd.y + dy;
      if (ok(x, y, elevAt(B, cmd.x, cmd.y))) { rv.x = x; rv.y = y; break; }
    }
    B._camTouched = false; B._camFollow = null;
    render();
  });
  await page.waitForTimeout(300); await dismiss(page);
}

// where the staged units sit on screen (CSS px), so review crops follow the units instead of fixed pixel boxes
const rects = (page) => page.evaluate(() => {
  const r = (el) => { if (!el) return null; const b = el.getBoundingClientRect(); return { x: b.x, y: b.y, w: b.width, h: b.height }; };
  return { commander: r(document.querySelector('#grid .unit.pc.current')), revenant: r(document.querySelector('#grid .unit.rev')),
           grid: r(document.getElementById('grid')), vw: innerWidth, vh: innerHeight };
});

const browser = await chromium.launch(process.env.PW_CHROMIUM ? { executablePath: process.env.PW_CHROMIUM } : {});
const shots = [], meta = {};
for (const dev of [{ n: 'desktop', vp: { width: 1280, height: 800 }, zooms: [0, 2.2] }, { n: 'phone', vp: { width: 390, height: 844 }, zooms: [0, 1.75] }]) {
  const page = await browser.newPage({ viewport: dev.vp, deviceScaleFactor: 2 });
  page.on('pageerror', e => console.log('pageerror', e.message));
  await stage(page);
  for (const z of dev.zooms) {
    const tag = `${dev.n}_${z ? 'zoom' : 'fit'}`;
    await unhook(page); await frame(page, z, null);
    await page.screenshot({ path: `${OUT}/${tag}_before.png` }); shots.push(`${tag}_before`);
    meta[tag] = await rects(page);
    for (const mode of MODE === 'both' ? ['ring', 'mini'] : [MODE]) {
      await inject(page, mode); await frame(page, z, mode);
      await page.screenshot({ path: `${OUT}/${tag}_${mode}.png` }); shots.push(`${tag}_${mode}`);
    }
  }
  await page.close();
}
await browser.close();
fs.writeFileSync(`${OUT}/rects.json`, JSON.stringify(meta, null, 1));
console.log(shots.join('\n'));
