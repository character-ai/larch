### OOS_1: correctness: python/step_7a.py:32-60
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] run_step7a is a stub missing pre-ship log flush rebase relay transcript capture and run-log commit from step-7a.sh /implement Step 7a via Python skips pre-ship flush; token timing and transcript batches never land in committed run logs before PR creation Port full step-7a.sh orchestration into run_step7a or retain thin bash wrapper until parity
- **Suggested revision**: Address the concern above.


### OOS_2: correctness: python/file_oos.py:546-578
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] OOS disposition checkpoint ignores non-empty security-oos-observations.md. Security-only OOS returns success because non_sec is 0, letting step-8 clear OOS_PENDING without private disposition. Fail validation when the security sidecar is non-empty unless fork or repo-unavailable applies.
- **Suggested revision**: Address the concern above.


### OOS_3: correctness: python/step_7a.py:36-41
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Step 7a calls diagrams upsert with invalid arguments and no issue. Generated diagrams are never posted because diagrams upsert requires --issue plus --code-flow-file or another section mode. Parse issue and repo data, write the code-flow section, and call diagrams upsert with --issue and --code-flow-file.
- **Suggested revision**: Address the concern above.


### OOS_4: correctness: python/step_7a.py:42-60
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Step 7a does not run or propagate the rebase checkpoint probe. A 7a.r conflict can be treated as success because the helper only reads a relay file and returns 0. Invoke rebase-checkpoint-probe.sh, relay stdout, propagate non-zero rc, and flush only after safe continue outcomes.
- **Suggested revision**: Address the concern above.


### OOS_5: correctness: python/step_7a.py:42-48
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Python Step 7a only flushes execution issues, not the full pre-ship run-log set. Pre-PR logs can miss token-report, timing-report, transcripts, vendor diagnostics, and the log commit. Port the full old run_log_flush sequence or call equivalent run_logs APIs for each batch and commit.
- **Suggested revision**: Address the concern above.


### OOS_6: correctness: python/pr_body.py:592-603
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] --comment-only skips the tracking-issue upsert. The post-PR final-report refresh in scripts/ship-pr.sh writes a local summary but leaves the tracking issue with placeholder PR data. Always upsert the tracking issue when possible; use comment_only only to avoid log-tree writes or commits.
- **Suggested revision**: Address the concern above.


### OOS_7: correctness: python/pr_body.py:547-590
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] write_final_report does not write larch-logs/implement/$RUN_ID/final-summary.md. The pre-PR run-log commit can omit final-summary.md even after final-report write succeeds. Copy the rendered body into the run log directory when not comment-only and preserve manifest updates.
- **Suggested revision**: Address the concern above.


### OOS_8: correctness: python/step_7a.py:42-46
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] RUN_ID resolved from missing ship-pr-state then wrong session-id fallback; ignores --run-id At Step 7a execution-issues flush writes to larch-logs/implement/<token-session-id>/ not the real RUN_ID Read RUN_ID from --run-id parent-issue.md then session-env LARCH_RUN_ID never session-id
- **Suggested revision**: Address the concern above.


### OOS_9: correctness: python/file_oos.py:688-699
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] file-conflict-deps emits OOS_ labels instead of numeric dependency rows. Downstream issue batching can reject or ignore OOS_1 to OOS_2 rows where it expects 1 to 2. Emit plain numeric TSV rows matching the retired helper contract.
- **Suggested revision**: Address the concern above.


### OOS_10: correctness: python/stall_recovery.py:508-510
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Required stall-recovery subcommands are no-op stubs. design-failure-report never sees LARCH_DEV_CLONE=true from is-larch-dev-clone, so Tier A filing is skipped in dev clones. Port the real subcommand behavior and exact stdout contracts.
- **Suggested revision**: Address the concern above.


### OOS_11: correctness: python/step_7a.py:32-60
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Python Step 7a is a stub; SKILL.md now invokes it instead of step-7a.sh. /implement Step 7a skips 7a.r rebase probe, pre-ship run-log write/commit, transcript capture, code-flow-section.md, and classifier paths; orchestrator sees REBASE_OUTCOME=skipped and may ship without rebasing or flushing logs. Port full step-7a.sh orchestration into step_7a.py with identical KV tail, exit codes, and rebase relay stdout ordering.
- **Suggested revision**: Address the concern above.


