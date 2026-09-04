// v0.68 trust-patch smoke: pressure bar renders → a fled courier beat re-posts → story beats survive a swallowed
// region → a fled heir beat re-posts but a WON one does not → the sword cap is said at muster and on the field →
// the reckoning fields the whole graveyard under the engine ceiling.
const { chromium } = await import(process.env.PW_MODULE || 'playwright');   // PW_MODULE=/path/to/playwright/index.mjs if not installed locally
const BASE = process.env.GB_URL || 'http://localhost:8931/';                 // python3 -m http.server 8931 --directory . in the repo root
const fail = (m) => { console.error('FAIL: ' + m); process.exit(1); };
const browser = await chromium.launch(process.env.PW_CHROMIUM ? { executablePath: process.env.PW_CHROMIUM } : {});
const page = await browser.newPage({ viewport: { width: 420, height: 800 } });
const errors = [];
page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
const dismissModals = async () => {
  for (let i = 0; i < 12; i++) {
    const clicked = await page.evaluate(() => { const m = document.querySelector('#modal button'); if (m) { m.click(); return true; } return false; });
    if (!clicked) break; await page.waitForTimeout(150);
  }
};
await page.goto(BASE, { waitUntil: 'load' }); await page.waitForTimeout(500);
await page.evaluate(() => { localStorage.clear(); G.newGame(); });
await dismissModals();

// 1. the pressure bar is back: select the caravan's hex and read the region panel
const bar = await page.evaluate(() => { sel = G.state.caravan.q + ',' + G.state.caravan.r; render(); const b = document.querySelector('.pressure > div'); return b ? b.style.width : null; });
if (!bar || !/^\d+%$/.test(bar)) fail('pressure bar missing from the region panel: ' + bar);

// 2. courier beat: post it, march, sound the retreat → the contract is consumed AND re-posted, stage unchanged
const posted = await page.evaluate(() => { G.state.story.stage = 3; postCourierContract(); const c = G.state.contracts.find(c => c.story === 'courier'); return c ? { id: c.id, region: c.regionId, stage: G.state.story.stage } : null; });
if (!posted || posted.stage !== 4) fail('courier did not post: ' + JSON.stringify(posted));
await dismissModals();
await page.evaluate((id) => { const c = G.state.contracts.find(c => c.id === id); startBattle(c, G.state.roster.slice(0, 4).map(s => s.id)); }, posted.id);
await page.waitForTimeout(300); await dismissModals();
const retreated = await page.evaluate(async () => {
  RETREAT(); await new Promise(r => setTimeout(r, 100));
  const btns = [...document.querySelectorAll('#modal button')];
  const go = btns.find(b => /retreat|sound|fall back|leave/i.test(b.textContent) && !/stay|hold|not yet|fight/i.test(b.textContent)) || btns[0];
  const labels = btns.map(b => b.textContent);
  if (go) go.click();
  await new Promise(r => setTimeout(r, 400));
  const S = G.state; const again = S.contracts.find(c => c.story === 'courier');
  return { labels, battle: !!S.battle, stage: S.story.stage, again: !!again, newId: again && again.id, log: (S.log.find(l => /rides again/.test(l.msg)) || {}).msg };
});
if (retreated.battle) fail('retreat did not end the battle; modal buttons were ' + JSON.stringify(retreated.labels));
if (retreated.stage !== 4 || !retreated.again || retreated.newId === posted.id || !retreated.log) fail('courier not re-posted after retreat: ' + JSON.stringify(retreated));
await dismissModals();

// 3. a swallowed region no longer culls the story beat
const cull = await page.evaluate(() => { const c = G.state.contracts.find(c => c.story === 'courier'); const r = G.state.regions[c.regionId]; r.swallowed = true; genContracts(); const kept = G.state.contracts.some(x => x.id === c.id); r.swallowed = false; return kept; });
if (!cull) fail('story contract was culled with its swallowed region');

