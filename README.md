# GRAVEBORNE — alpha

**▶ Play (desktop or phone): https://jeffersonpikejr.github.io/graveborne/**

Dark-fantasy mercenary squad tactics. **You will fight everyone you fail to protect**: soldiers whose bodies you abandon, sell, or bury in doomed ground come back as revenants carrying their exact builds and unfinished stories.

Single-file game — no build, no backend, saves to your device's localStorage. Play at the link above, or run locally: open `index.html` (or `python3 -m http.server 8931 --directory .` → localhost:8931). Design docs live in the Obsidian vault: `1 - Projects ☑️/Graveborne/` (roadmap v2 is the source of truth).

## How to play
- **Company screen**: take contracts (pay vs. danger vs. region pressure), hire, fit armor, buy provisions, rest to advance the week. The Blight pressure bars are the clock — a region at 100 is swallowed, and its buried graves rise.
- **Battle**: one **Move** + one **Action** per soldier per turn (pips in the top bar). Click gold tiles to move; click red-rimmed enemies to attack (hit % shown); click any other enemy to **scout** its threat range. **Brace** spends your action: −10 to be hit, +2 armor until your next turn. Retreating carries out only the bodies a living soldier stands beside — the rest are the Blight's.
- **Rites**: bury (12c, safe unless the ground is taken), burn (free, permanent, the company watches — resolve cost), or sell to the Conclave (+30c; she *will* be back, improved, and everyone knows what you did).

## v0.52 (2026-07-15) — Subtler Move Tiles & More Vertical Scroll Room
Battle-camera and readability.

**Move/dash tile outlines are much subtler.** The blue (move) and gold (dash) grids were loud enough to wash out the terrain; their outlines are now ~60% more transparent, so they read as a quiet indicator and you can see the ground underneath.

**More vertical scroll room, and the top stops clipping under the HUD.** Zoomed in, the map's top rows could jam under the roster with nowhere to scroll, and zooming with the +/- buttons made it worse. The +/- zoom now pivots around the clear band between the panels (not the raw screen centre), and there's far more black margin to scroll into — you can pull any edge well clear of the HUD.

## v0.51 (2026-07-15) — Charges on Solid Ground & the Maren-Proof Fix

**Charges no longer spawn adrift in a chasm or a lake.** On maps with a chasm or deep water through the middle, "Protect the Charges" (and the "seize this point" objective) used to drop the villagers/wagons on a single grass tile ringed by impassable void. They now land on solid, reachable ground near the centre — verified across dozens of chasm and water maps.

**The main-quest RNG wall is gone.** "Bring Maren proof — win purge or delve contracts to intercept Conclave letters" advanced on only a flat 35% chance per win, with no pity, so an unlucky company could sit on it for many weeks. The odds now climb with every purge/delve win *and* with how deep into the war you are: early game keeps the ~35% first-try flavour, but by the late weeks the letters surface at ~75%+ on the next win and are guaranteed shortly after. (There was never a time limit on this stage — it was recoverable all along, just badly gated.)

_(The mire darkening tried in v0.50 is reverted — back to the dark muck.)_

_On the ash-haze bow question: an enemy two diagonal squares away is at shooting distance 2 (diagonals count as 1 for line-of-fire, unlike the 1.5 they cost to walk), which is inside the ash-haze range of 3 — so it is in range. If a shot isn't offered, it's because that soldier has already spent their action (the readout shows "Action —") or something breaks line of sight._

## v0.49 (2026-07-15) — Framed Map, Actions Dropdown & Paced Enemy Turns
Battle-UI feel.

**The map is framed, not jammed.** The battlefield now fits into the clear band between the top bar and the action bar, so there's a proper buffer of black above and below it — the top and bottom edges are always reachable instead of hiding under the HUD.

**Actions are a dropdown.** The row of spell/graft buttons is gone; there's a single **✦ Actions ▾** that opens a menu of everything the soldier can do (spells, grafts, brace). And once a soldier has moved or struck, a **Next ▶** button appears right after the scout eye, so advancing to the next soldier is a single tap where your thumb already is.

**Enemy turns breathe.** After each enemy finishes its move or attack, the camera now holds on it for about a second — long enough to read what happened — before focus jumps to the next one. No more instant, hard-to-follow enemy phase.

## v0.48 (2026-07-14) — Battles Survive a Reload, Enemy Hit FX & Mobile Portrait Fix
Mobile robustness and combat feedback.

**Your fight is no longer lost on a rotate or refresh.** A battle was never written to the save, so when a mobile browser reloaded the page on an orientation change (they do this under memory pressure), the whole fight vanished — and re-entering felt like your party's turn had reset. Battles are now stashed when the page is hidden or unloaded and resumed exactly where they stood on the next open — same round, same positions, same actions spent (the map dimensions ride along, and the enemy AI is re-kicked if it was mid-phase).

**Enemy hits animate now.** Enemy attacks were queuing their arrows, damage counters and "dodged/blocked" tags, but a double-redraw in the enemy turn wiped them before they drew. They're now deferred to draw on the settled frame — you'll see the arrow fly, the number pop, and the miss register, for foes as well as your own soldiers (spell effects included).

**Portrait loads correctly the first time.** On some phones the map fit to a not-yet-settled viewport on first paint and only corrected after flipping to landscape and back. A viewport observer now re-fits the moment the real size is known (and on URL-bar show/hide), so the battlefield frames correctly from the start.

**Also:** the "Next" button now consistently skips soldiers with less than a full step of movement left (matching the Move-0 rule).

## v0.47 (2026-07-14) — Everyone Walks, Spell FX & Combat-Clarity Fixes
A polish pass on motion, feedback, and clarity.

**Enemies walk too.** The glide now works for the enemy AI, not just your soldiers — a rendering quirk (enemy moves fire two redraws back-to-back) was cancelling their animation. Walkers also ride **above** the ground and elevation tiles for the whole step, so they never disappear behind a wall or slope mid-move.

**Every spell has its own animation.** Ashfire hurls a fiery orb; blightbolt a violet one; Bone Spears erupt as a starburst of shards; Blight Storm and War-Cry roll out expanding shockwaves; Healing Aura blooms a green ring with rising motes; Smoke Bomb puffs a grey cloud; Sanctuary, Protection, Ashen Ward and Rally each settle a coloured ward-ring onto their target (gold / steel / violet / green). Cleave and Shield Bash land with an impact ring.

**Combat-clarity fixes.**
- **Hit % is hidden once a soldier has no action left** — no more phantom to-hit numbers on a soldier who can't strike.
- **Second attacks stay locked** until the level-5 Double Strike: a soldier who has moved, or who isn't yet level 5, can never swing twice (verified).
- **No more dead stops on a fraction of a step.** A soldier with less than one full point of movement left now reads **Move 0**, shows no move tiles, and the "Next" button skips them instead of stranding you on a soldier who can't do anything.

**A frame of black around the map.** You can now scroll a little past the map edge, so the corners are easy to bring into view instead of being pinned against the screen edge.

## v0.46 (2026-07-14) — Walking Tokens, Solid-Filling Walls & Cleaner Ground
Battlefield feel and legibility.

**Soldiers and enemies walk now.** When a unit changes tiles it glides from its old square to its new one instead of teleporting — a short, distance-scaled slide (a two-tile step is quicker than a long dash). Works for your soldiers and the enemy alike, at any zoom.

