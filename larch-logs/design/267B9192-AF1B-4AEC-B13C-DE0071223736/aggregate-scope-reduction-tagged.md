### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/plan_review.py:1143-1147; plan.txt:41,87-91
- **Concern**: [SCOPE-REDUCTION] Plan still regenerates tally-plan-review.sh although tally_plan_review() is in-process only and never runs the embedded bash. Scenario: tally_plan_review() returns plan_review_tally.main(list(argv)) and the comment states the gzip blob is retained but not executed. Re-encoding that blob changes hundreds of base64 lines with zero runtime effect; the only driver is the planned global quiet-before-validate test that scans every asset containing larch_quiet_init
- **Proposed resolution**: Drop skills/design/scripts/tally-plan-review.sh from the nine-script regen list. Scope the global invariant test to _LEGACY_ASSETS keys whose live Python entrypoints still call _run_legacy for that path (exclude tally explicitly), or add a small dead-asset denylist in the test so pytest does not force dead-blob churn
