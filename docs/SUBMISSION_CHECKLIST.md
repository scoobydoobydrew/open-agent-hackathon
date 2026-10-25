# Submission checklist (deadline 27 Oct 2026, 23:45 UTC)

Source: the workshop notes (screenshots from the first commit, since removed). They are a summary, not the official text:
confirm each point on https://hackathon.genai.works before submitting.

## Deliverables (from the notes) and where each one is
| deliverable | status |
|---|---|
| Demo video, 1 to 4 minutes: agent working, the solution explained, sponsor tools mentioned | `docs/submission/demo.mp4` (3:31, captions and synthetic voice-over). Script: `docs/submission/record_demo.py` |
| Slide deck: problem, solution, architecture diagram, tech stack, where Zetaris and Nemotron are used | `docs/submission/deck.pdf` (7 slides) and `deck.pptx` (same slides as pictures, with speaker notes) |
| GitHub repository: clean code, setup instructions, full README, `.env` ignored | done |
| Sponsor integration write-up for the form | text ready: `docs/SPONSOR_WRITEUP.md` |
| HackOS: team workspace, task board, claim sponsor credits | **you** |

## Scoring (from the notes) and what we show
| criterion | points | what we show |
|---|---|---|
| Impact | 30 | a real question (radiation-surviving tumours), measured honestly, with proofs of impossibility |
| Technical | 20 | exact solver, complete search, 82 tests, reproducible benchmark |
| Innovation | 15 | LLM proposes, solver proves, explanation re-checked; official H-MEM engine |
| Demo | 15 | the video: Explore, Search (with a proof of impossibility), Agent replay with SQL calls, Benchmark |
| Product UX | 10 | the UI (Explore, Search, Agent timeline with SQL calls, Benchmark, How it works) |
| Sponsor tech | 10 | Zetaris via REST + LLM-written SQL tool + JOIN; Nemotron; Meterless H-MEM; development tool statement |

## Done in the repo
- [x] Tests (`python -m pytest`), reproducible benchmark, honest README with limits and data provenance.
- [x] Nemotron through an OpenAI-compatible endpoint; Meterless endpoint supported through `METERLESS_API_KEY` and `METERLESS_BASE_URL`.
- [x] Zetaris as the data layer (`open_agent` database), the LLM's `run_sql` tool, and a SQL JOIN; the UI shows the data-layer chip.
- [x] Official Meterless H-MEM engine, vendored unmodified, conformance 13/13.
- [x] "How we built it" section in the README (the code was written with Claude Code; Cursor was not used and is not claimed).
- [x] `.env` is in `.gitignore`; no secret and no 28 MB platform zip in the history.
- [x] Every commit is dated 22 Oct 2026 or later (the two 21 Oct commits were dropped from the history, no dates were edited).

## You still need to do
1. **Push.** The local history was rewritten (the zip with local passwords is gone, the 21 Oct commits are gone), so it no
   longer matches what is on GitHub. Pick one:
   - keep the repository and overwrite its history: `git push --force-with-lease origin main`, or
   - cleanest (GitHub keeps old commits reachable by their hash until a repository is deleted): delete the repository on
     GitHub, create it again with the same name and the same public setting, then `git remote -v` (it should still point
     at it) and `git push -u origin main`.
   Then open the repository in a private window and check that `docs/submission/`, the README and the commit dates look right.
2. **HackOS:** claim the sponsor credits on the task board. If Meterless gives you a `METERLESS_BASE_URL` and key, put them
   in `.env` (the client switches to them automatically; that endpoint could not be tested without a key).
3. **Watch the video once, with sound** (`docs/submission/demo.mp4`) and upload it where the form asks (YouTube unlisted, Drive
   or Loom, whatever the form accepts). If you prefer your own voice, record it over `demo_silent.mp4`; the text is in
   `docs/submission/record_demo.py`.
4. **Upload the deck** (`deck.pdf`, or `deck.pptx` if the form wants PowerPoint).
5. **Fill the form:** repository URL `https://github.com/scoobydoobydrew/open-agent-hackathon`, track 02, the text from
   `docs/SPONSOR_WRITEUP.md`, the video and the deck.
6. Re-read the official rules at https://hackathon.genai.works (team names, what must be in the repo, anything the notes missed).

## Regenerating the submission material
```bash
bash scripts/zetaris_up.sh                 # the UI also does this itself; the chip must read "Zetaris"
(cd hmem/reference && npm install)         # once, for H-MEM
python -m pytest                           # expect all green
python ui/server.py                        # http://localhost:8765, leave it running
pip install playwright imageio-ffmpeg python-pptx
python docs/submission/capture_screens.py  # screenshots for the deck
python docs/submission/render_deck.py      # deck.pdf and slides/*.png
python docs/submission/build_pptx.py       # deck.pptx with notes
python docs/submission/record_demo.py      # demo.mp4 (Windows: Edge and the built-in voice)
```
Generated files (`shots/`, `slides/`, `deck.pptx`, `demo*.mp4`) are git-ignored; `deck.pdf` is kept in the repository.

## Let someone else check the setup
A judge who can run the repo in 5 minutes scores higher (per the notes). Test it on a clean checkout:
`git clone`, `python -m venv venv`, `pip install -r requirements.txt`, `cp .env.example .env`, `python -m pytest`,
`python ui/server.py`. Without Zetaris or an API key the UI still runs on the local CSV files and the recorded replays.
