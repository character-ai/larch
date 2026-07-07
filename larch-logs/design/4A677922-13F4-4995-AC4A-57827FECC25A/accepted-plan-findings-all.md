### FINDING_1: Pre-PR fix-first needs its own repair path
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Main Ci Guardian
- **Severity**: major
- **Concern**: Step 2 fix-first has no implementable pre-PR repair procedure; the documented ci-fix flow assumes PR/ship state that does not exist yet at feature admission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a thin pre-PR main-ci repair reference (or a `--site step2-main-ci` mode) covering run-log capture from `MAIN_FAILED_RUN_ID`, on-branch fix, relevant checks, commit, and continue to §2.1 dispatch without ship re-entry. Wire SKILL Step 0→2 boundary to that reference only.
  - From Cursor-Innovation: Add `skills/implement/references/early-main-ci-fix.md` (or equivalent) for pre-PR repair: persist `FAILED_RUN_ID`, capture `gh run-logs` for the default-branch push run, edit on the feature branch, run relevant checks, commit, then continue to `run-dispatch`. Wire it in `SKILL.md` before the Step 2 breadcrumb and `implement run-dispatch`.
  - From Cursor-Pragmatic: Add a named early-path reference (or shared helper) for Step 2 main-CI repair: write FAILED_RUN_ID handoff, capture default-branch run logs without PR context, fix/commit on the feature branch, rerun checks; do not call step-8-ship until feature work resumes
  - From Cursor-Requirements: Add a dedicated pre-implementation repair contract: NEW skills/implement/references/step2-main-health-fix.md (or equivalent) with log capture via gh run-logs, on-branch fix, checks, and commit; wire SKILL Step 2 before run-dispatch; persist preflight MAIN_CI_* into IMPLEMENT_TMPDIR for resume.
  - From Cursor-dyn-Main Ci Guardian: Add a firm ### NEW or ### UPDATED reference (e.g. step2-main-health-fix.md) or python/cli.py implement step2-main-health-fix: capture default-branch logs via MAIN_FAILED_RUN_ID, repair on the feature branch, commit/push, then continue Step 2 without step-8-ship


### FINDING_2: Preflight main-health must not depend on an explicit repo argument
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Main Ci Guardian
- **Severity**: major
- **Concern**: Default `/implement` preflight can skip main-health entirely when no repo is resolved, so red default-branch CI stays invisible at admission and Step 2’s response to pending/error is undefined.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Resolve repo in preflight when `--repo` is empty (`gh resolve-repo` or issue remote), pass `--base-ref main` (or `upstream/main` when forked), and always emit the additive main-health KVs. Update `skills/implement/SKILL.md` allowed envelope keys accordingly.
  - From Cursor-Innovation: Resolve repo inside preflight when `--repo` is empty (`python/cli.py gh resolve-repo`), then always run `ci main-health` against that repo and the default branch before emitting the success envelope.
  - From Cursor-Pragmatic: Resolve repo inside preflight when --repo is empty (gh.resolve_repo), then always run ci main-health; keep forked --repo override
  - From Cursor-Requirements: Resolve repo inside preflight when --repo is empty (for example gh resolve-repo from the consumer checkout), then always call ci main-health. Keep degraded error KVs without aborting admission.
  - From Cursor-dyn-Main Ci Guardian: Resolve repo for every run (e.g. gh resolve-repo or admission output), always invoke ci main-health when resolvable, and emit MAIN_CI_* on the success envelope
  - From Cursor-Arch: Define Step 2 behavior: bounded wait via ci main-health --wait, operator bail on error, or proceed-only-on-pass; mirror fork upstream/base-ref semantics


