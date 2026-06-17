## Proposed Design Outline

### Goals
- Chart the fix-applying coder on every per-round reviewer-timing Gantt, across `/implement`, `/review`, and `/design`.
- Close the post-vote gap so the charted window matches the round-meta `type=round` duration.
- Keep the chart readable: agents only, existing 25-row cap, no CI noise.

### Non-goals
- Do not chart post-apply CI-fix/CI-test verification rows (stay excluded).
- Do not add new instrumentation for agents with no vendor row today (e.g. main-agent vote adjudication).
- Do not redesign the round table, top-N reviewers, failed-slot counts, or cost columns.

### Approach sketch
- Emit a chartable `type=vendor` apply row from the cursor coder: add `--timing-task-kind cursor-review-fix` to `_run_coder_cursor` in `python/review_and_fix.py`.
- Confirm `_run_coder_codex`'s existing `codex-review-fix` row reaches the round-windowed ledger; fix the emit if it does not.
- Emit the analogous apply row from the `/design` plan-revise apply path (`plan revise-waterfall`).
- In `render-review-phase-detail.sh`, relax `skip_gantt_row` so `*-review-fix` apply kinds chart; keep excluding only true CI/launcher-probe noise; label apply bars clearly (e.g. `codex/apply`, `cursor/apply`).
- Update the `.md` contract and add harness coverage that an apply bar renders and degrades gracefully when no apply ran.

### Surfaces in scope
- `scripts/render-review-phase-detail.sh`, `scripts/render-review-phase-detail.md`
- `python/review_and_fix.py` (`_run_coder_cursor`; verify `_run_coder_codex`)
- `/design` apply path: `skills/design/scripts/review-design-step3-loop.sh` + `plan revise-waterfall` timing emission
- Tests: `scripts/test-render-review-phase-detail.sh`, `python/test_review_and_fix.py`, `python/test_progress_report.py`

### Open questions
- Does `agent run-external-agent` (cursor coder launcher) accept `--timing-task-kind` and write a windowed vendor row? Confirm during drafting; if not, route the cursor apply timing through whatever writer the codex path uses.
- Does the `/design` `plan revise-waterfall` vendor call already emit a windowed `type=vendor` row? Confirm and add a distinct kind if missing.
