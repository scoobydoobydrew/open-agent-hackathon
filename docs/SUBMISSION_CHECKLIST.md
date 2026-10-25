# Submission checklist (deadline 27 Oct 2026, 23:45 UTC)

Source: your own workshop notes (screenshots in the first git commit). They are a summary, not the official text:
confirm each point on https://hackathon.genai.works before submitting.

## Deliverables (from the notes)
| deliverable | status |
|---|---|
| Demo video, 1 to 4 minutes: agent working, the solution explained, sponsor tools mentioned | **you**: script in `docs/PITCH.md` |
| Slide deck: problem, solution, architecture diagram, tech stack, where Zetaris and Nemotron are used | **you**: outline in `docs/PITCH.md`; the diagram is the "How it works" tab |
| GitHub repository: clean code, setup instructions, full README, `.env` ignored | done (see below) |
| Sponsor integration write-up for the form | text ready: `docs/SPONSOR_WRITEUP.md` |
| HackOS: team workspace, task board, claim sponsor credits | **you** |

## Scoring (from the notes) and where we stand
| criterion | points | what we show |
|---|---|---|
| Impact | 30 | a real question (radiation-surviving tumours), measured honestly, with proofs of impossibility |
| Technical | 20 | exact solver, complete search, 67+ tests, reproducible benchmark |
| Innovation | 15 | LLM proposes, solver proves, explanation re-checked; official H-MEM engine |
| Demo | 15 | 1 to 4 minute video: use the script, record the replay, not a live run |
| Product UX | 10 | the UI (Explore, Search, Agent timeline with SQL calls, Benchmark) |
| Sponsor tech | 10 | Zetaris via REST + LLM-written SQL tool + JOIN; Nemotron; Meterless H-MEM; development tool statement |

## Done in the repo
- [x] Tests (`python -m pytest`), reproducible benchmark, honest README with limits and data provenance.
- [x] Nemotron through an OpenAI-compatible endpoint; Meterless endpoint supported through `METERLESS_API_KEY` and `METERLESS_BASE_URL`.
- [x] Zetaris as the data layer (`open_agent` database), the LLM's `run_sql` tool, and a SQL JOIN; the UI shows the data-layer chip.
- [x] Official Meterless H-MEM engine, vendored unmodified, conformance 13/13.
- [x] "How we built it" section in the README.
- [x] `.env` is in `.gitignore` and no secret is in the history of `main`.

## You still need to do
- [ ] **Push:** `git push --force-with-lease origin main` (history was rewritten locally to drop a 28 MB zip that contained local passwords).
- [ ] Claim the sponsor credits on the HackOS task board; if Meterless gives you a `METERLESS_BASE_URL` and key, put them in `.env` (the client switches to them automatically; I could not test that endpoint without a key).
- [ ] **Cursor:** the notes award points for saying the code was written in Cursor. This repo was written with Claude Code, so the README says so. Only add Cursor if you really used it, in the README "How we built it" and in `docs/SPONSOR_WRITEUP.md`.
- [ ] Record the demo video and make the deck (outline in `docs/PITCH.md`); paste `docs/SPONSOR_WRITEUP.md` into the form.
- [ ] Check the rules about commits inside the build window: the two oldest commits are dated 21 Oct (README and screenshots), before the window opened on 22 Oct 00:00 UTC.
- [ ] Make the repository public (or share it with the judges) only after the push.

## Before recording the demo
```bash
bash scripts/zetaris_up.sh                 # the UI also does this itself; the chip must read "Zetaris"
(cd hmem/reference && npm install)         # once, for H-MEM
python -m pytest                           # expect all green
python ui/server.py                        # http://localhost:8765
```

## Let someone else check the setup
A judge who can run the repo in 5 minutes scores higher (per the notes). Test it on a clean checkout:
`git clone`, `python -m venv venv`, `pip install -r requirements.txt`, `cp .env.example .env`, `python -m pytest`,
`python ui/server.py`. Without Zetaris or an API key the UI still runs on the local CSV files and the recorded replays.
