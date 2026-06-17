### FINDING_1: evaluate_failure outer retry loop multiplies agentic 20-cycle cap
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements, Cursor-dyn-ci-loop-correctness
- **Severity**: blocking
- **Concern**: The plan replaces `run_ci_fix` with a single agentic delegate capped at 20 cycles, but `evaluate_failure` still wraps CI recovery in `CI_MONITOR_FIX_WATERFALL_MAX_ATTEMPTS` (up to three outer attempts). That can re-invoke the agentic fixer multiple times per failure evaluation (up to ~60 inner cycles), preserving legacy verify-failed/waterfall-failed retry semantics the agentic loop is meant to own.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Collapse evaluate_failure CI recovery to a single agentic delegate per failed run; remove or bypass the outer attempt loop once agentic-fix returns
  - From Cursor-Requirements: After delegating role=fix to ci agentic-fix, make evaluate_failure call the delegate once per failure evaluation (or stop the outer loop on terminal agentic statuses). Remove or bypass the CI_MONITOR_FIX_WATERFALL_MAX_ATTEMPTS loop for the agentic path.
  - From Cursor-dyn-ci-loop-correctness: In ci_monitor.py evaluate_failure, delegate once to ci agentic-fix per failure evaluation; remove or bypass the CI_MONITOR_FIX_WATERFALL_MAX_ATTEMPTS outer loop for the role=fix path while keeping transient rerun and in-progress deferral before delegation.


### FINDING_2: Shipped conflict/docs still describe version-bump prepass and non-bump-only handoff
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: important
- **Concern**: The plan removes `rebase.py` deterministic prepass and bump-path gating but omits runtime/README and skill prose that still describe non-bump-only handoff and version-file auto-resolution. After merge, ship-pr can still special-case `plugin.json`, `version.go`, and `go.sum` conflicts instead of treating all conflicts uniformly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add these files to the plan and update them to remove deterministic prepass, non-bump-only, bump-only, and version-file trivial auto-resolve language; document unconditional handoff for unresolved conflicts and keep release-only version bump docs
  - From Codex-Requirements: Add these files to the plan and rewrite the handoff/conflict procedure docs so all ship-pr conflicts are treated uniformly with no bump-path gating or version-file auto-resolution, while preserving release-owned version docs


### FINDING_3: Agentic CI loop lacks mechanical HEAD-change gate before push
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The agentic CI loop relies on prompt text for no-commit behavior and does not preserve the existing mechanical HEAD-change gate before push. If Claude commits despite instructions and leaves further edits, the new driver can stage and push on top of a model-authored commit instead of failing closed like the current CI fixer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add an explicit baseline HEAD comparison after the Claude edit turn and before local verification, staging, or push; on mismatch, roll back working-tree deltas and return a fail-closed status such as STATUS=waterfall-failed DETAIL=head-changed; cover it in python/test_ci_agentic_fix.py


### FINDING_4: lint-fix no-tool gate ignores Claude tier on Claude-only hosts
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: `run_lint_fix` returns `main-agent-required` when only Codex and Cursor are absent, before probing or dispatching Claude. That violates change #4 (Claude/Opus first) on Claude-only hosts and prevents the new first tier from ever running.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add claude_present to the guard and dispatch order; only return main-agent-required after Claude, Codex, and Cursor are all unavailable or failed
  - From Cursor-Requirements: Update the pre-dispatch gate and dispatch order: probe Claude availability (for example shutil.which("claude") or launch-claude-ci preflight), try Claude first, then Codex/Cursor, and return main-agent-required only after all three tiers fail or are unavailable.


### FINDING_5: launch-claude-ci is read-only (`claude --print`) but ranked first in write paths
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Concern**: The plan reorders Claude first and routes CI fix and conflict resolution through `launch-claude-ci`, which uses `claude --print` only. Codex and Cursor edit the repo; Claude emits JSON text only. `run_waterfall` treats launcher exit 0 as a winning tier, so conflict resolution can stop after a no-op Claude launch and never reach Codex/Cursor; the agentic CI loop cannot produce working-tree fixes either.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Upgrade launch-claude-ci (or add a role-specific launcher) to a write-capable Claude agent mode with repo-scoped Edit/Write tools, matching launch-codex-ci and launch-cursor-ci. Require post-launch verification for resolve-conflict (unmerged paths cleared) before accepting a tier win, or keep trying lower tiers when conflicts remain.


