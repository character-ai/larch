# Review Round 4

- Mode: `diff`
- 10 accepted, 5 rejected (3 neutral)

## Accepted Findings

### FINDING_1: Gate-B dedup Makefile retarget lacks pytest coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-plan-cli-contracts-output.txt
- **Severity**: important
- **Concern**: `Makefile` retargets `test-gate-b-dedup-plan` to `pytest python/test_plan_review.py`, but that file has no `plan-review gate-b-dedup` tests. The retired harness covered fail-closed contracts (`--dedup` without prior `--snapshot-trailers` exits 3, optional-trailer preservation, snapshot value rejection, plan restore on dedup failure). CI can stay green while Gate B resume CLI contract drift ships undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add pytest cases or restore harnesses so each make target exercises its named behavior
  - From dyn-plan-cli-contracts-output.txt: Port the deleted harness cases into `python/test_plan_review.py` (snapshot, dedup-without-snapshot rc=3, trailer preservation, reject new trailers, restore-on-failure) and assert the same stdout/exit behavior through `python3 python/cli.py plan-review gate-b-dedup`.


### FINDING_10: `PlanReviewError` from materialization is uncaught in `cli.py` main
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `PlanReviewError` from `_materialize_legacy_root()` is uncaught in `cli` `main()`. Materialization failure yields a Python traceback instead of normalized Step 3 KVs; orchestrator may mis-route.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Catch PlanReviewError in plan_review entrypoints; emit contract KVs or stable stderr and a documented exit code.


### FINDING_13: `design-postplan-emit.sh` drift-baseline write is now fatal under `set -e`
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `_postplan_snapshot_drift_baseline` no longer ignores drift-baseline write failures. The old sourced helper was called with `|| true`, but the new `plan-review drift-baseline write-once` runs under `set -e`, so a corrupt `drift-baseline.env` directory, permission error, or invalid count can abort postplan emit instead of continuing with a warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Restore the non-fatal contract here, for example append `|| true` or make this call capture failure and emit the existing warning path without aborting.


### FINDING_14: Stdout overlay for loop envelope skipped on env-read failure
- **Reviewer(s)**: dyn-plan-cli-contracts-output.txt
- **Severity**: important
- **Concern**: The stdout overlay for `STEP3_REVIEW_LOOP_STATUS`, `POSTPLAN_RC`, `DEDUP_RC`, and `FINAL_ROUND_NUM` was moved inside the `read-result-env.sh` success branch. On `_rre_rc != 0`, the wrapper hard-sets `panel-failed` and never reads those keys from captured `plan-review run` stdout. Before the cutover, the overlay loop ran unconditionally after the if/else, so a valid loop envelope on stdout could still be recovered when the primary `.step3-review-result.env` was unreadable (for example a corrupt regular file). That can mis-route `/design` Step 3 resume/Gate B on degraded env-read paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plan-cli-contracts-output.txt: After the failure branch, still run the narrow stdout overlay (or re-invoke `read-result-env.sh` with stdout-only input) before defaulting to `panel-failed`, matching the pre-cutover contract; add an orchestrator-fence case where `_rre_rc != 0` and stdout carries `STEP3_REVIEW_LOOP_STATUS=main-agent-vote-required`.


### FINDING_15: Tally-error test omits `STEP3_REVIEW_LOOP_STATUS` orchestrator routing assertion
- **Reviewer(s)**: dyn-plan-cli-contracts-output.txt
- **Severity**: important
- **Concern**: `test_tally_error_rollback_review_round_count` stubs the inner loop with `LOOP_STATUS=complete` plus `TALLY_PLAN_REVIEW_STATUS=tally-error`, does not pass `--mode loop`, and never asserts `STEP3_REVIEW_LOOP_STATUS=tally-error` in `.step3-review-result.env` or wrapper output. Production Step 3 always calls `plan-review run --mode loop` via `design-step3-review.sh`, and the orchestrator routes on `STEP3_REVIEW_LOOP_STATUS` first. The test only proves round-count rollback and stdout tally KV, so a regression that omits `STEP3_REVIEW_LOOP_STATUS` on tally-error would still pass CI and could send the orchestrator down the Gate B path instead of the Gate B bypass path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plan-cli-contracts-output.txt: Add a `--mode loop` integration test (or extend `test-step3-orchestrator-fence.sh`) that stubs a tally-error loop envelope with `STEP3_REVIEW_LOOP_STATUS=tally-error` and asserts wrapper output plus `.step3-review-result.env` contain both `STEP3_REVIEW_LOOP_STATUS=tally-error` and `LOOP_STATUS=tally-error`.


