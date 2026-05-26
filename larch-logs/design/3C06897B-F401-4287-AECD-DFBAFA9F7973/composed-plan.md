## Plan

Implement `phase_plan_materialize` in `scripts/implement-bootstrap.sh` (Phase 3 of umbrella #2732). Absorbs current Step 0 SKILL.md calls #10–#16 plus the `snapshot-untracked.sh` baseline write currently between #9 and #10, plus the post-bootstrap token/timing marks at L658–673 for plan-materialization. After this lands, `skills/implement/SKILL.md` Step 0 collapses to a single Bash `implement-bootstrap.sh --up-to-phase plan` call covering #1–#16, leaving only the implementer waterfall as separate prompt-side prose.

### Phase-skip semantics

Introduces a new permissive predicate `should_run_phase_plan_materialize` (sits next to `should_run_post_tracking_phase`):

```sh
should_run_phase_plan_materialize() {
    [ -z "${IMPLEMENT_BAIL_REASON:-}" ] \
        && [ "${STALL_TRACKING:-false}" != "true" ] \
        && [ "${REPO_UNAVAILABLE:-false}" != "true" ]
}
```

Allows `DEFERRED=true` (FORKED_TARGET-skip, POSTED=false-deferred) so Step 2 dispatch still gets `feature-description.txt` + `plan.txt` materialized on those paths. Only hard bails (closed/PR/init-failed/STALL_TRACKING/REPO_UNAVAILABLE) skip the phase entirely. `phase_coder_select` (Phase 4) keeps the stricter `should_run_post_tracking_phase`.

`main()` dispatch updates:

```sh
plan)
    phase_tracking
    if should_run_phase_plan_materialize; then phase_plan_materialize; fi
    ;;
coder|all)
    phase_tracking
    if should_run_phase_plan_materialize; then phase_plan_materialize; fi
    if should_run_post_tracking_phase; then phase_coder_select; fi
    ;;
```

### Files to modify

#### UPDATED: `scripts/implement-bootstrap.sh`

- File-top globals: `BRANCH_NAME=""`, `BRANCH_ACTION=""`, `PLAN_FILE=""`, `PREFLIGHT_TMPDIR_OPT=""`.
- New `--preflight-tmpdir <path>` argv flag; validated as required when `--up-to-phase ∈ {plan, coder, all}` together with `--issue-number`.
- New `should_run_phase_plan_materialize` predicate.
- Replace `phase_plan_materialize` stub (lines ~513–516) with the function body below. Order matches current SKILL.md L645–810 byte-for-byte (sanitized goal text, byte-identical slug pipeline):
  1. `snapshot-untracked.sh --output … --nul` (best-effort, always exit 0).
  2. `token-ledger.sh mark` + `timing-ledger.sh mark "implement Step 0 — plan materialization"` (absorbed from SKILL.md L658–673).
  3. `cp "$PREFLIGHT_TMPDIR_OPT/plan-from-issue.txt" "$IMPLEMENT_TMPDIR/plan.txt"` → on failure: `STEP_FAILED=copy-plan` + `exit 2`. Set `PLAN_FILE`.
  4. `gh issue view "$gh_issue_arg" [--repo "$UPSTREAM_REPO_OPT"] --json title,body --template "{{.title}}\n\n{{.body}}"` (use `ISSUE_NUMBER_OPT` + `--repo` when `FORKED_TARGET=true`; else `ISSUE_NUMBER_RESOLVED`, no `--repo`). On non-zero: `STEP_FAILED=gh-issue-view` + `exit 2`.
  5. `timing-ledger.sh workflow-path "HARD"` (best-effort).
  6. `persist-implement-run-flags.sh --implement-tmpdir … --no-issues false --workflow-path HARD` → on **any** non-zero (not only exit 2): `STALL_TRACKING=true`, `IMPLEMENT_BAIL_REASON=run-flags-persist-failed`, `return 0`.
  7. `check-mid-run-dirty-tree.sh --mode checkpoint` → on `STATUS=dirty` OR `STATUS=unknown`: `IMPLEMENT_BAIL_REASON=dirty-tree`, `return 0` (no STALL — orchestrator routes to recovery `AskUserQuestion`).
  8. Conditional slug + create-branch (skip when `FORKED_TARGET=true` OR `IS_USER_BRANCH=true`). Byte-identical `tr | sed | cut` pipeline from current SKILL.md L757–761. On any non-zero from `create-branch.sh --branch`: `STALL_TRACKING=true`, `IMPLEMENT_BAIL_REASON=branch-create-failed`, `return 0`. Captures `BRANCH_ACTION` from `create-branch` stdout.
  9. `git-current-branch.sh` (ALWAYS runs, even on skip) → `BRANCH_NAME`.
  10. Compose sanitized goal text (`redact-secrets.sh` | `redact-tmpdir-paths.sh`), then `run-step1-plan-log.sh --implement-tmpdir … --goal-text "$goal_text"` (best-effort, log non-zero via `append-tool-failure.sh`).
  11. Compose sanitized `plan-review-tally-body.md` (`redact-secrets.sh` | `redact-tmpdir-paths.sh`), then `write-tally.sh --log-root … --skill implement --run-id "$RUN_ID" --phase plan-review --mode hard --rounds 0 --accepted 0 --rejected 0 --body-file …` (best-effort).
  12. When `FORKED_TARGET != true` AND `ISSUE_NUMBER_RESOLVED` non-empty: compose sanitized `larch-plan-summary.md`, then `tracking-issue-summary.sh upsert-summary --issue "$ISSUE_NUMBER_RESOLVED" --marker "<!-- larch:plan v1 runid=$RUN_ID -->" --content-file …` (best-effort).
  13. New helper `emit_plan_materialize_breadcrumbs_if_enabled` (mirrors `emit_tracking_breadcrumb_if_enabled`): only emits when `larch_quiet_truthy "${LARCH_QUIET_BREADCRUMBS:-}"`. Emits:
      - `→ step0: branch $BRANCH_NAME + plan logged`
      - `→ step0: larch:plan posted`
  14. `return 0`.
- `emit_final_tail` update: in the umbrella key block, populate `BRANCH_NAME` / `BRANCH_ACTION` / `PLAN_FILE` from the globals (replacing the existing empty `BRANCH_NAME` placeholder; insert `BRANCH_ACTION` immediately after `BRANCH_NAME`; insert `PLAN_FILE` after `BRANCH_ACTION`).

#### UPDATED: `scripts/implement-bootstrap.md`

- argv table: add `--preflight-tmpdir` row, required when `--up-to-phase ∈ {plan, coder, all}`.
- Bail reasons table: append `run-flags-persist-failed`, `dirty-tree`, `branch-create-failed` rows.
- Exit codes table: append `STEP_FAILED=copy-plan` and `STEP_FAILED=gh-issue-view` rows.
- Behavior mapping table: add rows for snapshot-untracked, gh-issue-view-compose (#10), persist-run-flags (#11), dirty-tree checkpoint (#12), slug + create-branch (#13), git-current-branch (#14), run-step1-plan-log + write-tally plan-review-tally (#15), tracking-issue-summary upsert larch:plan (#16); also the absorbed post-bootstrap token/timing marks.
- Outputs / stdout (KV) prose: `phase_plan_materialize` populates `BRANCH_NAME`, `BRANCH_ACTION`, `PLAN_FILE`. Phase 4 keys remain empty.
- Breadcrumbs section: replace "Future phases" sentence with the two new breadcrumbs and note they require `LARCH_QUIET_BREADCRUMBS` truthy.
- New "Phase-skip semantics" section documenting the permissive `should_run_phase_plan_materialize` vs strict `should_run_post_tracking_phase` (Phase 4) split.

#### UPDATED: `skills/implement/scripts/test-implement-bootstrap.sh`

- Extend `build_sandbox` with `$SANDBOX/bin/` directory containing a `gh` stub (configurable via `SANDBOX_GH_EXIT`, `SANDBOX_GH_TITLE`, `SANDBOX_GH_BODY`); `run_bootstrap` prepends `$SANDBOX/bin` to `PATH`.
- Add stubs for `snapshot-untracked.sh`, `persist-implement-run-flags.sh` (configurable `SANDBOX_PERSIST_FLAGS_EXIT`), `check-mid-run-dirty-tree.sh` (configurable `SANDBOX_DIRTY_STATUS`), `git-current-branch.sh` (reads `last-created-branch.txt`), `run-step1-plan-log.sh`, `write-tally.sh`, `tracking-issue-summary.sh`, `redact-secrets.sh` (identity pipe), `redact-tmpdir-paths.sh` (identity pipe).
- Extend `create-branch.sh` stub to handle `--branch <name>` (configurable `SANDBOX_CREATE_BRANCH_EXIT`); on success persist the requested branch to `last-created-branch.txt` so `git-current-branch.sh` reflects it.
- New B-cases (Phase 3-specific, suffixed `-plan` to avoid collision with existing B6/B7):
  - **B5-plan-green** — Branch 2 adoption + all sub-helpers succeed; 3 parameterized title iterations exercising slug pipeline (uppercase, special chars, 40+ chars); asserts `BRANCH_NAME` reflects the derived slug via the create-branch→git-current-branch chain; asserts ordered invoke-log sequence (snapshot, gh, persist, dirty, create-branch, git-current-branch, run-step1-plan-log, write-tally, tracking-issue-summary).
  - **B6-plan-flags** — `persist-implement-run-flags` non-zero (2 sub-iter: rc=2 and rc=1); asserts `run-flags-persist-failed` + STALL + no subsequent helpers.
  - **B7-plan-dirty-tree** — `check-mid-run-dirty-tree STATUS=dirty` and parameterized `STATUS=unknown`; asserts `dirty-tree` bail + no STALL + no subsequent helpers.
  - **B8-plan-forked-target** — `--forked-target true --upstream-repo upstream/repo --issue-number 123 --preflight-tmpdir <populated>`; phase entry permitted; asserts `BRANCH_SELECTED=forked-target-skip`, `DEFERRED=true`, `PLAN_FILE` populated, `BRANCH_NAME` populated (from git-current-branch), `BRANCH_ACTION=` empty, no `create-branch --branch`, no `tracking-issue-summary upsert-summary`.
  - **B9-plan-user-branch** — `SANDBOX_IS_USER_BRANCH=true`; asserts no `create-branch --branch` but `tracking-issue-summary` is invoked.
  - **B10-plan-missing-preflight-tmpdir** — die_usage on missing flag when `--up-to-phase plan`.
  - **B11-plan-copy-plan-failure** — `--preflight-tmpdir` without `plan-from-issue.txt`; asserts exit 2 + `STEP_FAILED=copy-plan`.
  - **B12-plan-gh-issue-view-failure** — `SANDBOX_GH_EXIT=1`; asserts exit 2 + `STEP_FAILED=gh-issue-view`.
- Extend existing B2-plan / B4-plan with 6 new `assert_not_contains` lines (3 new bail reasons × 2 cases) verifying F7 guard prevents Phase 3 bail overwrite on hard tracking bails.

#### UPDATED: `skills/implement/SKILL.md`

- Step 0 invocation (~L336): change `--up-to-phase tracking` to `--up-to-phase plan`; append `--preflight-tmpdir "$PREFLIGHT_TMPDIR"` to `_ib_args` array.
- KV parsing (~L363–417, `_ib_kv_scan`): add explicit case arms for `BRANCH_NAME=*`, `BRANCH_ACTION=*`, `PLAN_FILE=*` so they propagate; update parsed-keys prose at L294; update prose from "calls #1–#9" to "calls #1–#16".
- Exit-2 wrapper handler (~L298–304 / L339–361): add explicit branches for `STEP_FAILED=copy-plan` (surface `copy-plan.stderr.log`) and `STEP_FAILED=gh-issue-view` (surface `gh-issue-view.stderr.log`).
- `dirty-tree` routing (~L420 area): when `IMPLEMENT_BAIL_REASON=dirty-tree`, fire the existing dirty-tree recovery `AskUserQuestion`; idempotency sentinel `$IMPLEMENT_TMPDIR/.dirty-tree-prompted-step0-plan-materialize`.
- Remove the now-redundant prompt-side blocks: snapshot-untracked (~L645–650); "Copy plan + feature description + persist implement run flags" (~L686–728); "Dirty-tree checkpoint (post-persist)" (~L730 area); "Create feature branch" (~L734–780); "Capture branch name (BRANCH_NAME)" (~L780–790); "Larch-log batches — plan-goals-test + plan-review-tally" (~L783–795); post-bootstrap token/timing marks for plan-materialization (~L658–673); redundant second `create-branch.sh --check` (~L675–685).
- Anti-halt continuation reminder: update all 3+ occurrences of `implement-bootstrap.sh --up-to-phase tracking` to `--up-to-phase plan` (L12, L14, L294, L336).
- Preserve Implementer waterfall and Rebase-onto-main sections as-is.

## Acceptance

- All Phase 3 harness cases pass via `make test-implement-bootstrap`.
- `/implement <open-issue>` transcript shows a single Bash bootstrap call covering #1–#16 (down from the historical 16 separate calls); only the implementer waterfall remains as separate prompt-side prose.
- B5-plan-green's three slug iterations all assert correct `BRANCH_NAME=testuser/<slug>-N` with the byte-identical `tr | sed | cut` pipeline (uppercase, special chars, 40+ char title each covered).
- B8-plan-forked-target proves `feature-description.txt` and `plan.txt` materialize on forked-target paths (Step 2 dispatch requirement satisfied).
- B11-plan-copy-plan-failure and B12-plan-gh-issue-view-failure cover the two new `STEP_FAILED` exit-2 paths.
- B6-plan-flags covers persist-run-flags failure on any non-zero (not only rc=2).
- Existing B2-plan / B4-plan assertions confirm no Phase 3 bail reason overwrites hard tracking bails (F7 guard regression-protected).
- Manual smoke run confirms the KV tail includes `BRANCH_NAME=…`, `BRANCH_ACTION=created`, `PLAN_FILE=$IMPLEMENT_TMPDIR/plan.txt` and that both `larch-logs/implement/<RUN_ID>/plan-goals-test.md` and `plan-review-tally.json` exist.
- `make lint` (bash 3.2 portability + pre-commit hooks) passes.

diff_lines: 620
