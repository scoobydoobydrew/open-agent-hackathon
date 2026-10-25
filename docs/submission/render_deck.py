"""Render docs/submission/deck.html to slide PNGs and a PDF.

    python docs/submission/render_deck.py      (needs: pip install playwright; uses the installed Microsoft Edge)
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
OUT = HERE / "slides"
OUT.mkdir(exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge")
    pg = b.new_page(viewport={"width": 1920, "height": 1080})
    pg.goto((HERE / "deck.html").as_uri())
    pg.wait_for_timeout(800)
    for i in range(1, 8):
        pg.locator(f"#s{i}").screenshot(path=OUT / f"slide{i}.png")
    pg.pdf(path=HERE / "deck.pdf", width="1920px", height="1080px", print_background=True,
           margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
    b.close()
print("slides:", sorted(f.name for f in OUT.glob("*.png")), "pdf:", (HERE / "deck.pdf").stat().st_size // 1024, "KB")
