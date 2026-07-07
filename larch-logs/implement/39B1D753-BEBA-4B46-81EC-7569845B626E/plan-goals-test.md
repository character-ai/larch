## Goal
Implement issue #6506: [IMPLEMENTING] [BUG] /implement merges on broken or flaky main instead of fixing it in-run.

## Implementation Plan
## Plan

## Approach

Add a Python-owned main-health path with commit-scoped run selection, durable session materialization, split pre-PR vs ship-phase repair contracts, and explicit repair-state tracking so branch fixes do not deadlock on default-branch green. Keep prompt prose thin.

1. Add a typed default-branch CI health helper.
   - Query recent `push` runs for the configured workflow on the base branch.
   - Support optional `head_sha` / `--commit` filtering so pre-merge and post-merge checks target the intended commit, not a stale unrelated green run.
   - For forked runs, pass `--repo "$UPSTREAM_REPO"` and bare `--branch main` to `gh run list`; use `upstream/main` only for local git comparisons, never as the GitHub branch filter.
   - Emit `MAIN_CI_STATUS=pass|fail|pending|error`, `MAIN_FAILED_RUN_ID=`, `MAIN_HEALTH_HEAD_SHA=`, and bounded `MAIN_HEALTH_DETAIL`.
   - When classifying a branch head or requested SHA, inspect recent push runs for the same `headSha`. If any named repository test or lint failure for that SHA later concluded `success` without a new commit, return `fail` (or equivalent repair-needed classification) with the failed run ID instead of `pass`; reserve `pass` for no same-SHA repository-failure evidence.
   - Fail closed on malformed `gh` output or ambiguous state.
2. Always resolve repo and record main health at preflight.
   - When `--repo` is omitted, resolve via `python/cli.py gh resolve-repo` (forked runs still honor explicit `--repo` / upstream override).
   - Always invoke `ci main-health` against the resolved repo and bare default branch name (`main`).
   - Extend the success envelope additively with `MAIN_CI_STATUS`, `MAIN_FAILED_RUN_ID`, `MAIN_HEALTH_HEAD_SHA`, and `MAIN_HEALTH_DETAIL`.
   - On repo-resolution failure, skipped probe, or degraded `gh` read, still emit all four `MAIN_*` keys with `MAIN_CI_STATUS=error` and bounded detail; do not omit keys or abort admission solely for degraded reads.
   - Write `$PREFLIGHT_TMPDIR/main-health.env` with the same KVs; bootstrap copies it beside existing preflight artifact materialization (`preflight-tmpdir.env`, plan copy) so resume and multi-turn Step 2 do not depend on chat-only KVs.
3. Thread main health into `/implement` with distinct repair paths and split gates.
   - Preflight records main health only; it does not edit before Step 0 creates the run branch.
   - Orchestrator parses the full success-envelope key set (existing keys plus the four `MAIN_*` keys) and durable `$IMPLEMENT_TMPDIR/main-health.env` before Step 0 / Step 2 routing.
   - After `BOOTSTRAP_NEXT=step2`, if durable `MAIN_CI_STATUS=fail`, run the dedicated pre-PR repair reference (`step2-main-health-fix.md`) before `implement run-dispatch`.
   - Pre-PR repair exit contract (no deadlock): repair on the feature branch, run `python/cli.py checks run-relevant`, commit with a message naming the main-health repair, then record durable repair ownership in `main-health.env` (for example `MAIN_HEALTH_REPAIR_COMMITTED=true`, `MAIN_HEALTH_REPAIR_FAILED_RUN_ID`, `MAIN_HEALTH_REPAIR_BASE_SHA`, `MAIN_HEALTH_REPAIR_HEAD`). Re-run `ci main-health` for telemetry/logging only; do **not** require `MAIN_CI_STATUS=pass` on the default branch before dispatch. Continue to `implement run-dispatch` once branch verification passes.
   - If `MAIN_CI_STATUS=pending`, bounded wait via `ci main-health --wait`, then branch: `pass` continues, `fail` enters pre-PR repair, `pending` after timeout operator-bails with detail, `error` records detail and operator-bails (do not silently proceed).
   - Pre-merge merge gate (Step 8+): block merge on new or different default-branch failures. Allow merge over a **recorded** red-main failure only when durable state shows an in-branch repair for that same `MAIN_FAILED_RUN_ID` / base SHA fingerprint, PR checks pass, and branch guards succeed. Do not require default-branch green pre-merge when the current branch already carries the repair for that failure. Re-run main-health normally for any new or different failure and route to ci-fix.
   - Step 8+ also checks main health immediately before every merge attempt using the current base / merge commit SHA when no qualifying repair marker covers the active failure.
   - Red main with no recorded repair routes to the existing CI-fix handoff with the default-branch failed run ID.
