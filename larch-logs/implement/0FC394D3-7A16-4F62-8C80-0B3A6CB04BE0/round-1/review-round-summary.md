# Review Round 1

- Mode: `diff`
- 5 accepted, 3 rejected (3 exonerated)

## Accepted Findings

### FINDING_1: Pre-push handoff must be gated away from postbump callers
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `PrePushConflictHandoff` can be raised for all `rebase_and_push(..., allow_conflict_fix=True)` callers, including finalize/postbump paths where bash currently returns a plain rebase failure/stall without conflict-resolution handoff. The Python path needs an explicit handoff enablement guard used only by the CI-fix pre-push rebase entrypoint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: Python bump gate ignores canonical `LARCH_VERSION_FILES`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-handoff-contract-output.txt, dyn-bump-gate-output.txt
- **Severity**: important
- **Concern**: `_larch_bump_files()` reads only `LARCH_BUMP_FILES`, while bash treats `LARCH_VERSION_FILES` as canonical and falls back to deprecated `LARCH_BUMP_FILES`. Repos configured with only `LARCH_VERSION_FILES` can classify version-file conflicts differently in Python vs bash, causing spurious or missing `PrePushConflictHandoff`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-handoff-contract-output.txt, dyn-bump-gate-output.txt: Address the concern above.


### FINDING_6: Missing test for `IMPLEMENT_TMPDIR` fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tests do not cover the case where `tmpdir=None` and `IMPLEMENT_TMPDIR` is set. Callers relying on the environment fallback could regress without CI detecting flag placement or handoff behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_7: Missing test for unconfigured handoff tmpdir
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Tests do not cover the branch where both `tmpdir` and `IMPLEMENT_TMPDIR` are absent. That path should raise plain `Stalled` with no handoff tokens or flag write.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_9: Bump-only tests lock in weak or wrong bump-path coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-bump-gate-output.txt
- **Severity**: nit
- **Concern**: Bump-only exhaustion tests rely on CHANGELOG behavior and do not cover all bash-recognized bump path classes such as `.claude-plugin/plugin.json`, `version.go`, `go.sum`, or env-listed version files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-bump-gate-output.txt: Address the concern above.


