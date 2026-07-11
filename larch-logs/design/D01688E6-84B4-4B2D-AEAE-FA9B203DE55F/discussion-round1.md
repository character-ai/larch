# Discussion Round 1: resolved decisions

## Decision 1: cursor_auto_cost blast radius (full removal)
- **Question**: Does removing the auto rate row + CURSOR_AUTO_MODEL also excise the downstream cursor_auto_cost field that spreads into the PR-body cost segment, the /report-tokens vendor-breakdown row, and the pr_body.py/final_report.py CURSOR_AUTO_COST KV schema field?
- **Resolution**: Full removal. Delete cursor_auto_cost from the cost-record/PR-body/final-report schemas, drop the "Cursor Auto" render row and the "(Auto Z)" PR-body segment, and update the affected tests (test_pr_body.py, test_final_report.py, test_report_tokens_render.py, test_report_tokens_cost.py). Old committed run logs keep their text; the lenient KV parse ignores stale CURSOR_AUTO_COST.
- **Source**: user

## Decision 2: #6825 blocker is resolved (landed)
- **Question**: Is the native blocker #6825 (Grok 4.5 coder switch + ("cursor","grok-4.5") rate row) still open, or landed?
- **Resolution**: Landed. Issue #6825 is [DONE]/closed (2026-07-10) via merged PR #6843. The grok-4.5 rate row, CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY, and MODERATE coder routing already exist on the current tree. The acceptance criterion "Grok 4.5 surfaces byte-identical before and after" is live and must be preserved. Plan rebases on current HEAD, not the v52.5.23 inventory in the issue body.
- **Source**: codebase

## Hard constraints (must not break)
- The generic per-slot cursor_model / --cursor-model plumbing from #6553 stays in place. Only auto producers are removed.
- The ("cursor","composer-2.5") rate row keeps its existing Token Rate surcharge values (0.75 input / 0.45 cache read / 2.75 output). Relitigating the surcharge is out of scope.
- Do NOT run retro_fix_cursor over committed run logs. Committed cost text stays as written.
- The forced plan-fidelity "plan-fidelity-forced": "architecture" tally mapping in review_dispatch_panel stays unchanged.
- Voter roles keep composer-2.5 with no behavior change.
- Grok 4.5 surfaces (#6825) must be byte-identical before and after.

## Explicit non-goals
- #6825 (already landed).
- Re-verifying or changing the composer-2.5 Token Rate surcharge.
- Retro-fixing committed run-log cost text.
- Removing the generic per-slot cursor_model plumbing.
- Codex and Claude lane models.
