### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/agents/agent_waterfall.py:75-99
- **Concern**: [SCOPE-REDUCTION] Waterfall panel instrumentation needs an explicit opt-in flag, not default site alone. Scenario: `dispatch-waterfall` defaults `--site` to `review Step 2`. Decompose (`decompose.py:465-471`) and other non-panel callers omit `--site`, so site-based enablement would set `LARCH_PANEL_SLOT` on decompose/scout/autofix children and write stray `panel-prompt-sizes.tsv` outside the panel tier
- **Proposed resolution**: Add a required explicit flag (for example `--panel-artifact-dir` or `--panel-instrumentation`) to `Options`/argv. Set `LARCH_PANEL_*` only when that flag is present. Pass it only from plan-review, implement/review panel dispatch, and voter/aggregator callers; leave decompose, plan_scout, and plan-autofix paths unset