**Walls fill in solid.** Wall autotiling was reworked: any 2×2 or larger chunk of wall now fills with packed rubble in a mid gravel tone, framed by coursed stone and weathered merlons only on the *outer* exposed edges. Blocks read as solid ruined masonry instead of a ring of hollow frames, and adjacent walls merge seamlessly with no internal seams.

**Cleaner ground.** Removed the checkerboard tint on ground tiles and softened the per-tile grime so open terrain reads as one cohesive surface rather than a grid of squares.

**Movement colour cue.** Once a soldier has spent its action — dashed, attacked, or cast — its remaining movement tiles now show **gold** instead of blue, so you can tell at a glance that moving there won't cost an action you no longer have.

## v0.45 (2026-07-14) — Top-Down Sprites, Contiguous Walls & the Ash-Acolyte Capstone
A visual overhaul of the battlefield, plus a new endgame spell.

**Soldiers are now top-down sprites.** The front-facing portrait busts are gone from the battle map. Each class is drawn from a high angle — crown of the head, shoulders, gear projected onto the ground — grittier and more legible in the tactical view: the **fighter's** kite shield, sword and steel helm; the **ranger's** hood and longbow arc; the **cleric's** white cross-tabard and mace; the **acolyte's** hood, blight-veined robe and floating ashfire; the **shade's** twin daggers. The commander still flies the banner. (The pre-battle roster keeps the face portraits, so you always know *who* you're mustering.)

**Ruin and fortress walls connect.** Wall tiles now autotile — an adjacent wall makes the masonry join, so ruins read as continuous fortifications instead of scattered blocks. Each wall shows the coursed outer stone, packed-rubble core, and weathered parapet merlons (some crumbled away) of a top-down rampart. Runs, corners, T-junctions and broken sections all form correctly.

**Blight Storm — Ash-Acolyte level-5 capstone.** A 3×3 blight-nova hurled at range 5. Every enemy caught takes 5–8 damage that **ignores armor**, and the ground itself festers into blight. Once per battle, +1 corruption — the acolyte's answer to a clustered enemy line.

## v0.44 (2026-07-14) — Double Strike as a Choice, Cleric Kit, QM Economy & Polish
A batch of fixes and reworks.

**Double Strike is now a real decision.** A level-5 martial (fighter, ranger, shade) no longer just swings twice automatically. You may strike twice **only if you haven't moved** — plant your feet for two blows, and you can't reposition after. Move, and you get a single attack. Strike once and you can still move (forgoing the second). Rangers double-shoot the same way. It's the honest trade-off: two attacks, or move and one.

