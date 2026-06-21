# Review Round 4

- Mode: `diff`
- 6 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Cap rollup does not cap or reject when stable-id resolution exceeds N
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Cap rollup expansion does not cap or reject when explicit stable-id resolution yields more than N members for an "Aggregated rollup of N" title. A rollup ndjson can cite three resolvable OOS stable ids with title "Aggregated rollup of 2 capped OOS items"; the report then scores three reviewer rows for one filed issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: After expansion if expected > 0 and len(out) > expected return ambiguous rollup expansion or otherwise fail closed; add regression test.


### FINDING_2: Cap rollup scores partial members when cited stable ids are ambiguous
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-oos-reconciler-output.txt
- **Severity**: important
- **Concern**: When a cap-rollup or multi-stable-id ndjson record cites multiple stable IDs, IDs that resolve ambiguously are silently dropped if any sibling ID matched. One member can be scored while another is dropped with no `ambiguous stable id` or `ambiguous rollup expansion` bucket signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: If any rollup stable id is ambiguous return ambiguous rollup expansion instead of scoring a subset.
  - From dyn-oos-reconciler-output.txt: Track per-stable-id resolution; emit scored rows for unambiguous matches and increment `ambiguous stable id` (or a per-id skip bucket) for IDs that collided, instead of conditioning ambiguity reporting on zero matches.


### FINDING_3: Cap rollup all-or-nothing drops already-resolved members on shortfall
- **Reviewer(s)**: dyn-oos-reconciler-output.txt
- **Severity**: important
- **Concern**: If explicit stable-id resolution (or excerpt matching) produces some rows but candidate count still falls short of parsed N, `_expand_cap_rollup_records` returns only an `ambiguous rollup expansion` bucket row and drops already-resolved members. That undercounts provisional/adjusted points for unambiguously joined items.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-reconciler-output.txt: On ambiguous fallback, keep resolved `out` rows, append an `ambiguous rollup expansion` bucket entry for the unresolved remainder, and only return a single ambiguous row when `out` is empty.


### FINDING_4: Broad Aggregated rollup substring triggers empty expansion and vanishing filing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: An ndjson row with only a Filed URL and incidental "Aggregated rollup" prose can match `_is_cap_rollup_record`; `_expand_cap_rollup_records` returns `[]`, and the filing vanishes from fate scoring and buckets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Tighten rollup detection to canonical title or explicit multi-member evidence; fall back to normal join when expansion yields no rows.


### FINDING_5: Invalid GitHub label treated as closed-unfixed dock signal
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_has_not_planned_signal` treats the `invalid` label as a closed-unfixed dock signal, though the plan lists only NOT_PLANNED / wontfix / not-planned labels/body. A filed OOS issue closed with `invalid` but without NOT_PLANNED or wontfix text is docked to 0 in fate-adjusted scoring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Remove invalid from dock label set or require additional wontfix/not-planned evidence; add test expecting provisional unknown.
  - From cursor-specialist-edge-cases-output.txt: Remove invalid from dock labels or require stronger not-planned signals.


### FINDING_6: Filed-issue parser misses legacy URL forms in committed run logs
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: The filed-issue parser misses explicit legacy URL forms already present in committed run logs, including `Filed as https://github.com/.../issues/N` and `**Filed**: https://github.com/.../issues/N`; `_record_issue_urls` has the same gap. A record like `FINDING_1 ... Filed as https://github.com/character-ai/larch/issues/3025` yields no issue number, so `run_main` never fetches targeted details and fate scoring silently skips that filed OOS item.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Add explicit URL patterns for `Filed as <url>` and markdown-emphasized `Filed: <url>`, and cover them with regression tests using current legacy ndjson shapes.


