# Review Round 5

- Mode: `diff`
- 18 accepted, 2 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Step 3 records panel-failed escalation before stdout recovery
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-plan-cli-contracts-output.txt
- **Severity**: important
- **Concern**: On `read-result-env.sh` failure, `design-step3-review.sh` records `panel-failed` escalation evidence (via `step3_record_report_evidence`, with failures swallowed by `|| true`) before the stdout overlay can recover the true `STEP3_REVIEW_LOOP_STATUS`. When the result env is missing or unparseable but captured `plan-review run` stdout carries a valid bail-out envelope (e.g. `main-agent-vote-required`), the wrapper still writes `.step3-report-panel-failed.recorded` and a `design-failure-escalation-ledger.tsv` row, then overwrites handoff KVs to the recovered status. `/design` can route to the wrong Step 3 branch while carrying bogus degradation evidence; a failed evidence record may leave no ledger row at all.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Remove || true; surface non-zero exit or append to execution-issues.md.
  - From cursor-specialist-edge-cases-output.txt: Record escalation after stdout overlay and final status normalization using the resolved STEP3_REVIEW_LOOP_STATUS; skip recording when recovery shows a non-degradation status.
  - From dyn-plan-cli-contracts-output.txt: Move `--record-report-evidence` to after the stdout overlay and the final `STEP3_REVIEW_LOOP_STATUS` / `LOOP_STATUS` normalization, and record only the terminal status you are about to emit. Alternatively, skip the failure-path `panel-failed` record entirely when stdout contains a recognized loop envelope.


### FINDING_10: skills/design/SKILL.md still points at deleted plan-review contract docs
- **Reviewer(s)**: dyn-retired-path-sweep-output.txt
- **Severity**: important
- **Concern**: Step 3 prose (line 564) and wrapper inventory (lines 938–941) still point readers at deleted sibling contracts (`plan-review-loop.md`, `emit-plan.md`, `tally-plan-review.md`) even though the loop owner was retargeted to `python/plan_review.py`. `make lint-retired-scripts` does not flag bare basenames, so CI stays green while the normative `/design` entrypoint references files that no longer exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retired-path-sweep-output.txt: Replace those `plan-review-loop.md` pointers with `python/plan_review.py` / `python/test_plan_review.py` (or a new contract doc if you want one), and sweep the same pattern on lines 938 and 941 (`emit-plan.md`, `tally-plan-review.md`).
  - From dyn-retired-path-sweep-output.txt: Retarget those bullets to `python/plan_review.py` and `python/test_plan_review.py`, matching the C3a1 decision-log wording in `docs/python-migration.md`.


### FINDING_11: design-step3-review.md still references deleted run-step3-review.sh
- **Reviewer(s)**: dyn-retired-path-sweep-output.txt
- **Severity**: important
- **Concern**: The wrapper contract still says `--starting-round` is forwarded to `run-step3-review.sh --mode loop`, but the live wrapper calls `python3 …/cli.py plan-review run`. Anyone debugging mid-loop resume from the sibling doc will chase a deleted script.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retired-path-sweep-output.txt: Update the invariant to `plan-review run --mode loop` and note the Python contract in `python/plan_review.py`.


### FINDING_12: test-design-multi-round-integration.md partially updated for C3a1
- **Reviewer(s)**: dyn-retired-path-sweep-output.txt
- **Severity**: important
- **Concern**: The harness doc was only partly updated: the stub pointer now cites `python/test_plan_review.py`, but the intro and coverage bullets still describe `plan-review-loop.sh`, `design-step3-state.sh`, and `run-step3-review.sh --no-preview` as the live chain. That mismatches the harness, which now drives `python3 python/cli.py plan-review run`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retired-path-sweep-output.txt: Rewrite the intro/coverage bullets to name `plan-review run`, `plan-review step3-state`, and `plan-review-continuation.sh`, and drop retired script names.


### FINDING_13: lib-plan-optional-trailers.md lists retired callers/harnesses
- **Reviewer(s)**: dyn-retired-path-sweep-output.txt
- **Severity**: important
- **Concern**: Callers/harnesses still list retired surfaces (`plan-review-loop.sh`, `gate-b-dedup-plan.sh`, `test-gate-b-dedup-plan.sh`, `test-check-plan-size.sh`). After C3a1 those paths are gone; this doc is still a maintainer authority for trailer semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retired-path-sweep-output.txt: Retarget callers to `python/plan_review.py`, `python/cli.py plan-review gate-b-dedup`, `python/test_plan_review.py`, and `python/test_plan_quality.py`.


