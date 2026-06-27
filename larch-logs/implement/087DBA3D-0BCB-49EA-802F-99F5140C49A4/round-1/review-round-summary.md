# Review Round 1

- Mode: `diff`
- 2 accepted, 3 rejected (1 neutral)

## Accepted Findings

### FINDING_1: shipping omitted from terminal-outcome regexes shared across verify-completeness and audit-runs
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-edge-cases, cursor-specialist-testing
- **Severity**: important
- **Concern**: The new `shipping` outcome is not included in `_TERMINAL_OUTCOME_SUFFIX` / `_TERMINAL_RE` patterns in `python/run_log_tolerance.py`, `python/larch/report/run_logs.py`, and `python/larch/issue/audit_runs.py`. Pre-ship committed snapshots that now use a `shipping` heading (instead of `bailed`) no longer get the same bail-skip tolerance as `pr-created` headings. `verify_completeness` and audit-runs can falsely fail run directories missing later artifacts (e.g. step9a1) that previously passed under a `bailed` heading. Identical artifacts with a `pr-created` heading still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_5: shipping branch outranks BAIL_NEEDS_USER_INPUT in stall_recovery.py
- **Reviewer(s)**: codex-specialist-correctness, codex-generalist
- **Severity**: important
- **Concern**: The new no-PR `shipping` fallthrough in `python/larch/state/stall_recovery.py` (887–896) runs before or without checking `BAIL_NEEDS_USER_INPUT`. When `finalize-state.sh` contains `BAIL_NEEDS_USER_INPUT=true`, there is no PR evidence, no bail reason, and `EXIT_CODE=0`, `normalized_outcome_values()` returns `shipping` and promotes the manifest to `in-progress` instead of the existing `bailed-needs-user-input` outcome covered by `skills/implement/scripts/test-write-final-report.sh:213-228`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-generalist: Address the concern above.


