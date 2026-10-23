# Submission checklist (deadline 27 Oct 2026, 23:45 UTC)

## Done in the repo
- [x] Working system with tests (`python -m pytest`, 61 tests) and a reproducible benchmark.
- [x] Nemotron via direct REST (`agent/llm.py`).
- [x] Zetaris as the data layer through its REST gateway (`open_agent` database, three tables, SQL SELECT only).
- [x] Official Meterless H-MEM engine vendored unmodified; conformance 13/13; used by `agent/memory.py`.
- [x] Interactive demo UI with offline replays (`ui/`).
- [x] Honest README: results, limits, data provenance (Remy et al. 2015 model, PyBoolNet repository).
- [x] No secrets in the repository (`.env` ignored; `.env.example` has placeholders).

## You still need to do
- [ ] Push (history was rewritten locally to remove `zetaris-platform.zip`; see "Push" below).
- [ ] HackOS task board: complete the stages.
- [ ] Demo video, 1 to 4 minutes (script: `docs/PITCH.md`).
- [ ] Pitch deck, 5 to 7 slides (outline: `docs/PITCH.md`).
- [ ] Cursor: if the rules require evidence of using Cursor, add a screenshot or note; this repo was built with Claude Code
      and does not prove Cursor use.
- [ ] Check the rules about commits inside the build window: the two oldest commits are dated 21 Oct (README and
      screenshots), before the window opened on 22 Oct 00:00 UTC. All code is dated 22 Oct or later.
- [ ] Make the repository public (or share with the judges) only after the push below.

## Push
The local history was rewritten to drop the 28 MB `zetaris-platform.zip` (it contained a `.env` with local passwords and a
telemetry key). The remote still has the old history, so a normal push is rejected. Use:

```bash
git push --force-with-lease origin main
```

Check on GitHub afterwards that `zetaris-platform.zip` no longer appears in any commit. GitHub may keep unreachable
objects for a while; if the repository was ever public, treat the local default passwords in that zip as exposed and
change them (they only protect your local Zetaris).

## Before recording the demo
```bash
bash scripts/zetaris_up.sh                 # chip must read "Zetaris"
(cd hmem/reference && npm install)         # once, for H-MEM
python -m pytest                           # expect all green
python ui/server.py                        # http://localhost:8765
```