### FINDING_6: Agentic `STATUS=passed` not wired to `monitor()` success handling
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Concern**: The plan maps agentic `STATUS=passed` to a successful fix, but `monitor()` only treats `fix.status==pushed` (and a few error statuses) as success. A green passive CI wait that returns `passed` would fall through to `STALLED`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: In the ci_monitor.py update, map agentic STATUS=passed to a FixResult monitor() already handles (for example pushed with did_fixing=true), or add an explicit monitor() branch for passed that continues the ship loop without stalling.


### FINDING_7: Agentic `STATUS=ci-fix-exhausted` must map to `FixResult.status=fix-exhausted`
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Concern**: The plan maps `ci-fix-exhausted` to `NEEDS_USER_INPUT`, but `monitor()` only checks `fix.status==fix-exhausted` for operator handoff. Returning `FixResult.status=ci-fix-exhausted` would stall instead of bailing to the operator.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: When translating agentic KV output inside run_ci_fix/evaluate_failure, map STATUS=ci-fix-exhausted to FixResult(status=fix-exhausted, detail=<ci-fix-exhausted prefix...>).


### FINDING_8: `evaluate_failure` must forward `pr` into the agentic delegate
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan has `monitor()` pass `pr` into `evaluate_failure()` and `ci agentic-fix` requires `--pr`, but does not require `evaluate_failure`/`run_ci_fix` to forward `pr` into the delegate. Without that wire, passive CI wait inside the agentic loop cannot run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Thread pr from monitor() through evaluate_failure into run_ci_fix (or directly into python/cli.py ci agentic-fix) and cover it in python/test_ci_monitor.py.


### FINDING_9: Prompt-side exit contract still routes `ci-fix-exhausted` to main-agent CI-fix
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan leaves prompt-side exit-3 routing that sends `ci-fix-exhausted` into the autonomous main-agent CI-fix sub-procedure. After the Opus agentic fixer exhausts 20 cycles, Step 8+ would still try main-agent CI edits instead of bailing to the operator.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Update the plan to revise both Step 8 routing surfaces so ci-fix-exhausted from the delegated agentic fixer goes directly to user/operator bail, not the main-agent CI-fix sub-procedure


### FINDING_10: Agentic `rebase-required` lacks explicit rebase/handoff signal
- **Reviewer(s)**: Codex-dyn-ci-loop-correctness
- **Severity**: important
- **Concern**: The plan maps agentic `rebase-required` as generic success without a carried rebase or handoff signal. `stage_and_push` collapses rebase-prep conflicts or push blockers to `pushed=False` and pending flags, while ship-pr only enters the rebase path when `MonitorResult.goto_rebase` is true. A delegated fixer that hits `rebase-required` can be treated as OK without triggering existing rebase or `PrePushConflictHandoff`, or be demoted to waterfall-failed or ci-fix-exhausted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-ci-loop-correctness: Define the minimal explicit contract: agentic-fix rebase-required either propagates the existing PrePushConflictHandoff behavior in the parent process or maps in ci_monitor to Outcome.OK with goto_rebase=True and preserved CI_FIX_REBASE_PENDING or conflict detail. Update stage_and_push or the new driver to emit that signal instead of a generic push failure.


### FINDING_11: Agentic CI loop lacks forbidden-path/submodule guards before `stage_and_push`
- **Reviewer(s)**: Cursor-dyn-security-boundary
- **Severity**: important
- **Concern**: The agentic CI fixer reuses `stage_and_push` after Opus edits but does not require the mechanical forbidden-path/submodule guards that `run_lint_fix` applies before accepting coder output. Up to 20 autonomous fix→verify→push cycles could let Opus commit and push `.gitmodules` or submodule-path edits that lint-fix would reset.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-security-boundary: Before each `stage_and_push`, add the same forbidden-path scan/revert used in `run_lint_fix` (or a shared helper) and fail the cycle without push when forbidden paths appear in the delta.


### FINDING_12: Claude launcher health classification not extended for waterfall fallback
- **Reviewer(s)**: Codex-dyn-security-boundary
- **Severity**: important
- **Concern**: Claude becomes the first fixer, but the plan does not extend launcher health classification to Claude. Claude auth, quota, or transient launcher failures classify as `other` today, so the new first-tier short-circuit can bail instead of falling through to Codex/Cursor on conflict resolution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-security-boundary: Add Claude auth/quota/transient health detection and tests proving Claude health failures continue the reordered waterfall while Claude non-health failures still short-circuit


