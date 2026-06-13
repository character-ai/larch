## Decision 1: Dependency readiness
- **Question**: Are C1b, B1, B2 all landed and safe to depend on?
- **Resolution**: All three are CLOSED/DONE (#3677 C1b, #3670 B1, #3671 B2). Safe to proceed with full C2 scope.
- **Source**: codebase (review_pipeline.py exists; gh issue states)

## Decision 2: "In-process" definition
- **Question**: What does "no subprocess indirection between review and fix phases" mean given C1b's run_legacy() still shells out?
- **Resolution**: C2 calls review_pipeline.review_core(argv) as a direct Python function call instead of shelling out to review-core.sh. Even though run_legacy() still shells, the review-and-fix layer removes one subprocess hop. This matches the issue's framing.
- **Source**: codebase (review_pipeline.py run_legacy pattern; issue notes)

## Decision 3: Absorbed scripts scope
- **Question**: Are the test harnesses for absorbed scripts (test-review-and-fix.sh, test-check-review-changes.sh, etc.) also deleted?
- **Resolution**: Yes. Migration recipe step 6 says "Delete bash script + harness + .md siblings". All test-*.sh harnesses for absorbed scripts are deleted after pytest parity gate.
- **Source**: codebase (docs/python-migration.md recipe step 6)

## Decision 4: check-review-changes.sh call site
- **Question**: check-review-changes.sh is called from step-6-entry.sh. Must that call site be cut over in this issue?
- **Resolution**: Yes. "Direct call-site cutover (no shims)" is a DoD requirement. step-6-entry.sh gets updated to call python3 cli.py review-and-fix check-changes (or similar verb).
- **Source**: skills/implement/scripts/step-6-entry.sh:44 (direct caller)
