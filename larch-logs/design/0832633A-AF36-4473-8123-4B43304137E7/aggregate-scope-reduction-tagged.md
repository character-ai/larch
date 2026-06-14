### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:912-936
- **Concern**: [SCOPE-REDUCTION] Missing-composed-plan special case should key off tmpdir file state, not log substring matching. Scenario: Plan routes the Step 5c sub-branch by grepping VALIDATE_LOG_FILE for an unpinned diagnostic string. python/plan_quality.py auto-fix treats an empty composed-plan.md as a valid --plan-file (plan.is_file()). If detection misfires, auto-repair can run and synthesize content without Step 5c item 1 composition (## Plan, ## Acceptance, diff_lines).
- **Proposed resolution**: At _publish_rc=4 with VALIDATE_STATUS=defects-found, branch on [[ ! -s "$DESIGN_TMPDIR/composed-plan.md" ]] before auto-repair: skip autofix, offer Fix-and-retry/Cancel only, and Fix-and-retry re-runs Step 5c item 1. Drop log-text matching from SKILL.md.
