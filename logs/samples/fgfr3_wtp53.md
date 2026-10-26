# Ranked knockout experiments: fgfr3_wtp53

_FGFR3-driven tumour with wild-type p53 after radiation_

## 1. Knock out TP53  (selective; found by cegar)
- TP53: druggable=no, evidence=preclinical (pifithrin-alpha (research tool))

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
            TP53 = 0  [knockout]
            Growth_inhibitors = 0  [scenario]
          p16INK4a = 0
            Growth_inhibitors = 0  [scenario]
          RAS = 1
            FGFR3 = 1
              GRB2 = 0
                SPRY = 1  (chain cut here)
                EGFR = 0  (chain cut here)
              FGFR3_stimulus = 1  [scenario]
              EGFR = 0  (see above)
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

## 2. Knock out p21CIP  (selective; found by cegar)
- p21CIP: druggable=no, evidence=none

Solver derivation (why apoptosis holds):
```
Attractor 1 (fixed, 1 state(s)):
Apoptosis_high = 1
  E2F1_medium = 1
    E2F1_medium = 1  (see above)
    E2F1_high = 1
      RBL2 = 0
        CyclinD1 = 1
          p21CIP = 0  [knockout]
          p16INK4a = 0
            Growth_inhibitors = 0  [scenario]
          RAS = 1
            FGFR3 = 1
              GRB2 = 0
                SPRY = 1  (chain cut here)
                EGFR = 0  (chain cut here)
              FGFR3_stimulus = 1  [scenario]
              EGFR = 0  (see above)
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
    TP53 = 1
      MDM2 = 0
        p14ARF = 1
          E2F1_medium = 1  (see above)
      E2F1_medium = 1  (see above)
      E2F1_high = 1  (see above)
```

## 3. Knock out RB1 + RBL2  (selective; found by cegar)
- RB1: druggable=no, evidence=none
- RBL2: druggable=no, evidence=none

Solver derivation (why apoptosis holds):
```
Attractor 1 (fixed, 1 state(s)):
Apoptosis_high = 1
  E2F1_medium = 1
    E2F1_medium = 1  (see above)
    E2F1_high = 1
      RBL2 = 0  [knockout]
      RB1 = 0  [knockout]
      RAS = 1
        FGFR3 = 1
          GRB2 = 0
            SPRY = 1
              RAS = 1  (see above)
            EGFR = 0
              FGFR3 = 1  (see above)
          FGFR3_stimulus = 1  [scenario]
          EGFR = 0  (see above)
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
    TP53 = 1
      MDM2 = 0
        p14ARF = 1
          E2F1_medium = 1  (see above)
      E2F1_medium = 1  (see above)
      E2F1_high = 1  (see above)
```

---
model none | data layer local-csv (zetaris unavailable: SAMPLE_MODE is on) | memory session | rounds 2 | solver calls 55 (search 48, replayed from memory 6) | LLM calls 0 via none (no model) | tokens 0 | 0.5s
