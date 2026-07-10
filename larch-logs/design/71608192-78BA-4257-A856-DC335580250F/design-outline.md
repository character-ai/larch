## Proposed Design Outline

### Goals
- Adopt the GPT-5.6 Codex family (`sol`/`terra`/`luna`) with difficulty-conditional routing for the /implement coder, Step 5 reviewer panels, and finding voters.
- Refresh the three fixer waterfalls (CI recovery, review-fix, plan revision) and keep pricing/reporting couplings coherent so cost reports never KeyError or mis-bucket.

### Non-goals
- No composition changes to design-side panels/voters (`design.plan_review_panel`, `design.decompose_panel`, `design.plan_voters`) beyond inherited role defaults.
- No Cursor model changes beyond the named `auto` pins; effort stays `high`; no third pricing display bucket.

### Approach sketch
- One mechanism carries most routing: extend the `resolve_model_args` role path to honor `default_model` (precedence env > `default_model` > role default) in `_launch_failure.py`.
- Add difficulty→model maps and change role-default constants in `core/config.py`; thread a new `--difficulty` flag through the Step 2 Codex launcher and its dispatch caller.
- Panel/voter/fixer sites pass `default_model=<by-difficulty>[tier]`; reorder the CI-recovery and plan-revision vendor waterfalls; pin the named Cursor `auto` and Claude `[1m]` launch args.
- Pricing: add three Codex rate rows, introduce a `CODEX_MINI_MODELS` membership set at six call sites, strip `[1m]` at record time, bump the `Codex-5.5`→`Codex-5.6` display label.
- Round out with plugin.json option text, doc refreshes, test expectations, and the WI-12 verification checklist.

### Surfaces in scope
- `python/larch/core/config.py`, `agents/_launch_failure.py`, `agents/_ci_launcher.py`, `agents/_review_launcher.py`, `calibration/difficulty.py`, `design/plan_quality.py`
- `report/report_tokens_cost.py`, `report/final_report.py`, `design_summary.py`, `progress_report.py`, `analysis/codex_role_costs.py`, `git/pr_body.py`
- `.claude-plugin/plugin.json`; docs (`configuration-and-permissions.md`, `external-reviewers.md`, `review-agents.md`, `voting-process.md`); `skills/implement/SKILL.md` + `references/step2-dispatch.md`
- Tests under `python/tests/agents/`, `python/tests/report/`, and `python/analysis/test_codex_role_costs.py`

### Open questions
- None. Model ids/prices are taken as the issue's source-of-truth; authoritative verification is the WI-12 live probes at /implement time.