4. Preserve failed CI evidence through retry paths.
   - Do not let `fail + behind` hide the failed run by rebasing first.
   - Carry the failed run ID into the handoff, then allow the existing pre-fix rebase gate to rebase before repair.
5. Treat repo flakes as defects end-to-end.
   - If a named repository test or lint fails, then later passes with no authored fix commit or repair-path delta, return `flaky-defect-unfixed`.
   - Map `flaky-defect-unfixed` through `_agentic_fix_result`, `ci_monitor`, and ship routing to `NEEDS_USER_INPUT` / `NEXT_ACTION=ci-fix`, not `FixResult(status="pushed")` or terminal `passed`.
   - Keep infrastructure transients as the only log-only retry class.
6. Add bounded post-merge watch that is commit-scoped.
   - After merge, before postmerge finalize state, wait for the push workflow run whose `head_sha` matches the merged commit.
   - Ignore older default-branch greens; treat no matching run as `pending` until timeout.
   - On pass for that SHA, continue normally.
   - On fail for that SHA, enter an explicit post-merge emergency-repair state machine instead of finalizing success or routing through generic ci-fix alone.
7. Post-merge emergency repair state machine.
   - Phases: `postmerge-push-watch` → `emergency-repair` → `repair-shipped` or `stalled`.
   - Defer `post-merge-sentinel` and `_ship_postmerge_phase` until push CI for the merged SHA passes or repair ownership is established.
   - Checkout/create a dedicated repair branch from fresh `origin/main`; never commit or push on the original feature branch.
   - Track `EMERGENCY_REPAIR_BRANCH`, `ORIGINAL_BRANCH_FORBIDDEN`, `MAIN_REPAIR_RUN_ID`, `MAIN_REPAIR_HEAD`, `EMERGENCY_REPAIR_PR_NUMBER`, and related fields in validated ship state.
   - Fix from redacted push-run logs, open/ship/merge the repair PR on the repair branch only via a dedicated driver path; forbid larch-log commits after the original PR merge.
   - After repair merge, run commit-scoped push watch for the repair merge SHA; transition to `repair-shipped` only when that watch passes.
   - Keep `MERGE_RESULT` from marking terminal `done` until repair ships or the session stalls with explicit detail.
   - Do not reuse `ship-pr-ci-fix.md` verbatim for post-merge repair; use `postmerge-emergency-repair.md` and a dedicated `route-exit` action.
8. Wire new route reasons through all ship surfaces.
   - Add `main-ci-fail`, `postmerge-main-ci-fail`, and `flaky-defect-unfixed` to `config.NEEDS_USER_REASON_TOKENS`, `dispatch_ship.py` autonomous routing, `ship_result.py` validation, and `ship-pr-exit-matrix.md`.
   - Route `main-ci-fail` and `flaky-defect-unfixed` to `NEXT_ACTION=ci-fix`.
   - Route `postmerge-main-ci-fail` to a dedicated `NEXT_ACTION=postmerge-repair` that loads only `postmerge-emergency-repair.md`; do not fall through to generic ci-fix.
   - Include `FAILED_RUN_ID`, `DETAIL`, `MAIN_HEALTH_HEAD_SHA`, repair-marker fields, and emergency-repair state in `.ship-route-exit-handoff.env`.
9. Clarify review scope doctrine.
   - Red or flapping default-branch CI counts as actively blocking verification for every `/implement` run.
   - The orchestrator owns the repair. Reviewers should not turn this into unrelated scope expansion.

