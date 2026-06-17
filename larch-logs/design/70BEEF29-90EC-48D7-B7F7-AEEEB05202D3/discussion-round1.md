## Decision 1: Code-voter parse-rate retry — in scope
- **Question**: The voter parse-rate retry in `scripts/dispatch-code-voters.sh` applies the same retry-on-result anti-pattern for code voters. Fix it in this change, or split it to a separate issue?
- **Resolution**: Fix in this change. Remove the voter parse-rate retry in the same PR; align the voter tally so a parse-rate-failed voter is counted, not silently retried.
- **Source**: user

## Decision 2: NOT_SUBSTANTIVE — counted-failed and dropped (no waterfall fallback)
- **Question**: After ns-retry is removed, should a NOT_SUBSTANTIVE reviewer stay eligible for the waterfall alt-tool fallback, or be strictly counted-as-failed and dropped?
- **Resolution**: Strictly counted-as-failed and dropped. A result-quality failure must not trigger an alt-tool retry. Consistent with "retry only for launch, not results."
- **Source**: user

## Decision 3: Minimum healthy-reviewer floor — not added
- **Question**: Should this change add a new minimum healthy-reviewer floor that flags a round as degraded when too few reviewers remain after drops?
- **Resolution**: No new floor. Rely on the existing failure-threshold check (`check-reviewer-failure-threshold.sh` counts NOT_SUBSTANTIVE slots; >50% failed = degraded) and the existing degraded-empty-collector handling in the plan-review loop.
- **Source**: user

## Decision 4: Part B (prompt robustness) — in scope
- **Question**: The round-2+ combined codex-plan-generic prompt is the root cause of the format fragility. Include a prompt-robustness fix in this change, or defer it?
- **Resolution**: Include Part B now. Harden the round-2+ combined codex-plan-generic prompt so it is less likely to emit narrative/non-TSV output. The core warn-and-drop fix still stands on its own; Part B reduces how often the drop fires.
- **Source**: user

## Hard constraints (must not break)
- Keep launch-level retries: EMPTY_OUTPUT, transient-net signatures (`_build_initial_records` + `_apply_empty_retry_results`), and the agents.py auth-startup retry. Only the result-quality (ns-retry) stage is removed.
- Keep the detection validators `_validate_substantive` and `_validate_structured`; they still set `NOT_SUBSTANTIVE`. Only the retry response to that status changes.
- All `--substantive-validation` callers must keep working: `/design` plan review, `/review`, `/research`.
- A NOT_SUBSTANTIVE record must reach `_emit_records` so downstream tally counts it as a reviewer failure (`COLLECT_FAILURE_COUNT` increments).
- Remove ns-retry helpers only once they are unreferenced (no dangling imports/dead code).

decisions_resolved: 4
