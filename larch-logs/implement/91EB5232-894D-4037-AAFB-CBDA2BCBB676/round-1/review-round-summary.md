# Review Round 1

- Mode: `diff`
- 3 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_5: `emit_larch_run_sh` returns success after launcher write, chmod, or install failures
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `emit_larch_run_sh` captures `$?` after `!`, so write, chmod, or `mv` failures can return success. Step 0 can proceed without a usable launcher and fail later in post-Step-0 fences.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_6: Old-shape fence parsing no longer enforces exactly one logical command
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: A pre-bootstrap fence with extra commands can pass by substring matching. The retained one-command invariant is no longer enforced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_8: Repeat resume-tail idempotency does not assert launcher stability
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: B7 checks `plugin-root.env` idempotency but not `larch-run.sh`. A repeat resume-tail could drop or corrupt the launcher without failing the test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


