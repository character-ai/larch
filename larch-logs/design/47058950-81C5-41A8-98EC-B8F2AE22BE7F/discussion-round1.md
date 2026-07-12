## Decision 1: Fix breadth
- **Question**: Which of the issue's 4 suggested fixes should the plan include?
- **Resolution**: #1 (add `detail` to the outcome schema, populate from `_persist_unavailable`) + #2 (propagate detail to operator-bail via `ship route-exit`) + #4 (capture child stderr in `step-8-assessment.sh` `run_child`, forward via merge-result-env). Exclude #3 (commit receipt files to larch-logs). Once #1 puts detail in the outcome file, which is already committed to larch-logs, the receipt file is no longer the only detail source, so #3 is redundant.
- **Source**: user

## Decision 2: Non-goal — underlying claude CLI failure
- **Question**: Should the plan also fix WHY the `claude --print` subprocess returns empty stdout (an open question in the issue)?
- **Resolution**: No. This issue is scoped to surfacing diagnostics so the operator knows the failure reason. The empty-stdout / `json.JSONDecodeError` root cause and retry policy are separate concerns.
- **Source**: codebase (issue title and "Expected behavior" are diagnostic-surfacing only)

## Hard constraints
- The detail string must continue to be redacted and truncated by `_safe_detail` before it touches any committed artifact (outcome file, larch-logs). No raw stderr or exception with secrets reaches committed logs.
- Existing outcome-file consumers (`ship route-exit`, run-log readers, tests asserting `needs_user_reason == "architectural-assessment-unavailable"`) must keep working. Adding a `detail` field is additive; do not change the existing field grammar (`outcome`, `reason`, `note_state`).
- Receipt-file behavior stays as-is (still written for the same callers); only the outcome file and operator-bail path gain the detail.
