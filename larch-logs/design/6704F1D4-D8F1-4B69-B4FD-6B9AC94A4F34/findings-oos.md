### OOS_1:
- **Description**: Failure-mode text ties stale grouped relaunches to rising FALLBACK_COUNT. Scenario: FALLBACK_COUNT only increments phase-3 Claude launches (scripts/dispatch-with-waterfall.sh:517-524), so repeated phase-2 Codex relaunches from stale rows will not trip LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD; operators may miss cost regressions
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: plan.txt:90-95
- **Phase**: design

