# Review Round 1

- Mode: `diff`
- 31 accepted, 12 rejected (8 neutral)

## Accepted Findings

### FINDING_10: correctness: skills/design/scripts/design-step5c.sh:114-125
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] rc 2 and unexpected publish exits abort without failed-publish-tail staging or final summary routing design-publish.sh exits 2 after redaction or validator setup failure, and /design stops before the report gate can run Stage failed-publish-tail, invoke render-final-summary.sh --post-publish-only --outcome failed-publish-tail when safe, then abort
- **Suggested revision**: Address the concern above.


### FINDING_11: correctness: skills/design/scripts/design-step-validator-autofix.sh:135-143
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Validator autofix failures are normalized but never recorded as escalation evidence, and Cancel does not write operator-action audit artifacts An exhausted validator autofix later repaired inline can finish approved with no escalation ledger, so escalation-success reporting skips Call generic record-escalation for exhausted, failed, unavailable, and skipped-cycle-cap; add Cancel sentinel, chat sidecar, and run-log audit
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: skills/design/scripts/design-failure-report.sh:177-190
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] The design report gate always uses chat-print Tier B and never uses the required Tier A flow in larch dev clones A failed-plan-write in a larch dev clone files only a bounded public report instead of a full-context local Tier A issue input Detect Tier A eligibility and use compose-report --surface issue-input plus Tier A filing/dedup; use chat-print only for Tier B
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: skills/design/scripts/design-failure-report.sh:174-190
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Operator-action root-cause compose results are treated as terminal reports, so the required operator chat and run-log audit are skipped ROOT_CAUSE_HINT=operator-action makes compose-report return skipped_operator_action, but design-failure-report writes design-failure-terminal-report.env and no operator-action chat sidecar Parse compose status and verdict; on skipped_operator_action run the operator-action audit path and avoid the terminal-report sentinel
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: skills/design/scripts/design-step-validator-autofix.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Validator autofix never records escalation or operator-action on Cancel. Approved /design runs with validator exhaustion never get escalation-success evidence; Cancel after ledger rows cannot block later filing per plan. Call record-escalation for non-ok autofix statuses; on Cancel write operator-action sentinel chat sidecar and run-log audit.
- **Suggested revision**: Address the concern above.


### FINDING_16: correctness: skills/design/scripts/design-step5c.sh:114-125
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Publish-tail hard exits abort without staging failed-publish-tail or running the report gate. A redaction failure or design-publish configuration error exits before any durable /design failure report is created. Stage failed-publish-tail and invoke render-final-summary.sh --post-publish-only before aborting when DESIGN_TMPDIR is valid.
- **Suggested revision**: Address the concern above.


### FINDING_17: risk-integration: skills/design/scripts/design-step-validator-autofix.sh:131-143
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Validator autofix non-ok statuses are normalized but never recorded as escalation evidence. A run approved after main-agent repair of validator defects has no ledger, so escalation-success reporting is skipped. Call the generic record-escalation helper for exhausted, failed, unavailable, and skipped-cycle-cap after normalization.
- **Suggested revision**: Address the concern above.


### FINDING_18: correctness: skills/design/scripts/design-failure-report.sh:202-204
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] The escalation-success evidence check ignores tagged record-escalation Tool Failure entries. If ledger writes fail but execution-issues.md contains the tagged Tool Failure, approved teardown returns no-escalation-evidence. Include record_escalation_tool_failure_present or an equivalent public check before skipping.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: skills/design/scripts/design-failure-report.sh:177-190
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Operator-action root-cause compose results are treated as terminal reports. A ROOT_CAUSE_HINT=operator-action terminal state skips filing but misses the required chat and run-log audit, then terminal sentinel masks future repair. Parse compose status and route skipped_operator_action through the operator-action audit path instead of terminal sentinel creation.
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: skills/design/scripts/design-failure-report.sh:177-193
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Terminal reporting treats compose-report exit 0 as success without parsing STALL_RECOVERY_REPORT_STATUS. ROOT_CAUSE_HINT=operator-action yields skipped_operator_action from compose but gate still writes terminal sentinel and reports terminal-failure. Parse compose KVs; branch on skipped_operator_action and fallback-print-required before writing terminal sentinel.
- **Suggested revision**: Address the concern above.


