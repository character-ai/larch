### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md
- **Concern**: [SCOPE-REDUCTION] Stale panel-failed Split-path contract survives the inline rewrite. Scenario: The plan removes panel dispatch from Split-path but does not list updates to SKILL.md panel-failed handling, finalize-step5-failures.md Split-path ownership prose, or scripts/test-design-structure.sh lines 613-614. Inline prepare failure also has no named SUMMARY_OUTCOME, leaving failed-judge-panel tied to a removed panel-retry flow.
- **Proposed resolution**: Remove Split-path panel-failed and Retry panel branches; name a single terminal outcome for inline prepare failure; update finalize-step5-failures.md and test-design-structure.sh accordingly; keep failed-judge-panel only for Step 3 panel-init-failed.
