### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/stall-recovery-report.sh:226-237
- **Concern**: [SCOPE-REDUCTION] REPORT_DEDUP_SIGNATURE seeds dispatcher and matched_classifier for terminal-failure. Scenario: Req 4 targets one upstream issue per larch regression across consumer fleets; dispatcher follows implementer waterfall (codex/cursor/claude) and classifier pattern can vary with evidence shape, so identical defects hash differently and dedup creates duplicate upstream issues
- **Proposed resolution**: Remove dispatcher and matched_classifier from terminal-failure REPORT_DEDUP_SIGNATURE seed; keep report_kind, failure_class, step, phase, and safe bail token only unless a harness case proves cross-fleet stability
