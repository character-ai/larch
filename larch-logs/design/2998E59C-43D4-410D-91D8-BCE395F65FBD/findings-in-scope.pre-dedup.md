### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: Makefile
- **Concern**: The Makefile split calls timing wrapper use optional on new direct Bash shard leaves. Scenario: Every existing shard-bound harness uses `python3 python/cli.py timing harness-mark --label $@`; marking the wrapper optional lets new delegation smokes ship without `LARCH_HARNESS_TIMING` rows, so `python/harness_ci_timing.py` cannot attribute the four migrated families and future rebalance evidence stays incomplete
- **Proposed resolution**: Require each new direct Bash shard leaf to use the same `python3 python/cli.py timing harness-mark --label $@ -- bash …` pattern as `write-final-report-bash-harness`; drop “optionally wrapped” wording in the Makefile section



