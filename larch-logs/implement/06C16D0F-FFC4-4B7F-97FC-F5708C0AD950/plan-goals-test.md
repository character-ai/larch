## Goal
Implement issue #6526: [IMPLEMENTING] /implement must not declare success with plan work left undone: gate plan-coverage gaps and todos_left.

## Implementation Plan
## Plan

## Goal

Prevent `/implement` from declaring success while firm plan work remains undone, including fallback, recovery, direct PR mutation, and self-review paths.

Use the Step 0 materialized plan as the source of truth. Keep the gate mechanical: counts, thresholds, recorded disposition, and a durable fingerprint for stale-edit detection.

## Approach

1. Make scope disposition a shared fence with explicit timing and a live git baseline.

   - Add one shared scope-disposition compute/write path that compares `$IMPLEMENT_TMPDIR/plan.txt` (Step 0 materialized plan) against touched firm-heading paths derived from the Step 0 / prelaunch baseline through `HEAD`, plus current uncommitted and untracked paths. Produce:
     - total firm-heading paths
     - touched firm-heading paths
     - untouched firm-heading paths
     - untouched percent
     - band: `advisory`, `middle`, `high`
     - `todos_left` count and bounded text
     - a coverage fingerprint over plan paths + touched set + `todos_left`
     - `PLAN_COVERAGE_DISPOSITION_REQUIRED`
     - `PLAN_FIDELITY_FORCED` when middle band trips
   - **Pinned ordering for external `STATUS=complete`**: compute coverage in `dispatch_step2.py` and emit additive KVs, but run the operator disposition prompt and recording only after `step-2-post-dispatch.sh` returns `POST_DISPATCH_NEXT=continue`. Do not attach a partial disposition to a run that never settled post-dispatch.
   - **Separate pre-Step-3 fence for main-agent paths**: run the same compute/write path on `claude_fallback` and recovery after the main-agent edit leg and before Step 3 via `dispatch_commit_route.py`.
   - **Recompute and invalidate after later edits**: extend the shared fence to Step 5 review commits, Step 7 commit-route success, and checks-repair re-entry. When the live fingerprint differs from the recorded disposition fingerprint, clear the disposition artifact and require a fresh operator choice before Step 8 or PR mutation.
   - Missing or malformed plan/coverage input on a required-disposition path must fail closed, not advisory.

2. Add threshold constants in config.

   - Middle band: untouched firm headings `>= 20%` of firm headings or `>= 10` headings.
   - High band: untouched firm headings `>= 50%` of firm headings or `>= 30` headings.
   - Keep `### MAY_UPDATE:` excluded from the gate.
   - Add incident-rationale comments near the existing plan-size constants.
   - Add `NEEDS_USER_SCOPE_DISPOSITION` and `SHIP_ROUTE_ACTION_HALT_SCOPE_DISPOSITION` wire literals for ship route-exit.

3. Upgrade Step 2 coverage emission (compute early, prompt late on complete path).

   - In `dispatch_step2.py`, compute and persist coverage before emitting `STATUS=complete`.
   - Emit additive KVs only, preserving existing warning KVs for compatibility.
   - Add new KVs for:
     - `PLAN_COVERAGE_TOTAL`
     - `PLAN_COVERAGE_TOUCHED`
     - `PLAN_COVERAGE_UNTOUCHED`
     - `PLAN_COVERAGE_UNTOUCHED_PERCENT`
     - `PLAN_COVERAGE_BAND`
     - `PLAN_COVERAGE_FILE`
     - `PLAN_COVERAGE_UNTOUCHED_FILE`
     - `TODOS_LEFT_COUNT`
     - `TODOS_LEFT_FILE`
     - `PLAN_FIDELITY_FORCED`
   - Treat non-empty `todos_left` on `STATUS=complete` as disposition-required even when file coverage is otherwise complete.
   - Keep below-middle gaps warning-only only when the coverage artifact is valid; unreadable or malformed coverage on a complete path is a hard failure or disposition-required halt, not advisory.
   - Do not prompt or record disposition from the Step 2 envelope alone on the external-complete path; defer to post-dispatch.

