## Proposed Design Outline

### Goals
- Make the final run summary the last text output of the turn in both `/design` and `/implement`.
- Prefix `DONE` and `STALLED` outcome tokens with status emoji (`✅`/`❌`).
- Add a placement rule to the shared emit contract so future call sites default to turn-final ordering.

### Non-goals
- Not changing how `final-summary.md` is generated or what it contains.
- Not fixing interleaved progress-reporting visibility (breadcrumbs, voting tallies) — separate follow-up if needed.
- Not adding a durable pointer/fallback; existing run-log and tracking-issue comment are sufficient.

### Approach sketch
- `/design`: Keep the `Read final-summary.md` in Step 5c (before `$DESIGN_TMPDIR` is deleted). Suppress emission there. After the Step 6 cleanup fence, emit the already-read content as the turn's last text.
- `/implement`: Write `.step17-emitted` and run Step 18 fences before emitting the marker body, inverting the current order. Step 18b already checks `.step17-emitted` to suppress double-emission.
- Add a "must be turn-final, no tool call after" rule to `skills/shared/final-summary-emit.md`.
- Extend `_map_outcome_display` in `python/larch/git/pr_body.py`; update `final_report.py` reconciliation to match `❌ STALLED` / `✅ DONE`.

### Surfaces in scope
- `skills/design/SKILL.md`
- `skills/design/references/finalize-step5.md`
- `skills/shared/final-summary-emit.md`
- `skills/implement/SKILL.md`
- `python/larch/git/pr_body.py`
- `python/larch/report/final_report.py`
- `python/larch/design/design_summary.py` (check degraded fallback)
- `python/tests/git/test_pr_body.py`, `python/tests/report/test_run_logs.py`
- `skills/implement/scripts/test-write-final-report.sh`
- `scripts/test-design-structure.sh`, `scripts/test-implement-structure.sh`

### Open questions
- None.
