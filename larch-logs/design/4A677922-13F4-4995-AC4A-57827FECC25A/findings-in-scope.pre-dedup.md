### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/bootstrap.py
- **Concern**: Bootstrap materialization targets a non-existent path. Scenario: The plan lists `### UPDATED: python/bootstrap.py`, but the only bootstrap module is `python/larch/state/bootstrap.py` (wired from `python/larch/cli.py` `bootstrap invoke`). An implementer following the plan path will miss the `main-health.env` copy hook.
- **Proposed resolution**: Point `### UPDATED:` at `python/larch/state/bootstrap.py`, add a matching `python/tests/state/test_bootstrap.py` bullet for the copy/preserve behavior, and keep the SKILL shorthand `python/bootstrap.py` as prose-only if desired.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/preflight.py
- **Concern**: Preflight omits MAIN_* keys when repo resolution fails. Scenario: The plan adds `MAIN_CI_STATUS`, `MAIN_FAILED_RUN_ID`, and `MAIN_HEALTH_DETAIL` to strict `SUCCESS_ENVELOPE_KEYS`, but only runs `ci main-health` "when repo resolution succeeds." If `gh resolve-repo` fails, omitted keys make `_validate_success_envelope` exit 2 and block every `/implement` run.
- **Proposed resolution**: On resolve failure or skipped probe, still emit the three MAIN_* keys with `MAIN_CI_STATUS=error` and bounded `MAIN_HEALTH_DETAIL`; write the same KVs to `main-health.env`; do not abort admission solely for degraded reads.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/shared/voting-protocol.md
- **Concern**: [SCOPE-REDUCTION] Conditional shared-prompt files remain firm UPDATED. Scenario: `skills/shared/voting-protocol.md` and `skills/shared/oos-acceptance-rubric.md` are `### UPDATED:` while their bullets say "only if" wording conflicts. That turns optional prompt churn into mandatory diff surface.
- **Proposed resolution**: Move both to `### MAY_UPDATE:` or drop them from the firm file list; keep the required gate-5 edits in `skills/shared/review-acceptance-rubric.md` and `skills/shared/reviewer-templates.md` plus `make test-prompt-template-invariants`.



### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/references/step2-main-health-fix.md
- **Concern**: Pre-PR and emergency main repair can deadlock waiting for main to pass before the repair merges. Scenario: When main is red, the repair commit lives only on the feature or emergency branch. The planned rule to continue only after default-branch main-health is pass, plus the universal pre-merge red-main gate, can prevent the repair PR itself from ever merging.
- **Proposed resolution**: Record the failed main run as addressed by the repair commit. Allow merge only for that tracked red-main run when branch guards and PR CI pass, then require the commit-scoped post-merge watch to prove the repaired main SHA passes.



### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/implement/ship_state.py:25-70
- **Concern**: Emergency repair fields have no ship-state contract. Scenario: The plan tracks EMERGENCY_REPAIR_BRANCH, ORIGINAL_BRANCH_FORBIDDEN, MAIN_REPAIR_RUN_ID, and MAIN_REPAIR_HEAD, but current ship-state allowlists reject or drop unknown keys. Resume or route-exit can lose the repair branch guard or fail mid-repair.
- **Proposed resolution**: Add python/larch/implement/ship_state.py to firm changes. Define and validate the new fields, include them in write/patch/read paths, and hydrate them in resume handling.



### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/bootstrap.py:453-454,840-848
- **Concern**: Main-health sidecar materialization targets the wrong bootstrap module. Scenario: The plan names python/bootstrap.py, but bootstrap is routed through larch.state.bootstrap. If the real Step 0 materializer is not updated, $PREFLIGHT_TMPDIR/main-health.env never reaches $IMPLEMENT_TMPDIR/main-health.env, so Step 2 or resume can skip fix-first.
- **Proposed resolution**: Change the firm target to python/larch/state/bootstrap.py and copy main-health.env during existing preflight materialization, preserving an existing implement sidecar on resume.



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/references/step2-main-health-fix.md
- **Concern**: Pre-PR repair exit requires default-branch main-health pass after a feature-branch fix. Scenario: Approach §3 says Step 2 repair commits on the feature branch and continues to run-dispatch, but step2-main-health-fix.md requires `ci main-health` pass on the base ref before dispatch. A branch-only fix cannot turn `main` push CI green until merge, so sessions that already repaired can stall forever at Step 2.
- **Proposed resolution**: Continue after relevant checks plus a recorded repair commit (for example `MAIN_HEALTH_REPAIR_HEAD` in `main-health.env`); refresh main-health for logging only; do not gate dispatch on base-ref pass.



### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py
- **Concern**: Planned pre-merge main-health gate has no repair attestation exception. Scenario: The merge loop will call main-health on `origin/main` before `merge`. For the #6488 class the PR is green while `main` push CI stays red until the fix lands; a branch that already contains the repair still reads `fail` and routes to `main-ci-fail`/ci-fix in a loop, or never merges the fix.
- **Proposed resolution**: Allow merge when PR checks pass and durable state shows an in-branch main-health repair for the recorded failure (repair commit/sentinel); otherwise block and hand off to ci-fix. Do not require base-ref pass when the current branch already carries the repair.



### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md;python/larch/implement/dispatch_ship.py
- **Concern**: `postmerge-main-ci-fail` is wired to `NEXT_ACTION=ci-fix` while Approach §7 forbids reusing ship ci-fix. Scenario: Approach §7 and `postmerge-emergency-repair.md` require a dedicated post-merge driver (repair branch, no larch-log commits, separate repair PR). SKILL.md and item 8 still route `postmerge-main-ci-fail` to `NEXT_ACTION=ci-fix`, which loads `ship-pr-ci-fix.md` and `step-8-ship.sh` semantics that forbid the repair-branch lifecycle.
- **Proposed resolution**: Give `postmerge-main-ci-fail` its own `route-exit` action (for example `postmerge-repair`) and SKILL branch that loads only `postmerge-emergency-repair.md`; keep `main-ci-fail` and `flaky-defect-unfixed` on `ci-fix`.



### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/shared/voting-protocol.md;skills/shared/oos-acceptance-rubric.md
- **Concern**: [SCOPE-REDUCTION] Conditional shared-rubric files remain firm `### UPDATED:` entries. Scenario: Both files say update only when wording conflicts, but `### UPDATED:` still makes them mandatory diff targets and triggers the six-agent regen sweep even when gate-5 text is unchanged.
- **Proposed resolution**: Reclassify `skills/shared/voting-protocol.md` and `skills/shared/oos-acceptance-rubric.md` as `### MAY_UPDATE:`; run agent regen only when those files actually change.



### FINDING_11:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/references/step2-main-health-fix.md
- **Concern**: Pre-PR main repair waits for main to pass before the repair can merge. Scenario: A red default branch stays red until the feature branch carrying the repair is merged, so `ci main-health` on the base ref never reports pass. Step 2 can deadlock, and the Step 8 red-main gate can route the already-repaired failure back to CI-fix instead of shipping the repair.
- **Proposed resolution**: After the repair commit, validate the current branch with relevant checks and PR CI, record a durable repaired-main failure marker keyed by failed run ID or head SHA, and let the merge gate ship that explicit repair. Rely on the commit-scoped post-merge watch to prove main is green.



### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/state/bootstrap.py:1
- **Concern**: Main-health materialization targets a non-existent bootstrap file. Scenario: The plan lists `python/bootstrap.py`, but the Step 0 implementation lives in `python/larch/state/bootstrap.py`. If the implementer follows the listed file, `$PREFLIGHT_TMPDIR/main-health.env` is not copied into `$IMPLEMENT_TMPDIR`, so Step 2 and resume lose the red-main evidence.
- **Proposed resolution**: Replace the plan target with `python/larch/state/bootstrap.py` and wire the copy there, with resume preserving an existing `$IMPLEMENT_TMPDIR/main-health.env` unless preflight explicitly refreshes it.



