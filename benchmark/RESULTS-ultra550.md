# Benchmark results (nvidia/nemotron-3-ultra-550b-a55b)

Scored against exhaustive-solver ground truth. `solved_rate`/`recall` are over feasible scenarios; `infeasible_*` over the scenario with no solution.

| arm | runs | solved_rate | recall | solver_calls | calls_to_first | llm_calls | seconds | wrong_claim_rate | infeasible_proved | infeasible_hallucinated | explanation_steps_verified |
|---|---|---|---|---|---|---|---|---|---|---|---|
| llm_only | 8 | 0.12 | 0.04 | 0 |  | 1.12 | 56.24 | 0.97 |  |  |  |
| ours_full | 8 | 1 | 1.0 | 110.38 | 39.88 | 5.75 | 106.21 |  |  |  | 0.994 |

## Per scenario (mean over repeats)

| scenario | arm | solved | recall | solver calls | LLM calls | s |
|---|---|---|---|---|---|---|
| egf_tp53null | llm_only | 0 | 0.0 | 0 | 1.5 | 81.1 |
| egf_wtp53 | llm_only | 0 | 0.0 | 0 | 1 | 29.45 |
| fgfr3_rb1loss | llm_only | 0.5 | 0.17 | 0 | 1 | 65.6 |
| fgfr3_wtp53 | llm_only | 0 | 0.0 | 0 | 1 | 48.8 |
| egf_tp53null | ours_full | 1 | 1.0 | 19 | 2 | 43.6 |
| egf_wtp53 | ours_full | 1 | 1.0 | 258 | 10 | 204.1 |
| fgfr3_rb1loss | ours_full | 1 | 1.0 | 34 | 4.5 | 69.85 |
| fgfr3_wtp53 | ours_full | 1 | 1.0 | 130.5 | 6.5 | 107.3 |