### OOS_12: correctness: python/step_7a.py:63-77
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] CLI ignores --issue-number, --run-id, --no-logs-commit, --forked-target via parse_known_args. Fork base/rebase argv wrong; run-log commit runs when --no-logs-commit true; diagram upsert gates on issue/section incorrectly. Parse and enforce all step-7a.sh flags; mirror bash warnings and early exits.
- **Suggested revision**: Address the concern above.


### OOS_13: security: python/stall_recovery.py:508-510
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] populate-sensitive-corpus and normalize-file-failure-report-env are no-op stubs returning success. /design failure reports proceed without building redaction corpus or normalizing filed-env; sensitive log content may reach public Tier-A issues. Port bash corpus build and env normalization with tmpdir validation before retiring stall-recovery-report.sh.
- **Suggested revision**: Address the concern above.


### OOS_14: correctness: python/stall_recovery.py:470-477
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] dedup-tier-a-report aliases to compose_report instead of GitHub dedup logic. Tier-A dedup never runs; duplicate stall bugs are filed repeatedly; no-match filing path in design-failure-report.sh is bypassed. Implement separate dedup-tier-a-report subcommand matching bash status KVs.
- **Suggested revision**: Address the concern above.


### OOS_15: security: python/stall_recovery.py:355-382
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] validate_terminal_state omits value sanitization and tmpdir-local file checks present in bash. Terminal-state files containing URLs, paths, or invalid tokens pass validation and flow into public stall reports. Port bash terminal_state_value_valid, path containment, and forbidden-value rules.
- **Suggested revision**: Address the concern above.


### OOS_16: correctness: python/pr_body.py:775-787
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] generate_code_flow_diagram ignores base_remote/base_ref and uses a static placeholder diagram. Fork-mode and production runs get generic diagrams not derived from the branch diff; code-flow-section.md may never be produced for diagrams upsert. Restore subprocess generation and diff/base handling from generate-code-flow-diagram.sh.
- **Suggested revision**: Address the concern above.


### OOS_17: correctness: python/step_7a.py:36-41
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] diagrams upsert called with invalid --diagram-file instead of --issue and --code-flow-file Upsert always fails; COMMENT_URL empty after successful diagram generation Use diagrams upsert --issue --repo --code-flow-file code-flow-section.md
- **Suggested revision**: Address the concern above.


### OOS_18: correctness: python/pr_body.py:590-603
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] --comment-only disables the tracking-issue upsert. Post-PR final-report refresh succeeds but leaves the tracking issue with placeholder PR fields. Make comment_only skip git/log side effects only, and still run the API upsert.
- **Suggested revision**: Address the concern above.


### OOS_19: security: python/file_oos.py:574-586
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] The OOS disposition checkpoint ignores a non-empty security-oos-observations.md sidecar. Security-only OOS can pass the checkpoint and allow OOS_PENDING=false before ship blocks it. Fail closed on a non-empty security sidecar unless forked or repo unavailable.
- **Suggested revision**: Address the concern above.


### OOS_20: security: python/file_oos.py:346-350
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Manifest materialization does not read the planned "Focus area" key. A security OOS item with "Focus area": "security" can be written to public accepted-OOS markdown. Accept focus-area, focus_area, Focus area, and equivalent case/spacing variants through one extractor.
- **Suggested revision**: Address the concern above.


### OOS_21: risk-integration: python/step_7a.py:36-42
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Step 7a ignores issue args and calls diagrams upsert with an invalid --diagram-file option. The code-flow diagram comment is never posted and the failure is silent. Parse issue/repo args and call diagrams upsert with --issue and --code-flow-file, logging failures.
- **Suggested revision**: Address the concern above.


### OOS_22: correctness: python/step_7a.py:49-60
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Step 7a does not invoke the rebase checkpoint probe. A conflict or bail route at 7a.r is bypassed and pre-ship flushing proceeds on a stale base. Run rebase-checkpoint-probe.sh, relay its stdout, and return its nonzero status before flushing logs.
- **Suggested revision**: Address the concern above.


### OOS_23: risk-integration: python/stall_recovery.py:508-510
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Live stall-recovery subcommands are STATUS=ok no-ops. /design Tier A filing is disabled because is-larch-dev-clone never emits LARCH_DEV_CLONE=true. Port the subcommands fully or keep callers on the old helper until parity exists.
- **Suggested revision**: Address the concern above.


