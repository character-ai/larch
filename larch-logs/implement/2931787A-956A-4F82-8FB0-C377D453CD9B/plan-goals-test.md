## Goal
Implement issue #5563: [IMPLEMENTING] md-to-py-VII: fold /implement Step 3+4+4.r into one checks-commit-route composite; fold step-2-entry telemetry; collapse post-dispatch + rebase-routing parse-then-branch.

## Implementation Plan
## Plan

## Approach

- Treat `approach-synthesis.txt` as `NO_SKETCHES`.
- Keep the scope to the four approved folds.
- Do not touch the §2.1.5 dispatcher-envelope cross-check.
- Do not change existing Step 5 or Step 6 `checks-commit-route` callers except through additive parser support.
- Keep branch-assertion validation in `SKILL.md`, but make `step-2-post-dispatch` emit the branch routing token that drives routing.
- **Do not** add `step4` to `_COMMIT_ROUTE_SITES` or route it through `_run_commit_route_leg` / `review-and-fix commit-fixes --stage-all`. Step 4 uses a dedicated implementation-commit leg.
- Extend `CommitRouteOutcome` to include `noop` and update every explicit outcome allow-list / parser branch that consumes step4 commit-leg results.
- Pin fresh postlaunch porcelain capture before every pathspec derivation (`implementation-commit-paths.nul` and `step2-recovery-paths-final.nul`); never reuse a stale or missing `step2-postlaunch-porcelain.nul`.
- Thread `--tmpdir "$IMPLEMENT_TMPDIR"` and absolute session tmpdir paths through every `implement recovery-paths` invocation (orchestrator wires, dispatcher helpers, composite hooks).
- Resolve `repo_root` in `run_dispatch_main` (same `git rev-parse --show-toplevel` contract as `step2_dispatch_main`) and pass it into every `_capture_prelaunch_porcelain` / `_capture_postlaunch_porcelain` call; fail closed when git root resolution fails.
- After `step2-dispatch` child returns, parse captured stdout for `STATUS=claude_fallback` plus `ORCHESTRATOR_EDIT_AUTHORITY=allowed`; call `_capture_prelaunch_porcelain(repo_root=...)` when prelaunch artifacts are absent before relaying stdout to the orchestrator.
- **Remove** the early `cursor`/`codex` binary hard-fail in `run_dispatch_main`; missing binaries must flow through `step2_dispatch_main`'s existing `claude_fallback` branches (lines ~2648–2657 today).
- Run `implement recovery-paths` (with explicit `--repo-root`, `--tmpdir`, and fresh postlaunch porcelain) for ordinary fallback pathspec derivation and inside the composite recovery recompute hook.
- Mark Step 2 telemetry once only on the first dispatch under the dispatch lock; Q/A redispatch must not re-fire marks from wrapper, `step2-dispatch`, or external launchers.
- **Remove** `token mark "Step 2 — implementation"` from `launch_codex_implement_main` and `launch_cursor_implement_main`; `run_dispatch_main` owns the sole Step 2 token row (once-only, lock-gated).
- Persist `ship-seed-input.env` whenever branch read and SHA probe succeed, independent of `POST_DISPATCH_NEXT`.
- Align Step 3 composite post-parse routing with the existing Step 6 block (non-zero allowed when `NEXT_ACTION=continue`; parse `CHECKPOINT_NEXT` before treating exit code as invalid).
- Replace the Step 3 pre-fence anti-halt blockquote with the Step 6 composite pattern; remove `RELEVANT_CHECKS_OK`-only success routing and standalone Step 4 breadcrumb routing from that blockquote.
- On the `--rebase-checkpoint-4r` branch, emit **exactly one** line-anchored `NEXT_ACTION=` from the 4.r leg; suppress the outer composite duplicate emit (mirror 7.r relay semantics, not double-print).
- Pin Step 4 commit-failure stall seeding to `stall_step="4"` and bail token `implementation-commit-failed` (not Step 5/7 review-fix tokens).
- Remove dead `step-2-entry.md` from the extracted script registry when deleting the file.
- Delete duplicate Step 2.4 orchestrator recovery-paths / post-checks recompute prose; composite `_run_step4_recovery_recompute` owns post-checks recompute.