### FINDING_13:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/agents.py:2514-2525,4797-4843
- **Concern**: [SCOPE-REDUCTION] Plan widens the agent launch contract with --pr, --base-remote, --base-ref, and --max-cycles. Scenario: Those inputs belong to the new ci agentic-fix driver. Forwarding them through launch-claude-ci and build_launch_argv adds parser, test, and contract churn without helping the single-cycle Claude edit prompt.
- **Proposed resolution**: Keep those args only on python/cli.py ci agentic-fix. Leave agent launch-*-ci on the existing role/output/run-id/repo/plan-file/failure-log/conflict-files surface.


### FINDING_14:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/agents.py:2514-2529,4797-4839
- **Concern**: [SCOPE-REDUCTION] Planned per-tier launcher args widen the CI launcher surface unnecessarily. Scenario: ci agentic-fix already owns --pr, --base-remote, --base-ref, and --max-cycles; passing them through agent launch-claude-ci either forces unrelated parser churn or fails argparse if parser support is missed
- **Proposed resolution**: Keep those args only on ci agentic-fix; keep build_launch_argv limited to fields the tier prompt actually consumes


### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: docs/external-reviewers.md:99
- **Concern**: [SCOPE-REDUCTION] Row 99 bundles review-and-fix with lint-fix but only lint-fix is in scope. Scenario: Issue change #4 targets python/checks.py only. Updating the combined review-and-fix / lint-fix row to Claude-first would misdocument review_and_fix.py, which remains Cursor then Codex then main agent.
- **Proposed resolution**: Split the table row or limit the edit to the lint-fix bullet: lint-fix becomes Claude/Opus to Codex to Cursor to main-agent-required; leave review-and-fix coder order unchanged.



### FINDING_1: Post-tier unmerged-path verification conflicts with stock `run_waterfall`
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Stock `run_waterfall` returns a winner when `launcher_exit==0` on the first tier, even if conflict markers remain (`python/agents.py:4972-4973`). With Claude first, `launch_claude_ci` can exit 0 while `_unmerged_paths` is non-empty. `_resolve_conflicts` then stalls or handoffs instead of continuing to Codex/Cursor. The plan’s post-tier verification requirement is incompatible with an unchanged wholesale `run_waterfall` call.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace the wholesale run_waterfall call in _resolve_conflicts with an explicit tier loop that launches one tier, checks _unmerged_paths, reverts the tier delta and continues when paths remain, and preserves first-fixer non-health short-circuit only for the first tier.
  - From Cursor-Pragmatic: Replace the run_waterfall call in _resolve_conflicts with an explicit per-tier loop: launch tier, require _unmerged_paths empty, revert tier delta and continue on failure; keep first-fixer non-health short-circuit on the first tier only


### FINDING_2: Step 8+ SKILL prose still routes `ci-fix-exhausted` through autonomous main-agent CI-fix
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `skills/implement/SKILL.md` (around line 744) still bundles `ci-fix-exhausted` with `first-fixer-non-health` in the 12-step autonomous sub-procedure. Only `ship-pr-exit-matrix.md` is listed for the routing change, so operator flow would still send exhausted agentic CI-fix back to the main agent instead of Step 12d bail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add ### UPDATED: skills/implement/SKILL.md; remove ci-fix-exhausted from autonomous CI-fix tokens and route it to Step 12d operator bail after agentic exhaustion


### FINDING_3: Claude health classification helpers not wired for conflict waterfall continuation
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan mentions `classify_launch_failure(tool=claude)` only. `_AUTH_RE`, `is_quota_failure`, and `is_transient_infra_failure` lack Claude support. Auth, quota, and transient infra failures on the first (Claude) tier will not classify as health failures, breaking first-fixer non-health short-circuit semantics when Claude leads the waterfall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend _AUTH_RE, is_quota_failure, and is_transient_infra_failure for claude (or document equivalent inline logic in classify_launch_failure) and add tests mirroring Codex/Cursor health cases


