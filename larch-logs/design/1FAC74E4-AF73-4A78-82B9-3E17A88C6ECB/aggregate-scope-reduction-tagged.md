### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/rebase.py:240-289
- **Concern**: [SCOPE-REDUCTION] The plan reimplements the entire run_waterfall tier loop inline instead of extending run_waterfall with a small post-success hook for driver staging and unmerged-path verification.. Scenario: A second copy of first-tier short-circuit, health continuation, and paths_delta_revert logic will drift from agents.run_waterfall (already covered by test_agents.py), producing conflict-resolution behavior that diverges from CI/lint fixer semantics after future waterfall tweaks.
- **Proposed resolution**: Prefer extending run_waterfall with optional on-success staging plus unmerged-path gating (continue to next tier when markers remain), and keep rebase.py diff limited to removing bump prepass plus wiring the hook; retain the new staging tests without duplicating the full loop body.
