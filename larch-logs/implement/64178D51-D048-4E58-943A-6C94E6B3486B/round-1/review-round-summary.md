# Review Round 1

- Mode: `diff`
- 12 accepted, 2 rejected (2 neutral)

## Accepted Findings

### FINDING_1: plan_review.py is a gzip-embedded Bash relay, not an in-process Python port
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-retired-path-sweep-output.txt
- **Severity**: important
- **Concern**: Core `plan-review` verbs (`emit_plan`, `run_step3_review`, `tally_plan_review`, `gate_b_dedup_plan`, and siblings) delegate to gzip-embedded copies of deleted shell scripts via `_materialize_legacy_root()` / `_run_legacy()` instead of native Python. `python3 python/cli.py plan-review tally` still materializes and runs `tally-plan-review.sh`. Retired scripts are frozen blobs while live `scripts/` dependencies are symlinked, creating a hidden dual-maintenance surface that can desync from HEAD and fails the C3a1 "direct cutover, no shims" goal; `plan_quality` in-process integration never lands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Complete the in-process port or document as legacy relay and adjust acceptance criteria
  - From codex-specialist-correctness-output.txt: Replace the compatibility asset layer with real Python implementations and explicit subprocess seams.
  - From cursor-specialist-edge-cases-output.txt: Complete native port or add CI pinning/decoding checks and explicit compatibility-layer docs
  - From codex-specialist-edge-cases-output.txt: Replace _LEGACY_ASSETS and _run_legacy with native Python implementations, or keep shell scripts until the real port lands.
  - From codex-specialist-testing-output.txt: Port the absorbed script logic into real Python functions and remove the legacy asset materialization/delegation layer.
  - From dyn-retired-path-sweep-output.txt: Either finish the in-process port per the plan, or document and test blob regeneration from HEAD whenever absorbed scripts' live dependencies change; do not treat `python/plan_review.py` as migrated while it shells frozen snapshots.


### FINDING_11: plan-review.md documents wrong Step 3 execution graph
- **Reviewer(s)**: dyn-retired-path-sweep-output.txt
- **Severity**: important
- **Concern**: The normative Step 3 reference still opens with `plan-review-loop.sh` as the consumer, describes `dispatch-plan-review-panel.sh` for dynamic prompts, and documents `run-step3-review.sh` sourcing `review-design-step3-loop.sh`, contradicting the wrapper change to `python/cli.py plan-review run` in `design-step3-review.sh`. Agents reading this file get the wrong execution graph.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retired-path-sweep-output.txt: Rewrite ownership paragraphs so panel/voter dispatch, loop driver, tally, and continuation all name `python/cli.py plan-review` / `python/plan_review.py`, retaining only historical mentions in a short migration note if needed.


### FINDING_13: step3_record_report_evidence lacks design-tmpdir allowlist validation
- **Reviewer(s)**: dyn-artifact-security-output.txt
- **Severity**: important
- **Concern**: `step3_record_report_evidence` writes escalation logs and invokes `stall-recovery-report.sh record-escalation` under whatever path is passed as `--design-tmpdir` (or `DESIGN_TMPDIR`) without calling `session_env.validate_design_tmpdir`. The new direct CLI entrypoint (`plan-review run --record-report-evidence`) lets any caller with shell access target an arbitrary writable directory, including another session's tmpdir, and create `design-failure-escalation-ledger.tsv` outside the documented cache/`/tmp` allowlist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-security-output.txt: Require `--design-tmpdir` on this path, call `validate_design_tmpdir()` before `mkdir` or file writes, reject symlinked tmpdir leaves, and fail closed when validation fails (do not fall back to `DESIGN_TMPDIR` from the environment on the CLI surface).


### FINDING_14: drift_baseline_write_once lacks tmpdir validation and numeric constraints
- **Reviewer(s)**: dyn-artifact-security-output.txt
- **Severity**: important
- **Concern**: `drift_baseline_write_once` and the `plan-review drift-baseline write-once` CLI write `drift-baseline.env` without design-tmpdir allowlist checks and without constraining `plan_lines` / `diff_lines` to single-line numeric tokens. A crafted CLI invocation can create `drift-baseline.env` outside allowed session roots, and embedded newlines in `--plan-lines` or `--diff-lines` can inject extra `KEY=value` lines into the env file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-security-output.txt: Validate `design_tmpdir` with `validate_design_tmpdir()`, reject symlinked targets, and accept only `^[0-9]+$` (or similarly strict) values for both line-count fields before `_write_atomic`.


