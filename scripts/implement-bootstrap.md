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
| `--emergency-requested` | no | `true` \| `false` | Default `false`. Forwarded to run-flag persistence and metadata summaries; also controls whether a Preflight `emergency-bypass.log` is surfaced as a warning for the current run. |
| `--upstream-repo` | no | `OWNER/REPO` | Required by callers in fork mode when upstream issue context should be fetched. Validated as one owner/repo slash with GitHub-safe characters. |
| `--run-id` | no | `^[A-Za-z0-9._-]+$` | Preferred Branch 2 run id; takes precedence over `$IMPLEMENT_TMPDIR/session-id` and `LARCH_TOKEN_SESSION_ID`. |
| `--coder` | no | `claude` \| `codex` \| `cursor` | Pins the explicit implementer. When the pinned external tool is unavailable, `phase_coder_select` **waterfalls instead of bailing** (#3207): `--coder codex` → Cursor → Claude; `--coder cursor` → Codex → Claude (`claude` is the always-available main-agent path, so `--coder claude` resolves to claude). A warning names the unavailable tool and the waterfall target. When omitted, `phase_coder_select` runs the Cursor → Codex → Claude waterfall. |
| `--preflight-tmpdir` | with `--issue-number` when `--up-to-phase` is `plan`, `coder`, or `all` | path | Directory containing `plan-from-issue.txt` from Preflight. |
| `--resume-plan-tail` | no | flag | Dirty-tree recovery continuation. Reuses the caller-exported `IMPLEMENT_TMPDIR` / `session-env.sh`, re-runs the dirty-tree checkpoint, and resumes only the Phase 3 tail after that checkpoint succeeds. Reviewer availability is reloaded from the persisted session-env keys; no fresh reviewer probes run on this path. |

## Inputs (Phase 1)

- Git repository state (via `create-branch.sh --check`, `session-setup.sh` preflight).
- Optional caller-env file (`--caller-env`) for forked / nested flows.
- On `--resume-plan-tail`, the caller must preserve `IMPLEMENT_TMPDIR` and the existing `$IMPLEMENT_TMPDIR/session-env.sh`; the bootstrap reuses that session tmpdir instead of allocating a new plan-materialization workspace.
- No direct reads of `$IMPLEMENT_TMPDIR/session-env.sh` before `session-setup.sh` succeeds (empty tmpdir guard).

`phase_plan_materialize` reads `$PREFLIGHT_TMPDIR/plan-from-issue.txt` and writes conventional `$IMPLEMENT_TMPDIR/plan.txt` / `feature-description.txt` artifacts. When `$PREFLIGHT_TMPDIR/emergency-bypass.log` exists, is non-empty, and `--emergency-requested true` is in effect, it appends that file to `$IMPLEMENT_TMPDIR/execution-issues.md` as a `Warnings` entry with site `implement-bootstrap emergency-bypass-log`. Each bypass line must match `BYPASS kind=<lowercase-token> issue=<number>`. Canonical current `kind=` tokens are `missing-plan`, `malformed-plan`, and `audit-refuse`. Invalid logs are converted into a redacted invalid-format warning entry and the run continues; only temporary-file allocation failures still fail closed with `STEP_FAILED=emergency-bypass-log`. Once the warning is appended, resume-tail re-entry does not append the same bypass log again.

## Outputs

### stdout (KV)

Machine-readable `KEY=value` lines. `LARCH_QUIET_DISABLE=1` is forced for this script so `emit_kv` writes to stdout (orchestrator command substitution). **Warnings** for repo / Codex / Cursor health use `larch_err` (stderr) so stdout stays KV-shaped.

**Per-phase:** `phase_infra` emits a consolidated infra block via `emit_infra_kv_block` inside `emit_final_tail`, including `CURRENT_BRANCH`, `IS_MAIN`, `IS_USER_BRANCH`, `USER_PREFIX`, `ENTRY_GATE`, `SKIP_BRANCH_CHECK`, `IMPLEMENT_TMPDIR`, `SESSION_ID`, reviewer keys, `REPO`, `REPO_UNAVAILABLE`, `CLAUDE_SOURCE_OK`, `LARCH_TOKEN_SESSION_ID`, `LARCH_CLAUDE_SOURCE_FILE`, `LARCH_TIMING_LEDGER`, `codex_available`, `cursor_available`, then umbrella keys: `ISSUE_NUMBER`, `RUN_ID`, `BRANCH_SELECTED`, `DEFERRED`, `STALL_TRACKING`, `BRANCH_NAME`, `BRANCH_ACTION`, `PLAN_FILE`, `EMERGENCY_REQUESTED`, `coder`, `coder_fallback`, `IMPLEMENT_BAIL_REASON`.

`phase_plan_materialize` populates `BRANCH_NAME`, `BRANCH_ACTION`, and `PLAN_FILE`. `phase_coder_select` populates `coder` and, only when the implicit waterfall reaches Claude because both external implementers are unavailable, `coder_fallback=true`.

`diff_lines: <N>` in `plan.txt` is informational sizing context. It does not route the implementer; `phase_coder_select` and the bail table below are the routing authority.

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

### Breadcrumbs (stderr via `larch_err`)

Emits operator-visible progress lines on stderr via `larch_err`:

`→ step0: infra ready (tmpdir=$IMPLEMENT_TMPDIR session=$SESSION_ID)`

Tracking phase may also emit:

- `→ step0: tracking adopted #<N> (run=<RUN_ID> branch=<branch-1-resume|branch-2-adopt>)`
- `⏩ step0: tracking — skip (repo-unavailable|forked-target)`
- `→ step0: branch $BRANCH_NAME + plan logged` or `→ step0: branch $BRANCH_NAME`
- `→ step0: larch:plan posted`
- `→ step0: coder=<claude|codex|cursor>`

`LARCH_QUIET_DISABLE=1` keeps stdout readable for KV parsing, but these breadcrumbs still surface on stderr via `larch_err` and are mirrored into the quiet log. `REPO_UNAVAILABLE` and missing-plan early-return paths skip the coder breadcrumb because `coder` is never selected there. An explicit `--coder` naming an unavailable tool still emits the breadcrumb — it now resolves to a waterfall target (#3207) rather than bailing.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success through `--up-to-phase` boundary. |
| 2 | Infrastructure/tracking helper failure: `STEP_FAILED=` plus diagnostic (`GATE_ERROR=` or `PREFLIGHT_ERROR=` on stdout where applicable). `STEP_FAILED=get-issue-state` is emitted when Branch 2 cannot verify issue state or returns a non-`OPEN`/non-`CLOSED` issue state, and `STEP_FAILED=issue-number-required-for-resume` is emitted when a resume sentinel exists but argv omitted `--issue-number`. |
| (other) | argv validation failures (`die_usage`). |

Additional Phase 3 exit-2 diagnostics: `STEP_FAILED=copy-plan` when `$PREFLIGHT_TMPDIR/plan-from-issue.txt` cannot be copied, `STEP_FAILED=gh-issue-view` when issue title/body composition fails, and `STEP_FAILED=resume-plan-tail-sentinel` when dirty-tree resume cannot validate the tracking sentinel or equivalent persisted plan artifacts.

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

**Removed (#3207):** `coder-unavailable` is no longer emitted. An explicit `--coder` naming an unavailable external tool now **waterfalls** to the alternate external then Claude (see the `--coder` row above) instead of bailing, so a pinned-but-unhealthy tool degrades gracefully rather than stalling the run.

## Phase-skip semantics

Phase 3 uses permissive `should_run_phase_plan_materialize`: it runs when there is no bail reason, no stall, and the repo is available. This intentionally allows `DEFERRED=true` paths such as forked targets and `POSTED=false` metadata defers so Step 2 still receives `feature-description.txt` and `plan.txt`. Phase 4's `should_run_post_tracking_phase` is equally permissive for deferred paths: it runs whenever there is no hard bail and no stall. `REPO_UNAVAILABLE` / missing-plan skip is enforced inside `phase_coder_select` itself; those paths return early without populating `coder=`. For the coder gate, "missing-plan" includes empty / unreadable `PLAN_FILE` and missing `$IMPLEMENT_TMPDIR/feature-description.txt`.

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
| Repo-unavailable snapshot-only path (`ensure_untracked_baseline_snapshot`) | `main()` before `phase_plan_materialize`, when `REPO_UNAVAILABLE=true` and `--up-to-phase` is `plan`, `coder`, or `all` |
| Post-bootstrap token/timing marks for plan materialization (`implement Step 0 — plan materialization`) | `phase_plan_materialize` |
| Copy Preflight plan to `$IMPLEMENT_TMPDIR/plan.txt` | `phase_plan_materialize` |
| Issue title/body compose (`gh issue view`) | `phase_plan_materialize` |
| Persist run flags (`persist-implement-run-flags.sh`) | `phase_plan_materialize` |
| Preflight emergency bypass log (`emergency-bypass.log`) | `phase_plan_materialize` warning append |
| Dirty-tree checkpoint (`check-mid-run-dirty-tree.sh --mode checkpoint`) | `phase_plan_materialize` |
| Slug derivation + `create-branch.sh --branch` | `phase_plan_materialize` |
| Branch capture (`git-current-branch.sh`) | `phase_plan_materialize` |
| Plan-goals batch (`run-step1-plan-log.sh`) and plan-review tally (`write-tally.sh`) | `phase_plan_materialize` |
| `larch:plan` summary upsert (`tracking-issue-summary.sh upsert-summary`) | `phase_plan_materialize` |
| Prompt-side implementer waterfall | `phase_coder_select` |

## NEVER #14

This script **must not** append or overwrite `$IMPLEMENT_TMPDIR/session-env.sh` via raw shell redirection (`>>`, `cat > … <<`). Only `write-session-env.sh` writes the file. The offline harness greps the live source for forbidden patterns.

## Resume-tail idempotency

Audit of the `phase_plan_materialize` checkpoint-and-tail region around lines ~750–911. On `--resume-plan-tail` re-entry, resume skips the earlier first-pass block and re-enters at the dirty-tree checkpoint near line ~755; the post-checkpoint helper tail is the portion that can continue after that checkpoint.

**Load-bearing invariant:** `run_dirty_tree_checkpoint` runs at the top of `phase_plan_materialize` after the resume-skip block (`RESUME_PLAN_TAIL=true` skips copy/gh/persist at lines ~708–754). On the canonical dirty-tree-then-resume sequence, the first pass bails at this checkpoint (`IMPLEMENT_BAIL_REASON=dirty-tree`, return 0) **before** any helper at lines ~759–915 runs. Those post-checkpoint helpers therefore execute exactly once across the dirty-tree-then-resume sequence, not twice.

**Post-checkpoint helpers** (idempotency if re-run):

| Helper | Idempotency |
|--------|-------------|
| `create-branch.sh --branch <name>` (~765) | NOT idempotent in isolation — exits 1 with `ERROR: Branch already exists` when the branch exists. Safe on the canonical flow because the first-pass dirty-tree bail prevents this line from running twice. |
| `git-current-branch.sh` (~780) | Read-only; idempotent. |
| `redact-secrets.sh` \| `redact-tmpdir-paths.sh` pipelines (~800, ~847, ~887) | Read-only filters; stable output from stable input. Safe to re-run. |
| `run-step1-plan-log.sh` write (~814) | Writes under `$IMPLEMENT_TMPDIR/larch-logs/` (session-scoped tmpdir). Idempotent within the same tmpdir. |
| `write-tally.sh --phase plan-review` (~851) | Same session tmpdir; atomic compose+write of a tally batch. Idempotent within the same tmpdir. |
| `tracking-issue-summary.sh upsert-summary --marker "<!-- larch:plan v1 runid=$RUN_ID -->"` (~898) | Marker-based upsert; idempotent by construction (finds existing marker and replaces the comment). |
| `append-tool-failure.sh` (~804, ~817, ~831, ~865, ~888, ~902) | Failure-only paths gated on the helper above returning non-zero. NOT independently idempotent if forced to re-run (each call appends to `execution-issues.md`). On the canonical flow each fires at most once because gating helpers are idempotent and the first-pass bail prevents the surrounding block from running twice. Revisit the audit if a future change makes failure paths reachable on resume. |
| `emit_plan_materialize_breadcrumbs` (~915) | Breadcrumb emitter at function tail; reads env state and emits the applicable Step 0 progress lines. Safe to re-run. |

**`phase_tracking` cross-reference (lines ~545–587):** On `RESUME_PLAN_TAIL=true`, `phase_tracking` short-circuits before `rename_to_implementing`, `run_larch_log_init`, or `post-tracking-issue.sh` can re-run, so the duplicate tracking-metadata concern in issue #2977 is already mitigated there.

**Scope:** This audit covers the canonical “dirty-tree bail → single resume” sequence (exercised by `test-implement-bootstrap.sh` case B7-plan-dirty-tree resume tail). Multi-resume sequences (resume → dirty-tree → resume again) are out of scope.

## Edit-in-sync

- `skills/implement/SKILL.md` Step 0 call site and KV parsing.
- `scripts/lint-foreground-markers.sh` DENYLIST (Family B foreground).
- `skills/implement/scripts/test-implement-bootstrap.sh` (+ `.md`).
- `SECURITY.md`, `scripts/test-implement-step2-routing.sh` (+ `.md`), `scripts/test-implement-structure.sh` (+ `.md`), `docs/linting.md`, and `skills/shared/subskill-invocation.md` for Step 0 implementer-selection wording.
- This file.
