// In-game preview: boots the real game headless, stages a battle, and screenshots the SAME board state
// before and after swapping Blender sprites in — without touching index.html. Used for every asset review.
//
//   python3 -m http.server 8931 --directory .            # serve the repo root
//   node art/tools/ingame.mjs --sprites art/sprites --out /tmp/review [--mode ring|mini|both] [--squad fighter|ranger|cleric|acolyte|company]
//   node art/tools/ingame.mjs --sprites art/sprites --out /tmp/review --foes husk     # a pod of foes before the company
//
// Sprite files follow <class>[_<weapon>][_commander|_veteran][_revenant]_<m|f>.webp (see art/README.md): a kit drawn
// for the soldier's own weapon wins (ranger_spear_...), else the class's own (the Ranger's bow); the Commander kit
// wins, then the Veteran kit from level 5 (the game's own veterancy capstone), then the base kit. A soldier with a
// look (s.look, 'f07': dealt at creation, see LOOKS in index.html) is drawn in layers: the kit's body
// (body/<variant>.webp) under their own head (heads/<class>_<look>[_revenant].webp), the form from the look;
// without one, the whole sprite of the form the preview stages. The override is the integration contract in
// miniature: a 1.5-tile sprite anchored at 50%/74% on the tile centre, and a team ring drawn in CSS under the feet.
//
// --squad stages the same people every time: the Commander (a Fighter, a founder's head), then three of the class
// under review (one at veterancy; the third carries another of the class's weapons: the Ranger's spear, the Cleric's
// shortsword, the Acolyte's spear) and the founding grave risen as that class.
// --foes <key> stages a pod of four of that foe a few tiles before the company (by default the mixed squad: the
// Commander, a Ranger, a Cleric and an Acolyte) instead of the risen grave, the last two carrying its TIER_UPGRADES
// tags, and draws foes from foe_<key>[_<tag>]_<n>_<m|f>.webp: whole sprites, each unit dealt one by its id, from its
// tier's looks if its name carries the tag; ringed red, or green for the undead.
import fs from 'node:fs';
import path from 'node:path';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, arr) => (v.startsWith('--') ? a.concat([[v.slice(2), arr[i + 1]]]) : a), []));
const SPR = args.sprites || 'art/sprites';
const OUT = args.out || '.';
const MODE = args.mode || 'ring';
const SQUADS = {
  fighter: { roster: [{ look: 'f00' }, { cls: 'fighter', level: 5, weapon: 'shortsword', look: 'm06' },
    { cls: 'fighter', weapon: 'shortsword', look: 'f07' }, { cls: 'fighter', weapon: 'shortsword', look: 'm13' }],
    grave: { cls: 'fighter', weapon: 'shortsword', look: 'f05' } },
  ranger: { roster: [{ look: 'f00' }, { cls: 'ranger', level: 5, weapon: 'bow', look: 'm06' },
    { cls: 'ranger', weapon: 'bow', look: 'f07' }, { cls: 'ranger', weapon: 'spear', look: 'm13' }],
    grave: { cls: 'ranger', weapon: 'bow', look: 'f05' } },
  cleric: { roster: [{ look: 'f00' }, { cls: 'cleric', level: 5, weapon: 'mace', look: 'm06' },
    { cls: 'cleric', weapon: 'mace', look: 'f07' }, { cls: 'cleric', weapon: 'shortsword', look: 'm13' }],
    grave: { cls: 'cleric', weapon: 'mace', look: 'f05' } },
  acolyte: { roster: [{ look: 'f00' }, { cls: 'acolyte', level: 5, weapon: 'shortsword', look: 'm06' },
    { cls: 'acolyte', weapon: 'shortsword', look: 'f07' }, { cls: 'acolyte', weapon: 'spear', look: 'm13' }],
    grave: { cls: 'acolyte', weapon: 'shortsword', look: 'f05' } },
  // the company as it fights: the Commander, a Ranger, a Cleric and an Acolyte (the default before a foe pod)
  company: { roster: [{ look: 'f00' }, { cls: 'ranger', weapon: 'bow', look: 'm06' },
    { cls: 'cleric', weapon: 'mace', look: 'f07' }, { cls: 'acolyte', weapon: 'shortsword', look: 'm13' }],
    grave: { cls: 'fighter', weapon: 'shortsword', look: 'f05' } },
};
const SQUAD = SQUADS[args.squad || (args.foes ? 'company' : 'fighter')];
const FOES = args.foes || null;
const BASE = process.env.GB_URL || 'http://localhost:8931/';
const { chromium } = await import(process.env.PW_MODULE || 'playwright');   // PW_MODULE=/path/to/playwright/index.mjs if not installed locally
fs.mkdirSync(OUT, { recursive: true });