## Files to modify/create

### NEW: python/larch/implement/main_health.py

Create the typed main-health module.

- Add frozen dataclasses such as `MainHealthStatus` and `MainHealthWaitResult`.
- Add `read_main_health(...)`.
  - Inputs: runner, repo, base branch (bare name, e.g. `main`), workflow name, limit, cwd, optional `head_sha`, optional forked upstream repo override.
  - Use filtered `gh run list` with `--event push`, `--branch`, `--workflow`, `--limit`, and `--commit` when `head_sha` is set.
  - When `head_sha` is set, accept only rows whose `headSha` matches; do not treat an older unrelated success as pass.
  - When classifying a SHA or current default-branch head, scan recent push runs for the same `headSha`; if a named repository failure for that SHA was later followed by `success` without a new commit, classify as repair-needed (`fail`) with the failed run ID, not `pass`.
  - Classify:
    - matching completed `success` with no same-SHA repository-failure flap evidence as `pass`
    - matching completed failure-like conclusion as `fail`
    - matching queued or in-progress run as `pending`
    - no usable matching rows or read errors as `error`
  - Return the failed run ID and matched head SHA for failure-like conclusions.
- Add `wait_main_health(...)`.
  - Poll with bounded timeout and interval constants.
  - Stop on matching `pass` or `fail` for the requested SHA.
  - Return `pending` on timeout with no matching terminal run.
- Keep parsing strict. Treat untrusted `gh` JSON as data.

### NEW: skills/implement/references/step2-main-health-fix.md

Dedicated pre-PR main-CI repair contract.

- Entry: after `BOOTSTRAP_NEXT=step2` when durable `$IMPLEMENT_TMPDIR/main-health.env` has `MAIN_CI_STATUS=fail` and no repair marker covers the recorded failure.
- Read `MAIN_FAILED_RUN_ID`, `MAIN_HEALTH_HEAD_SHA`, and repair-marker fields from the sidecar; do not assume PR context.
- Capture redacted logs via `gh run view` / `gh run download` for the default-branch push run.
- Repair on the current feature branch: edit, run `python/cli.py checks run-relevant`, commit with a message that names the main-health repair.
- Write repair ownership to `main-health.env` (`MAIN_HEALTH_REPAIR_COMMITTED=true`, `MAIN_HEALTH_REPAIR_FAILED_RUN_ID`, `MAIN_HEALTH_REPAIR_BASE_SHA`, `MAIN_HEALTH_REPAIR_HEAD`).
- Refresh `ci main-health` for evidence/logging only; proceed to `implement run-dispatch` after branch checks pass without requiring default-branch `MAIN_CI_STATUS=pass`.
- Explicitly forbid calling `step-8-ship`, `ship pre-driver`, or post-PR ci-fix machinery on this path.

### NEW: skills/implement/references/postmerge-emergency-repair.md

Dedicated post-merge repair state machine reference.

- Document phases: `postmerge-push-watch`, `emergency-repair`, `repair-shipped`, `stalled`.
- Define when `post-merge-sentinel` may be written (only after merged-SHA push pass or emergency-repair ownership handoff).
- Define repair-branch checkout from `origin/main`, log capture from the failed merged-SHA push run, fix/commit/push rules, repair PR open/ship/merge on `EMERGENCY_REPAIR_BRANCH`, commit-scoped push watch for the repair merge SHA, and stall/operator-bail outcomes.
- State that `PR_NUMBER` in state remains the original feature PR; `EMERGENCY_REPAIR_PR_NUMBER` tracks the repair PR separately.
- Forbid commits on the original feature branch and forbid larch-log commits on any branch after original merge.
- State that this path is entered via `NEXT_ACTION=postmerge-repair`, not generic `ci-fix`.

### NEW: python/tests/implement/test_main_health.py

Cover main-health classification.

