# Review Round 2

- Mode: `diff`
- 3 accepted, 7 rejected (2 neutral)

## Accepted Findings

### FINDING_1: `_dynamic_evidence_in_manifest` false-positive without dropped-slots ledger
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-dyn-retry-warnings-output.txt
- **Severity**: important
- **Concern**: When `dropped_slots_file` is `None`, `_dynamic_evidence_in_manifest` can treat any `dyn-*` manifest row as straggler backstop evidence. A static-only straggler (`STRAGGLER_DROPPED_COUNT=1`, zero `DYNAMIC_*` counters) with scout dynamic slots in the panel manifest but no matching `*.dropped-slots` ledger can still emit a dynamic-drop warning while `DYNAMIC_FAILED_SLOTS` and `DYNAMIC_DROPPED_SLOTS` stay zero. `_run_round` passes `dropped_slots_file=None` when `round_dir.glob("*.dropped-slots")` is empty and does not fall back to dispatch `DROPPED_SLOTS_FILE`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-retry-warnings-output.txt: treat manifest-based backstop as qualified only when a readable dropped-slots ledger is present (or resolve the ledger from dispatch `DROPPED_SLOTS_FILE` before warning); if the ledger is missing, do not infer dynamic evidence from manifest rows alone.


### FINDING_4: Missing review-core integration test for 9-slot dynamic straggler threshold path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-generalist-output.txt, dyn-dyn-threshold-accounting-output.txt, dyn-dyn-retry-warnings-output.txt
- **Severity**: important
- **Concern**: The plan-required review-core integration test is still absent. Unit and isolated threshold tests pass, but nothing drives `review core` with `STATIC_SLOT_COUNT=7`, `DYNAMIC_SLOTS=2`, `SLOT_COUNT=9`, a real `check-reviewer-failure-threshold`, dynamic dropped-slots ledger, and dispatch `STRAGGLER_DROPPED_COUNT` appended into `review-core-threshold.env`. Regressions in `SLOT_COUNT` → `--intended-slots`, `_append_threshold_dispatch_metadata`, or the end-to-end dispatch → threshold → retry-warning chain (#5499 wiring) would not be caught. `test_review_core_real_threshold_straggler_static_not_counted_as_failure` only pins the static-straggler exemption.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add review-core stub test: `STATIC_SLOT_COUNT=7`, `DYNAMIC_SLOTS=2`, `SLOT_COUNT=9`, dynamic dropped row, assert `review-core-threshold.env` has `INTENDED_SLOTS=9`, `FAILED_SLOTS=1`, `STRAGGLER_DROPPED_COUNT=1` from dispatch.
  - From codex-generalist-output.txt: Add the planned `test_review_core...` case with `STATIC_SLOT_COUNT=7`, `DYNAMIC_SLOTS=2`, `SLOT_COUNT=9`, one `dyn-dyn-lint-escalation` dropped row, real threshold execution, and assertions for `INTENDED_SLOTS=9`, `FAILED_SLOTS=1`, `DYNAMIC_DROPPED_SLOTS=1`, and appended `STRAGGLER_DROPPED_COUNT=1`.
  - From dyn-dyn-threshold-accounting-output.txt: Add the plan-specified review-core integration test using the default non-legacy `TEST_THRESHOLD` stub (real threshold CLI), a dispatch stub emitting `SLOT_COUNT=9` and `STRAGGLER_DROPPED_COUNT=1`, and assert the merged `review-core-threshold.env` contents after `_run_round`.
  - From dyn-dyn-retry-warnings-output.txt: add the missing integration test (real `check-reviewer-failure-threshold`, dynamic straggler drop, no collector record, assert threshold env KVs and one settled-round warning).


### FINDING_7: Missing threshold regression tests for synthetic/unresolvable dynamic drops
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-dyn-threshold-accounting-output.txt
- **Severity**: important
- **Concern**: Plan-required regression tests for synthetic/unresolvable dynamic drop basename handling and the collector-present + basename-miss carve-out are absent. Existing tests cover ERROR+drop double-count or collector-OK + resolvable straggler basename, but not the synthetic-key / `(slot, tool)` dedupe path at `review_pipeline.py:1971-1980` or the case where `FAILED_SLOTS=0`, `COUNTED_SLOTS=1`, `DYNAMIC_DROPPED_SLOTS=1` when collector OK pairs with an unresolvable drop for the same slot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add threshold test: manifest-mapped collector OK + unresolvable drop for same slot; assert `FAILED_SLOTS=0`, `COUNTED_SLOTS=1`, `DYNAMIC_DROPPED_SLOTS=1`.
  - From dyn-dyn-threshold-accounting-output.txt: Add focused threshold tests for (a) dropped-only dynamic row with manifest miss forcing synthetic `dyn-slot:{slot}:{tool}` counting when `(slot, tool)` is unseen, and (b) collector `OK` for manifest-mapped `(slot, tool)` plus a same-slot drop where basename dedupe must skip synthetic `count_once` while still incrementing `DYNAMIC_DROPPED_SLOTS`.