### FINDING_3: Preflight envelope parsing needs the new main-health keys
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Main Ci Guardian
- **Severity**: major
- **Concern**: The preflight success-envelope parser is missing the new main-health KVs, so even if preflight emits them the orchestrator can drop them before Step 0/Step 2 routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add the three keys to the allowed preflight envelope list in SKILL item 3 and mirror in `python/tests/implement/test_preflight.py` success-envelope expectations.
  - From Cursor-Innovation: Add `MAIN_CI_STATUS`, `MAIN_FAILED_RUN_ID`, and `MAIN_HEALTH_DETAIL` to the allowed preflight parse list; document fix-first branching immediately after `BOOTSTRAP_NEXT=step2`.
  - From Cursor-Pragmatic: Add the three keys to allowed preflight parse keys; bind them before Step 0/Step 2 routing; update the envelope-count prose (`DESIGN_DIFFICULTY` is already emitted)
  - From Cursor-Requirements: Update Preflight item 3 to parse the full SUCCESS_ENVELOPE_KEYS set additively (DESIGN_DIFFICULTY plus MAIN_CI_STATUS, MAIN_FAILED_RUN_ID, MAIN_HEALTH_DETAIL).
  - From Cursor-dyn-Main Ci Guardian: Add MAIN_CI_STATUS, MAIN_FAILED_RUN_ID, and MAIN_HEALTH_DETAIL to the allowed preflight envelope keys (update the seven-key wording) and bind them before Step 0/Step 2 routing


### FINDING_4: Post-merge main-health watch must be commit-scoped
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: Main-health selection is not commit-scoped, so both pre-merge and post-merge waits can accept a stale or unrelated default-branch run instead of the run for the current base/merge commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add optional `head_sha` (merge commit) to `read_main_health` / `wait_main_health`, filter `gh run list` rows to that SHA, and have `ship.py` pass the merged SHA into the post-merge watch before `_ship_postmerge_phase`.
  - From Codex-Arch: Make the post-merge watch tied to the merged commit. Scenario: The plan says to wait for the next default-branch push run, while main_health inputs omit a commit/head SHA requirement. A later unrelated push run can pass before polling and mask the merged PR's failed push run, so the #6488 class can still ship silently.
  - From Cursor-Innovation: Require merge-commit correlation: extend filtered run list with `head_sha` (or equivalent), and have post-merge `wait_main_health` match the merged SHA before pass/fail routing and emergency repair.
  - From Codex-Innovation: Pass the merged commit SHA into the post-merge wait. Filter by `--commit` or parse `headSha`, and poll until a run for that SHA reaches pass or fail. Add a ship test where an older main success exists before the merge-SHA run appears and fails.
  - From Cursor-Pragmatic: After merge, wait/filter for the push workflow run whose head_sha matches the merged commit (use planned WorkflowRun.head_sha / --commit filter); only pass watch on that run
  - From Codex-Pragmatic: Thread the merged commit SHA or a lower-bound run identity through main_health, the CLI, and ship.py. For post-merge watch, ignore older default-branch runs and wait for the push run for the merged commit, using the planned commit/head_sha gh fields. Add the stale previous-green case to test_ship.py or test_main_health.py.
  - From Cursor-Requirements: Make post-merge watch commit-bound: capture the merged commit SHA via PR merge metadata or refreshed `origin/main`, add/pass a `--commit` or `head_sha` filter through `ci main-health` and `read_main_health`, treat no run for that SHA as pending until timeout, and never accept a pass from an unrelated default-branch run.
  - From Codex-Requirements: Make headSha or commit filtering mandatory at call sites. Compare runs to fetched origin/main for pre-merge and to the merged commit for post-merge. Treat no matching run as pending until timeout, then stall or error.


### FINDING_5: Flaky-defect handling still exits as success downstream
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: A named repository failure that later turns green can still be treated as success downstream, including after rebases, because the flaky-defect-unfixed status is not wired through the monitor/agentic-fix handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend `_agentic_fix_result` (and any caller that treats `passed` as terminal) to map `flaky-defect-unfixed` to a CI-fix handoff / `NEEDS_USER_INPUT`, not `FixResult(status="pushed")`. Add the case to `test_ci_agentic_fix.py` and `test_ci_monitor.py`.
  - From Codex-Innovation: Track a non-rebase repair delta after the failed repository test or lint log. Do not clear the flaky-defect obligation for base-only rebases, reruns, shard movement, or other head changes that do not contain an authored fix commit or changed repair paths.
  - From Cursor-Pragmatic: Map flaky-defect-unfixed to a NEEDS_USER_INPUT/ci-fix handoff in ci_monitor (and agentic-fix result parsing), parallel to first-fixer-non-health, instead of returning passed
  - From Cursor-Requirements: Extend ci_monitor to treat flaky-defect-unfixed as a non-success handoff (ci-fix or NEEDS_USER_INPUT with the new reason), and add the matching test in test_ci_monitor.py.


