// v0.70 regressions: one assertion per dead end or engine bug that this build closed, each driven through the same
// globals a click reaches. If any of these ever fails again, a player can get stuck (or silently cheated) again.
const { chromium } = await import(process.env.PW_MODULE || 'playwright');
const BASE = process.env.GB_URL || 'http://localhost:8931/';
const browser = await chromium.launch(process.env.PW_CHROMIUM ? { executablePath: process.env.PW_CHROMIUM } : {});
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
const errors = []; page.on('pageerror', e => errors.push(e.message));
page.on('dialog', d => d.accept());
const results = []; let failed = 0;
const check = (name, ok, detail) => { results.push((ok ? 'ok   ' : 'FAIL ') + name + (ok ? '' : ' — ' + JSON.stringify(detail))); if (!ok) failed++; };
const fresh = async (seed) => { await page.goto(BASE, { waitUntil: 'load' }); await page.waitForTimeout(250);
  await page.evaluate((sd) => { localStorage.clear(); G.newGame({ seed: sd }); activeModal = null; modalQ.length = 0; battleMs = () => 0; render(); }, seed || 'regress'); };
// kill the whole deployed squad the way the field would, and let the battle end itself
const wipe = () => page.evaluate(() => { const B = S.battle; for (const u of B.units.filter(z => z.kind === 'pc' && z.hp > 0)) { u.hp = 0; applyDeath(B, u); if (!S.battle) break; } activeModal = null; modalQ.length = 0; modalHold = 0; render(); });

// 1. the same seed draws the same realm, the same company, the same first week of work
await fresh('same-seed');
const sig = () => page.evaluate(() => JSON.stringify([S.roster.map(s => [s.name, s.cls, s.maxhp, s.weapon]), S.hirePool.map(s => s.name), S.contracts.map(c => [c.type, c.q, c.r, c.pay]),
  Object.values(S.hexes).filter(h => h.prov === 0).map(h => h.t + (h.blighted ? '!' : '')).join(''), S.omens, S.cname, S.graves[0].name]));
const a = await sig(); await fresh('same-seed'); const b = await sig(); await fresh('other-seed'); const c = await sig();
check('seed: identical seeds give identical runs', a === b, { a: a.slice(0, 80), b: b.slice(0, 80) });
check('seed: different seeds differ', a !== c);

// 2. a squad wiped away from any town must not strand the company
await fresh('wipe');
const w = await page.evaluate(() => { const con = S.contracts.find(x => x.q !== S.caravan.q || x.r !== S.caravan.r); S.caravan = { q: con.q, r: con.r }; startBattle(con, S.roster.map(s => s.id)); return atSettlement(); });
await wipe();
const w2 = await page.evaluate(() => ({ battle: !!S.battle, roster: S.roster.length, setl: atSettlement(), over: S.over, hires: S.hirePool.length, canHire: S.hirePool.some(h => S.coin >= hireCost(h)) }));
check('wipe on the road: the wagons reach a settlement', w === null && !w2.battle && w2.roster === 0 && (w2.over || (w2.setl !== null && w2.hires > 0 && w2.canHire)), w2);

// 3. losing the courier does not delete the next act; and a record stranded by an older build heals on load
await fresh('courier');
await page.evaluate(() => { S.story.stage = 3; postCourierContract(); const con = S.contracts.find(x => x.story === 'courier'); S.roster.push(makeSoldier('fighter'), makeSoldier('fighter')); startBattle(con, S.roster.slice(0, 2).map(s => s.id)); });
await wipe();
const c1 = await page.evaluate(() => ({ stage: S.story.stage, posted: S.contracts.filter(x => x.story === 'courier').length }));
check('story: a lost courier fight leaves the contract on the map', c1.stage === 4 && c1.posted === 1, c1);
await page.evaluate(() => { S.contracts = S.contracts.filter(x => !x.story); S.battle = null; G.save(); });
await page.reload({ waitUntil: 'load' }); await page.waitForTimeout(250);
const c2 = await page.evaluate(() => ({ stage: S.story.stage, posted: S.contracts.filter(x => x.story === 'courier').length }));
check('story: a stage-4 record with no courier contract re-posts it on load', c2.stage === 4 && c2.posted === 1, c2);
const c3 = await page.evaluate(() => { TCONT(); activeModal = null; modalQ.length = 0; S.regions.forEach(r => { r.swallowed = true; r.pressure = 100; r.salvage = 6; }); S.regions[1].swallowed = false; genContracts(); return S.contracts.filter(x => x.story === 'courier').length; });
check('story: the Swallowing does not cull a story contract', c3 === 1, c3);

