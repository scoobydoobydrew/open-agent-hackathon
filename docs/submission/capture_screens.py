"""Capture high-resolution screenshots of the running UI for the deck (python docs/submission/capture_screens.py)."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / "shots"
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765"


def tab(pg, name):
    pg.locator("#tabs button", has_text=name).first.click()
    pg.wait_for_timeout(500)


def scenario(pg, text):
    pg.locator("#scenario-bar button", has_text=text).first.click()
    pg.wait_for_timeout(500)


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge")
    pg = b.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=1.5)
    pg.goto(BASE + "/#explore"); pg.wait_for_timeout(2500)
    pg.locator("g.node", has_text="TP53").first.click(); pg.wait_for_timeout(2500)
    pg.screenshot(path=OUT / "explore_forced.png")
    pg.locator("g.node", has_text="TP53").first.click(); pg.wait_for_timeout(300)
    pg.locator("g.node", has_text="MDM2").first.click(); pg.wait_for_timeout(2500)
    pg.screenshot(path=OUT / "explore_survives.png")

    tab(pg, "Search"); scenario(pg, "EGF · p53 wild-type")
    pg.locator("#view-search button", has_text="⚡").first.click()
    pg.locator("#view-search button", has_text="Run search").first.click()
    pg.get_by_text("minimal solution(s) found").wait_for(timeout=60000); pg.wait_for_timeout(800)
    pg.screenshot(path=OUT / "search_tree.png")
    scenario(pg, "Quiescent")
    pg.locator("#view-search button", has_text="Run search").first.click()
    pg.get_by_text("No solution exists").wait_for(timeout=60000); pg.wait_for_timeout(800)
    pg.screenshot(path=OUT / "search_proof.png")

    tab(pg, "Agent"); scenario(pg, "FGFR3 · p53 wild-type")
    pg.locator("#view-agent button", has_text="Replay recorded run").last.click()
    pg.get_by_text("Skip animation").click()
    pg.get_by_text("Run finished").wait_for(timeout=120000); pg.wait_for_timeout(1000)
    tl = pg.locator("#view-agent .overflow-y-auto").first
    tl.evaluate("e => e.scrollTop = 0"); pg.wait_for_timeout(600)
    pg.screenshot(path=OUT / "agent_sql.png")
    sol = pg.get_by_text("Verified solution #1").first
    sol.scroll_into_view_if_needed(); tl.evaluate("e => e.scrollTop += 0"); pg.wait_for_timeout(600)
    pg.screenshot(path=OUT / "agent_solution.png")
    pg.get_by_text("H-MEM recalled").first.scroll_into_view_if_needed(); pg.wait_for_timeout(600)
    pg.screenshot(path=OUT / "agent_nightshift.png")        # LLM request lines (provider and model) and the H-MEM recall

    tab(pg, "Benchmark"); pg.wait_for_timeout(1500)
    pg.screenshot(path=OUT / "benchmark.png")
    tab(pg, "How it works"); pg.wait_for_timeout(800)
    pg.screenshot(path=OUT / "how.png")
    b.close()
print("captured:", sorted(f.name for f in OUT.glob("*.png")))
