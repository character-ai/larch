## Decision 1: Skill scope
- **Question**: The issue guesses /implement and /review are "likely" affected too. Code inspection shows /implement Step 5 and /review already emit per-substep breadcrumbs; only /design's plan-review (Step 3) lacks them. Scope the fix to which skills?
- **Resolution**: /design only. Add the missing sub-step breadcrumbs to the /design plan-review round to reach parity with the code-review path. Do NOT modify /implement or /review; they already emit these breadcrumbs.
- **Source**: user

## Decision 2: Breadcrumb granularity
- **Question**: Which review sub-steps should each emit an individual status line?
- **Resolution**: Full set matching the code-review path: launching reviewers, collecting reviewer outputs, aggregating findings, dispatching voters, tallying votes.
- **Source**: user

## Hard constraints (from codebase inspection)
- The status line renders only the tail of the clone-scoped progress log (`python/larch/report/statusline.py`), so each new breadcrumb overwrites the visible line. Breadcrumbs are best-effort file appends via `progress_file.append_breadcrumb`; failures must stay silent.
- The plan-review round (`python/larch/review/plan_review_round.py::execute_round`) runs in-process inside the Step 3 background bgjob. Its stdout is captured to a buffer, but breadcrumbs write to a file, so they are unaffected.
- Do NOT alter the `KEY=value` stdout contract emitted by `_emit(...)`; breadcrumbs are a separate side channel.
- Match the established pattern and wording already used in `python/larch/review/review_core_body.py` (skill label "design", step "3").