// 4. standing menhirs do not hold a field; a slain leader ends it too
await fresh('menhir');
const m1 = await page.evaluate(() => { const con = { id: nid(), type: 'patrol', regionId: 1, pay: 10, danger: 1, obj: 'slay', layout: 'menhir', expires: 99, q: S.caravan.q, r: S.caravan.r };
  startBattle(con, S.roster.map(s => s.id)); activeModal = null; modalQ.length = 0; const B = S.battle; const stones = B.units.filter(u => u.ekey === 'menhir').length;
  for (const f of B.units.filter(u => u.kind === 'foe' && !u.prop)) { f.hp = 0; applyDeath(B, f); if (!S.battle) break; } return { stones, over: !S.battle, outcome: B.outcome }; });
check('menhir field: killing every foe wins with the stones still standing', m1.stones > 0 && m1.over && m1.outcome === 'victory', m1);

// 5. the Retinue Step runs when the turn ends by itself
await fresh('retinue');
const r1 = await page.evaluate(() => { const s = S.roster[0]; s.level = 6; s.retinue = [makeSword()];
  const con = { id: nid(), type: 'patrol', regionId: 1, pay: 10, danger: 1, obj: 'slay', layout: 'fields', expires: 99, q: S.caravan.q, r: S.caravan.r };
  startBattle(con, [s.id]); activeModal = null; modalQ.length = 0; const B = S.battle; let ran = 0; const real = swordAct; swordAct = function (B2, u) { ran++; return real(B2, u); };
  const u = B.units.find(z => z.kind === 'pc' && !z.sword); u.acted = true; u.mp = 0; u.strikes = 9; afterPcAct(u); swordAct = real; return { ran, phase: B.phase, swords: B.units.filter(z => z.sword).length }; });
check('retinue: sworn swords act when the turn auto-ends', r1.swords === 1 && r1.ran === 1, r1);

// 6. releasing an oath-holder files no buy-back stub
await fresh('oath');
const o1 = await page.evaluate(() => { const s = S.roster[1]; s.oath = { to: 'folk', state: 'kept', strain: 3, receipts: ['x'] }; oathCrisisModal(s);
  activeModal.btns.find(x => /^Release/.test(x.label)).fn(); return { inRoster: S.roster.includes(s), deserters: S.deserters.length }; });
check('oath release: no deserter stub is left behind', !o1.inRoster && o1.deserters === 0, o1);

// 7. an interception cannot be walked away from for free
await fresh('ambush');
const a1 = await page.evaluate(() => { const ag = { id: nid(), kind: 'brigands', q: S.caravan.q, r: S.caravan.r, str: 8 }; S.agents.push(ag); const coin = S.coin, prov = S.prov;
  interceptEncounter(ag, ''); const first = activeModal.btns.map(x => x.label); activeModal.btns[0].fn();                 // "Stand and fight" → the muster
  const muster = activeModal.btns.map(x => x.label); const flee = activeModal.btns.find(x => !/^March/.test(x.label)); flee.fn();
  return { first, muster, cost: (coin - S.coin) + (prov - S.prov), cool: ag.cool > S.day }; });
check('ambush: the muster offers no free "Not yet"', !a1.muster.includes('Not yet') && a1.cost > 0 && a1.cool, a1);