### FINDING_6: Main-health evidence needs durable materialization for resume
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Preflight main-health evidence is not durably materialized into the implement session, so resume and multi-turn Step 2 orchestration can lose the recorded failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend bootstrap Step 0 materialization to write a durable sidecar (for example `main-health.env`) or session keys from preflight output; have Step 2 and ship routing read that file instead of chat-only KVs.
  - From Cursor-Pragmatic: Have preflight write $PREFLIGHT_TMPDIR/main-health.env (or equivalent) and bootstrap copy it to $IMPLEMENT_TMPDIR/main-health.env during Step 0 materialization


### FINDING_7: Post-merge emergency repair needs an explicit state machine
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Main Ci Guardian, Codex-dyn-Main Ci Guardian
- **Severity**: major
- **Concern**: Post-merge emergency repair needs an explicit state machine and repaired-run tracking; otherwise the merged run can finalize, loop on the same failed run, or leave the repair PR/state ambiguous.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Define one owner state machine: delay `post-merge-sentinel` until push watch passes or repair completes; define terminal outcome (`merged` vs `stalled` vs `repair-shipped`); list any updates to `ship_resume.py`, `finalize.py`, and stall recovery for mid-repair resume.
  - From Cursor-Pragmatic: Spell out the emergency-repair state machine: defer post-merge-sentinel until repair ownership; block run-log commit on main; define whether the session stalls, spawns a child ship on the repair branch, or operator-bails; add matching ship.py tests
  - From Cursor-Requirements: Define a separate post-merge repair flow (NEW reference + ship.py driver branch + route-exit action): checkout repair branch from origin/main, fix from redacted push-run logs, open/ship repair PR, defer post-merge-sentinel until repair owns lifecycle; do not reuse ship-pr-ci-fix verbatim.
  - From Codex-Requirements: Specify phases (e.g. postmerge-push-watch, emergency-repair), defer post-merge-sentinel and _ship_postmerge_phase until push CI passes or repair completes, keep MERGE_RESULT from marking done until repair ships, and document repair PR vs original PR_NUMBER handling
  - From Cursor-dyn-Main Ci Guardian: Add an exact repair state such as MAIN_REPAIR_RUN_ID and MAIN_REPAIR_HEAD. Allow merge only when the current red main run matches that repaired run, the branch has the repair commit, and PR CI is green. Clear the state when main reports a different failed run.


### FINDING_8: New route reasons must be wired through all ship routing surfaces
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Main Ci Guardian
- **Severity**: major
- **Concern**: New main-health-related route reasons need to be recognized consistently across config, ship_result validation, dispatch, and the exit-matrix prose, or route-exit validation can misclassify them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Mirror new reason tokens in `config.py` and autonomous CI-fix routing so `route-exit` JSON validation and `NEXT_ACTION=ci-fix` do not fall through to `operator-bail`.
  - From Cursor-Pragmatic: Add ### UPDATED: skills/implement/references/ship-pr-exit-matrix.md mapping the new needs_user_reason tokens to ci-fix, default-branch FAILED_RUN_ID semantics, and post-merge emergency repair continuation
  - From Cursor-Requirements: Add ship_result.py (and config.NEEDS_USER_REASON_TOKENS) updates for main-ci-fail, postmerge-main-ci-fail, and flaky-defect-unfixed so handoffs classify to ci-fix
  - From Codex-Requirements: Add ### UPDATED: skills/implement/references/ship-pr-exit-matrix.md documenting main-ci-fail and postmerge-main-ci-fail routing, handoff fields, and orchestrator steps (including whether post-merge uses ci-fix or a dedicated action).
  - From Cursor-dyn-Main Ci Guardian: Add ### UPDATED: skills/implement/references/ship-pr-exit-matrix.md listing main-ci-fail and postmerge-main-ci-fail under ci-fix with default-branch FAILED_RUN_ID semantics


### FINDING_9: Post-merge repair must be isolated from the original feature branch
- **Reviewer(s)**: Cursor-dyn-Main Ci Guardian, Codex-dyn-Main Ci Guardian
- **Severity**: major
- **Concern**: The post-merge repair branch must be isolated from the original feature branch, with a dedicated context and commit guard so emergency fixes cannot mutate or push the merged PR branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Main Ci Guardian: Add ship-state fields (e.g. EMERGENCY_REPAIR_BRANCH, ORIGINAL_BRANCH_FORBIDDEN) and a firm ship.py/git-commit guard: after merge, allow code commits only on the repair branch; never on the original feature branch; still forbid larch-log commits via existing MERGE_RESULT/post-merge rules
  - From Codex-dyn-Main Ci Guardian: Add a dedicated emergency repair state or action. It should write the post-merge sentinel before any repair edit, set NO_LOGS_COMMIT or skip run-log refresh for the repair, checkout/create a separate repair branch, and pass that branch through a separate context so the original PR branch is never pushed or force-rebased.