**Cleric spellbook reworked.** Sanctuary and Ward are now distinct: **Sanctuary** shelters an ally so *no enemy can attack them* until your next turn (it does not stack with the Ashen Ward's +armor). **Protection** is a new cleric blessing — +1 armor to an ally for the rest of the battle. The old team-heal is now **Healing Aura**, a level-5 cleric capstone (heal all allies nearby). Every level-up now names the capstone you unlock.

**Quartermaster economy fixed.** Rescuing the Quartermaster no longer hands you a free squad slot — it *opens the baggage train*: after that you can **pay** for a fifth sword (100c) and a sixth (200c), and lay in one-time supplies. **Consumables (kits, horns) are locked until the Quartermaster is rescued.**

**Elevation gained its low end.** The z-level engine now has **shallows (z−1)** and **pits (z−2)** below ground level — wadeable fens, deep quarry floors, sinkholes — reached down the same one-level slopes.

**Cleaner map.** Removed the gridlines (the move/attack tile outlines are enough), and the battle action bar now scrolls horizontally on every screen so nothing hangs off the edge.

## v0.43 (2026-07-14) — Z-Levels: Slopes & Cliffs
Elevation is now a real, Dwarf-Fortress-style z-level system rather than a flat modifier. Every tile sits at a discrete height, and the difference between neighbours decides how you move:

- **Level (Δ0)** — flat ground, normal cost.
- **One level (Δ1) = a slope.** You can walk it, but crossing that threshold costs the extra movement.
- **Two or more (Δ2+) = a cliff.** Impassable on foot — you path around it, climb a ramp, or get shoved off it.

Terrain now builds in these steps. **Stepped hills and crags** rise z1→2→3 as walkable slopes (the ritual field's shrine now sits atop a proper climbable crag; ruined keeps are sometimes fortified heights). **Bluffs and mesas** stand with sheer cliff sides and a single ramp up — high ground you have to earn. The quarry's terraces, the causeway, and the pit all obey the same rules.

The map reads the terrain for you: higher ground catches light, low ground sinks into shadow, each terrace edge shows a lit lip and a shadow, and **cliff faces are drawn as thick dark drops**. Inspect any tile to see its z-level and which sides are slopes vs cliffs.

Height still helps in a fight — attacking downhill hits harder, archers see and shoot farther from high ground, and a hill blocks line of sight past it. And a **shield-bash can now shove an enemy off a cliff** for a hard fall (heavy damage; a chasm is still an outright kill). Every generated map was checked to remain fully traversable.

## v0.42 (2026-07-14) — Mobile Battle UI Pass
The immersive battle HUD was built desktop-first; this pass makes it right on a phone.

**Portrait phones** get a proper stacked layout instead of overlapping desktop corners:
- A slim single-line title bar (contract · round · objective) with the **☰ Log** button beside it.
- The squad roster becomes a horizontal, swipeable strip below the title.
- The field log opens as a full-width sheet under the roster (not a cramped corner box).
- The bottom is a clean stack — a compact soldier card (no wall of instructions), the move/action readout, then a swipeable action row with **End Turn pinned to the left so it's always in reach** and Retreat tucked at the far end.
- Zoom ＋/－ moved to the right edge, mid-screen, at a thumb-friendly 44px.

**Landscape phones** keep the desktop corners but drop the verbose hint and tighten the cards so nothing overflows or collides on a short screen.

Also fixed touch-scrolling on the roster and action strips (the map's gesture-capture had been swallowing it), and confirmed tap-to-select, tap-to-move, and the log toggle all work by touch. Desktop is unchanged.

## v0.41 (2026-07-13) — Grimdark Company: Class Character Tokens
Your soldiers no longer read as interchangeable faces on the board. Each is now a **class-distinct grimdark figure** — their own face framed in the armour, helm/hood, and weapon of their calling:

- **Fighter** — steel plate, red surcoat, a great-helm, sword and kite shield.
- **Ranger** — a green hood and cloak, longbow at the ready.
- **Cleric** — chainmail coif and a white tabard marked with a red cross, mace in hand.
- **Ash Acolyte** — dark ashen robes shot through with blight-violet, a hood, and a coil of ashfire.
- **Underkingdom Shade** — black hood and leathers, twin daggers.
- **Commander** — whatever their class, they carry a tattered banner over the shoulder.
- **Revenants** rise as a corrupted version of exactly what they were — same kit, violet glow, dead-eyed.

They read by silhouette and colour when zoomed out and by detail when you zoom in, and the same figure now heads the unit card. Individual faces are preserved inside the armour.

## v0.40 (2026-07-13) — Immersive Battle Map: Pan, Zoom, Floating HUD
The scrolling grid-in-a-box is gone. The battlefield now fills the screen and everything else floats over it.

- **Pan & zoom.** Drag to pan, scroll-wheel or pinch to zoom, or use the ＋ / － buttons. The map opens framed to fit the whole field and follows whichever soldier's turn it is; once you take the camera, it's yours.
- **Floating HUD.** Contract/round/objective sit top-left, your squad roster top-right, the selected soldier's card bottom-left, and the action bar bottom-center — all as translucent overlays on the map.
- **Field log minimized.** The log is hidden by default behind a **☰ Log** button; pop it open when you want the play-by-play, close it to see the field.
- **"Next ▶" button.** Jumps to the next soldier who still has a move or action left, and greys out once the whole squad is spent — quick to run your turn without hunting the roster.
- **Rain now bites.** Rain shaves 1 off ranged range (bows and thrown weapons), where before it was pure atmosphere. Fog and ash-haze still cap range harder.

Works on desktop and phone (pinch-zoom, compact mobile HUD).

## v0.39 (2026-07-13) — Graphics Depth: Atmosphere & Built Ruins
A cinematic pass to bring the battlefields closer to grimdark tabletop art.

**Vignette.** The viewport is now framed in darkness — edges fall off to shadow, drawing the eye to the fight. It stays fixed as the map scrolls.

**Weather you can feel.** Fog and ash-haze, which used to share one generic veil, now read as their own thing: fog drifts in pale banks; ash-haze hangs warm and brown with embers sifting down. And a new **rain** — diagonal streaks sweeping the field — falls on some clear-weather maps. Rain is pure atmosphere (no combat penalty); fog and ash-haze still cap sight and bowshot as before.

**Built ruins, not icons.** The stone tiles were redrawn to read as made things: **walls** are broken courses of dressed masonry with mortar lines and stones fallen at their feet; **columns** are fluted drums with capitals; **standing stones** are weathered, cracked, moss-flecked; **bridges** are heavy timber decking; **boulders** got naturalistic shading. Corrupted ground carries a faint violet edge.

## v0.38 (2026-07-13) — Hazard Maps: Spreading Blight & Killing Falls
Two more tactically distinct battlegrounds, each with a hazard that reshapes the fight.

- **The Blight-Menhir Field** — the map itself turns against you. Cracked standing stones seed a corruption that **spreads across the ground every round**, searing anyone who ends a turn on it (2 damage) and steadily swallowing your safe footing. The menhirs are attackable: **crack them and the creep halts** — but the ground you've already lost stays lost. Race to kill the enemy, or spend blows silencing the stones. A clock you can fight.
- **The Cliffs** — narrow ledges above a sheer **chasm**. It's a brutal funnel: cross the land-bridges or take the long way round the ends, with archers duelling across the gap. And a **shield-bash lands a foe over the edge — a clean kill, gone into the dark.** (It cuts both ways: mind your own footing near a drop.)

New terrain: **chasm** — impassable, but you can see and shoot across it, and a shove sends you over.

Also hardened the connectivity guarantee: the whole battlefield is now verified as one walkable component (a stray unit sealed in a wall-pocket gets pulled to reachable ground), checked across 120 generations of all 13 map types.

## v0.37 (2026-07-13) — Four Tactically Distinct Battlegrounds
Four new map types, each built around a genuinely different tactical problem, plus a new terrain: **mire** — soft ground that's passable but slow (costs double to cross).

- **The Causeway** — a raised stone road cutting through a drowned fen. The road is the fast, dry, high-ground chokepoint; the flanks are slow mire and black pools. Take the causeway or slog through the muck the long way.
- **The Fever Marsh** — broad slow mire from edge to edge, strung with black pools and reed beds, broken only by a few dry hummocks. Safe, fast footing is the scarce resource; who holds the hummocks holds the fight.
- **The Quarry** — a terraced stone pit: a high spoil-rim rings a floor that steps *down* through levels. Each level change costs movement, the rim commands the pit, and boulders and cut stone give cover. Vertical fighting.
- **The Boulder Field** — open killing ground broken by boulder cover-islands and low ruined walls. Cover is scarce and precious; a ranged-duel map where positioning between the rocks decides it.

New maps roll into the pool automatically (marshes and causeways in wet country, quarries in the hills, boulder fields anywhere). Every one is guaranteed reachable and was verified across 70+ generations with clean AI battles.

## v0.36 (2026-07-13) — Grimdark Ground: Texture, Debris, Cover
The battlefields were clean and barren between their centerpieces. Now they're grimed and lived-in.

**Textured ground.** Open ground is no longer a flat colour swatch — every tile gets procedural mud, dirt speckle, and grime, so the earth reads as trodden and filthy. The palette went muddier and darker overall.

**Ambient debris.** Non-blocking clutter now dresses the ground, themed to each map: bones and skulls, broken planks, mud puddles, blood stains, scattered rocks, marsh reeds, ferns and stumps in the woods, and — in the pillaged hamlets — barrels, crates, cart wheels, and gore. Purely visual; it doesn't change how anyone moves or fights.

**More honest cover.** Each map now scatters extra passable brush, a few trees, and the odd boulder in sensible places, so there's more to fight around without clogging the travel lanes. The thematic centerpieces (river, fort, hilltop, well) are untouched.

**Every battle winnable.** Added a connectivity guarantee: the game now checks that the company can actually walk to every enemy, and drags any foe stranded behind sealed walls out to reachable ground. (This also clears the way for the walled map types coming next.)

## v0.35 (2026-07-13) — Cinematic Battlegrounds + Diagonal Movement
A battle-map overhaul plus a movement upgrade.

**Bigger, square maps.** Battlefields are now roughly square (~20–26 per side) instead of short-and-wide — a proper arena with room to maneuver.

**Muster on a random edge.** The company no longer always starts on the left. On open battles (slay/hunt) you deploy on a random edge — a corner or the middle of some side — and the enemy pods deploy in the quarter farthest from wherever you landed. Directional missions (escort a wagon, guard charges, seize a point) still start you on the west edge with your objective.

**Cohesive battlegrounds with a centerpiece.** Maps are built around one honest feature and clear lanes rather than scattered noise: a **river** with two bridges, the walled **ruins of an old fort** (rubble walls, corner columns, a raised keep) with gate gaps, a **hilltop** ringed with standing stones, a mountain **pass**, dense **woods** around a central clearing, or a pillaged **hamlet** of ruined houses around a well. Cover comes in clean clumps, so travel lanes read clearly.

**Plateaus.** Elevated ground now plateaus properly: stepping up onto it costs one extra movement at the single-tile slope edge, and the flat top is normal-cost ground you can cross freely (and it can hold its own terrain). No more paying a climb tax on every tile of a hill. High ground is drawn more legibly, too.

**Diagonals cost 1.5.** Movement is now 8-directional — a diagonal step costs 1.5 movement (an orthogonal step still costs 1), so your reach forms an octagon. You can't cut a diagonal corner between two solid walls, and melee now strikes any of the 8 neighbors (diagonals included), so standing corner-to-corner is a real engagement. Enemies use it too, closing the distance on the diagonal instead of the long way round.

## v0.34 (2026-07-13) — Enemies Double-Move to Close (When They Have a Reason)
Corrects the previous turn's over-caution. Enemies now **can** double-move — a melee foe that's engaged or pursuing but can't reach anyone this turn spends its turn on a **second move** to close the gap (a dash, like the player's, no attack after). It only happens when they have a reason: it's gated to the combat body, so a foe that's **on patrol never double-moves**, and a foe that can already reach an attack just moves and strikes. Patrols are back to **full-speed** wandering (the earlier gentle-cap was a mistake). Net effect: distant enemies commit and run you down once they're onto you, instead of ambling one move at a time — but unaware patrols still move at a normal, non-aggressive pace.

## v0.33 (2026-07-13) — Softer Move Tiles, Cleaner Scout Mode, Gentler Patrols
Polish + an AI check.
- **Softer movement outlines.** The blue (move) and gold (dash) tile rings are now more transparent for a lighter touch, and the **gold ring is solid** like the blue rather than dashed — the two are distinguished by colour, not line style.
- **Scout mode hides the action outlines.** With the 👁 inspect toggle on, the blue/gold move rings and the red attack markers disappear, so it's obvious that tapping a square only reads it — it won't move or attack.
- **Enemies don't double-move — confirmed, and patrols now idle.** Checked: enemies never dash (they use a single movement budget, never move twice), and protect/caravan missions correctly field enemies that pursue the objective. But patrolling squads were wandering at *full* speed, which read as purposeful. **Unaware patrols now wander gently (a capped idle drift)**; full-speed movement is reserved for a charge (once they've spotted you) or an alerted search.

## v0.32 (2026-07-13) — Movement-Color Fix & Honest Bow Range
Two follow-ups to the squad-tactics rework.
- **Once your action is spent, movement stays gold.** Previously, if you dashed (spending your action to move into the gold tiles) and had movement left over, the remaining tiles reverted to blue — implying you could still act. They now stay **gold** whenever the action is gone (from a dash or an attack), so the color always tells the truth: blue = you'll keep your action, gold = your action is/was spent.
- **The bow "range 6" now reads honestly.** The archer's range was never wired to movement — it's line-of-sight and weather. Two clarity fixes: (1) **fog and ash-haze cap ranged attacks to 3**, and the unit card now says so — e.g. "range 6 (3 in this fog)"; (2) an enemy that's **in range but behind a tree/hill** (visible because a frontline soldier spotted it, but with no clear line from your archer) is now flagged with a dashed red outline and an "IN RANGE but no line of sight — move for a clear shot" tooltip, instead of just looking un-shootable. High ground shows its "+1 on high ground" bonus too.

## v0.31 (2026-07-13) — Squad Tactics: One Player Turn, Split Movement
A ground-up rework of the tactical layer into proper squad tactics, plus a difficulty tightening.
- **One Player Phase, then the Enemy Phase.** Individual initiative is gone. On your turn you command **your whole company in any order you choose** — tap a soldier (on the map or in the roster strip up top) to make them active, move/act them, switch to another, come back. Move the soldiers on the outside first to clear a lane for the one boxed in. When you're done, **End Turn** and the whole enemy line moves.
- **Movement is a pool you spend around your action.** Each soldier has movement points and one action. **Blue tiles** are reachable with your remaining movement and keep your action free; **gold-dashed tiles** are reachable only by dashing (which spends your action). Crucially, movement **splits around your action** — with Speed 3 you can move two tiles, strike, then move the last tile. Move, attack, move.
- **Skirmisher** now refreshes your movement to a full budget (+1) after you attack — strike and fade, in the new economy.
- **No more easy-XP farming.** Danger-1 contracts dry up by **week 4** (a green company gets three weeks to blood itself on the frontier, then the war moves on and the softest work available is danger 2).

Verified end-to-end and run through a multi-agent adversarial review (turn engine, movement, control, status timing, stale-reference sweep) — no softlocks; three confirmed issues fixed (roster-tap selection, brace-while-aiming, ability fog-of-war guard).

## v0.30 (2026-07-13) — Milestone Hardening (Adversarial Review Fixes)
A multi-agent adversarial review of the v0.26–v0.29 milestone surfaced five confirmed bugs, all fixed here:
- **(major) Raising the dead no longer restarts the round.** The Blight-Mage's and Blight-Sorcerer's raise called `buildQueue()` mid-turn, which reset the initiative index and cleared everyone's move/action flags — replaying the round and handing bonus turns to both sides. The raised unit now simply joins the tail of the current round. (This was a latent bug in the mage since v0.17, caught because the new sorcerer reproduced the pattern.)
- **(minor) Set-piece elites stay off the easy contracts.** The new Conclave Circle (Blight-Sorcerer) and Blight Warhost (Blight-Troll) doctrines now require danger 2+, so they never spawn on the deliberately-safe danger-1 frontier fight.
- **(minor) Cleave kills count.** A kill via the Cleave ability now credits Reaper stacks and the battle-kill tally, like any other kill.
- **(minor) No unlock from a failed rescue.** Quartermaster commission rewards (party/armour) are no longer granted if the protect/escort charges all died.
- **(minor) The frontier floor respects fixed contracts.** The danger-1 guarantee no longer overwrites the pay/danger of a Quartermaster, Cinderling, or story contract — it clamps a plain contract instead.

## v0.29 (2026-07-13) — The Cinderling: a Rare Underkingdom Recruit
Sometimes, from **week 4 on**, a rumor surfaces (rare, ~7%/week): a stranger who "moves by ashfall and smoke" is cornered by grey riders. Take **The Hunted Stranger** contract and an **Underkingdom Shade** fights at your side as a guest you control — and if they're **alive when you win**, they join the company for good. Lose, retreat, or let them fall, and they're gone (a guest leaves no grave).

The Shade is a new class — a glass skirmisher (high SKL/SPD, thin HP/armour, **no Ash graft, no corruption**): the anti-Conclave craft to the Ash Acolyte's bargain. Their kit:
- **☁ Smoke Bomb** (starter, once/battle): drop a choking cloud — enemies within 2 are **blinded (−10 to hit)** until their next turn.
- **Underkingdom Garrote**: **+15 hit and +2 damage** against an **isolated** target (no ally adjacent to it) — punishing anyone who strays from the line.
- Plus Skirmisher/Fleet/Duelist/Executioner from level-ups, and (being martial) **Double Strike at level 5**.

Only surfaces when you have room in the company (roster < 12).

## v0.28 (2026-07-13) — A Bigger Company & Earned Upgrades
Progression is less "pay coin, get stronger" and more "do the work, unlock the capability."
- **Bigger company.** The roster cap is now **12** (was 6), so you can keep a bench — rotate the wounded out, hold reserves against your own rising dead. You still **muster at most 6** to any single battle.
- **Weapon & armour upgrades are unlocked, not assumed.** Reforging weapons and fitting armour start **locked**. Recover the **Blacksmith's Anvil** (a ruin-forge you seize) to unlock reforging, and the **Armorsmith's Tools** (a stranded wagon you escort home) to unlock fitting — both posted as **Quartermaster commissions** you take like any contract. Soldier cards show 🔒 chips until you've earned each. (Existing campaigns are grandfathered — you don't lose access mid-run.)
- **Party size comes from a rescue, not a purchase.** The +1-field upgrades are gone from the coin shop; instead, **Rescue the Quartermaster** on a protect-the-convoy commission to widen your battle line (up to the field cap of 6). The Quartermaster panel now splits into mission **Commissions** and coin **Supplies**.
- **Ash grafts only where the Blight is.** Relic grafts were dropping on any purge/delve/reclaim — including clean, low-pressure frontier jobs. Now they only appear where the Blight actually bites: swallowed or high-pressure regions, blighted ground, or burn/reconsecrate objectives. Steel companies stay Steel unless they go looking in the dark.