### FINDING_21: risk-integration: skills/design/scripts/design-failure-report.sh:177-218
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] The /design gate always uses the Tier B chat-print surface and never emits Tier A issue input in larch dev clones. Dev-clone terminal or escalation reports lose full local context and are forced into bounded cross-repo filing. Detect Tier A eligibility and call compose-report --surface issue-input for dev clones, using chat-print only for Tier B.
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: skills/design/scripts/design-publish.sh:573-575
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Failed design-log publish is staged without an environment root-cause hint. GitHub auth or network failures after plan write are filed as larch-defect by the default root-cause path. Pass --root-cause-hint environment for failed-publish or map publish transport/auth failures to environment in the report gate.
- **Suggested revision**: Address the concern above.


### FINDING_23: risk-integration: Makefile:1132-1141
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] New test-design-stage-terminal-state, test-design-failure-report, and test-design-step3-review targets are not assigned to any test-harnesses-N shard. make lint runs test-harness-shards-coverage which fails on orphan test-* recipes; new harnesses never run in full CI either. Add each target to exactly one test-harnesses-N prerequisite list and refresh docs/linting.md shard mapping.
- **Suggested revision**: Address the concern above.


### FINDING_25: risk-integration: skills/design/scripts/design-step5c.sh:114-125
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Publish-tail abort path lacks planned terminal staging and failed-publish-tail summary routing. Unexpected publish rc exits immediately with no design-failure-terminal-state.env and no report gate; operators get no durable filing path. Implement design-stage-terminal-state plus render-final-summary failed-publish-tail flow and add a hermetic harness case.
- **Suggested revision**: Address the concern above.


### FINDING_26: risk-integration: skills/design/scripts/design-step-validator-autofix.sh:131-143
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Validator autofix script omits planned record-escalation and operator-action Cancel handling. Validator exhaustion never creates escalation ledger evidence; later approved runs cannot file escalation-success; Cancel does not block filing per plan. Wire generic record-escalation and operator-action artifacts; add harness coverage for ledger and sentinel precedence.
- **Suggested revision**: Address the concern above.


### FINDING_29: risk-integration: Makefile:1132-1141
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] New test targets are not assigned to any test-harnesses shard. make lint shard coverage will fail and the new report-gate harnesses will not run in the aggregate. Add the three new targets to appropriate test-harnesses-N prerequisite lines.
- **Suggested revision**: Address the concern above.


### FINDING_3: correctness: skills/design/scripts/design-step5c.sh:114-125
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Publish-tail hard exits abort without staging failed-publish-tail or running final summary. design-publish.sh exit 2 leaves no terminal state; report gate never sees a failed-* outcome. Stage terminal state and invoke render-final-summary.sh --post-publish-only --outcome failed-publish-tail before abort.
- **Suggested revision**: Address the concern above.


### FINDING_30: correctness: skills/implement/scripts/stall-recovery-report.sh:1016-1019
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] validate-terminal-state rejects valid FAILURE_DETAIL_LOG paths containing /Users before confinement validation. /design tmpdirs under /Users with a valid failure detail log cannot stage terminal state and fall back instead of reporting. Exempt FAILURE_DETAIL_LOG from generic raw-path rejection and rely on tmpdir confinement validation; add /Users or /home path coverage.
- **Suggested revision**: Address the concern above.


### FINDING_31: correctness: skills/design/scripts/design-failure-report.sh:174-192
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] Terminal compose status is not inspected for skipped_operator_action. A terminal state with ROOT_CAUSE_HINT=operator-action writes a terminal sentinel and misses the required operator-action chat audit on first teardown. Parse compose env status and route skipped_operator_action to operator-action audit without writing the terminal sentinel.
- **Suggested revision**: Address the concern above.