### FINDING_14: check-plan-size.md has partial stale-reference sweep
- **Reviewer(s)**: dyn-retired-path-sweep-output.txt
- **Severity**: important
- **Concern**: Line 15 was updated to cite `plan-review emit`, but the same section still says "`emit-plan.sh` grammar" / "`emit-plan.sh` would refuse"; lines 41, 89, and 93 still name `emit-plan.sh`, `test-emit-plan.sh`, and `plan-review-loop.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retired-path-sweep-output.txt: Finish the sweep so every runtime/harness reference points at `plan-review emit`, `python/test_plan_review.py`, and `python/plan_review.py` / `design-postplan-emit.sh`.


### FINDING_15: voting-protocol.md still documents tally-plan-review.sh in three places
- **Reviewer(s)**: dyn-retired-path-sweep-output.txt
- **Severity**: important
- **Concern**: Voter dispatch paths were updated to `plan-review voter-dispatch`, but `/design` tally authority is still documented as `tally-plan-review.sh` in three places (lines 11, 226, 266). That script is retired; tally now goes through `python/cli.py plan-review tally` / `python/plan_review.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retired-path-sweep-output.txt: Replace `tally-plan-review.sh` with `python/cli.py plan-review tally` (and `python/voting.py` where shared semantics are meant).


### FINDING_16: docs/python-migration.md contradicts itself on drift-baseline status
- **Reviewer(s)**: dyn-retired-path-sweep-output.txt
- **Severity**: important
- **Concern**: The Plan-quality section still says `lib-drift-baseline.sh` remains deferred, but C3a1 retired that script and `design-postplan-emit.sh` now calls `plan-review drift-baseline write-once`. The decision log contradicts itself across sections 136–154.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retired-path-sweep-output.txt: Update line 138 to note drift baseline moved to `plan-review drift-baseline`, and cross-link the C3a1 entry.


### FINDING_17: eval-set.md penalizes correct C3a1 Python citations
- **Reviewer(s)**: dyn-retired-path-sweep-output.txt
- **Severity**: important
- **Concern**: Eval cases `eval-5` and `eval-14` still require keywords `run-step3-review.sh`, `review-design-step3-loop.sh`, and `plan-review-loop.sh`. Those scripts were deleted in this branch, so research scoring will penalize correct answers that cite the new Python surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retired-path-sweep-output.txt: Update `expected_keywords` to `python/cli.py plan-review run`, `python/plan_review.py`, `plan-review voter-dispatch`, and `cursor_available` / fallback semantics.


### FINDING_18: test-design-step3-review.md describes deleted harness chain
- **Reviewer(s)**: dyn-retired-path-sweep-output.txt
- **Severity**: important
- **Concern**: The harness contract still says it exercises `review-design-step3-loop.sh` through `run-step3-review.sh` stubs. The live harness (`test-design-step3-review.sh`) is static checks against `python/plan_review.py` and `plan-review run --record-report-evidence`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retired-path-sweep-output.txt: Rewrite the sibling doc to match the current harness behavior and Python CLI surface.


### FINDING_2: Env-read failure stdout overlay drops most handoff KVs
- **Reviewer(s)**: dyn-plan-cli-contracts-output.txt
- **Severity**: important
- **Concern**: The stdout overlay on env-read failure only replays four keys (`STEP3_REVIEW_LOOP_STATUS`, `POSTPLAN_RC`, `DEDUP_RC`, `FINAL_ROUND_NUM`). `read-result-env.sh` does not use `--fallback-input` when the primary `.step3-review-result.env` is a regular but malformed file. The wrapper therefore drops the rest of the normalized envelope (`TALLY_PLAN_REVIEW_STATUS`, `SCOPE_ANCHOR_FILE`, `REVIEW_ROUND_COUNT`, counts, cap flags, etc.) even when those KVs are present in captured stdout. Step 3 resume, MainAgent re-tally, and Gate B routing can diverge from the loop driver contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plan-cli-contracts-output.txt: On `_rre_rc != 0`, either parse the full allowlisted KV set from `_plan_review_stdout_file` (same allowlist as `read-result-env`) before falling back to `panel-failed`, or teach `read-result-env.sh` to consult `--fallback-input` when the regular primary fails parsing.


