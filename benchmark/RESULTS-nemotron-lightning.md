# Benchmark results (nvidia/nemotron-3.5-lightning-30b-a3b)

Scored against exhaustive-solver ground truth. `solved_rate`/`recall` are over feasible scenarios; `infeasible_*` over the scenario with no solution.

| arm | runs | solved_rate | recall | solver_calls | calls_to_first | llm_calls | seconds | wrong_claim_rate | infeasible_proved | infeasible_hallucinated | explanation_steps_verified |
|---|---|---|---|---|---|---|---|---|---|---|---|
| brute_force | 8 | 1 | 1.0 | 2876.38 |  | 0 | 21.59 |  | 1 |  |  |
| llm_only | 22 | 0.26 | 0.09 | 0 |  | 1 | 7.25 | 0.91 |  | 1 |  |
| llm_feedback | 24 | 0.29 | 0.13 | 13.67 | 2.67 | 7.67 | 52.69 |  | 0 |  |  |
| symbolic_cegar | 24 | 1 | 1.0 | 84.12 | 55.14 | 3.38 | 0.93 |  | 1 |  |  |
| llm_cegar | 24 | 1 | 1.0 | 105.17 | 67.14 | 3.58 | 29.9 |  | 1 |  |  |
| ours_full | 24 | 1 | 1.0 | 113.79 | 66.24 | 5.92 | 43.16 |  | 1 |  | 0.968 |

## Per scenario (mean over repeats)

| scenario | arm | solved | recall | solver calls | LLM calls | s |
|---|---|---|---|---|---|---|
| egf_growthinh | brute_force | 1 | 1.0 | 2048 | 0 | 26.6 |
| egf_mdm2amp | brute_force | 1 | 1.0 | 1795 | 0 | 17.3 |
| egf_tp53null | brute_force | 1 | 1.0 | 1563 | 0 | 17.4 |
| egf_wtp53 | brute_force | 1 | 1.0 | 2007 | 0 | 16.0 |
| fgfr3_growthinh | brute_force | 1 | 1.0 | 1987 | 0 | 13.9 |
| fgfr3_rb1loss | brute_force | 1 | 1.0 | 1163 | 0 | 7.1 |
| fgfr3_wtp53 | brute_force | 1 | 1.0 | 1545 | 0 | 9.6 |
| growthinh_only | brute_force | n/a | n/a | 10903 | 0 | 64.8 |
| egf_growthinh | llm_only | 0 | 0.0 | 0 | 1 | 10.63 |
| egf_mdm2amp | llm_only | 0 | 0.0 | 0 | 1 | 9.1 |
| egf_tp53null | llm_only | 0 | 0.0 | 0 | 1 | 6.87 |
| egf_wtp53 | llm_only | 0 | 0.0 | 0 | 1 | 7.37 |
| fgfr3_growthinh | llm_only | 0.33 | 0.11 | 0 | 1 | 5.53 |
| fgfr3_rb1loss | llm_only | 0.33 | 0.11 | 0 | 1 | 5.5 |
| fgfr3_wtp53 | llm_only | 1 | 0.33 | 0 | 1 | 7.4 |
| growthinh_only | llm_only | n/a | n/a | 0 | 1 | 6.8 |
| egf_growthinh | llm_feedback | 0 | 0.0 | 12 | 8 | 52.17 |
| egf_mdm2amp | llm_feedback | 0 | 0.0 | 12.33 | 7.33 | 52.9 |
| egf_tp53null | llm_feedback | 0 | 0.0 | 17.67 | 8 | 61.43 |
| egf_wtp53 | llm_feedback | 0 | 0.0 | 16.67 | 7.67 | 48.63 |
| fgfr3_growthinh | llm_feedback | 0 | 0.0 | 11.67 | 8 | 51.33 |
| fgfr3_rb1loss | llm_feedback | 1 | 0.56 | 14.67 | 6.33 | 50.8 |
| fgfr3_wtp53 | llm_feedback | 1 | 0.33 | 15.33 | 8 | 49.37 |
| growthinh_only | llm_feedback | n/a | n/a | 9 | 8 | 54.87 |
| egf_growthinh | symbolic_cegar | 1 | 1.0 | 200 | 5 | 2.63 |
| egf_mdm2amp | symbolic_cegar | 1 | 1.0 | 11 | 1 | 0.23 |
| egf_tp53null | symbolic_cegar | 1 | 1.0 | 11 | 1 | 0.2 |
| egf_wtp53 | symbolic_cegar | 1 | 1.0 | 263 | 7 | 2.0 |
| fgfr3_growthinh | symbolic_cegar | 1 | 1.0 | 60 | 2 | 0.87 |
| fgfr3_rb1loss | symbolic_cegar | 1 | 1.0 | 17 | 1 | 0.3 |
| fgfr3_wtp53 | symbolic_cegar | 1 | 1.0 | 55 | 2 | 0.5 |
| growthinh_only | symbolic_cegar | n/a | n/a | 56 | 8 | 0.7 |
| egf_growthinh | llm_cegar | 1 | 1.0 | 213.67 | 4.67 | 45.43 |
| egf_mdm2amp | llm_cegar | 1 | 1.0 | 47.67 | 1.33 | 13.5 |
| egf_tp53null | llm_cegar | 1 | 1.0 | 50.33 | 1.33 | 10.17 |
| egf_wtp53 | llm_cegar | 1 | 1.0 | 294.67 | 7.67 | 34.83 |
| fgfr3_growthinh | llm_cegar | 1 | 1.0 | 82 | 1.67 | 14.47 |
| fgfr3_rb1loss | llm_cegar | 1 | 1.0 | 30.33 | 2 | 15.87 |
| fgfr3_wtp53 | llm_cegar | 1 | 1.0 | 66.33 | 2 | 27.23 |
| growthinh_only | llm_cegar | n/a | n/a | 56.33 | 8 | 77.67 |
| egf_growthinh | ours_full | 1 | 1.0 | 235 | 8.67 | 47.2 |
| egf_mdm2amp | ours_full | 1 | 1.0 | 48 | 2.67 | 13.2 |
| egf_tp53null | ours_full | 1 | 1.0 | 39 | 2 | 38.1 |
| egf_wtp53 | ours_full | 1 | 1.0 | 354.33 | 11 | 59.6 |
| fgfr3_growthinh | ours_full | 1 | 1.0 | 79.67 | 5.33 | 50.6 |
| fgfr3_rb1loss | ours_full | 1 | 1.0 | 29 | 4.67 | 39.57 |
| fgfr3_wtp53 | ours_full | 1 | 1.0 | 68.67 | 5 | 46.27 |
| growthinh_only | ours_full | n/a | n/a | 56.67 | 8 | 50.73 |