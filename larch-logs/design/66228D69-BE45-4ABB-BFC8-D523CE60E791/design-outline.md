## Proposed Design Outline

### Goals
- Restore the `Step 2 — implementation` token mark on the live external-implementer path so Codex/Cursor coder tokens attribute to Step 2, not Step 0.
- Harden `.codex.per_step` consumers so a missing or misplaced mark cannot silently zero the coder-cost split again.
- Add regression coverage over the live launch route, not just the dispatcher.

### Non-goals
- No backfill or rewrite of already-committed historical run logs (fix forward only).
- No change to the mark label string `Step 2 — implementation` or the `Step 2 ` prefix contract.
- No change to the dispatcher timing-mark or claude/fallback token-mark behavior.

### Approach sketch
- Root cause: `launch_codex_implement_main` / `launch_cursor_implement_main` in `python/larch/agents/_ci_launcher.py` run the token-budget preflight but never emit `token mark "Step 2 — implementation"`; the dispatcher (`_maybe_mark_step2_telemetry`) defers that token mark to them on the external path.
- Emit the token mark in each launcher right after the budget preflight passes, best-effort (never abort the launch).
- Harden consumers so the coder split degrades loudly, not silently: explicit vendor-row labeling and/or a guard that flags a $0 coder split alongside nonzero external-vendor tokens.
- Leave the dispatcher timing mark and `_step2_token_mark_eligible` logic unchanged.

### Surfaces in scope
- `python/larch/agents/_ci_launcher.py`: external launcher token mark.
- `python/analysis/codex_role_costs.py`, `python/larch/report/tokens.py`: consumer hardening / guard.
- `python/tests/implement/test_implement_dispatch.py` and analysis/report tests: regression coverage for the live route.

### Open questions
- Exact consumer-hardening mechanism (explicit row labeling vs. a validation guard) to be settled in plan review.
