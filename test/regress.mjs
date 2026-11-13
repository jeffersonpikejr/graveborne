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

// ---- found by an independent review of the v0.70 diff, each reproduced before it was fixed ----
// 12. a lost story contract goes to ground for a week: no re-fighting it at once for XP and a fresh cache
await fresh('farm');
await page.evaluate(() => { S.story.stage = 3; postCourierContract(); const con = S.contracts.find(x => x.story === 'courier'); S.caravan = { q: con.q, r: con.r }; startBattle(con, S.roster.map(s => s.id)); activeModal = null; modalQ.length = 0; S.battle.round = 2; endBattle('retreat'); activeModal = null; modalQ.length = 0; modalHold = 0; });
const f1 = await page.evaluate(() => { const con = S.contracts.find(x => x.story === 'courier'); TAKE(con.id); const blocked = !S.battle && !activeModal; S.week++; TAKE(con.id); const open = !!activeModal; S.roster.slice(0, partyCap()).forEach(x => TOG(x.id)); activeModal.btns[0].fn(); const B = S.battle;
  return { blocked, open, retry: B && B.retry, caches: B ? B.tiles.filter(t => t.cache).length : -1 }; });
check('story retry: gone to ground until the week turns, and the field is picked clean', f1.blocked && f1.open && f1.retry === true && f1.caches === 0, f1);

// 13. sellable wagons keep an empty banner alive
await fresh('stashover');
const g1 = await page.evaluate(() => { S.roster = []; S.coin = 8; stashAdd({ k: 'w', key: 'longsword', mod: 0, aff: { uq: 'widowstithe' } }); checkGameOver(); const alive = !S.over; S.stash = []; checkGameOver(); return { alive, overWithout: S.over }; });
check('game over: what is in the wagons counts toward the next hire', g1.alive && g1.overWithout, g1);

// 14. a charm's hit points are not banked
await fresh('ring');
const h1 = await page.evaluate(() => { const s = S.roster[0]; s.trinket = 'weddingiron'; s.hp = 5; const con = { id: nid(), type: 'patrol', regionId: 1, pay: 10, danger: 1, obj: 'slay', layout: 'fields', expires: 99, q: S.caravan.q, r: S.caravan.r };
  startBattle(con, [s.id]); activeModal = null; modalQ.length = 0; const u = S.battle.units.find(z => z.kind === 'pc'); const inField = u.hp; S.battle.round = 2; endBattle('retreat'); return { inField, after: s.hp }; });
check('Wedding-Iron Ring: +3 on the field, nothing carried home', h1.inField === 8 && h1.after === 5, h1);

// 15. the first-strike bonus is spent by an ability that rolls to hit
await fresh('opener');
const p1 = await page.evaluate(() => { S.doctrines = ['firstblood']; const con = { id: nid(), type: 'patrol', regionId: 1, pay: 10, danger: 1, obj: 'slay', layout: 'fields', expires: 99, q: S.caravan.q, r: S.caravan.r };
  startBattle(con, S.roster.map(s => s.id)); activeModal = null; modalQ.length = 0; const B = S.battle, u = B.units.find(z => z.kind === 'pc'); u.weapon = 'axe';
  const fs = B.units.filter(z => z.kind === 'foe' && !z.prop), f = fs[0]; f.x = u.x + 1 < GW ? u.x + 1 : u.x - 1; f.y = u.y; f.hp = 60; f.maxhp = 60; for (const o of fs.slice(1)) { o.x = 0; o.y = 0; }
  const before = hitChance(B, u, f); execAbility(B, u, { k: 'cleave' }, f); return { before, after: hitChance(B, u, f) }; });
check('First Blood: used up by a Cleave, not kept all battle', p1.before - p1.after === 15, p1);

// 16. a nemesis that took a trophy still drops the steel it started with
await fresh('trophy');
const t1 = await page.evaluate(() => { S.week = 6; let n = null; for (let i = 0; i < 40 && !n; i++) n = nemesisSpawn(); n.wpn = 'longsword'; n.aff = { uq: 'widowstithe' }; n.trophy = { key: 'armingsword', aff: null, name: 'Morwen’s Arming Sword', from: 'Morwen' }; nemesisPost(n);
  const con = S.contracts.find(x => x.nemId === n.id); startBattle(con, S.roster.map(s => s.id)); activeModal = null; modalQ.length = 0; const B = S.battle, lead = B.units.find(z => z.uid === B.leaderUid);
  const wields = wpnName(lead.weapon, lead.wAff); lead.hp = 0; creditKill(B, B.units.find(z => z.kind === 'pc'), lead); activeModal = null; modalQ.length = 0;
  return { wields, over: !S.battle, hasUnique: S.stash.some(i => i.aff && i.aff.uq === 'widowstithe'), hasTrophy: S.stash.some(i => i.name === 'Morwen’s Arming Sword'), state: n.state }; });
