## Plan

Add a launch-time health gate so production external-agent launches fast-fail to Claude when an
installed Codex/Cursor binary is unhealthy, instead of waiting the full 20-30 min `--timeout`.
Reuse the existing `check-reviewers.sh` probe + per-tool stamp cache; do not build a parallel probe.

### Problem

`check-reviewers.sh` already runs a bounded (`LARCH_PROBE_TIMEOUT_SECONDS`=30s), cached
(`LARCH_PROBE_TTL_SECONDS`=60s, per-USER stamp) real probe at session start. The residual gap: a
tool healthy at session start can degrade mid-run (quota, network, token expiry); dispatchers still
launch it via `run-external-agent.sh`, which waits the full `--timeout` before the waterfall reaches
Claude. The gate closes that gap at the shared chokepoint.

### Files to modify (all UPDATED — no new files)

- `scripts/lib-external-launcher-common.sh` — add `external_launch_health_gate <tool>` (Bash-3.2-safe,
  sourced-only). Timeout resolution: (1) process env `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT` when a
  positive integer; (2) else read from `$SESSION_ENV_PATH` then `$IMPLEMENT_TMPDIR/session-env.sh` via
  `read-session-env-key.sh`; (3) else gate OFF (return 0). Once a positive `N` resolves: no-op for
  non-codex/cursor; else run `check-reviewers.sh --skip-<other>-probe` with `LARCH_EXTERNAL_AUTH_RETRIES=1`,
  wrapped in `timeout`/`gtimeout N` when available (else rely on the probe's internal bound). Decision
  order: wrapper exit `124`/`143` → unhealthy (skip) BEFORE any fail-open; `*_PRESENT=false` → unhealthy
  (skip); `*_PRESENT=true` → proceed; no parseable line and rc not 124/143 → fail OPEN (proceed).
- `scripts/lib-external-launcher-common.md` — document the helper, the resolution order, and the
  124/143-before-fail-open rule.
- `scripts/run-external-agent.sh` — source the lib; before launch, for `--tool codex|cursor` call the
  gate. On unhealthy: skip the launch, append a `health-probe fast-fail` line to `${OUTPUT_FILE}.diag`,
  leave output empty, exit codex→`7` / cursor→`8` (the existing `health`/`health-probe` classification;
  no classifier change).
- `scripts/run-external-agent.md` — document the gate, env var, chokepoint resolution, and exit semantics.
- `scripts/write-design-current-env.sh` (+ `.md`) — `build_export LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT`
  default `30` (source-env.sh is sourced by /design blocks → reaches launchers directly).
- `scripts/write-session-env.sh` (+ `.md`) — persist the key (default `30`) via the existing
  `CONTENT`/`KEY=VALUE` append pattern (NOT `build_export`, which is design-writer-only); the chokepoint
  read consumes it on /implement and nested /review.
- `skills/design/scripts/plan-review-loop.md` — document transitive coverage (launches funnel through
  `run-external-agent.sh`); no `.sh` change needed.
- `docs/configuration-and-permissions.md` — document `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT` beside the
  `LARCH_PROBE_*` entries, plus the activation scope (auto-on for /design + /implement+nested /review;
  standalone /review and /research are an L1 gap, env-var opt-in; /research tracked by OOS #3369).
- `python/config.py` — add `ENV_LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT` + `EXTERNAL_HEALTH_CHECK_TIMEOUT_DEFAULT_SEC=30`
  parity constants. `checks.py`/`agents.py` inherit the gate transitively via `os.environ` (no `env=`
  override on their `run-external-agent.sh` / `launch-*-ci.sh` calls) — no functional change.
- `python/test_checks_bash_parity.py` — assert the Python default + env-var name match the bash sources.
- `scripts/test-lib-external-launcher-common.sh` — unit-test the gate (healthy / unhealthy /
  124-143-unhealthy-before-fail-open / off / session-env-read / non-tool / fail-open) with a stubbed
  `check-reviewers.sh`.
- `scripts/test-run-external-agent.sh` — integration: gate-enabled unhealthy → exit 7/8, command not run;
  gate-disabled (env unset + no session-env) → command runs; non-tool → command runs.

### Approach

Reuse `check-reviewers.sh` and its 60s stamp cache. The first launch against a degraded tool pays one
bounded probe; the fresh `false` stamp makes subsequent launches and `launch-review.sh` retries fast-fail
instantly. Activation is on-by-default in production (sourceable export for /design; persisted key +
chokepoint read for /implement) and off in test/CI (no env var, no session-env file → zero harness churn).
Waterfall: codex-7/cursor-8 + empty output is `health` class — CI family falls through (not `other`, so no
short-circuit); review family retries cheaply then falls through. Both reach Claude.

### Edge cases

`timeout`/`gtimeout` absent → rely on the probe's internal bound. Outer-timeout kill (124/143, no
`*_PRESENT` line) → unhealthy, not fail-open. Fresh stamp (true/false) → no new probe. Non-codex/cursor →
no-op. Parallel launches → safe (atomic stamp + Darwin serial lock). Broken `check-reviewers.sh` (rc not
124/143, no line) → fail open.

### Failure modes

(1) False-positive on a slow-but-healthy tool → needless Claude fallback; mitigated by the 30s default,
60s stamp expiry, and the unset/`0` opt-out. (2) Accidental test/CI activation → mitigated by off-unless-resolved
activation + stubbed `check-reviewers.sh` in gate tests. (3) Probe cost creep → bounded to ~1 probe/60s by
the stamp cache + `LARCH_EXTERNAL_AUTH_RETRIES=1`.

### Testing strategy

`test-lib-external-launcher-common.sh` (gate branches), `test-run-external-agent.sh` (integration),
`python/test_checks_bash_parity.py` (parity). Run `bash scripts/relevant-checks.sh` (or `make lint`), the
touched `test-*.sh` harnesses, and `make py-lint` / `make py-test`.

## Acceptance

- `external_launch_health_gate <tool>` exists in `scripts/lib-external-launcher-common.sh`, resolves the
  timeout from process env → `$SESSION_ENV_PATH` → `$IMPLEMENT_TMPDIR/session-env.sh` (via
  `read-session-env-key.sh`), and is OFF (returns 0/proceed) when no positive timeout resolves.
- The gate checks wrapper exit `124`/`143` as unhealthy BEFORE the missing-`*_PRESENT`-line fail-open; it
  reuses `check-reviewers.sh` (no parallel probe) and is no-op for non-codex/cursor tools.
- `scripts/run-external-agent.sh` calls the gate for `--tool codex|cursor` before launch; on unhealthy it
  skips the launch, leaves output empty, writes a `health-probe fast-fail` diag line, and exits `7` (codex)
  or `8` (cursor) — producing a `health`/`health-probe` waterfall verdict (no classifier change).
- `scripts/write-design-current-env.sh` exports the var (default `30`) via `build_export`;
  `scripts/write-session-env.sh` persists it (default `30`) via the `CONTENT+=` pattern (not `build_export`).
- `python/config.py` defines `ENV_LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT` and
  `EXTERNAL_HEALTH_CHECK_TIMEOUT_DEFAULT_SEC=30`; `python/test_checks_bash_parity.py` asserts they match the
  bash sources. `checks.py`/`agents.py` need no functional change (transitive inheritance).
- `docs/configuration-and-permissions.md` documents the env var and the activation scope (incl. the
  standalone /review + /research L1 gap, with /research tracked by OOS #3369).
- Every `.sh` change carries its sibling `.md` update; Codex/Cursor stay symmetric (launcher-parity rule).
- Existing tests are unaffected with the gate off (env unset + no session-env file); the new gate tests
  pass; `make lint`, `make py-lint`, and `make py-test` are green. No SECURITY.md change required.

diff_lines: 360
