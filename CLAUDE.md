# Working rules for Claude

## Ship every update
The owner's standing rule: merge and push every update without asking first. Commit on the session's working
branch, push it, open a pull request into `main` if none is open, and merge it. `main` is what GitHub Pages serves,
so every merge goes live at once.

Before merging, run the checks in `test/README.md` (smoke, spine, trust and regress, plus the fuzz bot after engine
changes). Fix anything that fails rather than merging it.