// 4. heir beat: choose → post; simulate a loss (contract gone, stage 7) → re-posts; then WIN the fight → the stage
//    advances synchronously (before any modal), and nothing re-posts
const heir = await page.evaluate(() => {
  const S = G.state; S.story.stage = 6; chooseHeir('aldric');
  const first = S.contracts.find(c => c.story === 'heir'); if (!first) return 'no-post';
  S.contracts = S.contracts.filter(c => c.story !== 'heir'); ensureStorySpine();
  const re = S.contracts.find(c => c.story === 'heir'); const relog = S.log.some(l => /posted again/.test(l.msg));
  return { stage: S.story.stage, re: !!re, reId: re && re.id, firstId: first.id, relog };
});
if (heir === 'no-post' || heir.stage !== 7 || !heir.re || heir.reId === heir.firstId || !heir.relog) fail('heir beat not re-posted on loss: ' + JSON.stringify(heir));
await dismissModals();
const heirWin = await page.evaluate(async () => {
  const S = G.state; const c = S.contracts.find(c => c.story === 'heir');
  startBattle(c, S.roster.slice(0, 4).map(s => s.id));
  endBattle('victory');
  const stageAtResolve = S.story.stage, weekAtResolve = S.story.heirWeek;   // read BEFORE any modal runs
  await new Promise(r => setTimeout(r, 200));
  return { stageAtResolve, weekAtResolve, battle: !!S.battle, reposted: S.contracts.some(x => x.story === 'heir') };
});
if (heirWin.stageAtResolve !== 8 || heirWin.weekAtResolve == null || heirWin.battle || heirWin.reposted) fail('heir WIN did not advance synchronously / re-posted: ' + JSON.stringify(heirWin));
await dismissModals();

// 5. sword cap honesty: three living swords on one banneret → muster names the one that stays; the field benches it and says so
const swords = await page.evaluate(() => {
  const S = G.state; const s = S.roster[0];
  s.retinue = [makeSword(), makeSword(), makeSword()].map((w, i) => { w.alive = true; if (w.id == null) w.id = nid(); w.name = 'Sword' + i; return w; });
  pickSquad(() => {}); TOG(s.id);
  const txt = document.querySelector('#modal').textContent; activeModal = null; render();
  startBattle(S.contracts[0], [s.id]);
  const B = S.battle; const out = { musterText: /stays? with the baggage/.test(txt) && /2 swords ride at most/.test(txt), rides: B.units.filter(u => u.sword).length, benchedLog: B.log.some(m => /stays with the baggage/.test(m)) };
  S.battle = null; clearStashedBattle(); s.retinue = []; render();
  return out;
});
if (!swords.musterText || swords.rides !== 2 || !swords.benchedLog) fail('sword cap not surfaced: ' + JSON.stringify(swords));
await dismissModals();

// 6. the reckoning fields EVERY risen grave (was capped at 3), under the engine ceiling, retinues filling after
const finale = await page.evaluate(() => {
  const S = G.state;
  for (let i = 0; i < 5; i++) { const s = makeSoldier(); S.graves.push({ id: nid(), soldierId: s.id, name: 'Fallen' + i, bg: s.bg, face: s.face,
    snap: { maxhp: 20, skl: 4, spd: 3, weapon: s.weapon, wMod: 0, armor: 0, feats: [], level: 3, cls: s.cls, commander: false, deeds: [], retinue: [] },
    bonds: [], state: 'risen', regionId: 3, weekDied: 1, iter: 0, hook: 'test' }); }
  // a late-game company: the budget must be big enough that the throne room's own reinforcements would fill to the
  // ceiling — the case where an unreserved comp fill used to leave the dead only two slots
  for (const s of S.roster) { s.level = 5; s.skl += 6; s.maxhp += 40; s.hp = s.maxhp; s.wMod = 2; }
  startBattle({ id: nid(), type: 'putdown', cname: 'Test Throne', regionId: 3, pay: 0, danger: 3, obj: 'assassinate', story: 'finale', comp: ['acolyte', 'graveguard'], reckoning: true }, S.roster.slice(0, 4).map(s => s.id));
  const B = S.battle; const foes = B.units.filter(u => u.kind === 'foe' && !u.prop);
  const revs = foes.filter(u => u.ekey === 'revenant').length, guards = foes.filter(u => u.revguard).length;
  const out = { revs, foes: foes.length, cap: MAXFOES, guards, comp: foes.length - revs - guards, budget: B.pbudget, grid: !!document.getElementById('grid') };
  return out;
});
if (finale.revs !== 5) fail('reckoning did not field every risen grave: ' + JSON.stringify(finale));
if (finale.foes > finale.cap) fail('reckoning exceeded MAXFOES: ' + JSON.stringify(finale));
if (!finale.guards) fail('reckoning fielded no retinue at all: ' + JSON.stringify(finale));

const unexpected = errors.filter(e => !e.includes('Failed to load resource'));
if (unexpected.length) fail('unexpected page errors: ' + JSON.stringify(unexpected, null, 1));
console.log('PASS — pressure bar · courier re-post on retreat · swallow-cull exemption · heir re-post + synchronous win · sword cap said twice · reckoning fields all ' + finale.revs + ' revenants + ' + finale.guards + ' retinue beside a ' + finale.comp + '-body comp (' + finale.foes + '/' + finale.cap + ', budget ' + finale.budget + ')');
await browser.close();