### FINDING_32: correctness: skills/design/scripts/design-step5c.sh:114-126
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] Step 5c hard exits still bypass failed-publish-tail staging and summary routing. design-publish exit 2 or unexpected non-zero exits abort without durable /design failure reporting. Stage failed-publish-tail and call render-final-summary before aborting when DESIGN_TMPDIR is valid.
- **Suggested revision**: Address the concern above.


### FINDING_34: **risk-integration** `skills/design/scripts/design-step-validator-autofix.sh:135-143` — The plan and `skills/design/SKILL.md` (line 902) require `record-escalation` for `exhausted`, `failed`, `unavailable`, and `skipped-cycle-cap` before the validator operator prompt, but the wrapper stops after normalizing `_autofix_status` and never calls `stall-recovery-report.sh --profile generic --artifact-prefix design-failure record-escalation`. Validator handoffs on an otherwise-successful `/design` run will not produce durable escalation evidence, so the teardown gate will skip escalation-success filing even when the run later ends `approved` / `approved-partition`. **Suggested fix:** After `_autofix_status` normalization, map `SITE` to design tokens and invoke `record-escalation` with confined `--failure-detail-log` when the validator log is under `$DESIGN_TMPDIR`; keep it non-blocking and capture stdout/stderr into sidecars per the plan.
- **Reviewer**: dyn-design-reporting-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/design-step-validator-autofix.sh:135-143` — The plan and `skills/design/SKILL.md` (line 902) require `record-escalation` for `exhausted`, `failed`, `unavailable`, and `skipped-cycle-cap` before the validator operator prompt, but the wrapper stops after normalizing `_autofix_status` and never calls `stall-recovery-report.sh --profile generic --artifact-prefix design-failure record-escalation`. Validator handoffs on an otherwise-successful `/design` run will not produce durable escalation evidence, so the teardown gate will skip escalation-success filing even when the run later ends `approved` / `approved-partition`. **Suggested fix:** After `_autofix_status` normalization, map `SITE` to design tokens and invoke `record-escalation` with confined `--failure-detail-log` when the validator log is under `$DESIGN_TMPDIR`; keep it non-blocking and capture stdout/stderr into sidecars per the plan.
- **Suggested revision**: Address the concern above.


### FINDING_35: **risk-integration** `skills/design/scripts/design-publish.sh:11-14,364-398` and `skills/design/scripts/design-step5c.sh:115-125` — Publish-tail hard failures (`fail()` exits with code `2` for missing Step 5b sentinel, missing `composed-plan.md`, validator infrastructure failure, redact failure, etc.) do not stage `design-failure-terminal-state.env` as `failed-publish-tail`, and `design-step5c.sh` aborts on `_publish_rc=2` without setting `SUMMARY_OUTCOME=failed-publish-tail` or routing through `render-final-summary.sh --post-publish-only`. The report gate therefore never runs on those paths, despite the plan and `SKILL.md` exit-code contract requiring terminal staging plus final-summary routing before abort. **Suggested fix:** Add a shared publish-tail failure helper that stages `failed-publish-tail` (best effort), sets `SUMMARY_OUTCOME`, invokes `render-final-summary.sh --post-publish-only`, then exits; call it from every `fail()` path and from `design-step5c.sh` when `_publish_rc` is `2` or another unexpected hard code.
- **Reviewer**: dyn-design-reporting-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/design-publish.sh:11-14,364-398` and `skills/design/scripts/design-step5c.sh:115-125` — Publish-tail hard failures (`fail()` exits with code `2` for missing Step 5b sentinel, missing `composed-plan.md`, validator infrastructure failure, redact failure, etc.) do not stage `design-failure-terminal-state.env` as `failed-publish-tail`, and `design-step5c.sh` aborts on `_publish_rc=2` without setting `SUMMARY_OUTCOME=failed-publish-tail` or routing through `render-final-summary.sh --post-publish-only`. The report gate therefore never runs on those paths, despite the plan and `SKILL.md` exit-code contract requiring terminal staging plus final-summary routing before abort. **Suggested fix:** Add a shared publish-tail failure helper that stages `failed-publish-tail` (best effort), sets `SUMMARY_OUTCOME`, invokes `render-final-summary.sh --post-publish-only`, then exits; call it from every `fail()` path and from `design-step5c.sh` when `_publish_rc` is `2` or another unexpected hard code.
- **Suggested revision**: Address the concern above.