### OOS_24: correctness: python/file_oos.py:534-586
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Python disposition-checkpoint drops bash security-sidecar fail-closed and missing-ndjson validation from oos-disposition-checkpoint.sh:176-182. Security-only manifest OOS can pass checkpoint rc=0 and clear OOS_PENDING despite plan fail-closed security sidecar semantics. Port both pre-gate checks into disposition_checkpoint_main with exit 2 and matching Tool Failures sites; add pytest parity cases.
- **Suggested revision**: Address the concern above.


### OOS_25: correctness: python/step_7a.py:32-60
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] SKILL routes Step 7a to Python CLI but step_7a.py omits rebase probe, transcript capture, run-log commit, skip classifiers, and fork/no-logs-commit handling present in step-7a.sh. /implement skips 7a.r rebase and pre-ship log flush while make test-step-7a still validates the bash script. Complete Python Step 7a to bash parity or revert SKILL routing until parity; expand test_step_7a.py for rebase and flush paths.
- **Suggested revision**: Address the concern above.


### OOS_26: correctness: python/step_7a.py:53-60
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Python returns exit 1 on diagram failure; bash continued with exit 0 Diagram sanitizer failure aborts Step 7a and skips pre-ship flush Warn on diagram failure continue rebase and flush match bash exit semantics
- **Suggested revision**: Address the concern above.


### OOS_27: risk-integration: python/file_oos.py:323-586
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] ~500 lines of new OOS port logic have zero new pytest; CI still runs test-oos-disposition-gate.sh against bash oos-disposition-gate.sh while Step 8 calls Python. Disposition regressions ship with green CI because production and harness exercise different code. Port harness scenarios into python/test_file_oos.py per plan; update Makefile targets.
- **Suggested revision**: Address the concern above.


### OOS_28: [OUT_OF_SCOPE] risk-integration: python/migrated-scripts.tsv
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No C4c retired-path rows because bash scripts were not deleted. lint-retired-scripts will not guard stale references after deletion. Add rows when scripts are removed.
- **Suggested revision**: Address the concern above.


### OOS_29: [OUT_OF_SCOPE] risk-integration: python/test_pr_body.py
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] pr_body.py gained write_final_report and related helpers without new implement-focused pytest on this branch. Final-report regressions rely on bash test-write-final-report harness. Add write_final_report/step18b pytest per plan before deleting bash harness.
- **Suggested revision**: Address the concern above.


### OOS_30: security: python/file_oos.py:574-578
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] disposition_checkpoint_main ignores security-oos-observations.md Step 8 can clear OOS_PENDING for a security-only sidecar even though the plan requires fail-closed handling Check the sidecar before disposition_gate except for fork or repo-unavailable, preserve Tool Failures logging, and test the security-only path
- **Suggested revision**: Address the concern above.


### OOS_31: correctness: python/pr_body.py:565-588
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] write_final_report hardcodes cost_unavailable=True All final reports show Cost N/A even when token reports exist Port token cost loading from write-final-report.sh
- **Suggested revision**: Address the concern above.


### OOS_32: risk-integration: python/step_7a.py:32-60
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] Step 7a does not invoke or relay the rebase checkpoint contract The orchestrator expects ROUTE, REBASE_RC, REBASE_ERROR, and CONFLICT_FILES, so conflicts or failed rebases can skip conflict/stall routing Call the existing probe, relay its stdout keys, preserve exit-code mapping, and test conflict, bail, and continue outcomes
- **Suggested revision**: Address the concern above.


### OOS_33: risk-integration: python/pr_body.py:590-592
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] final-report write lost the run-log mirror and inverted comment-only behavior Pre-PR log commit can miss final-summary.md, and post-PR --comment-only can return success without refreshing the tracking comment Write larch-logs/implement/<RUN_ID>/final-summary.md unless comment_only is true, always upsert the comment except skip cases, and test both paths
- **Suggested revision**: Address the concern above.


### OOS_34: security: python/file_oos.py:346-350
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] materialize_manifest_oos does not honor the plan-required Focus area manifest key A security observation using Focus area: security is materialized into public accepted OOS instead of the private security sidecar Normalize focus-area keys across case, spaces, hyphens, and underscores, and add a regression test
- **Suggested revision**: Address the concern above.