### FINDING_1: Bootstrap target points at the wrong module
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: The plan points at `python/bootstrap.py`, but the real Step 0 bootstrap path is `python/larch/state/bootstrap.py`, so the durable handoff that should copy and preserve `main-health.env` can be missed entirely or implemented in the wrong place.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: "Point `### UPDATED:` at `python/larch/state/bootstrap.py`, add a matching `python/tests/state/test_bootstrap.py` bullet for the copy/preserve behavior, and keep the SKILL shorthand `python/bootstrap.py` as prose-only if desired."
  - From Codex-Arch: "Change the firm target to `python/larch/state/bootstrap.py` and copy main-health.env during existing preflight materialization, preserving an existing implement sidecar on resume."
  - From Codex-Innovation: "Replace the plan target with `python/larch/state/bootstrap.py` and wire the copy there, with resume preserving an existing `$IMPLEMENT_TMPDIR/main-health.env` unless preflight explicitly refreshes it."
  - From Cursor-Pragmatic: "Retarget the plan to `python/larch/state/bootstrap.py` (and `python/tests/state/test_bootstrap.py` if copy behavior is asserted)."
  - From Codex-Pragmatic: "Change the firm target to `python/larch/state/bootstrap.py` and add the Step 0 copy and resume-preserve logic there."
  - From Cursor-Requirements: "Retarget the bootstrap bullet to `python/larch/state/bootstrap.py` and add a copy step beside existing preflight artifact materialization (plan copy, tally copy). Optionally add `python/test_bootstrap.py` coverage for the handoff."
  - From Codex-Requirements: "Replace the firm file entry with `python/larch/state/bootstrap.py` and copy `$PREFLIGHT_TMPDIR/main-health.env` beside `preflight-tmpdir.env`, preserving an existing implement-side file on resume unless a refreshed preflight explicitly rewrites it."


### FINDING_2: Preflight main-health envelope drops required fields
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Preflight can emit an incomplete main-health envelope: on repo-resolution failure it omits the `MAIN_*` keys entirely, and it also leaves out `MAIN_HEALTH_HEAD_SHA`, so Step 2 admission or repair logic may fail or lose the evidence it expects.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: "On resolve failure or skipped probe, still emit the three MAIN_* keys with `MAIN_CI_STATUS=error` and bounded `MAIN_HEALTH_DETAIL`; write the same KVs to `main-health.env`; do not abort admission solely for degraded reads."
  - From Cursor-Pragmatic: "Include `MAIN_HEALTH_HEAD_SHA` in preflight envelope keys, `main-health.env`, and orchestrator parsing."


