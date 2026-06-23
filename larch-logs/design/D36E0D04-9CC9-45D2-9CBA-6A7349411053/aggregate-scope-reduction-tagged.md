### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/shared/reviewer-templates.md:245-248 and python/rendering.py:116-129
- **Concern**: [SCOPE-REDUCTION] Plan injects identical OOS cap/materiality blocks in four GENERATED_BODY sections, five hand-maintained agents, `_dynamic_agent_body`, and `_specialist_tagging`/`render_plan_review_main`. Scenario: Every `/implement` specialist prompt loads agent/pre-rendered body then appends `_specialist_tagging`; dynamic slots always go through `render specialist` after `_dynamic_agent_body`. Duplicating the cap block 2x per reviewer adds vendor tokens while the issue targets OOS over-production waste.
- **Proposed resolution**: Keep one proposal-time source: `rendering._oos_proposal_instruction()` wired into `render_plan_review_main` and `_specialist_tagging` only. In templates/agents, replace contradictory uncapped-finding sentences (round-1 FINDING_2) but omit redundant `### Out-of-Scope Observations` cap bullet triplets. Drop `_dynamic_agent_body` cap injection unless a path renders dynamic agents without `_specialist_tagging` (none today).