### FINDING_13:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/main_health.py
- **Concern**: Main-health latest-success classification misses default-branch flakes. Scenario: A default-branch commit can have a failed push run followed by a successful rerun with no code change. The planned helper classifies the latest matching success as `pass`, so `/implement` can merge on flapping main even though the feature scope says red or flapping default-branch CI blocks verification.
- **Proposed resolution**: When classifying a branch head or requested SHA, inspect recent push runs for the same `headSha`. If any named repository failure for that SHA later passed without a new commit, return a repair-needed status with the failed run ID instead of `pass`; reserve `pass` for no same-SHA repository failure evidence.



### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/references/step2-main-health-fix.md
- **Concern**: Pre-PR repair exit wrongly requires default-branch CI pass. Scenario: The reference says continue to `implement run-dispatch` only when `ci main-health` reports `pass` for the base ref. A repair on the feature branch cannot turn `main` green until merge, so a red-main admission deadlocks Step 2 after a repair commit.
- **Proposed resolution**: Exit after repair commit plus `checks run-relevant` pass; refresh `main-health.env` for evidence only; record `MAIN_CI_REPAIR_DONE=true` (or equivalent) and proceed while `MAIN_CI_STATUS` may still be `fail` until merge.



### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py
- **Concern**: Merge gate cannot require literal main pass before squash merge. Scenario: The plan gates merge on `MAIN_CI_STATUS=pass` and tests "pass still merges only when main health is pass." While `origin/main` HEAD still has a failed push run, an in-PR repair leaves main red until merge, so ci-fix → re-merge loops forever (#6488 class).
- **Proposed resolution**: Split gates: pre-merge `fail` routes to ci-fix once per failed run fingerprint; allow merge when repair is committed on the PR branch and PR checks pass, without requiring default-branch green pre-merge. Post-merge commit-scoped watch stays strict.



### FINDING_16:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/bootstrap.py
- **Concern**: Bootstrap materialization targets the wrong file path. Scenario: The plan lists `### UPDATED: python/bootstrap.py`, but Step 0 materialization lives in `python/larch/state/bootstrap.py` (`cli.py bootstrap invoke`). The copy of `$PREFLIGHT_TMPDIR/main-health.env` may be skipped.
- **Proposed resolution**: Retarget the plan to `python/larch/state/bootstrap.py` (and `python/tests/state/test_bootstrap.py` if copy behavior is asserted).



### FINDING_17:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/implement/references/step2-main-health-fix.md
- **Concern**: `MAIN_HEALTH_HEAD_SHA` omitted from durable preflight sidecar. Scenario: Preflight writes envelope/sidecar KVs `MAIN_CI_STATUS`, `MAIN_FAILED_RUN_ID`, `MAIN_HEALTH_DETAIL` only, but Step 2 repair reads `MAIN_HEALTH_HEAD_SHA` from `$IMPLEMENT_TMPDIR/main-health.env`.
- **Proposed resolution**: Include `MAIN_HEALTH_HEAD_SHA` in preflight envelope keys, `main-health.env`, and orchestrator parsing.



### FINDING_18:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/shared/voting-protocol.md
- **Concern**: [SCOPE-REDUCTION] Conditional reviewer prompt files listed as firm `### UPDATED:`. Scenario: Bullets say update `voting-protocol.md` and `oos-acceptance-rubric.md` only when wording conflicts, but firm `### UPDATED:` makes optional prompt churn mandatory (~6 agent regens).
- **Proposed resolution**: Reclassify those two paths as `### MAY_UPDATE:`; keep `review-acceptance-rubric.md` and generated agent regen as the firm doctrine surface.



### FINDING_19:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/references/step2-main-health-fix.md; python/larch/implement/ship.py
- **Concern**: Pre-PR repair still requires red main to turn green before the repair can merge. Scenario: Main is red from run R. Step 2 commits the fix on the feature branch, but `ci main-health` against the base ref still reports fail for R until that branch merges. The plan can bail at the pre-PR repair check or loop at the pre-merge red-main gate instead of shipping the repair it just made.
- **Proposed resolution**: Track a covered main failure run or SHA plus the repair commit. After pre-PR or emergency repair, allow merge over only that same failed main SHA when the branch contains the repair and PR checks pass. Keep blocking new or different default-branch failures.



### FINDING_20:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/bootstrap.py:153; python/larch/state/bootstrap.py
- **Concern**: Durable main-health materialization targets the wrong bootstrap file. Scenario: The repo has `python/larch/state/bootstrap.py`, not `python/bootstrap.py`. If the plan is followed as written, Step 0 will not copy `$PREFLIGHT_TMPDIR/main-health.env` into `$IMPLEMENT_TMPDIR`, so resume or a later turn can lose `MAIN_CI_STATUS=fail` and enter Step 2 without the required repair.
- **Proposed resolution**: Change the firm target to `python/larch/state/bootstrap.py` and add the Step 0 copy and resume-preserve logic there.



### FINDING_21:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/implement/preflight.py; python/larch/implement/main_health.py
- **Concern**: Forked main-health uses a remote-qualified name as a GitHub branch filter. Scenario: In forked mode the plan calls main-health with `--repo` set to the upstream repo but `--branch upstream/main`. GitHub Actions branch filters use `main`, so `gh run list --branch upstream/main` can return no rows and force an error or pending bail before Step 2.
- **Proposed resolution**: Keep repo selection and git remote refs separate. For forked runs, query `--repo $UPSTREAM_REPO --branch main`; use `upstream/main` only for local git comparisons.



### FINDING_22:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/bootstrap.py
- **Concern**: Pre-PR main-health materialization targets a non-existent bootstrap module. Scenario: The plan lists `### UPDATED: python/bootstrap.py` for copying `$PREFLIGHT_TMPDIR/main-health.env` into `$IMPLEMENT_TMPDIR`, but the Step 0 implementation lives at `python/larch/state/bootstrap.py` (invoked via `python/cli.py bootstrap invoke`). Round-1 durable-handoff acceptance is not implementable at the cited path.
- **Proposed resolution**: Retarget the bootstrap bullet to `python/larch/state/bootstrap.py` and add a copy step beside existing preflight artifact materialization (plan copy, tally copy). Optionally add `python/test_bootstrap.py` coverage for the handoff.



### FINDING_23:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/references/step2-main-health-fix.md
- **Concern**: Pre-PR repair exit still requires default-branch `pass` (FINDING_1 incomplete). Scenario: The reference says continue to `implement run-dispatch` only when `ci main-health` reports `pass` on the base ref. Issue scope and Approach fix-first both repair on the feature branch and merge the fix with the feature PR. For push-red/PR-green failures (#6488 class), default-branch push CI stays red until that merge lands, so Step 2 would stall forever after a correct repair.
- **Proposed resolution**: Exit pre-PR repair on a committed repair plus relevant checks (record e.g. `MAIN_HEALTH_REPAIR_COMMITTED=true` / failed-run ID in `main-health.env`). Re-run `ci main-health` for telemetry only; do not require `MAIN_CI_STATUS=pass` before dispatch.



### FINDING_24:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py
- **Concern**: Pre-merge main-health `fail` has no repair-on-branch carve-out. Scenario: Approach §3 routes every pre-merge `fail` to `main-ci-fail` / ci-fix. When the feature branch already contains the in-run main-health repair, default-branch push CI can remain red while PR checks are green; blocking merge retries ci-fix indefinitely and prevents the repair from landing (the #6488 failure mode the issue targets).
- **Proposed resolution**: At the merge gate, allow merge when durable state shows a main-health repair commit for the recorded `MAIN_FAILED_RUN_ID`, or when PR checks pass for the current head and the failure is push-only; otherwise route to ci-fix. Document the rule in `ship-pr-exit-matrix.md`.



### FINDING_25:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/implement/references/postmerge-emergency-repair.md
- **Concern**: Post-merge emergency repair lacks a terminal completion contract (FINDING_7 incomplete). Scenario: The reference defines phases through `repair-shipped` / `stalled` and forbids larch-log commits after original merge, but does not specify how the repair PR is merged, how push CI for the repair merge is watched, or how `MERGE_RESULT` / manifest `done` / `post-merge-sentinel` are written only after repair succeeds. Implementers can finalize the original run, loop on the same failed push run, or leave repair PR state ambiguous.
- **Proposed resolution**: Spell out repair-PR open/ship/merge (reuse ship driver on `EMERGENCY_REPAIR_BRANCH` or explicit operator gate), commit-scoped push watch for the repair merge SHA, transition to `repair-shipped`, and defer original-run terminal finalize until that watch passes.



### FINDING_26:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/references/step2-main-health-fix.md:77-82; python/larch/implement/ship.py:200-202
- **Concern**: Pre-PR main repair cannot require base main to turn green before merge. Scenario: The failed default-branch run stays red until the feature branch repair is merged. The planned Step 2 reference waits for `ci main-health` on the base ref to report pass, and the pre-merge gate routes any red base to ci-fix, so a run can fix the defect on its branch but then loop or bail instead of shipping the repair the issue requires.
- **Proposed resolution**: Record the repaired failed run and base SHA as owned by the branch, run branch or PR verification, and let the merge gate proceed only for that recorded main failure when the repair commit is present and the base SHA has not changed. Re-run main-health normally for any new or different failure.



### FINDING_27:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/implement/ship_state.py:18-56
- **Concern**: Emergency repair state keys are not added to the ship-state contract. Scenario: The plan tracks `EMERGENCY_REPAIR_BRANCH`, `ORIGINAL_BRANCH_FORBIDDEN`, `MAIN_REPAIR_RUN_ID`, and `MAIN_REPAIR_HEAD`, but ship state only accepts fixed keys. Patch or write attempts can raise invalid field or drop the fields, so resume cannot enforce repair branch isolation.
- **Proposed resolution**: Add `python/larch/implement/ship_state.py` to firm changes and allow, initialize, validate, and preserve the new repair-state fields used by `ship.py`, `ship_resume.py`, and `dispatch_ship.py`.



### FINDING_28:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/state/bootstrap.py:453-454
- **Concern**: Durable main-health materialization targets the wrong bootstrap file. Scenario: The plan lists `python/bootstrap.py`, but Step 0's session materializer is `python/larch/state/bootstrap.py`; following the plan leaves only `preflight-tmpdir.env` copied, so Step 2 or resume can lose `main-health.env` and skip or misroute the red-main repair.
- **Proposed resolution**: Replace the firm file entry with `python/larch/state/bootstrap.py` and copy `$PREFLIGHT_TMPDIR/main-health.env` beside `preflight-tmpdir.env`, preserving an existing implement-side file on resume unless a refreshed preflight explicitly rewrites it.



### FINDING_29:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/git/gh.py:966-985; skills/implement/SKILL.md:31
- **Concern**: Forked main-health must not pass `upstream/main` to `gh run list --branch`. Scenario: The plan says forked runs query the upstream repo with base ref `upstream/main`, but the new helper uses `gh run list --branch`; GitHub branch filters expect the branch name in that repo. A forked run can get no rows or error for a healthy upstream `main` and bail before Step 2.
- **Proposed resolution**: Normalize the GitHub run-list branch to `main` while using `--repo "$UPSTREAM_REPO"`; keep `upstream/main` only for local git and rebase comparisons, and add a forked argv case for `ci main-health`.



