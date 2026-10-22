# Neuro-Symbolic Agent for Biological Regulatory Networks & Apoptosis Verification

Ερευνητικό και υπολογιστικό σύστημα (Neuro-Symbolic Agent) για την ανάλυση δικτύων απόκρισης σε βλάβες DNA (p53/ATM), την επίλυση NP-hard προβλημάτων συνδυαστικής βιολογίας και τον εντοπισμό ελάχιστων παρεμβάσεων (minimal knockout sets) που οδηγούν καρκινικά κύτταρα ανθεκτικά στην ακτινοθεραπεία σε απόπτωση[cite: 5].

---

## 1. Problem Statement & Scientific Rationale

* **Το Πρόβλημα:** Τα κύτταρα με ανθεκτικότητα στην ακτινοθεραπεία επιβιώνουν της θεραπείας[cite: 5]. Ο πειραματικός εντοπισμός των γονιδίων που πρέπει να απενεργοποιηθούν (knockout) μέσω brute-force εργαστηριακών δοκιμών είναι εξαιρετικά αργός και κοστοβόρος[cite: 5].
* **Μαθηματική Πολυπλοκότητα:** Σε ένα μοντέλο Boolean δικτύου για το μονοπάτι p53/ATM με $N$ κόμβους, ο χώρος των δυνατών καταστάσεων είναι $2^N$[cite: 5]. Η εύρεση minimal intervention sets αποτελεί NP-hard πρόβλημα στο οποίο η μέθοδος brute force αποτυγχάνει[cite: 5].
* **Το Κενό των LLMs:** Τα κλασικά μοντέλα γλώσσας μόνα τους αδυνατούν να εγγυηθούν ορθότητα σε εκθετικούς χώρους καταστάσεων και παράγουν ψευδείς συσχετίσεις[cite: 5]. Αντίστοιχα, οι τυπικοί solvers μόνοι τους μπορούν να επαληθεύσουν κανόνες, αλλά δεν μπορούν να προτείνουν νέες βιολογικές υποθέσεις από τη βιβλιογραφία[cite: 5].
* **Στόχος Έργου:** Παραγωγή μιας ιεραρχημένης λίστας πειραμάτων υψηλής αξίας (ranked list of experiments worth running) με μαθηματική απόδειξη ορθότητας και όχι αυθαίρετων κλινικών ισχυρισμών[cite: 5].

---

## 2. Architecture: Counterexample-Guided Abstraction Refinement (CEGAR)

Το σύστημα υλοποιεί έναν κλειστό βρόχο επαλήθευσης και διόρθωσης (CEGAR Loop)[cite: 5]:

```text
       ┌────────────────────────────────────────────────────────┐
       │                Data Layer (Zetaris)                    │
       │    - known_phenotypes.csv | p53_interactions.csv       │
       └──────────────────────────┬─────────────────────────────┘
                                  │ SQL Queries (REST / JDBC)
                                  ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │                     Reasoning Agent (LLM)                        │
 │  - Διαβάζει βιολογικά δεδομένα & βιβλιογραφία                   │
 │  - Προτείνει νέους ρυθμιστικούς Boolean κανόνες                  │
 └─────────────────┬──────────────────────────────▲─────────────────┘
                   │ Candidate Rules               │ Counterexamples
                   ▼                               │ (UNSAT Phenotype)
 ┌─────────────────────────────────────────────────┴────────────────┐
 │             Formal Solvers (pyboolnet + Z3 / clingo)             │
 │  - Επαλήθευση ενάντια σε wild-type & mutant φαινότυπα            │
 │  - Υπολογισμός attractors (Apoptosis vs. Survival)               │
 │  - Εύρεση minimal knockout sets                                  │
 └──────────────────────────────────────────────────────────────────┘
```

1. **Information Retrieval:** Ο Agent εκτελεί SQL queries στη Zetaris και αντλεί δεδομένα γνωστών φαινοτύπων και αλληλεπιδράσεων[cite: 5].
2. **Rule Synthesis:** Το LLM προτείνει τροποποιημένους ή νέους ρυθμιστικούς κανόνες για το δίκτυο p53/ATM[cite: 5].
3. **Formal Verification:** Ο solver (`pyboolnet` + `Z3`/`clingo`) ελέγχει αν το δίκτυο ικανοποιεί όλα τα γνωστά πειραματικά δεδομένα (wild-type και mutants)[cite: 5]:
   * **SAT:** Το μοντέλο επαληθεύεται και χρησιμοποιείται για την εύρεση του ελάχιστου knockout set που εξαναγκάζει τα ανθεκτικά κύτταρα σε απόπτωση[cite: 5].
   * **UNSAT:** Ο solver επιστρέφει αντίπαραδειγμα (counterexample) με τον φαινότυπο που παραβιάζεται[cite: 5].
4. **Self-Correction:** Το LLM αναλύει το counterexample και αναδιατυπώνει τη λογική συνάρτηση[cite: 5].

---

## 3. Technology Stack & Integration Requirements