const load = (dir) => {
  const out = {};
  if (fs.existsSync(dir)) for (const f of fs.readdirSync(dir)) if (f.endsWith('.webp')) out[f.slice(0, -5)] = 'data:image/webp;base64,' + fs.readFileSync(path.join(dir, f)).toString('base64');
  return out;
};
const sprites = load(SPR), bodies = load(path.join(SPR, 'body')), heads = load(path.join(SPR, 'heads'));

const CSS = `
#grid .unit:has(> img.spr){background:none!important;box-shadow:none!important;border-color:transparent!important;z-index:5;overflow:visible}
#grid .unit > img.spr{position:absolute;pointer-events:none;max-width:none;width:calc(var(--ts)*1.5);height:calc(var(--ts)*1.5);
  left:calc(var(--ts)*-0.25 - 4px);top:calc(var(--ts)*-0.61 - 4px);filter:drop-shadow(0 0 .7px rgba(0,0,0,.95))}
#grid.ringmode .unit:has(> img.spr)::before{content:'';position:absolute;left:50%;top:50%;width:calc(var(--ts)*.76);height:calc(var(--ts)*.5);
  transform:translate(-50%,-50%);border-radius:50%;--ring:#8fa6b8;border:2px solid var(--ring);
  box-shadow:0 0 0 1px rgba(0,0,0,.65),inset 0 0 0 1px rgba(0,0,0,.5);background:radial-gradient(closest-side,rgba(0,0,0,.3),transparent 85%)}
#grid.ringmode .unit.rev:has(> img.spr)::before{--ring:#a77fd6;box-shadow:0 0 0 1px rgba(0,0,0,.65),0 0 8px rgba(154,111,201,.85)}
#grid.ringmode .unit.foe:has(> img.spr)::before{--ring:#b5523a}
#grid.ringmode .unit.undead:has(> img.spr)::before{--ring:#7f9a5c}
#grid.ringmode .unit.current:has(> img.spr)::before{--ring:#d9b23a;box-shadow:0 0 0 1px rgba(0,0,0,.65),0 0 9px 1px rgba(201,162,39,.8)}
#grid.minimode .unit.current > img.spr{filter:drop-shadow(0 0 .7px #000) drop-shadow(0 0 3px rgba(201,162,39,.9))}
.spr-card{display:block;border:1px solid var(--line);border-radius:3px;background-color:#161310;background-repeat:no-repeat}
`;