## v0.27 (2026-07-13) — Double Strike & Cleave-as-a-Choice
Two combat-depth changes.
- **Martial capstone — Double Strike.** At **level 5**, Fighters and Rangers strike **twice** on a basic attack (two independent hit/damage rolls — a Ranger looses two arrows). It kicks in mid-battle the moment they ding 5, and it never wastes the second swing on an already-dead target. Clerics (support/heal) and Ash Acolytes (casters) are excluded by design. The soldier's battle card shows a **⚔ Double Strike** flag.
- **Cleave is now a decision, not a freebie.** Axes/great-axes/halberds no longer auto-splash into a neighbour on every hit. Instead they get a **🪓 Cleave** ability: strike your target for **reduced** damage and carry the blow into one enemy standing adjacent to it — you choose the trade of single-target power for hitting two. A plain attack is clean single-target. (Enemies lost their free auto-cleave in the bargain, which the v0.26 escalation more than makes up for.)

## v0.26 (2026-07-13) — The World Hardens: Time-Based Escalation & New Blight Horrors
Mid/late game was flattening out — danger 2 and 3 felt only mildly worse than 1, and easy contracts vanished by week 5. This makes the world escalate on a clock, not just on region pressure.
- **World tier** rises every ~3 weeks (`worldTier()` = floor(week/3)). It's the new difficulty heartbeat, independent of where you fight.
- **Randomized enemy upgrades over time.** Each spawned foe rolls tier-gated buffs whose odds ramp the deeper you are: husks become **Ironbound** (+armor) then **Bloated** (+HP); brigands/cutthroats/deserters carry upgraded weapons and turn **Hardened**; graveguards become **Dread**; blight-mages become **Elders**. By tier 3 a "Veteran Ironbound Husk" can pack 23 HP against the 10 it started at — the power creep is deliberate, so your levelled heroes keep meeting a rising floor.
- **Elites scale with tier too.** Pods reach their full 4-unit comps mid-game, and the promoted elite's buff grows with the tier (Veteran → Elite).
- **Two new enemies, gated to tier 2+ (≈week 6+):** the **Blight-Sorcerer** — an offensive caster that erupts an armor-ignoring **blight nova** when two of your soldiers cluster, raises **graveguards** (not mere husks), and snipes with a longer, harder blightlance; and the **Blight-Troll** — a 34-HP bruiser that **regenerates 4 HP every round**, so you have to burst it down, not chip it. They ride in two new pod doctrines, the **Conclave Circle** and the **Blight Warhost**, still capped to one set-piece pod per battle.
- **Frontier floor:** there's now always at least one danger-1 contract open on the softest region you still hold, so a green company always has somewhere to blood itself — the rest of the map keeps escalating around it.

