### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step-16-17.sh:1-40
- **Concern**: [SCOPE-REDUCTION] New `---LARCH-SUMMARY-FINAL-BEGIN/END---` markers duplicate an existing cross-skill handoff pattern. Scenario: `/design` already standardizes on whole-line `LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END` in `skills/design/scripts/design-step-final-summary.sh` and marker-extraction prose in `skills/design/SKILL.md`; a second marker grammar adds parser/orchestrator divergence and extra harness pins without changing behavior
- **Proposed resolution**: Reuse the design marker literals in `step-16-17.sh` and `skills/implement/SKILL.md`; keep implement SKILL bash fences marker-free per `scripts/test-implement-structure.sh:215-229`