// 8. a step can be undone only while it taught the player nothing
await fresh('undo');
const u1 = await page.evaluate(() => { const con = { id: nid(), type: 'patrol', regionId: 1, pay: 10, danger: 1, obj: 'slay', layout: 'fields', expires: 99, q: S.caravan.q, r: S.caravan.r };
  startBattle(con, S.roster.map(s => s.id)); activeModal = null; modalQ.length = 0; const B = S.battle;
  for (const f of B.units.filter(z => z.kind === 'foe')) { f.x = 0; f.y = 0; } const far = B.units.find(z => z.kind === 'foe' && !z.prop);
  const u = B.units.find(z => z.uid === B.sel), x0 = u.x, y0 = u.y, mp0 = u.mp; const opt = reachCosts(B, u, u.mp).sort((p, q) => p.cost - q.cost)[0];
  TILE(opt.x, opt.y); const moved = (u.x !== x0 || u.y !== y0), offered = !!B._undo; UNDO(); const back = u.x === x0 && u.y === y0 && u.mp === mp0 && !u.moved;
  // now a step that brings an enemy into view must NOT be undoable
  const o2 = reachCosts(B, u, u.mp).sort((p, q) => p.cost - q.cost)[0]; far.x = o2.x + 2 < GW ? o2.x + 2 : o2.x - 2; far.y = o2.y; B.seen = {}; const vis = computeVis(B);
  const seenBefore = vis.has(far.x + ',' + far.y); TILE(o2.x, o2.y);
  return { moved, offered, back, seenBefore, undoAfterReveal: !!B._undo }; });
check('undo: a blind step can be taken back exactly', u1.moved && u1.offered && u1.back, u1);
check('undo: not offered once the step changed what is known', u1.seenBefore || !u1.undoAfterReveal, u1);

// 9. one kill, one payout: an ability kill feeds Reaper and the battle tally like any other
await fresh('credit');
const k1 = await page.evaluate(() => { const con = { id: nid(), type: 'patrol', regionId: 1, pay: 10, danger: 1, obj: 'slay', layout: 'fields', expires: 99, q: S.caravan.q, r: S.caravan.r };
  startBattle(con, S.roster.map(s => s.id)); activeModal = null; modalQ.length = 0; const B = S.battle; const u = B.units.find(z => z.kind === 'pc'); u.feats.push('reaper');
  const fs = B.units.filter(z => z.kind === 'foe' && !z.prop); const f = fs[0]; f.x = u.x + 1 < GW ? u.x + 1 : u.x - 1; f.y = u.y; f.hp = 1; for (const o of fs.slice(1)) { o.x = 0; o.y = 0; }
  const kills0 = soldierById(u.ref).kills; execAbility(B, u, { k: 'bash' }, f); return { reaper: u.reaper, bk: u.bkills, kills: soldierById(u.ref) ? soldierById(u.ref).kills - kills0 : -1, dead: f.hp <= 0 }; });
check('creditKill: a Shield-Bash kill feeds Reaper, the tally and the ledger', k1.dead && k1.reaper === 1 && k1.bk === 1 && k1.kills === 1, k1);

// 10. the muster roll does not run dry
await fresh('names');
const n1 = await page.evaluate(() => { for (let i = 0; i < 120; i++) refreshHirePool(); const all = S.roster.concat(S.hirePool).map(s => s.name); return { dup: new Set(all).size !== all.length, numbered: all.filter(n => / II$/.test(n)).length, used: S.usedNames.length }; });
check('names: 120 weeks of hiring lines burn no names', !n1.dup && n1.numbered === 0 && n1.used < 12, n1);

// 11. loot goes to the wagons, and what a soldier puts down goes back in
await fresh('wagons');
const l1 = await page.evaluate(() => { const s = S.roster[0], old = s.weapon; const it = stashAdd({ k: 'w', key: 'longsword', mod: 0, aff: { uq: 'widowstithe' } }); equipWeapon(s, stashTake(it.id));
  return { now: wpnName(s.weapon, s.wAff), back: S.stash.some(i => i.k === 'w' && i.key === old), dmg: wOf({ weapon: s.weapon, wAff: s.wAff, feats: [] }).lo }; });
check('wagons: equipping returns the old weapon; a unique answers to its name', l1.now === 'Widow’s Tithe' && l1.back && l1.dmg === 5, l1);

check('no uncaught page errors', errors.length === 0, errors.slice(0, 3));
console.log(results.join('\n'));
console.log(failed ? `\n${failed} regression(s) FAILED` : '\nPASS — ' + results.length + ' checks');
await browser.close();
process.exit(failed ? 1 : 0);