4. Update /implement routing with path-specific disposition timing.

   - Update `skills/implement/SKILL.md` Step 2 routing:
     - On `STATUS=complete`: after envelope validation and `step-2-post-dispatch.sh` returns `POST_DISPATCH_NEXT=continue`, parse coverage KVs, and when `PLAN_COVERAGE_DISPOSITION_REQUIRED=true`, run the disposition prompt and recording before Step 3.
     - On `claude_fallback` / recovery: run the disposition prompt after the post-main-agent / recovery coverage fence and before Step 3 when required.
   - Prompt choices:
     - `proceed-partial`
     - `bail-rescope`
   - Wait indefinitely; if the platform returns a no-response fallback, re-ask the same prompt.
   - Do not default silently.
   - After Step 5 review commits, Step 7 commit-route success, or checks-repair edits, re-run the shared compute fence; if the fingerprint changed, invalidate disposition and re-prompt before continuing toward Step 8.
   - Add/adjust Step 8 routing for `halt-scope-disposition` so readable artifacts re-enter the disposition prompt instead of terminating as Tool Failure.
   - Reserve Tool Failure for malformed or tampered coverage/disposition artifacts.

5. Record disposition durably and in the right order.

   - `proceed-partial`:
     - File the follow-up issue first via the existing `python/cli.py issue create-one` helper with a body file (no direct `gh issue create` in `scope_disposition.py`).
     - Cross-link both issues through existing repo helpers.
     - Make the current tracking issue blocked by the follow-up issue via `python/cli.py issue add-blocked-by` (tracking issue is client, follow-up is blocker).
     - Record the disposition and run-log batch only after issue number, URL, cross-link, and block relation all succeed.
     - Persist `FOLLOWUP_ISSUE_NUMBER` and URL.
     - On any follow-up or dependency failure, do not write `proceed-partial`; keep the run parked or route to `bail-rescope`.
   - `bail-rescope`:
     - Record the disposition.
     - Route through Step 12d with `plan-scope-disposition-bail-rescope`.
   - Both paths write the tmpdir artifact with the coverage fingerprint at record time.
   - Do not make the follow-up issue blocked by the still-open parent issue; that can deadlock the partial-scope workflow.

6. Harden ship, route-exit, and PR mutation surfaces.

   - Add shared `validate_disposition_for_ship()` that recomputes live coverage from `$IMPLEMENT_TMPDIR/plan.txt` and the current git delta, compares the live fingerprint to the recorded disposition fingerprint, and fails closed when recompute fails on a required-disposition path.
   - Call it from:
     - `ship_pre_driver_main`
     - `ship.py` immediately before every `ensure_pr` or PR-body refresh mutation
     - `pr.ensure_pr`, `_push_existing_pr`, and any PR-body refresh or rebase-refresh entry point before `gh.pr_create` / `gh.pr_edit_body` / `gh.pr_edit_body_file`
   - When disposition is required but missing, stale, or invalid:
     - emit `needs_user_reason=scope-disposition` (config constant)
     - map to `NEXT_ACTION=halt-scope-disposition` in `_classify_ship_needs_user_reason`
     - return non-zero
     - do not seed PR state
     - do not create or update a PR
   - Step 8 orchestrator re-prompts disposition on `halt-scope-disposition` when artifacts are readable.

7. Force plan-fidelity on every Step 5 round with a prune wire contract.

   - When the middle threshold trips, set durable `PLAN_FIDELITY_FORCED=true`.
   - In `review_dispatch_panel.py`, append a forced row for `plan-fidelity-forced` with manifest field `prune_exempt=true`.
   - Select the first eligible external tool available in the panel from the plan-fidelity agent source, so TRIVIAL or Cursor-absent panels still get the forced check.
   - Keep the existing additive plan-fidelity lane.
   - In `reviewer_prune_filter`, skip productivity pruning for rows with `prune_exempt=true` before `net_prunable` and `floor_prunable` checks.
   - For self-review mode, honor the forced flag per the updated self-review reference (inline bounded plan-fidelity pass or explicit block while forced).
   - Add tests for TRIVIAL, MODERATE, and HARD panels, including Cursor-unavailable cases, and assert `prune_exempt=true` survives pruning.