### FINDING_16: `lint-retired-scripts` gives false clean signal for embedded legacy assets
- **Reviewer(s)**: dyn-retired-path-sweep-output.txt
- **Severity**: important
- **Concern**: `make lint-retired-scripts` reports `RETIRED_REFS=0` even though retired script identities remain in-repo via `_p("skills", "design", "scripts", "emit-plan.sh")` tuple literals and gzip assets. The linter only matches contiguous full repo-relative paths; split `_p()` paths evade detection. That gives a false "stale-reference sweep passed" signal while operational dependence on retired script bodies persists inside `plan_review.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retired-path-sweep-output.txt: Extend `migration_lint.py` (or add a sibling check) to flag `_LEGACY_ASSETS` / `_run_legacy` call sites for manifest-listed scripts, or require regenerated embedded assets to be excluded from the manifest with an explicit allowlist entry and a comment contract.


### FINDING_19: Publish deny-list incomplete for escalation-evidence artifacts
- **Reviewer(s)**: dyn-artifact-security-output.txt
- **Severity**: important
- **Concern**: `design-log-publish.sh` adds `step3-record-escalation-*.stdout.log`, `step3-record-escalation-*.stderr.log`, and `design-failure-escalation-*.tsv` to `design_artifact_excluded`, but sibling artifacts from the same `step3_record_report_evidence` → `stall-recovery-report.sh record-escalation` path remain publish-eligible: `design-failure-escalation-record-failure.env` (can carry operator-facing `REASON=…` text) and `.step3-report-<status>.recorded` sentinels (basename exposes which escalation trigger fired). The new exclusions are therefore incomplete for the escalation-evidence surface this migration moved into Python.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-security-output.txt: Extend `design_artifact_excluded` to cover the full `design-failure-escalation-*` family used by generic profile (`design-failure-escalation-record-failure.env`, and any other `design-failure-*` stall-recovery artifacts written under `$DESIGN_TMPDIR`), plus `.step3-report-*.recorded` sentinels from `step3_record_report_evidence`; add a `test-design-log-publish.sh` assertion that these basenames never reach `larch-logs/design/<RUN_ID>/`.
  - From dyn-artifact-security-output.txt: Add `.step3-report-*.recorded` to `design_artifact_excluded`, or stop creating publish-visible sentinels under the design tmpdir root.


### FINDING_2: Panel and voter dispatch pytest coverage is trivial versus deleted harnesses
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Deleted `test-dispatch-plan-review-panel.sh` and `test-dispatch-plan-voters.sh` harnesses (1100+ lines) were replaced by minimal usage/help pytest checks. Regressions in static slot matrix, scout dynamic rows, Claude fallback, pruned-empty handling, or voter KV order can merge without CI failure because `test-dispatch-plan-voters` and `test-dispatch-plan-review-panel` now run an almost empty pytest module while Makefile and docs still claim full waterfall/matrix coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port retired dispatch-plan-review-panel and dispatch-plan-voters harness scenarios into pytest
  - From cursor-specialist-testing-output.txt: Port deleted test-dispatch-plan-voters.sh and test-dispatch-plan-review-panel.sh scenarios into python/test_plan_review_panel.py with PATH stubs and KV assertions.


### FINDING_5: No pytest for degraded-empty-collector review-round-count rollback
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: No pytest covers degraded-empty-collector review-round-count rollback. Count may not roll back after degraded-empty-collector rounds, breaking cap semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add stub-based test mirroring tally-error rollback case


### FINDING_6: Plan-review domain remains gzip-embedded bash shim, not native Python port
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-generic-output.txt, dyn-retired-path-sweep-output.txt
- **Severity**: important
- **Concern**: The C3a1 cutover deletes plan-review bash from the tree, but core CLI verbs (`emit`, `finalize`, `preview`, `gate-b-dedup`, `step3-state`, `tally`, `run`, etc.) still delegate through `_run_legacy()` / `_materialize_legacy_root()`, which gunzips embedded copies of retired scripts into a temp `CLAUDE_PLUGIN_ROOT` and executes them. `python/plan_review_panel.py` does the same for panel/voter dispatch. Wrappers and docs point at `python/cli.py plan-review …`, but runtime behavior is still absorbed bash, not the native Python port the plan describes. Future fixes require opaque blob edits; import callers cannot exercise or patch real Python tally, loop, or dispatch logic; `SKILL.md` claims `python/plan_review.py` owns the loop while execution stays in opaque blobs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Complete native port or document and track façade as explicit follow-up issue
  - From cursor-specialist-edge-cases-output.txt: Complete the in-process port per plan, or document delegation everywhere and add tooling to regenerate _LEGACY_ASSETS from reviewable sources.
  - From codex-generic-output.txt: Replace the embedded legacy assets and `_run_legacy` verb bodies with native Python implementations, or keep the shell scripts undeleted until the real port lands.
  - From dyn-retired-path-sweep-output.txt: Either finish the native port (move loop/tally/dispatch logic into `plan_review.py` / `plan_review_panel.py` and delete `_LEGACY_ASSETS`), or document this as an intentional compatibility shim and add a regeneration workflow for the embedded blobs so maintainers do not edit deleted paths by mistake.


