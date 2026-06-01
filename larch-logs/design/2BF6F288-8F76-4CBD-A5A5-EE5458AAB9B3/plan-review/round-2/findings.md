### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-18b-final-report.sh:43-45
- **Concern**: Plan uses bare .step18-prebody and summary-final.md in cp/cmp without cd or $tmpdir prefixes. Scenario: Wrapper run from repo cwd leaves snapshot/cmp on wrong paths; EMIT_BODY true when body unchanged or false when it changed
- **Proposed resolution**: Wire paths as $tmpdir/.step18-prebody and $tmpdir/summary-final.md (or cd "$tmpdir" once and document it in step-18b-final-report.md)

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/stall-recovery-report.sh:79-90
- **Concern**: Plan reuses validate_ship_pr_state for clear-stall/seed-terminal-state but requires emitting CLEARED=false or SEEDED=false before exit 3. Scenario: validate_ship_pr_state calls exit 3 directly; orchestrator may see no machine KV and miss terminal routing
- **Proposed resolution**: Refactor to a non-exiting validator or emit CLEARED=false/SEEDED=false before any malformed-state exit 3 in cmd_clear_stall and cmd_seed_terminal_state

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/stall-recovery-report.sh (proposed cmd_clear_stall / cmd_seed_terminal_state)
- **Concern**: `set -euo pipefail` can exit before `CLEARED`/`SEEDED` KVs are emitted. Scenario: Plan requires `CLEARED=false` / `SEEDED=false` on temp-read, `mv`, or dest-read failure, but an uncaught `mktemp`, `awk`, or `read-session-env-key.sh` failure will abort the script without emitting the machine key; orchestrator then sees missing KV / non-zero and mis-routes (same class as failure mode 1)
- **Proposed resolution**: Wrap the write/read/mv chain in explicit `|| { emit_kv … false; exit … }` handlers (or a local err trap that emits then re-exits); do not rely on bare `set -e` alone

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/stall-recovery-report.sh:79-89
- **Concern**: Plan says reuse `validate_ship_pr_state` for `clear-stall` / `seed-terminal-state`, but that helper calls `exit 3` on malformed lines without emitting `CLEARED`/`SEEDED` first. Scenario: Recovery success path calls `clear-stall`; malformed `ship-pr-state.sh` exits 3 with no `CLEARED=` line, so the orchestrator treats the KV as missing and mis-routes (plan edge case expects `CLEARED=false` then exit 3)
- **Proposed resolution**: Wrap validation: on format failure emit `CLEARED=false` or `SEEDED=false` via `emit_kv`, then exit 3; or split validation into a non-exiting helper used only after the emit
