// Save-spine smoke (v0.67 spine, v0.69 shape): fresh stamp → legacy record walks the gauntlet once → one-shot
// versioned backup → both stash shapes resume (twice) → resume path snapshots → corrupt main save recovers → new
// banner from recovery → an oath-crisis release leaves no stub, and v0.67 records carrying stubs load clean →
// every soldier is dealt a head of their own, and a v0.68 company is dealt heads that match its faces.
const { chromium } = await import(process.env.PW_MODULE || 'playwright');   // PW_MODULE=/path/to/playwright/index.mjs if not installed locally
const BASE = process.env.GB_URL || 'http://localhost:8931/';                 // python3 -m http.server 8931 --directory . in the repo root
const fail = (m) => { console.error('FAIL: ' + m); process.exit(1); };
const VER = 69, BACKUP = 'graveborne_pre_v' + VER;                          // bump both with SAVE_VER
const browser = await chromium.launch(process.env.PW_CHROMIUM ? { executablePath: process.env.PW_CHROMIUM } : {});
const page = await browser.newPage({ viewport: { width: 420, height: 800 } });
const errors = [];
page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
// The game re-stashes a live battle on visibilitychange/pagehide during navigation, so hand-edits to the stash made
// in the OLD document get overwritten. Patch the stash from an init script instead: it runs in the NEW document
// before the game script, driven by a one-shot job left in localStorage.
await page.addInitScript((BACKUP) => {
  const job = localStorage.getItem('__test_stash_job'); if (!job) return;
  localStorage.removeItem('__test_stash_job');
  const j = JSON.parse(job);
  if (j.dropBackup) localStorage.removeItem(BACKUP);
  const d = JSON.parse(localStorage.getItem('graveborne_active_v01') || 'null'); if (!d) return;
  if (j.stripVer) delete d.S.ver;
  if (j.legacyDims) { d.GW = d.S.battle.gw; d.GH = d.S.battle.gh; delete d.S.battle.gw; delete d.S.battle.gh; }
  localStorage.setItem('graveborne_active_v01', JSON.stringify(d));
}, BACKUP);
const boot = async () => { await page.goto(BASE, { waitUntil: 'load' }); await page.waitForTimeout(500); };
const job = async (j) => page.evaluate((j) => localStorage.setItem('__test_stash_job', JSON.stringify(j)), j);
const dismissModals = async () => {
  for (let i = 0; i < 12; i++) {
    const clicked = await page.evaluate(() => { const m = document.querySelector('#modal button'); if (m) { m.click(); return true; } return false; });
    if (!clicked) break; await page.waitForTimeout(150);
  }
};

// 1. fresh record is born stamped, and survives a plain save/load
await boot();
await page.evaluate(() => { localStorage.clear(); G.newGame(); });
await dismissModals();
const fresh = await page.evaluate(() => { G.save(); return { ver: G.state.ver, raw: localStorage.getItem('graveborne_v01'), face: !!G.state.graves[0].face }; });
if (fresh.ver !== VER) fail('fresh ver: ' + fresh.ver);
if (!fresh.face) fail('founding grave has no face on a fresh record');
await boot();
const reloaded = await page.evaluate((BACKUP) => ({ ver: G.state.ver, backup: localStorage.getItem(BACKUP) }), BACKUP);
if (reloaded.ver !== VER) fail('ver after reload: ' + reloaded.ver);
if (reloaded.backup) fail('a current-shape save must NOT write a pre-migration backup');

