## Proposed Design Outline

### Goals
- Emit `NEXT_ACTION=` from `normalize-status` (stdout + persisted `.step3-review-result.env`) as the single routing directive for the Step 3 post-loop matrix.
- Collapse the 12-case "Post-loop branch matrix" in `SKILL.md` to a thin `NEXT_ACTION` lookup table.
- Remove the parallel "Legacy single-round `LOOP_STATUS` mapping" prose from `SKILL.md` and the "Loop mode / Legacy `--mode single` only" splits from `approval-gates.md`.

### Non-goals
- Changing the existing loop status values (`STEP3_REVIEW_LOOP_STATUS`) or the loop logic itself.
- Moving sentinel double-gating (`step-3-terminal` / `step-3` checks) out of SKILL.md prose.
- Removing `--mode` from `plan_review.py`'s argparse (it stays for backward compat; only prose referencing it as a routing path is removed).

### Approach sketch
- Add `_step3_status_to_next_action()` helper in `python/plan_review.py` mapping each `STEP3_REVIEW_LOOP_STATUS` value to a `NEXT_ACTION` token.
- Emit `NEXT_ACTION=` in `step3_loop_emit_envelope` (stdout) and `step3_loop_persist_envelope` (result env) and `normalize_step3_status_main` (via `_step3_emit_normalize_envelope`).
- Update `test-step3-review-cap.sh` and `test-step3-orchestrator-fence.sh` harness pins **before** editing prose.
- Rewrite SKILL.md "Post-loop branch matrix" → compact `NEXT_ACTION` table; delete "Legacy single-round" section.
- Simplify `approval-gates.md` shared post-apply pipeline steps 9-10 and "Step 3 outcomes" to loop-only path.

### Surfaces in scope
- `python/plan_review.py`
- `python/test_plan_review.py`
- `skills/design/SKILL.md`
- `skills/design/references/approval-gates.md`
- `skills/design/scripts/test-step3-review-cap.sh`
- `skills/design/scripts/test-step3-orchestrator-fence.sh`

### Open questions
- None.