### FINDING_2: design-step3-review.sh deletes stdout before unconditional replay on env-read failure
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: On `.step3-review-result.env` read failure, the wrapper deletes stdout before an unconditional replay reads it. A symlinked or unreadable env file with unusable fallback stdout aborts under `set -e` before `panel-failed` KVs are emitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Keep stdout until after replay or skip replay on read-result-env failure and emit the already-set panel-failed values.


### FINDING_3: Harnesses quote `python/cli.py` plus subcommands as one executable path
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Retargeted harnesses (notably `scripts/test-prompt-template-invariants.sh:132`) quote `python/cli.py` plus args as a single executable path. The shell tries to execute a filename containing spaces instead of running `python3 cli.py plan-review <verb>`; `make test-prompt-template-invariants` fails before voter-dispatch assertions run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Use python3 "$REPO_ROOT/python/cli.py" plan-review <verb> or command arrays.
  - From cursor-specialist-edge-cases-output.txt: Split python3, cli.py, and subcommands into separate argv words; provide a real fake python/cli.py stub.
  - From codex-specialist-testing-output.txt: Invoke python3 "$REPO_ROOT/python/cli.py" plan-review voter-dispatch with the domain and verb as separate arguments.


### FINDING_4: test-design-step2b-drafter.sh fake plugin can dirty real repo via symlinked python dir
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The fake plugin writes a stub through a symlinked `python` directory using a filename with spaces (`python/cli.py plan-review preview`). Running the harness can dirty the real repo and still does not stub the actual CLI invocation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Create a real fake python/cli.py wrapper or inject a dedicated stub path.


### FINDING_5: plan_quality.py auto-fix defaults to deleted gate-b-dedup-plan.sh
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `plan auto-fix-commands` defaults to deleted `gate-b-dedup-plan.sh`. Auto-fix on `plan.txt` without an override tries to execute a missing file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Default to python3 python/cli.py plan-review gate-b-dedup or call the helper directly, and test the no-override path.


