# Review Round 1

- Mode: `diff`
- 5 accepted, 5 rejected (5 exonerated)

## Accepted Findings

### FINDING_1: Stale “convergence streak” prose in env docs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-caller-sweep-completeness-output.txt
- **Severity**: important
- **Concern**: `docs/configuration-and-permissions.md` (~line 250) still describes plan-review convergence with a “streak” / two-round streak semantics after `LARCH_DESIGN_CONVERGENCE_THRESHOLD` and streak machinery were removed. Operators and doc grep can believe streak-based stopping still applies, conflicting with the single-round hardcoded rule (≤5 non-nit accepted, 0 important accepted, nits excluded) documented elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-caller-sweep-completeness-output.txt: Reword line 250 to match `skills/design/references/flags.md` and `plan-review.md` — e.g. “Plan-review convergence (≤5 non-nit accepted, 0 important; nits excluded) is hardcoded in `plan-review-loop.sh`” — with no mention of streak.


### FINDING_10: Missing convergence narrative in `plan-review-loop.md`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Plan asked for updated convergence prose in `skills/design/scripts/plan-review-loop.md`; only KV/argv tables changed. Consumers of the driver `.md` sibling without `plan-review.md` may miss nit-exclusion and single-round semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add a short Convergence (multi-round) subsection aligned with `plan-review.md`.


### FINDING_3: Misleading harness banner still references convergence streak
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/test-plan-review-loop.sh` (~1631) test section title/echo still refers to “convergence streak” / “resets convergence streak” after single-round convergence; misleading for maintainers debugging harness behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Update echo string to reflect single-round converged reason.
  - From cursor-specialist-testing-output.txt: Rename echo to degraded-then-converged or similar.


### FINDING_4: Missing test for converged termination when snapshot fails
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No harness asserts converged termination when `_snapshot_round_dir` fails after a qualifying round. A regression could yield `panel-failed` or wrong `REASON` instead of preserving `converged` / `converged,snapshot-failed` without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add integration case forcing snapshot failure after `NON_NIT_ACCEPTED_COUNT<=5` and assert `LOOP_STATUS=converged` and `REASON=converged,snapshot-failed`.


### FINDING_5: Plan-required nit-heavy convergence case not exercised (`many_nits_three_latent`)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `many_nits_three_latent` collect mode exists in `skills/design/scripts/test-plan-review-loop.sh` (~349–366) but is not wired into any `run_loop` case. Plan acceptance for many nits + ≤5 non-nit convergence is only partially covered by separate cases; combined tally path and nit-heavy boundary could regress undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Wire `many_nits_three_latent` into a converging `run_loop` and assert `NIT_ACCEPTED_COUNT` and `NON_NIT_ACCEPTED_COUNT=3`.
  - From cursor-specialist-plan-fidelity-output.txt: Add a test invoking `write_collect many_nits_three_latent` asserting converged `REASON=converged` `NIT_ACCEPTED_COUNT=10` `NON_NIT_ACCEPTED_COUNT=3` `ROUNDS_COMPLETED=1`.