## Files to modify/create

### UPDATED: `python/implement_dispatch.py`

- Extend `CommitRouteOutcome` to `Literal["continue", "seeded-stall", "seed-failed", "noop"]`.
  - Add `noop` to `_COMMIT_ROUTE_SUCCESS_OUTCOMES` (or equivalent success/outcome allow-list) wherever step4 no-op must flow to 4.r without stall.
  - Update `_run_commit_route_leg` and composite branches that pattern-match outcomes so `noop` is handled explicitly alongside `continue` for 4.r eligibility.
- Add `_resolve_repo_root() -> Path | None`.
  - Run `git rev-parse --show-toplevel` from the current working tree (same contract as `step2_dispatch_main`).
  - Return `None` on failure; callers map to non-zero / `seed-failed` / fail-closed relay.
- Add `_capture_postlaunch_porcelain(*, repo_root: Path, implement_tmpdir: Path) -> int`.
  - Run `git status --porcelain=v1 -z --untracked-files=all` from `repo_root`.
  - Write bytes atomically to `$IMPLEMENT_TMPDIR/step2-postlaunch-porcelain.nul`.
  - Return non-zero on git failure.
- Add `_capture_prelaunch_porcelain(*, repo_root: Path, implement_tmpdir: Path) -> int`.
  - **Require** `repo_root: Path` (no implicit cwd-only capture).
  - Idempotent when `step2-prelaunch-porcelain.nul` already exists.
  - Write `step2-prelaunch-porcelain.nul`, `step2-prelaunch-content-digests.txt`, and index flag using the same semantics as `_write_prelaunch_baseline`.
  - Return non-zero when `repo_root` is missing or git commands fail.
- Add `_child_stdout_is_claude_fallback(stdout: str) -> bool`.
  - Parse line-anchored `STATUS=claude_fallback` and `ORCHESTRATOR_EDIT_AUTHORITY=allowed` from captured child stdout.
- Add `_derive_pathspec_via_recovery_paths(*, implement_tmpdir: Path, repo_root: Path, out_file: Path) -> int`.
  - Call `_capture_postlaunch_porcelain(repo_root=repo_root, ...)` first.
  - Invoke `implement recovery-paths` with `--repo-root`, `--tmpdir "$IMPLEMENT_TMPDIR"`, absolute prelaunch/postlaunch/digest/out paths, and tmpdir-exclusion semantics matching `recovery_paths_main`.
  - Return non-zero when postlaunch capture or recovery-paths fails.