- latest matching success returns pass
- latest matching failure returns fail and failed run ID
- queued or in-progress matching run returns pending
- no rows, no SHA match, and malformed JSON return error
- filtered `gh run list` argv includes repo, bare branch `main`, event, workflow, limit, and commit when `head_sha` is set
- forked upstream repo uses `--repo upstream` with `--branch main`, not `upstream/main`
- stale older green ignored when waiting for a specific merged SHA
- same-SHA repository failure followed by success without new commit returns repair-needed/fail, not pass

### UPDATED: python/larch/git/gh.py

Extend the typed `gh run list` surface.

- Add optional `workflow`, `event`, `status`, and `commit` filters to a new helper, or add a separate `run_list_filtered_read`.
- Extend `WorkflowRun` additively with `head_sha` and `event`.
- Preserve existing callers of `run_list` and `run_list_successful`.
- Add parser coverage for missing, null, and malformed row fields.

### UPDATED: python/larch/implement/ci.py

Expose the new CLI.

- Add `main_health_main(argv)`.
- Emit only stable KVs:
  - `MAIN_CI_STATUS=pass|fail|pending|error`
  - `MAIN_FAILED_RUN_ID=`
  - `MAIN_HEALTH_HEAD_SHA=`
  - `MAIN_HEALTH_DETAIL=`
- Add `--repo`, `--base-ref` (local git ref; normalize to bare branch name for `gh`), `--workflow`, `--limit`, `--timeout`, `--wait`, and `--commit`.
- For forked runs, accept upstream repo override and always query GitHub with bare `main`.
- Validate non-negative numeric flags.
- Keep usage errors distinct from health errors.

### UPDATED: python/larch/cli.py

Register `("ci", "main-health")`.

### UPDATED: python/larch/core/config.py

Define the new wire literals and bounds once.

- Default workflow name, likely `CI`.
- run-list limit.
- main-health wait timeout and poll interval.
- reason tokens for `main-ci-fail`, `postmerge-main-ci-fail`, and `flaky-defect-unfixed`, pending timeout, and post-merge push failure.
- Add matching `NEEDS_USER_*` entries to `NEEDS_USER_REASON_TOKENS`.
- Add route token for `postmerge-repair` handoff action.

### UPDATED: python/larch/implement/preflight.py

Thread preflight main-health evidence.

- Resolve repo when `--repo` is empty via `gh resolve-repo`; forked explicit `--repo` override unchanged.
- After existing admission and plan materialization succeed, always run `ci main-health` when repo resolution succeeds.
- Extend `SUCCESS_ENVELOPE_KEYS` additively with `MAIN_CI_STATUS`, `MAIN_FAILED_RUN_ID`, `MAIN_HEALTH_HEAD_SHA`, and `MAIN_HEALTH_DETAIL`.
- Always emit all four keys on success, including degraded paths (`MAIN_CI_STATUS=error` when probe skipped or `gh` read fails).
- Write `$PREFLIGHT_TMPDIR/main-health.env` with the same KVs for bootstrap handoff.
- Do not edit or fix here. Preflight is still before branch setup.
- Do not abort admission solely for degraded main-health reads.

### UPDATED: python/larch/state/bootstrap.py

Materialize durable main-health evidence.

- During Step 0 plan/session materialization beside existing `preflight-tmpdir.env` and plan copy, copy `$PREFLIGHT_TMPDIR/main-health.env` to `$IMPLEMENT_TMPDIR/main-health.env` when present.
- On resume, preserve existing `$IMPLEMENT_TMPDIR/main-health.env` unless a refreshed preflight explicitly rewrites it.
- SKILL prose may still say `python/bootstrap.py` as the CLI entry; firm implementation target is this module.

### UPDATED: python/tests/state/test_bootstrap.py

Cover main-health handoff.

- copy from preflight tmpdir to implement tmpdir during initial bootstrap
- preserve existing implement-side `main-health.env` on resume unless preflight refresh overwrites it

### UPDATED: skills/implement/SKILL.md

Wire the new orchestration rules.

