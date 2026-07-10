## Goal
Implement issue #6784: [IMPLEMENTING] /design and /implement status report breadcrumbs in review phase should always report review round in every breadcrumb.

## Implementation Plan
## Plan

### Approach

- Keep the change narrow. Do not change `_progress_note`, `_run_cli_with_progress`, or `append_breadcrumb` signatures.
- Prefix every review-phase sub-phase breadcrumb with `f"round {round_num}: ..."`.
- Leave outer-loop breadcrumbs unchanged (`review round {round_num} running`, `review round {round_num} done: ...`, `round {round_num} launched`, `round {round_num} complete with ...`) because they already include the round number.
- **Accepted finding (FINDING_1):** The first Step 5 sub-phase breadcrumb at `review_core_body.py:833` (`reviewer panel dispatch running`) must receive the same `round {round_num}:` prefix as all later sub-phase breadcrumbs. Without it, the Step 5 breadcrumb stream starts without a round marker while later entries are prefixed.
- Before editing, inventory all `_progress_note(step="5", ...)` call sites in `_review_core_body` and confirm each sub-phase string is prefixed. Re-grep after edits to catch any missed site.

### Files to modify/create

### UPDATED: python/larch/review/review_core_body.py

- In `_review_core_body`, prefix each Step 5 review sub-phase `_progress_note` `text=` with `f"round {round_num}: ..."`:
  - **`reviewer panel dispatch running`** (line 833 — first sub-phase breadcrumb; required by FINDING_1)
  - `launching reviewers`
  - `collecting reviewer outputs`
  - `reviewers X/Y done`
  - `checking reviewer failure threshold`
  - `aggregating reviewer findings`
  - `dispatching 3 voters`
  - `tallying votes`
  - both `post-fix checks running` calls
  - `voting done A/B accepted`
- Preserve all branch behavior and return values. Breadcrumbs on early-return paths (e.g. dispatch failure immediately after line 833) must still emit the prefixed text before the return.

### UPDATED: python/larch/review/plan_review_round.py

- In `execute_round`, prefix each `_run_cli_with_progress(..., text=...)` value with `f"round {round_num}: ..."`:
- Do not change `_run_cli_with_progress` itself.

### UPDATED: python/larch/review/plan_review.py

- In `_run_post_apply`, prefix:
  - `plan-review post-apply running`
  - `plan-review awaiting continuation`
- In `_run_dedup`, prefix:
  - `plan-review dedup running`
- Leave `round {round_num} launched` and `round {round_num} complete with ... accepted` unchanged.

### UPDATED: python/tests/review/test_plan_review_round.py

- Update `test_execute_round_records_progress_breadcrumb_sequence` expected breadcrumb text to include `round 1: ` for all five asserted entries.
- Keep the test focused on the existing public behavior: the breadcrumb text emitted by `execute_round`.

### Edge cases

- Breadcrumb sanitizer still rejects invalid text. The added prefix uses fixed ASCII text and a positive integer.
- Round 2 and later should show the live `round_num`, not a hardcoded value.
- Early-return paths should still include the round number for breadcrumbs emitted before the return (including dispatch failure after the line-833 breadcrumb).

### Failure modes

- A missed call site leaves mixed breadcrumbs in the review phase; the line-833 dispatch breadcrumb is the highest-risk miss because it is first in the stream.
- A typo in expected strings can hide a regression if the test is too broad. Keep exact tuple assertions.

### Testing strategy

- Run:
  - `python3 -m pytest python/tests/review/test_plan_review_round.py -k progress_breadcrumb_sequence`
- If time permits, run the changed review tests file:
  - `python3 -m pytest python/tests/review/test_plan_review_round.py`
- Post-edit verification: `rg '_progress_note\(step="5"' python/larch/review/review_core_body.py` and confirm every sub-phase `text=` includes `round {round_num}` (outer-loop callers in `review_and_fix.py` are out of scope).
- No full lint sweep is required for this narrow Python-only change.

## Acceptance

- Run:
  - `python3 -m pytest python/tests/review/test_plan_review_round.py -k progress_breadcrumb_sequence`
- If time permits, run the changed review tests file:
  - `python3 -m pytest python/tests/review/test_plan_review_round.py`
- Post-edit verification: `rg '_progress_note\(step="5"' python/larch/review/review_core_body.py` and confirm every sub-phase `text=` includes `round {round_num}` (outer-loop callers in `review_and_fix.py` are out of scope).
- No full lint sweep is required for this narrow Python-only change.

diff_lines: 35

## Test plan
(no test plan section in plan-file)
