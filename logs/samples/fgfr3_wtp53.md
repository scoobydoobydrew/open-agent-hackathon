# Ranked knockout experiments: fgfr3_wtp53

_FGFR3-driven tumour with wild-type p53 after radiation_

## 1. Knock out TP53  (selective; found by cegar)
- TP53: druggable=no, evidence=preclinical (pifithrin-alpha (research tool))

Knocking out TP53 forces committed apoptosis (Apoptosis_high=1) in every long-term state of this scenario. The knockout is selective: a resting normal cell exposed to the same radiation survives. The 8 steps below are each checked against the model's update rules.

1. [verified] TP53 knockout eliminates p21CIP, removing a growth inhibitor and allowing proliferation.  (TP53=0, Growth_inhibitors=0 => p21CIP=0)
2. [verified] With EGFR absent and SPRY present, GRB2 is inactive, leaving FGFR3 signaling unopposed.  (SPRY=1, EGFR=0 => GRB2=0)
3. [verified] FGFR3 remains active because GRB2 is inactive and the FGFR3 stimulus is present, while EGFR is absent.  (GRB2=0, FGFR3_stimulus=1, EGFR=0 => FGFR3=1)
4. [verified] RAS becomes active due to the presence of active FGFR3.  (FGFR3=1 => RAS=1)
5. [verified] CyclinD1 is expressed because p21CIP and p16INK4a are inactive and RAS is active.  (p21CIP=0, p16INK4a=0, RAS=1 => CyclinD1=1)
6. [verified] RBL2 is inactivated because CyclinD1 is present, relieving inhibition on E2F transcription factors.  (CyclinD1=1 => RBL2=0)
7. [verified] E2F1 becomes highly active because RBL2 and RB1 are inactive, RAS is active, and the DNA damage response is engaged.  (RBL2=0, RB1=0, RAS=1, E2F1_medium=1, CHEK1_2_medium=1, CHEK1_2_high=1, ATM_medium=1, ATM_high=1 => E2F1_high=1)
8. [verified] Apoptosis at the medium level is triggered because E2F1 is both medium and high active.  (E2F1_medium=1, E2F1_high=1 => Apoptosis_medium=1)

Explanation check: 8/8 steps verified against the model rules

Caveats: The model assumes wild-type p53 context; the verified knockout set ['TP53'] indicates the solver proved apoptosis in every long-term state under that condition.

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

Knocking out p21CIP forces committed apoptosis (Apoptosis_high=1) in every long-term state of this scenario. The knockout is selective: a resting normal cell exposed to the same radiation survives. The 8 steps below are each checked against the model's update rules.

1. [verified] FGFR3 becomes active because GRB2 is absent and FGFR3 is stimulated, with EGFR inactive.  (GRB2=0, FGFR3_stimulus=1, EGFR=0 => FGFR3=1)
2. [verified] RAS becomes active because FGFR3 is active.  (FGFR3=1 => RAS=1)
3. [verified] CyclinD1 becomes active because p21CIP is knocked out, p16INK4a is absent, and RAS is active.  (p21CIP=0, p16INK4a=0, RAS=1 => CyclinD1=1)
4. [verified] RBL2 becomes inactive because CyclinD1 is active.  (CyclinD1=1 => RBL2=0)
5. [verified] RB1 becomes inactive because CyclinD1 is active and p16INK4a is absent.  (CyclinD1=1 => RB1=0)
6. [verified] E2F1 becomes highly active because RBL2 and RB1 are inactive, RAS is active, and CHEK1/2 medium/high and ATM medium/high are present.  (RBL2=0, RB1=0, RAS=1, E2F1_medium=1, CHEK1_2_medium=1, CHEK1_2_high=1, ATM_medium=1, ATM_high=1 => E2F1_high=1)
7. [verified] TP53 becomes active because MDM2 is inactive, E2F1 medium, and E2F1 high are present.  (MDM2=0, E2F1_medium=1, E2F1_high=1 => TP53=1)
8. [verified] Apoptosis high becomes active because E2F1 medium, E2F1 high, and Apoptosis medium are present.  (E2F1_medium=1, E2F1_high=1, Apoptosis_medium=1 => Apoptosis_high=1)

Explanation check: 8/8 steps verified against the model rules

Caveats: The model assumes the given knockout and scenario conditions hold; other network interactions are not described.

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

Knocking out RB1 + RBL2 forces committed apoptosis (Apoptosis_high=1) in every long-term state of this scenario. The knockout is selective: a resting normal cell exposed to the same radiation survives. The 8 steps below are each checked against the model's update rules.

1. [verified] FGFR3 is active because GRB2 is inactive and FGFR3 is stimulated, with EGFR off.  (GRB2=0, FGFR3_stimulus=1, EGFR=0 => FGFR3=1)
2. [verified] RAS is active because FGFR3 is active.  (FGFR3=1 => RAS=1)
3. [verified] ATM medium is active because DNA damage is present in the scenario.  (DNA_damage=1 => ATM_medium=1)
4. [verified] CHEK1_2 medium is active because ATM medium is active.  (ATM_medium=1 => CHEK1_2_medium=1)
5. [verified] CHEK1_2 high is active because E2F1 medium, CHEK1_2 medium, and ATM medium are all present.  (E2F1_medium=1, CHEK1_2_medium=1, ATM_medium=1 => CHEK1_2_high=1)
6. [verified] ATM high is active because E2F1 medium, DNA damage, and ATM medium are present.  (E2F1_medium=1, DNA_damage=1, ATM_medium=1 => ATM_high=1)
7. [verified] E2F1 high is active because RB1 and RBL2 are knocked out, RAS is active, E2F1 medium, CHEK1_2 medium, CHEK1_2 high, ATM medium, and ATM high are all present.  (RBL2=0, RB1=0, RAS=1, E2F1_medium=1, CHEK1_2_medium=1, CHEK1_2_high=1, ATM_medium=1, ATM_high=1 => E2F1_high=1)
8. [verified] E2F1 medium is active because RB1 and RBL2 are knocked out and RAS is active, or because E2F1 medium and E2F1 high are both present.  (E2F1_medium=1, E2F1_high=1 => E2F1_medium=1)

Explanation check: 8/8 steps verified against the model rules

Caveats: The derivation follows the solver's causal chain; other network interactions are not described.

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
model nvidia/nemotron-3.5-lightning-30b-a3b | data layer zetaris | memory session | rounds 2 | solver calls 60 (search 49, replayed from memory 33) | LLM calls 6 via nightshift (nvidia/nemotron-3.5-lightning-30b-a3b) | tokens 13635 | 21.4s
