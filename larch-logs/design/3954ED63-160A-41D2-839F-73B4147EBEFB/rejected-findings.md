### [Plan Review] FINDING_11

### FINDING_11:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/design_lifecycle.py:2990-3439, python/agents.py:2793-3168, skills/design/SKILL.md:482-484, skills/design/references/plan-review.md:3-55, python/design_summary.py:167-245
- **Concern**: [SCOPE-REDUCTION] Design dynamic-archetype migration is outside the issue scope. Scenario: The issue and examples target /implement Step 5, especially main-agent emergency. The current design path already has the Step 2b drafter materialize scout-plan-manifest.json and Step 3 consume it, so the proposed design warnings, summaries, and docs add behavior not needed for the implement fix.
- **Proposed resolution**: Drop the firm design_lifecycle.py, design_summary.py, skills/design/*, and design scout test changes unless a separate design regression is demonstrated.