### FINDING_4: Write-capable `launch-claude-ci` argv contract is unspecified
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `launch_claude_ci_main` uses read-only `claude --print`. The agentic ship-pr CI fixer must apply working-tree edits. Without a pinned write-capable invocation parallel to `launch-cursor-ci`, the Opus CI fixer cannot mutate the repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Specify and test the write-capable Claude launcher argv (repo-scoped Edit/Write, no model commits) in agents.py plan section, matching project claude -p permission conventions


### FINDING_5: `evaluate_failure` outer 3-attempt loop can re-run the full agentic delegate
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: After `run_ci_fix` becomes a single agentic-fix delegate (≤20 internal cycles), the existing `CI_MONITOR_FIX_WATERFALL_MAX_ATTEMPTS` loop in `evaluate_failure` (`python/ci_monitor.py:1486-1607`) may invoke that delegate up to three times per monitor failure, multiplying fix cycles beyond the intended 20-cycle cap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Collapse evaluate_failure to a single agentic-fix delegate per failure evaluation; retain only transient rerun, in-progress wait, and ci_fix_rebase_pending push-only handling outside the delegate


### FINDING_6: Plan omits removing pre-dispatch gate that skips Claude when externals are absent
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Concern**: `python/checks.py:1840-1856` returns `main-agent-required` when both Codex and Cursor are absent, before any Claude dispatch. With Claude on PATH but both externals down, lint-fix never reaches the Opus tier, violating requirement 4 (Claude/Opus first).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Delete or reorder the early `if not codex_present and not cursor_present` block so Claude is attempted first and main-agent-required is returned only after Claude, Codex, and Cursor are unavailable or have failed.


### FINDING_7: Claude lint-fix tier lacks a prompt-compatible launcher contract
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan routes `_run_claude` through `launch-claude-ci`, but that launcher only accepts CI-role inputs and builds a CI prompt from `--failure-log`/`--plan-file`; `--failure-log` also requires `IMPLEMENT_TMPDIR`. Routine pre-ship and `/review-and-fix` lint failures would get the wrong CI prompt, or Claude would be skipped before Codex/Cursor. The Claude/Opus-first lint-fix policy is not reliably deliverable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Revise the plan to add a dedicated safe prompt-file path for the Claude lint-fix helper, or extend launch-claude-ci with an explicit lint-fix prompt mode that consumes checks.py prompt_body, uses claude-opus-4-8, does not push or wait on CI, and works for all run_lint_fix callers.


### FINDING_8: Version-bump and non-bump ship-pr handoff language remains outside the listed update set
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan removes bump-path gating in `rebase.py` but omits `PrePushConflictHandoff` default messaging (`python/errors.py:26-35`) and the implement-skill note on postbump/non-bump ship-pr conflict behavior (`skills/implement/SKILL.md:83-85`). After unconditional handoff, operator-facing errors and skill instructions would contradict the release-only version-bump contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add these surfaces to the plan. Make the PrePushConflictHandoff message generic for unresolved pre-push conflicts, remove or rewrite the skills/implement/SKILL.md postbump/non-bump note, and add a focused grep or test update for retired ship-pr bump wording.


### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/rebase.py:261-289
- **Concern**: [SCOPE-REDUCTION] Per-tier unmerged-path verification is incompatible with stock run_waterfall. Scenario: Plan requires reverting a no-op Claude tier and continuing to Codex/Cursor, but run_waterfall returns on first launcher_exit==0 before rebase checks unmerged paths
- **Proposed resolution**: Replace run_waterfall in _resolve_conflicts with an explicit tier loop that verifies _unmerged_paths is empty before accepting a tier, reverting and continuing otherwise




### FINDING_1: Stall-recovery chain still routes `ci-fix-exhausted` to `step8-shippr`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: blocking
- **Concern**: The plan reroutes `ci-fix-exhausted` to Step 12d operator bail, but stall-recovery surfaces (`stall_recovery.py`, `stall-recovery-report.sh`, related tests/docs) still classify `ci-fix-exhausted` as recoverable with `RESUME_HINT=step8-shippr`. Exit matrix, SKILL prose, and Step 18a recovery would disagree with the new operator-only bail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/stall_recovery.py, skills/implement/scripts/stall-recovery-report.sh, skills/implement/scripts/test-stall-recovery-report-1.sh, skills/implement/scripts/test-stall-recovery-report-2.sh, and python/test_ship.py (ci-fix-exhausted classifier). Make ci-fix-exhausted unrecoverable with RESUME_HINT=none; drop step8-shippr resume for this bail token.
  - From Cursor-Innovation: Add UPDATED steps for python/stall_recovery.py, skills/implement/scripts/stall-recovery-report.sh, skills/implement/references/stall-recovery.md, python/test_ship.py, python/test_stall_recovery.py, scripts/test-implement-step8-exit3-first-fixer.sh, and skills/implement/scripts/test-stall-recovery-report-2.sh; classify ci-fix-exhausted as unrecoverable (RESUME_HINT=none) consistent with Step 12d operator bail


