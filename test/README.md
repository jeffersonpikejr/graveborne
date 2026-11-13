# Headless tests

Playwright scripts that boot the real game in headless Chromium and drive it through the same globals a click reaches.

    python3 -m http.server 8931 --directory .      # serve the repo root
    node test/smoke.mjs                             # battle speed, stash/resume, error banner
    node test/spine.mjs                             # save stamp, legacy walk (incl. the v0.70 shape), backups, recovery
    node test/regress.mjs                           # one check per dead end / engine bug closed in v0.70
    node test/fuzz.mjs                              # a bot plays whole campaigns and fails on anything that reads as "it broke"

`fuzz.mjs` takes `RUNS`, `WEEKS`, `SEED`, `STORY=1` (bias toward the authored spine) and `VERBOSE=1` (per-battle notes).
It fails on an uncaught error, an error banner, an enemy phase that never returns the turn, a modal that cannot be
dismissed, a record that breaks its invariants or will not round-trip a reload, a stall, or a dead end. A failing
seed replays: the game's RNG is one seeded stream on the record, and the bot's choices are seeded too.

Needs `playwright` resolvable from Node (or `PW_MODULE=/path/to/playwright/index.mjs`), optionally
`PW_CHROMIUM=/path/to/chromium`, and `GB_URL` if the server is elsewhere. Nothing here ships in `index.html`.
