### FINDING_18:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/assess-plan-round.sh:21-28,127
- **Concern**: [SCOPE-REDUCTION] Plan deletes the existing --design-classification helper option instead of preserving it as a compatibility no-op. Scenario: Any direct or downstream caller that still passes the documented option will start failing with unknown option, and the extra caller/docs/test churn is not required to run the SIMPLE assessor
- **Proposed resolution**: Keep --design-classification HARD|SIMPLE accepted and validated but ignored; remove only the tier skip and stop relying on the value for behavior
