### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:35
- **Concern**: [SCOPE-REDUCTION] Approach promises broad prompt-prose resync beyond firm file list. Scenario: Approach says to update prompt prose that hardcodes role defaults, but firm `Files to modify/create` only updates `skills/design/references/brainstorm.md` and `docs/external-reviewers.md`. Prior review rejected sweeping `skills/design/SKILL.md` / `plan-review.md` / `voting-protocol.md` edits as unnecessary scope.
- **Proposed resolution**: The plan can pull a large markdown resync into scope without a consumer or CI pin, increasing diff size without advancing the registry goal. Narrow Approach item 35 to the two documented surfaces (brainstorm reference + docs table), or add explicit `MAY_UPDATE` rows for any additional prose files before claiming full prompt sync.
