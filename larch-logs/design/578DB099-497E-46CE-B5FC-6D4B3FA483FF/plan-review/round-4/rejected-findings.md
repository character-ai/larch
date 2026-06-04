### [Plan Review] FINDING_3

### FINDING_3: Manifest `.slot` values are not vendor-distinct
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan mirrors `/design` both-vendor rows via output paths only and does not require vendor-distinct manifest `.slot` values. `queue_external_slot` still sets `"slot":"%s"` to the bare archetype slug (e.g. `testing`). Emitting Cursor and Codex static rows (and Cursor/Codex dynamic twins) with the same slug duplicates slot IDs in `panel-manifest.ndjson`, unlike `dispatch-plan-review-panel.sh` (`cursor-plan-*` / `codex-plan-*`, `dyn-cursor-plan-*` / `dyn-codex-plan-*`). That collides drop diagnostics (`DROPPED_SLOTS_FILE` TSV), `dispatch-with-waterfall.sh` timing kinds (`${tool}-phase1-${slot}`), and dynamic tally attribution when `.slot` is used.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add explicit manifest contract to the plan: static slots `cursor-specialist-<archetype>` / `codex-specialist-<archetype>` (matching output basenames); dynamic slots `dyn-<name>` / `dyn-codex-<name>` with outputs `dyn-<name>-output.txt` / `dyn-<name>-codex-output.txt`. Refactor emission accordingly and assert unique `.slot` values in `test-dispatch-panel.sh`.


### [Plan Review] FINDING_4

### FINDING_4: Codex dynamic basename may bypass failure-threshold dynamic carve-out
- **Reviewer(s)**: Cursor-dyn-threshold-denominator
- **Severity**: important
- **Concern**: The plan permits non-`dyn-*` Codex dynamic output basenames while `is_dynamic_reviewer_basename` in `check-reviewer-failure-threshold.sh` only matches `^dyn-.*-output`. Design-style `codex-primary-plan-dyn-*` paths would be counted as static failures and can false-trigger `>50%` panel-failed despite partial static success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-threshold-denominator: Require dyn-${name}-codex-output.txt (remove or equivalent distinct basename) or extend is_dynamic_reviewer_basename to cover every permitted dynamic Codex basename before counting static FAILED_SLOTS