8. Project partial scope into completion surfaces with disposition-aware PR linking.

   - Add disposition-aware linker helpers in `tracking_issue.py`:
     - `link_pr_closes` for full scope (unchanged behavior)
     - `link_pr_part_of` for `proceed-partial`
     - a selector that chooses linker from recorded disposition
   - PR body:
     - Route both create and update footers through the disposition-aware linker.
     - For `proceed-partial`, emit `Part of #N` instead of `Closes #N`.
     - Add a bounded `## Deferred plan inventory` section with untouched headings, bounded `todos_left`, and the follow-up issue reference.
     - On existing-PR refresh, replace a prior `Closes #N` footer with `Part of #N` when disposition is partial; do not reinsert `Closes #N`.
   - Final summary:
     - Add one plan-coverage line with touched/total firm headings, disposition, `todos_left` count, and follow-up issue number.
   - Tracking issue rename:
     - Suppress `[DONE]` when disposition is `proceed-partial`.
     - Do not close the tracking issue via a closing keyword on partial scope.
   - Full-scope runs keep existing closing-keyword behavior.

9. Close acceptance-gaming vectors and document the flow.

   - Compare coverage against the Step 0 materialized plan only.
   - Do not use tests, allowlists, skip markers, baselines, or implementation-authored acceptance artifacts as the coverage source.
   - Add docs for:
     - Step 2 coverage bands
     - post-dispatch vs pre-Step-3 disposition timing
     - operator disposition choices
     - `todos_left` as an independent trigger
     - fingerprint invalidation after Step 5 / Step 7 / checks-repair edits
     - the forced plan-fidelity reviewer and `prune_exempt=true`
     - ship-pre-driver, route-exit `halt-scope-disposition`, and direct-mutation hard gates
     - `Part of #N` and `[DONE]` suppression on partial scope
     - self-review behavior when forced review is active
   - Keep the gate mechanical; do not reintroduce subjective mid-run scope judgment.

## Files to modify/create

### NEW: python/larch/implement/scope_disposition.py

Add the shared compute/write fence and durable disposition helpers.

Include dataclasses and entry points for:

- computing coverage from Step 0 plan + baseline-to-HEAD git delta + uncommitted/untracked paths
- classifying middle/high/disposition-required state
- recording `proceed-partial` or `bail-rescope` only after durable side effects succeed
- rendering deferred inventory
- orchestrating follow-up issue filing via `issue create-one` and block relation via `issue add-blocked-by` (delegate to existing issue modules; no second direct `gh` create path)
- validating disposition for ship and PR mutation paths via live recompute + fingerprint compare
- invalidating stale disposition records

Use `larch.io` for KV reads/writes and atomic writes.

### NEW: python/tests/implement/test_scope_disposition.py

Add focused durability tests that mock `issue create-one` and `issue add-blocked-by`:

- assert no disposition artifact or run-log batch is written until issue number, URL, cross-link, and block relation all succeed
- assert failures leave the run parked or route to `bail-rescope`
- assert live recompute from baseline-to-HEAD detects committed-before-ship coverage drift

### UPDATED: python/larch/core/config.py

Add plan-coverage gate thresholds, `NEEDS_USER_SCOPE_DISPOSITION`, `SHIP_ROUTE_ACTION_HALT_SCOPE_DISPOSITION`, and incident-rationale comments near existing plan-size constants.

### UPDATED: python/larch/cli.py

Register new `implement scope-disposition ...` subcommands.

Keep exit codes distinct:

- usage: existing usage code
- missing required disposition: needs-user-input or stalled-style code as appropriate
- invalid persisted artifact: fail closed

### UPDATED: python/larch/implement/dispatch_step2.py

Replace the advisory-only uncovered count with the new coverage summary call.

Keep existing `WARN_PLAN_FILES_UNTOUCHED=true` and count KVs.

Emit additive coverage, `todos_left`, and `PLAN_FIDELITY_FORCED` KVs.

Do not run disposition prompt/recording here on the external-complete path; only compute and persist artifacts for post-dispatch consumption.

Fail closed or require disposition when coverage input is missing or malformed on a complete path.

### UPDATED: python/larch/implement/dispatch_commit_route.py

Run the shared scope-disposition compute/write fence on `claude_fallback` and recovery paths after the main-agent edit leg and before Step 3.