### FINDING_3: Base-ref main-health gate deadlocks branch repairs
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: The repair path deadlocks because it still requires default-branch `ci main-health` to report `pass` before dispatch or merge, but the repair lives on the PR branch and cannot make `main` green until it merges. For push-red/PR-green failures, the run can stall forever or loop back to ci-fix instead of shipping the repair it already made.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: "Record the failed main run as addressed by the repair commit. Allow merge only for that tracked red-main run when branch guards and PR CI pass, then require the commit-scoped post-merge watch to prove the repaired main SHA passes."
  - From Cursor-Innovation: "Continue after relevant checks plus a recorded repair commit (for example `MAIN_HEALTH_REPAIR_HEAD` in `main-health.env`); refresh main-health for logging only; do not gate dispatch on base-ref pass."
  - From Cursor-Innovation: "Allow merge when PR checks pass and durable state shows an in-branch main-health repair for the recorded failure (repair commit/sentinel); otherwise block and hand off to ci-fix. Do not require base-ref pass when the current branch already carries the repair."
  - From Codex-Innovation: "After the repair commit, validate the current branch with relevant checks and PR CI, record a durable repaired-main failure marker keyed by failed run ID or head SHA, and let the merge gate ship that explicit repair. Rely on the commit-scoped post-merge watch to prove main is green."
  - From Cursor-Pragmatic: "Exit after repair commit plus `checks run-relevant` pass; refresh `main-health.env` for evidence only; record `MAIN_CI_REPAIR_DONE=true` (or equivalent) and proceed while `MAIN_CI_STATUS` may still be `fail` until merge."
  - From Cursor-Pragmatic: "Split gates: pre-merge `fail` routes to ci-fix once per failed run fingerprint; allow merge when repair is committed on the PR branch and PR checks pass, without requiring default-branch green pre-merge. Post-merge commit-scoped watch stays strict."
  - From Codex-Pragmatic: "Track a covered main failure run or SHA plus the repair commit. After pre-PR or emergency repair, allow merge over only that same failed main SHA when the branch contains the repair and PR checks pass. Keep blocking new or different default-branch failures."
  - From Cursor-Requirements: "Exit pre-PR repair on a committed repair plus relevant checks (record e.g. `MAIN_HEALTH_REPAIR_COMMITTED=true` / failed-run ID in `main-health.env`). Re-run `ci main-health` for telemetry only; do not require `MAIN_CI_STATUS=pass` before dispatch."
  - From Cursor-Requirements: "At the merge gate, allow merge when durable state shows a main-health repair commit for the recorded `MAIN_FAILED_RUN_ID`, or when PR checks pass for the current head and the failure is push-only; otherwise route to ci-fix. Document the rule in `ship-pr-exit-matrix.md`."
  - From Codex-Requirements: "Record the repaired failed run and base SHA as owned by the branch, run branch or PR verification, and let the merge gate proceed only for that recorded main failure when the repair commit is present and the base SHA has not changed. Re-run main-health normally for any new or different failure."


### FINDING_4: Emergency repair fields are missing from ship state
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: major
- **Concern**: The emergency-repair branch and run-tracking fields are not part of the ship-state contract, so patch/write/resume paths can reject them or drop them, which breaks branch isolation and can lose repair context mid-repair.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: "Add python/larch/implement/ship_state.py to firm changes. Define and validate the new fields, include them in write/patch/read paths, and hydrate them in resume handling."
  - From Codex-Requirements: "Add `python/larch/implement/ship_state.py` to firm changes and allow, initialize, validate, and preserve the new repair-state fields used by `ship.py`, `ship_resume.py`, and `dispatch_ship.py`."


### FINDING_5: Post-merge repair flow still reuses ci-fix
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: The post-merge failure path still routes into the normal ci-fix machinery and lacks a dedicated emergency-repair lifecycle, so the repair PR/branch, merge watch, and finalization steps can stay ambiguous or get stuck in the wrong workflow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: "Give `postmerge-main-ci-fail` its own `route-exit` action (for example `postmerge-repair`) and SKILL branch that loads only `postmerge-emergency-repair.md`; keep `main-ci-fail` and `flaky-defect-unfixed` on `ci-fix`."
  - From Cursor-Requirements: "Spell out repair-PR open/ship/merge (reuse ship driver on `EMERGENCY_REPAIR_BRANCH` or explicit operator gate), commit-scoped push watch for the repair merge SHA, transition to `repair-shipped`, and defer original-run terminal finalize until that watch passes."


### FINDING_6: Same-SHA flaps are misclassified as pass
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: Main-health currently treats the latest success as clean even when the same commit had a prior push failure and then passed without a new commit, so flapping default-branch CI can be mistaken for a healthy main.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: "When classifying a branch head or requested SHA, inspect recent push runs for the same `headSha`. If any named repository failure for that SHA later passed without a new commit, return a repair-needed status with the failed run ID instead of `pass`; reserve `pass` for no same-SHA repository failure evidence."


### FINDING_7: Forked main-health uses the wrong GitHub branch filter
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: minor
- **Concern**: Forked runs can query the upstream repo with a remote-qualified branch name, but GitHub branch filters expect the bare branch name inside that repo, so `gh run list` can return no rows or error even when upstream `main` is healthy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: "Keep repo selection and git remote refs separate. For forked runs, query `--repo $UPSTREAM_REPO --branch main`; use `upstream/main` only for local git comparisons."
  - From Codex-Requirements: "Normalize the GitHub run-list branch to `main` while using `--repo \"$UPSTREAM_REPO\"`; keep `upstream/main` only for local git and rebase comparisons, and add a forked argv case for `ci main-health`."


