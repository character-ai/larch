# implement-bootstrap.sh

Mechanical `/implement` Step 0 bootstrap: branch facts, entry gate, session setup, session-env write, token/timing marks, rehydrate keys, tracking issue adoption, reviewer warnings, and the umbrella KV tail. **Primary caller:** `skills/implement/SKILL.md` Step 0 (foreground). **Offline harness:** `skills/implement/scripts/test-implement-bootstrap.sh` (+ sibling `.md`).

## argv

| Flag | Required | Values | Notes |
|------|----------|--------|-------|
| `--up-to-phase` | yes | `infra` \| `tracking` \| `plan` \| `coder` \| `all` | `tracking` absorbs Step 0 tracking issue adoption. Later phases extend dispatch without argv churn. |
| `--caller-env` | no | path | Forwarded to `session-setup.sh --caller-env` when set. Also used to read `LARCH_DYNAMIC_ARCHETYPES_MAX` for `write-session-env.sh --dynamic-archetypes` (same contract as legacy prompt-side `SESSION_ENV_PATH` / `CALLER_ENV_PATH`). |
| `--skip-codex-probe` | no | flag | Forwarded to `session-setup.sh` / `check-reviewers.sh` (skip Codex runtime probe). |
| `--skip-cursor-probe` | no | flag | Forwarded to `session-setup.sh` / `check-reviewers.sh` (skip Cursor runtime probe). |
| `--issue-number` | no | numeric string | Target issue for tracking adoption. Empty means no fresh Branch 2 adoption. |
| `--forked-target` | no | `true` \| `false` | Default `false`. When `true`, tracking adoption is skipped and upstream context is fetched best-effort. |
| `--upstream-repo` | no | `OWNER/REPO` | Required by callers in fork mode when upstream issue context should be fetched. Validated as one owner/repo slash with GitHub-safe characters. |
| `--run-id` | no | `^[A-Za-z0-9._-]+$` | Preferred Branch 2 run id; takes precedence over `$IMPLEMENT_TMPDIR/session-id` and `LARCH_TOKEN_SESSION_ID`. |

## Inputs (Phase 1)

- Git repository state (via `create-branch.sh --check`, `session-setup.sh` preflight).
- Optional caller-env file (`--caller-env`) for forked / nested flows.
- No direct reads of `$IMPLEMENT_TMPDIR/session-env.sh` before `session-setup.sh` succeeds (empty tmpdir guard).

Later phases (not implemented in this PR) will read `$IMPLEMENT_TMPDIR/session-env.sh` and design plan artifacts under `$DESIGN_TMPDIR/`.

## Outputs

### stdout (KV)

Machine-readable `KEY=value` lines. `LARCH_QUIET_DISABLE=1` is forced for this script so `emit_kv` writes to stdout (orchestrator command substitution). **Warnings** for repo / Codex / Cursor health use `larch_err` (stderr) so stdout stays KV-shaped.

**Per-phase:** `phase_infra` emits a consolidated infra block via `emit_infra_kv_block` inside `emit_final_tail`, including `CURRENT_BRANCH`, `IS_MAIN`, `IS_USER_BRANCH`, `USER_PREFIX`, `ENTRY_GATE`, `SKIP_BRANCH_CHECK`, `IMPLEMENT_TMPDIR`, `SESSION_ID`, reviewer keys, `REPO`, `REPO_UNAVAILABLE`, `CLAUDE_SOURCE_OK`, `LARCH_TOKEN_SESSION_ID`, `LARCH_CLAUDE_SOURCE_FILE`, `LARCH_TIMING_LEDGER`, `codex_available`, `cursor_available`, then umbrella keys: `ISSUE_NUMBER`, `RUN_ID`, `BRANCH_SELECTED`, `DEFERRED`, `STALL_TRACKING`, `BRANCH_NAME`, `PLAN_FILE`, `coder`, `coder_fallback`, `IMPLEMENT_BAIL_REASON`.

Phase 3–4 keys are present (empty values) for parser stability.

`BRANCH_SELECTED` values:

| Value | Meaning |
|-------|---------|
| `branch-1-resume` | Usable `parent-issue.md` sentinel matched the requested issue and supplied a numeric `ISSUE_NUMBER` plus a valid `RUN_ID`. |
| `branch-2-adopt` | Fresh open issue adoption path. |
| `forked-target-skip` | Fork mode skipped local tracking adoption; upstream context fetch was best-effort. |
| `repo-unavailable-skip` | Repo discovery failed; tracking adoption was skipped. |
| *(empty)* | No tracking branch reached, or Branch 2 bailed before adoption. |