## v0.25 (2026-07-13) — Every Ability Usable, Skirmisher Fixed, Terrain Inspector
Three combat-clarity fixes.
- **Multiple abilities are all usable now.** The action bar only ever showed one ability button (the highest-priority one), so a soldier who knew, say, both Sanctuary and an Ash graft could only reach the Ash one — the heal was stranded. It now shows **one button per ability**; you still get one action a turn, but you choose which. Toggle the ability you want, or press F for the first.
- **Skirmisher no longer costs you mobility.** The old "free step" was a single tile *and it overrode your normal move* — so attacking first with a Skirmisher gave you **less** reach than a plain soldier. It's now a proper **full move at +1 speed** after you attack (even if you already moved) — strike and fade, the way it should read.
- **New terrain inspector (👁).** There was no way to see what a square actually did. A new eyeball toggle in the action bar turns on inspect mode: tap any square to read its **terrain effects** — cover values, movement cost, line-of-sight blocking, blight damage, high/low-ground bonuses — and, if occupied, the **occupant's stats** (visible units only; fog still hides the unseen). Works on any turn; the inspected tile is highlighted.

## v0.24 (2026-07-13) — Initiative Tracker Respects Fog of War
The turn-order strip listed *every* unit by name — including enemy squads you hadn't spotted yet, spoiling what waited in the fog. It now applies the same fog gate as the map: an enemy only appears in the tracker once it's in your line of sight. Your soldiers and any discovered foes show; undiscovered pods stay off the strip until a scout catches sight of them, then they populate in real time. No count, no names, no free intel.

## v0.23 (2026-07-13) — Nest Births 3× Rarer
Cut the Blight-nest birth-rate to a third across every difficulty. It still scales with the skulls, just far slower now: **danger 3 every 3rd round** (was every round), **danger 2 every 6th**, **danger 1 every 9th**. Burning the nest is about closing on it, not out-attriting an endless tide.

## v0.22 (2026-07-13) — Blight-Nest Birth-Rate Scales with Danger
On "Burn the Nest" contracts the nest disgorged a fresh husk/hound **every single round** regardless of the skull rating, which made even a 1-skull burn a grind against an endless tide. The birth-rate now tracks difficulty: **danger 3 still births every round** (the old rate, kept as the ceiling), **danger 2 every 2nd round, danger 1 every 3rd**. Same 7-mobile field cap and same "it won't stop until it burns" win condition — you just aren't drowned on the easy ones while you close on the nest. (Battle now carries its `danger` so objectives can scale off it.)

## v0.21 (2026-07-13) — Pod Count Tracks the Skulls (Honest Danger)
The pod count now matches the danger rating on the tin. It was fixed at **danger + 1** (a 1-skull fight *always* fielded 2 pods, a 2-skull always 3), so an "easy" 1-skull contract could put 5-6 bodies on the field. Now it's a **range that tracks the skulls: N skulls → N or N+1 pods** — danger 1 → **1–2** (often just a single pod of 2-3 foes), danger 2 → **2–3**, danger 3 → **3–4**. The Scout Report preview shows the range to match. The other half of "why did my 1-skull fight have seven enemies": a **revenant** — your own risen dead — is injected into ~72% of fights in a region where it walks, and it carries a full soldier's build, a real threat the skull count never showed. That's now **telegraphed on the contract** ("⚰ Your dead walks {region} — it may rise into this fight, beyond the skulls"), both on the map hex panel and the muster prompt, so a hard fight in a haunted region reads as hard before you ride out.

## v0.20 (2026-07-13) — Pods Spawn Spread Out (No More Turn-One Swarm)
Fixes a real "I got overwhelmed by seven at once" problem. Enemy pods were placed by rejection-sampling with a spacing floor as low as 4 tiles — but the shout that wakes a *neighbouring* pod carries 6 tiles, so on a 3-pod fight (a danger-2 purge) **~69% of the time two pods spawned within shout range** and co-aggroed the instant you were spotted: you'd trip one squad and its shout would drag a second onto you. Pod homes are now chosen by **farthest-point placement** — each pod is seated on the open tile farthest from every pod already placed, spreading them as far apart as the battlefield geometry allows. Result: 2- and 3-pod fights now spawn pods a **median 11 tiles apart with 0% inside shout range** (down from ~69%), and even 4-pod danger-3 fields drop from 99% to ~13%. You can pull and fight squads **piecemeal** again — which is the whole point of the patrol/alert/charge system. It's still fine for pods to *patrol into* each other over the course of a fight; they just no longer start on top of one another. (Verified: a danger-2 purge leaves all three pods patrolling and unaware while your line holds its deploy zone.)

## v0.19 (2026-07-13) — Starting Feats, Bigger Company & the Quartermaster
The opening is fairer and the strategy layer got a shop. **Every soldier now starts with a feat** — no more a blank turn-one build: Fighters open with **Shieldwall** (+1 armor beside an ally), Rangers with **Deadeye** (+10 hit & +1 range), Clerics with **Sanctuary** (the team heal), Ash Acolytes with **Ashfire** (armor-ignoring blightfire at range). **The founding company is four** now — one of each archetype — so you can field a full line from the first contract, and the deployable party caps at **4, upliftable to 6**. **New Quartermaster** at any settlement — one-time purchases:
- **Party size** — permanently field more soldiers: 4→5 for 100c, 5→6 for 200c.
- **Scout Report (40c)** — reveals the enemy pods waiting on *every* posted contract (pod count, doctrines, and a warning if a Blight-mage coven might ride along), shown right in the contract list. Spent the moment you begin any mission — buy it when you're choosing where to march.
- **Chirurgeon's Kit (35c)** — a consumable you choose at muster: your squad deploys at **full HP**, wounds and all.
- **War Horn (30c)** — a consumable that opens the battle with the **enemy line shaken** (−10 to hit on round one), buying you the first exchange.

