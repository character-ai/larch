### FINDING_1: Remaining leak sites not traced to plan closure
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Issue repro scenario 3 and two other cited leak sites are not traced to a fix. The binding issue lists five remaining leak sites and repro scenario 3 (no-session `plan validate` via `_plan_quality_commands.py:887`), plus `scripts/sweep-design-logs.sh:17` and top-level quiet-log writes, as still-unmet criteria. The plan only details report-tokens hygiene and SessionStart wiring and explicitly skips `_plan_quality_commands.py` and `sweep-design-logs.sh` changes. It never states that those artifacts are closed by automatic `cleanup run` matching `larch-*` with 7-day retention, so an implementer cannot verify full issue closure from the plan alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add Approach/Edge cases bullets mapping `larch-validate-plan-commands.log.*`, `larch-sweep-design-logs-*.log`, and `larch-quiet-*.log` to SessionStart `cleanup run` (`larch-*`, default 7-day retention), explicitly closing issue sites 3–5 and repro scenario 3 without per-site try/finally.

### FINDING_2: SessionStart mirror omits fail-open log redirect
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Mirror contract omits fail-open log redirect from `sweep-design-logs.sh`. The plan requires mirroring `scripts/sweep-design-logs.sh` but only says to redirect hook output to a `${TMPDIR}` `larch-` log. It omits the paired `: >"$LOG" 2>/dev/null || LOG=/dev/null` guard. Under `set -euo pipefail`, a missing or unwritable `${TMPDIR}` can make the redirect/truncate fail before the hook reaches unconditional `exit 0`, blocking SessionStart.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Require the same fail-open log setup as `sweep-design-logs.sh` lines 17–18 (`|| LOG=/dev/null`), and pin it in `scripts/test-cleanup-sessionstart.sh` source assertions.
