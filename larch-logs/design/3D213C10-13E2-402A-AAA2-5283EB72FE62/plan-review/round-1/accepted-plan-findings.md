### FINDING_1: Session-env persistence does not activate the health gate on production launch paths
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-dyn-script-contract-verifier, Cursor-dyn-env-wiring-completeness
- **Severity**: important
- **Concern**: Persisting `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT` in `session-env.sh` (via `write-session-env.sh`) does not turn on `external_launch_health_gate` on the main `/implement` and nested `/review` paths. `session-env.sh` is not sourceable and is only consumed when callers parse keys with `read-session-env-key.sh`; `/implement` and launchers rehydrate only a small allowlist (e.g. token/timing keys) before `launch-review.sh` → `run-external-agent.sh`, which gates on the process environment. With the var unset in the shell env, Decision 2 keeps the gate OFF despite the writer’s default, so mid-run hangs remain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Enable production activation at the chokepoint: in `run-external-agent.sh` or `external_launch_health_gate`, when the var is unset/invalid, read `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT` from `$IMPLEMENT_TMPDIR/session-env.sh` (and/or `$SESSION_ENV_PATH` when set) via `read-session-env-key.sh`, or add the same read+export pattern used for `LARCH_TIMING_LEDGER` to implement Step 5 launch blocks. `/design` is already covered via sourceable `write-design-current-env.sh` exports.
  - From Cursor-Edge: In external_launch_health_gate (or run-external-agent.sh immediately before it), when the env var is unset/0/non-numeric, read LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT from $IMPLEMENT_TMPDIR/session-env.sh via read-session-env-key (IMPLEMENT_TMPDIR is exported on Step 2/5 blocks). Document the fallback in lib-external-launcher-common.md and write-session-env.md.
  - From Cursor-Innovation: Append the key in write-session-env CONTENT (not build_export), then read+export it in implement-bootstrap after write (mirror LARCH_TIMING_LEDGER) and add the same read+export to implement SKILL rehydration blocks that launch external reviewers
  - From Cursor-dyn-script-contract-verifier: Minimal chokepoint: in launch-review.sh (and any other direct run-external-agent parent used in production), read LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT from IMPLEMENT_TMPDIR/session-env.sh via read-session-env-key.sh with default 30 and export before spawn; keep write-session-env.sh persistence as the durable default source
  - From Cursor-dyn-env-wiring-completeness: Resolve the timeout at the run-external-agent chokepoint: if LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT is unset, read it from $IMPLEMENT_TMPDIR/session-env.sh and/or $SESSION_ENV_PATH via read-session-env-key.sh (default 30 when the key is present), matching the writer default without adding SKILL.md export churn
  - From Cursor-dyn-env-wiring-completeness: Prefer the single chokepoint read in run-external-agent.sh over sprinkling export lines across ~40 SKILL sites; if chokepoint read is rejected, mirror run-step5-review.sh:170 and the LARCH_TOKEN_SESSION_ID pattern in skills/implement/SKILL.md


### FINDING_2: Wrapper timeout exit must fail unhealthy before missing-line fail-open
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The planned `external_launch_health_gate` orders unhealthy on outer timeout vs fail-open on missing parseable `*_PRESENT`, but does not require checking wrapper exit 124 (or 143) before the fail-open branch. A `timeout`/`gtimeout` kill can yield exit 124 with no `CODEX_PRESENT`/`CURSOR_PRESENT` line; treating that as infra fail-open would proceed with a 20–30m launch instead of fast-fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Specify in the helper contract: if wrapper exit is 124 (or 143), return unhealthy before the missing-line fail-open path


### FINDING_4: Standalone `/review` and `/research` never run `write-session-env`
- **Reviewer(s)**: Cursor-dyn-env-wiring-completeness
- **Severity**: important
- **Concern**: Standalone `/review` and `/research` Step 0 call `session-setup.sh` without `--write-session-env`, so the proposed `write-session-env.sh` change never runs on those entry points. Even with a chokepoint read, standalone production external launches can bypass both session-env writers unless scope is narrowed or entry points are extended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-env-wiring-completeness: Standalone production /review and /research external launches bypass both writers; gate stays OFF even after the plan lands Only if standalone runs must be gated: add --write-session-env "$REVIEW_TMPDIR/session-env.sh" (and the research analogue) to session-setup, plus the chokepoint read above; otherwise document that only /design (sourceable env) and /implement-nested paths are in scope