Consumables are toggled on the Muster screen and only spent if you actually march, so you can carry them for the fight that needs them. (Design note: "max party 5" was extended to 6 to fit both the +1 and +2 upgrades — trivially capped back to 5 if preferred.)

## v0.18 (2026-07-12) — Tactical UI Polish & Player-Favored Rebalance
A pass on feel and fairness, all verified in-browser (and adversarially reviewed for regressions). **Initiative tracker** left the obstructive right-sidebar column and became a compact **horizontal strip** that sits right of the Move/Action tracker above the map, scrolling sideways as the turn order runs long — the active unit is chip-highlighted. **The camera no longer betrays the fog**: on enemy turns it used to scroll straight to whoever was acting, revealing foes you hadn't spotted; now it only follows your own units and enemies you can actually *see* — during a hidden enemy's turn it holds exactly where you left it instead of snapping away. **Action bar is sticky**: Brace / End Turn / Retreat / your ability now pin to the bottom of the battle screen on desktop as well as phone, always in reach. **Rebalance, tilted back toward the player**: the Blight-Mage's **Ebon Coven is now a rare set-piece** — barred entirely from danger-1 and danger-2 fights, and even on the hardest contracts it's at most **one** pod and only shows up in a minority of them. Typical pods are now **two foes (sometimes three)** of lower level rather than three-to-four, especially on easy contracts; a Coven fields the mage plus **two** husk guards (down from three melee); and **husks are softened** (14→10 HP) so a 15-HP starting soldier drops them in a couple of hits instead of grinding. **Clerics start with Sanctuary** — a once-per-battle team heal (all allies within two tiles, including the cleric, +4 HP) — so the squad has real sustain through multi-pod fights from turn one; it takes priority over a mace's Shield Bash so a cleric always has the heal in hand.

## v0.17 (2026-07-12) — Classes, Commanders & Pod Doctrines
Both sides of the field grew a spine. **Your soldiers now have classes** — Fighter, Ranger, Cleric, or **Ash Acolyte** — and the class drives everything: starting weapon and stat ranges, and the **feat pool you level into**. A Fighter builds toward duelist/shieldwall/bulwark/berserker/reaper; a Ranger toward deadeye/fleet/skirmisher; a Cleric toward medic/bonecarver/stalwart; an Acolyte only ever grafts Ash powers (ashfire/veindrink/bonespears/ashward). No more picking a random feat that fights your kit. **Backgrounds are class-matched** — a shieldbearer reads as a Fighter, a huntsman as a Ranger, a field-chirurgeon as a Cleric, an ash-touched as an Acolyte — so who a soldier *is* fits what they *do*. **The Commander is singular now**: only the banner-bearer can take **War-Cry** and **Rally**, and standing within two tiles of the Commander grants a **+hit banner aura** to the soldiers around them. Old saves migrate cleanly — a classless veteran infers their class from their kit (Ash feats → Acolyte, medic → Cleric, a bow → Ranger, else Fighter).