check('nemesis: its own named steel drops even when it was swinging a trophy', t1.over && t1.hasUnique && t1.hasTrophy && t1.state === 'dead', t1);

// 17. two weeks turning at once do not send two collectors
await fresh('debt');
const d1 = await page.evaluate(() => { S.debt = { amt: 120, week: 2 }; S.coin = 36; S.week = 2; debtModal(); activeModal.btns.find(x => /Pay what is in the box/.test(x.label)).fn(); debtModal(); return { amt: S.debt && S.debt.amt, due: S.debt && S.debt.week, second: !!activeModal }; });
check('Undercrown debt: a part-payment is not followed by a second demand', d1.amt === 105 && d1.due === 6 && !d1.second, d1);

// 18. backing out of an event fight is not a brigand robbery
await fresh('evflee');
const e1 = await page.evaluate(() => { const coin = S.coin, prov = S.prov; evFight('What Was Under the Field', ['husk', 'husk']); const labels = activeModal.btns.map(x => x.label); activeModal.btns.find(x => !/^March/.test(x.label)).fn(); return { labels, coin: coin - S.coin, prov: prov - S.prov }; });
check('event fight: backing away costs nerve, not a wagon', e1.coin === 0 && e1.prov === 0 && !e1.labels.some(l => /wagon/.test(l)), e1);

// 19. a road modal queued behind an event does not open on top of the event's battle
await fresh('roadq');
const q1 = await page.evaluate(() => { const con = S.contracts.find(x => x.q !== S.caravan.q || x.r !== S.caravan.r); evShow({ t: 'An event', b: '<p>x</p>', o: [{ l: 'Fight', f: () => evFight('Event Fight', ['husk', 'husk']) }] });
  S.caravan = { q: con.q, r: con.r };                                  // an arrival modal queues behind the event, as a multi-week march would do
  queueModal(() => { if (S.battle || S.over || !S.contracts.includes(con)) { closeModal(); return; } showModal('On the ground', '<p>x</p>', [{ label: 'Muster and fight', fn: () => {} }]); activeModal.road = true; });
  activeModal.btns[0].fn(); const cap = partyCap(); [...S.roster].slice(0, cap).forEach(s => TOG(s.id)); activeModal.btns.find(x => /^March/.test(x.label)).fn();
  return { battle: S.battle && S.battle.cname, modal: activeModal ? activeModal.title : null }; });
check('modal queue: marching into an event fight is not interrupted by a queued arrival', q1.battle === 'Event Fight' && q1.modal !== 'On the ground', q1);

// ---- v0.71: the rendered company ----
// 20. every soldier of a sprited class is drawn as her kit's body under her own head; every image actually loads;
//     the Classic setting puts the hand-drawn figures back; the Shade (no sprites yet) falls back on her own
await fresh('sprites');
const sp = await page.evaluate(async () => { const R = S.roster; R[1].level = 5; R[2].weapon = 'spear'; R.push(makeSoldier('shade'));
  const con = { id: nid(), type: 'patrol', regionId: 1, pay: 10, danger: 1, obj: 'slay', layout: 'fields', expires: 99, q: S.caravan.q, r: S.caravan.r };
  startBattle(con, R.slice(0, 5).map(s => s.id)); activeModal = null; modalQ.length = 0; const B = S.battle; for (const t of B.tiles) B.seen[t.x + ',' + t.y] = 1; render();
  const imgs = [...document.querySelectorAll('#grid .unit.pc.sprited img.sp')];
  await Promise.all(imgs.map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; })));
  const shade = B.units.find(u => u.kind === 'pc' && soldierById(u.ref) && soldierById(u.ref).cls === 'shade');
  const out = { sprited: document.querySelectorAll('#grid .unit.pc.sprited').length, broken: imgs.filter(i => !i.naturalWidth).length, imgs: imgs.length,
    shadeSvg: !!document.querySelector(`#grid .unit[data-uid="${shade.uid}"] svg`), vet: imgs.some(i => /_veteran_/.test(i.src)), spear: imgs.some(i => /_spear/.test(i.src)) };
  PREFS.sprites = false; render(); out.classic = document.querySelectorAll('#grid .unit.sprited').length; PREFS.sprites = true; S.battle = null; clearStashedBattle(); return out; });