### OOS_35: risk-integration: python/stall_recovery.py:508-510
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] stall-recovery subcommands are successful no-ops design-failure-report expects LARCH_DEV_CLONE=true from is-larch-dev-clone, so Tier-A filing is always skipped Implement the old stdout and file contracts for these subcommands and test through the design callers
- **Suggested revision**: Address the concern above.


### OOS_36: **correctness** `python/step_7a.py:32-77` — `python/cli.py implement step-7a` is a stub, not a port of `skills/implement/scripts/step-7a.sh`. It skips the small/non-runtime classifier, `code-flow-section.md` composition, embedded `7a.r` rebase via `rebase-checkpoint-probe.sh`, the full pre-ship flush (token/timing reports, transcript capture, vendor-failure batch, run-log commit, post-transcript execution-issues flush), and it ignores `--issue-number`, `--run-id`, `--no-logs-commit`, and `--forked-target` from `skills/implement/SKILL.md`. **Suggested fix:** Port the remaining `step-7a.sh` orchestration into `run_step7a`/`main`, or keep a thin bash wrapper that delegates to Python leaf verbs until parity is complete; do not wire SKILL.md to the stub.
- **Reviewer**: dyn-migration-parity-output.txt
- **Concern**: - **correctness** `python/step_7a.py:32-77` — `python/cli.py implement step-7a` is a stub, not a port of `skills/implement/scripts/step-7a.sh`. It skips the small/non-runtime classifier, `code-flow-section.md` composition, embedded `7a.r` rebase via `rebase-checkpoint-probe.sh`, the full pre-ship flush (token/timing reports, transcript capture, vendor-failure batch, run-log commit, post-transcript execution-issues flush), and it ignores `--issue-number`, `--run-id`, `--no-logs-commit`, and `--forked-target` from `skills/implement/SKILL.md`. **Suggested fix:** Port the remaining `step-7a.sh` orchestration into `run_step7a`/`main`, or keep a thin bash wrapper that delegates to Python leaf verbs until parity is complete; do not wire SKILL.md to the stub.
- **Suggested revision**: Address the concern above.


### OOS_37: **correctness** `python/step_7a.py:36-41` — Diagram upsert calls `diagrams upsert --diagram-file`, but `python/rendering.py` requires `--issue` plus `--code-flow-file` (or another section mode). The call always fails, so `COMMENT_URL` stays empty even when diagram generation succeeds. **Suggested fix:** Compose `code-flow-section.md` like the shell helper, then call `diagrams upsert --issue "$ISSUE_NUMBER" [--repo "$REPO"] --code-flow-file "$IMPLEMENT_TMPDIR/code-flow-section.md"`.
- **Reviewer**: dyn-migration-parity-output.txt
- **Concern**: - **correctness** `python/step_7a.py:36-41` — Diagram upsert calls `diagrams upsert --diagram-file`, but `python/rendering.py` requires `--issue` plus `--code-flow-file` (or another section mode). The call always fails, so `COMMENT_URL` stays empty even when diagram generation succeeds. **Suggested fix:** Compose `code-flow-section.md` like the shell helper, then call `diagrams upsert --issue "$ISSUE_NUMBER" [--repo "$REPO"] --code-flow-file "$IMPLEMENT_TMPDIR/code-flow-section.md"`.
- **Suggested revision**: Address the concern above.


### OOS_38: **correctness** `python/pr_body.py:565-589` — `write_final_report` always passes `cost_unavailable=True` into `render_run_summary`, so Step 17/18 summaries always show `- **Cost**: N/A`. The ported `render_run_summary_main` already knows how to compute costs via `report_tokens_cost.token_cost_from_args` (`python/pr_body.py:437-459`). **Suggested fix:** Reuse the bash helper’s token-report discovery and cost assembly in `write_final_report`, and only set `cost_unavailable=True` when token data is missing or corrupt.
- **Reviewer**: dyn-migration-parity-output.txt
- **Concern**: - **correctness** `python/pr_body.py:565-589` — `write_final_report` always passes `cost_unavailable=True` into `render_run_summary`, so Step 17/18 summaries always show `- **Cost**: N/A`. The ported `render_run_summary_main` already knows how to compute costs via `report_tokens_cost.token_cost_from_args` (`python/pr_body.py:437-459`). **Suggested fix:** Reuse the bash helper’s token-report discovery and cost assembly in `write_final_report`, and only set `cost_unavailable=True` when token data is missing or corrupt.
- **Suggested revision**: Address the concern above.