- Move the Step 2 token/timing logic from `step2_entry_main` into `run_dispatch_main`.
  - Reuse `_rehydrate_larch_triplet`.
  - Preserve the coder and binary-found conditions from `step2_entry_main` for **token** mark eligibility only.
  - Perform validation (`session-env`, plan, feature, plugin root) **before** acquiring `dispatch.lock`.
  - **Remove** the early binary hard-fail blocks (`args.coder == "cursor" and cursor_binary_found != "true"` / codex analogue); always spawn `step2-dispatch` with the session's `--cursor-binary-found` / `--codex-binary-found` flags so missing binaries reach `step2_dispatch_main`'s `claude_fallback` branches.
  - Acquire `dispatch.lock` (`LOCK_EX|LOCK_NB`) **before** any telemetry marks or `.step2-telemetry-marked` write.
  - **Once-only guard** (evaluated only after lock held): skip token/timing marks when `--answers` is non-empty **or** when `$IMPLEMENT_TMPDIR/.step2-telemetry-marked` exists.
  - On first mark (after lock held and validation succeeded): best-effort `token mark` (same coder/binary-found conditions as today's `step2_entry_main`) and best-effort timing mark with `DESIGN_TMPDIR=""` and `LARCH_TIMING_SKILL=implement`.
  - Write `.step2-telemetry-marked` only after successful first-mark invocation while lock is held.
  - Spawn `step2-dispatch` child while lock is held; release lock in `finally`.
  - **After child returns**, before relaying stdout:
    1. When `_child_stdout_is_claude_fallback(result.stdout)`:
       - Resolve `repo_root = _resolve_repo_root()`; on `None`, return non-zero **without** relaying success stdout (fail closed).
       - When prelaunch artifacts are absent, call `_capture_prelaunch_porcelain(repo_root=repo_root, implement_tmpdir=tmpdir)`; on non-zero, return non-zero (fail closed).
    2. Relay child stdout and return child rc unchanged on success paths.
- Remove `step2_entry_main` after `run_dispatch_main` owns the behavior.
- In `step2_dispatch_main`:
  - **Remove** the unconditional `_invoke_cli(["timing", "mark", "Step 2 — implementation"], ...)` at external-implementer entry (line ~2665 today).
  - **Do not** add replacement token/timing marks here; `run_dispatch_main` owns once-only ledger rows.
  - Keep `_write_prelaunch_baseline(st)` on the external-implementer launch path only.
  - Early `claude_fallback` returns (`coder=claude`, missing cursor/codex binary) remain unchanged; prelaunch capture is owned by `run_dispatch_main` post-child hook above.
- Extend `step2_post_dispatch_main`.
  - Add `--expected-branch` with `required=True` (argparse hard failure when omitted).
  - Treat empty `--expected-branch` after parse as `POST_DISPATCH_NEXT=bail` + `BAIL_REASON=main-branch-post-dispatch`.
  - Emit `PHANTOM_*` and optional `COMMIT_SHA=` before routing decisions.
  - On successful named-branch read (and optional SHA probe), call `_persist_ship_seed_context` **before** comparing to `--expected-branch` (seed even on bail).
  - Emit `POST_DISPATCH_NEXT=continue|bail`.
  - Emit `BAIL_REASON=main-branch-post-dispatch` on detached HEAD, git-worktree failure, missing `--expected-branch` match, or branch read failure.
  - Use `POST_DISPATCH_NEXT` only for routing; do not gate ship-seed persistence on `continue`.
- Add `_run_step4_commit_leg(implement_tmpdir, *, deadline_ms) -> tuple[CommitRouteOutcome, str]`.
  - **Do not** invoke `review-and-fix commit-fixes --stage-all`.
  - **Do not** register `step4` in `_COMMIT_ROUTE_SITES`.
  - Pin Step 4 stall metadata:
    - `stall_step="4"`
    - `bail_reason="implementation-commit-failed"`
    - `failure_log_label="Step 4 — implementation commit failed"`
  - Deterministic branch selectors (evaluate in this order):
    1. **External no-op**: `ship-seed-input.env` has non-empty `MANIFEST_PATH` → return `noop` without calling `git commit`.
    2. **Recovery commit**: readable `recovery-metadata.json` **and** readable `recovery-commit-message.txt` → read message in-process (redact if needed), invoke `implement commit --message <text> --pathspec-from-file step2-recovery-paths-final.nul --pathspec-file-nul`. **Do not** use `--message-file` or `git add -A`.
    3. **Ordinary Claude fallback**: readable `implementation-commit-message.txt` **and** readable non-empty `implementation-commit-paths.nul` → read message in-process, invoke `implement commit --message <text> --pathspec-from-file implementation-commit-paths.nul --pathspec-file-nul`. Do not use `git add -A`.
  - Missing required artifacts for the selected branch → `seed-failed` (no `NEXT_ACTION=stall`).
  - After `implement commit` returns, map stdout explicitly:
    - `COMMITTED=true` → `continue` (relay `SHA=` when present).
    - `COMMITTED=false` or non-zero rc → `_seed_durable_stall_state` with `stall_step="4"` and `bail_reason="implementation-commit-failed"`; on success return `seeded-stall`, else `seed-failed`.
    - External no-op branch → `noop`.
  - **Do not** reuse `review-fix-commit-failed`, `commit-failed`, or other Step 5/7 review-fix tokens on this leg.
- Add `_run_step4_recovery_recompute(implement_tmpdir, *, repo_root: Path) -> int`.
  - When `recovery-metadata.json` is present and checks passed:
    - Call `_capture_postlaunch_porcelain(repo_root=repo_root, ...)` immediately before `recovery-paths`.
    - Invoke `implement recovery-paths` with `--repo-root`, `--tmpdir`, absolute porcelain/digest/out paths.
  - Re-run `dirty-tree scope-check` on `step2-recovery-paths-final.nul`; non-zero → emit `BAIL_REASON=recovery-out-of-scope`, return non-zero **without** `NEXT_ACTION=continue`.
  - Call **after** checks pass and **before** `_run_step4_commit_leg`.
- Extend `checks_commit_route_main`.
  - Add `--rebase-checkpoint-4r` (`action="store_true"`).
  - Add `--commit-site step4` as a parser choice distinct from `_COMMIT_ROUTE_SITES`; when `commit_site == "step4"`, call `_run_step4_recovery_recompute` (when applicable) then `_run_step4_commit_leg`.
  - **Step4 commit-failure routing**: `seeded-stall` → `NEXT_ACTION=stall`, return `0` (skip 4.r); `seed-failed` → non-zero without `NEXT_ACTION=stall`; `noop` or `continue` → proceed to 4.r when `--rebase-checkpoint-4r`.
  - **Scope-check failure routing**: non-zero with `BAIL_REASON=recovery-out-of-scope`, no `NEXT_ACTION=continue` or `NEXT_ACTION=stall`.
- Add `_run_4r_rebase_checkpoint(forked_target) -> int` mirroring `_run_7r_rebase_checkpoint` relay shape.
  - Emit **exactly one** line-anchored `NEXT_ACTION=continue` after the probe relay.
  - Return probe rc; **do not** rely on outer composite for a second `NEXT_ACTION=continue`.
- Update `checks_commit_route_main` 4.r tail:
  - When `commit_site == "step4"` and `--rebase-checkpoint-4r` and commit leg outcome is `continue` or `noop`, call `_run_4r_rebase_checkpoint` and return its rc **without** emitting a second `NEXT_ACTION=continue`.
- Keep `CHECKS_COMMIT_ROUTE_OUTER_TIMEOUT_MS` at `15_600_000` ms for the Step 3 fence.

### UPDATED: `python/agents.py`

- **Remove** `proc.run([..., "token", "mark", "Step 2 — implementation"], ...)` from `launch_codex_implement_main` and `launch_cursor_implement_main`.
- Keep `token check-budget` preflight and all other launcher behavior unchanged.
- Step 2 token ledger rows are owned solely by `run_dispatch_main` once-only block (not per external launch or Q/A redispatch).

### UPDATED: `python/cli.py`

- Remove the `("implement", "step-2-entry")` registry row.
- Keep `("implement", "step-2-post-dispatch")` and existing `checks-commit-route` registration.

### UPDATED: `python/larch/core/config.py`

- Add `Final` literals for new post-dispatch wire tokens when imported:
  - `POST_DISPATCH_NEXT_CONTINUE`
  - `POST_DISPATCH_NEXT_BAIL`
  - `POST_DISPATCH_BAIL_MAIN_BRANCH`
  - `BAIL_REASON_RECOVERY_OUT_OF_SCOPE`
- Add `IMPLEMENTATION_COMMIT_FAILED` (or equivalent) for `implementation-commit-failed`.
- Append `implementation-commit-failed` to `STALL_RECOVERY_BAIL_REASON_TOKENS`.

### UPDATED: `skills/implement/SKILL.md`

- Delete the standalone Step 2 entry fence.
- Remove `step-2-entry.md` from the **Extracted Script Registry** list.
- Update Step 2 dispatch prose:
  - `implement run-dispatch` marks Step 2 token/timing internally on the **first** dispatch only (not on `--answers` redispatch); marks run after `dispatch.lock` acquisition.
  - Missing `cursor`/`codex` binaries no longer hard-fail at the wrapper; they flow through `step2_dispatch_main` `claude_fallback`, then `run_dispatch_main` captures prelaunch porcelain before orchestrator Step 2.4 edits.
- Change post-dispatch fence to pass `--expected-branch "$BRANCH_NAME"`.
- Replace prompt-side wrapper exit and branch comparison with `POST_DISPATCH_NEXT` token routing.
- **Step 2.4 ordinary fallback wire (before composite)**:
  - After first `run_dispatch_main` returns `STATUS=claude_fallback` with `ORCHESTRATOR_EDIT_AUTHORITY=allowed`, require `step2-prelaunch-porcelain.nul` / digests (written by dispatcher post-child hook); if absent, fail closed before edits.
  - After main-agent implementation and `normalize-coder-scout`, write `implementation-commit-message.txt`.
  - Derive `implementation-commit-paths.nul` via fresh postlaunch capture + `implement recovery-paths` with `--repo-root`, `--tmpdir`, and absolute porcelain/digest/out paths.
  - Refresh postlaunch porcelain, pathspec, and commit message after checks-repair-loop edits before re-launching the composite.
- **Step 2.4 recovery sub-branch**:
  - **Keep** pre-composite `dirty-tree scope-check` on `$RECOVERY_PATHS_FILE`.
  - **Delete** orchestrator prose that recomputes `recovery-paths` / `step2-recovery-paths-final.nul` after Step 3 checks; composite `_run_step4_recovery_recompute` owns that work.
  - Remove standalone foreground Step 4 recovery commit fence.
- Replace Step 3 pre-fence blockquote, checks fence, Step 4 commit prose/fences, and 4.r rebase fence with one composite fence:

```bash
bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py implement checks-commit-route --checks-site step3 --commit-site step4 --rebase-checkpoint-4r --forked-target "${forked_target:-false}"
```

- Replace Step 3 `> **Continue after child returns.**` blockquote to mirror Step 6 (~675).
- Mark the composite fence immediate-background with `timeout: 15600000` (not `10800000`).
- Keep Step 4 skip breadcrumb when external path no-ops inside composite.
- Update **Rebase Checkpoint Macro**: 4.r folded into Step 3 composite stdout relay, not a standalone foreground probe.

### UPDATED: `skills/implement/references/step2-dispatch.md`

- Update Step 2 timing/token bullet (~line 32):
  - `run_dispatch_main` owns once-only wrapper-side token/timing marks after `dispatch.lock`.
  - `step2-dispatch` must not emit timing rows.
  - External launchers must **not** emit `token mark "Step 2 — implementation"` (removed from `agents.py`); budget preflight remains.
- Document `run_dispatch_main` post-child hook: on `claude_fallback` + `ORCHESTRATOR_EDIT_AUTHORITY=allowed`, resolve `repo_root`, call `_capture_prelaunch_porcelain` when absent, fail closed on git-root or capture failure.
- Document removal of wrapper-side missing-binary hard-fail; missing binaries reach dispatcher fallback branches.

### UPDATED: `skills/implement/references/checks-repair-loop.md`

- Treat Step 3 as a folded composite site (same class as Step 5 self-review, Step 5 MAV, Step 6).
- Pin Step 3 composite launcher in section 2:

python/cli.py implement checks-commit-route --checks-site step3 --commit-site step4 --rebase-checkpoint-4r --forked-target "${forked_target:-false}"

- **Delete** the Step-3-only bullet that treats `NEXT_ACTION=continue` as checks-only success.
- Add Step 3 to folded-sites list in section 4.
- Document orchestrator refresh after repair edits (postlaunch, recovery-paths with `--tmpdir`, commit message).
- Replace `run-step-checks.sh --site step3` with the Step 3 composite pin.
- Pin structure-test needle for this composite argv inside `checks-repair-loop.md`.

### UPDATED: `skills/implement/references/rebase-checkpoint-routing.md`

- Replace separate absorbed-1.r and direct-probe tables with one shared routing table.
- Add input-source note: `1.r` = Step 0 envelope; `4.r` = Step 3 composite stdout; `7.r` = Step 6 composite stdout; `7a.r` = `implement step-7a` stdout.
- Update wording that 4.r is a standalone foreground fence.

### MAY_UPDATE: `skills/implement/references/phantom-probe.md`

- Update only if post-dispatch branch assertion prose becomes stale.
- Keep the `PHANTOM_*` contract unchanged.

### UPDATED: `skills/implement/scripts/step-2-post-dispatch.md`

- Document `--expected-branch` as `required=True`.
- Document `POST_DISPATCH_NEXT=continue|bail` and `BAIL_REASON=main-branch-post-dispatch`.
- State callers route by `POST_DISPATCH_NEXT`, not wrapper exit plus prompt-side byte compare.
- State `_persist_ship_seed_context` runs before `POST_DISPATCH_NEXT` emission.

### UPDATED: `skills/implement/scripts/step-2-entry.sh`

- Delete this file.

### UPDATED: `skills/implement/scripts/step-2-entry.md`

- Delete this file.

### UPDATED: `skills/implement/scripts/step-8-seed-initial.md`

- Remove stale `step-2-entry.sh` reference; prefer live Python/wrapper reference.

### UPDATED: `skills/implement/scripts/run-step-checks.md`

- Remove Step 3 from the active caller list.
- Mark wrapper legacy/helper-only if retained.

### UPDATED: `python/migrated-scripts.tsv`

- Add retired rows for `step-2-entry.md` and `step-2-entry.sh`.

### UPDATED: `python/test_residual_bash.py`

- Build both retired paths from fragments in `test_manifest_excludes_non_residual_orchestration`.

### UPDATED: `python/test_fixtures/plan-fidelity-calibration/diffs/*.diff`

- Update tracked literals referencing `step-2-entry` registry rows or launcher fences.

### UPDATED: `python/test_config.py`

- Add coverage for new config literals including `implementation-commit-failed` in `STALL_RECOVERY_BAIL_REASON_TOKENS`.

### UPDATED: `python/test_implement_dispatch.py`

- Remove registry assertion for `implement step-2-entry`.
- **Delete** direct `step2_entry_main` unit test; replace with `run_dispatch_main` coverage:
  - Step 2 telemetry runs on first dispatch **after lock acquisition**.
  - Second call with `--answers` does **not** re-invoke token/timing mark.
  - Pure `claude_fallback` child return writes prelaunch porcelain/digests with resolved `repo_root` before orchestrator edits.
  - Fail closed when `claude_fallback` but `git rev-parse --show-toplevel` fails.
- **Replace** `test_run_dispatch_fails_closed_on_cursor_binary_missing` with fallback coverage:
  - `coder=cursor` + `CURSOR_BINARY_FOUND=false` → child invoked, stdout `STATUS=claude_fallback`, wrapper returns 0, prelaunch capture runs.
  - Same pattern for `coder=codex` + `CODEX_BINARY_FOUND=false`.
- Add `step2_dispatch_main` coverage proving `--answers` redispatch does **not** emit an additional `Step 2 — implementation` timing row.
- Add `step2_post_dispatch_main` coverage for `POST_DISPATCH_NEXT`, bail, missing `--expected-branch`, detached HEAD, and ship-seed persistence on mismatch.
- Add `_capture_postlaunch_porcelain` / `_derive_pathspec_via_recovery_paths` coverage.
- Add `_run_step4_commit_leg` / `checks_commit_route_main` coverage for `--commit-site step4 --rebase-checkpoint-4r` (all branches from original plan).
- Add `agents.py` launcher coverage (or dispatch integration test) proving external launch no longer calls `token mark "Step 2 — implementation"`.
- Extend timeout and structure tests for Step 3/4/4.r composite.

### UPDATED: `scripts/test-implement-fence-shape.sh`

- Update `EXPECTED_NEW` after SKILL.md edit.

### UPDATED: `scripts/test-implement-structure.sh`

- Remove required Step 2 entry fence.
- Remove required Step 3 `run-step-checks.sh --site step3` fence and standalone 4.r probe fence.
- Add Step 3/4/4.r `checks-commit-route` launcher pin.
- **Delete** the global `timeout: 10800000` tier check (lines 343–344 today).
- **Add** Step 3 composite to the `for script, timeout in [...]` loop (lines 229–236):

```python
(launcher + 'python/cli.py implement checks-commit-route --checks-site step3 --commit-site step4 --rebase-checkpoint-4r', 'timeout: 15600000'),
```

- Optionally `forbid` `run-step-checks.sh --site step3` as an active Step 3 fence after fold.
- Update timeout assertions to `15600000` for the Step 3 composite.
- Update post-dispatch assertions for `--expected-branch` and `POST_DISPATCH_NEXT`.
- Replace `rebase_ref` direct-probe-fences needle with folded-4.r wording.
- Require Step 3 composite launcher pin inside `checks-repair-loop.md`.

### UPDATED: `scripts/test-implement-rebase-macro.sh`

- Require zero standalone 4.r launcher probes.
- Require Step 3/4/4.r composite launcher.
- Replace direct-probe-fences substring with folded-4.r input-source wording.

### UPDATED: `scripts/test-implement-timing-rehydration.sh`

- Remove `step-2-entry.sh` from wrapper self-rehydration list.
- Add coverage that `run_dispatch_main` rehydrates timing keys and marks Step 2 once on first dispatch only (after lock).

### UPDATED: `scripts/test-implement-timing-rehydration.md`

- Remove `step-2-entry.sh` from documented wrapper list.
- State Step 2 telemetry lives in `implement run-dispatch` with once-only semantics under `dispatch.lock`.

### UPDATED: `skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh`

- Update Step 3 expectations to composite launcher and Step 6-parity blockquote.

### UPDATED: `skills/implement/scripts/test-implement-relevant-checks-anti-halt.md`

- Document Step 3 success routes on composite `NEXT_ACTION=continue` (+ `CHECKPOINT_NEXT` for 4.r).

## Edge cases

- `POST_DISPATCH_NEXT=bail` with valid `BRANCH=` still bails; `ship-seed-input.env` updates when branch read succeeds.
- Missing or duplicated `POST_DISPATCH_NEXT` fails closed as `main-branch-post-dispatch`.
- Omitted `--expected-branch` on post-dispatch argv fails closed.
- External implementer path keeps commit no-op (`noop`) when `MANIFEST_PATH` is set in `ship-seed-input.env`.
- Pure `claude_fallback` (`coder=claude`, missing-binary, `--force`) must have prelaunch baseline before Step 2.4 edits; `run_dispatch_main` post-child hook writes it when absent; wrapper fail-closed when git root or capture fails.
- Missing `cursor`/`codex` binary no longer aborts `run_dispatch_main`; dispatcher emits `claude_fallback`, wrapper captures prelaunch, orchestrator proceeds to Step 2.4.
- Ordinary Claude fallback requires fresh postlaunch + non-empty `implementation-commit-paths.nul`; repair-loop re-entry refreshes artifacts with `--tmpdir` and absolute paths.
- Recovery mode keeps pre-composite `scope-check` on `$RECOVERY_PATHS_FILE`; composite owns post-checks fresh postlaunch, `recovery-paths`, and final scope-check on `step2-recovery-paths-final.nul`.
- Post-checks recovery scope-check failure emits `BAIL_REASON=recovery-out-of-scope` → Step 12d.
- `implement commit` failure emits `NEXT_ACTION=stall` with `STALL_STEP=4` / `implementation-commit-failed`; skips 4.r.
- 4.r conflict returns non-zero with exactly one `NEXT_ACTION=continue`; orchestrator parses `CHECKPOINT_NEXT` (Step 6 parity).
- Q/A `--answers` redispatch must not duplicate Step 2 token/timing rows from wrapper, `step2-dispatch`, or external launchers.
- `--rebase-checkpoint-4r` must not double-print `NEXT_ACTION=continue`.

## Failure modes

- Step 4 commit semantics drift if `step4` reuses `review-and-fix commit-fixes --stage-all`. Mitigate with dedicated `_run_step4_commit_leg` and regression test.
- Prelaunch baseline missing on pure `claude_fallback` if `run_dispatch_main` calls `_capture_prelaunch_porcelain` without resolved `repo_root` or skips post-child hook. Mitigate with `_resolve_repo_root`, mandatory `repo_root` param, fail-closed relay, and pytest.
- Missing-binary scenarios blocked if wrapper hard-fail remains. Mitigate by deleting early binary checks and replacing hard-fail test with fallback coverage.
- Step 2 token double-count if launcher marks remain. Mitigate by removing `agents.py` token marks and pytest on launcher + once-only wrapper guard.
- Structure test false-negative if `10800000` tier check remains after Step 3 fold. Mitigate by deleting lines 343–344 and adding Step 3 composite to timeout loop with `15600000`.
- Pathspec empty/stale without fresh postlaunch. Mitigate with `_capture_postlaunch_porcelain` before every `recovery-paths` call.
- Recovery commits use stale pathspecs if composite skips fresh postlaunch. Mitigate with `_run_step4_recovery_recompute` capture-then-recompute.
- Step 3 anti-halt drift causes double-commit or skipped 4.r. Mitigate with Step 6-parity blockquote and structure tests.
- Retired `step-2-entry` literals break lint/calibration. Mitigate with deletions, registry removal, migrated-scripts rows, fixture updates.

## Testing strategy

- Run `make test-implement-fence-shape`.
- Run `scripts/test-implement-structure.sh`.
- Run `scripts/test-implement-rebase-macro.sh`.
- Run `scripts/test-implement-timing-rehydration.sh`.
- Run `skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh`.
- Run `python3 -m pytest python/test_implement_dispatch.py python/test_config.py python/test_residual_bash.py`.
- Run `make lint-retired-scripts`.
- Run `make lint`.

## Acceptance

- One composite fence replaces /implement Step 3 checks, Step 4 commit, and 4.r: `checks-commit-route --checks-site step3 --commit-site step4 --rebase-checkpoint-4r`, immediate-background, `timeout: 15600000`.
- The step4 commit leg is a dedicated `_run_step4_commit_leg` (no `--stage-all`): `noop` on the external path, pathspec commit with the implementation message on claude-fallback, pathspec recovery commit on the recovery path. `CommitRouteOutcome` includes `noop`; `commit_route_main` exits 0 on `noop`.
- Step 2 token/timing telemetry runs once in `run_dispatch_main` under `dispatch.lock`; `--answers` redispatch does not re-mark. `agents.py` launchers drop the Step 2 token mark. `step-2-entry.sh`, `step-2-entry.md`, and the `step-2-entry` registry row are deleted with no dangling references.
- `step-2-post-dispatch` requires `--expected-branch` and emits `POST_DISPATCH_NEXT=continue|bail` plus `BAIL_REASON`. The orchestrator routes on the token and still sets its in-memory bail vars (NEVER #9). The §2.1.5 dispatcher-envelope cross-check (#1058) stays unchanged.
- `rebase-checkpoint-routing.md` has one unified routing table plus an input-source note. `CHECKPOINT_NEXT=continue|load-routing` and the call-site registry rows are preserved.
- The early `cursor`/`codex` binary hard-fail is removed from `run_dispatch_main`; missing binaries flow to `step2_dispatch_main` `claude_fallback` and `run_dispatch_main` captures prelaunch porcelain (fail closed on git-root or capture failure).
- `EXPECTED_NEW` in `test-implement-fence-shape.sh` is updated. `make test-implement-fence-shape`, `scripts/test-implement-structure.sh`, `scripts/test-implement-rebase-macro.sh`, `scripts/test-implement-timing-rehydration.sh`, `test-implement-relevant-checks-anti-halt.sh`, `python3 -m pytest python/test_implement_dispatch.py python/test_config.py python/test_residual_bash.py`, `make lint-retired-scripts`, and `make lint` all pass.

diff_lines: 1380

## Test plan
(no test plan section in plan-file)