### FINDING_6: Normative /design prose still invokes deleted Bash entrypoints
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-plan-cli-contracts-output.txt, dyn-retired-path-sweep-output.txt
- **Severity**: important
- **Concern**: Live prompt and reference prose still route orchestrators through deleted scripts (`gate-b-dedup-plan.sh`, `tally-plan-review.sh`, `run-step3-review.sh`, `plan-review-loop.sh`, `review-design-step3-loop.sh`) and deleted contract docs. Gate A re-entry is half-migrated (`--snapshot-trailers` uses Python CLI but `--dedup` still names the shell script). Gate B post-apply, MainAgent 0-judge re-tally, and discussion-round rewrites will fail with "command not found" if followed literally. `make lint-retired-scripts` only flags full repo-relative paths, so basename references pass lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Replace the stale helper names with python3 python/cli.py plan-review verbs.
  - From codex-specialist-testing-output.txt: Replace prompt-facing retired helper commands with python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review gate-b-dedup ...
  - From dyn-plan-cli-contracts-output.txt: Replace both invocations in `SKILL.md:665` with `"${CLAUDE_PLUGIN_ROOT}/python/cli.py plan-review gate-b-dedup" --design-tmpdir "$DESIGN_TMPDIR" --snapshot-trailers` and the matching `--dedup` form, matching `approval-gates.md` §Shared post-apply pipeline.
  - From dyn-plan-cli-contracts-output.txt: Change the post-rewrite step to `"${CLAUDE_PLUGIN_ROOT}/python/cli.py plan-review gate-b-dedup" --design-tmpdir "$DESIGN_TMPDIR" --dedup`, and align `skills/design/references/discussion-rounds.md:119` the same way.
  - From dyn-plan-cli-contracts-output.txt: Replace the tally invocation with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py plan-review tally --design-tmpdir "$DESIGN_TMPDIR" --ballot-file "$DESIGN_TMPDIR/ballot.txt" --voter MainAgent:$DESIGN_TMPDIR/voter-main-agent.txt ...` (preserve all other tally flags from the old contract), and update `skills/design/references/plan-review.md:249-251` to match.
  - From dyn-retired-path-sweep-output.txt: Replace every operational instruction with `python3 …/cli.py plan-review …` verbs and point contract reads at `python/plan_review.py` / `python/test_plan_review.py`; extend `migration_lint.py` or `test-design-structure.sh` to fail on basename references to retired scripts inside `skills/design/SKILL.md` and `skills/design/references/*.md`.


### FINDING_7: Deleted shell harness coverage not replaced by pytest; CI gives false green
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-retired-path-sweep-output.txt
- **Severity**: important
- **Concern**: ~20 shell harnesses deleted with only ~10 pytest functions added. `python/test_plan_review.py` (7 tests) and `python/test_plan_review_panel.py` (3 tests) are smoke-level replacements. Twelve Makefile targets (`test-plan-review-loop`, `test-run-step3-review`, `test-tally-plan-review`, `test-gate-b-dedup-plan`, `test-persist-retally-step3-env`, etc.) all invoke the same unfiltered pytest files. `docs/linting.md` overstates coverage for retally, loop, tally, preview mtime, voter PATH stubs, cap/rollback, all `LOOP_STATUS` values, scope-anchor relay, and panel/voter matrix. Missing versus deleted harnesses: `plan-review run --mode loop`, cap persist/rollback, tally-error / degraded-empty-collector rollback, MainAgent vote handoff, gate-b dedup snapshot/restore, retally env refresh, round-snapshot shape, panel slot matrix, waterfall, parse-rate, and plan-voter-paths. Plan acceptance claims parity that is not met.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port deleted tally harness scenarios into pytest; use make test-tally-plan-review with -k tally filter.
  - From cursor-specialist-testing-output.txt: Port deleted panel/voter harness cases into pytest with injectable subprocess stubs per plan.
  - From cursor-specialist-testing-output.txt: Implement documented pytest cases or rewrite docs; align Makefile targets with -k subsets.
  - From cursor-specialist-testing-output.txt: Port gate-b-dedup and persist-retally scenarios to pytest; give each Makefile target a unique -k filter.
  - From cursor-specialist-testing-output.txt: Complete plan test port or revise acceptance with explicit coverage mapping before merge.
  - From codex-specialist-testing-output.txt: Port the deleted shell harness cases into python/test_plan_review.py and python/test_plan_review_panel.py before retiring the old coverage.
  - From dyn-retired-path-sweep-output.txt: Either port the deleted harness scenarios into pytest before merge, or keep Makefile target names mapped to real coverage and downgrade `docs/linting.md` claims until parity exists; at minimum restore scope-anchor loop tests (the deleted `test-plan-review-scope-anchor.sh` had no equivalent in `test_plan_review.py`).
  - From dyn-retired-path-sweep-output.txt: Port the high-value cases from the deleted harnesses (or run them once against the CLI path before deletion) so `make test-plan-review-loop` and sibling targets exercise real contracts, not smoke tests.


### FINDING_8: step3_record_report_evidence omits WARN KV on escalation failure
- **Reviewer(s)**: dyn-plan-cli-contracts-output.txt
- **Severity**: important
- **Concern**: `step3_record_report_evidence()` no longer emits `WARN=Step 3: failed to record design escalation evidence for …` on `stall-recovery-report.sh` failure. The old `review-design-step3-loop.sh` did emit that KV on stdout (FD 3). The wrapper now calls this Python path on `.step3-review-result.env` read failure, so escalation recording can fail silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plan-cli-contracts-output.txt: On non-zero helper exit, print `WARN=Step 3: failed to record design escalation evidence for ${status}` to stdout (via `logging_util.emit_kv` or equivalent) before returning 1, matching the retired shell contract.


### FINDING_9: topology.tsv lists deleted dispatch-plan-review-panel.sh as runtime authority
- **Reviewer(s)**: dyn-retired-path-sweep-output.txt
- **Severity**: important
- **Concern**: The `design.plan_review.panel_slots` row still lists `dispatch-plan-review-panel.sh` as the runtime authority. That script was deleted and registered in `python/migrated-scripts.tsv`. Topology generation will project a dead path as canonical.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retired-path-sweep-output.txt: Update the authority column to `python/plan_review_panel.py` (or `python/cli.py plan-review panel-dispatch`) and regenerate topology docs.


