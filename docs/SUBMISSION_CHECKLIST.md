# Submission checklist (deadline 27 Oct 2026, 23:45 UTC, on HackOS)

Source: the official "Submission Requirements" document of the hackathon (where it and the Official Rules disagree, the
Rules apply). Status: **done** = in the repository now, **you** = needs you.

## The four components
| component | requirement | status |
|---|---|---|
| Demo video | 1 to 4 minutes; main workflow, how the agent solves the challenge, key features, Zetaris and Meterless integration, **one real request through Nightshift**; no keys on screen | `docs/submission/demo.mp4` (3:33, live run through Nightshift, captions and synthetic voice-over); `docs/submission/record_demo.py` rebuilds it |
| Slide deck | problem and target users, solution, workflow/architecture, tech stack, Zetaris and Meterless use, what was unique, product visuals, future enhancements | done: `docs/submission/deck.pdf` (9 slides, one per point), screenshots from the Nightshift run |
| GitHub repository | public; README with setup, usage, dependencies; sample inputs and outputs; logs with the model per request; test of the Meterless engine; `.env.example`; `SAMPLE_MODE` fallback | done; `logs/samples/` has four real runs through Nightshift (reports, events, H-MEM ledger, per-request model trace) |
| Sponsor technology explanation | Zetaris, Meterless engines and their test, Nightshift connection, NVIDIA, what was unique | done: `docs/SPONSOR_WRITEUP.md` |

## Sponsor requirements
- [x] **Zetaris as the data layer** (`open_agent` database, LLM-written `run_sql` tool, SQL JOIN).
- [x] **A Meterless engine in a working feature with a passing test**: official H-MEM as the agent's memory;
  `python -m pytest tests/test_hmem.py` (12 tests, conformance 13/13 when `npm install` was run). The built bridge is
  committed, so a clean clone needs only Node.js.
- [x] **Nightshift as the primary AI provider (code)**: `agent/llm.py` calls the local runtime first, logs the routed model
  of every request, and falls back to NVIDIA directly only when Nightshift is unreachable, always labelled.
  Covered by `tests/test_llm.py` against a stand-in runtime and **verified against the real Nightshift** (22 requests in the samples).
- [x] **NVIDIA through Nightshift, with the model shown per request** (needed for the DGX Spark award): every request shows
  `nvidia/nemotron-3.5-lightning-30b-a3b` as the model that handled it, in the UI, in the trace and in the video.
- [x] Claude Code is the only development tool claimed (Cursor is optional and was not used).

## Extra points from the official rules and the Meterless README
- [x] Evidence logs as JSONL in `logs/` (the Meterless README asks for it; the rules disqualify "no evidence of how the agent
  reached its output"): LLM requests with the routed model, H-MEM retrieval trace, per-run events and H-MEM ledger.
- [x] From the troubleshooting guide: a programmatic interface (`POST /run`, `GET /health`), `input_examples/` and `output_examples/`
  (3 each), a Dockerfile, a connection test script (`scripts/check_nightshift.py`), Zetaris and LLM calls logged.
- [x] A sample mode that runs without credentials (`SAMPLE_MODE=true`); one seam for the provider (`agent/llm.py`); capped
  rounds, retries and SQL turns (no unbounded loops against a paid API).
- [x] Responsible AI section (rules, section 18): README "Responsible use", limits slide.
- [x] Not a "fixed chain" or fabricated activity (rules, section 7.3): the solver's verdict decides every step, the demo
  replays are recordings of real runs and are labelled as such.
- [ ] Rules, section 11.3: data prepared before the window must be declared. Declared: the published network file.
- The rules' own text says the binding version is on hackathon.genai.works; reread it before submitting.

## Done in the repository
- [x] 102 tests (`python -m pytest`), reproducible benchmark, honest README with limits and data provenance.
- [x] `.env` is git-ignored, `.env.example` has placeholders only, no secret in the history.
- [x] `SAMPLE_MODE=true python ui/server.py` runs from a clean clone with no account, key or service (checked on a simulated clean
  clone: 89 passed, 2 skipped that need `npm install`).
- [x] Every commit is dated 22 Oct 2026 or later.
- [x] Pre-existing components listed for the form (`docs/SPONSOR_WRITEUP.md`, last section).

## Nightshift on this PC (done)
Installed from https://meterless.ai/Nightshift/WIN/ (the online installer works without a dedicated GPU), NVIDIA key sealed in
its KEYS tab (never in the project), the runtime token is read automatically from `%LOCALAPPDATA%/ai.meterless.runtime/proxy-token`.
Check any time with `python scripts/check_nightshift.py`. Keep the Nightshift window open while you run the agent or record.

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
python scripts/make_samples.py             # logs/samples/: reports, event logs, H-MEM ledger, per-request model traces
python docs/submission/capture_screens.py  # screenshots for the deck
python docs/submission/render_deck.py      # deck.pdf and slides/*.png
python docs/submission/build_pptx.py       # deck.pptx with speaker notes
python docs/submission/record_demo.py      # demo.mp4 (Windows: Edge and the built-in voice)
```
Generated files (`shots/`, `slides/`, `deck.pptx`, `demo*.mp4`) are git-ignored; `deck.pdf` is kept in the repository.

## Let someone else check the setup
A judge who can run the repo in 5 minutes scores higher. Clean checkout: `git clone`, `python -m venv venv`,
`pip install -r requirements.txt`, `cp .env.example .env`, `SAMPLE_MODE=true python ui/server.py`, `python -m pytest`.
