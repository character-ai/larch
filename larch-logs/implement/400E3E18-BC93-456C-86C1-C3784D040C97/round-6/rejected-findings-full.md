### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Implement lint-fix-main-agent-required path may rely on deferred orchestration for timing rows
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The lint-fix-main-agent-required branch persists `round-start-s` but emits no in-loop timing row, so a missing deferred helper would drop the round from `timing-report.json`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Implement in-loop timing helper can bypass refreshed round tally when explicit zero counts are passed
- **Reviewer(s)**: dyn-bash32-output.txt
- **Severity**: latent
- **Concern**: `_emit_implement_round_timing_row` passes explicit `IRF_LAST_*` counts, causing `record-implement-review-round-timing.sh` to skip `review-tally.env` whenever arguments are non-empty, including `"0"`. This is safe for current orchestrator paths but fragile for future deferred callers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-output.txt: Only pass `--accepted`/`--rejected` when intentionally overriding tally lookup (e.g., add an explicit `--prefer-tally` flag, or pass counts only when `IRF_LAST_*` is known fresh and omit the flags otherwise so the helper reads `review-tally.env` first).


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: `emit_round_array` uses undeclared global awk arrays
- **Reviewer(s)**: dyn-bash32-output.txt
- **Severity**: nit
- **Concern**: `match_idx` and `round_match_pos` are not function-local awk arrays, making the renderer fragile if extended or reused.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-output.txt: Add `match_idx` and `round_match_pos` to the awk function-local list (`function emit_round_array(..., i, j, ..., match_idx, round_match_pos)`) and clear them on every exit path.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: Duplicate round ledger rows are silently resolved last-wins
- **Reviewer(s)**: dyn-jsonawk-output.txt
- **Severity**: latent
- **Concern**: `emit_round_array` deduplicates rows with the same round key by keeping the last row silently, so warn-only retries or partial failures can overwrite duration/counts without signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-jsonawk-output.txt: Either reject/ warn on duplicate `(skill, step, round, interval)` rows during aggregation, or deterministically prefer the row whose `[start_s, end_s)` best matches the parent step interval instead of last-wins.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Implement/design deferred timing helpers duplicate ledger binding and record-round plumbing
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Deferred timing helper logic is duplicated across implement and design, increasing regression risk when validation, ledger binding, or round-record columns change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Timing report round ordering uses unnecessary bubble sort
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/timing-report.sh` uses bubble sort for matched round indices. It is unlikely to break at current caps, but adds avoidable complexity in the report path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

