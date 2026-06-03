### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:68-80
- **Concern**: Implement session-env persistence does not export the gate env var to launchers. Scenario: `write-session-env.sh` writes plain KEY=VALUE lines that orchestrators parse with `read-session-env-key.sh`; it is explicitly not sourceable (`scripts/write-session-env.sh:26-28`). `/implement` and nested `/review` rehydrate only a small allowlist (e.g. `LARCH_TIMING_LEDGER` in `skills/implement/SKILL.md`) before external launches, and `launch-review.sh` does not read `SESSION_ENV_PATH`. Adding `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=30` to the file therefore leaves the gate OFF for the main production path unless every launch Bash block exports it.
- **Proposed resolution**: Enable production activation at the chokepoint: in `run-external-agent.sh` or `external_launch_health_gate`, when the var is unset/invalid, read `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT` from `$IMPLEMENT_TMPDIR/session-env.sh` (and/or `$SESSION_ENV_PATH` when set) via `read-session-env-key.sh`, or add the same read+export pattern used for `LARCH_TIMING_LEDGER` to implement Step 5 launch blocks. `/design` is already covered via sourceable `write-design-current-env.sh` exports.

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/write-session-env.md:3-4
- **Concern**: Production activation assumes session-env persistence alone wires the gate. Scenario: /implement never sources session-env.sh; post-Step-0 Bash blocks only rehydrate a small key set via read-session-env-key (skills/implement/SKILL.md:121). Writing LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT into session-env.sh leaves run-external-agent with an unset gate env, so Decision 2 does not apply on the main implement/review launch path despite the 30s default in the writer.
- **Proposed resolution**: In external_launch_health_gate (or run-external-agent.sh immediately before it), when the env var is unset/0/non-numeric, read LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT from $IMPLEMENT_TMPDIR/session-env.sh via read-session-env-key (IMPLEMENT_TMPDIR is exported on Step 2/5 blocks). Document the fallback in lib-external-launcher-common.md and write-session-env.md.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/write-session-env.sh:189-216 / skills/implement/SKILL.md:513-655
- **Concern**: Production enablement assumes persisting LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT in session-env writers activates the gate, but session-env.sh is not sourced and implement only rehydrates token/timing keys. Scenario: After write-session-env adds the key, /implement and nested /review Bash blocks still invoke launch-review.sh → run-external-agent.sh with an empty LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT, so the gate stays OFF and mid-run hangs remain
- **Proposed resolution**: Append the key in write-session-env CONTENT (not build_export), then read+export it in implement-bootstrap after write (mirror LARCH_TIMING_LEDGER) and add the same read+export to implement SKILL rehydration blocks that launch external reviewers

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/lib-external-launcher-common.sh (planned external_launch_health_gate)
- **Concern**: Plan orders unhealthy on outer timeout vs fail-open on missing parseable *_PRESENT, but does not require checking wrapper exit 124 before the fail-open branch. Scenario: A timeout/gtimeout kill can yield exit 124 and no CODEX_PRESENT/CURSOR_PRESENT line; treating that as infra fail-open proceeds with a 20–30m launch instead of fast-fail
- **Proposed resolution**: Specify in the helper contract: if wrapper exit is 124 (or 143), return unhealthy before the missing-line fail-open path

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: correctness
- **Location**: scripts/write-session-env.sh (plan ### UPDATED)
- **Concern**: Plan says to use build_export in write-session-env.sh; that writer only builds a KEY=VALUE CONTENT blob (build_export exists only in write-design-current-env.sh). Scenario: Implementer may call a nonexistent helper or skip the implement writer change
- **Proposed resolution**: Use the existing CONTENT+= pattern (same as LARCH_TIMING_LEDGER) for write-session-env; keep build_export only in write-design-current-env.sh

### FINDING_6:
- **Reviewer(s)**: Cursor-dyn-script-contract-verifier
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/write-session-env.md:3-4 / scripts/launch-review.sh:168-176
- **Concern**: Plan turns the gate on via session-env writers but implement/review never export that key into the environment run-external-agent reads. Scenario: The gate only checks LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT in the shell env. write-session-env.sh persists KEY=value lines that must not be sourced (write-session-env.md:3-4). /implement rehydration exports only token/timing keys (skills/implement/SKILL.md pattern); launch-review.sh exports LARCH_TOKEN_SESSION_ID from IMPLEMENT_TMPDIR but not session-env probe tunables (168-176). Persisting LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=30 in session-env.sh leaves /implement and most /review launches with the gate OFF despite Decision 2
- **Proposed resolution**: Minimal chokepoint: in launch-review.sh (and any other direct run-external-agent parent used in production), read LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT from IMPLEMENT_TMPDIR/session-env.sh via read-session-env-key.sh with default 30 and export before spawn; keep write-session-env.sh persistence as the durable default source

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-env-wiring-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/write-session-env.md:3-4
- **Concern**: Plan treats write-session-env.sh as turning the gate on in production, but session-env.sh is explicitly not sourced; only parsed keys that callers re-export reach child processes. Scenario: After Step 0 writes LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=30 into $IMPLEMENT_TMPDIR/session-env.sh, later Bash blocks and launchers (step2-implement.sh, run-step5-review.sh → review-and-fix → launch-review.sh → run-external-agent.sh) still see an empty process env, so external_launch_health_gate keeps the gate OFF despite the plan’s on-by-default claim
- **Proposed resolution**: Resolve the timeout at the run-external-agent chokepoint: if LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT is unset, read it from $IMPLEMENT_TMPDIR/session-env.sh and/or $SESSION_ENV_PATH via read-session-env-key.sh (default 30 when the key is present), matching the writer default without adding SKILL.md export churn

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-env-wiring-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/SKILL.md:27
- **Concern**: skills/research/SKILL.md:125. Scenario: Standalone /review and /research Step 0 call session-setup.sh without --write-session-env, so the proposed write-session-env.sh change never runs on those entry points
- **Proposed resolution**: Standalone production /review and /research external launches bypass both writers; gate stays OFF even after the plan lands Only if standalone runs must be gated: add --write-session-env "$REVIEW_TMPDIR/session-env.sh" (and the research analogue) to session-setup, plus the chokepoint read above; otherwise document that only /design (sourceable env) and /implement-nested paths are in scope

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-env-wiring-completeness
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/run-step5-review.sh:166-170
- **Concern**: Existing rehydration exports token/timing keys from session-env but not LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT; plan adds no parallel export or read sites. Scenario: Even with the key in session-env.sh, run-step5-review.sh and implement SKILL.md rehydration blocks (e.g. skills/implement/SKILL.md:121) never export the new key, reinforcing the silent-OFF gap for Step 5 and ship-pr CI launches under the same tmpdir
- **Proposed resolution**: Prefer the single chokepoint read in run-external-agent.sh over sprinkling export lines across ~40 SKILL sites; if chokepoint read is rejected, mirror run-step5-review.sh:170 and the LARCH_TOKEN_SESSION_ID pattern in skills/implement/SKILL.md

### OOS_1:
- **Description**: Plan mirrors the default into write-session-env for /research, but /research Step 0 runs session-setup without --write-session-env and calls run-external-agent.sh directly from phase markdown. Scenario: Research validation/research lanes never inherit the production default; only /design (source-env export) and fully wired /implement paths benefit
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/research/SKILL.md:125 / skills/research/references/validation-phase.md:96
- **Phase**: design
