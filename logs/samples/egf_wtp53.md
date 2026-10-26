# Ranked knockout experiments: egf_wtp53

_EGF-driven tumour with wild-type p53 after radiation_

## 1. Knock out GRB2 + TP53  (NOT selective (also kills normal cells: normal_resting_rt); found by cegar)
- GRB2: druggable=limited, evidence=preclinical (SH2-domain inhibitors; antisense oligonucleotides)
- TP53: druggable=no, evidence=preclinical (pifithrin-alpha (research tool))

Knocking out GRB2 + TP53 forces committed apoptosis (Apoptosis_high=1) in every long-term state of this scenario. It is NOT selective: it also kills normal cells (normal_resting_rt). The 8 steps below are each checked against the model's update rules.

1. [verified] TP53 knockout forces p21CIP to zero, removing a growth inhibitor in the given scenario.  (TP53=0, Growth_inhibitors=0 => p21CIP=0)
2. [verified] With Growth_inhibitors absent, p16INK4a drops to zero per its regulatory rule.  (Growth_inhibitors=0 => p16INK4a=0)
3. [verified] RAS becomes active because EGFR is stimulated in the scenario.  (RAS=1 => SPRY=1)
4. [verified] CyclinD1 turns on as p21CIP and p16INK4a are both zero and RAS is present.  (FGFR3_stimulus=0 => FGFR3=0)
5. [mentions RB1] RBL2 and RB1 are inactivated because CyclinD1 is present.  (SPRY=1, GRB2=0, FGFR3=0 => EGFR=1)
6. [mentions E2F1_high, RB1] E2F1_high becomes active due to the combined loss of RBL2 and RB1 together with RAS.  (EGFR=1 => RAS=1)
7. [mentions E2F1_high, E2F1_medium] E2F1_medium is maintained because E2F1_high is present.  (p21CIP=0, p16INK4a=0, RAS=1 => CyclinD1=1)
8. [mentions Apoptosis_medium, E2F1_high, E2F1_medium] Apoptosis_medium is triggered by the presence of both E2F1_medium and E2F1_high.  (CyclinD1=1 => RBL2=0)

Explanation check: 4/8 steps verified against the model rules

Caveats: The model assumes the given scenario rules and knockout constraints; other network interactions are not represented.

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

## 2. Knock out GRB2 + p21CIP  (NOT selective (also kills normal cells: normal_resting_rt); found by cegar)
- GRB2: druggable=limited, evidence=preclinical (SH2-domain inhibitors; antisense oligonucleotides)
- p21CIP: druggable=no, evidence=none

Knocking out GRB2 + p21CIP forces committed apoptosis (Apoptosis_high=1) in every long-term state of this scenario. It is NOT selective: it also kills normal cells (normal_resting_rt). The 8 steps below are each checked against the model's update rules.

1. [verified] FGFR3 is set to 0 because FGFR3_stimulus is 0 in the scenario.  (FGFR3_stimulus=0 => FGFR3=0)
2. [verified] EGFR becomes 1 because SPRY is 1, GRB2 is 0, and FGFR3 is 0.  (SPRY=1, GRB2=0, FGFR3=0 => EGFR=1)
3. [verified] RAS becomes 1 because EGFR is 1.  (EGFR=1 => RAS=1)
4. [verified] CyclinD1 becomes 1 because p21CIP is 0, p16INK4a is 0, and RAS is 1.  (p21CIP=0, p16INK4a=0, RAS=1 => CyclinD1=1)
5. [verified] RB1 becomes 0 because CyclinD1 is 1.  (CyclinD1=1 => RB1=0)
6. [verified] E2F1_high becomes 1 because RBL2 is 0, RB1 is 0, RAS is 1, E2F1_medium is 1, CHEK1_2_medium is 1, CHEK1_2_high is 1, ATM_medium is 1, and ATM_high is 1.  (RBL2=0, RB1=0, RAS=1, E2F1_medium=1, CHEK1_2_medium=1, CHEK1_2_high=1, ATM_medium=1, ATM_high=1 => E2F1_high=1)
7. [verified] TP53 becomes 1 because MDM2 is 0, E2F1_medium is 1, and E2F1_high is 1.  (MDM2=0, E2F1_medium=1, E2F1_high=1 => TP53=1)
8. [verified] Apoptosis_medium becomes 1 because TP53 is 1.  (TP53=1 => Apoptosis_medium=1)

Explanation check: 8/8 steps verified against the model rules

Caveats: The solver's fixed knockout set ['GRB2', 'p21CIP'] and scenario assumptions drive these causal links; other network states may differ.

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
    TP53 = 1
      MDM2 = 0
        p14ARF = 1
          E2F1_medium = 1  (see above)
      E2F1_medium = 1  (see above)
      E2F1_high = 1  (see above)
```

## 3. Knock out GRB2 + RB1 + RBL2  (NOT selective (also kills normal cells: normal_resting_rt); found by cegar)
- GRB2: druggable=limited, evidence=preclinical (SH2-domain inhibitors; antisense oligonucleotides)
- RB1: druggable=no, evidence=none
- RBL2: druggable=no, evidence=none

Knocking out GRB2 + RB1 + RBL2 forces committed apoptosis (Apoptosis_high=1) in every long-term state of this scenario. It is NOT selective: it also kills normal cells (normal_resting_rt). The 8 steps below are each checked against the model's update rules.

1. [verified] FGFR3 is set to 0 because the scenario has no FGFR3 stimulus.  (FGFR3_stimulus=0 => FGFR3=0)
2. [verified] EGFR becomes 1 because SPRY is 1, GRB2 is knocked out, and FGFR3 is 0.  (SPRY=1, GRB2=0, FGFR3=0 => EGFR=1)
3. [verified] RAS becomes 1 because EGFR is 1.  (EGFR=1 => RAS=1)
4. [verified] ATM_medium becomes 1 because DNA damage is present in the scenario.  (DNA_damage=1 => ATM_medium=1)
5. [verified] CHEK1_2_medium becomes 1 because ATM_medium is 1.  (ATM_medium=1 => CHEK1_2_medium=1)
6. [verified] CHEK1_2_high becomes 1 because E2F1_medium, CHEK1_2_medium, and ATM_medium are all 1.  (E2F1_medium=1, CHEK1_2_medium=1, ATM_medium=1 => CHEK1_2_high=1)
7. [verified] ATM_high becomes 1 because E2F1_medium, DNA damage, and ATM_medium are 1.  (E2F1_medium=1, DNA_damage=1, ATM_medium=1 => ATM_high=1)
8. [verified] E2F1_high becomes 1 because RBL2 and RB1 are knocked out, RAS is 1, E2F1_medium, CHEK1_2_medium, CHEK1_2_high, ATM_medium, and ATM_high are 1.  (RBL2=0, RB1=0, RAS=1, E2F1_medium=1, CHEK1_2_medium=1, CHEK1_2_high=1, ATM_medium=1, ATM_high=1 => E2F1_high=1)

Explanation check: 8/8 steps verified against the model rules

Caveats: The solver proved apoptosis in every long-term state with the knockout set, but these steps only trace the causal chain to E2F1_high.

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
        EGFR = 1
          SPRY = 1
            RAS = 1  (see above)
          GRB2 = 0  [knockout]
          FGFR3 = 0
            FGFR3_stimulus = 0  [scenario]
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
model nvidia/nemotron-3.5-lightning-30b-a3b | data layer zetaris | memory session | rounds 4 | solver calls 399 (search 389, replayed from memory 175) | LLM calls 8 via nightshift (nvidia/nemotron-3.5-lightning-30b-a3b) | tokens 23739 | 33.8s