### FINDING_36: **risk-integration** `skills/implement/scripts/stall-recovery-report.sh:2096-2124` and `skills/design/scripts/design-failure-report.sh:115-134` — The plan requires the design Tier B sensitive corpus to include `issue-body.txt`, `composed-plan.md`, and related raw design inputs, but `build_sensitive_corpus_from_evidence()` only pulls `plan.txt`, `feature-description.txt`, `source-env.sh`, and a few implement-centric artifacts. `design-failure-report.sh` also truncates `design-failure-sensitive-corpus.env` to empty in `prepare_root_cause()` instead of seeding design-specific sensitive inputs. Tier B validation for `/design` can miss tokens from issue bodies or composed plans and fail to reject leaked content in chat-print or duplicate occurrence comments. **Suggested fix:** Extend generic-profile corpus discovery for `$DESIGN_TMPDIR` to include `issue-body.txt`, `composed-plan.md`, and other plan-listed design artifacts, or have `design-failure-report.sh` populate `design-failure-sensitive-corpus.env` before `compose-report`.
- **Reviewer**: dyn-design-reporting-output.txt
- **Concern**: - **risk-integration** `skills/implement/scripts/stall-recovery-report.sh:2096-2124` and `skills/design/scripts/design-failure-report.sh:115-134` — The plan requires the design Tier B sensitive corpus to include `issue-body.txt`, `composed-plan.md`, and related raw design inputs, but `build_sensitive_corpus_from_evidence()` only pulls `plan.txt`, `feature-description.txt`, `source-env.sh`, and a few implement-centric artifacts. `design-failure-report.sh` also truncates `design-failure-sensitive-corpus.env` to empty in `prepare_root_cause()` instead of seeding design-specific sensitive inputs. Tier B validation for `/design` can miss tokens from issue bodies or composed plans and fail to reject leaked content in chat-print or duplicate occurrence comments. **Suggested fix:** Extend generic-profile corpus discovery for `$DESIGN_TMPDIR` to include `issue-body.txt`, `composed-plan.md`, and other plan-listed design artifacts, or have `design-failure-report.sh` populate `design-failure-sensitive-corpus.env` before `compose-report`.
- **Suggested revision**: Address the concern above.