### FINDING_20: plan-review preview lacks in-process allowlist validation
- **Reviewer(s)**: dyn-artifact-security-output.txt
- **Severity**: important
- **Concern**: `emit_design_plan_preview()` / `preview_main()` delegate straight to `_run_legacy()` with no in-process `validate_design_tmpdir()` call, while `docs/configuration-and-permissions.md` now states that `python/cli.py plan-review preview` performs allowlist validation. Enforcement depends on the gzip-embedded retired `emit-design-plan-preview.sh`, not reviewable Python. `design-step4b-preview.sh` has no wrapper-level validation either. Deleted shell harnesses that pinned preview allowlist behavior were not replaced with equivalent pytest cases beyond threshold rendering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-security-output.txt: Call `validate_design_tmpdir()` at the top of `emit_design_plan_preview()` (or `preview_main()`) for all variants before `_run_legacy()`, emit the same warning-and-exit-0 diagnostics, and port the disallowed-tmpdir / no-sentinel tests into `python/test_plan_review.py`.


### FINDING_3: Plan-review tally CLI never exercised in pytest
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `make test-tally-plan-review` claims tally vote/OOS/security/scoreboard coverage via `python/test_plan_review.py`, but no test invokes plan-review tally after `test-tally-plan-review.sh` deletion. A tally regression in embedded tally logic can ship with green shard-11 and py-test because the tally CLI is never exercised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port deleted tally harness cases into python/test_plan_review.py (ballot fixtures + voter files + artifact assertions)


### FINDING_4: Plan dedup failure restore coverage missing from pytest
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required dedup failure restore coverage from deleted `test-review-design-step3-loop.sh` is missing; only Gate B dedup tests exist. A `dedup-plan-lines.py` failure during loop post-apply can corrupt `plan.txt` without restore being asserted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add pytest stubbing dedup seam with forced failure and assert plan.txt restored from pre-dedup snapshot


### FINDING_6: Plan-required panel dispatch scenarios untested beyond round-1 happy path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required panel tests are missing: dynamic scout rows, pruned-empty panel, degraded round, waterfall failure, parse-rate `NOT_SUBSTANTIVE`, quota warnings. Panel dispatch contract changes in embedded dispatch logic go untested beyond round-1 happy path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port deleted test-dispatch-plan-review-panel.sh scenarios using waterfall stub and scout JSON fixtures


### FINDING_7: record-round-timing idempotency and round snapshot shape untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required `record-round-timing` idempotency and round snapshot shape tests are absent. No test catches double timing writes or wrong `plan-review/round-N` artifact layout breaking design-log-publish.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add pytest for record-round-timing idempotency and minimal round snapshot file assertions


### FINDING_8: Gate C preview variant/threshold/tmpdir tests not ported from deleted harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-emit-design-plan-preview` documents Gate C variants, invalid threshold, and empty tmpdir cases beyond the single step3 threshold test in pytest. Gate C preview or invalid-tmpdir warn path can regress while test-harnesses-6 stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add documented preview variant/threshold/tmpdir tests or narrow linting.md row


### FINDING_9: plan-review domain is gzip-embedded bash façade, not native Python port
- **Reviewer(s)**: codex-generic-output.txt, dyn-retired-path-sweep-output.txt
- **Severity**: important
- **Concern**: C3a1 acceptance called for importable Python functions and a hard cutover with absorbed bash deleted, but `python/plan_review.py` and `python/plan_review_panel.py` still delegate every verb through `_run_legacy()` / gzip-embedded retired scripts (`EMBEDDED_LEGACY_REFS=27`; `lint-retired-scripts` exits 0). Runtime behavior is a hidden bash compatibility layer, not the native port described in the plan and `docs/python-migration.md` §C3a1. Fixes to advertised Python functions can silently miss actual Step 3 loop, tally, and dispatch paths; blob drift vs live symlinked helpers is an ongoing integration risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Either port the absorbed bodies into native Python functions now, or keep the bash files as explicit legacy runtime sources and do not mark this as the no-shim C3a1 port.
  - From dyn-retired-path-sweep-output.txt: Document the gzip-shim façade explicitly in `docs/python-migration.md` §C3a1 (and regenerate blobs from reviewable sources when behavior changes), or finish the in-process port so `plan_review.py` no longer materializes retired scripts.


