### FINDING_2: SessionStart mirror omits fail-open log redirect
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Mirror contract omits fail-open log redirect from `sweep-design-logs.sh`. The plan requires mirroring `scripts/sweep-design-logs.sh` but only says to redirect hook output to a `${TMPDIR}` `larch-` log. It omits the paired `: >"$LOG" 2>/dev/null || LOG=/dev/null` guard. Under `set -euo pipefail`, a missing or unwritable `${TMPDIR}` can make the redirect/truncate fail before the hook reaches unconditional `exit 0`, blocking SessionStart.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Require the same fail-open log setup as `sweep-design-logs.sh` lines 17–18 (`|| LOG=/dev/null`), and pin it in `scripts/test-cleanup-sessionstart.sh` source assertions.


Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: [OUT_OF_SCOPE] Per-process unlink for validate-plan-commands mkstemp fallback
- **Description**: [OUT_OF_SCOPE] Per-process unlink for validate-plan-commands mkstemp fallback. Scenario: Outside Claude Code, `plan validate` without `DESIGN_TMPDIR` still leaves `larch-validate-plan-commands.log.*` at `$TMPDIR` top level until manual `/larch:cleanup` or a 7-day SessionStart sweep. SessionStart-only mitigation is enough for the plugin hook path; per-process try/finally is optional hardening for headless CLI.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/design/_plan_quality_commands.py:887
- **Phase**: design

Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