After Step 5 review commits and Step 7 commit-route success, recompute coverage, invalidate disposition when the fingerprint changes, and surface `PLAN_COVERAGE_DISPOSITION_REQUIRED` for orchestrator re-prompt.

### UPDATED: python/larch/implement/dispatch_manifest.py

Keep `todos_left` schema validation as a list.

Add bounded sanitizer support if the disposition module consumes `todos_left` text.

Do not change the external implementer manifest contract.

### UPDATED: skills/implement/SKILL.md

Update Step 2 external-complete routing:

- parse additive coverage KVs after envelope validation
- run disposition prompt/recording only after `POST_DISPATCH_NEXT=continue`
- wait indefinitely; re-ask on no-response platform fallback
- call disposition-recording CLI
- route `bail-rescope` to Step 12d
- continue to Step 3 only after `proceed-partial` records successfully

Add the pre-Step-3 claude_fallback/recovery disposition prompt when required.

Add re-prompt hooks after Step 5 commits, Step 7 commit-route success, and checks-repair re-entry when fingerprint invalidation occurs.

Update Step 8 routing for `halt-scope-disposition` from ship route-exit.

Document self-review forced-review behavior by reference.

### UPDATED: skills/implement/references/self-review.md

Add a forced-flag branch when `PLAN_FIDELITY_FORCED=true`:

- run an inline bounded plan-fidelity pass before continuing to Step 6, or
- block self-review with an explicit halt until the forced pass completes

Pin the branch before the existing checks-commit route.

### UPDATED: python/larch/implement/dispatch_ship.py

Gate `ship_pre_driver_main` before seed and OOS filing.

Refuse when disposition is required but not recorded or is stale.

Return `needs_user_reason=scope-disposition`.

Map `scope-disposition` to `NEXT_ACTION=halt-scope-disposition` in `_classify_ship_needs_user_reason`.

### UPDATED: python/larch/implement/ship.py

Call the shared ship-disposition validator immediately before every PR create/update mutation.

Ensure PR create and PR update paths fail closed when disposition is required but missing or stale.

### UPDATED: python/larch/git/pr.py

Call disposition validation before `ensure_pr`, before `_push_existing_pr`, and before any PR-body refresh or rebase-refresh path that reaches `gh.pr_create` / `gh.pr_edit_body_file`.

Cover both new PR creation and existing PR body update when `PR_NUMBER` is already set.

### UPDATED: python/larch/git/pr_body.py

Route `compose_pr_body` and `update_pr_body` footers through disposition-aware linker helpers.

Add deferred-inventory section support for `proceed-partial`.

Ensure existing PR update paths do not re-add `Closes #N` over a partial-scope body.

Extend the run-summary rendering hook so it can carry a plan-coverage line from final reporting.

### UPDATED: python/larch/issue/tracking_issue.py

Add `link_pr_part_of` and a disposition-aware linker selector used by PR compose/update paths.

Keep `link_pr_closes` behavior unchanged for full-scope runs.

### UPDATED: python/larch/review/review_dispatch_panel.py

Inject the forced plan-fidelity reviewer when persisted coverage requires it.

Emit manifest rows with `prune_exempt=true`.

Ensure every Step 5 round includes it, even on TRIVIAL or Cursor-absent panels.

Choose an available external tool from the plan-fidelity source instead of depending on Cursor alone.

### UPDATED: python/larch/review/review_prune.py

In `reviewer_prune_filter`, skip productivity pruning for manifest rows with `prune_exempt=true` before `net_prunable` and `floor_prunable` checks.

Keep ordinary reviewers and the existing additive plan-fidelity lane subject to current rules unless already exempt.

### UPDATED: python/larch/state/finalize.py

Suppress `[DONE]` tracking issue rename when disposition is `proceed-partial`.

Keep stalled rename behavior unchanged.

### UPDATED: python/larch/report/final_report.py

Read disposition and coverage artifacts.

Pass a `plan_coverage_line` and bounded `todos_left` detail into the run-summary renderer.

Ensure the final summary carries the line even on `proceed-partial` success.

### UPDATED: python/larch/report/run_log_batch.py

Add a `scope-disposition` batch with a simple JSON replace payload.

