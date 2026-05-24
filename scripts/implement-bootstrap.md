# implement-bootstrap.sh

Mechanical `/implement` Step 0 bootstrap: branch facts, entry gate, session setup, session-env write, token/timing marks, rehydrate keys, reviewer warnings, and the umbrella KV tail. **Primary caller:** `skills/implement/SKILL.md` Step 0 (foreground). **Offline harness:** `skills/implement/scripts/test-implement-bootstrap.sh` (+ sibling `.md`).

## argv

| Flag | Required | Values | Notes |
|------|----------|--------|-------|
| `--up-to-phase` | yes | `infra` \| `tracking` \| `plan` \| `coder` \| `all` | Phase 1 ships `--up-to-phase infra` from SKILL.md. Later phases extend dispatch without argv churn. |
| `--caller-env` | no | path | Forwarded to `session-setup.sh --caller-env` when set. Also used to read `LARCH_DYNAMIC_ARCHETYPES_MAX` for `write-session-env.sh --dynamic-archetypes` (same contract as legacy prompt-side `SESSION_ENV_PATH` / `CALLER_ENV_PATH`). |
| `--issue-number` | no | string | Echoed in final tail as `ISSUE_NUMBER=` for forward-compatible orchestrator wiring (empty when omitted). |

## Inputs (Phase 1)

- Git repository state (via `create-branch.sh --check`, `session-setup.sh` preflight).
- Optional caller-env file (`--caller-env`) for forked / nested flows.
- No direct reads of `$IMPLEMENT_TMPDIR/session-env.sh` before `session-setup.sh` succeeds (empty tmpdir guard).

Later phases (not implemented in this PR) will read `$IMPLEMENT_TMPDIR/session-env.sh` and design plan artifacts under `$DESIGN_TMPDIR/`.

## Outputs

### stdout (KV)

Machine-readable `KEY=value` lines. `LARCH_QUIET_DISABLE=1` is forced for this script so `emit_kv` writes to stdout (orchestrator command substitution). **Warnings** for repo / Codex / Cursor health use `larch_err` (stderr) so stdout stays KV-shaped.

**Per-phase:** `phase_infra` emits a consolidated infra block via `emit_infra_kv_block` inside `emit_final_tail`, including `CURRENT_BRANCH`, `IS_MAIN`, `IS_USER_BRANCH`, `USER_PREFIX`, `ENTRY_GATE`, `SKIP_BRANCH_CHECK`, `IMPLEMENT_TMPDIR`, `SESSION_ID`, reviewer keys, `REPO`, `REPO_UNAVAILABLE`, `CLAUDE_SOURCE_OK`, `LARCH_TOKEN_SESSION_ID`, `LARCH_CLAUDE_SOURCE_FILE`, `LARCH_TIMING_LEDGER`, `codex_available`, `cursor_available`, then umbrella keys: `ISSUE_NUMBER`, `RUN_ID`, `BRANCH_NAME`, `PLAN_FILE`, `coder`, `coder_fallback`, `IMPLEMENT_BAIL_REASON`.

Phase 2–4 keys are present (empty values) in Phase 1 for parser stability.

### stderr

- Repo-unavailable advisory (`REPO_UNAVAILABLE=true`).
- Codex / Cursor two-tier availability advisories (binary missing vs runtime unhealthy).
- Invalid `LARCH_DYNAMIC_ARCHETYPES_MAX` caller warning.

All of the above use `larch_err` (never raw `printf`/`echo` to stderr after `larch_quiet_init`) per `lint-no-raw-stderr-after-quiet-init`.

### Breadcrumbs (`LARCH_QUIET_BREADCRUMBS=1`)

When `LARCH_QUIET_BREADCRUMBS` is truthy, emits exactly one line via `emit_breadcrumb`:

`→ step0: infra ready (tmpdir=$IMPLEMENT_TMPDIR session=$SESSION_ID)`

Future phases will add `→ step0: tracking adopted …`, `→ step0: branch + plan logged`, `→ step0: larch:plan posted`, `→ step0: coder=…` (documented here; not emitted in Phase 1).

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success through `--up-to-phase` boundary. |
| 2 | Infrastructure failure: `STEP_FAILED=` plus diagnostic (`GATE_ERROR=` or `PREFLIGHT_ERROR=` on stdout where applicable). |
| (other) | argv validation failures (`die_usage`). |

## Bail reasons (`IMPLEMENT_BAIL_REASON`)

| Value | When |
|-------|------|
| *(empty)* | Normal Phase 1 success or infra-only run. |
| `not-yet-implemented-phase-2` | Stub `phase_tracking` (when `--up-to-phase` reaches `tracking` or beyond). |
| `not-yet-implemented-phase-3` | Stub `phase_plan_materialize`. |
| `not-yet-implemented-phase-4` | Stub `phase_coder_select`. |

Later issues replace stubs with real bail tokens (`adopted-issue-closed`, etc.).

## Behavior mapping (Step 0 SKILL.md)

| Legacy call | Absorbed here |
|-------------|----------------|
| `create-branch.sh --check` | `phase_infra` |
| `session-entry-gate.sh` | `phase_infra` |
| `session-setup.sh` | `phase_infra` |
| Inline `write-session-id` + `token-claude-source` + `write-session-env` + ledgers | `phase_infra` |
| Three-key `read-session-env-key.sh` rehydrate | `phase_infra` (re-read for parity) |

## NEVER #14

This script **must not** append or overwrite `$IMPLEMENT_TMPDIR/session-env.sh` via raw shell redirection (`>>`, `cat > … <<`). Only `write-session-env.sh` writes the file. The offline harness greps the live source for forbidden patterns.

## Edit-in-sync

- `skills/implement/SKILL.md` Step 0 call site and KV parsing.
- `scripts/lint-foreground-markers.sh` DENYLIST (Family B foreground).
- `skills/implement/scripts/test-implement-bootstrap.sh` (+ `.md`).
- This file.
