// v0.67 save-spine smoke: fresh stamp → legacy record walks the gauntlet once → one-shot versioned backup →
// both stash shapes resume (twice) → resume path snapshots → corrupt main save recovers → new banner from recovery.
const { chromium } = await import(process.env.PW_MODULE || 'playwright');   // PW_MODULE=/path/to/playwright/index.mjs if not installed locally
const BASE = process.env.GB_URL || 'http://localhost:8931/';                 // python3 -m http.server 8931 --directory . in the repo root
const fail = (m) => { console.error('FAIL: ' + m); process.exit(1); };
const browser = await chromium.launch(process.env.PW_CHROMIUM ? { executablePath: process.env.PW_CHROMIUM } : {});
const page = await browser.newPage({ viewport: { width: 420, height: 800 } });
const errors = [];
page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
// The game re-stashes a live battle on visibilitychange/pagehide during navigation, so hand-edits to the stash made
// in the OLD document get overwritten. Patch the stash from an init script instead: it runs in the NEW document
// before the game script, driven by a one-shot job left in localStorage.
await page.addInitScript(() => {
  const job = localStorage.getItem('__test_stash_job'); if (!job) return;
  localStorage.removeItem('__test_stash_job');
  const j = JSON.parse(job);
  if (j.dropBackup) localStorage.removeItem('graveborne_pre_v67');
  const d = JSON.parse(localStorage.getItem('graveborne_active_v01') || 'null'); if (!d) return;
  if (j.stripVer) delete d.S.ver;
  if (j.legacyDims) { d.GW = d.S.battle.gw; d.GH = d.S.battle.gh; delete d.S.battle.gw; delete d.S.battle.gh; }
  localStorage.setItem('graveborne_active_v01', JSON.stringify(d));
});
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
if (fresh.ver !== 67) fail('fresh ver: ' + fresh.ver);
if (!fresh.face) fail('founding grave has no face on a fresh record');
await boot();
const reloaded = await page.evaluate(() => ({ ver: G.state.ver, backup: localStorage.getItem('graveborne_pre_v67') }));
if (reloaded.ver !== 67) fail('ver after reload: ' + reloaded.ver);
if (reloaded.backup) fail('a current-shape save must NOT write a pre-migration backup');

// 2. legacy record (no ver, fields the gauntlet restores stripped) walks once, gets stamped, gets backed up
const legacyRaw = await page.evaluate((raw) => {
  const d = JSON.parse(raw); const S = d.S;
  delete S.ver; delete S.unlocks; delete S.kits; delete S.horns; delete S.mapWide; delete S.crossTried; delete S.deedPrimerSeen; delete S.pendingSwordFate;
  for (const s of S.roster) { delete s.deeds; delete s.retinue; delete s.oath; }
  const out = JSON.stringify(d); localStorage.setItem('graveborne_v01', out); return out;
}, fresh.raw);
await boot();
const mig = await page.evaluate(() => {
  const S = G.state; return { ver: S.ver, unlocks: !!S.unlocks, kits: S.kits, mapWide: S.mapWide, deeds: Array.isArray(S.roster[0].deeds), retinue: Array.isArray(S.roster[0].retinue),
    savedVer: JSON.parse(localStorage.getItem('graveborne_v01')).S.ver, backup: localStorage.getItem('graveborne_pre_v67') };
});
if (mig.ver !== 67 || mig.savedVer !== 67) fail('legacy record not stamped/saved: ' + JSON.stringify(mig));
if (!mig.unlocks || mig.kits !== 0 || mig.mapWide !== false || !mig.deeds || !mig.retinue) fail('legacy gauntlet did not restore fields: ' + JSON.stringify(mig));
if (mig.backup !== legacyRaw) fail('pre-migration backup must equal the untouched legacy record');

