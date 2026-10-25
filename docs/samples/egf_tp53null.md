# Ranked knockout experiments: egf_tp53null

_EGF-driven tumour that has lost TP53, after radiation_

## 1. Knock out GRB2  (selective; found by cegar)
- GRB2: druggable=limited, evidence=preclinical (SH2-domain inhibitors; antisense oligonucleotides)

Solver derivation (why apoptosis holds):
```
Attractor 1 (fixed, 1 state(s)):
Apoptosis_high = 1
  E2F1_medium = 1
    E2F1_medium = 1  (see above)
    E2F1_high = 1
      RBL2 = 0
        CyclinD1 = 1
          p21CIP = 0
            TP53 = 0  [scenario]
            Growth_inhibitors = 0  [scenario]
          p16INK4a = 0
            Growth_inhibitors = 0  [scenario]
          RAS = 1
            EGFR = 1
              SPRY = 1
                RAS = 1  (see above)
              GRB2 = 0  [knockout]
              FGFR3 = 0
                FGFR3_stimulus = 0  [scenario]
      RB1 = 0
        CyclinD1 = 1  (see above)
      RAS = 1  (see above)
      E2F1_medium = 1  (see above)
      CHEK1_2_medium = 1
        ATM_medium = 1
          DNA_damage = 1  [scenario]
      CHEK1_2_high = 1
        E2F1_medium = 1  (see above)
        CHEK1_2_medium = 1  (see above)
        ATM_medium = 1  (see above)
      ATM_medium = 1  (see above)
      ATM_high = 1
        E2F1_medium = 1  (see above)
        DNA_damage = 1  [scenario]
        ATM_medium = 1  (see above)
  E2F1_high = 1  (see above)
  Apoptosis_medium = 1
    E2F1_medium = 1  (see above)
    E2F1_high = 1  (see above)
```

---
model none | data layer local-csv (zetaris unavailable: SAMPLE_MODE is on) | memory session | rounds 4 | solver calls 324 (search 321, replayed from memory 244) | LLM calls 0 via none (no model) | tokens 0 | 2.3s