// 2. legacy record (no ver, fields the gauntlet restores stripped) walks once, gets stamped, gets backed up
const legacyRaw = await page.evaluate((raw) => {
  const d = JSON.parse(raw); const S = d.S;
  delete S.ver; delete S.unlocks; delete S.kits; delete S.horns; delete S.mapWide; delete S.crossTried; delete S.deedPrimerSeen; delete S.pendingSwordFate;
  for (const s of S.roster) { delete s.deeds; delete s.retinue; delete s.oath; }
  const out = JSON.stringify(d); localStorage.setItem('graveborne_v01', out); return out;
}, fresh.raw);
await boot();
const mig = await page.evaluate((BACKUP) => {
  const S = G.state; return { ver: S.ver, unlocks: !!S.unlocks, kits: S.kits, mapWide: S.mapWide, deeds: Array.isArray(S.roster[0].deeds), retinue: Array.isArray(S.roster[0].retinue),
    savedVer: JSON.parse(localStorage.getItem('graveborne_v01')).S.ver, backup: localStorage.getItem(BACKUP) };
}, BACKUP);
if (mig.ver !== VER || mig.savedVer !== VER) fail('legacy record not stamped/saved: ' + JSON.stringify(mig));
if (!mig.unlocks || mig.kits !== 0 || mig.mapWide !== false || !mig.deeds || !mig.retinue) fail('legacy gauntlet did not restore fields: ' + JSON.stringify(mig));
if (mig.backup !== legacyRaw) fail('pre-migration backup must equal the untouched legacy record');

// 3. the backup is one-shot per target: a second legacy record must not overwrite it
await page.evaluate((raw) => { const d = JSON.parse(raw); delete d.S.ver; d.S.coin = 9999; localStorage.setItem('graveborne_v01', JSON.stringify(d)); }, fresh.raw);
await boot();
const oneShot = await page.evaluate((BACKUP) => ({ coin: G.state.coin, ver: G.state.ver, backup: localStorage.getItem(BACKUP) }), BACKUP);
if (oneShot.coin !== 9999 || oneShot.ver !== VER) fail('second legacy load wrong: ' + JSON.stringify(oneShot));
if (oneShot.backup !== legacyRaw) fail('backup was overwritten by a later legacy load');

// 4a. v0.67 stash with its ver stripped: the battle carries gw/gh; the RESUME path migrates and stamps
await dismissModals();
const st = await page.evaluate(() => { const c = G.state.contracts[0]; startBattle(c, G.state.roster.slice(0, 4).map(s => s.id)); const B = G.state.battle; return { gw: B.gw, gh: B.gh, tiles: B.tiles.length }; });
if (typeof st.gw !== 'number' || st.gw * st.gh !== st.tiles) fail('battle does not carry its dims: ' + JSON.stringify(st));
await dismissModals();
await job({ stripVer: true });
await boot(); await dismissModals();
const r1 = await page.evaluate(() => { const B = G.state.battle; return { resumed: !!B, ver: G.state.ver, gw: B && B.gw, tiles: B && B.tiles.length, grid: !!document.getElementById('grid') }; });
if (!r1.resumed || r1.ver !== VER || !r1.grid) fail('stash resume (ver stripped): ' + JSON.stringify(r1));

// 4b. an older build's stash kept GW/GH beside S — must resume, adopt them, and resume AGAIN from its own re-stash
await job({ legacyDims: true });
await boot(); await dismissModals();
const r2 = await page.evaluate(() => { const B = G.state.battle; return { resumed: !!B, grid: !!document.getElementById('grid'), gw: B && B.gw, gh: B && B.gh, tiles: B && B.tiles.length, units: B && B.units.filter(u => document.querySelector(`.unit[data-uid="${u.uid}"]`)).length }; });
if (!r2.resumed || !r2.grid || !r2.units || r2.gw * r2.gh !== r2.tiles) fail('legacy-shape stash resume (adopt dims): ' + JSON.stringify(r2));
await boot(); await dismissModals();   // plain re-stash by this build → second resume must still have dims
const r2c = await page.evaluate(() => { const B = G.state.battle; const d = JSON.parse(localStorage.getItem('graveborne_active_v01')); return { resumed: !!B, tiles: B && B.tiles.length, gw: B && B.gw, gh: B && B.gh, top: d && d.GW }; });
if (!r2c.resumed || r2c.gw * r2c.gh !== r2c.tiles || r2c.top !== undefined) fail('second resume of a legacy-shape battle: ' + JSON.stringify(r2c));

