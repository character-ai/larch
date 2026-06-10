### FINDING_1:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:13,380-383; skills/upgrade-larch/scripts/upgrade-larch.sh:7-16
- **Concern**: [SCOPE-REDUCTION] Plan ports scripts/lib-larch-dev-clone.sh into upgrade_larch.py even though /upgrade-larch does not source or call that library. Scenario: Implementation adds unused Python code and tests outside the small-skill execution path while the live shell library must remain for check-stale-plugin.sh and stall-recovery-report.sh
- **Proposed resolution**: Drop scripts/lib-larch-dev-clone.sh from the upgrade_larch.py port; keep the shell library live and out of python/migrated-scripts.tsv until its actual consumers migrate
