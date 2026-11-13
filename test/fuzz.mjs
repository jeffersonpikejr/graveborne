// Fuzz harness: a headless bot plays whole campaigns — strategy layer and battles — making seeded random choices,
// and fails on anything a player would experience as "the game broke": an uncaught error, an enemy phase that
// never hands the turn back, a modal that cannot be dismissed, a save that will not round-trip, or a DEAD END
// (a company that is neither over nor able to do anything about its situation).
//
//   node test/fuzz.mjs                       # 6 campaigns of 16 weeks
//   RUNS=20 WEEKS=30 SEED=7 node test/fuzz.mjs
//   STORY=1 node test/fuzz.mjs               # bias the bot toward the authored spine (palace → courier → heirs → finale)
//
// Nothing here ships in index.html: the bot is injected by this script and drives the same globals a click does.
const { chromium } = await import(process.env.PW_MODULE || 'playwright');
const BASE = process.env.GB_URL || 'http://localhost:8931/';
const RUNS = Number(process.env.RUNS || 6), WEEKS = Number(process.env.WEEKS || 16), SEED0 = Number(process.env.SEED || 1);
const STORY = !!process.env.STORY, VERBOSE = !!process.env.VERBOSE;

const browser = await chromium.launch(process.env.PW_CHROMIUM ? { executablePath: process.env.PW_CHROMIUM } : {});
const failures = [];
let totals = { battles: 0, weeks: 0, victories: 0, defeats: 0, retreats: 0, events: 0, over: 0, storyMax: 0 };