// 4c. the RESUME path must take the pre-migration snapshot too (main record on disk = clean pre-battle save)
await job({ stripVer: true, dropBackup: true });
await boot(); await dismissModals();
const snap = await page.evaluate((BACKUP) => ({ backup: !!localStorage.getItem(BACKUP), ver: G.state.ver, resumed: !!G.state.battle }), BACKUP);
if (!snap.resumed || snap.ver !== VER || !snap.backup) fail('resume path did not snapshot before migrating: ' + JSON.stringify(snap));

// 5. recovery: corrupt main save + a versioned backup present → modal offers restore → restore works
await page.evaluate(() => { G.state.battle = null; localStorage.removeItem('graveborne_active_v01'); localStorage.setItem('graveborne_v01', '{"S":{"broken":'); });   // no live battle, or pagehide re-stashes it and boot never reads the main save
await boot();
const rec = await page.evaluate(() => { const m = document.querySelector('#modal'); return m ? m.textContent : null; });
if (!rec || !rec.includes('Restore the company and reload')) fail('recovery modal did not offer the versioned backup: ' + (rec || '').slice(0, 120));
await page.evaluate(() => { const b = [...document.querySelectorAll('#modal button')].find(x => x.textContent.includes('Restore')); b.click(); });
await page.waitForTimeout(900);
const after = await page.evaluate(() => ({ ver: G.state.ver, roster: G.state.roster.length, battle: !!G.state.battle }));
if (after.ver !== VER || !after.roster || after.battle) fail('restore from backup failed: ' + JSON.stringify(after));

// 5b. from the recovery modal with NO company loaded, "Raise a new banner" must work (was a TypeError on null S)
await page.evaluate(() => { G.state.battle = null; localStorage.removeItem('graveborne_active_v01'); localStorage.setItem('graveborne_v01', '{"S":{"broken":'); });
await boot();
const nb = await page.evaluate(() => { const b = [...document.querySelectorAll('#modal button')].find(x => x.textContent.includes('Raise a new banner')); if (!b) return 'no-button'; b.click(); return { s: !!G.state, ver: G.state && G.state.ver, roster: G.state && G.state.roster.length }; });
if (nb === 'no-button' || !nb.s || nb.ver !== VER || !nb.roster) fail('"Raise a new banner" from recovery with no company loaded: ' + JSON.stringify(nb));

// 6a. an oath-crisis release: the soldier leaves the roster, the chronicle keeps it, and nothing lands among the
//     deserters (it used to push a stub with no weekGone: "NaN wk to find them", a broken buy-back)
await dismissModals();
const rel = await page.evaluate(() => {
  const S = G.state, s = S.roster[1];
  s.oath = { to: 'folk', state: 'strained', strain: 3, receipts: ['the company sold a grave'] };
  const before = (S.deserters || []).length, chron = S.chronicle.length;
  oathCrisisModal(s);
  const b = [...document.querySelectorAll('#modal button')].find(x => x.textContent.startsWith('Release her'));
  if (!b) return 'no-button';
  b.click();
  return { gone: !S.roster.includes(s), deserters: (S.deserters || []).length - before, chronicled: S.chronicle.length === chron + 1,
    stubs: (S.deserters || []).filter(d => d.released).length };
});
if (rel === 'no-button' || !rel.gone || rel.deserters !== 0 || rel.stubs || !rel.chronicled) fail('oath-crisis release: ' + JSON.stringify(rel));