Include the coverage fingerprint, disposition, follow-up issue reference, and bounded `todos_left` summary.

Prefer JSON for machine consumption.

### UPDATED: docs/workflow-lifecycle.md

Document:

- Step 2 coverage bands
- post-dispatch disposition timing on external-complete paths
- operator disposition choices
- `todos_left` as an independent trigger
- fingerprint invalidation after Step 5 / Step 7 / checks-repair edits
- the forced plan-fidelity reviewer and `prune_exempt=true`
- ship-pre-driver, route-exit `halt-scope-disposition`, and direct-mutation hard gates
- `Part of #N` and `[DONE]` suppression on partial scope
- self-review behavior when forced review is active

### UPDATED: docs/issue-anchored-plan.md

Clarify that firm-heading coverage uses the Step 0 materialized plan.

Clarify that `### MAY_UPDATE:` stays excluded from this gate.

### UPDATED: docs/run-logs.md

Document the new scope-disposition run-log batch and final-summary plan-coverage projection.

### UPDATED: docs/review-agents.md

Document that the plan-fidelity finder is forced and prune-exempt via `prune_exempt=true` when the middle plan-coverage band trips.

Document that degraded or Cursor-absent panels still include the forced row.

### UPDATED: python/tests/implement/test_implement_dispatch.py

Add tests for:

- middle band emits `PLAN_FIDELITY_FORCED`
- high band emits disposition required
- `todos_left` emits disposition required even with complete file coverage
- `MAY_UPDATE` remains excluded
- below-middle behavior remains advisory when coverage is valid
- the 61-untouched-of-85 case requires disposition
- post-dispatch ordering: disposition not recorded before `POST_DISPATCH_NEXT=continue`
- ship pre-driver refuses when disposition is required but missing or stale
- ship pre-driver proceeds when `proceed-partial` is recorded and fingerprint matches
- stale-fingerprint test after committed edits before ship
- route-exit maps `needs_user_reason=scope-disposition` to `NEXT_ACTION=halt-scope-disposition`
- commit-route / claude_fallback fence runs shared coverage before Step 3

### UPDATED: python/tests/review/test_review_pipeline.py

Add or extend tests proving forced plan-fidelity appears in every Step 5 round across tiers.

Assert `prune_exempt=true` rows remain present after `reviewer_prune_filter`.

Include a TRIVIAL or Cursor-unavailable panel case.

### UPDATED: python/tests/git/test_pr_body.py


- `Part of #N` replaces closing keyword on partial scope
- deferred inventory section renders
- existing PR update through disposition-aware path does not reinsert `Closes #N`
- full-scope runs still use `Closes #N`

### UPDATED: python/tests/git/test_pr.py

Add a direct-mutation test where `PR_NUMBER` is already set and disposition is required but missing.

Verify `ensure_pr` / body-update paths fail closed before `gh` mutation.

### UPDATED: python/tests/state/test_finalize.py

Add tests that `proceed-partial` suppresses `[DONE]` rename.

Keep stalled and normal done paths unchanged.

### UPDATED: python/tests/report/test_final_report.py

Add tests for the plan-coverage line in final summary, including `todos_left` count.

### UPDATED: python/tests/implement/test_implement_self_review.py

Add a test that forced plan-fidelity runs inline on self-review, or that self-review is blocked while `PLAN_FIDELITY_FORCED=true`.

### MAY_UPDATE: skills/implement/scripts/test-implement-fence-shape.sh

Only update if SKILL.md Bash fence shape changes.

If updated, adjust `EXPECTED_OLD` / `EXPECTED_NEW`.

## Edge cases

- Empty firm-heading list: no gate; keep advisory behavior.
- `todos_left` with non-string entries: count entries, render only safe bounded string forms.
- Plan read failure or git probe failure on a required-disposition path: fail closed or require re-prompt, never advisory.
- External complete path: disposition waits for successful post-dispatch branch verification.
- Existing PR on resume: update footer from `Closes` to `Part of` if disposition is partial.
- Follow-up issue filing or dependency write fails: do not record `proceed-partial`; keep the run parked or route to `bail-rescope`.
- `bail-rescope`: do not create a PR.
- Repo unavailable or forked dry-run: fail closed for required disposition unless the existing flow cannot publish, then record a local-only disposition and surface it in final summary.
- Self-review with `PLAN_FIDELITY_FORCED=true`: run the inline bounded plan-fidelity pass or block the flow per `self-review.md`.
- Later edits after disposition: recompute coverage from live git delta, invalidate stale disposition, and require a fresh operator choice before ship.

