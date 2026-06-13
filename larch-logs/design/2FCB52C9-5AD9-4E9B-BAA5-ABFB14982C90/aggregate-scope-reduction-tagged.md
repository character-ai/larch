### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:38-611
- **Concern**: [SCOPE-REDUCTION] Plan only instructs updating the Step 5 compose-review-findings note but leaves multiple live review-core.sh references in NEVER #4 and Step 5 prose. Scenario: After review-core.sh deletion bare review-core.sh prose in implement/SKILL.md survives path lint and misdirects operators to a removed entrypoint
- **Proposed resolution**: Expand the skills/implement/SKILL.md update to retarget all review-core.sh and compose-review-findings.sh references to python/cli.py review core and review compose-findings (including NEVER #4 and Step 5 panel prose)
