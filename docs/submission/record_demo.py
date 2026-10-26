"""Record the demo video: a scripted run of the real UI with captions and a synthetic voice-over.

    python ui/server.py                                  (in another terminal; the chip should read Zetaris)
    python docs/submission/record_demo.py                (needs: pip install playwright imageio-ffmpeg; Windows, uses Edge and
                                                         the built-in System.Speech voice)

Writes docs/submission/demo.mp4. The script is the narration text below; to use your own voice instead, record it over
the muted video (demo_silent.mp4) with the same text.
"""
import base64
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
WORK = HERE / "_video"
WORK.mkdir(exist_ok=True)
BASE = next((a for a in sys.argv[1:] if a.startswith("http")), "http://localhost:8765")
W, H = 1600, 900
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

OVERLAY_JS = """
(() => {
  const mk = () => {
    if (document.getElementById('__cap')) return;
    const cap = document.createElement('div'); cap.id = '__cap';
    cap.style.cssText = 'position:fixed;left:50%;bottom:26px;transform:translateX(-50%);max-width:1180px;padding:14px 26px;'
      + 'border-radius:16px;background:rgba(5,9,18,.88);border:1px solid rgba(34,211,238,.45);color:#f1f5ff;'
      + 'font:600 25px/1.35 "Segoe UI",Arial,sans-serif;text-align:center;z-index:99998;pointer-events:none;'
      + 'box-shadow:0 12px 40px rgba(0,0,0,.6);transition:opacity .25s;opacity:0';
    document.body.appendChild(cap);
    const dot = document.createElement('div'); dot.id = '__dot';
    dot.style.cssText = 'position:fixed;left:-50px;top:-50px;width:26px;height:26px;margin:-13px 0 0 -13px;border-radius:50%;'
      + 'border:3px solid #fff;background:rgba(34,211,238,.4);z-index:99999;pointer-events:none;box-shadow:0 0 14px rgba(34,211,238,.9)';
    document.body.appendChild(dot);
    document.addEventListener('mousemove', e => { dot.style.left = e.clientX + 'px'; dot.style.top = e.clientY + 'px'; }, true);
    document.addEventListener('mousedown', e => {
      const r = document.createElement('div');
      r.style.cssText = 'position:fixed;left:' + e.clientX + 'px;top:' + e.clientY + 'px;width:12px;height:12px;margin:-6px 0 0 -6px;'
        + 'border-radius:50%;border:3px solid #22d3ee;z-index:99999;pointer-events:none;transition:all .5s ease-out;opacity:1';
      document.body.appendChild(r);
      requestAnimationFrame(() => { r.style.width = '70px'; r.style.height = '70px'; r.style.margin = '-35px 0 0 -35px'; r.style.opacity = '0'; });
      setTimeout(() => r.remove(), 600);
    }, true);
  };
  document.addEventListener('DOMContentLoaded', mk); if (document.body) mk();
  window.__cap = t => { mk(); const c = document.getElementById('__cap'); c.textContent = t; c.style.opacity = t ? 1 : 0; };
})();
"""

# (key, caption, narration). Numbers in the narration are the ones on screen or in benchmark/RESULTS-nemotron-lightning.md.
SCRIPT = [
    ("intro", "An LLM proposes. An exact solver proves. The explanation is checked.",
     "A tumour cell can survive radiation, and the question is which genes to switch off so that it dies instead. "
     "This is for research teams who have to choose which knockouts to test, because every wrong guess is a wasted experiment. "
     "The Verified Knockout Agent lets a language model propose, an exact solver prove or refute every proposal, "
     "and checks every explanation against the rules. It runs on Zetaris, Meterless Nightshift with the official H-MEM engine, and NVIDIA Nemotron."),
    ("mdm2", "Explore: knock out MDM2. The cell still survives",
     "The model is a published bladder tumour network with thirty five genes. After radiation, this cell survives. "
     "Let's knock out MDM2. It does not help, and the solver returns the surviving state and names the genes that keep the cell alive."),
    ("tp53", "Knock out TP53: apoptosis is forced, with a checked proof",
     "Now TP53. Apoptosis is forced in every long term state of the cell, including oscillations. "
     "Each step of the proof is a rule of the model, and each one is re-checked. A selectivity check shows that a resting normal cell survives."),
    ("proof", "Complete search: \"No solution exists\" is a proof, not a failure to find one",
     "The search is complete: every failing set comes with a surviving state, and only the genes active in it can break it, so nothing is skipped. "
     "For a quiescent cell with no growth signal it runs until the queue is empty and reports that no solution exists. "
     "One hundred thirty nine solver calls, where brute force would check ten thousand nine hundred and three sets."),
    ("agent", "Live run: Zetaris SQL, H-MEM recall, Nemotron through Nightshift, verified solution",
     "Now the agent, live. Every request goes through Meterless Nightshift to NVIDIA Nemotron, and each line shows which model answered. "
     "First the model queries Zetaris with its own read only S Q L. Then the official H-MEM engine recalls what earlier rounds verified and puts it into the prompt. "
     "The solver answers each proposal with a counterexample, the search completes the job, and the result is a verified solution "
     "whose explanation steps are checked against the rules."),
    ("bench", "Measured on 8 scenarios against exhaustive ground truth",
     "We measured it. Without the solver, the language model's proposals are wrong ninety one percent of the time. "
     "With the solver and the complete search the system is never wrong, with thirty four times fewer solver calls than brute force, "
     "and ninety seven percent of the explanation steps stay inside the proof. On this network the search itself needs no language model; "
     "the value is verification, proofs of impossibility, and checked explanations."),
    ("end", "In-silico hypotheses on one published model: not medical advice. github.com/scoobydoobydrew/open-agent-hackathon",
     "These are in silico hypotheses on one published model, not medical advice, and they need lab and expert review. "
     "The code is open source on GitHub. Thank you."),
]