// 6b. a v0.67 record carrying stubs (one among the deserters as the old release left it, walked by v0.67's class
//     inference; one a buy-back already carried onto the roster) loads clean at v0.68: stubs gone, real deserters
//     kept, a pre-migration backup of the stubbed record taken, no NaN countdown, no card throws, weeks tick over
const stubRaw = await page.evaluate((BACKUP) => {
  const d = JSON.parse(localStorage.getItem('graveborne_v01')); const S = d.S;
  S.ver = 67;
  const real = JSON.parse(JSON.stringify(S.roster[0])); real.id = 9001; real.name = 'Real Deserter'; real.commander = false;
  real.town = 0; real.weekGone = S.week; real.wasCommander = false;
  S.deserters = [real,
    { name: 'Stub Released', level: 2, town: 0, released: true, cls: 'fighter', deeds: [], retinue: [], oath: null, bannerWeek: 0 }];
  S.roster.push({ name: 'Stub Bought Back', level: 1, released: true, cls: 'fighter', deeds: [], retinue: [], oath: null, bannerWeek: 0 });
  localStorage.removeItem(BACKUP);
  const out = JSON.stringify(d); localStorage.setItem('graveborne_v01', out); return out;
}, BACKUP);
await boot(); await dismissModals();
const cleaned = await page.evaluate((BACKUP) => {
  const S = G.state;
  G.weeklyTick(); G.save();
  // the rendered page, collapsed panels included (the deserters list folds away at phone width), script source excluded
  const page = [...document.body.children].filter(e => e.tagName !== 'SCRIPT').map(e => e.textContent).join(' ');
  const lines = [...document.querySelectorAll('.statline')].map(e => e.textContent).filter(t => t.includes('wk to find them'));
  return { ver: S.ver, deserters: S.deserters.map(d => d.name), stubs: [...S.deserters, ...S.roster].filter(p => p.released).length,
    backup: localStorage.getItem(BACKUP), listed: lines.some(t => t.includes('Real Deserter')), nan: page.includes('NaN') };
}, BACKUP);
if (cleaned.ver !== VER || cleaned.stubs || cleaned.nan || !cleaned.listed || cleaned.deserters.join() !== 'Real Deserter') fail('v0.67 record with stubs: ' + JSON.stringify({ ...cleaned, backup: !!cleaned.backup }));
if (cleaned.backup !== stubRaw) fail('pre-v0.68 backup must equal the untouched stubbed record');

// 7a. looks (v0.69): a fresh company is dealt heads of its own. Never two alike among the living, the founding
//     Commander a founder's head and nobody else one, the founding grave a head, every procedural face agreeing
//     with its head; the living stay unique through a full roster and forty turns of the hire pool; a grave keeps
//     its head. The game's LOOKS must be the pipeline's manifest.
await page.evaluate(() => { localStorage.clear(); G.newGame(); });
await dismissModals();
const dealt = await page.evaluate(async () => {
  const S = G.state, manifest = await (await fetch('art/sprites/heads/looks.json')).json();
  const living = () => { const o = []; for (const arr of [S.roster, S.hirePool, S.deserters || []]) for (const p of arr) { o.push(p); for (const w of p.retinue || []) o.push(w); } return o; };
  const dupes = () => { const ids = living().map(p => p.look).filter(Boolean); return ids.length - new Set(ids).size; };
  const agree = p => { const e = lookEntry(p.look); return !!e && e[0] === p.face.skin && e[1] === p.face.hc && e[2] === p.face.hair; };
  const cmd = S.roster.find(p => p.commander);
  const out = { manifest: JSON.stringify(manifest) === JSON.stringify(LOOKS), all: living().every(p => lookEntry(p.look)), dupes: dupes(),
    founder: !!cmd.look && +cmd.look.slice(1) < LOOKS.founders, others: living().filter(p => p !== cmd).every(p => !!p.look && +p.look.slice(1) >= LOOKS.founders),
    agree: living().every(agree), grave: !!lookEntry(S.graves[0].look) };
  let worst = 0;
  for (let i = 0; i < 40; i++) {
    if (S.roster.length < ROSTER_CAP) S.roster.push(S.hirePool.shift());
    refreshHirePool(); worst = Math.max(worst, dupes());
  }
  out.churn = worst; out.full = S.roster.length === ROSTER_CAP;
  const s = S.roster[S.roster.length - 1], look = s.look;
  G.dbgKill(s.id);
  out.kept = S.graves[S.graves.length - 1].look === look;
  return out;
});
if (!dealt.manifest) fail('LOOKS must equal art/sprites/heads/looks.json: paste the manifest the looks pipeline wrote');
if (!dealt.all || dealt.dupes || !dealt.founder || !dealt.others || !dealt.agree || !dealt.grave || dealt.churn || !dealt.full || !dealt.kept) fail('looks on a fresh company: ' + JSON.stringify(dealt));