**Enemy pods fight as real formations** now, each running a named **doctrine** that keeps them clustered and executing one plan: **Brigand Warband**, **Hound Outriders**, **Karsk Shieldwall**, **Risen Tide**, and — the big one — the **Ebon Coven**. A Coven is led by a **Blight-Mage** who backs away from your blades, slings **blightbolts** at your softest target, and **raises the dead** — clawing fresh husks up from the ground on a cooldown (capped per battle) to replace the ones you cut down. Its **husks become bodyguards**, interposing themselves between you and their mage. New **Hound-Riders** are mounted archers that **kite** — they ride clear of anyone who closes and shoot from range, never letting you pin them. Pods converge on a **shared quarry** and hold a **cohesion leash** (verified: a charging Coven's members stayed within ~4 tiles across a full engagement), so you fight a squad that moves like a squad, not a crowd of individuals. Doctrines are drawn from the contract type — undead Covens and Risen Tides answer purge/delve, brigand warbands and outriders roam patrols. Scout a pod and its tooltip now names its doctrine and shows whether it's unaware, alerted, or engaged.

## v0.16 (2026-07-12) — Enemy Pods, Robustness Audit & Art Unification
Reviewed the last two builds with a multi-agent audit (3 robustness finders + adversarial verification, a graphics reviewer, a pod designer). **Enemy pods**: on generic hunts (slay/capture/generic-assassinate), foes now deploy as **patrolling squads (2–4)** that wander their home ground and look around with *their own* field of vision — one tile shorter than yours, so you out-scout them by a hair. A pod stays unaware (grey ◦ badge) until a member actually **sees** a soldier; then it **charges** and **shouts**, waking nearby pods to *alert* (they march on the noise, red `!` badge) — one bounded hop, no instant map-wide aggro. Shooting a patroller from stealth wakes its pod too. Easy maps field 2–3 pods; the hardest 4–5, with a `Veteran` elite promoted per pod at high danger. You can now flank, avoid, or rush the objective past sleeping squads. Set-pieces (finale, courier/barrow, burn, protect/escort, ambushes) stay full-aggro. **7 verified bugs fixed**: `tileAt` had no bounds check (Shield Bash could shove an enemy off-grid into an unwinnable stall — now bounds-guarded, also fixing edge cover-wrap); low ground (elev 0) was silently coerced to normal by `||1`; the reclaim objective had no win handler (six-round hold now wins); a wounded revenant double-moved (fled cover then re-charged same turn); escort wagons crawled 1 tile/round on the big maps (now ~2); skittish-leader guards could spawn on impassable tiles; the palace stealth cone was drawn as a triangle but detected as a sector (now a true arc, so the red cone tells the truth). **Art unified**: retired off-palette teal (hunters→blight-purple, deserters→steel, shrine→green), collapsed five near-duplicate reds to a two-red system, unified four near-black outline colors to one, pulled battle water into the steel family, fixed the archer's out-of-convention gold eyes, and — the big one — replaced `filter:brightness` tile shading (which was dimming the portrait *inside* each tile) with inset shadows that paint under the token; deleted dead v0.14 CSS.

## v0.15 (2026-07-12) — Battle Maps II: Terrain, Elevation & Fog
The tactical map is rebuilt at a finer scale — single-tile features (a wagon now fills ~3×3) on **much larger maps (~19–24 × 13–16, ~280–380 tiles)** that **scroll**, auto-centering on the acting unit. **Fog of war is default**: your soldiers reveal a radius (blocked by trees, walls, hills), enemies are hidden until seen — and actual fog/ash-haze weather shrinks the sight radius further and caps ranged range. **Elevation**: high ground gives archers +range and everyone +hit downhill (and blocks line of sight past it — climb it to see over); low ground/dig-pits leave you exposed from above. **Themed generators keyed to mission, with procedural variation for replays**: a river arcing corner-to-corner with just **two bridge bottlenecks**; ancient **ruins** (rubble walls, fallen columns) that break sight, with dig-pits and mounds for elevation; a **ritual hilltop** ringed with standing stones (Weathertop) for capture/reclaim/reconsecrate; mountain **passes**; dense **woods**; open **fields**. Feature tiles carry real rules — brush (soft cover), trees (cover + LOS block), boulders/rubble/columns/stones (impassable, block sight), water (impassable), bridges/roads (fast crossings), blighted ground (2 dmg/round). Line-of-sight, movement cost (climbing and dense terrain cost more), and cover all key off the new tiles.

## v0.14 (2026-07-12) — Act III Update, Part 2: The Finale & Live Stealth
**The spine has an ending now.** Three weeks after you name an heir, the King dies and Magister Vell seizes the throne room — you're summoned to Karsk Gate for **The Throne of Karsk**, the finale set-piece. Vell fights as a boss, and the **reckoning** is literal: every soldier you lost and never laid to rest walks in *his* colors, carrying the builds you gave them — "you will fight everyone you failed to protect," at the climax. Lay all your dead to rest beforehand and he stands with only his own. Victory ends the campaign on a proper **ending screen** that reads your whole run: which heir sits the throne (three distinct epilogues), whether you won on Steel or Ash (corruption/graft count), and your graveyard reckoning (how many of your dead still walk vs. rest). **The palace stealth is now real-time**: guards patrol continuously and sweep red vision cones you must dodge live — tap a spot or use WASD/arrows to glide, pillars break line of sight, reach the gold door before a cone catches you (caught = cells + lost days, same as before). Replaces the old turn-based grid.

## v0.13 (2026-07-12) — Act III Update, Part 1: Blades, Ash & Shrines
A big tactical & content pass (the combat half of the Act III update). **Weapons have identity now**: spears/pikes/halberds get *reach* (hit diagonally and poke two tiles straight over the front rank); war axes/greataxes/halberds *cleave* into foes beside the one you strike; mace & shield grants +1 armor and a **Shield Bash** ability (knockback + stagger, skip their next turn). Weapons tier up — **reforge** them at settlements. **Novel-action feats** beyond "hit it": Grapple-Hook (yank + off-balance), War-Cry (AoE shaken), Skirmisher (free step after attacking), Rally (steady an ally). **More Ash**: Bone Spears (ranged root), Ashen Ward (ally shield) join Ashfire/Veindrinker — all on the corruption clock. Full status system (rooted / staggered / warded / off-balance) with a unified ability-targeting UI. **Smarter enemies**: threat-weighted targeting means they gun for your archers and wounded; Cutthroat flankers beeline the backline; Shieldmen anchor; the assassinate leader is now either a **Butcher** (tough, charges, cleaves) or the **Quarry** (skittish, flees, ringed by shield-guards). **Shrines**: kneel to donate coin and push back regional Blight, or take a **Reconsecrate** contract that reverses Blight across a whole region on victory. **QoL**: keyboard hotkeys (Space end · B brace · F ability · R retreat · Esc cancel) and a mobile fixed bottom action bar. *Deferred to Part 2: the real-time palace stealth rework and the Act III finale itself.*

## v0.12 (2026-07-12) — The Deserter & the Banner (story never dead-ends)
Fixes a real soft-lock: when the Commander deserted (e.g. from a provisions-zero morale collapse) or fell in battle, the authored spine gated on `cmdr()` and became unreachable. Now **the banner always passes** — a "The Banner Passes" beat promotes the senior survivor and the story continues under new leadership; story progress lives on the campaign, not the person, so nothing is lost but the one who carried it. And desertion is now **recoverable**: deserters flee to a named town (teal ⚐ marker on the map, a Deserters rumor list with a countdown, and a buy-back button when you reach that settlement). Pay back-wages (40c + 10/level) to bring them home — and if it was your Commander, choose whether to hand them back the banner or take them on as a common sword. You have **4 weeks** to find them before they're gone for good (another company, another road, or the Blight) — a consequence that still moves the story forward. Total-wipe safety: a lone deserter with enough coin no longer triggers game-over.

## v0.11 (2026-07-12) — Mobile Pass & Public Release
The game is now phone-playable and live at https://jeffersonpikejr.github.io/graveborne/ (GitHub Pages, public, no personal data — saves stay in your own browser). On narrow screens the three-column company view collapses into a **tab bar** (March / Company / Camp), the hex map goes full-width with the selected-hex panel inline beneath it, battle tiles scale down to fit all 13 columns on a 375px screen, and the palace stealth grid scales too. Hover tooltips (weapons, feats, stats, standing) become **tap-to-reveal** toasts on touch. Tactical views re-render on rotate/resize. Desktop layout unchanged.

## v0.10 (2026-07-11) — Act III Part 1: The Succession
**The heir choice.** With the ledger (or without it, on the missed path), the palace at Karsk Gate opens onto *Three Doors*: the dying King's three heirs, each demanding a different quest and offering a different company future. **Prince Aldric** the soldier — hold the ford road against a Blight surge (survive); perk: a second royal column patrols the March at strength 16, and armor comes at quartermaster's rates (−20%). **Princess Maren** the knife — seize the Collegium archive and drag Vell into the light (capture); perk: +15 Karsk standing and a 10c weekly palace stipend. **Prince Casmir** the dealmaker — hand him the evidence quietly through fog and Hunters, your own wagons on the field (protect); perk: +15 Conclave standing, bodies and relics sell +10c, and the Folk hear of it (−5). Each posts an authored set-piece; winning it closes Act III part 1 with the heir in your debt and the King's bedside candles lit. The choice is permanent, the perks run for the rest of the campaign, and all three paths converge on the finale hook.

## v0.9 (2026-07-11) — The Barrow Meeting & The Grafts Negotiate
**Act II finale — timed and missable.** The courier's satchel schedules a meeting under a real barrow hex, three weeks out, marked on the map with a pulsing week-stamped ring and a countdown in the caravan panel. Be standing on that hex during that week and you descend into "Lanterns Under the Barrow": an ash-haze assassination of **The Grey Envoy** — the Magister's man meeting the Conclave's, trading names for bodies, yours among them. Kill him for the Envoy's Ledger (+150c, +3 renown, Act II closed: *"the King is dying, and three heirs are listening"*). **Miss the week and it happens without witnesses** — Act II closes on the failed path, and the Hunters ride in force (str 14, up to two bands) either way. **Corruption loyalty events**: grafted soldiers at corruption 4 get *The Whisper* (indulge it: +1 SKL, +1 corruption / help her fight it: −2 RES, −1 corruption / excise at a settlement: 30c, −2 max HP, graft gone); at 7, *The Demand* — promise the Ash +2 permanent damage, and her hook becomes *"a promise to the Ash, unkept"*: her revenant rises a full iteration stronger. The Ash keeps its side of the bargain.

## v0.8 (2026-07-11) — Act II Part 1: The Courier
**The story continues past the proof.** With the letters in hand, Maren receives you at Karsk Gate openly (side door, quiet steward) and posts the game's first **authored set-piece contract**: *The Magister's Courier* — a purple mark on the map, a fog-locked mountain-pass assassination with a fixed Collegium escort and a named elite, **The Magister's Blade** (♛-marked, crowned on his token). Kill him and the escort scatters. The satchel scene pays 80c and +2 renown — and costs you anonymity: *"The mercenaries. Find what they love."* From then on, **the Magister's Hunters** (⚚, grey riders, Collegium steel) walk the March as a roving agent that stalks the caravan harder than brigands and respawns while Act II stands open. **Two new objectives** power it and enter the regular rotation: **Cut Off the Head** (patrol contracts can roll a marked leader whose death routs the rest) and **Burn the Nest** (purge contracts against a Blight-nest that births a husk every round until destroyed — clearing the field is not winning). Set-piece tech is general: contracts can carry authored names, fixed enemy comps, locked weather, and forced layouts.

## v0.7 (2026-07-11) — Battle Maps & Objectives
Battles are composed scenarios now, not arenas. **Mission objectives** are rolled at the contract level and advertised on the map panel before you ride out: **No Survivors**, **Protect the Charges** (villagers or your own wagons — if they all die the contract fails, whatever else you kill), **Hold the Line** (survive 6 rounds against reinforcement waves), **Escort the Wagon** (it creaks forward on its own; keep the road clear), **Seize the Ground** (hold the marked tile at round's end, twice). Objective bonuses on success; failed charges = no pay + rep hit; brigand caravan raids put your actual wagons on the field (each lost = −5 provisions). **Scenario dressing**: hill/mountain hexes generate walled mountain-pass maps; protect maps get huts and cowering villagers; capture maps ruin-ringed objective tiles; escort maps a cleared road. **Weather**: fog and ash-haze cap sight and bowshot at 3 and hide enemies beyond 5 tiles as shapes in the murk, under a drifting fog veil. **Line of sight**: ranged fire is blocked by rocks and wagons — wagons literally limit sightlines. **Smarter enemies**: flank deployments on protect/escort, archers keep their distance, and the revenant reads the field — she goes for what you're paid to keep alive, hunts your isolated and bonded, and slips behind cover when wounded.

## v0.6 (2026-07-11) — Art Pass I
**Enemies have faces now**: procedural SVG portraits per archetype — leather-capped brigands, hooded archers, scarred deserters in kettle helms, beast-skull Blight-hounds, sunken-eyed husks, Conclave acolytes as glowing eyes in a deep cowl, riveted graveguard greathelms — on battle tokens and the inspector. **Drawn terrain everywhere**: the hex March renders pine clusters, snow-capped ridges, marsh reeds, hill lines, settlement house clusters, broken ruin columns, shrines/barrows/watchtowers, and blight tendrils that curl off corrupted ground, under a vignette. Battle tiles get boulders, pines, grass tufts, and pulsing blight pools with checkerboard shading. **Chrome**: banner emblem, ornamented headers, gradient buttons with hover glow, textured page background, log-line icons, torch-flicker in the palace, arrowheads on arrows, ☠ marks on deaths, and portrait shading (neck + cheek).

## v0.5 (2026-07-11) — Scale, Scars, Ash & Standing
**Tactical screen scales to your window** (tiles up to 84px — no more quarter-screen battles), and map agents are now real tokens: backed discs with faction colors, revenants get a glow ring, stacked agents fan out. **Battle traits**: fights leave permanent marks, good and bad — Scarred (+3 RES, and the portrait literally gains the scar), Cold-Blooded (+5 hit after a 3-kill battle), Pack-Bound, Nervous, Blight-Marked, Grieving (until their dead is laid to rest). Max 3, one per battle. **Ash begins**: purge/delve victories can yield relics — Ashfire Graft (ranged 4–7, ignores armor: the anti-archer answer) and Veindrinker Graft (melee lifesteal) — permanent surgery with a **corruption clock** that takes resolve back at 4 and 7... and what dies grafted comes back grafted. Archers rebalanced: **no point-blank shots** (someone must hold the line) and enemy archers back away from blades. **Dash**: skip your attack to move twice. **Faction standing** (Karsk / the Folk / the Conclave, −60..+60): moved by contracts kept and broken, rites (burying pleases the Folk, selling bodies pleases only the Conclave), road-clearing, and relic sales; ±25 shifts contract pay, hire prices, and body/relic prices.

## v0.4 (2026-07-11) — Faces, Roads & the Princess
**Modular character portraits**: procedurally composed SVG faces (skin/hair/eyes/mouth/scars/eyepatch/hood) on every soldier, hire, and grave — and the same face returns **corrupted** on her revenant (pale, purple-lit eyes, cracks) in callout modals, battle tokens, and the inspector. Recognition is now visual, not just textual. **Roads** drawn as clear dashed tracks between towns. **Inline tooltips** (hover the dotted underlines) on weapons, armor, feats, statuses, and every stat; **level-up screen** shows the full character sheet with the raised stat highlighted. **Authored spine begins**: your first soldier is the Commander; the princess Maren pays for discreet swords in Karsk Gate, but the nameless don't get an audience — so you **sneak into the palace** (turn-based stealth minigame: patrol routes, torchlight vision cones, pillars, 2-tile moves; caught = a night in the cells and two lost days). She reveals High Magister Vell — the crown's arch-mage — secretly corresponds with the schismatic order behind the Blight, and sets the proof-hunt objective (purge/delve victories can surface sealed Conclave letters → Act II hook).

## v0.3 (2026-07-11) — Hex March module
The strategy layer is now played ON the map. 176-hex world: terrain with movement costs (plains/roads fast, forest/hills slow, marsh slower, mountains impassable), settlements (hire and buy provisions only in towns; Karsk Gate is cheap), landmarks (ruins draw delve contracts, barrows, shrines, watchtowers, old battlefields), and hex-level Blight creep — corruption spreads tile by tile as regional pressure climbs; a Swallowing turns the whole region purple. **Roving agents** move daily, even while you rest: brigand warbands (stalk the caravan within 3 hexes), Blight hordes (march on towns and raid them, +10 pressure), a Karsk column (patrols the roads and auto-resolves fights against hostiles — losable), and your risen dead as named ⚰ tokens that walk their ground and can be hunted directly (put-down pays 60c + 20c/improvement). **Contracts are gold ! markers on the map** — click to inspect, take, and ride out with a dashed path preview; interceptions happen mid-route where the agents actually are. Old saves migrate (world generates once, then locks in).

## v0.2 (2026-07-11) — World Map module (superseded by v0.3's hex March)
Six regions on a spatial road graph (SVG map, caravan position, per-node pressure). Distance is real: contracts show days-by-road, pay scales with hops, travel advances the day clock (wages/provisions/Blight tick when the week turns — in camp or on the road). Roads through dying ground (pressure ≥60 or swallowed) roll ambushes: an unpaid fight en route, then choose to see the contract through or abandon it. Blight pressure now spreads along road corridors from hot regions and swallowed neighbors — fronts, not a global timer. Karsk Gate sells cheap provisions (geography matters for logistics). Old saves migrate automatically.

## v0.1 (2026-07-11)
Core loop: contracts → permadeath → corpse decisions → revenants with inherited builds → callouts that shake bonded survivors → lay-to-rest resolution (gravetempered + gear echoes). Founding-grave prologue guarantees a revenant by ~week 3. 19 verified bug-hunt fixes + playtest patch (action economy, combat FX, threat scouting, hit odds).

## Backlog (v0.3+)
- **Faction reputation** (next module): per-faction standing that goes negative; Karsk vs. Conclave vs. Faith reactions (roadmap: "relationship matrix"). Renown → per-employer.
- Region-node interactions on the map (click a node → its contracts/rumors); named settlements.
- Steel/Ash progression tracks; camp events/vignettes; company doctrines; more factions' combat grammars (Thornwood, Faith purge-squads, Blight tides).
- Richer combat animation pass (attack lunges, projectile variety, death beats); sound.
- Difficulty modes + Memento save posture (deaths always commit even if battles restart).