### FINDING_38: **risk-integration** `skills/design/scripts/design-failure-report.sh:174-193` — On the terminal path, `design-failure-report.sh` always emits `DESIGN_FAILURE_REPORT_DECISION=terminal-failure` and writes `design-failure-terminal-report.env` when `compose-report` exits `0`, even if `stall-recovery-report.sh` returned `STALL_RECOVERY_REPORT_STATUS=skipped_operator_action` or `fallback-print-required` because `ROOT_CAUSE_HINT=operator-action` or Tier B filing failed. That breaks operator-action skip semantics and can mark a run as terminal-reported when no issue was filed and no operator-action audit was written by the design gate. **Suggested fix:** Parse `design-failure-compose.env` after compose and branch on `STALL_RECOVERY_REPORT_STATUS`: map `skipped_operator_action` to `write_operator_action_audit`, map `fallback-print-required` to `write_fallback_chat`, and only write the terminal sentinel when status is `filed`, `dry-run`, or another explicit success token.
- **Reviewer**: dyn-design-reporting-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/design-failure-report.sh:174-193` — On the terminal path, `design-failure-report.sh` always emits `DESIGN_FAILURE_REPORT_DECISION=terminal-failure` and writes `design-failure-terminal-report.env` when `compose-report` exits `0`, even if `stall-recovery-report.sh` returned `STALL_RECOVERY_REPORT_STATUS=skipped_operator_action` or `fallback-print-required` because `ROOT_CAUSE_HINT=operator-action` or Tier B filing failed. That breaks operator-action skip semantics and can mark a run as terminal-reported when no issue was filed and no operator-action audit was written by the design gate. **Suggested fix:** Parse `design-failure-compose.env` after compose and branch on `STALL_RECOVERY_REPORT_STATUS`: map `skipped_operator_action` to `write_operator_action_audit`, map `fallback-print-required` to `write_fallback_chat`, and only write the terminal sentinel when status is `filed`, `dry-run`, or another explicit success token.
- **Suggested revision**: Address the concern above.


### FINDING_4: correctness: skills/design/scripts/design-step-validator-autofix.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Validator autofix script lacks record-escalation and operator Cancel sentinel writes required by plan. Autofix exhaustion on an otherwise successful run can file escalation-success without ledger evidence; Cancel does not block escalation. Implement record-escalation for non-ok autofix statuses and operator-action artifacts on Cancel.
- **Suggested revision**: Address the concern above.


### FINDING_41: **security** `skills/implement/scripts/stall-recovery-report.sh:2096-2124` — `build_sensitive_corpus_from_evidence` does not ingest `issue-body.txt` or `composed-plan.md`, even though `SECURITY.md` and the design reporting contract mark both as sensitive Tier B inputs. The helper only pulls `plan.txt`, `feature-description.txt`, `source-env.sh`, and a few other artifacts. If bounded Tier B text ever echoes issue-body or composed-plan content that is not also present in the scanned files, `sensitive_token_rejects_file` will not fail closed. **Suggested fix:** extend `build_sensitive_corpus_from_evidence` to append `issue-body.txt`, `composed-plan.md`, and any other design-only sensitive artifacts named in the contract; add harness cases that place unique secrets only in those files and assert Tier B compose/validate rejects the body.
- **Reviewer**: dyn-tierb-safety-output.txt
- **Concern**: - **security** `skills/implement/scripts/stall-recovery-report.sh:2096-2124` — `build_sensitive_corpus_from_evidence` does not ingest `issue-body.txt` or `composed-plan.md`, even though `SECURITY.md` and the design reporting contract mark both as sensitive Tier B inputs. The helper only pulls `plan.txt`, `feature-description.txt`, `source-env.sh`, and a few other artifacts. If bounded Tier B text ever echoes issue-body or composed-plan content that is not also present in the scanned files, `sensitive_token_rejects_file` will not fail closed. **Suggested fix:** extend `build_sensitive_corpus_from_evidence` to append `issue-body.txt`, `composed-plan.md`, and any other design-only sensitive artifacts named in the contract; add harness cases that place unique secrets only in those files and assert Tier B compose/validate rejects the body.
- **Suggested revision**: Address the concern above.


### FINDING_42: **security** `scripts/file-failure-report-cross-repo.sh:117` — Tier B duplicate `+1 occurrence` comments call `validate-tier-b-public-file` without `--profile generic` or `--artifact-prefix design-failure`. Inside `cmd_validate_tier_b_public_file`, the rebuilt corpus uses `artifact_path` with the default `stall-recovery` prefix, so design-prefixed `design-failure-classification.env`, ledger, and marker files are skipped during duplicate-comment validation. Initial compose for `/design` validates with the correct prefix; duplicate comments get a weaker corpus and are more likely to accept text that matches design-only classification or ledger fields. **Suggested fix:** pass `--profile generic --artifact-prefix design-failure` (or an explicit `--sensitive-corpus-file` pointing at the persisted effective corpus from compose) from `file-failure-report-cross-repo.sh` when the body or `--sensitive-corpus-file` basename uses the `design-failure` prefix; add a dedup test where a sensitive token exists only in `design-failure-classification.env` and assert the duplicate comment is rejected.
- **Reviewer**: dyn-tierb-safety-output.txt
- **Concern**: - **security** `scripts/file-failure-report-cross-repo.sh:117` — Tier B duplicate `+1 occurrence` comments call `validate-tier-b-public-file` without `--profile generic` or `--artifact-prefix design-failure`. Inside `cmd_validate_tier_b_public_file`, the rebuilt corpus uses `artifact_path` with the default `stall-recovery` prefix, so design-prefixed `design-failure-classification.env`, ledger, and marker files are skipped during duplicate-comment validation. Initial compose for `/design` validates with the correct prefix; duplicate comments get a weaker corpus and are more likely to accept text that matches design-only classification or ledger fields. **Suggested fix:** pass `--profile generic --artifact-prefix design-failure` (or an explicit `--sensitive-corpus-file` pointing at the persisted effective corpus from compose) from `file-failure-report-cross-repo.sh` when the body or `--sensitive-corpus-file` basename uses the `design-failure` prefix; add a dedup test where a sensitive token exists only in `design-failure-classification.env` and assert the duplicate comment is rejected.
- **Suggested revision**: Address the concern above.


### FINDING_43: **risk-integration** `skills/design/scripts/design-failure-report.sh:133-134` — `prepare_root_cause` truncates `design-failure-sensitive-corpus.env` to empty before compose, so cross-repo filing receives an empty explicit corpus file (`stall-recovery-report.sh:2669-2673`). Compose still rebuilds an effective corpus internally, but the on-disk artifact does not reflect the full sensitive set documented for `/design`. That makes duplicate-path validation and operator debugging depend entirely on the dynamic rebuild path, which is prefix-sensitive and incomplete for `issue-body.txt` / `composed-plan.md` as above. **Suggested fix:** after building the effective corpus in compose, persist it to `design-failure-sensitive-corpus.env` (or a sibling `.effective` file) and pass that path to cross-repo filing and duplicate validation.
- **Reviewer**: dyn-tierb-safety-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/design-failure-report.sh:133-134` — `prepare_root_cause` truncates `design-failure-sensitive-corpus.env` to empty before compose, so cross-repo filing receives an empty explicit corpus file (`stall-recovery-report.sh:2669-2673`). Compose still rebuilds an effective corpus internally, but the on-disk artifact does not reflect the full sensitive set documented for `/design`. That makes duplicate-path validation and operator debugging depend entirely on the dynamic rebuild path, which is prefix-sensitive and incomplete for `issue-body.txt` / `composed-plan.md` as above. **Suggested fix:** after building the effective corpus in compose, persist it to `design-failure-sensitive-corpus.env` (or a sibling `.effective` file) and pass that path to cross-repo filing and duplicate validation.
- **Suggested revision**: Address the concern above.


### FINDING_5: correctness: skills/design/scripts/design-failure-report.sh:115-134
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Sensitive corpus is emptied instead of populated from plan-listed design artifacts; issue-body.txt and composed-plan.md are not in shared corpus builder. Tier B validation may fail to reject reports containing issue body or composed plan text. Populate design-failure-sensitive-corpus.env from plan artifacts before compose; extend build_sensitive_corpus_from_evidence if needed.
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: skills/design/scripts/design-failure-report.sh:177-184
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Teardown gate only uses chat-print (Tier B); no Tier A issue-input path for larch dev clones. Design runs in larch source never get local full-context Tier A issues per plan. Add is-larch-dev-clone check and issue-input compose path before Tier B fallback.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: skills/implement/scripts/stall-recovery-report.sh:1016-1019
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] validate-terminal-state rejects valid macOS DESIGN_TMPDIR failure-detail paths before key-specific confinement validation A failed publish staged with FAILURE_DETAIL_LOG=<OPERATOR_REPO_PATH>/.../design-log-publish.failure.log fails validation, so no terminal report is filed Exempt FAILURE_DETAIL_LOG from generic raw-path rejection and rely on validate_tmpdir_local_file, or store a relative artifact name
- **Suggested revision**: Address the concern above.


