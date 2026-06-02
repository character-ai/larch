# lib-cursor-auth.sh

Sourced library exposing Cursor auth helpers used by every live `cursor agent` call site:

- `cursor_auth_export_env` — normalizes `CURSOR_API_KEY` in the environment so the Cursor child authenticates via the env var with **no `--api-key` argv element** (issue #3375). Whitespace-trims the value and re-exports it; `unset`s `CURSOR_API_KEY` when the trimmed value is empty/whitespace-only (preserves the `cursor login` keychain fallback) or contains an embedded newline/CR (fail-closed against paste corruption). Always returns 0 so it composes in `&&` chains.
- `cursor_auth_preflight` — Darwin-gated read-only sanity check. Returns 0 when the launcher should proceed (env or keychain looks viable), returns 2 when both auth sources are demonstrably absent on Darwin. Writes an actionable multi-line message to stderr on the failure path.
- `cursor_preread_service_token` — Darwin-gated best-effort keychain pre-read that exports the `cursor-user` / `cursor-access-token` service value into `CURSOR_API_KEY` when the env var is otherwise empty, so the Cursor child authenticates from the environment instead of performing its own keychain read.

## Why env-based auth (issue #3375)

Passing `--api-key <key>` on the `cursor agent` argv leaked the secret into `scripts/run-external-agent.sh`'s `.meta` `CMD_JSON` (and in one case into a committed run-log), `ps` listings, and any captured command line. Cursor authenticates equally from the `CURSOR_API_KEY` environment variable, mirroring how Claude (ambient session) and Codex (`CODEX_HOME` + OAuth) authenticate — no secret on argv. The launchers now export the normalized key into the environment the Cursor child inherits and pass **no** `--api-key`.

## Callers (parity contract)

- `scripts/launch-review.sh --tool cursor` — review reviewer panel launcher (via `cursor_launcher_setup_auth_argv`).
- `scripts/launch-cursor-implement.sh` — Cursor implementer launcher (Step 2 of `/implement`; via `cursor_launcher_setup_auth_argv`).
- `scripts/launch-cursor-ci.sh` — Cursor CI-fix launcher (via `cursor_launcher_setup_auth_argv`).
- `scripts/check-reviewers.sh` — reviewer presence check (sources the lib; calls `cursor_preread_service_token` + `cursor_auth_export_env` — `cursor_auth_preflight` is invoked separately to gate the probe loop).
- `scripts/run-negotiation-round.sh` — negotiation runner (calls `cursor_auth_export_env` after `cursor_auth_preflight`).
- `scripts/cursor-auth-flags.sh` — Darwin preflight **gate** for runtime skill markdown blocks (`skills/shared/voting-protocol.md`, `skills/shared/dialectic-protocol.md`, `skills/research/references/validation-phase.md`) where direct `source` of a library is awkward. It runs `cursor_auth_preflight` and emits **no** argv flags; the markdown blocks rely on the orchestrator's inherited `CURSOR_API_KEY` for the Cursor child.

## Invariants

- Never echoes the key on any path (including all error paths in `cursor_auth_preflight`).
- `cursor_auth_export_env` mutates only `CURSOR_API_KEY` in the environment (export/unset); it builds no argv. Callers pass no auth argv element.
- `cursor_auth_preflight` returns rather than `exit`s — keeps callers in control of exit semantics so each launcher can synthesize its tool-specific failure channel (sentinel files for `launch-review.sh --tool cursor`, KV envelope for `launch-cursor-implement.sh`, plain `exit 3` for `run-negotiation-round.sh`).
- Darwin-only service-specific keychain probe (`security find-generic-password -a cursor-user -s cursor-access-token`); on non-Darwin, preflight is a no-op.
- Darwin-only keychain pre-read uses `security find-generic-password -a cursor-user -s cursor-access-token -w`; failures and empty reads are silent no-ops so callers retain Cursor's default auth fallback.
- Strictly read-only: never invokes `security delete-*`, never spawns a Cursor subprocess, never performs network I/O.
- Bash 3.2-safe: forbids `declare -n`, `local -n`, `mapfile`, `readarray`, and `eval` for secret-bearing assembly. Whitespace trim uses Bash-3.2-safe parameter expansion only.

## Test-mode gating (FINDING_6)

Every test-only branch in `lib-cursor-auth.sh` (`LIB_CURSOR_AUTH_TEST_UNAME`, `LIB_CURSOR_AUTH_TEST_SECURITY_RC`, `LIB_CURSOR_AUTH_TEST_PREREAD_TOKEN`) is reachable ONLY when `LARCH_LIB_CURSOR_AUTH_TEST_MODE=1`. Production code paths ignore all `LIB_CURSOR_AUTH_TEST_*` vars unless that single sentinel is also set, so an operator setting one of the test vars alone cannot disable Darwin preflight or inject a fake pre-read token on a real machine.

## Verified Cursor CLI behavior

`cursor agent --help` documents `--api-key <key>` with the note `can also use CURSOR_API_KEY env var`. The env path was verified locally per `.claude/rules/verify-external-tool-invocations.md` (issue #3375): a bogus key supplied **only** via the environment (no `--api-key` argv) produced `The provided API key is invalid. The API key was loaded from the CURSOR_API_KEY environment variable`, confirming Cursor consults the env var. Locked here for future maintainers — a future Cursor release that drops env-var support will be detected by `scripts/test-launch-review.sh` and `scripts/test-cursor-implementer.sh` regression coverage (the harnesses assert no `--api-key` token appears in recorded argv and that the Cursor child inherits `CURSOR_API_KEY` in its environment when the key is set).

## Test harness

`scripts/test-lib-cursor-auth.sh` (sibling contract `scripts/test-lib-cursor-auth.md`). Verifies:
- `cursor_auth_export_env` exports the trimmed key for single-line / leading-or-trailing-whitespace values, and `unset`s `CURSOR_API_KEY` for empty / whitespace-only / embedded-newline / embedded-CR values.
- `cursor_auth_preflight` returns 0 for non-empty key, 0 on non-Darwin, 0 on Darwin when keychain entry exists, 2 on Darwin with empty key + missing keychain entry.
- `cursor_preread_service_token` preserves an existing key, no-ops on non-Darwin, exports a mocked Darwin token, and no-ops on empty token reads.
- `cursor_launcher_setup_auth_argv` wires the pre-read before `cursor_auth_export_env`, so a readable Darwin service becomes the exported `CURSOR_API_KEY`.
- `cursor-auth-flags.sh` emits no argv flags and exits 0 (proceed) / 2 (Darwin preflight failure).
- All `LIB_CURSOR_AUTH_TEST_*` overrides are silently ignored unless `LARCH_LIB_CURSOR_AUTH_TEST_MODE=1`.

Wired into `Makefile` `test-harnesses-2` shard (`test-launch-review` is on shard 9). Excluded from `agent-lint.toml` per the standard pattern for test scripts and their `.md` siblings.

## Edit-in-sync rules

When editing this library:
- Mirror the parity contract: every caller above must continue to deliver auth via `cursor_auth_export_env` (env var) and pass **no** `--api-key` argv element. The Cursor child inherits `CURSOR_API_KEY` from the launcher process.
- Update the verified Cursor CLI version notes if a new release changes env-var auth behavior.
- Re-run `bash scripts/test-lib-cursor-auth.sh` and `bash scripts/test-launch-review.sh`.