def check_provider() -> None:
    """The video must show a real request through Nightshift: refuse to record on a fallback or without an LLM."""
    import json
    import urllib.request
    meta = json.load(urllib.request.urlopen(BASE + "/api/meta", timeout=30))
    llm = meta["llm"]
    print("LLM status:", llm.get("provider"), llm.get("state"), llm.get("model"))
    if llm.get("provider") != "nightshift" and "--allow-fallback" not in sys.argv:
        raise SystemExit("Nightshift is not the active provider (" + str(llm.get("note")) + "). Start Nightshift, set "
                         "NIGHTSHIFT_TOKEN, restart ui/server.py, or pass --allow-fallback for a rehearsal.")


def tts(key: str, text: str) -> Path:
    txt, wav = WORK / f"{key}.txt", WORK / f"{key}.wav"
    txt.write_text(text, encoding="utf-8")
    ps = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Rate = -1; "
          f"$s.SetOutputToWaveFile('{wav}'); $s.Speak((Get-Content -Raw -Encoding UTF8 '{txt}')); $s.Dispose()")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    return wav


def wav_seconds(p: Path) -> float:
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


class Driver:
    def __init__(self, pg):
        self.pg = pg
        self.x, self.y = W / 2, H / 2

    def wait(self, s):
        self.pg.wait_for_timeout(int(s * 1000))

    def glide(self, x, y, steps=28):
        x0, y0 = self.x, self.y
        for i in range(1, steps + 1):
            t = i / steps
            t = t * t * (3 - 2 * t)
            self.pg.mouse.move(x0 + (x - x0) * t, y0 + (y - y0) * t)
            self.pg.wait_for_timeout(14)
        self.x, self.y = x, y

    def center(self, loc):
        loc.scroll_into_view_if_needed()
        b = loc.bounding_box()
        return b["x"] + b["width"] / 2, b["y"] + b["height"] / 2

    def click(self, loc, target=None):
        x, y = self.center(target if target is not None else loc)
        self.glide(x, y)
        self.wait(0.2)
        self.pg.mouse.click(x, y)
        self.wait(0.3)

    def hover(self, loc):
        x, y = self.center(loc)
        self.glide(x, y)

    def to_top(self):
        # the sticky header would otherwise cover the scenario chips and swallow the click
        self.pg.evaluate("window.scrollTo(0, 0)")
        self.wait(0.3)

    def tab(self, name):
        self.to_top()
        self.click(self.pg.locator("#tabs button", has_text=name).first)
        self.wait(0.5)

    def scenario(self, text):
        self.to_top()
        self.click(self.pg.locator("#scenario-bar button", has_text=text).first)
        self.wait(0.5)

    def node(self, gene):
        n = self.pg.locator("g.node", has_text=gene).first
        self.click(n, target=n.locator("circle").first)

    def caption(self, text):
        self.pg.evaluate("t => window.__cap(t)", text)