- Preflight item 3: expand allowed success-envelope keys to include `MAIN_CI_STATUS`, `MAIN_FAILED_RUN_ID`, `MAIN_HEALTH_HEAD_SHA`, and `MAIN_HEALTH_DETAIL` (update the seven-key wording to the full additive set).
- Bind durable main-health evidence from parsed envelope and/or `$IMPLEMENT_TMPDIR/main-health.env` before Step 0 / Step 2 routing.
- After `BOOTSTRAP_NEXT=step2`:
  - `MAIN_CI_STATUS=fail` without repair marker → execute `step2-main-health-fix.md` before `implement run-dispatch`.
  - repair marker present for recorded failure → continue to dispatch without re-entering repair.
  - `MAIN_CI_STATUS=pending` → bounded `ci main-health --wait`, then pass / repair / bail per Approach §3.
  - `MAIN_CI_STATUS=error` → operator bail with recorded detail.
  - `MAIN_CI_STATUS=pass` → continue to Step 2 dispatch.
- In Step 8+ routing, document that `main-ci-fail` and `flaky-defect-unfixed` route to `NEXT_ACTION=ci-fix`.
- Document `postmerge-main-ci-fail` routes to `NEXT_ACTION=postmerge-repair` and loads only `postmerge-emergency-repair.md`.
- Document merge-over-recorded-repair rule: allow merge when durable repair marker matches `MAIN_FAILED_RUN_ID` / base SHA and PR checks pass; block new or different default-branch failures.
- Update the CI-fix procedure call site so `FAILED_RUN_ID` may refer to a default-branch push run, not only a PR run.
- Update the no-post-merge-commit rule with the narrow emergency repair-branch exception.
- Do not add Bash logic beyond thin calls to Python CLI helpers.
- If Bash fences change, update `scripts/test-implement-fence-shape.sh`.

### UPDATED: scripts/test-implement-fence-shape.sh

Update `EXPECTED_OLD` / `EXPECTED_NEW` only if the `skills/implement/SKILL.md` Bash fence shape changes.

### UPDATED: python/larch/implement/ship_state.py

Extend the ship-state contract for emergency repair and main-health repair markers.

- Add allowed keys such as `EMERGENCY_REPAIR_BRANCH`, `ORIGINAL_BRANCH_FORBIDDEN`, `MAIN_REPAIR_RUN_ID`, `MAIN_REPAIR_HEAD`, `EMERGENCY_REPAIR_PR_NUMBER`, `MAIN_HEALTH_REPAIR_COMMITTED`, `MAIN_HEALTH_REPAIR_FAILED_RUN_ID`, `MAIN_HEALTH_REPAIR_BASE_SHA`, `MAIN_HEALTH_REPAIR_HEAD`, and `MAIN_HEALTH_HEAD_SHA`.
- Include them in `_ALLOWED_SHIP_STATE_KEYS`, write/patch/read validation, initial-state defaults where needed, and resume hydration.
- Reject unknown keys and preserve repair-state fields across patch/write/resume paths.

### UPDATED: python/larch/implement/dispatch_ship.py

Route main-health failures into existing handoff mechanics.

- Add `main-ci-fail` and `flaky-defect-unfixed` to autonomous CI-fix routing alongside `first-fixer-non-health`.
- Add `postmerge-main-ci-fail` to dedicated `postmerge-repair` routing, not ci-fix.
- Include `FAILED_RUN_ID`, `DETAIL`, `MAIN_HEALTH_HEAD_SHA`, repair-marker fields, and emergency-repair state in `.ship-route-exit-handoff.env`.
- Keep route-exit JSON validation strict.

### UPDATED: python/larch/implement/ship_result.py

Recognize new needs-user reasons.

- Extend validation / normalization so `main-ci-fail` and `flaky-defect-unfixed` classify to CI-fix handoffs, not `operator-bail` fallthrough.
- Map `postmerge-main-ci-fail` to `NEXT_ACTION=postmerge-repair`.

### UPDATED: python/larch/implement/ship.py

Add merge-loop and post-merge integration.

