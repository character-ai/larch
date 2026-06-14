### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:16-40
- **Concern**: [SCOPE-REDUCTION] Design delivery contract requires Read of background-task output plus in-orchestrator marker slicing even though wrappers already mirror the same body to disk via emit_final_summary_marked_from_disk in design-step5c.sh and design-step-final-summary.sh. Scenario: Orchestrators must learn marker parsing in prompt while the on-disk final-summary.md already holds the identical body; extra prose at seven emit sites without fixing the original failure mode (partial chat emission)
- **Proposed resolution**: Primary rule after notification: Read ${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md} then write the full file as orchestrator chat text; optionally Read $DESIGN_TMPDIR/design-report-gate-sidecars.md when non-empty. Keep marker emission in wrappers unchanged; drop task-output marker slicing from SKILL prose
