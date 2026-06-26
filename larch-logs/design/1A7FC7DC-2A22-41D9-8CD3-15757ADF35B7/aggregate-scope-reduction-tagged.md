### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:210-232
- **Concern**: [SCOPE-REDUCTION] Firm test-design-structure.sh recovery mirror duplicates test-implement-anti-polling-rule.sh while the mirror spec is incomplete. Scenario: Anti-polling already owns full negative pins (179-206) and positive split-branch pins (188-193); promoting test-design-structure.sh adds parallel maintenance without new coverage, and the truncated mirror block (224-225) is error-prone
- **Proposed resolution**: Drop the firm test-design-structure.sh anti-polling mirror (keep existing design-structure concerns only) or, if retained, paste lines 183-193 verbatim into that subsection and drop duplicate assertions from the anti-polling harness only after parity is explicit
