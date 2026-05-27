## Decision 1: Item A — production wiring status
- **Question**: Should /design re-wire `dispatch-plan-review-panel.sh` `fallback_group` field, or only close the harness gap?
- **Resolution**: Production wiring already landed via commit 2fc03694 (Fixes #2898). Close only the static-slot pairing-check gap in `test-dispatch-plan-review-panel.sh` (mirror lines 98-103 of `test-decompose-panel-dispatch.sh`).
- **Source**: codebase + user

## Decision 2: Item B — empty-ballot skip site
- **Question**: Where should the empty-ballot voter-launch skip live?
- **Resolution**: `review-core.sh`. After aggregator returns, if `REASON=ok` AND `MERGED_COUNT=0`, route into the existing zero-findings short-circuit branch (review-core.sh:451-514) which already produces correct tally artifacts for the empty case.
- **Source**: user

## Decision 3: Item C — review-core.md scope
- **Question**: What to add to `review-core.md:65`?
- **Resolution**: Add `aggregator-output-phase2.txt` and `aggregator-output-phase3.txt` to the artifact paths list (alongside existing `aggregator-output.txt`). These are documented in `aggregate-findings.md:26` but missing from the review-core consumer doc.
- **Source**: codebase + user

## Decision 4: SIMPLE tier scope discipline
- **Question**: What's out of scope?
- **Resolution**: Three targeted edits only — (1) harness pairing assertion, (2) review-core.sh empty-ballot short-circuit reuse, (3) review-core.md doc-line update. No refactors to `aggregate-findings.sh`, no changes to `dispatch-code-voters.sh`, no changes to `dispatch-plan-review-panel.sh` production wiring.
- **Source**: user (SIMPLE tier discipline)