// 3. the backup is one-shot per target: a second legacy record must not overwrite it
await page.evaluate((raw) => { const d = JSON.parse(raw); delete d.S.ver; d.S.coin = 9999; localStorage.setItem('graveborne_v01', JSON.stringify(d)); }, fresh.raw);
await boot();
const oneShot = await page.evaluate(() => ({ coin: G.state.coin, ver: G.state.ver, backup: localStorage.getItem('graveborne_pre_v67') }));
if (oneShot.coin !== 9999 || oneShot.ver !== 67) fail('second legacy load wrong: ' + JSON.stringify(oneShot));
if (oneShot.backup !== legacyRaw) fail('backup was overwritten by a later legacy load');

// 4a. v0.67 stash with its ver stripped: the battle carries gw/gh; the RESUME path migrates and stamps
await dismissModals();
const st = await page.evaluate(() => { const c = G.state.contracts[0]; startBattle(c, G.state.roster.slice(0, 4).map(s => s.id)); const B = G.state.battle; return { gw: B.gw, gh: B.gh, tiles: B.tiles.length }; });
if (typeof st.gw !== 'number' || st.gw * st.gh !== st.tiles) fail('battle does not carry its dims: ' + JSON.stringify(st));
await dismissModals();
await job({ stripVer: true });
await boot(); await dismissModals();
const r1 = await page.evaluate(() => { const B = G.state.battle; return { resumed: !!B, ver: G.state.ver, gw: B && B.gw, tiles: B && B.tiles.length, grid: !!document.getElementById('grid') }; });
if (!r1.resumed || r1.ver !== 67 || !r1.grid) fail('v0.67 stash resume: ' + JSON.stringify(r1));

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
const snap = await page.evaluate(() => ({ backup: !!localStorage.getItem('graveborne_pre_v67'), ver: G.state.ver, resumed: !!G.state.battle }));
if (!snap.resumed || snap.ver !== 67 || !snap.backup) fail('resume path did not snapshot before migrating: ' + JSON.stringify(snap));

// 5. recovery: corrupt main save + a versioned backup present → modal offers restore → restore works
await page.evaluate(() => { G.state.battle = null; localStorage.removeItem('graveborne_active_v01'); localStorage.setItem('graveborne_v01', '{"S":{"broken":'); });   // no live battle, or pagehide re-stashes it and boot never reads the main save
await boot();
const rec = await page.evaluate(() => { const m = document.querySelector('#modal'); return m ? m.textContent : null; });
if (!rec || !rec.includes('Restore the company and reload')) fail('recovery modal did not offer the versioned backup: ' + (rec || '').slice(0, 120));
await page.evaluate(() => { const b = [...document.querySelectorAll('#modal button')].find(x => x.textContent.includes('Restore')); b.click(); });
await page.waitForTimeout(900);
const after = await page.evaluate(() => ({ ver: G.state.ver, roster: G.state.roster.length, battle: !!G.state.battle }));
if (after.ver !== 67 || !after.roster || after.battle) fail('restore from backup failed: ' + JSON.stringify(after));

// 5b. from the recovery modal with NO company loaded, "Raise a new banner" must work (was a TypeError on null S)
await page.evaluate(() => { G.state.battle = null; localStorage.removeItem('graveborne_active_v01'); localStorage.setItem('graveborne_v01', '{"S":{"broken":'); });
await boot();
const nb = await page.evaluate(() => { const b = [...document.querySelectorAll('#modal button')].find(x => x.textContent.includes('Raise a new banner')); if (!b) return 'no-button'; b.click(); return { s: !!G.state, ver: G.state && G.state.ver, roster: G.state && G.state.roster.length }; });
if (nb === 'no-button' || !nb.s || nb.ver !== 67 || !nb.roster) fail('"Raise a new banner" from recovery with no company loaded: ' + JSON.stringify(nb));

const unexpected = errors.filter(e => !e.includes('Failed to load resource'));
if (unexpected.length) fail('unexpected page errors: ' + JSON.stringify(unexpected, null, 1));
console.log('PASS — fresh stamp+face · legacy walk+stamp · one-shot backup · both stash shapes resume (twice) · resume-path snapshot · recovery restore · new banner from recovery');
await browser.close();
