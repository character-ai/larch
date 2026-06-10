### FINDING_1:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:10-20,69-98,144-162
- **Concern**: [SCOPE-REDUCTION] Plan adds deferred preflight stderr capture sanitize and quiet-aware replay plus acceptance items 5-6 and t-optb stderr tests beyond binding issue goals (Options A/B/C only). Scenario: Binding scope and approved outline require retry negative TTL and one-shot live fallback only; the temp-file defer/replay path and its tests add substantial check-reviewers complexity without being needed to stop transient preflight from skipping the live probe or caching false
- **Proposed resolution**: Remove acceptance 5-6 and t-optb-stderr-routing/t-optb-limited-negative replay assertions; on preflight exit 2 run setup plus one larch_run_one_cursor_probe without redirecting cursor_auth_preflight stderr (keep existing quiet-log routing) and write the stamp from the live outcome only
