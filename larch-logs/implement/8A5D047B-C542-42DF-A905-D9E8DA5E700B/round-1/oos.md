### FINDING_1: [OUT_OF_SCOPE] reserved gantt rows can exceed the cap
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-gantt-fallback
- **Severity**: major
- **Concern**: When reserved `*/apply` and phase2/phase3 rows alone exceed `PROGRESS_GANTT_ROW_CAP`, `_cap_gantt_rows_reserving_apply` can return more than the cap, and the overflow case is not covered by a multi-reserved regression test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Only if overflow becomes common: truncate reserved rows by latest start time after reserving the earliest N fallback/apply slots, or document the soft cap.
  - From cursor-specialist-testing: Only if saturated rounds with many reserved rows become realistic; add an explicit overflow test or cap reserved rows.
  - From dyn-dyn-gantt-fallback: After collecting reserved rows, if `len(reserved_rows) > cap`, apply a deterministic sub-cap policy (for example, keep all apply rows, then newest or per-slot phase2/phase3 rows, then fill to `cap`); otherwise keep the current `non_reserved[:budget] + reserved_rows` path and assert `len(kept) <= cap` before return.


Vote tally: YES=1 NO=1 JUDGE_ERROR=1 Result=neutral Fileable=false

### FINDING_3: [OUT_OF_SCOPE] raw phase2/phase3 basename hits skip reconciliation
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-gantt-fallback
- **Severity**: minor
- **Concern**: Exact raw-basename manifest hits for `-phase2`/`-phase3` rows return before vendor reconciliation and fallback labeling, so a manifest that ever keyed those basenames directly could misattribute the vendor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: No change unless manifests start keying phase2 basenames directly; then reconcile vendor on raw hits before returning.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_4: [OUT_OF_SCOPE] live gantt path still omits failed primary attempts
- **Reviewer(s)**: dyn-dyn-gantt-fallback
- **Severity**: minor
- **Concern**: The live/inflight gantt path still filters on complete status, so failed primary attempts are omitted during Step 5 monitoring.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

