## Goal
Implement issue #6049: [IMPLEMENTING] [BUG] ship-pr merge conflicts route to Step 16/18 teardown instead of CI-failure-….

## Implementation Plan
## Summary

`/implement` gives CI failures a closed-loop treatment: the ship driver bails with a machine reason, `ship route-exit` emits `NEXT_ACTION=ci-fix`, the main agent fixes, commits, and re-invokes `step-8-ship.sh`. Merge-conflict-shaped failures do not get that parity. Only one flavor (post-PR fixer-waterfall exhaustion, `PrePushConflictHandoff`) reaches the main-agent conflict-resolution loop, and even that rides the generic `NEXT_ACTION=stall` token plus two state-file KVs the orchestrator must remember to read. Every other conflict flavor routes into the "Otherwise continue to Step 16 with `STALL_TRACKING`, then Step 18" arm: pre-PR `postbump` rebase conflicts, bare-`Stalled` bails inside `_resolve_conflicts`, `POLICY_DENIED`-with-conflict-signal merges, and the `no-ci-checks-observed` stall whose sanctioned recovery re-monitors an unchanged head that GitHub will never build. A live run (F7F30088, PR #6041) walked Step 16/18 teardown and burned a capped reship loop on exactly this.

## Original report

> There is a bug, apparently, in ship-pr machinery of `/implement`, wherein when it detects merge conflict (I am not even sure it is detecting it properly, but in the face of merge conflict, what happens is that) it returns control to main agent but in a way that makes main agent go to Step 18 Cleanup, instead of handling it like it does the CI failure situation. Proper behavior: merge conflicts undergo the same treatment as CI failures: main agent takes over, fixes the problem, commits, and re-invokes ship-pr machinery.

Reported live from an in-flight run in the larch1 clone (run `F7F30088-0014-47D6-A2F9-A899E1A79955`, PR #6041, issue #5887, 2026-07-02).

## Reproduction scenario

Concurrent-clone setting: run `/implement --merge` while sibling PRs merge into `main` mid-run (here #6042 through #6046 landed during the run). Any of these then reproduces a conflict-shaped stall that bypasses the fix-and-reship loop:

1. **Cross-PR generated-file conflict + no-checks loop (observed live).** The branch becomes semantically conflicted with advanced `main` through a regenerated file (`python/skill-closure-baseline.json`). CI fails; main agent ci-fixes without rebasing; the reship pushes a head for which GitHub never creates a workflow run; `ci_monitor` bails `no-ci-checks-observed` at the ~300s startup deadline; route-exit emits `NEXT_ACTION=stall`; the orchestrator walks Step 16 then Step 18; Step 18a classifies `transient-infra` / `step8-shippr` and reships; the reship re-monitors the same head and is guaranteed to bail the same way. Cap: 4 attempts, roughly 5.5 minutes each.
2. **Pre-PR rebase conflict.** Make the feature branch conflict with `origin/main` in any file outside `REBASE_AUTORESOLVE_GENERATED_FILES` and run Step 8. `finalize.postbump` aborts the rebase and returns terminal `STALLED` / `rebase-failed`. No fixer waterfall runs, no conflict-resolution handoff. `skills/implement/SKILL.md` documents this as "operators must resolve those Step 8b rebase conflicts manually".
3. **Post-PR waterfall bare-stalls.** Inside `_resolve_conflicts`, the flavors "conflict fixer touched forbidden path", "rebase --continue failed without unmerged paths", and "git rebase --skip failed" raise plain `Stalled` with no `RESUME_PHASE`/`CALLER_KIND`, so the stall arm's "Otherwise" branch sends them to Step 16/18 despite known conflict context.

## Expected behavior

Merge conflicts, in every recoverable flavor, get the CI-failure treatment:

- The driver hands off with a first-class deterministic routing token (for example `NEXT_ACTION=conflict-fix`), emitted by Python `ship route-exit` from persisted state, analogous to `ci-fix`.
- The main agent resolves (rebase, `conflict-resolution.md` Phase 1-4, regenerate generated files), commits, and re-invokes `step-8-ship.sh`.
- No Step 16/18 teardown walk for recoverable conflict states, and no re-monitoring of an unchanged head that cannot acquire checks.

## Observed behavior

Timeline from the live run (journal, `larch-quiet-ship.py-*.log`, `gh run list`, reflog):

- 18:57Z: CI failed on head `4fac4b38a`. Ship exited 3, `needs_user_reason=first-fixer-non-health`, `NEXT_ACTION=ci-fix`. Main agent fixed CI (commit `53a4a41a9` + log flush `ed0bd23fa`) and reshipped. This is the working CI-failure loop.
- ~19:24-19:29Z: reship pushed head `ed0bd23fa`. GitHub never created a workflow run for that head (`gh run list` shows runs only for `4fac4b38a` at 18:57, `7486ac510` at 18:58 from the bail-path terminal-snapshot push, and `56904c311` at 19:42). `ci_monitor` bailed at 307s: `STALLED` `no-ci-checks-observed`, exit 4, `STALL_TRACKING=true`.
- 19:30Z: `route-exit` wrote `NEXT_ACTION=stall`, `DETAIL=no-ci-checks-observed`. `RESUME_PHASE` and `CALLER_KIND` were empty in `ship-pr-state.sh`, so per the SKILL stall arm the main agent continued to Step 16 and then **Step 18**.
- 19:31Z: Step 18a classified `FAILURE_CLASS=transient-infra` (`MATCHED_CLASSIFIER_PATTERN=transient-output`), `RESUME_HINT=step8-shippr`, and reshipped.
- 19:31-19:36Z: the reship re-monitored the same head `ed0bd23fa` (22 polls, all pending, no checks). By design nothing moves the head on this path: the `no_checks_stall` branch skips the terminal snapshot (issue #5186) and `_post_ensure_flush_and_push` never re-flushes (issue #5217). The loop is doomed; the `transient-infra` cap allows 4 such walks.
- 19:40Z: recovery happened only when HEAD moved: a rebase onto `origin/main` (clean) plus push attached CI run 28616948785 on `56904c311`.
- 19:42Z: that CI run failed with `python/skill-closure-baseline.json is stale; run make regen-skill-closure-baseline` — the cross-PR semantic merge conflict with the five sibling PRs merged into `main` mid-run. The earlier 19:23Z ci-fix had regenerated the baseline without rebasing, so the `pull_request` merge-ref CI stayed red.

Historical corroboration: committed transcript of run 9563A912 (turn 67) shows the orchestrator receiving a conflict stall, checking the state file, concluding "Not a `ship_pr_pre_push` path (RESUME_PHASE/CALLER_KIND are empty)", and proceeding to stall teardown plus improvised manual recovery.

## Root cause analysis

Three composable gaps. A and B are observations from code and live state; C is an inference from the live CI evidence.

**A. `no-ci-checks-observed` recovery re-monitors an unchanged head.** The bail path in `run_ship` deliberately keeps HEAD stable (correct per #5186), and the sanctioned recovery (Step 18a `transient-infra` → `step8-shippr` reship) re-enters the monitor on the same head. Neither the bail nor the reship probes why checks are absent. Two non-transient causes make re-monitoring unwinnable: GitHub skipped or lost the workflow run for that head, and a merge-CONFLICTING (`mergeStateStatus=DIRTY`) PR for which GitHub cannot build `refs/pull/N/merge`, so zero checks ever attach. The machinery already has the recovery primitive (the `ship-pr-rrr-after-phase14.flag` rebase used by `_ship_phase14_rebase`), but nothing on this path invokes it.

**B. Conflict handoff exists for exactly one flavor and is not first-class.** `PrePushConflictHandoff` (raised by `_resolve_conflicts` when the fixer waterfall exhausts, with `enable_pre_push_handoff=True`) persists `RESUME_PHASE=ship-pr-rrr-phase14`, `CALLER_KIND=ship_pr_pre_push`, `CONFLICT_FILES`, exits 4, and the SKILL stall arm routes to `conflict-resolution.md` Phase 1-4 and reship. But `ship route-exit` classifies exit 4 as bare `NEXT_ACTION=stall` and does not surface `RESUME_PHASE`/`CALLER_KIND`/`CONFLICT_FILES` into `.ship-route-exit-handoff.env`; the conflict branch depends on the orchestrator remembering to read `ship-pr-state.sh`. All other conflict flavors have no handoff at all:

- Pre-PR `postbump` conflicts: `_rebase_no_push` auto-resolves only `REBASE_AUTORESOLVE_GENERATED_FILES` (currently just `python/skill-closure-baseline.json`), aborts the rebase otherwise, and returns terminal `rebase-failed`. No waterfall, no handoff, documented as manual operator work.
- `_resolve_conflicts` bare-`Stalled` flavors (forbidden-path revert, `rebase --continue` failure without unmerged paths, `rebase --skip` failure) write terminal stall state with no conflict routing.
- `merge.py _maybe_review_required` converts `ADMIN_FAILED`-with-conflict-signal to `MAIN_ADVANCED` (rebase path) but not `POLICY_DENIED`-with-conflict-signal under `--no-admin-fallback`, which lands in the terminal merge stall.

**C. Cross-PR generated-file staleness is a merge conflict that only surfaces as merge-ref CI failure.** The `pull_request` event tests the merge of PR head with current `main`. A baseline regenerated on the branch without rebasing can stay stale forever while `main` advances. The ci-fix path has no rule that merge-ref-sensitive failures require rebase-onto-main before regeneration, so the loop converges only by luck or manual rebase.

## Evidence

- Journal `larch-journal-F7F30088-0014-47D6-A2F9-A899E1A79955.jsonl` in `$IMPLEMENT_TMPDIR`: 18:58:27Z `NEEDS_USER_INPUT` / `first-fixer-non-health` (ledger site `ship-pr`, step 8); 19:29:51Z `STALLED` / `no-ci-checks-observed`.
- `$IMPLEMENT_TMPDIR/.ship-route-exit-handoff.env`: `DETAIL=no-ci-checks-observed`, `NEXT_ACTION=stall`, no conflict or resume KVs.
- `$IMPLEMENT_TMPDIR/ship-pr-state.sh`: `RESUME_PHASE=` and `CALLER_KIND=` empty, `STALL_TRACKING=true`, `STALL_STEP=no-ci-checks-observed`, `LAST_MONITORED_HEAD=4fac4b38a...`.
- `$IMPLEMENT_TMPDIR/stall-recovery-classification.env`: `FAILURE_CLASS=transient-infra`, `RESUME_HINT=step8-shippr`, `MATCHED_CLASSIFIER_PATTERN=transient-output`, created 2026-07-02T19:31:14Z.
- `larch-quiet-ship.py-13048.log`: 22 polls then `CI NO_CHECKS after 307s -> bail (no-ci-checks-observed)`; `larch-quiet-ship.py-35136.log`: the recovery reship polling the same head, 22 pending polls, no bail line (interrupted).
- `gh run list` for the branch: runs exist only for heads `4fac4b38a` (18:57:01Z), `7486ac510` (18:58:31Z), `56904c311` (19:42:10Z). No run for pushed head `ed0bd23fa`.
- Run 28616948785 failure: `FAILED tests/lint/test_lint_skill_closure_growth.py::test_committed_baseline_matches_fresh_scan - AssertionError: python/skill-closure-baseline.json is stale`.
- git reflog (larch1): ci-fix commit `53a4a41a9` at 19:23:27Z, flush `ed0bd23fa` at 19:23:39Z, clean rebase onto `origin/main` finishing 19:41:19Z.
- No `.conflict-launch/` directory and no `ship-pr-rrr-after-phase14.flag` in `$IMPLEMENT_TMPDIR`: the fixer waterfall and phase14 handoff never ran in this run.
- Committed transcript `larch-logs/implement/9563A912-2BA4-45D4-B895-31F975E04A55/session-transcript.jsonl` turn 66-67: exit 4 conflict stall, orchestrator finds empty `RESUME_PHASE`/`CALLER_KIND`, proceeds to stall teardown.
- Code sites: `run_ship` `no_checks_stall` branch and the `PrePushConflictHandoff` carve-out in the exception handler (`python/larch/implement/ship.py`); `_classify_ship_route_exit` and `_write_ship_route_handoff` (`python/larch/implement/dispatch_ship.py`); `_handoff_or_stall` and the bare-`Stalled` flavors in `_resolve_conflicts` (`python/larch/git/rebase.py`); `_rebase_no_push` / `_autoresolve_generated_conflicts` (`python/larch/state/finalize.py`); `_maybe_review_required` (`python/larch/git/merge.py`); SKILL Step 8+ post-driver `stall` bullet and the Step 8b force-push-gate paragraph (`skills/implement/SKILL.md`); `ship-pr-exit-matrix.md` branch semantics; retry caps table (`python/stall-recovery-report.md`, `transient-infra` = 4 attempts).

## Affected files

- `python/larch/implement/ship.py`: `no_checks_stall` bail returns bare `STALLED` with no diagnosis; exception handler distinguishes `PrePushConflictHandoff` only by skipping the terminal write.
- `python/larch/implement/dispatch_ship.py`: `ship route-exit` maps exit 4 to generic `stall` and omits `RESUME_PHASE`/`CALLER_KIND`/`CONFLICT_FILES` from the handoff env; no `conflict-fix` action exists.
- `python/larch/implement/ci_monitor.py`: `NO_CHECKS` bail never probes `mergeStateStatus`/`mergeable`, so a DIRTY PR (zero attachable checks) is indistinguishable from CI lag.
- `python/larch/git/rebase.py`: `_resolve_conflicts` bare-`Stalled` flavors lose conflict context; handoff fires only on waterfall exhaustion or first-fixer `other`.
- `python/larch/state/finalize.py`: `postbump` `_rebase_no_push` aborts on any conflict outside the one-entry generated-file allow-list and returns terminal `rebase-failed`.
- `python/larch/git/merge.py`: conflict-signal conversion to `MAIN_ADVANCED` covers `ADMIN_FAILED` but not `POLICY_DENIED`.
- `skills/implement/SKILL.md`: Step 8+ post-driver `stall` arm defaults everything but the phase14 pair to "Step 16 with `STALL_TRACKING`, then Step 18"; Step 8b paragraph mandates manual operator resolution.
- `skills/implement/references/ship-pr-exit-matrix.md`, `skills/implement/references/conflict-resolution.md`, `skills/implement/references/stall-recovery.md`: routing and recovery contracts that would carry the new token and diagnosis.
- `python/stall-recovery-report.md`: retry-caps table governing the doomed reship loop.

## Suggested fix(es)

1. **First-class deterministic conflict routing.** Teach `ship route-exit` to emit a dedicated token (for example `NEXT_ACTION=conflict-fix`) when persisted state carries the conflict handoff, and write `RESUME_PHASE`, `CALLER_KIND`, and `CONFLICT_FILES` into `.ship-route-exit-handoff.env`. The SKILL stall arm then branches on the token instead of prompt-side reads of `ship-pr-state.sh`. This mirrors the `ci-fix` contract and removes the historical-miss mode (run 9563A912).
2. **Diagnose before reshipping a `no-ci-checks-observed` stall.** At bail time or at `step8-shippr` reship entry, probe the PR: `mergeStateStatus=DIRTY` → write the phase14 flag so the next ship entry rebases (existing `_ship_phase14_rebase` machinery); behind `main` → same rebase route; otherwise re-trigger CI for the unchanged head (`gh run rerun` of the newest run, or an empty commit) instead of re-monitoring a head GitHub has declined to build. In the live run this converts two 5.5-minute doomed walks into one rebase.
3. **Extend the handoff to the uncovered conflict flavors.** Pre-PR `postbump` conflicts: instead of abort-plus-terminal-stall, persist `CONFLICT_FILES` and hand off to the main agent through the same conflict routing (either keep the rebase in progress like the `early_rebase` caller family, or make the handoff restartable after abort). Give the `_resolve_conflicts` bare-`Stalled` flavors conflict metadata so they route the same way. Convert `POLICY_DENIED`-with-conflict-signal to `MAIN_ADVANCED` for parity with `ADMIN_FAILED`.
4. **Merge-ref-sensitive ci-fix rule.** In `ship-pr-ci-fix.md` (and/or the driver's rebase decision), require rebase onto current `main` before regenerating merge-ref-sensitive artifacts such as `python/skill-closure-baseline.json`, so the fix converges while `main` advances.

## Open questions

- Should pre-PR `postbump` conflicts keep the rebase in progress for main-agent resolution (matching the `early_rebase` caller family), or abort and re-run the rebase under the handoff? Keeping it in progress preserves stage data; aborting is safer across turn breaks.
- Token naming and scope: one `conflict-fix` action for all flavors, or separate tokens for pre-PR versus post-PR conflicts (they re-enter ship differently)?
- Should `ci_monitor` probe `mergeStateStatus` during the empty-checks window and short-circuit to the rebase route on DIRTY, rather than waiting out the full startup deadline?
- Safest CI re-trigger for an unchanged head under concurrent clones: `gh run rerun`, empty commit, or `workflow_dispatch`? An empty commit moves HEAD (reliable) but adds noise; rerun depends on a prior run existing for that head (none existed here).
- Does the `transient-infra` classifier need a distinct class for `no-ci-checks-observed` so its retry policy can carry the diagnosis step instead of a plain reship?

## Test plan
(no test plan section in plan-file)
