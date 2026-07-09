## Proposed Design Outline

### Goals
- Emit one status-line breadcrumb per /design plan-review sub-step, so Step 3 updates instead of staying on "round N launched".
- Reach parity with the code-review path, which already emits these breadcrumbs.

### Non-goals
- No changes to /implement or /review; they already emit per-substep breadcrumbs.
- No change to the status-line renderer, the progress-file format, or the `KEY=value` review contract.

### Approach sketch
- Add a local `_progress_note(step, text)` helper in `python/larch/review/plan_review_round.py`, mirroring the one in `review_core_body.py`.
- Insert 5 breadcrumb calls in `execute_round` before each sub-step: launching reviewers, collecting reviewer outputs, aggregating findings, dispatching voters, tallying votes.
- Reuse the established wording from the code-review path; skill label "design", step "3".

### Surfaces in scope
- `python/larch/review/plan_review_round.py` (execute_round plus helper and import).
- `python/tests/review/test_plan_review_round.py` (breadcrumb-sequence test).

### Open questions
- None.
