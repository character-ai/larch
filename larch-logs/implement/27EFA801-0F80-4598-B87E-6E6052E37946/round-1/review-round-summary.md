# Review Round 1

- Mode: `diff`
- 5 accepted, 13 rejected (6 exonerated)

## Accepted Findings

### FINDING_1: code-quality: skills/design/scripts/test-run-step3-review.sh:370-397
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Integration-seam stub duplicates plan-review-loop argv whitelist manually. plan-review-loop.sh adds a new flag and run-step3-review.sh forwards it, but the seam stub is not updated: the test still passes while production Step 3 fails with unknown option. Add a structure-test pin on the driver invocation flag set, or document/sync the stub whitelist with plan-review-loop.sh's case parser.
- **Suggested revision**: Address the concern above.


### FINDING_29: **code-quality** `skills/cleanup/scripts/test-cleanup.sh:218-253` — `assert_eq`, `assert_contains`, and `kv_get` all call `fail`, which runs `exit 1` (lines 16–18, 21–28, 31–36), so a failed assertion aborts the harness before the trailing `unset PATH_PREFIX` in the two new enumeration cases. That pattern already existed for `find-failure-skips-deletion`, but placing `enumeration-failure-warns-tmp` immediately before `mktemp-allocation-failure-warns` amplifies the risk: `mktemp-allocation-failure-warns` never sets `PATH_PREFIX`, yet `run_cleanup` prefers a leaked shell `PATH_PREFIX` over per-case `$work/bin` (line 101). If `enumeration-failure-warns-tmp` fails after `PATH_PREFIX="$work/bin:"` and before line 231, the next case still runs `cleanup.sh` with the enumeration-failure stub on `PATH`, so `mktemp-allocation-failure-warns` can fail for the wrong reason (enumeration warnings instead of allocation warnings) and later cases can flake similarly. **Suggested fix:** Move `unset PATH_PREFIX` to immediately after each `run_cleanup` (before any assertion), or wrap each stubbed case in a subshell / `trap 'unset PATH_PREFIX' RETURN` so teardown runs even when `fail` exits. The `mktemp-allocation-failure-warns` block already does the right thing for `TMPDIR`/`chmod` (lines 244–245 run before assertion failures at 246+).
- **Reviewer**: dyn-test-env-isolation-output.txt
- **Concern**: - **code-quality** `skills/cleanup/scripts/test-cleanup.sh:218-253` — `assert_eq`, `assert_contains`, and `kv_get` all call `fail`, which runs `exit 1` (lines 16–18, 21–28, 31–36), so a failed assertion aborts the harness before the trailing `unset PATH_PREFIX` in the two new enumeration cases. That pattern already existed for `find-failure-skips-deletion`, but placing `enumeration-failure-warns-tmp` immediately before `mktemp-allocation-failure-warns` amplifies the risk: `mktemp-allocation-failure-warns` never sets `PATH_PREFIX`, yet `run_cleanup` prefers a leaked shell `PATH_PREFIX` over per-case `$work/bin` (line 101). If `enumeration-failure-warns-tmp` fails after `PATH_PREFIX="$work/bin:"` and before line 231, the next case still runs `cleanup.sh` with the enumeration-failure stub on `PATH`, so `mktemp-allocation-failure-warns` can fail for the wrong reason (enumeration warnings instead of allocation warnings) and later cases can flake similarly. **Suggested fix:** Move `unset PATH_PREFIX` to immediately after each `run_cleanup` (before any assertion), or wrap each stubbed case in a subshell / `trap 'unset PATH_PREFIX' RETURN` so teardown runs even when `fail` exits. The `mktemp-allocation-failure-warns` block already does the right thing for `TMPDIR`/`chmod` (lines 244–245 run before assertion failures at 246+).
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: scripts/test-design-structure.sh:156-158
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Structure harness lacks absent pin for SKILL.md convergence forwarding. Someone re-adds --convergence-threshold to SKILL.md Step 3; structure tests stay green until a live /design run hits argv errors. Add absent "$SKILL_MD" '--convergence-threshold' (or the full expansion line) alongside the existing run-step3 absent pin.
- **Suggested revision**: Address the concern above.


### FINDING_8: risk-integration: scripts/test-design-structure.sh:156-165
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Removed SKILL.md contains pin for --convergence-threshold without an absent guard. Re-adding --convergence-threshold to SKILL Step 3 would not fail test-design-structure.sh; only run-step3-review.sh forwarding is absent-pinned. Add absent "$SKILL_MD" '--convergence-threshold' and/or absent "$SKILL_MD" 'LARCH_DESIGN_CONVERGENCE_THRESHOLD'.
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: skills/cleanup/scripts/test-cleanup.sh:233-251
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] mktemp-allocation-failure-warns asserts one generic allocation warning, not both pass-specific messages. A regression that warns/skips only the cache or only the /tmp pass could still pass if any allocation warning appears once. Assert both failed to allocate temp list for cache cleanup and for /tmp cleanup substrings when both passes run.
- **Suggested revision**: Address the concern above.


