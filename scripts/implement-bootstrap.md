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
| `--preflight-tmpdir` | with `--issue-number` when `--up-to-phase` is `plan`, `coder`, or `all` | path | Directory containing `plan-from-issue.txt` from Preflight. |
| `--resume-plan-tail` | no | flag | Dirty-tree recovery continuation. Reuses the caller-exported `IMPLEMENT_TMPDIR` / `session-env.sh`, re-runs the dirty-tree checkpoint, and resumes only the Phase 3 tail after that checkpoint succeeds. |

## Inputs (Phase 1)

- Git repository state (via `create-branch.sh --check`, `session-setup.sh` preflight).
- Optional caller-env file (`--caller-env`) for forked / nested flows.
- On `--resume-plan-tail`, the caller must preserve `IMPLEMENT_TMPDIR` and the existing `$IMPLEMENT_TMPDIR/session-env.sh`; the bootstrap reuses that session tmpdir instead of allocating a new plan-materialization workspace.
- No direct reads of `$IMPLEMENT_TMPDIR/session-env.sh` before `session-setup.sh` succeeds (empty tmpdir guard).

`phase_plan_materialize` reads `$PREFLIGHT_TMPDIR/plan-from-issue.txt` and writes conventional `$IMPLEMENT_TMPDIR/plan.txt` / `feature-description.txt` artifacts.

## Outputs

### stdout (KV)

Machine-readable `KEY=value` lines. `LARCH_QUIET_DISABLE=1` is forced for this script so `emit_kv` writes to stdout (orchestrator command substitution). **Warnings** for repo / Codex / Cursor health use `larch_err` (stderr) so stdout stays KV-shaped.

**Per-phase:** `phase_infra` emits a consolidated infra block via `emit_infra_kv_block` inside `emit_final_tail`, including `CURRENT_BRANCH`, `IS_MAIN`, `IS_USER_BRANCH`, `USER_PREFIX`, `ENTRY_GATE`, `SKIP_BRANCH_CHECK`, `IMPLEMENT_TMPDIR`, `SESSION_ID`, reviewer keys, `REPO`, `REPO_UNAVAILABLE`, `CLAUDE_SOURCE_OK`, `LARCH_TOKEN_SESSION_ID`, `LARCH_CLAUDE_SOURCE_FILE`, `LARCH_TIMING_LEDGER`, `codex_available`, `cursor_available`, then umbrella keys: `ISSUE_NUMBER`, `RUN_ID`, `BRANCH_SELECTED`, `DEFERRED`, `STALL_TRACKING`, `BRANCH_NAME`, `BRANCH_ACTION`, `PLAN_FILE`, `coder`, `coder_fallback`, `IMPLEMENT_BAIL_REASON`.

`phase_plan_materialize` populates `BRANCH_NAME`, `BRANCH_ACTION`, and `PLAN_FILE`; Phase 4 keys remain present with empty values for parser stability.

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

Plan materialization may also emit `→ step0: branch $BRANCH_NAME + plan logged` when `run-step1-plan-log.sh` succeeds, otherwise `→ step0: branch $BRANCH_NAME`. `→ step0: larch:plan posted` is emitted only when the `tracking-issue-summary.sh upsert-summary` call succeeds. Breadcrumbs require `LARCH_QUIET_BREADCRUMBS` truthy. Future Phase 4 may add `→ step0: coder=…`.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success through `--up-to-phase` boundary. |
| 2 | Infrastructure/tracking helper failure: `STEP_FAILED=` plus diagnostic (`GATE_ERROR=` or `PREFLIGHT_ERROR=` on stdout where applicable). `STEP_FAILED=get-issue-state` is emitted when Branch 2 cannot verify issue state or returns a non-`OPEN`/non-`CLOSED` issue state, and `STEP_FAILED=issue-number-required-for-resume` is emitted when a resume sentinel exists but argv omitted `--issue-number`. |
| (other) | argv validation failures (`die_usage`). |

Additional Phase 3 exit-2 diagnostics: `STEP_FAILED=copy-plan` when `$PREFLIGHT_TMPDIR/plan-from-issue.txt` cannot be copied, and `STEP_FAILED=gh-issue-view` when issue title/body composition fails.

## Bail reasons (`IMPLEMENT_BAIL_REASON`)

