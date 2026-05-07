# lib-cursor-auth.sh

Sourced library exposing two pure functions used by every live `cursor agent` call site:

- `cursor_auth_argv` — populates the global `CURSOR_AUTH_ARGS` array with `(--api-key "$CURSOR_API_KEY")` when the env var is non-empty after whitespace trim, else leaves the array empty (preserves today's `cursor login` keychain fallback).
- `cursor_auth_preflight` — Darwin-gated read-only sanity check. Returns 0 when the launcher should proceed (env or keychain looks viable), returns 2 when both auth sources are demonstrably absent on Darwin. Writes an actionable multi-line message to stderr on the failure path.

## Callers (parity contract)

- `scripts/launch-cursor-review.sh` — review reviewer panel launcher.
- `scripts/launch-cursor-implement.sh` — Cursor implementer launcher (Step 2 of `/implement`).
- `scripts/check-reviewers.sh` — reviewer health probe (sources the lib; calls `cursor_auth_argv` only — preflight is intentionally NOT invoked from the probe, whose job is to report binary health).
- `scripts/run-negotiation-round.sh` — negotiation runner.
- `scripts/cursor-auth-flags.sh` — small helper that prints the conditional `--api-key` argv elements one per line, used by runtime skill markdown blocks (`skills/shared/voting-protocol.md`, `skills/shared/dialectic-protocol.md`, `skills/research/references/validation-phase.md`) where direct `source` of a library is awkward.

## Invariants

- Never echoes the key on any path (including all error paths in `cursor_auth_preflight`).
- Never mutates argv beyond the `CURSOR_AUTH_ARGS` global array; callers control the rest.
- Returns rather than `exit`s — keeps callers in control of exit semantics so each launcher can synthesize its tool-specific failure channel (sentinel files for `launch-cursor-review.sh`, KV envelope for `launch-cursor-implement.sh`, plain `exit 3` for `run-negotiation-round.sh`).
- Darwin-only keychain probe (`security find-generic-password -a cursor-user`); on non-Darwin, preflight is a no-op.
- Strictly read-only: never invokes `security delete-*`, never spawns a Cursor subprocess, never performs network I/O.
- Bash 3.2-safe: forbids `declare -n`, `local -n`, `mapfile`, `readarray`, and `eval` for secret-bearing assembly. Whitespace trim uses Bash-3.2-safe parameter expansion only.

## Test-mode gating (FINDING_6)

Every test-only branch in `lib-cursor-auth.sh` (`LIB_CURSOR_AUTH_TEST_UNAME`, `LIB_CURSOR_AUTH_TEST_SECURITY_RC`) is reachable ONLY when `LARCH_LIB_CURSOR_AUTH_TEST_MODE=1`. Production code paths ignore all `LIB_CURSOR_AUTH_TEST_*` vars unless that single sentinel is also set, so an operator setting one of the test vars alone cannot disable Darwin preflight on a real machine.

## Verified Cursor CLI behavior

`cursor agent --help` documents `--api-key <key>` with the note `can also use CURSOR_API_KEY env var`. Explicit `--api-key` takes precedence over keychain. Locked here for future maintainers — a future Cursor release that changes the flag name or precedence will be detected by `scripts/test-launch-cursor-review.sh` and `scripts/test-cursor-implementer.sh` regression coverage (the harness asserts `--api-key <value>` appears as adjacent tokens in recorded argv when `CURSOR_API_KEY` is set).

## Test harness

`scripts/test-lib-cursor-auth.sh` (sibling contract `scripts/test-lib-cursor-auth.md`). Verifies:
- `cursor_auth_argv` populates `CURSOR_AUTH_ARGS` correctly for empty / whitespace-only / single-line / leading-or-trailing-whitespace key values.
- `cursor_auth_preflight` returns 0 for non-empty key, 0 on non-Darwin, 0 on Darwin when keychain entry exists, 2 on Darwin with empty key + missing keychain entry.
- All `LIB_CURSOR_AUTH_TEST_*` overrides are silently ignored unless `LARCH_LIB_CURSOR_AUTH_TEST_MODE=1`.

Wired into `Makefile` `test-harnesses-2` shard alongside `test-launch-gemini-review`. Excluded from `agent-lint.toml` per the standard pattern for test scripts and their `.md` siblings.

## Edit-in-sync rules

When editing this library:
- Mirror the parity contract: every caller above must continue to assemble argv via `cursor_auth_argv` and the conditional `"${CURSOR_AUTH_ARGS[@]}"` expansion in the same argv position (between `$AGENT_MODEL_ARGS` and `--workspace`).
- Update the verified Cursor CLI version notes if a new release changes flag behavior.
- Re-run `bash scripts/test-lib-cursor-auth.sh` and `bash scripts/test-launch-cursor-review.sh`.
