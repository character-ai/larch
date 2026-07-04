### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: BASH_AUTHORING.md
- **Concern**: Planned bounded-root guidance is scoped to background probes only, but the new lint and Approach text apply to every orchestrator grep-family path operand. Scenario: The bug report centers on a background runaway scan, but a foreground `command grep -r` with `$IMPLEMENT_TMPDIR/../../../..` can still walk the home directory. If BASH_AUTHORING keeps the rule under "Background grep-family probes," operators may treat foreground discovery greps as exempt and repeat the ascent mistake outside linted skill fences
- **Proposed resolution**: In the "Bounded search roots" subsection, state the rule for all orchestrator grep-family probes in Bash fences (or all such probes), not only background ones; keep the background stdin-blocking note separate from the parent-ascent ban



### FINDING_2:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/lint/lint_tier1a.py:10-15
- **Concern**: BASH_AUTHORING.md is already at its tier-1a line cap, but the plan adds a subsection without preserving or updating that cap. Scenario: After the proposed BASH_AUTHORING.md bullets are added, python3 python/cli.py lint tier1a-size reports BASH_AUTHORING.md over cap, so make lint and CI fail before the feature can ship
- **Proposed resolution**: Add a firm plan step to keep the BASH_AUTHORING.md edit line-neutral, or update TIER1A_LINE_CAPS with the intentional growth and include tier1a-size validation in the focused checks