check('sprites: four sprited classes drawn body+head, all images load, Classic and the Shade fall back to SVG',
  sp.sprited === 4 && sp.imgs === 8 && sp.broken === 0 && sp.shadeSvg && sp.vet && sp.spear && sp.classic === 0, sp);

// 21. v0.72 — the rest of the field is rendered: every file the manifest names exists; a foe with sprites is drawn from its
//     own pool (its tier's looks by the tag in its name, the ♛ from the captain's); every tile lies on painted ground and
//     every image on the field loads; the march map is painted; Classic puts all of it back to the drawn art
await fresh('art72');
const art = await page.evaluate(async () => {
  const out = {};
  const miss = []; for (const n of SPR_MAN.whole) { const r = await fetch(SPR_ROOT + n + '.webp', { method: 'HEAD' }); if (!r.ok) miss.push(n); } out.miss = miss;
  out.mapPainted = /url\(#mp-/.test(document.querySelector('#mapwrap svg').innerHTML);
  const con = { id: nid(), type: 'patrol', regionId: 1, pay: 10, danger: 1, obj: 'slay', layout: 'river', expires: 99, q: S.caravan.q, r: S.caravan.r };
  startBattle(con, S.roster.slice(0, 4).map(s => s.id)); activeModal = null; modalQ.length = 0; const B = S.battle;
  const foes = B.units.filter(u => u.kind === 'foe' && !u.prop);
  const h = foes[0], h2 = foes[1], b = foes[2]; h.ekey = 'husk'; h.name = 'Ironbound Husk'; h2.ekey = 'husk'; h2.name = 'Husk'; b.ekey = 'brigand'; b.name = 'Brigand'; B.leaderUid = b.uid;
  out.tier = /foe_husk_ironbound_/.test(foeSprite(h) || ''); out.base = /foe_husk_\d/.test(foeSprite(h2) || ''); out.captain = /foe_brigand_captain_/.test(foeSprite(b) || '');
  out.none = foeSprite({ ekey: 'nosuchfoe', name: 'X', uid: 1 }) === null;
  for (const t of B.tiles) B.seen[t.x + ',' + t.y] = 1; computeVis = function (B) { const v = new Set(); for (const t of B.tiles) v.add(t.x + ',' + t.y); return v; };
  render();
  const tiles = [...document.querySelectorAll('#grid .tile')]; out.tiles = tiles.length; out.painted = tiles.filter(t => t.classList.contains('gt')).length;
  out.edges = document.querySelectorAll('#grid .ge').length; out.foeSprited = document.querySelectorAll('#grid .unit.sprited:not(.pc)').length;
  const imgs = [...document.querySelectorAll('#grid img')]; await Promise.all(imgs.map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; })));
  out.broken = imgs.filter(i => !i.naturalWidth).map(i => i.src.split('/').pop()).slice(0, 4);
  const bg = getComputedStyle(document.querySelector('#grid .tile.gt')).backgroundImage; out.bg = /ground_[a-z]+\.webp/.test(bg);   // asked of the live grid: a redraw during the await detaches the old tiles
  PREFS.sprites = false; render(); out.classic = document.querySelectorAll('#grid .gt, #grid img.sp, #grid img.ts, #grid .ge').length;
  out.classicMap = /url\(#mp-/.test(hexSvg()); out.classicFace = /<svg/.test(portrait(S.roster[0], 46)); PREFS.sprites = true;
  out.face = /spr-card pt/.test(portrait(S.roster[0], 46)); S.battle = null; clearStashedBattle(); return out; });
check('rendered field: manifest files exist, foes drawn from their own tier/captain pools, painted ground and edges, all images load, painted map, Classic restores the drawn art',
  art.miss.length === 0 && art.mapPainted && art.tier && art.base && art.captain && art.none && art.painted === art.tiles && art.edges > 0 && art.foeSprited >= 3
  && art.broken.length === 0 && art.bg && art.classic === 0 && !art.classicMap && art.classicFace && art.face, art);

check('no uncaught page errors', errors.length === 0, errors.slice(0, 3));
console.log(results.join('\n'));
console.log(failed ? `\n${failed} regression(s) FAILED` : '\nPASS — ' + results.length + ' checks');
await browser.close();
process.exit(failed ? 1 : 0);
