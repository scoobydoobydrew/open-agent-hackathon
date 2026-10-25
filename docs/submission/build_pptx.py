"""Build deck.pptx from the rendered slide images, with speaker notes.

    python docs/submission/render_deck.py     (first: writes slides/slide1..7.png)
    python docs/submission/build_pptx.py      (needs: pip install python-pptx)

The slides are pictures of deck.html, so the PDF is the faithful version; the .pptx exists for platforms that
only accept PowerPoint, and carries the speaker notes.
"""
from pathlib import Path

from pptx import Presentation
from pptx.util import Emu

HERE = Path(__file__).parent

NOTES = [
    "A tumour cell that survives radiation, and an LLM that proposes how to stop it. This is Track 02: the agent that "
    "can explain why. The idea in one line: an LLM proposes, an exact solver proves, and the explanation is checked.",
    "After radiation, a tumour with working p53 stops its cell cycle and repairs instead of dying. Which genes should "
    "we switch off so the cell commits to apoptosis? We asked Nemotron with no checker behind it, on eight scenarios "
    "with exhaustive ground truth: 91 percent of its proposals were wrong, and for the one scenario where no solution "
    "exists it invented one.",
    "Every claim goes through the solver. Zetaris holds the network rules, the scenarios and the drug evidence, and the "
    "LLM writes its own read-only SQL. Nemotron proposes knockouts with a rationale. The exact solver checks every "
    "long-term state, including oscillations, and returns a verdict or a counterexample. The complete search finds "
    "every minimal set or proves that none exists. The explanation is cut into steps and each step is re-checked "
    "against the rules. Official Meterless H-MEM keeps the memory, and passes the conformance suite 13 of 13.",
    "Why the search cannot miss: when a knockout fails, the solver returns the surviving state. Only genes that are "
    "active in that state can break it, so we extend the set only with them. Nothing is skipped, so either every "
    "minimal solution is found or the queue runs dry and impossibility is proved. That is 34 times fewer solver calls "
    "than brute force, and 56 calls to prove that no set of up to four genes works, where brute force needs 10,903.",
    "In the Explore tab you click a gene. Knocking out TP53 forces apoptosis in every long-term state, with numbered "
    "proof steps and a selectivity check against a resting normal cell. In the Agent tab you see the LLM proposals "
    "with their rationale, the counterexamples fed back, the search, and a verified solution with checked steps. "
    "These are real runs recorded against Zetaris and Nemotron; the replays work offline.",
    "What we measured, not promised. The LLM alone finds a valid minimal set in 26 percent of cases. With the solver "
    "and the search it is 100 percent and never wrong. The honest reading: on this network the search is symbolic "
    "and needs no LLM. The LLM gives the interface and the wording, and every claim it makes is checked. 97 percent "
    "of the explanation steps stayed inside the proof.",
    "Sponsor technology: Zetaris as the data layer with an LLM-written run_sql tool and a SQL join, Nemotron for "
    "proposals, SQL and explanations with thinking off after we measured 268 seconds against 2, and the official "
    "Meterless H-MEM engine, unmodified. Built with Claude Code. The limits: in-silico hypotheses on one published "
    "model, the solutions are loss of tumour suppressors so there is no drug, and the exact engine handles about 21 "
    "free nodes, so a 53-node model returned UNKNOWN and we say so. Next: a symbolic attractor backend, validation "
    "against published knockouts, and the same solver on other models. The takeaway: a system that proves what it "
    "claims, and says impossible when it is.",
]


def main() -> None:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)  # 16:9, 13.333 x 7.5 in
    blank = prs.slide_layouts[6]
    for i, note in enumerate(NOTES, start=1):
        slide = prs.slides.add_slide(blank)
        slide.shapes.add_picture(str(HERE / "slides" / f"slide{i}.png"), 0, 0, prs.slide_width, prs.slide_height)
        slide.notes_slide.notes_text_frame.text = note
    out = HERE / "deck.pptx"
    prs.save(out)
    print("wrote", out, out.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
