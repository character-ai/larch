### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:40-40
- **Concern**: [SCOPE-REDUCTION] Unknown-exit transient branch is broader than the issue needs and risks misclassifying positive child failures. Scenario: `dispatch_commit_route.py` always relays `EXIT_CODE` on `checks-child-failed`, but Step 18a item 3 only adds `--in-memory-stall-tracking` and never requires forwarding that KV to `stall-recovery classify`. The new `unknown` branch then classifies any `checks-child-failed` stall without `--exit-code` as `transient-infra`, so a real `EXIT_CODE=1` structural failure (no `REDACTED_LOG_FILE`) retries instead of staying `contract-failure`
- **Proposed resolution**: Remove the `unknown`-exit transient arm; in item 3 document passing `--exit-code "${EXIT_CODE}"` from the parsed checks-failed composite first line together with the in-memory stall flag and bail triplet. Bind `EXIT_CODE` in `skills/implement/references/checks-repair-loop.md` section 1 structural-stall routing (Step 3/6 today only parse `FAILURE_REASON` explicitly). Keep transient matching to negative integer exit codes only