### FINDING_2: `ci_fix_rebase_pending` push-only retry lost when outer loop / `run_ci_fix` removed
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The `evaluate_failure` refactor removes the outer `CI_MONITOR_FIX_WATERFALL_MAX_ATTEMPTS` loop and plans to delete `run_ci_fix`, but the plan does not pin where bounded push-only retry for `ci_fix_rebase_pending` lives, its retry cap, or tests. Today that path retries push-only `run_ci_fix` / `stage_and_push` (up to 3 attempts with backoff). Removing the loop without an explicit replacement can cap push retries at one and break flaky post-rebase push recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Restructure evaluate_failure: single agentic delegate for normal fix; separate ci_fix_rebase_pending branch that calls run_ci_fix push-only or stage_and_push directly; do not nest pending retry inside the removed outer loop
  - From Cursor-Innovation: Explicitly retain run_ci_fix ci_fix_rebase_pending-only branch or document inlined stage_and_push equivalent in evaluate_failure; add test that rebase-pending retry still pushes without re-running ci agentic-fix
  - From Cursor-Pragmatic: Keep a bounded push-only retry loop (same cap or explicit new constant) that calls slim `run_ci_fix(..., ci_fix_rebase_pending=True)` without re-invoking `ci agentic-fix`
  - From Cursor-Requirements: In `### UPDATED: python/ci_monitor.py`, add an explicit early `evaluate_failure` branch: when `ci_fix_rebase_pending=True`, call `stage_and_push` only (no `ci agentic-fix`), preserve bounded retry/backoff if still required, and add/keep tests for the existing `ci_fix_rebase_pending` cases in `python/test_ci_monitor.py`.


### FINDING_7: Shared HEAD guard extraction may break lint-fix commit-acceptance semantics
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `checks.py` uses `_head_change_invalid_after_dispatch` (strict no-commit on clean baseline). `coder_delta_guards` may only list simple HEAD compare. Conflating them can break valid lint-fix commits or accept invalid ones in CI agentic fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Keep strict no-commit HEAD compare in CI agentic fix; move or preserve `_head_change_invalid_after_dispatch` unchanged for lint-fix (do not replace with naive HEAD equality in `run_lint_fix`)


### FINDING_9: Claude conflict mode lacks staging; post-tier unmerged check can reject valid resolutions
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Claude conflict mode is planned with only Edit/Write tools while the conflict contract requires staging resolved files. After Claude edits conflict markers, Git still reports unmerged paths until `git add`; the planned post-tier `_unmerged_paths` check can reject and revert the Claude tier, so the new first tier cannot actually win conflict resolution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Make the conflict role stageable: either allow the minimal Bash git-add command for `launch-claude-ci --role resolve-conflict` or have `_resolve_conflicts` stage resolved conflict files after marker verification; keep commits and pushes outside the model




### FINDING_2: Agentic delegate omits implement session fields for run-log flush
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The planned `ci agentic-fix` argv includes `--pr`, `--repo`, `--run-id`, and `--plan-file` but not `--implement-tmpdir` or ship state fields. `stage_and_push` calls `run_logs.flush_logs_pre` only when `ctx` is set. An in-loop rebase+force-push in the delegated subprocess may skip the pre-push log refresh and return `ci_fix_rebase_pending` or push failure, unlike today's in-process `run_ci_fix(..., ctx=ctx)` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `--implement-tmpdir` (and `--state-file` or `--no-logs-commit` as needed) to `ci agentic-fix`, reconstruct `RunContext` inside `ci_agentic_fix.py`, and pass `ctx` into `stage_and_push`; thread the same fields from `evaluate_failure` when spawning the delegate.