### OOS_39: **correctness** `python/file_oos.py:613-646` — `issue_cap` does not match `skills/implement/scripts/oos-issue-cap.sh` validation or output shape. It skips `issue parse-input`, ITEMS_TOTAL vs heading-count checks, OOS-shape refusal, excerpt cap default (**800** vs **200**), file-ref extraction in rollups, and post-cap header renumbering. Invalid batches can be compacted silently or produce rollups the `/issue` pipeline does not expect. **Suggested fix:** Port the parse-input gate, excerpt helper behavior, renumber pass, and rollup format from the shell helper, or keep calling the shell helper until parity tests pass.
- **Reviewer**: dyn-migration-parity-output.txt
- **Concern**: - **correctness** `python/file_oos.py:613-646` — `issue_cap` does not match `skills/implement/scripts/oos-issue-cap.sh` validation or output shape. It skips `issue parse-input`, ITEMS_TOTAL vs heading-count checks, OOS-shape refusal, excerpt cap default (**800** vs **200**), file-ref extraction in rollups, and post-cap header renumbering. Invalid batches can be compacted silently or produce rollups the `/issue` pipeline does not expect. **Suggested fix:** Port the parse-input gate, excerpt helper behavior, renumber pass, and rollup format from the shell helper, or keep calling the shell helper until parity tests pass.
- **Suggested revision**: Address the concern above.


### OOS_40: **correctness** `python/file_oos.py:677-685` — `file_conflict_deps` is a simplified regex pairwise check. It does not use `issue parse-input`, `voting file-line-regex`, cluster/global caps, path safety rules, or fatal cleanup behavior from `skills/implement/scripts/oos-file-conflict-deps.sh`. Design filing order can miss or invent edges relative to the absorbed contract. **Suggested fix:** Port the shell helper’s parse/extract/cap pipeline, or route `file-design-oos.sh` through the existing shell implementation until Python parity is proven.
- **Reviewer**: dyn-migration-parity-output.txt
- **Concern**: - **correctness** `python/file_oos.py:677-685` — `file_conflict_deps` is a simplified regex pairwise check. It does not use `issue parse-input`, `voting file-line-regex`, cluster/global caps, path safety rules, or fatal cleanup behavior from `skills/implement/scripts/oos-file-conflict-deps.sh`. Design filing order can miss or invent edges relative to the absorbed contract. **Suggested fix:** Port the shell helper’s parse/extract/cap pipeline, or route `file-design-oos.sh` through the existing shell implementation until Python parity is proven.
- **Suggested revision**: Address the concern above.


### OOS_41: correctness: python/stall_recovery.py:508-510
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] is-larch-dev-clone populate-sensitive-corpus normalize-file-failure-report-env lint are no-ops; dedup-tier-a-report is not real dedup /design failure reports skip Tier-A eligibility sensitive corpus and cross-repo dedup filing Port bash subcommand behavior instead of STATUS=ok stubs
- **Suggested revision**: Address the concern above.


### OOS_42: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-callsite-routing-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/test-design-publish.sh:51`, `test-design-stage-terminal-state.sh:64`, `test-design-failure-report.sh:150` — Design test harnesses still symlink or point at `stall-recovery-report.sh`; acceptable only while bash remains, but they will need pytest/harness updates when the script is deleted (plan item, not a new runtime regression today).
- **Suggested revision**: Address the concern above.


### OOS_43: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-callsite-routing-output.txt
- **Concern**: - **architecture** `docs/run-logs.md` (diff hunk ~592) — The migrated doc link targets `scripts/python/cli.py render run-summary`, which is not a real path; the authority is `python/cli.py render run-summary`.
- **Suggested revision**: Address the concern above.