- Before accepting `monitor.action == "merge"`, evaluate main health for the current base commit / `origin/main` HEAD.
- Allow merge when durable repair marker covers the recorded default-branch failure for the same run/SHA fingerprint and PR checks pass; otherwise on `fail`, write terminal state with the failed default-branch run ID and return a CI-fix handoff (`main-ci-fail`).
- On `pending`, wait within the configured bound or stall with clear detail. Do not merge onto unknown red main.
- After a successful merge result, capture merged commit SHA from PR merge metadata or refreshed `origin/main`.
- Before `_ship_postmerge_phase`, wait for the push workflow run matching that merged SHA.
- On post-merge push failure for that SHA, enter `postmerge-emergency-repair` driver branch (`postmerge-main-ci-fail`) instead of finalizing success or generic ci-fix.
- Enforce repair-branch-only commits after original merge via ship-state guards (`ORIGINAL_BRANCH_FORBIDDEN`).
- Ensure no larch-log commit happens after the original PR merge.

### UPDATED: python/larch/implement/ship_pr.py

Keep postmerge finalization compatible.

- Write `post-merge-sentinel` only after merged-SHA push watch passes or emergency repair ownership is established per `postmerge-emergency-repair.md`.
- Keep normal successful-merge finalize behavior unchanged once the watch passes.

### UPDATED: python/larch/implement/ship_resume.py

Support mid-repair resume.

- Recognize `postmerge-push-watch` and `emergency-repair` phases.
- Resume from durable repair-state fields in validated ship state without reusing the original feature branch.

### UPDATED: python/larch/implement/ci_monitor.py

Fix retry semantics that hide failures.

- Change `decide` so `fail + behind + failed_run_id` routes to failure evaluation or handoff before rebase discards the run signal.
- Keep a conservative rebase path for failed status with no run ID.
- Preserve `failed_run_id` in `MonitorResult` and ship state through rebase-required handoffs.
- At merge decision, consult main health and durable repair markers per Approach §3; do not merge on PR-green alone when default-branch failure is uncovered and unrepaired.
- Map `flaky-defect-unfixed` from agentic-fix results to a non-success handoff (`NEEDS_USER_INPUT` / ci-fix), parallel to `first-fixer-non-health`.
- Add tests for:
  - pass still merges only when main health is pass or a qualifying repair marker covers the active failure
  - fail plus behind does not lose `FAILED_RUN_ID`
  - red main without repair returns a CI-fix handoff, not merge
  - recorded repair marker allows merge without default-branch green pre-merge
  - flaky-defect-unfixed does not return terminal passed

### UPDATED: python/larch/implement/ci_agentic_fix.py

Block no-change green exits for repository failures.

- Track whether a fix commit or pushed repair-path delta landed after the observed failed run.
- Do not clear the flaky-defect obligation for base-only rebases, reruns, shard movement, or other head changes without an authored fix.
- If CI turns green with no code change and the failed log names a repository test or lint, return `flaky-defect-unfixed`.
- Let infrastructure-only transient signatures keep the existing rerun behavior.
- Include the redacted failed log detail file in the exhausted or handoff path.

### UPDATED: skills/implement/references/ship-pr-ci-fix.md

Replace the 30-attempt wording.

- State that repository tests or lints that fail and then pass with no code change are nondeterminism defects.
- Require root cause and repair before ship completes.
- Allow only named operator deferral or outside-repo root cause as exceptions.
- Mention default-branch failed run IDs as valid inputs.
- State that `flaky-defect-unfixed` is a handoff status, not success.
- Document merge-over-recorded-repair exception for push-red/PR-green failures repaired on the feature branch.

### UPDATED: skills/implement/references/ship-pr-exit-matrix.md

Document new route reasons and handoff fields.

- Map `main-ci-fail` and `flaky-defect-unfixed` to `NEXT_ACTION=ci-fix` with default-branch `FAILED_RUN_ID` semantics.
- Map `postmerge-main-ci-fail` to `NEXT_ACTION=postmerge-repair` loading `postmerge-emergency-repair.md`.
- Document pre-PR Step 2 repair as a separate reference, not this matrix path.
- Document merge-over-recorded-repair rule and post-merge emergency repair continuation vs generic ci-fix.

### UPDATED: skills/implement/references/execution-issues-tracking.md

Replace the log-only transient wording.

- Reserve log-only for infrastructure transients.
- State that named repository test or lint failures are deterministic breakage or nondeterminism, both in-scope defects.
- Require recording explicit operator deferrals.

