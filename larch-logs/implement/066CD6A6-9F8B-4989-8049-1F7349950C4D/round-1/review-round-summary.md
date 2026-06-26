# Review Round 1

- Mode: `diff`
- 1 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Lint-fix 600s budget enforced only after each tier completes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The 600-second lint-fix total budget is checked only after each tier returns, not before starting the next tier. In the default claude → codex → cursor waterfall, two near-300s failures can leave elapsed time below 600s after tiers 1–2, so the third tier still launches and may run up to ~300s more (~800–900s wall time total). The guard does not short-circuit mid-waterfall as documented. On the success path, a third-tier success can return after roughly 900 seconds with no `lint-fix-budget-exceeded` signal because the budget check runs only on the failure path after a tier finishes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add a pre-tier budget guard or pass remaining budget into each _run_* call so total wall time cannot exceed 600s
  - From cursor-specialist-edge-cases-output.txt: Check budget before dispatching each tier (and optionally when elapsed plus _RUN_EXTERNAL_TIMEOUT would exceed the cap); add a regression test with two fast failures and a third tier that should be skipped.
  - From codex-specialist-edge-cases-output.txt: enforce a hard deadline before each launch and reject successes once the budget is exhausted, or pass the remaining budget into the launcher and stop before starting the next tier.
  - From codex-specialist-testing-output.txt: Compute or check a deadline before each launch, or clamp each tier’s timeout to the remaining budget and stop dispatching when the budget is exhausted.


