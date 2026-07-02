### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/agents/agent_waterfall.py:75-99
- **Concern**: [SCOPE-REDUCTION] Waterfall panel instrumentation needs an explicit opt-in flag, not default site alone. Scenario: `dispatch-waterfall` defaults `--site` to `review Step 2`. Decompose (`decompose.py:465-471`) and other non-panel callers omit `--site`, so site-based enablement would set `LARCH_PANEL_SLOT` on decompose/scout/autofix children and write stray `panel-prompt-sizes.tsv` outside the panel tier
- **Proposed resolution**: Add a required explicit flag (for example `--panel-artifact-dir` or `--panel-instrumentation`) to `Options`/argv. Set `LARCH_PANEL_*` only when that flag is present. Pass it only from plan-review, implement/review panel dispatch, and voter/aggregator callers; leave decompose, plan_scout, and plan-autofix paths unset


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: [OUT_OF_SCOPE] Cursor launches measure the pre-preamble resolved prompt, not the strict preamble bytes actually sent on the wire.
- **Description**: [OUT_OF_SCOPE] Cursor launches measure the pre-preamble resolved prompt, not the strict preamble bytes actually sent on the wire.. Scenario: Logging after _review_resolve_prompt but before _review_launch_cursor omits _CURSOR_REVIEW_STRICT_PREAMBLE from prompt_bytes, so Cursor panel-tier totals undercount a large share of lifetime tokens; rankings by agent_file stay directionally useful but are not fully realized.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/agents/_review_launcher.py:1195-1200
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