function inject(page, mode) {
  return page.evaluate(({ sprites, bodies, heads, CSS, mode }) => {
    if (!window.__origPc) window.__origPc = window.pcTopDown;
    if (!window.__origFoe) window.__origFoe = window.enemyFace;
    if (!window.__origRender) window.__origRender = window.render;
    // foe_<key>[_<tag>]_<n>_<m|f>: a foe's base looks, and its tier looks by the tag its upgrade puts in its name
    const foeKits = {};
    for (const k of Object.keys(sprites).sort()) {
      const m = k.match(/^foe_([a-z]+)_(?:([a-z]+)_)?\d+_[mf]$/); if (!m) continue;
      const kit = foeKits[m[1]] = foeKits[m[1]] || { base: [], tiers: {} };
      if (m[2]) (kit.tiers[m[2]] = kit.tiers[m[2]] || []).push(k); else kit.base.push(k);
    }
    const foeSprite = (u) => {
      const kit = foeKits[u.ekey], tag = u.name.split(' ')[0].toLowerCase();
      const pool = kit.tiers[tag] || kit.base;
      return sprites[pool[u.uid % pool.length]];
    };
    window.enemyFace = function (key, size) {
      const kit = window.__sprMode && foeKits[key];
      if (!kit) return window.__origFoe(key, size);
      const src = sprites[kit.base[0]];        // each unit is dealt its own once the grid is drawn (render below)
      if (size >= 44) return `<div class="spr-card" style="width:${size}px;height:${size}px;background-image:url(${src});background-size:175%;background-position:50% 64%"></div>`;
      return `<img class="spr" src="${src}" alt="">`;
    };
    window.render = function (...a) {        // deal every foe on the grid its sprite by its id and its tier
      const r = window.__origRender.apply(this, a);
      const B = window.__sprMode && G.state.battle;
      if (B) for (const el of document.querySelectorAll('#grid .unit.foe, #grid .unit.undead')) {
        const u = B.units.find(x => String(x.uid) === el.dataset.uid), img = el.querySelector(':scope > img.spr');
        if (u && img && foeKits[u.ekey]) img.src = foeSprite(u);
      }
      return r;
    };
    let st = document.getElementById('sprcss');
    if (!st) { st = document.createElement('style'); st.id = 'sprcss'; document.head.appendChild(st); }
    st.textContent = CSS;
    window.__sprMode = mode;
    window.pcTopDown = function (s, size, o) {
      o = o || {};
      if (!window.__sprMode) return window.__origPc(s, size, o);
      s = s || {};
      const cls = s.cls || 'fighter', rev = o.revenant ? '_revenant' : '';
      const form = s.look ? s.look[0] : (s.form || (s.commander ? 'f' : 'm'));
      const tiers = s.commander ? ['_commander', ''] : ((s.level || 1) >= 5 ? ['_veteran', ''] : ['']);
      const kits = s.weapon ? [`${cls}_${s.weapon}`, cls] : [cls];
      const head = s.look && heads[`${cls}_${s.look}${rev}`];
      let body = null;
      for (const k of kits) for (const t of tiers) body = body || bodies[`${k}${t}${rev}_${form}`];
      if (head && body) {       // the kit's body under the soldier's own head
        if (size >= 44) return `<div class="spr-card" style="width:${size}px;height:${size}px;background-image:url(${head}),url(${body});background-size:175%;background-position:50% 64%"></div>`;
        return `<img class="spr" src="${body}" alt=""><img class="spr" src="${head}" alt="">`;
      }
      let src = null;
      for (const k of kits) for (const t of tiers) for (const f of [form, form === 'm' ? 'f' : 'm']) src = src || sprites[`${k}${t}${rev}_${f}`];
      if (!src) return window.__origPc(s, size, o);
      if (size >= 44) return `<div class="spr-card" style="width:${size}px;height:${size}px;background-image:url(${src});background-size:175%;background-position:50% 64%"></div>`;
      return `<img class="spr" src="${src}" alt="">`;
    };
    render();
    const g = document.getElementById('grid');
    if (g) { g.classList.toggle('ringmode', mode === 'ring'); g.classList.toggle('minimode', mode === 'mini'); }
  }, { sprites, bodies, heads, CSS, mode });
}
async function unhook(page) { await page.evaluate(() => { window.__sprMode = null; render(); }); }
// render() rebuilds #grid, so the mode class has to be re-applied after any re-render
async function frame(page, zoom, mode) {
  await page.evaluate(({ zoom, mode }) => {
    const B = G.state.battle, vp = document.getElementById('viewport'), pz = document.getElementById('panzoom');
    const c = B.units.find(u => u.kind === 'pc' && u.hp > 0); const TS = battleGridPx(B);
    const at = B._podCentre || { x: c.x + 1, y: c.y };      // the squad, or with a pod staged the squad and the pod
    if (zoom) { B._cam.z = zoom; centerCamOn(B, vp, (at.x + 0.5) * TS, (at.y + 0.5) * TS); applyCam(B, pz, vp); B._camTouched = true; }
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
  await page.evaluate((squad) => {
    const S = G.state, c = S.contracts.find(c => c.type === 'patrol') || S.contracts[0];
    // staged: the same four people every review (see --squad), two men and two women
    squad.roster.forEach((o, i) => Object.assign(S.roster[i], o));
    startBattle(c, S.roster.slice(0, 4).map(s => s.id));
  }, SQUAD);
  await page.waitForTimeout(400); await dismiss(page);
  if (FOES) return stageFoes(page);
  // A fair comparison: clear weather (fog stripes muddy the art), the squad gathered mid-map on level ground so the
  // camera isn't pinned to an edge, and the founding grave raised as a Fighter revenant on the Commander's flank.
  await page.evaluate((grave) => {
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
    g.snap.cls = grave.cls; g.snap.weapon = grave.weapon; g.snap.commander = false; g.look = grave.look;
    spawnRevenant(B, g);
    const rv = B.units.find(u => u.graveId === g.id), cmd = pcs[0];
    for (const [dx, dy] of [[3, 0], [3, 1], [4, 0], [3, -1], [2, 1]]) {
      const x = cmd.x + dx, y = cmd.y + dy;
      if (ok(x, y, elevAt(B, cmd.x, cmd.y))) { rv.x = x; rv.y = y; break; }
    }
    B._camTouched = false; B._camFollow = null;
    render();
  }, SQUAD.grave);
  await page.waitForTimeout(300); await dismiss(page);
}

// --foes: the squad gathered mid-map as for the classes, and a pod of four of the foe a few tiles before it
async function stageFoes(page) {
  await page.evaluate((key) => {
    const S = G.state, B = S.battle;
    B.weather = null; B.rain = false;
    let best = null;   // the most central open, level patch: 8x4 if the map has one, else 7x3, else 6x3
    for (const [w, h] of [[8, 4], [7, 3], [6, 3]]) {
      for (let y = 2; y < GH - h - 1; y++) for (let x = 2; x < GW - w - 1; x++) {
        const z = elevAt(B, x, y); let fits = true;
        for (let dy = 0; dy < h && fits; dy++) for (let dx = 0; dx < w && fits; dx++) { const t = tileAt(B, x + dx, y + dy); fits = t && !bImpass(t.t) && !t.blighted && elevAt(B, x + dx, y + dy) === z; }
        const d = Math.abs(x + w / 2 - GW / 2) + Math.abs(y + h / 2 - GH / 2);
        if (fits && (!best || d < best.d)) best = { x, y, w, h, d };
      }
      if (best) break;
    }
    const pcs = B.units.filter(u => u.kind === 'pc');
    for (const u of B.units.filter(u => u.kind !== 'pc')) if (u.x >= best.x - 2 && u.x <= best.x + best.w + 1 && u.y >= best.y - 2 && u.y <= best.y + best.h + 1) { u.hp = 0; }
    B.units = B.units.filter(u => u.hp > 0);
    [[0, 1], [1, 0], [1, 2], [0, 2]].forEach(([dx, dy], i) => { if (pcs[i]) { pcs[i].x = best.x + dx; pcs[i].y = best.y + dy; } });
    // four of the foe at the patch's far end; the last two carry its tier upgrades (TIER_UPGRADES' tags), so every
    // look is on the board
    const tags = (TIER_UPGRADES[key] || []).filter(t => t.tag).map(t => t.tag);
    const { w, h } = best;
    const pod = [[w - 3, 0], [w - 2, 1], [w - 3, h - 1], [w - 1, h - 1]].map(([dx, dy], i) => {
      const u = spawnEnemy(B, key, 1, false); u.x = best.x + dx; u.y = best.y + dy;
      u.name = ENEMIES[key].n; const tag = tags[i - 2]; if (tag) u.name = tag + ' ' + u.name;
      return u;
    });
    // the pod stays in view whatever the fog (one of them standing behind another would otherwise go unseen)
    B._podKeys = pod.map(u => u.x + ',' + u.y);
    if (!window.__origVis) {
      window.__origVis = window.computeVis;
      window.computeVis = (b) => { const v = window.__origVis(b); for (const k of b._podKeys || []) v.add(k); return v; };
    }
    B._podCentre = { x: best.x + (w - 1) / 2, y: best.y + (h - 1) / 2 };     // frame() centres the zoomed shots on it
    B._camTouched = false; B._camFollow = null;
    render();
  }, FOES);
  await page.waitForTimeout(300); await dismiss(page);
}

// where the staged units sit on screen (CSS px), so review crops follow the units instead of fixed pixel boxes
const rects = (page) => page.evaluate(() => {
  const r = (el) => { if (!el) return null; const b = el.getBoundingClientRect(); return { x: b.x, y: b.y, w: b.width, h: b.height }; };
  return { commander: r(document.querySelector('#grid .unit.pc.current')), revenant: r(document.querySelector('#grid .unit.rev')),
           foes: [...document.querySelectorAll('#grid .unit.foe, #grid .unit.undead')].map(r),
           grid: r(document.getElementById('grid')), vw: innerWidth, vh: innerHeight };
});

const browser = await chromium.launch(process.env.PW_CHROMIUM ? { executablePath: process.env.PW_CHROMIUM } : {});
const shots = [], meta = {};    // (a foe pod beside the squad is too wide for a phone at the classes' 1.75x)
for (const dev of [{ n: 'desktop', vp: { width: 1280, height: 800 }, zooms: [0, 2.2] }, { n: 'phone', vp: { width: 390, height: 844 }, zooms: [0, FOES ? 1.3 : 1.75] }]) {
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
