# implement-bootstrap-invoke.sh

Thin `/implement` Step 0 wrapper around `scripts/implement-bootstrap.sh`. Collapses initial (`--up-to-phase coder`) and dirty-tree resume (`--up-to-phase plan --resume-plan-tail`) invoke paths into one script with a compact routing envelope for the orchestrator.

## argv

| Flag | Required | Values | Notes |
|------|----------|--------|-------|
| `--mode` | yes | `initial` \| `resume` | Any other value exits with usage. |

## Env inputs (caller must export)

| Variable | `initial` | `resume` |
|----------|-----------|----------|
| `CLAUDE_PLUGIN_ROOT` | required | required |
| `CALLER_ENV_PATH` / `SESSION_ENV_PATH` | optional | optional |
| `TARGET_ISSUE_NUMBER` / `ISSUE_NUMBER` | optional | optional |
| `forked_target`, `UPSTREAM_REPO` | optional | optional |
| `RUN_ID`, `PREFLIGHT_TMPDIR` | optional | optional |
| `emergency_requested` | `true`/`false` only when passed as `--emergency-requested` | same |
| `coder` | optional (`--coder` forwarded only when non-empty) | ignored |
| `IMPLEMENT_TMPDIR` | — | **required** (pass-through to bootstrap child for `resume_existing_tmpdir`) |

On `--mode resume`, the wrapper re-exports caller `IMPLEMENT_TMPDIR` unchanged before invoking bootstrap.

## Bootstrap argv per mode

- **`initial`**: `implement-bootstrap.sh --up-to-phase coder` plus common args; `--coder "$coder"` only when `coder` is non-empty.
- **`resume`**: `implement-bootstrap.sh --up-to-phase plan --resume-plan-tail` plus common args; no `--coder`.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success — routing envelope on stdout and `$IMPLEMENT_TMPDIR/bootstrap-routing.env`. |
| `2` | Bootstrap exit 2 — per-`STEP_FAILED` operator message on **stderr**, **empty stdout**. Callers propagate with `exit 2` only (do not print `$_inv_out`). |
| other | Bootstrap failure or usage; non-2 bootstrap exit codes are propagated unchanged. |

## Exit-2 single-owner invariant

The wrapper is the **sole owner** of exit-2 message formatting (including `copy-plan` / `gh-issue-view` `redact-secrets.sh | redact-tmpdir-paths.sh` pipes). `skills/implement/SKILL.md` call sites use `set +e` / `set -e` around `_inv_out=$(…)` and `exit 2` on `_inv_rc -eq 2` without re-printing.

## Routing envelope (stdout + `bootstrap-routing.env`)

Keys with consumers before the first `read-session-env-key.sh` / session-env rehydration:

`IMPLEMENT_TMPDIR`, `IMPLEMENT_BAIL_REASON`, `STALL_TRACKING`, `PLAN_FILE`, `coder`, `coder_fallback`, `REPO_UNAVAILABLE`, `DEFERRED`, `ISSUE_NUMBER`, `REPO`, `CODEX_PRESENT`, `CURSOR_PRESENT`, `CODEX_BINARY_FOUND`, `CURSOR_BINARY_FOUND`, `codex_available`, `cursor_available`, `RUN_ID`, `BRANCH_NAME`, `BRANCH_ACTION`.

Dual transport: stdout envelope (for command substitution) and `$IMPLEMENT_TMPDIR/bootstrap-routing.env` (file-first re-parse via `scripts/parse-bootstrap-routing-envelope.sh`). On success the wrapper writes through a same-directory temporary file when `bootstrap-routing.env` is absent or a regular file. When the path is a symlink or other non-regular file, the wrapper emits the filtered envelope on **stdout**, warns on **stderr**, and exits `0` without overwriting the path.

The file envelope is authoritative when present and regular; stdout is a fallback only for keys still empty after file parsing. Before each parse, the orchestrator clears stale volatile routing keys so a skipped or unreadable file cannot retain old bail/branch state. Dirty-tree resume preserves the caller's existing `coder` / `coder_fallback` selection, and the wrapper omits empty `coder` / `coder_fallback` values in resume mode so a plan-tail envelope cannot erase that preserved implementer state.

## NEVER #14

This script must **never** write or append `$IMPLEMENT_TMPDIR/session-env.sh`. Only `implement-bootstrap.sh` / sanctioned writers own session-env.

## Primary caller

`skills/implement/SKILL.md` Step 0 (initial + dirty-tree `--mode resume`).

## Offline harness

`skills/implement/scripts/test-implement-bootstrap-invoke.sh` — `make test-implement-bootstrap-invoke`.

## Edit-in-sync

- `skills/implement/SKILL.md` Step 0 + preamble Protocol Execution Directive
- `scripts/parse-bootstrap-routing-envelope.sh` + `scripts/parse-bootstrap-routing-envelope.md`
- `scripts/test-implement-structure.sh` + `scripts/test-implement-structure.md`
- `scripts/test-implement-step2-routing.sh`
- `skills/shared/subskill-invocation.md`
- `scripts/implement-bootstrap.md`
- `Makefile` (`test-implement-bootstrap-invoke` target + harness shard)
