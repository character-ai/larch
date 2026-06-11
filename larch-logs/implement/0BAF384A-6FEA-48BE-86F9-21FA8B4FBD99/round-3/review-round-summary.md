# Review Round 3

- Mode: `diff`
- 6 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: list_issues closed-window cutoff uses UTC instead of local date
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Phase 1 dedup closed-issue cutoff now uses UTC today instead of the prior local-date behavior. Near timezone or day boundaries, this can include or exclude different closed issues and change duplicate or dependency triage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_2: create-one treats successful non-JSON issue creation as failure
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `issue create-one` no longer handles `gh issue create --json` returning exit 0 with plain URL or other non-JSON output. The issue may already be created, but the helper emits failure, which can leave orphans or cause duplicate creation on retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_3: cleanup empty tmp-root env var no longer falls back to /tmp
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `cleanup` changed semantics when `LARCH_TEST_TMP_ROOT` is exported as an empty string. It can scan the current working directory and remove old `larch-*` entries there instead of falling back to `/tmp`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_4: add_blocked_by redaction failures bypass fail-closed reporting
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `add_blocked_by` failure paths use `_flat_error` without the fail-closed redaction wrapper. If outbound secret redaction raises during dependency-link failure, `/issue` Step 6 may crash or return the wrong status instead of reporting `BLOCKED_BY_FAILED=true`, `ERROR=redaction:…`, and exit 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: allocate-candidates boundary tests were not ported
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Boundary coverage from the deleted allocate-candidates shell harness was not ported. Floor-formula, spillover, or Pass-B tie-break regressions could mis-rank Phase 2 candidates for multi-item `/issue` batches without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: destructive forked-repo setup coverage was not ported
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Required forked-repo setup tests were not ported for happy remote rewrite, push-disable, mirror guard, and mirror sync paths. Regressions in origin/upstream rewrite, `remote.upstream.pushurl`, or `--mirror-confirmed` behavior can pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