## Failure modes

- **Disposition before post-dispatch**: external-complete path defers prompt/recording until `POST_DISPATCH_NEXT=continue`.
- **Artifact tampering**: ship and PR mutation paths recompute live coverage and reject fingerprint mismatch.
- **Dropped `todos_left`**: Step 2 writes `todos_left` into the coverage artifact before sanitizing manifest output.
- **Reviewer pruning removes finder**: forced slot carries `prune_exempt=true` with unit coverage in `reviewer_prune_filter`.
- **Closing keyword leak**: create and update both route through disposition-aware linker helpers in `tracking_issue.py` / `pr_body.py`.
- **Silent `[DONE]` rename**: finalize reads the disposition artifact directly and skips done rename on partial scope.
- **Route-exit fallthrough**: missing/stale disposition maps to `halt-scope-disposition`, not operator bail.
- **Premature proceed-partial durability**: disposition and run-log batch are written only after issue create and block relation succeed.
- **Coverage read/parse failure**: complete-path scope stays fail-closed until the plan can be reread or disposition can be recorded.

## Testing strategy

Run focused tests only for changed files first:

- `python3 -m pytest python/tests/implement/test_scope_disposition.py python/tests/implement/test_implement_dispatch.py`
- `python3 -m pytest python/tests/review/test_review_pipeline.py`
- `python3 -m pytest python/tests/git/test_pr_body.py python/tests/git/test_pr.py`
- `python3 -m pytest python/tests/state/test_finalize.py`
- `python3 -m pytest python/tests/report/test_final_report.py`
- `python3 -m pytest python/tests/implement/test_implement_self_review.py`

Then run required aggregates:

- `make py-lint`
- `make py-test`
- affected `test-harnesses` shards, including `scripts/test-implement-fence-shape.sh` if SKILL.md fence shape changes

## Acceptance mapping

1. 61 untouched of 85 firm headings plus non-empty `todos_left` cannot reach PR without disposition.
   - Covered by Step 2 compute, post-dispatch prompt ordering, pre-Step-3 recompute, and pre-driver/direct-mutation tests.

2. `proceed-partial` PR body uses `Part of`, suppresses `[DONE]`, and final summary has plan coverage plus `todos_left`.
   - Covered by `tracking_issue.py`, PR body, finalize, and final-report tests.

3. Forced plan-fidelity finder appears every Step 5 round, carries `prune_exempt=true`, and survives pruning, including degraded and Cursor-absent panels.
   - Covered by dispatch-panel and `reviewer_prune_filter` tests, plus the self-review forced-pass test.

4. Thresholds live in config with comments, and docs explain disposition timing, fingerprint invalidation, and re-prompt semantics.
   - Covered by config review and docs updates.

5. Ship and direct PR mutation paths fail closed on missing, stale, or invalid disposition artifacts and route-exit returns `halt-scope-disposition`.
   - Covered by ship pre-driver, route-exit, `test_pr.py` direct-mutation, and `test_scope_disposition.py` durability tests.

## Acceptance

Run focused tests only for changed files first:

- `python3 -m pytest python/tests/implement/test_scope_disposition.py python/tests/implement/test_implement_dispatch.py`
- `python3 -m pytest python/tests/review/test_review_pipeline.py`
- `python3 -m pytest python/tests/git/test_pr_body.py python/tests/git/test_pr.py`
- `python3 -m pytest python/tests/state/test_finalize.py`
- `python3 -m pytest python/tests/report/test_final_report.py`
- `python3 -m pytest python/tests/implement/test_implement_self_review.py`

Then run required aggregates:

- `make py-lint`
- `make py-test`
- affected `test-harnesses` shards, including `scripts/test-implement-fence-shape.sh` if SKILL.md fence shape changes

diff_added: 1540
diff_deleted: 175
mechanical_churn: false
oversize_override: operator
diff_lines: 1715

## Test plan
(no test plan section in plan-file)
