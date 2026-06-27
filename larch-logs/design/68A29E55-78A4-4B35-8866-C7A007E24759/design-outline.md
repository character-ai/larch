## Proposed Design Outline

### Goals
- Fix `DISPATCH_OK` in the full-panel `dispatch_voters` path to reflect actual effective-judge count, not solely Claude voter health.
- Ensure the tally runs and findings survive when ≥1 vendor voter (Codex or Cursor) produces substantive output, even if Claude fails transiently.
- Add a regression test: voter_1 fails, voter_2+3 succeed → DISPATCH_OK=true, exit 0.

### Non-goals
- Retry logic for transient Claude voter errors (separate hardening).
- Surfacing voter-phase failure in the reviewer-status table (separate UX improvement).
- Investigating `--permission-mode plan` + ANTHROPIC_API_KEY interaction (separate investigation).
- Changes to `plan_review_round.py` (fixing panel.py DISPATCH_OK is sufficient).

### Approach sketch
- Change one expression in `plan_review_panel.py` `dispatch_voters` (full-panel path) line ~1054: from `"false" if voter_1_status == "failed"` to `"true" if effective > 0`.
- `effective` is already computed at line 1000 via the `voting effective-judges` subprocess; no new computation needed.
- The return code logic (`return 0 if dispatch_ok == "true" else 1`) is unchanged — effective=0 still exits 1.
- Add one monkeypatched unit test in `test_plan_review_panel.py` following the existing pattern.

### Surfaces in scope
- `python/larch/review/plan_review_panel.py` — 1 expression changed.
- `python/test_plan_review_panel.py` — 1 new test function added (~50 lines).

### Open questions
- None.
