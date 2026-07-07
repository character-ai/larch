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

### FINDING_8:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/shared/voting-protocol.md
- **Concern**: [SCOPE-REDUCTION] Conditional shared-prompt files remain firm UPDATED. Scenario: `skills/shared/voting-protocol.md` and `skills/shared/oos-acceptance-rubric.md` are `### UPDATED:` while their bullets say "only if" wording conflicts. That turns optional prompt churn into mandatory diff surface.
- **Proposed resolution**: Move both to `### MAY_UPDATE:` or drop them from the firm file list; keep the required gate-5 edits in `skills/shared/review-acceptance-rubric.md` and `skills/shared/reviewer-templates.md` plus `make test-prompt-template-invariants`.

### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/shared/voting-protocol.md;skills/shared/oos-acceptance-rubric.md
- **Concern**: [SCOPE-REDUCTION] Conditional shared-rubric files remain firm `### UPDATED:` entries. Scenario: Both files say update only when wording conflicts, but `### UPDATED:` still makes them mandatory diff targets and triggers the six-agent regen sweep even when gate-5 text is unchanged.
- **Proposed resolution**: Reclassify `skills/shared/voting-protocol.md` and `skills/shared/oos-acceptance-rubric.md` as `### MAY_UPDATE:`; run agent regen only when those files actually change.

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/shared/voting-protocol.md
- **Concern**: [SCOPE-REDUCTION] Conditional reviewer prompt files listed as firm `### UPDATED:`. Scenario: Bullets say update `voting-protocol.md` and `oos-acceptance-rubric.md` only when wording conflicts, but firm `### UPDATED:` makes optional prompt churn mandatory (~6 agent regens).
- **Proposed resolution**: Reclassify those two paths as `### MAY_UPDATE:`; keep `review-acceptance-rubric.md` and generated agent regen as the firm doctrine surface.
