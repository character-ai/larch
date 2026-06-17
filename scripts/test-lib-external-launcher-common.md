# test-lib-external-launcher-common.sh

Offline unit-test harness for `scripts/lib-external-launcher-common.sh`.

Primary contract: `scripts/lib-external-launcher-common.md`.

Covers `external_is_transient_infra_failure` — all decision branches exercised by the current helper: missing output file, unknown tool, exit-code allowlist (codex 5/7, cursor 4/8), non-empty output file, and the happy path returning 0.

Covers `external_launch_health_gate` with a temp script root and stubbed
`agent check-reviewers`: healthy, unhealthy, timeout exits `124` / `143` before
fail-open, gate off, explicit `0` opt-out, `SESSION_ENV_PATH` and
`$IMPLEMENT_TMPDIR/session-env.sh` timeout resolution, non-tool no-op, and
malformed non-timeout fail-open.

Covers the shared Darwin startup lock: Codex and Cursor use the same Bash lock
path, cross-tool acquisition blocks within the Bash lane, startup-lock env var
names drive tuning, and Bash acquire uses the two-argument form
`<out_var> <tool>`. Unset and empty `USER` both resolve to `larch` via
`${USER:-larch}`. Lock tests use a path-safe `USER` token such as
`larch-test-$(basename "$TMPDIR_ROOT")`. Cross-lane Python-holds /
Bash-blocked coverage lives in `python/test_agents.py`.

Run via `bash scripts/test-lib-external-launcher-common.sh` or `make test`.