### OOS_44: **code-quality** `python/stall_recovery.py:508-510` — Four live subcommands (`populate-sensitive-corpus`, `normalize-file-failure-report-env`, `is-larch-dev-clone`, `lint`) are no-op stubs that only emit `STATUS=ok`, while `skills/design/scripts/design-failure-report.sh` still calls them for Tier A routing, sensitive-corpus population, env normalization, and allowlist lint. `is-larch-dev-clone` must emit `LARCH_DEV_CLONE=true|false` per the bash contract; the stub never does, so `tier_a_eligible()` will always fail and Tier A issue-input filing is silently disabled. **Suggested fix:** Port the bash implementations for these four subcommands (or delegate to the remaining bash only until parity exists), emit the full KV contracts callers grep for, and add pytest cases mirroring `test-stall-recovery-report-1.sh` cases 12 and 24 plus `test-design-failure-report.sh` populate-sensitive coverage.
- **Reviewer**: dyn-lint-readiness-output.txt
- **Concern**: - **code-quality** `python/stall_recovery.py:508-510` — Four live subcommands (`populate-sensitive-corpus`, `normalize-file-failure-report-env`, `is-larch-dev-clone`, `lint`) are no-op stubs that only emit `STATUS=ok`, while `skills/design/scripts/design-failure-report.sh` still calls them for Tier A routing, sensitive-corpus population, env normalization, and allowlist lint. `is-larch-dev-clone` must emit `LARCH_DEV_CLONE=true|false` per the bash contract; the stub never does, so `tier_a_eligible()` will always fail and Tier A issue-input filing is silently disabled. **Suggested fix:** Port the bash implementations for these four subcommands (or delegate to the remaining bash only until parity exists), emit the full KV contracts callers grep for, and add pytest cases mirroring `test-stall-recovery-report-1.sh` cases 12 and 24 plus `test-design-failure-report.sh` populate-sensitive coverage.
- **Suggested revision**: Address the concern above.


### OOS_45: **code-quality** `python/stall_recovery.py:224-237` — `normalize_outcome()` only reads `ship-pr-state.sh` / `finalize-state.sh` via `_state()` and ignores `--in-memory-stall-tracking`, even though Step 18a.5 passes that flag and bash `cmd_normalize_outcome` unions memory, ship, finalize, and session-env stall layers before choosing outcome. The `normalize-outcome` subcommand parser (`main()` around 451-453) also does not declare `--in-memory-stall-tracking`, so the flag is dropped on the floor. **Suggested fix:** Add `--in-memory-stall-tracking` to the subcommand parser, read `session-env.sh` stall keys, and mirror the bash truthy union logic before emitting `IMPLEMENT_NORMALIZED_OUTCOME` / `IMPLEMENT_OUTCOME_SUCCEEDED`.
- **Reviewer**: dyn-lint-readiness-output.txt
- **Concern**: - **code-quality** `python/stall_recovery.py:224-237` — `normalize_outcome()` only reads `ship-pr-state.sh` / `finalize-state.sh` via `_state()` and ignores `--in-memory-stall-tracking`, even though Step 18a.5 passes that flag and bash `cmd_normalize_outcome` unions memory, ship, finalize, and session-env stall layers before choosing outcome. The `normalize-outcome` subcommand parser (`main()` around 451-453) also does not declare `--in-memory-stall-tracking`, so the flag is dropped on the floor. **Suggested fix:** Add `--in-memory-stall-tracking` to the subcommand parser, read `session-env.sh` stall keys, and mirror the bash truthy union logic before emitting `IMPLEMENT_NORMALIZED_OUTCOME` / `IMPLEMENT_OUTCOME_SUCCEEDED`.
- **Suggested revision**: Address the concern above.


### OOS_46: **code-quality** `python/test_stall_recovery.py:1-32` — Pytest coverage for the new stall-recovery module is only two smoke tests (`retry_policy`, `normalize_issue_env`), while the plan requires porting three bash harnesses (`test-stall-recovery-report-{1,2,3}.sh`) and `Makefile` still runs those harnesses against `skills/implement/scripts/stall-recovery-report.sh`, not `python/cli.py stall-recovery`. CI can stay green on bash parity while the Python path used by production callers remains largely untested. **Suggested fix:** Port the harness scenarios into `python/test_stall_recovery.py` (classify, validate-token, dedup, is-larch-dev-clone, lint allowlist drift, populate-sensitive-corpus), then repoint or retire the bash harness targets once Python passes the same cases.
- **Reviewer**: dyn-lint-readiness-output.txt
- **Concern**: - **code-quality** `python/test_stall_recovery.py:1-32` — Pytest coverage for the new stall-recovery module is only two smoke tests (`retry_policy`, `normalize_issue_env`), while the plan requires porting three bash harnesses (`test-stall-recovery-report-{1,2,3}.sh`) and `Makefile` still runs those harnesses against `skills/implement/scripts/stall-recovery-report.sh`, not `python/cli.py stall-recovery`. CI can stay green on bash parity while the Python path used by production callers remains largely untested. **Suggested fix:** Port the harness scenarios into `python/test_stall_recovery.py` (classify, validate-token, dedup, is-larch-dev-clone, lint allowlist drift, populate-sensitive-corpus), then repoint or retire the bash harness targets once Python passes the same cases.
- **Suggested revision**: Address the concern above.


