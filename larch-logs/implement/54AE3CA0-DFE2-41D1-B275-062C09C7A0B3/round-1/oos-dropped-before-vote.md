### OOS_1: [OUT_OF_SCOPE] Step 5 pre-round window allows stale ship-pr fallback
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: After stall recovery, a short window remains where the Step 5 timing mark exists but `round-N` is not created yet (`review_and_fix.py` writes the mark before `_persist_round_start`). If stale `ship-pr-state.sh` is still present, `_render_step5` returns `""` and the hook can still report ship-pr until round artifacts appear. This is pre-existing residual behavior; the diff does not widen it (before, ship-pr always won when the state file existed). The plan explicitly treats ship-pr as fallback when Step 5 has no renderable round evidence; this pre-round window is an accepted trade-off, not a regression from the reorder.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] Missing test for `progress/done` plus `ship-pr-state.sh` → ship-pr
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The plan calls out preserving “done + ship-pr-state → ship-pr”, and the new layout does that via the ship-pr check outside the done gate. There is no regression test for `progress/done` plus `ship-pr-state.sh`; only the no-ship-state path is covered (`test_step5_done_falls_through`). Behavior is preserved by placing the ship-pr branch outside the done gate, but coverage for done+ship-pr was not added and is not required for this fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a small test with `progress/done` plus `ship-pr-state.sh` and assert ship-pr output.

### OOS_3: [OUT_OF_SCOPE] `_render_step5` reports existing `round-N/` as in progress when `review-and-fix.env` exists
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `_render_step5` reports any existing `round-N/` as “in progress” even when `review-and-fix.env` exists. Pre-existing; unchanged by this diff. Forward progress to ship-pr relies on later timing marks (Step 6+) superseding Step 5, which is normal in `/implement`.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] `test_implement_stale_label_with_fresh_round_dir_triggers_step5` omits stale `ship-pr-state.sh`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test_implement_stale_label_with_fresh_round_dir_triggers_step5` exercises stale non-Step-5 marks with fresh round artifacts, but omits a stale `ship-pr-state.sh`. A partial revert (ship-pr before the stale-mark branch only) would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `ship-pr-state.sh` to that fixture and assert ship-pr text is absent.

### OOS_5: [OUT_OF_SCOPE] No test for Step 5 mark + stale ship-pr + no round directory → ship-pr fallback
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No test covers Step 5 mark + stale ship-pr + no round directory → ship-pr fallback. The plan calls this out as an edge case where ship-pr must still render.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a case with Step 5 mark and `ship-pr-state.sh` but no `round-*` dir; assert ship-pr output.

---

**Merge notes (not for machine output):**
- Input FINDING_1 + FINDING_3 → FINDING_1 (same pre-round ship-pr window).
- Input FINDING_2 + FINDING_4 + FINDING_11 → FINDING_2 (same missing done+ship-pr test).
- Input FINDING_5 → FINDING_3 (`round-N` in-progress with `review-and-fix.env`).
- Input FINDING_12 → FINDING_4 (stale-label test gap).
- Input FINDING_13 → FINDING_5 (no-round ship-pr fallback test gap).
- Input FINDING_6–FINDING_10 are affirmative implementation/test observations, not fixable risks; omitted from the finding list.