| Value | When |
|-------|------|
| *(empty)* | Normal success through requested boundary, infra-only run, skip, or deferred metadata publication. |
| `adopted-issue-closed` | Branch 2 verified the target issue is closed. |
| `adopted-issue-is-pr` | Branch 2 verified the target number is a pull request, not an issue. |
| `tracking-init-failed` | `RUN_ID` derivation failed or `larch-log.sh init` failed; `STALL_TRACKING=true`. Closed / PR bails clear `ISSUE_NUMBER` in the final KV tail; stalled tracking preserves a resolved issue number when available. |
| `run-flags-persist-failed` | `persist-implement-run-flags.sh` returned non-zero; `STALL_TRACKING=true`. |
| `dirty-tree` | `check-mid-run-dirty-tree.sh --mode checkpoint` reported `STATUS=dirty` or `STATUS=unknown`; no stall flag so the orchestrator can route to dirty-tree recovery, then re-enter with `--resume-plan-tail` inside the existing `IMPLEMENT_TMPDIR` for another checkpoint before any Phase 3 tail helper runs. |
| `branch-create-failed` | `create-branch.sh --branch` returned non-zero, or `git-current-branch.sh` could not capture a non-empty branch name after plan materialization; `STALL_TRACKING=true`. |
| `not-yet-implemented-phase-4` | Stub `phase_coder_select`. |

## Phase-skip semantics

Phase 3 uses permissive `should_run_phase_plan_materialize`: it runs when there is no bail reason, no stall, and the repo is available. This intentionally allows `DEFERRED=true` paths such as forked targets and `POSTED=false` metadata defers so Step 2 still receives `feature-description.txt` and `plan.txt`. Phase 4 keeps the stricter `should_run_post_tracking_phase`, which also skips when `DEFERRED=true`.

## Behavior mapping (Step 0 SKILL.md)

| Legacy call | Absorbed here |
|-------------|----------------|
| `create-branch.sh --check` | `phase_infra` |
| `session-entry-gate.sh` | `phase_infra` |
| `session-setup.sh` | `phase_infra` |
| Inline `write-session-id` + `token-claude-source` + `write-session-env` + ledgers | `phase_infra` |
| Resume-tail tmpdir/session-env reuse after dirty-tree recovery | `phase_infra` (`--resume-plan-tail`) |
| Three-key `read-session-env-key.sh` rehydrate | `phase_infra` (re-read for parity) |
| Sentinel read / resume (`tracking-issue-read.sh --sentinel`) | `phase_tracking` Branch 1 |
| Issue state probe (`get-issue-state.sh`) | `phase_tracking` Branch 2 |
| Manifest init (`larch-log.sh init`) | `phase_tracking` Branch 1 and Branch 2 |
| Metadata summary (`post-tracking-issue.sh`) | `phase_tracking` Branch 2 |
| Rename to `[IMPLEMENTING]` (`tracking-issue-write.sh rename`) | Best-effort inside `phase_tracking` Branch 1 and Branch 2 |
| Session untracked baseline (`snapshot-untracked.sh --output … --nul`) | `phase_plan_materialize` |
| Post-bootstrap token/timing marks for plan materialization (`implement Step 0 — plan materialization`) | `phase_plan_materialize` |
| Copy Preflight plan to `$IMPLEMENT_TMPDIR/plan.txt` | `phase_plan_materialize` |
| Issue title/body compose (`gh issue view`) | `phase_plan_materialize` |
| Persist run flags (`persist-implement-run-flags.sh`) | `phase_plan_materialize` |
| Dirty-tree checkpoint (`check-mid-run-dirty-tree.sh --mode checkpoint`) | `phase_plan_materialize` |
| Slug derivation + `create-branch.sh --branch` | `phase_plan_materialize` |
| Branch capture (`git-current-branch.sh`) | `phase_plan_materialize` |
| Plan-goals batch (`run-step1-plan-log.sh`) and plan-review tally (`write-tally.sh`) | `phase_plan_materialize` |
| `larch:plan` summary upsert (`tracking-issue-summary.sh upsert-summary`) | `phase_plan_materialize` |

## NEVER #14

This script **must not** append or overwrite `$IMPLEMENT_TMPDIR/session-env.sh` via raw shell redirection (`>>`, `cat > … <<`). Only `write-session-env.sh` writes the file. The offline harness greps the live source for forbidden patterns.

## Edit-in-sync

- `skills/implement/SKILL.md` Step 0 call site and KV parsing.
- `scripts/lint-foreground-markers.sh` DENYLIST (Family B foreground).
- `skills/implement/scripts/test-implement-bootstrap.sh` (+ `.md`).
- This file.