### OOS_47: **code-quality** `python/test_execution_issues.py:1-25` — Execution-issues pytest has only append/record-split tests; `flush_execution_issues()` and `refresh_execution_issues()` (including validation RC `2`, sentinel idempotency, and `REFRESHED`/`ERROR` KV tails) are untested despite the plan calling for harness ports from `test-flush-execution-issues.sh` and `test-refresh-execution-issues.sh`. **Suggested fix:** Add flush/refresh tests covering empty skip, already-flushed sentinel, failed `run-log append`, invalid `--log-root`, and tracking-issue upsert failure paths before deleting the bash harnesses.
- **Reviewer**: dyn-lint-readiness-output.txt
- **Concern**: - **code-quality** `python/test_execution_issues.py:1-25` — Execution-issues pytest has only append/record-split tests; `flush_execution_issues()` and `refresh_execution_issues()` (including validation RC `2`, sentinel idempotency, and `REFRESHED`/`ERROR` KV tails) are untested despite the plan calling for harness ports from `test-flush-execution-issues.sh` and `test-refresh-execution-issues.sh`. **Suggested fix:** Add flush/refresh tests covering empty skip, already-flushed sentinel, failed `run-log append`, invalid `--log-root`, and tracking-issue upsert failure paths before deleting the bash harnesses.
- **Suggested revision**: Address the concern above.


### OOS_48: **code-quality** `python/test_step_7a.py:1-17` — Step 7a pytest only checks that a diagram file is created and two KVs appear; it does not cover execution-issues flush with a real `RUN_ID`, `7a.r` rebase relay, bail on diagram failure, or `COMMENT_URL` upsert behavior promised in the plan. `Makefile` still runs `skills/implement/scripts/test-step-7a.sh` against the bash `step-7a.sh` wrapper. **Suggested fix:** Expand `test_step_7a.py` to exercise flush, relay, and failure branches with mocks, then switch `test-step-7a` Makefile target to pytest.
- **Reviewer**: dyn-lint-readiness-output.txt
- **Concern**: - **code-quality** `python/test_step_7a.py:1-17` — Step 7a pytest only checks that a diagram file is created and two KVs appear; it does not cover execution-issues flush with a real `RUN_ID`, `7a.r` rebase relay, bail on diagram failure, or `COMMENT_URL` upsert behavior promised in the plan. `Makefile` still runs `skills/implement/scripts/test-step-7a.sh` against the bash `step-7a.sh` wrapper. **Suggested fix:** Expand `test_step_7a.py` to exercise flush, relay, and failure branches with mocks, then switch `test-step-7a` Makefile target to pytest.
- **Suggested revision**: Address the concern above.


### OOS_49: correctness: python/pr_body.py:775-776
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] generate_code_flow_diagram discards base_remote and base_ref Fork mode diagram generation ignores upstream diff context Wire base remote/ref into generation prompt or diff
- **Suggested revision**: Address the concern above.


### OOS_50: [OUT_OF_SCOPE] **`python/migrated-scripts.tsv`** does not yet list C4c retired paths (`stall-recovery-report.sh`, `step-7a.sh`, `flush-execution-issues.sh`, etc.) called for in the plan acceptance checklist; that is a migration-hygiene gap but not a current linter failure.
- **Reviewer**: dyn-lint-readiness-output.txt
- **Concern**: - **`python/migrated-scripts.tsv`** does not yet list C4c retired paths (`stall-recovery-report.sh`, `step-7a.sh`, `flush-execution-issues.sh`, etc.) called for in the plan acceptance checklist; that is a migration-hygiene gap but not a current linter failure.
- **Suggested revision**: Address the concern above.


### OOS_51: correctness: python/step_7a.py:63-77
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] CLI silently ignores --issue-number --run-id --no-logs-commit --forked-target Orchestrator flags documented in SKILL.md have no effect Parse and implement all documented Step 7a flags
- **Suggested revision**: Address the concern above.


