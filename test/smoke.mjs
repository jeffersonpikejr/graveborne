// v0.66 smoke: boot → battle at instant speed → enemy phase completes fast → error banner shows → resume keeps setting.
const { chromium } = await import(process.env.PW_MODULE || 'playwright');   // PW_MODULE=/path/to/playwright/index.mjs if not installed locally
const BASE = process.env.GB_URL || 'http://localhost:8931/';                 // python3 -m http.server 8931 --directory . in the repo root

const fail = (m) => { console.error('FAIL: ' + m); process.exit(1); };
const browser = await chromium.launch(process.env.PW_CHROMIUM ? { executablePath: process.env.PW_CHROMIUM } : {});
const page = await browser.newPage({ viewport: { width: 420, height: 800 } });
const errors = [];
page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()); });

const dismissModals = async () => {
  for (let i = 0; i < 12; i++) {
    const clicked = await page.evaluate(() => {
      const m = document.querySelector('#modal button');
      if (m) { m.click(); return true; } return false;
    });
    if (!clicked) break;
    await page.waitForTimeout(150);
  }
};
await page.goto(BASE, { waitUntil: 'load' });
await page.waitForTimeout(600);

// fresh company, deterministic-ish entry
await page.evaluate(() => { localStorage.clear(); G.newGame(); });
await page.waitForTimeout(300);
await dismissModals();

// cycle the speed button: 1 -> 2 -> 3(instant) -> wraps to 1; leave at instant
const cyc = await page.evaluate(() => { SPEED(); SPEED(); const a = G.state.battleSpeed; SPEED(); const b = G.state.battleSpeed; SPEED(); SPEED(); return [a, b, G.state.battleSpeed]; });
if (cyc[0] !== 3 || cyc[1] !== 1 || cyc[2] !== 3) fail('speed cycle wrong: ' + JSON.stringify(cyc));

// start a real battle from the first contract
const started = await page.evaluate(() => {
  const c = G.state.contracts[0]; if (!c) return 'no-contract';
  const squad = G.state.roster.slice(0, 4).map(s => s.id);
  startBattle(c, squad); return G.state.battle ? 'ok' : 'no-battle';
});
if (started !== 'ok') fail('battle start: ' + started);
await page.waitForTimeout(400);
await dismissModals();

// speed button should render the instant glyph in battle
const glyph = await page.evaluate(() => { const b = [...document.querySelectorAll('#zoombtns button')].pop(); return b && b.textContent; });
if (glyph !== '⚡') fail('speed button glyph: ' + glyph);

// end the player phase; at instant speed the whole enemy phase should resolve in ~a second even with pods
await dismissModals();
const t0 = Date.now();
await page.evaluate(() => ENDT());
await page.waitForFunction(() => { const B = G.state.battle; return !B || B.over || B.phase === 'player'; }, null, { timeout: 8000 }).catch(() => fail('enemy phase did not return to player within 8s at instant speed'));
const enemyMs = Date.now() - t0;

// round-trip: back to 1x, make sure the throttle helper restores full pauses (no NaN / stuck state)
await page.evaluate(() => { SPEED(); const sp = G.state.battleSpeed; if (sp !== 1) throw new Error('expected wrap to 1x, got ' + sp); });

// stash + resume mid-battle keeps the setting and re-kicks cleanly
await page.evaluate(() => { G.state.battleSpeed = 3; window.dispatchEvent(new Event('pagehide')); });
await page.reload({ waitUntil: 'load' });
await page.waitForTimeout(700);
await dismissModals();
const resumed = await page.evaluate(() => ({ b: !!G.state.battle, sp: G.state.battleSpeed }));
if (!resumed.b) fail('battle did not resume after reload');
if (resumed.sp !== 3) fail('battleSpeed not restored on resume: ' + resumed.sp);

// error banner: a thrown error must surface as .errtoast
await page.evaluate(() => { setTimeout(() => { throw new Error('smoke-test boom'); }, 0); });
await page.waitForTimeout(300);
const toast = await page.evaluate(() => { const t = document.querySelector('.errtoast'); return t && t.textContent; });
if (!toast || !toast.includes('smoke-test boom')) fail('error toast missing: ' + toast);

// no unexpected page errors besides the deliberate one
const unexpected = errors.filter(e => !e.includes('smoke-test boom') && !e.includes('Failed to load resource'));
if (unexpected.length) fail('unexpected errors: ' + JSON.stringify(unexpected, null, 1));

console.log('PASS — enemy phase at instant speed: ' + enemyMs + 'ms; toast + resume + cycle OK');
await browser.close();
