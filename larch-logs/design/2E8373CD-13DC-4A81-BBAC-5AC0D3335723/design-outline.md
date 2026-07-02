## Proposed Design Outline

### Goals
- When both externals were healthy at Step 0 but zero survive by the review stage, do a loud-warned main-agent self-review instead of an unreviewed bypass (`/design`) or a stall (`/review`, `/implement` Step 5).
- Remove the Codex/Cursor panel from `/implement` conflict-resolution Phase 3 (`ship_pr_pre_push` non-trivial path); main agent self-reviews resolutions, keeping the 2-round retry cap.

### Non-goals
- Do not change the Step 0 degraded-tools gate's hard-fail-both-down behavior.
- Do not change voter fallback (single-Claude-voter-when-Cursor-unavailable already exists).
- Do not extend `audit_runs.py` / `final_report.py` analytics for the new paths beyond the existing `execution-issues.md` warning; that is a follow-up.

### Approach sketch
- `/design` Step 3: on `LOOP_STATUS=degraded-empty-collector`, main agent reviews and directly revises `plan.txt`, warns loudly, then proceeds via the existing Step 3b-bypass destination.
- `/implement` Step 5: route the zero-survivor branch of `panel-failed` into the existing `--self-review` inline procedure instead of stalling as a Tool Failure.
- `/review`: add a new main-agent self-review pass, modeled on `/implement`'s, triggered by the same zero-survivor branch.
- Conflict-resolution Phase 3: drop reviewer launch and voting; main agent reviews its own resolution from the existing per-file context blocks.

### Surfaces in scope
- `python/larch/review/plan_review_round.py` (or sibling loop file) for the `/design` hook.
- `python/larch/review/review_core_body.py`, `review_threshold.py` for the shared `/review`/Step 5 coverage-gate branch.
- `skills/implement/references/self-review.md`, `skills/implement/SKILL.md` Step 5 wiring.
- `skills/review/SKILL.md` plus a new self-review reference for `/review`.
- `skills/implement/references/conflict-resolution.md` Phase 3.
- `skills/shared/external-reviewers.md` for the documented contract.

### Open questions
- None. Step 1c resolved the architectural forks; two low-stakes scope assumptions are recorded in `discussion-round1.md`.
