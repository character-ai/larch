## Proposed Design Outline

### Goals
- Add static-slot cursor+codex pairing assertion to `test-dispatch-plan-review-panel.sh` so the plan-review harness matches the decompose harness contract (Item A literal close).
- Reuse the existing zero-findings short-circuit in `review-core.sh` when aggregator returns `REASON=ok` AND `MERGED_COUNT=0` (Item B: skip three wasted voter launches on attestation-only ballot).
- Add `aggregator-output-phase2.txt` / `aggregator-output-phase3.txt` to the artifact-paths list in `skills/review/scripts/review-core.md:65` (Item C: phase-suffixed dispatcher path doc-drift close).

### Non-goals
- No edits to `dispatch-plan-review-panel.sh` (fallback_group wiring already landed via #2898).
- No edits to `dispatch-code-voters.sh` (skip site is the upstream caller, not the dispatcher).
- No refactor of `aggregate-findings.sh`, no changes to the zero-findings tally machinery, no `aggregate-findings.md` edits.

### Approach sketch
- Item A: extend the existing static-slot `for archetype in ...` loop in `test-dispatch-plan-review-panel.sh` lines 86-90 with a `jq -e` pairing assertion modeled on `test-decompose-panel-dispatch.sh` lines 98-103 (verify `cursor-plan-${a}` AND `codex-plan-${a}` both carry `fallback_group=plan-${a}`).
- Item B: after `aggregate-findings.sh` returns in `review-core.sh`, branch on `REASON=ok && MERGED_COUNT=0` and dispatch through the same zero-findings code path used at lines 451-514 (synthesized empty voter file → tally → emit). Extract or jump-to that block; do not duplicate it.
- Item C: edit one line in `review-core.md` (line 65) to enumerate `aggregator-output.txt`, `aggregator-output-phase2.txt`, `aggregator-output-phase3.txt`.
- Add a regression assertion to `test-aggregate-findings.sh` or create a dedicated review-core empty-merge harness asserting the new branch path is taken (no voter launch).

### Surfaces in scope
- `skills/design/scripts/test-dispatch-plan-review-panel.sh` (harness pairing assertion).
- `skills/review/scripts/review-core.sh` (empty-merge short-circuit branch).
- `skills/review/scripts/review-core.md` (doc line 65).
- Regression harness for the new empty-merge branch (existing harness extension or a new test, choice deferred to Step 2b).

### Open questions
- None.