### stderr

- Repo-unavailable advisory (`REPO_UNAVAILABLE=true`).
- Codex / Cursor two-tier availability advisories (binary missing vs runtime unhealthy).
- Invalid `LARCH_DYNAMIC_ARCHETYPES_MAX` caller warning.

All of the above use `larch_err` (never raw `printf`/`echo` to stderr after `larch_quiet_init`) per `lint-no-raw-stderr-after-quiet-init`.

### Breadcrumbs (`LARCH_QUIET_BREADCRUMBS=1`)

When `LARCH_QUIET_BREADCRUMBS` is truthy, emits exactly one line via `emit_breadcrumb`:

`→ step0: infra ready (tmpdir=$IMPLEMENT_TMPDIR session=$SESSION_ID)`

Tracking phase may also emit:

- `→ step0: tracking adopted #<N> (run=<RUN_ID> branch=<branch-1-resume|branch-2-adopt>)`
- `⏩ step0: tracking — skip (repo-unavailable|forked-target)`

Set `LARCH_QUIET_BREADCRUMB_FD` to a numeric descriptor when you need breadcrumbs on a dedicated stream. When breadcrumbs are enabled but `LARCH_QUIET_BREADCRUMB_FD` is unset or non-numeric, the line is emitted via `larch_err` (stderr / quiet FD4) so stdout remains KV-only under `LARCH_QUIET_DISABLE=1`.

Future phases will add the later Step 0 breadcrumbs only: `→ step0: branch + plan logged`, `→ step0: larch:plan posted`, `→ step0: coder=…`.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success through `--up-to-phase` boundary. |
| 2 | Infrastructure/tracking helper failure: `STEP_FAILED=` plus diagnostic (`GATE_ERROR=` or `PREFLIGHT_ERROR=` on stdout where applicable). `STEP_FAILED=get-issue-state` is emitted when Branch 2 cannot verify issue state or returns a non-`OPEN`/non-`CLOSED` issue state, and `STEP_FAILED=issue-number-required-for-resume` is emitted when a resume sentinel exists but argv omitted `--issue-number`. |
| (other) | argv validation failures (`die_usage`). |

## Bail reasons (`IMPLEMENT_BAIL_REASON`)

| Value | When |
|-------|------|
| *(empty)* | Normal success through requested boundary, infra-only run, skip, or deferred metadata publication. |
| `adopted-issue-closed` | Branch 2 verified the target issue is closed. |
| `adopted-issue-is-pr` | Branch 2 verified the target number is a pull request, not an issue. |
| `tracking-init-failed` | `RUN_ID` derivation failed or `larch-log.sh init` failed; `STALL_TRACKING=true`. Closed / PR bails clear `ISSUE_NUMBER` in the final KV tail; stalled tracking preserves a resolved issue number when available. |
| `not-yet-implemented-phase-3` | Stub `phase_plan_materialize`. |
| `not-yet-implemented-phase-4` | Stub `phase_coder_select`. |

## Behavior mapping (Step 0 SKILL.md)

| Legacy call | Absorbed here |
|-------------|----------------|
| `create-branch.sh --check` | `phase_infra` |
| `session-entry-gate.sh` | `phase_infra` |
| `session-setup.sh` | `phase_infra` |
| Inline `write-session-id` + `token-claude-source` + `write-session-env` + ledgers | `phase_infra` |
| Three-key `read-session-env-key.sh` rehydrate | `phase_infra` (re-read for parity) |
| Sentinel read / resume (`tracking-issue-read.sh --sentinel`) | `phase_tracking` Branch 1 |
| Issue state probe (`get-issue-state.sh`) | `phase_tracking` Branch 2 |
| Manifest init (`larch-log.sh init`) | `phase_tracking` Branch 1 and Branch 2 |
| Metadata summary (`post-tracking-issue.sh`) | `phase_tracking` Branch 2 |
| Rename to `[IMPLEMENTING]` (`tracking-issue-write.sh rename`) | Best-effort inside `phase_tracking` Branch 1 and Branch 2 |

## NEVER #14

This script **must not** append or overwrite `$IMPLEMENT_TMPDIR/session-env.sh` via raw shell redirection (`>>`, `cat > … <<`). Only `write-session-env.sh` writes the file. The offline harness greps the live source for forbidden patterns.

## Edit-in-sync

- `skills/implement/SKILL.md` Step 0 call site and KV parsing.
- `scripts/lint-foreground-markers.sh` DENYLIST (Family B foreground).
- `skills/implement/scripts/test-implement-bootstrap.sh` (+ `.md`).
- This file.
