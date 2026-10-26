# Ranked knockout experiments: egf_tp53null

_EGF-driven tumour that has lost TP53, after radiation_

## 1. Knock out GRB2  (selective; found by cegar)
- GRB2: druggable=limited, evidence=preclinical (SH2-domain inhibitors; antisense oligonucleotides)

Knocking out GRB2 forces committed apoptosis (Apoptosis_high=1) in every long-term state of this scenario. The knockout is selective: a resting normal cell exposed to the same radiation survives. The 8 steps below are each checked against the model's update rules.

1. [verified] FGFR3 is set to 0 because its stimulus is absent and GRB2 is knocked out.  (FGFR3_stimulus=0 => FGFR3=0)
2. [verified] EGFR becomes 1 because SPRY is 1, GRB2 is absent, and FGFR3 is 0.  (SPRY=1, GRB2=0, FGFR3=0 => EGFR=1)
3. [verified] RAS becomes 1 because EGFR is 1.  (EGFR=1 => RAS=1)
4. [verified] CyclinD1 becomes 1 because p21CIP is 0, p16INK4a is 0, and RAS is 1.  (p21CIP=0, p16INK4a=0, RAS=1 => CyclinD1=1)
5. [verified] RBL2 becomes 0 because CyclinD1 is 1.  (CyclinD1=1 => RBL2=0)
6. [verified] RB1 becomes 0 because CyclinD1 is 1.  (CyclinD1=1 => RB1=0)
7. [verified] E2F1_high becomes 1 because RBL2 is 0, RB1 is 0, RAS is 1, E2F1_medium is 1, CHEK1_2_medium is 1, CHEK1_2_high is 1, ATM_medium is 1, and ATM_high is 1.  (RBL2=0, RB1=0, RAS=1, E2F1_medium=1, CHEK1_2_medium=1, CHEK1_2_high=1, ATM_medium=1, ATM_high=1 => E2F1_high=1)
8. [verified] Apoptosis_medium becomes 1 because E2F1_medium is 1 and E2F1_high is 1.  (E2F1_medium=1, E2F1_high=1 => Apoptosis_medium=1)

Explanation check: 8/8 steps verified against the model rules

Caveats: The model assumes Boolean logic and does not capture continuous dynamics or all biological feedbacks.

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
model nvidia/nemotron-3.5-lightning-30b-a3b | data layer zetaris | memory session | rounds 1 | solver calls 43 (search 37, replayed from memory 3) | LLM calls 3 via nightshift (nvidia/nemotron-3.5-lightning-30b-a3b) | tokens 5862 | 16.0s