### UPDATED: skills/shared/review-acceptance-rubric.md

Clarify gate 5.

- Add that red or flapping default-branch CI actively blocks verification for every run.
- State that restoring or stabilizing default-branch CI clears the gate.
- State that `/implement`, not reviewers, owns executing the repair.

### UPDATED: skills/shared/reviewer-templates.md

Propagate the gate 5 clarification to reviewer self-filter prose.

### UPDATED: skills/shared/voting-protocol.md

Update the YES definition only if the gate wording needs a matching voter clarification.

### UPDATED: skills/shared/oos-acceptance-rubric.md

Update only the OOS boundary wording that conflicts with the new default-branch CI rule.

### UPDATED: agents/code-reviewer.md

Regenerate from `skills/shared/reviewer-templates.md`.

### UPDATED: agents/reviewer-plan-fidelity.md

Apply the same gate wording, then regenerate pre-rendered prompts.

### UPDATED: agents/reviewer-code-robustness.md


### UPDATED: agents/reviewer-security-structure-tests.md


### UPDATED: agents/reviewer-edge-cases.md


### UPDATED: agents/reviewer-testing.md


### UPDATED: docs/clean-main-contract.md

Document that `/implement --merge` also checks default-branch CI health.

- Explain that red default-branch CI becomes in-scope repair work.
- Explain pending/error behavior at entry, durable `main-health.env` handoff, repair-marker merge exception, and forked upstream branch-filter semantics.

### UPDATED: docs/workflow-lifecycle.md

Document the main-health gate, pre-PR repair reference, repair-marker merge rule, flaky-test doctrine, commit-scoped post-merge push watch, `postmerge-repair` routing, and emergency-repair state machine.

### UPDATED: docs/configuration-and-permissions.md

Update the `--admin` merge safety invariants.

- Add default-branch CI health to the pre-admin merge gate.
- Clarify that green PR checks alone are insufficient when default-branch push CI is red and unrepaired.

### UPDATED: python/tests/implement/test_ci.py

Cover `ci main-health` CLI KVs, `--commit`, forked bare-branch argv, and usage failures.

### UPDATED: python/tests/implement/test_ci_monitor.py

Cover fail-plus-behind preservation, main-health merge gating, repair-marker merge allowance, and flaky-defect-unfixed non-success handoff.

### UPDATED: python/tests/implement/test_ci_agentic_fix.py

Cover no-code-change pass after a named repository failure returning `flaky-defect-unfixed`.

### UPDATED: python/tests/implement/test_preflight.py

Cover additive preflight main-health KVs (including `MAIN_HEALTH_HEAD_SHA`), always-present keys on degraded reads, repo auto-resolution, `main-health.env` write, and error-path envelope completeness.

### UPDATED: python/tests/implement/test_ship.py

Cover merge-loop and post-merge behavior.

- pre-merge red main without repair routes to CI-fix
- recorded repair marker allows merge without default-branch green pre-merge
- pending main health stalls or waits without merging
- post-merge watch ignores stale previous green and waits for merged SHA
- post-merge push failure for merged SHA enters `postmerge-repair`, not generic ci-fix
- repair-branch guard forbids commits on original feature branch
- flaky-defect-unfixed routes to ci-fix, not terminal success

### UPDATED: python/tests/implement/test_ship_state.py

Cover allowed emergency-repair and repair-marker keys through write/patch/resume validation.

## Edge cases

- `gh run list` returns a pending run above an older failed run for the same SHA. Treat as `pending` until bounded wait resolves.
- `gh run list` returns no rows or no row for the requested SHA. Treat as `error` or `pending` (watch mode) respectively; do not silently merge.
- An older default-branch success exists before the merged-SHA run appears. Post-merge watch must ignore the stale green and wait for the merge commit's run.
- Same-SHA flap: repository failure for a SHA followed by success without a new commit must not classify as `pass`.
- Forked runs query `--repo "$UPSTREAM_REPO" --branch main`; `upstream/main` is for local git only.
- A failed run ID may be a default-branch push run. CI log capture must not assume PR context.
- Pre-PR repair must not deadlock waiting for default-branch green; repair markers plus branch/PR verification gate dispatch and merge instead.
- Emergency repair must not touch the original feature branch or commit run logs after merge.
- Operator can explicitly defer a named flaky test. Record that deferral in execution issues.
- Resume mid pre-PR repair or mid emergency repair must read `$IMPLEMENT_TMPDIR/main-health.env` and validated ship repair-state fields, not stale chat KVs.
- Base SHA changes after repair marker recorded. Treat as a new default-branch failure and block merge until re-evaluated.