// ---- the in-page bot ----
const BOT = (seed, story) => {
  let s = seed >>> 0;
  const rnd = () => { s |= 0; s = s + 0x6D2B79F5 | 0; let t = Math.imul(s ^ s >>> 15, 1 | s); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  const pick = a => a[Math.floor(rnd() * a.length)];
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const st = { battles: 0, victories: 0, defeats: 0, retreats: 0, events: 0, notes: [], lastTitle: '' };
  const patron = (seed % 5) !== 0;
  // pacing off: the enemy phase is a timer chain; collapse every beat to 0 so a campaign fits in seconds
  window.battleMs = () => 0;
  window.pauseNextTurn = function () { const B = S.battle; if (!B) return; clearTimeout(B._ntT); B._ntT = setTimeout(() => { if (S.battle && !S.battle.over) nextTurn(); }, 0); };
  // drawing 500 tiles after every bot click is most of a campaign's wall-clock. The harness draws the real field one
  // render in eight (enough to catch a renderer that throws) and a stub the rest of the time; the fog-of-war set the
  // bot reads is computed either way.
  if (!window.__realRenderBattle) { window.__realRenderBattle = window.renderBattle; let rn = 0;
    window.renderBattle = function () { if (++rn % 8 === 0) return window.__realRenderBattle(); const B = S.battle; B._vis = computeVis(B); B._ts = B._ts || 56; return '<div id="battle"></div>'; }; }
  const fail = m => { throw new Error(m); };

  async function dismiss(limit = 60) {
    for (let i = 0; i < limit; i++) {
      const m = document.querySelector('#modal'); if (!m) return true;
      const title = (m.querySelector('h2') || {}).textContent || '';
      st.lastTitle = title;
      const btns = [...m.querySelectorAll('.btns button')];
      if (!btns.length) fail('modal with no buttons: ' + title);
      if (/Muster/.test(title)) {
        // tick available soldiers up to the cap, then march
        const picks = [...m.querySelectorAll('button.pick:not([disabled])')].filter(b => /^☐/.test(b.textContent.trim()) && !/Kit|Horn|Draught|Firepot|Salt/.test(b.textContent));
        const cap = typeof partyCap === 'function' ? partyCap() : 4;
        let n = [...m.querySelectorAll('button.pick')].filter(b => /^☑/.test(b.textContent.trim())).length;
        if (picks.length && n < cap) { picks[0].click(); await sleep(0); continue; }
        if (n === 0) {   // nobody can march — the modal must offer a way out that is not "March"
          const out = btns.filter(b => !b.disabled && !/^March/.test(b.textContent.trim()));
          if (!out.length) fail('muster modal with nobody available and no way out');
          pick(out).click(); await sleep(0); continue;
        }
        btns.find(b => /^March/.test(b.textContent.trim())).click(); await sleep(0); continue;
      }
      const enabled = btns.filter(b => !b.disabled);
      if (!enabled.length) fail('modal with every button disabled: ' + title);
      let b = pick(enabled);
      if (story && /Palace|Princess|Doors|Throne|Barrow|Courier|Satchel|Ledger|ground/i.test(title)) b = enabled[0];   // take the spine's first door
      const before = m.innerHTML;
      b.click(); await sleep(0);
      const m2 = document.querySelector('#modal');
      if (m2 && m2.innerHTML === before && enabled.length === 1) fail('modal button does nothing: ' + title + ' / ' + b.textContent.slice(0, 60));
    }
    fail('modal chain did not end after ' + limit + ' dismissals (last: ' + st.lastTitle + ')');
  }

  async function waitPlayer(ms = 12000) {
    const t0 = Date.now();
    while (S.battle && !S.battle.over && S.battle.phase !== 'player') {
      if (document.querySelector('#modal')) await dismiss();
      if (Date.now() - t0 > ms) fail('enemy phase never returned the turn (round ' + S.battle.round + ', qi ' + S.battle.qi + '/' + S.battle.queue.length + ')');
      await sleep(4);
    }
  }

  async function playBattle() {
    st.battles++;
    const B0 = S.battle; let guard = 0;
    // The bot is a poor tactician, and a campaign that dies in week 2 exercises nothing. Most fights it is handed a
    // thumb on the scale (foes at one hit point, or a third of their health) so runs reach the late systems; the rest it fights straight.
    const thumb = rnd();
    if (thumb < 0.8) for (const f of B0.units) if (f.kind === 'foe' && !f.prop) { f.hp = thumb < 0.55 ? 1 : Math.max(1, Math.ceil(f.hp / 3)); }
    while (S.battle && !S.battle.over) {
      if (document.querySelector('#modal')) { await dismiss(); continue; }
      const B = S.battle; if (!B || B.over) break;
      if (B.phase !== 'player') { await waitPlayer(); continue; }
      if (++guard > 400) fail('battle did not end after 400 player phases');
      if (B.round > 45 || (B.round > 6 && rnd() < 0.02)) {            // sometimes the bot runs
        RETREAT(); await sleep(0);
        const m = document.querySelector('#modal');
        if (m) { [...m.querySelectorAll('.btns button')].find(b => /^Retreat/.test(b.textContent.trim())).click(); await sleep(0); }
        continue;
      }
      const pcs = B.units.filter(u => u.kind === 'pc' && !u.sword && u.hp > 0 && !u.fled);
      for (const u of pcs) {
        let acts = 0;
        while (S.battle === B && !B.over && B.phase === 'player' && u.hp > 0 && pcTurnLeft(u) && acts++ < 6) {
          if (document.querySelector('#modal')) { await dismiss(); continue; }
          SELECT(u.uid);
          if (B.sel !== u.uid) break;
          // an ability, sometimes
          const abs = unitAbilities(u);
          if (!u.acted && !(u.strikes > 0) && abs.length && rnd() < 0.35) {
            const ab = pick(abs);
            ACTPICK(ab.k); await sleep(0);
            if (S.battle !== B || B.over) break;
            if (B.aim) {
              const ts = B.units.filter(t => abilityValidTarget(B, u, ab, t));
              if (ts.length) { const t = pick(ts); TILE(t.x, t.y); await sleep(0); continue; }
              ACTMENU(1);
            } else continue;
          }
          const vis = B._vis || new Set();
          const tg = (!u.acted && (u.strikes || 0) < maxStrikes(u)) ? attackTargets(B, u).filter(t => t.kind !== 'foe' || vis.has(t.x + ',' + t.y)) : [];
          const live = tg.filter(t => !t.prop || B.obj === 'burn');          // masonry is not a target unless burning it is the job
          if (live.length) { const t = live.sort((a, b) => a.hp - b.hp)[0]; TILE(t.x, t.y); await sleep(0); continue; }
          // otherwise close on the objective / nearest foe
          const mp = u.mp || 0;
          // walk first (keeps the action for a strike on arrival); dash only when the enemy is still far off
          let opts = mp >= 1 ? reachCosts(B, u, mp) : [];
          const nearest = B.units.filter(f => f.kind === 'foe' && f.hp > 0 && !f.fled).reduce((m, f) => Math.min(m, distC(f, u)), 99);
          if ((!opts.length || nearest > mp + 3) && !u.acted && !(u.strikes > 0)) opts = reachCosts(B, u, mp + moveBudget(u));
          if (!opts.length) break;
          let goal = null;
          if (B.obj === 'capture' && B.objTile) goal = B.objTile;
          else { const foes = B.units.filter(f => f.kind === 'foe' && f.hp > 0 && !f.fled && (!f.prop || B.obj === 'burn')); goal = foes.sort((a, b) => distC(a, u) - distC(b, u))[0] || null; }
          if (!goal) break;
          const pf = pathField(B, goal.x, goal.y);
          const d = o => { const v = pf[o.x + ',' + o.y]; return v === undefined ? 9999 : v; };
          opts.sort((a, b) => (d(a) - d(b)) || (rnd() - 0.5));
          const here = d(u), best = opts[0];
          if (d(best) >= here && rnd() < 0.7) break;
          const px = u.x, py = u.y;
          TILE(best.x, best.y); await sleep(0);
          if (S.battle === B && !B.over && u.x === px && u.y === py && B.phase === 'player' && !document.querySelector('#modal')) break;   // the click did nothing
        }
        if (S.battle !== B || B.over) break;
      }
      if (S.battle === B && !B.over && B.phase === 'player' && !document.querySelector('#modal')) { ENDT(); await sleep(0); }
    }
    const out = B0.outcome; if (out === 'victory') st.victories++; else if (out === 'defeat') st.defeats++; else if (out === 'retreat') st.retreats++;
    st.notes.push(`${B0.cname || B0.type}/${B0.obj} ☠${B0.danger} ${B0.mapTheme} squad ${B0.units.filter(u => u.kind === 'pc').length} thumb ${thumb.toFixed(2)} → ${out} r${B0.round}${out !== 'victory' ? ' | ' + B0.log.slice(0, 4).reverse().join(' / ') : ''}`);
    await dismiss();
  }

  function invariants(where) {
    if (!S) fail('no state @' + where);
    for (const k of ['coin', 'prov', 'renown', 'week', 'day']) if (typeof S[k] !== 'number' || Number.isNaN(S[k])) fail(k + ' is ' + S[k] + ' @' + where);
    if (S.coin < 0 || S.prov < 0) fail('negative ledger: coin ' + S.coin + ' prov ' + S.prov + ' @' + where);
    const ids = new Set();
    for (const p of S.roster) {
      if (!p || typeof p.id !== 'number') fail('malformed roster entry @' + where + ': ' + JSON.stringify(p).slice(0, 120));
      if (ids.has(p.id)) fail('duplicate soldier id ' + p.id + ' @' + where); ids.add(p.id);
      if (!Array.isArray(p.feats) || !Array.isArray(p.bonds) || !p.face) fail('soldier missing fields: ' + p.name + ' @' + where);
      if (!WEAPONS[p.weapon]) fail(p.name + ' holds unknown weapon ' + p.weapon + ' @' + where);
      if (!(p.maxhp > 0) || Number.isNaN(p.hp) || p.hp > p.maxhp) fail(p.name + ' hp ' + p.hp + '/' + p.maxhp + ' @' + where);
      if (!p.alive) fail('dead soldier on the roster: ' + p.name + ' @' + where);
      if (!S.battle && p.guest) fail('guest left on the roster outside battle: ' + p.name + ' @' + where);
    }
    for (const c of S.contracts) { if (!S.regions[c.regionId]) fail('contract in no region @' + where); if (!hex(c.q, c.r)) fail('contract off the sheet @' + where); if (!CONTRACT_TYPES[c.type]) fail('contract of unknown type @' + where); }
    for (const a of S.agents) if (!hex(a.q, a.r)) fail('agent off the sheet: ' + a.kind + ' @' + where);
    for (const d of (S.deserters || [])) if (typeof d.id !== 'number' || !Array.isArray(d.feats)) fail('malformed deserter record: ' + JSON.stringify(d).slice(0, 100) + ' @' + where);
    if (!hex(S.caravan.q, S.caravan.r)) fail('caravan off the sheet @' + where);
    const names = S.roster.concat(S.hirePool).map(p => p.name);
    if (new Set(names).size !== names.length) fail('duplicate names on the muster roll: ' + names.join(', ') + ' @' + where);
    // the record must survive its own save
    if (!S.battle) { const raw = JSON.stringify({ S, uid: 1 }); JSON.parse(raw); }
  }

  // can the player do ANYTHING that changes their situation? (the definition of not-a-dead-end)
  function hasWayForward() {
    if (S.over || S.battle) return true;
    if (document.querySelector('#modal')) return true;
    const fielders = S.roster.filter(p => !((p.benchedUntil || 0) >= S.week) && !(p.stationedProv !== undefined && p.stationedProv !== null));
    if (fielders.length) return true;
    if (S.roster.length) return true;                                   // benched/stationed swords come back or can be recalled
    if (atSettlement() !== null && S.hirePool.some(h => S.coin >= hireCost(h))) return true;
    if (atSettlement() !== null && !S.hirePool.length && S.coin >= hireCost({ cost: 20 })) return true;   // resting a week refills the hiring line
    // an empty company off the road needs SOME lever: a travel button that works, or a way to hire here
    const travel = [...document.querySelectorAll('button')].some(b => /Travel here|ride out/.test(b.textContent) && !b.disabled);
    return travel;
  }

  async function strategicStep() {
    await dismiss();
    if (S.over) return 'over';
    if (S.battle) { await playBattle(); return 'battle'; }
    if (typeof SNK !== 'undefined' && SNK) { if (rnd() < 0.85) sneakSuccess(); else sneakCaught(); await sleep(0); await dismiss(); return 'sneak'; }
    invariants('strategy');
    // A PATRON: four runs in five, somebody is quietly paying this company's bills and patching it up, so the campaign
    // lives long enough to reach doctrines, named heads, unfinished business and the far provinces. The fifth run
    // gets nothing, and exercises ruin.
    if (patron) { if (S.coin < 160) S.coin += 140; if (S.prov < 12) S.prov += 12; for (const p of S.roster) p.hp = p.maxhp; }
    if (!hasWayForward()) fail('DEAD END: week ' + S.week + ', roster ' + S.roster.length + ', coin ' + S.coin + ', at settlement ' + atSettlement() + ', story ' + (S.story && S.story.stage));
    const setl = atSettlement();
    // upkeep the way a sane player would
    if (setl !== null) {
      if (S.prov < S.roster.length * 2 && S.coin >= provCost() + 10) { BUYPROV(); return 'prov'; }
      if (S.roster.length < 4 && S.hirePool.length) { const i = S.hirePool.findIndex(h => S.coin >= hireCost(h)); if (i >= 0) { HIRE(i); return 'hire'; } }
      if (rnd() < 0.25 && S.roster.length < 7 && S.hirePool.length && S.coin > 90) { HIRE(0); return 'hire'; }
    }
    // story buttons
    const sb = [...document.querySelectorAll('button.storybtn:not([disabled])')];
    if (sb.length && rnd() < (story ? 0.9 : 0.4)) { pick(sb).click(); await sleep(0); return 'story'; }
    // any other enabled button in the camp panel, occasionally (commissions, shrine, outfitting, doctrines…)
    if (rnd() < 0.22) {
      const side = [...document.querySelectorAll('#sideCol button:not([disabled]), #rosterCol button:not([disabled])')].filter(b => !/Rest a week|New Company|Hire|Provisions/.test(b.textContent));
      if (side.length) { pick(side).click(); await sleep(0); return 'misc'; }
    }
    const r = rnd();
    if (S.roster.length && S.contracts.length && r < 0.62) {
      let cs = S.contracts.slice();
      if (story) { const sc = cs.filter(c => c.story); if (sc.length) cs = sc; else if (S.story && S.story.stage === 2) { const pj = cs.filter(c => c.type === 'purge' || c.type === 'delve'); if (pj.length) cs = pj; } }
      const c = pick(cs); TAKE(c.id); await sleep(0); return 'take';
    }
    if (story && S.roster.length && S.story && [1, 3, 6, 9].includes(S.story.stage) && setl !== 3) { TRAVEL(realmQ(3), realmR(3)); await sleep(0); return 'travel-gate'; }
    if (story && S.story && S.story.stage === 5 && S.story.meetHex && S.week === S.story.meetWeek) { TRAVEL(S.story.meetHex.q, S.story.meetHex.r); await sleep(0); return 'travel-barrow'; }
    if (S.roster.length && r < 0.74) {                                 // wander to a town
      const towns = REGION_DEFS.map((d, i) => i).filter(i => provKnown(REGION_DEFS[i].prov));
      const t = pick(towns); TRAVEL(realmQ(t), realmR(t)); await sleep(0); return 'travel';
    }
    WEEK(); await sleep(0); return 'rest';
  }

  window.__bot = { st, strategicStep, dismiss, invariants, rnd };
};

for (let run = 0; run < RUNS; run++) {
  const seed = SEED0 + run * 7919;
  const page = await browser.newPage({ viewport: run % 2 ? { width: 420, height: 800 } : { width: 1280, height: 800 } });
  const errors = [];
  page.on('pageerror', e => errors.push('pageerror: ' + e.message + (e.stack ? ' @ ' + String(e.stack).split('\n').slice(1, 3).join(' | ') : '')));
  page.on('dialog', d => d.accept());
  const label = `run ${run} seed ${seed}`;
  try {
    await page.goto(BASE, { waitUntil: 'load' });
    await page.waitForTimeout(250);
    await page.evaluate((sd) => { localStorage.clear(); if (G.newGame.length >= 1) G.newGame({ seed: sd, origin: 'random' }); else G.newGame(); }, seed);
    await page.evaluate(`(${BOT.toString()})(${seed}, ${STORY})`);
    let steps = 0, lastWeek = 0, sameWeek = 0;
    const acc = { battles: 0, victories: 0, defeats: 0, retreats: 0, notes: [] };   // the bot is re-injected after every reload; its tallies are folded in here
    const fold = async () => { const t = await page.evaluate(() => window.__bot ? window.__bot.st : null); if (t) { acc.battles += t.battles; acc.victories += t.victories; acc.defeats += t.defeats; acc.retreats += t.retreats; acc.notes.push(...t.notes); } };
    for (;;) {
      const r = await page.evaluate(async () => {
        const kind = await window.__bot.strategicStep();
        return { kind, week: S.week, over: S.over, stage: S.story ? S.story.stage : -1, toast: (document.querySelector('.errtoast') || {}).textContent || null };
      });
      steps++;
      if (errors.length) throw new Error(errors[0]);
      if (r.toast) throw new Error('error banner: ' + r.toast);
      if (VERBOSE) console.log(label, steps, r.kind, 'wk', r.week, 'stage', r.stage);
      totals.storyMax = Math.max(totals.storyMax, r.stage);
      if (r.week === lastWeek) { if (++sameWeek > 260) throw new Error('STALL: 260 bot steps without the week advancing (week ' + r.week + ', last action ' + r.kind + ')'); } else { lastWeek = r.week; sameWeek = 0; }
      if (r.over) { totals.over++; break; }
      if (r.week > WEEKS || steps > 2500) break;
      // every so often: reload mid-campaign (and mid-battle) and make sure the record comes back
      if (steps % 37 === 0) {
        await fold();
        const before = await page.evaluate(() => ({ week: S.week, roster: S.roster.length, battle: !!S.battle }));
        await page.evaluate(() => { if (!S.battle) G.save(); window.dispatchEvent(new Event('pagehide')); });
        await page.reload({ waitUntil: 'load' }); await page.waitForTimeout(200);
        const cont = await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find(x => /^Continue/.test(x.textContent.trim())); if (b) b.click(); return !!S; });
        if (!cont) throw new Error('state missing after reload');
        const after = await page.evaluate(() => ({ week: S.week, roster: S.roster.length, battle: !!S.battle }));
        if (after.week !== before.week || after.battle !== before.battle) throw new Error('reload changed the record: ' + JSON.stringify(before) + ' → ' + JSON.stringify(after));
        await page.evaluate(`(${BOT.toString()})(${seed + steps * 5}, ${STORY})`);
      }
    }
    await fold(); const st = acc;
    totals.battles += st.battles; totals.victories += st.victories; totals.defeats += st.defeats; totals.retreats += st.retreats; totals.weeks += lastWeek;
    if (errors.length) throw new Error(errors[0]);
    console.log(`ok   ${label}: ${steps} steps, week ${lastWeek}, ${st.battles} battles (${st.victories}W/${st.defeats}L/${st.retreats}R)`);
    if (VERBOSE) for (const n of st.notes) console.log('     · ' + n);
  } catch (e) {
    const ctx = await page.evaluate(() => { try { return { week: S && S.week, stage: S && S.story && S.story.stage, battle: !!(S && S.battle), modal: (document.querySelector('#modal h2') || {}).textContent || null, last: window.__bot && window.__bot.st.lastTitle }; } catch (x) { return { err: String(x) }; } }).catch(() => ({}));
    const msg = String(e.message || e).split('\n')[0];
    failures.push({ label, msg, ctx });
    console.log(`FAIL ${label}: ${msg} ${JSON.stringify(ctx)}`);
  }
  await page.close();
}
await browser.close();
console.log(`\n${RUNS - failures.length}/${RUNS} campaigns clean · ${totals.battles} battles (${totals.victories}W/${totals.defeats}L/${totals.retreats}R) · ${totals.weeks} weeks · ${totals.over} ended · deepest story stage ${totals.storyMax}`);
if (failures.length) { const uniq = {}; for (const f of failures) (uniq[f.msg.replace(/\d+/g, '#')] = uniq[f.msg.replace(/\d+/g, '#')] || []).push(f.label); console.log('\nDistinct failures:'); for (const k in uniq) console.log(' · ' + k + '  ×' + uniq[k].length + '  (' + uniq[k][0] + ')'); process.exit(1); }