### FINDING_4: Explicit conflict loop omits launcher-failure handling from `run_waterfall`
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan's explicit per-tier conflict loop replaces `agents.run_waterfall` but documents success-path staging and first-fixer short-circuit without non-zero launcher-exit handling: no `paths_delta_revert`, no `effective_failure_class` health-vs-other routing, and no first-tier other short-circuit. Claude-first conflict resolution can regress (e.g., auth/quota on tier 1 may short-circuit instead of falling through to Codex/Cursor, or failed tiers may leave dirty deltas for the next tier).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Spell out the failure branch in the _resolve_conflicts loop: on launcher failure revert the tier delta, continue when failure_class is health, and short-circuit only when idx==0 and failure_class is other; add tests mirroring test_agents.py first-fixer cases under the explicit loop.


### FINDING_5: Conflict prompt still allows model-driven rebase continuation
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: With write-capable Claude first, the `role=resolve-conflict` prompt still instructs the model to stage resolved files and run `git rebase --continue`. The model may advance or disturb rebase state before the driver stages and verifies conflicts; the driver can then see advanced or missing rebase state and stall or move HEAD outside its planned boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Revise the plan so role=resolve-conflict prompts tell the model to edit conflict files only; do not stage or run git rebase --continue; _resolve_conflicts owns staging and rebase_continue


### FINDING_6: Plan maps to nonexistent `FixResult.did_fixing` field
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan maps a green passive-wait outcome to `FixResult` with a `did_fixing` field, but `FixResult` has no such field (only `MonitorResult` carries `did_fixing`). Following the plan literally raises `TypeError` or forces unnecessary dataclass churn; a successful pushed fix may not route through `monitor()`'s existing `fix.status == "pushed"` → `did_fixing=True` handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Map passed to FixResult(status="pushed", winning_tier="claude", delta_paths=...) and let monitor's existing pushed handling set did_fixing=True; do not pass did_fixing into FixResult



### FINDING_2: Agentic delegate omits repo working-tree cwd contract
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: `evaluate_failure` spawns `ci agentic-fix` without passing the parent process working directory (`cwd=repo_root`) or an explicit `--cwd`/`--repo-root` flag. `RunContext.repo` is the GitHub slug, not a filesystem path, so git reads, `launch_tier`, `verify_job_locally`, and `stage_and_push` inside the delegate can run against the wrong directory when the parent `cwd` differs from the repo root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Document and implement that `evaluate_failure` passes the parent `cwd` into the subprocess invocation (or add `--repo-root` to `ci agentic-fix` and thread it through every git call)
  - From Cursor-Pragmatic: Add --cwd (or --repo-root) to the ci agentic-fix CLI surface, thread evaluate_failure's cwd into the subprocess invocation, and assert in test_ci_monitor.py that runner.run uses the same cwd the in-process path used today.


### FINDING_4: local-unfixable drops fix-exhausted promotion parity
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Replacing `run_ci_fix` with agentic KV mapping drops the `code_fix_attempted_on_ready_log` to fix-exhausted promotion for local-unfixable outcomes. Today, when fixers run but jobs are later deemed unfixable (toolchain/prepare_python_toolchain path), `evaluate_failure` returns fix-exhausted with the `ci-fix-exhausted` detail prefix; the plan maps agentic `STATUS=local-unfixable` straight to `NEEDS_USER_INPUT`, changing operator routing and stall detail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Either emit a distinct agentic status (or DETAIL flag) when fix was attempted before local-unfixable, or have evaluate_failure promote local-unfixable to fix-exhausted using the same code_fix_attempted_on_ready_log rule; extend test_ci_monitor.py to cover post-attempt unfixable parity with evaluate_failure_exhausted_routes_needs_user_input.


### FINDING_5: Agentic cycle omits delta path computation before stage_and_push
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan captures baseline tracked/untracked sets and calls `ci_monitor.stage_and_push` after verification, but never computes changed paths via `ci_monitor._delta_paths` (or equivalent). `stage_and_push` only commits when `delta_paths` is non-empty, so a successful Opus edit plus passing local verify would still return push failed with no commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: After verification passes, compute delta_paths from the pre-cycle baselines (same contract as ci_monitor.run_ci_fix today), pass them into stage_and_push with commit_label claude, and treat empty delta as a no-progress cycle outcome