### Open Agent Hackathon 2026 (GenAI Works / HackOS)
* **Team:** `cache me if u can` (Solo entry: Andreas Petros Rigoutsos)[cite: 3, 4]
* **Target Track:** Track 02 (The Agent That Can Explain Why) / Track 03 (Reasoning Architecture)
* **Build Window:** 22 Οκτωβρίου 2026 (00:00 UTC) έως 27 Οκτωβρίου 2026 (23:45 UTC)[cite: 3]
* **Data Layer (Zetaris Local Engine):**
  * Τοπική εκτέλεση μέσω Docker στο `/mnt/c/Users/Master/Desktop/zetaris-platform`.
  * Web UI διαχείρισης: `http://localhost:3000` (Credentials: `admin@zetaris.com` / `<default password from the Zetaris setup guide>`)[cite: 10].
  * REST API Query Endpoint: `http://localhost:8888`.
  * Ingestion: Αποθήκευση CSV αρχείων στον φάκελο `customer_data/` και δήλωση ως Data Sources στο UI[cite: 10].
* **Power Layer (NVIDIA Nemotron via Meterless):**
  * LLM Reasoning Engine για σύνθεση κανόνων και διαχείριση του reflection loop.
* **Build Layer (Cursor):**
  * Κύριο περιβάλλον ανάπτυξης (Composer / multi-file editing) με επιλογή μοντέλου Claude 3.5 Sonnet.
* **Verification Layer:**
  * `z3-solver`, `pyboolnet`, `clingo`[cite: 5].

---

### Meta Global AI Developer Hackathon (Cerebral Valley & Meta)
* **Status:** **APPROVED!**[cite: 6]
* **Διάρκεια:** 26 Οκτωβρίου 2026 (12:00 PM GMT-5) έως 4 Νοεμβρίου 2026 (9:00 PM GMT-5)[cite: 6]
* **Αποσύζευξη (Modular Portability):**
  * Ο πυρήνας των Solvers (`solver/`) παραμένει εντελώς ανεξάρτητος[cite: 5].
  * Στο `agent/llm.py`, η διασύνδεση του μοντέλου μεταφέρεται στο Meta Model API (Muse Spark / Llama 3)[cite: 5].

---

## 4. Repository Structure

```text
.
├── agent/
│   ├── __init__.py
│   ├── main.py              # CEGAR Orchestrator / Reflection Loop
│   ├── llm.py               # Interface για Nemotron (Open Agent) / Meta Model API
│   ├── prompts.py           # Prompts σύνθεσης κανόνων & διαχείρισης counterexamples
│   └── tools_zetaris.py     # SQL Tool για επικοινωνία με Zetaris REST API
├── solver/
│   ├── __init__.py
│   ├── verifier.py          # Z3 SAT/UNSAT verification & counterexample generation
│   ├── boolean_net.py       # pyboolnet wrapper για attractor analysis
│   └── knockout_opt.py      # Minimal intervention set optimization
├── data/
│   ├── known_phenotypes.csv # Wild-type & mutant φαινότυποι από τη βιβλιογραφία
│   └── p53_interactions.csv # Αρχικές αλληλεπιδράσεις του δικτύου p53/ATM
├── tests/
│   ├── smoke_test.py        # Επαλήθευση σύνδεσης Zetaris, Meterless, Z3
│   └── test_solver.py       # Unit tests λειτουργίας solver
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 5. Development & Setup

### Προαπαιτούμενα
* Python 3.10+
* Docker Desktop & WSL2
* Zetaris Platform (ενεργό container stack στο παρασκήνιο)[cite: 10]

### Ρύθμιση Περιβάλλοντος
1. Δημιουργία αρχείου μεταβλητών περιβάλλοντος:
   ```bash
   cp .env.example .env
   ```
2. Ορισμός παραμέτρων στο `.env`:
   ```ini
   # Meterless / NVIDIA Nemotron
   METERLESS_BASE_URL="[https://api.meterless.ai/v1](https://api.meterless.ai/v1)"
   METERLESS_API_KEY="your_meterless_api_key_here"
   NEMOTRON_MODEL="nvidia/nemotron-4-340b-instruct"

   # Zetaris Configuration
   ZETARIS_REST_URL="http://localhost:8888/api/v1/query"
   ZETARIS_USER="admin@zetaris.com"
   ZETARIS_PASS="<default password from the Zetaris setup guide>"
   ```
3. Εγκατάσταση βιβλιοθηκών:
   ```bash
   pip install -r requirements.txt
   ```
4. Έλεγχος συνδεσιμότητας:
   ```bash
   python tests/smoke_test.py
   ```

---

## 6. Deliverables & Benchmarks Checklist

### Open Agent Hackathon (Deadline: 27 Οκτ, 23:45 UTC)[cite: 3]
* [ ] Task Board: Ολοκλήρωση των σταδίων στο HackOS[cite: 4, 7]
* [ ] Commits εντός του επίσημου Build Window (22–27 Οκτωβρίου)[cite: 3]
* [ ] Τεκμηρίωση χρήσης των **Zetaris**, **Meterless**, **Cursor**
* [ ] Demo Video (1–4 λεπτά): Παρουσίαση του CEGAR loop και ζωντανή εκτέλεση του agent
* [ ] Pitch Deck (5–7 διαφάνειες): Μαθηματικό υπόβαθρο και εξαγωγή minimal knockouts

### Meta Global AI Developer Hackathon (26 Οκτ – 4 Νοε)[cite: 6]
* [ ] Ενσωμάτωση Meta Model API / Llama 3 στο `agent/llm.py`[cite: 5]
* [ ] Benchmark αξιολόγησης: Σύγκριση ακρίβειας LLM-only vs. LLM + Solver στην αναπαραγωγή knockouts από held-out βιβλιογραφία[cite: 5]
