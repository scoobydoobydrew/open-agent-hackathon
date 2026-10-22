# Project Context: Neuro-Symbolic Agent for Biological Knockouts

## Overview
We are building a Neuro-Symbolic AI Agent for the Open Agent Hackathon 2026. The goal is to identify minimal knockout sets in the p53 DNA damage response Boolean network to force radiation-resistant cancer cells into apoptosis.

We use a CEGAR (Counterexample-Guided Abstraction Refinement) loop:
1. **LLM (NVIDIA Nemotron):** Proposes gene knockouts based on biological context.
2. **Solver (Z3 / pyboolnet):** Mathematically verifies if the proposed knockout forces the cell to the apoptosis attractor state. If it fails, it returns a counterexample.
3. **Refinement:** The LLM reads the counterexample and proposes a new knockout.

## Hackathon Sponsor Requirements & Tech Stack
- **AI Model:** NVIDIA Nemotron (`nvidia/nemotron-3.5-lightning-30b-a3b` or `nemotron-3-ultra-550b-a55b`) via direct REST API calls (API Key is in `.env`).
- **Data Layer (Zetaris):** We have a local Zetaris Docker instance (`http://localhost:8888/api/v1/query`). The agent must fetch the biological network rules (CSV data) using SQL queries via Zetaris REST API.
- **Agent Engine (Meterless):** We MUST implement the **H-MEM (Memory)** engine. It will be used to store the history of failed knockouts (counterexamples) so the LLM Agent remembers what hasn't worked and refines its next guess.

## Project Structure
```text
.
├── agent/
│   ├── main.py              # CEGAR Orchestrator (Loop)
│   ├── llm.py               # API calls to NVIDIA Nemotron
│   ├── memory.py            # Meterless H-MEM implementation for storing counterexamples
│   └── tools_zetaris.py     # SQL Tool for Zetaris REST API
├── solver/
│   ├── verifier.py          # Z3 SAT/UNSAT verification logic
│   └── boolean_net.py       # p53 network logical rules mapping
├── data/
│   └── p53_network.csv      # (To be created) Mock data for Zetaris ingestion
├── tests/
│   └── smoke_test.py        # Already passing (NVIDIA API is verified)
├── .env                     # Contains NVIDIA_API_KEY, ZETARIS_URL, etc.
└── requirements.txt
```



