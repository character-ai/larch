## Proposed Design Outline

### Goals
- Remove the Cursor `auto` model from larch entirely. Every Cursor lane launches `--model composer-2.5` and panel manifests record `resolved_model=composer-2.5`.
- Delete the `("cursor", "auto")` rate row, the `CURSOR_AUTO_MODEL` constant, and all "Cursor auto" prose across code, docs, skills, and generated projections.
- Excise the downstream `cursor_auto_cost` schema and render surface (PR body, final report, `/report-tokens`), per the full-removal decision.

### Non-goals
- Do not relitigate the composer-2.5 Token Rate surcharge values (0.75/0.45/2.75); keep them.
- Do not run `retro_fix_cursor` over committed run logs; legacy cost text stays as written.
- Do not remove the generic per-slot `cursor_model` plumbing from #6553; only auto producers go. Codex and Claude lanes are untouched.

### Approach sketch
- Producer removal first: drop `cursor_model=CURSOR_AUTO_MODEL` overrides so Cursor reviewer slots resolve through the standard chain (`LARCH_CURSOR_MODEL` -> `CLAUDE_PLUGIN_OPTION_CURSOR_MODEL` -> `CURSOR_DEFAULT_MODEL`).
- Replace the two hardcoded fixer lanes (CI recovery, review-and-fix coder) with the standard `resolve_model_args("cursor", with_effort=True)` resolution.
- Rate layer: delete the auto rate row, the `cursor_auto` DisplayRates rate fields, and the `model == CURSOR_AUTO_MODEL` cost special case. Legacy `model="auto"` ledger rows fall back to `DEFAULT_VENDOR_MODEL["cursor"] = "composer-2.5"`.
- Full cost-record removal: drop `cursor_auto_cost` from the RunCost/RunRecord schemas, the "Cursor Auto" render row, and the PR-body "(Composer, Grok, Auto)" segment.
- Delete `CURSOR_AUTO_MODEL`; update doc_fallback strings, the Step 5 banner prose, topology.tsv, regenerate topology.md, and the pinned tests.

### Surfaces in scope
- `python/larch/core/config.py`
- `python/larch/review/{review_dispatch_panel,plan_review_panel,coder_runner}.py`
- `python/larch/agents/_ci_launcher.py`
- `python/larch/report/{report_tokens_cost,report_tokens_models,report_tokens_render,final_report}.py`
- `python/larch/git/pr_body.py`
- `skills/implement/SKILL.md`, `skills/shared/topology.tsv`, `docs/topology.md`, `docs/review-agents.md`
- Tests: `test_external_role_defaults.py`, `test_external_dispatch.py`, `test_plan_review_panel.py`, `test_report_tokens_cost.py`, `test_report_tokens_render.py`, `test_final_report.py`, `test_pr_body.py`

### Open questions
- None.
