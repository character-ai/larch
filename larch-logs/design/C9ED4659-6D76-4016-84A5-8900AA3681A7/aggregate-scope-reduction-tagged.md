### FINDING_2:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: code-quality
- **Location**: scripts/test-implement-structure.sh:226-227
- **Concern**: [SCOPE-REDUCTION] Durable Bail harness pins widen the prompt-slimming change beyond the minimum-change scope. Scenario: The issue asks to relocate/compress prompt prose and run the existing structure harness. The current plan adds new Durable Bail assertions for override prose, literal --stall-tracking true, and present-state STALL_TRACKING=true even though the feature can ship with the relocated reference prose alone. This converts an OOS hardening idea into required scope and adds new brittle prompt-prose test surface.
- **Proposed resolution**: Remove the Durable Bail harness-pin bullets from the plan. Keep only the necessary structure-harness update that repoints the existing folded-site recapture assertion from SKILL.md to checks-repair-loop.md.
