### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:3372-3381
- **Concern**: Postbump Phase 1–4 handoff omits ship-pr-rrr-after-phase14.flag write. Scenario: After conflict-resolution Phase 4, --resume-phase ship-pr-rrr-phase14-postbump may replay drop/rebase or die_usage without the flag; run_rebase_rebump only skips to _run_rebase_rebump_from_step3 when the flag exists (3159-3164)
- **Proposed resolution**: Mirror the CI non-bump path: touch ship-pr-rrr-after-phase14.flag before exit 5; require that flag in the new ship-pr-rrr-phase14-postbump resume arm before the deferred re-bump tail and force-push-gate