// 7b. a v0.68 company (no heads) loads at v0.69 dealt heads that match its faces: a bearded face a bearded head,
//     the skin kept; the living unique; the Commander (no Commander has fallen) a founder's head; every grave a
//     head; the faces themselves untouched; a pre-migration backup of the v0.68 record taken
const v68Raw = await page.evaluate((BACKUP) => {
  G.save();
  const d = JSON.parse(localStorage.getItem('graveborne_v01')); const S = d.S;
  S.ver = 68;
  const strip = p => { delete p.look; for (const w of p.retinue || []) delete w.look; };
  for (const arr of [S.roster, S.hirePool, S.deserters || []]) arr.forEach(strip);
  for (const g of S.graves) { delete g.look; for (const w of (g.snap && g.snap.retinue) || []) delete w.look; }
  S.roster[1].face.hair = 5;
  S.roster[2].face = { skin: 3, hair: 1, hc: 2, eyes: 0, mouth: 0, extra: 0 };
  localStorage.removeItem(BACKUP);
  const out = JSON.stringify(d); localStorage.setItem('graveborne_v01', out); return out;
}, BACKUP);
await boot(); await dismissModals();
const dealt68 = await page.evaluate((BACKUP) => {
  const S = G.state, before = JSON.parse(localStorage.getItem(BACKUP) || 'null');
  const living = []; for (const arr of [S.roster, S.hirePool, S.deserters || []]) for (const p of arr) { living.push(p); for (const w of p.retinue || []) living.push(w); }
  const cmd = S.roster.find(p => p.commander);
  const ids = living.map(p => p.look).filter(Boolean);
  return { ver: S.ver, all: living.every(p => lookEntry(p.look)), dupes: ids.length - new Set(ids).size,
    founder: !!cmd.look && +cmd.look.slice(1) < LOOKS.founders,
    bearded: !!S.roster[1].look && S.roster[1].look[0] === 'm' && (lookEntry(S.roster[1].look) || [])[2] === 5,
    skin: (lookEntry(S.roster[2].look) || [])[0] === 3, graves: S.graves.every(g => lookEntry(g.look)),
    faces: !!before && JSON.stringify(S.roster.map(p => p.face)) === JSON.stringify(before.S.roster.map(p => p.face)),
    backup: localStorage.getItem(BACKUP) };
}, BACKUP);
if (dealt68.ver !== VER || !dealt68.all || dealt68.dupes || !dealt68.founder || !dealt68.bearded || !dealt68.skin || !dealt68.graves || !dealt68.faces) fail('v0.68 company dealt heads: ' + JSON.stringify({ ...dealt68, backup: !!dealt68.backup }));
if (dealt68.backup !== v68Raw) fail('pre-v0.69 backup must equal the untouched v0.68 record');

const unexpected = errors.filter(e => !e.includes('Failed to load resource'));
if (unexpected.length) fail('unexpected page errors: ' + JSON.stringify(unexpected, null, 1));
console.log('PASS — fresh stamp+face · legacy walk+stamp · one-shot backup · both stash shapes resume (twice) · resume-path snapshot · recovery restore · new banner from recovery · release leaves no stub · stubbed v0.67 record loads clean · heads dealt unique · v0.68 company dealt matching heads');
await browser.close();
