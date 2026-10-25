# Submission checklist (deadline 27 Oct 2026, 23:45 UTC, on HackOS)

Source: the official "Submission Requirements" document of the hackathon (where it and the Official Rules disagree, the
Rules apply). Status: **done** = in the repository now, **you** = needs you, **after Nightshift** = needs the Nightshift
runtime running on your PC.

## The four components
| component | requirement | status |
|---|---|---|
| Demo video | 1 to 4 minutes; main workflow, how the agent solves the challenge, key features, Zetaris and Meterless integration, **one real request through Nightshift**; no keys on screen | **after Nightshift**: `docs/submission/record_demo.py` rebuilds it from the running UI |
| Slide deck | problem and target users, solution, workflow/architecture, tech stack, Zetaris and Meterless use, what was unique, product visuals, future enhancements | done: `docs/submission/deck.pdf` (9 slides, one per point); screenshots are refreshed **after Nightshift** |
| GitHub repository | public; README with setup, usage, dependencies; sample inputs and outputs; logs with the model per request; test of the Meterless engine; `.env.example`; `SAMPLE_MODE` fallback | done, except `docs/samples/` with LLM runs (**after Nightshift**) |
| Sponsor technology explanation | Zetaris, Meterless engines and their test, Nightshift connection, NVIDIA, what was unique | done: `docs/SPONSOR_WRITEUP.md` |

## Sponsor requirements
- [x] **Zetaris as the data layer** (`open_agent` database, LLM-written `run_sql` tool, SQL JOIN).
- [x] **A Meterless engine in a working feature with a passing test**: official H-MEM as the agent's memory;
  `python -m pytest tests/test_hmem.py` (12 tests, conformance 13/13 when `npm install` was run). The built bridge is
  committed, so a clean clone needs only Node.js.
- [x] **Nightshift as the primary AI provider (code)**: `agent/llm.py` calls the local runtime first, logs the routed model
  of every request, and falls back to NVIDIA directly only when Nightshift is unreachable, always labelled.
  Covered by `tests/test_llm.py` against a stand-in runtime. **Not yet run against the real Nightshift: after Nightshift.**
- [ ] **NVIDIA through Nightshift, with the model shown per request** (needed for the DGX Spark award): the UI and the trace
  show the routed model; to be proven with a real run: **after Nightshift**.
- [x] Claude Code is the only development tool claimed (Cursor is optional and was not used).

## Done in the repository
- [x] 91 tests (`python -m pytest`), reproducible benchmark, honest README with limits and data provenance.
- [x] `.env` is git-ignored, `.env.example` has placeholders only, no secret in the history.
- [x] `SAMPLE_MODE=true python ui/server.py` runs from a clean clone with no account, key or service (checked on a simulated clean
  clone: 89 passed, 2 skipped that need `npm install`).
- [x] Every commit is dated 22 Oct 2026 or later.
- [x] Pre-existing components listed for the form (`docs/SPONSOR_WRITEUP.md`, last section).

## What you do now (needed for the real Nightshift run)
1. Install **Meterless Nightshift** for Windows from https://meterless.ai/Nightshift/WIN/ (the page asks for a 64-bit Windows
   10/11 PC with a dedicated GPU; see the Participant Setup Guide in the HackOS Resource Center, or ask in the help desk if
   you have no GPU).
2. In Nightshift's **Providers tab** add your NVIDIA key. It does not go into this project.
3. Find the Nightshift **runtime token** (the `proxy-token` file in its state directory, or its Connect link) and put it in
   `.env` as `NIGHTSHIFT_TOKEN=...`, or point `NIGHTSHIFT_TOKEN_FILE=` at the file. Do not paste it in chat.
4. Tell me when Nightshift is running; I check `python -c "from agent.llm import llm_status; print(llm_status())"`, run the
   three sample scenarios, refresh the screenshots, re-record the video and rebuild the deck.

## At the end (you)
1. `git push` (the history was already pushed cleanly once).
2. On HackOS: team with your name in it, **one primary track (Track 02)**, project name and description, roster correct *before*
   the first submission is created (the team locks then), pre-existing components declared (see `docs/SPONSOR_WRITEUP.md`).
3. Upload the video and the deck, paste the sponsor explanation, give the repository URL
   `https://github.com/scoobydoobydrew/open-agent-hackathon`.
4. Claim the sponsor credits on the HackOS task board. Submit early; nothing can be fixed after the deadline.
5. Check the repository in a private browser window: public, README renders, no `.env`, no keys.

## Regenerating the submission material
```bash
python ui/server.py                        # http://localhost:8765 (leave it running; the chips must read Zetaris and Nightshift)
pip install playwright imageio-ffmpeg python-pptx
python scripts/make_samples.py             # docs/samples/: reports, event logs, per-request model traces
python docs/submission/capture_screens.py  # screenshots for the deck
python docs/submission/render_deck.py      # deck.pdf and slides/*.png
python docs/submission/build_pptx.py       # deck.pptx with speaker notes
python docs/submission/record_demo.py      # demo.mp4 (Windows: Edge and the built-in voice)
```
Generated files (`shots/`, `slides/`, `deck.pptx`, `demo*.mp4`) are git-ignored; `deck.pdf` is kept in the repository.

## Let someone else check the setup
A judge who can run the repo in 5 minutes scores higher. Clean checkout: `git clone`, `python -m venv venv`,
`pip install -r requirements.txt`, `cp .env.example .env`, `SAMPLE_MODE=true python ui/server.py`, `python -m pytest`.
