# Review Round 4

- Mode: `diff`
- 9 accepted, 6 rejected (5 exonerated)

## Accepted Findings

### FINDING_1: Step 0 breadcrumb gating contract is inconsistent
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Step 0 now emits `larch_err` progress unconditionally while helper names and tests still imply `LARCH_QUIET_BREADCRUMBS` opt-in behavior. The implementation, harness expectations, and documented contract need to agree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_10: Duplicate symlink rejection tests have ambiguous names
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-larch-log.sh` contains two near-identical symlink rejection sections with matching headers, making failures harder to diagnose and increasing maintenance cost.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_11: `larch_errf` lacks direct unit coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: After deleting `emit_breadcrumb_stderr` tests, `scripts/test-lib-quiet.sh` no longer directly covers `larch_errf` formatting and newline behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_19: Branch includes unrelated #2667 and design-doc changes
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch mixes unrelated #2667 commit `984ec3ad` plus design-doc/env/agent-lint changes with the Stage 2 breadcrumb migration, violating the plan’s single-feature PR constraint and making the work harder to land or revert independently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: `source_dir` breadcrumb publish contract is stale or silently weakened
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `larch_log_publish_breadcrumbs_shared` retains a `source_dir`-style interface after ndjson removal, but no longer applies the old source-directory fail-closed checks. Misconfiguration can silently no-op, and maintainers may assume obsolete path guards still run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt: Address the concern above.


### FINDING_3: Review-and-fix breadcrumb pin tests describe an inert env flag
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `skills/review-and-fix/scripts/test-review-and-fix.sh` still uses or comments on `LARCH_QUIET_BREADCRUMBS=1` as if it controls breadcrumb visibility, even though Stage 2 behavior depends on stderr capture instead.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_7: SECURITY rejected-list documents removed source-dir checks
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` still says source-directory breadcrumb checks reject non-absolute or symlinked `LARCH_BREADCRUMB_SOURCE_DIR`, but the implementation now applies quiet-log and session-root guards instead.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_8: Outside-session quiet-log publish test is vacuous
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-larch-log.sh` creates an outside quiet-log directory but does not stage a quiet log, so the case can pass without exercising boundary enforcement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: Structured NS-retry tests discard diagnostics they should assert
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Some structured NS-retry success cases send stderr to `/dev/null` while related behavior emits `larch_err` diagnostics, so stdout-only or missing-diagnostic regressions would not fail those tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