def run():
    check_provider()
    wavs = {k: tts(k, narr) for k, _, narr in SCRIPT}
    dur = {k: wav_seconds(p) for k, p in wavs.items()}
    print("narration seconds:", {k: round(v, 1) for k, v in dur.items()}, "total", round(sum(dur.values())))

    frames_dir = WORK / "frames"
    shutil.rmtree(frames_dir, ignore_errors=True)
    frames_dir.mkdir()
    frames = []                      # (timestamp in seconds, jpeg path)
    starts = {}                      # segment key -> wall-clock start
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        ctx = b.new_context(viewport={"width": W, "height": H})
        ctx.add_init_script(OVERLAY_JS)
        pg = ctx.new_page()
        cdp = ctx.new_cdp_session(pg)

        def on_frame(params):
            path = frames_dir / f"{len(frames):06d}.jpg"
            path.write_bytes(base64.b64decode(params["data"]))
            frames.append((params["metadata"]["timestamp"], path))
            cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})

        cdp.on("Page.screencastFrame", on_frame)
        cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 80, "maxWidth": W, "maxHeight": H, "everyNthFrame": 1})
        d = Driver(pg)
        pg.goto(BASE + "/#explore")
        pg.wait_for_timeout(1800)

        def seg(key, caption, actions):
            starts[key] = time.time()
            d.caption(caption)
            actions()
            left = dur[key] + 0.8 - (time.time() - starts[key])
            if left > 0:
                d.wait(left)

        def intro():
            d.scenario("FGFR3 · p53 wild-type")
            for sel in ("Data layer", "LLM", "Solver"):
                d.hover(pg.locator("header").get_by_text(sel, exact=True).first)
                d.wait(1.6)
            d.glide(W / 2, 600, 20)

        def mdm2():
            d.wait(6)
            d.node("MDM2")
            d.wait(4)

        def tp53():
            d.node("MDM2")      # un-knock MDM2
            d.node("TP53")
            d.wait(3)
            d.glide(1330, 650, 20)
            for _ in range(4):
                pg.mouse.wheel(0, 260)
                d.wait(1.8)

        def proof():
            d.tab("Search")
            d.scenario("Quiescent")
            pg.locator("#view-search select").select_option("4")
            d.click(pg.locator("#view-search button", has_text="16×").first)
            d.click(pg.locator("#view-search button", has_text="Run search").first)
            pg.get_by_text("No solution exists").wait_for(timeout=90000)
            d.wait(3)

        def agent():
            d.tab("Agent")
            d.scenario("EGF · p53 wild-type")
            d.hover(pg.locator("header").get_by_text("LLM", exact=True).first)
            d.wait(1.5)
            d.click(pg.locator("#view-agent button", has_text="Run live").first)      # mode switch
            d.click(pg.locator("#view-agent button", has_text="Run live").last)       # start: a real run, not a replay
            pg.get_by_text("Run finished").wait_for(timeout=300000)
            d.wait(1)
            tl = pg.locator("#view-agent .overflow-y-auto").first
            d.glide(520, 560, 20)
            tl.evaluate("e => e.scrollTop = 0")                                        # SQL calls, model per request, H-MEM recall
            d.wait(3)
            for _ in range(3):
                pg.mouse.wheel(0, 380)
                d.wait(3.5)
            pg.get_by_text("Run finished").scroll_into_view_if_needed()
            d.wait(3)

        def bench():
            d.tab("Benchmark")
            d.glide(W / 2, 560, 20)
            d.wait(17)                       # headline numbers stay in view while they are spoken
            for _ in range(3):
                pg.mouse.wheel(0, 420)
                d.wait(5)

        def end():
            d.tab("How it works")
            d.wait(2)

        acts = {"intro": intro, "mdm2": mdm2, "tp53": tp53, "proof": proof, "agent": agent, "bench": bench, "end": end}
        for key, cap, _ in SCRIPT:
            seg(key, cap, acts[key])
        d.caption("")
        d.wait(1.0)
        end_ts = time.time()
        cdp.send("Page.stopScreencast")
        b.close()

    # resample the (irregular) screencast frames to a constant 25 fps and encode
    t_first = frames[0][0]
    fps = 25
    total = int((end_ts - t_first) * fps)
    silent = HERE / "demo_silent.mp4"
    enc = subprocess.Popen([FFMPEG, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps), "-c:v", "mjpeg", "-i", "-",
                            "-vf", "scale=in_range=pc:out_range=tv,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "24", str(silent)], stdin=subprocess.PIPE)
    j, cur = 0, frames[0][1].read_bytes()
    for n in range(total):
        t = t_first + n / fps
        while j + 1 < len(frames) and frames[j + 1][0] <= t:
            j += 1
            cur = frames[j][1].read_bytes()
        enc.stdin.write(cur)
    enc.stdin.close()
    enc.wait()
    print("frames captured:", len(frames), "video seconds:", round(total / fps, 1))
    shutil.rmtree(frames_dir, ignore_errors=True)
    inputs, filt, labels = [], [], []
    for i, (key, _, _) in enumerate(SCRIPT, start=1):
        inputs += ["-i", str(wavs[key])]
        ms = int((starts[key] - t_first + 0.25) * 1000)
        filt.append(f"[{i}:a]adelay={ms}|{ms}[a{i}]")
        labels.append(f"[a{i}]")
    filt.append("".join(labels) + f"amix=inputs={len(SCRIPT)}:normalize=0[a]")
    out = HERE / "demo.mp4"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(silent), *inputs, "-filter_complex", ";".join(filt),
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", str(out)], check=True)
    print("wrote", out, out.stat().st_size // (1024 * 1024), "MB; starts:", {k: round(v, 1) for k, v in starts.items()})


if __name__ == "__main__":
    run()