## Failure modes when non-trivial

- Wrong workflow filter could miss red main. Keep workflow configurable and default to `CI`.
- Missing `head_sha` correlation could mask merged-SHA failures behind unrelated greens. Commit filter is mandatory at ship call sites.
- Repair-marker merge allowance keyed to wrong run/SHA could ship without fixing the active failure. Bind markers to `MAIN_FAILED_RUN_ID` and base SHA fingerprint.
- Post-merge repair branch can conflict with concurrent main changes. Rebase from fresh `origin/main` and fail closed on conflict.
- A no-change green may be a true infrastructure transient. Only classify named repository test or lint failures as flaky defects.
- Main-health `error` can block merges during GitHub API issues. Use bounded pending/error behavior and clear operator detail.
- Incomplete route-token or ship-state wiring could misclassify new reasons or drop repair fields mid-resume. Keep `config`, `ship_state`, `ship_result`, `dispatch_ship`, and exit-matrix in sync.
- Routing post-merge failure through generic ci-fix could strand repair on the wrong branch or lifecycle. Keep `postmerge-repair` separate.

## Testing strategy

Run targeted tests only for changed files.

- `python -m pytest python/tests/implement/test_main_health.py`
- `python -m pytest python/tests/implement/test_ci.py python/tests/implement/test_ci_monitor.py python/tests/implement/test_ci_agentic_fix.py`
- `python -m pytest python/tests/implement/test_preflight.py python/tests/implement/test_ship.py python/tests/implement/test_ship_state.py`
- `python -m pytest python/tests/state/test_bootstrap.py -k main_health`
- `python3 python/cli.py generate code-reviewer-agent`
- `python3 python/cli.py generate reviewer-plan-fidelity-agent`
- `python3 python/cli.py generate reviewer-code-robustness-agent`
- `python3 python/cli.py generate reviewer-security-structure-tests-agent`
- `python3 python/cli.py generate pre-rendered-reviewer-prompts`
- `make test-prompt-template-invariants`
- If `skills/implement/SKILL.md` fences changed: `bash scripts/test-implement-fence-shape.sh`
- `make py-lint`
- `make py-test`

## Difficulty

HARD. This changes merge gating, CI retry semantics, post-merge lifecycle, pre-PR repair orchestration, ship-state contracts, and prompt doctrine. It also adds a narrow exception to a high-stakes no-post-merge-commit invariant and a repair-marker merge exception to avoid pre-merge deadlock.

## Acceptance

Run targeted tests only for changed files.

- `python -m pytest python/tests/implement/test_main_health.py`
- `python -m pytest python/tests/implement/test_ci.py python/tests/implement/test_ci_monitor.py python/tests/implement/test_ci_agentic_fix.py`
- `python -m pytest python/tests/implement/test_preflight.py python/tests/implement/test_ship.py python/tests/implement/test_ship_state.py`
- `python -m pytest python/tests/state/test_bootstrap.py -k main_health`
- `python3 python/cli.py generate code-reviewer-agent`
- `python3 python/cli.py generate reviewer-plan-fidelity-agent`
- `python3 python/cli.py generate reviewer-code-robustness-agent`
- `python3 python/cli.py generate reviewer-security-structure-tests-agent`
- `python3 python/cli.py generate pre-rendered-reviewer-prompts`
- `make test-prompt-template-invariants`
- If `skills/implement/SKILL.md` fences changed: `bash scripts/test-implement-fence-shape.sh`
- `make py-lint`
- `make py-test`

diff_lines: 1950

## Test plan
(no test plan section in plan-file)
