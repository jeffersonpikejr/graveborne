# Headless smokes

Two Playwright scripts that boot the real game in headless Chromium and drive it through the paths that have
bitten before. They are the seed of the harness session on the roadmap (seeded RNG, committed save fixtures).

    python3 -m http.server 8931 --directory .      # serve the repo root
    node test/smoke.mjs                             # v0.66: battle speed, stash/resume, error banner
    node test/spine.mjs                             # v0.67: save stamp, legacy walk, backups, recovery
    node test/trust.mjs                             # v0.68: story re-posts, sword cap, pressure bar, reckoning uncap

Needs `playwright` resolvable from Node (or `PW_MODULE=/path/to/playwright/index.mjs`), optionally
`PW_CHROMIUM=/path/to/chromium`, and `GB_URL` if the server is elsewhere. Nothing here ships in `index.html`.
