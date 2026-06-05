### FINDING_1: code-quality: scripts/test-design-structure.sh:89-120
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] No negative self-test for assert_postplan_thin_fence despite plan/acceptance requiring one Removing an rc arm from a merged fence outside Step 2b could pass CI because Gate B/discussion are only grep-pinned Add postplan self-tests mirroring Step 3.6: fixture missing rc arm must fail; optionally scope assert_postplan_thin_fence to approval-gates and discussion-rounds regions
- **Suggested revision**: Address the concern above.


### FINDING_10: correctness: skills/design/SKILL.md:1397-1421
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 5c still conditionally runs prompt-side invoke-plan-validator.sh based on review_budget, while design-publish.sh always validates composed-plan.md. Orchestrator may double-validate, skip pre-publish Fix/Override/Cancel handling, or rely on a removed run-params field for composed-plan validation. Remove the review_budget-gated item-2 validator block; delegate composed-plan validation to design-publish.sh and align Step 5c defect handling with publish exit 4 / result-env contract.
- **Suggested revision**: Address the concern above.


### FINDING_11: correctness: skills/design/scripts/design-postplan-emit.sh:47-58
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] partition_requested fallback parsing accepts bare true/false only, not quoted JSON string booleans. run-params.json with "partition_requested": "true" routes as false, suppressing rc 13 partition Split despite --partition. Extend json_boolean_or_sed (and plan-review-loop partition reader) to accept quoted true/false strings, or reject non-boolean values at write time.
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: skills/design/SKILL.md:1124
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Gate B prose requires Step 2b.5 to return after merged re-emit, but merged --with-plan-size rc 0 already writes step-2b.5 sentinel without standalone Step 2b.5. Orchestrator may invoke redundant standalone Step 2b.5 after a clean merged Gate B re-emit. Reword Gate B continuation prose to distinguish merged rc 0 sentinel write from retained Override standalone Step 2b.5 path.
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: scripts/test-design-structure.sh:89-120
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] assert_postplan_thin_fence only on SKILL Step 2b Gate B/discussion delegate to SKILL arms; incomplete fence copy may pass CI Scope assert_postplan_thin_fence to approval-gates and discussion-rounds or add negative fixture
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: scripts/test-design-structure.sh:756-761
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Missing structure pins for Split-return and Override sentinels Split Refine may omit step-2b.5 sentinel; pause/resume replays Step 2b Add plan-matrix grep pins or integration assertions on .completed files
- **Suggested revision**: Address the concern above.


### FINDING_17: risk-integration: skills/design/SKILL.md:953-955
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Retained Step 2b.5 pause example lacks REPO threading Override path pause may omit --repo on forked issues Align Step 2b.5 example with merged prelude REPO passthrough
- **Suggested revision**: Address the concern above.


### FINDING_18: security: skills/design/scripts/design-postplan-emit.sh:312-319
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] New plan-size rc2/rc3 path appends check-plan-size.validation.log via append-tool-failure.sh without --redact unlike validator Override and other design append sites. Tool stderr or captured output containing tokens or internal URLs can land verbatim in execution-issues.md and operator-visible session artifacts before publish-time redaction. Add --redact to append-tool-failure.sh; update plan-review-loop.sh and SKILL.md Step 2b.5 retained procedure to match; extend tests to assert redaction runs.
- **Suggested revision**: Address the concern above.


### FINDING_19: security: skills/design/scripts/plan-review-loop.sh:629-636
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Direct check-plan-size rc2/rc3 append omits --redact while other plan-review-loop append paths use it. Same secret-leak surface as merged driver when size check fails under set -e-safe warn-and-continue. Pass --redact on this append; keep helper stdout/stderr redirected to /dev/null.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: skills/design/scripts/plan-review-loop.sh:600-609
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] partition_requested parsing duplicated instead of reusing json_boolean_or_sed; jq semantics differ from merged driver String "true" in run-params.json could enable partition in plan-review-loop but not in design-postplan-emit --with-plan-size Extract json_boolean_or_sed to shared lib and use it in both scripts
- **Suggested revision**: Address the concern above.


### FINDING_21: correctness: skills/design/scripts/design-postplan-emit.sh:150-162
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] _postplan_fatal always exits 2 including missing plan.txt and pause without issue. In --with-plan-size runs the Step 2b fence labels rc 2 as configuration error and skips rc 1 op-failure handling with specific diagnostics. Use _postplan_exit_merged_failure (rc 1) for operational fatals in merged mode; reserve exit 2 for true argv/config failures via fail().
- **Suggested revision**: Address the concern above.


### FINDING_22: architecture: skills/design/scripts/design-postplan-emit.sh:47-58
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] skills/design/scripts/plan-review-loop.sh:600-610 Partition flag parsing differs between merged driver and plan-review-loop. String JSON partition_requested true can trigger plan-size-trigger in Step 3 but not rc 13 on merged Step 2b/Gate B paths. Share one boolean partition reader used by design-postplan-emit.sh and plan-review-loop.sh.
- **Suggested revision**: Address the concern above.


### FINDING_23: risk-integration: skills/design/SKILL.md:1124-1125
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Step 3.5 Gate B intro still mandates standalone Step 2b.5 after every design-postplan-emit re-emit. Orchestrator may double-run plan-size or write sentinels out of order despite merged --with-plan-size in approval-gates. Update Step 3.5 prose to match approval-gates merged fence; standalone 2b.5 only for Override and plan-size-trigger handoffs.
- **Suggested revision**: Address the concern above.


### FINDING_27: correctness: skills/design/SKILL.md:882-888
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Merged Step 2b captures design-postplan-emit.sh without LARCH_QUIET_DISABLE=1 while merged mode emits display on FD 3 only. Under default larch_quiet_init, _postplan_out is empty; operators see no hard-trigger, partition, soft-advisory, or WARN text even though SKILL.md says the driver already printed them. Wrap every merged design-postplan-emit.sh invocation as env LARCH_QUIET_DISABLE=1 ... in command substitution, matching run-step3-review.sh:269, and pin in assert_postplan_thin_fence.
- **Suggested revision**: Address the concern above.


### FINDING_28: correctness: skills/design/SKILL.md:651
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 2a still claims review_budget skips the Step 2b plan-command validator on quick. Agents may treat validation as optional despite unconditional design-postplan-emit.sh behavior after #3418. Update Step 2a prose to state validation always runs; remove or narrow review_budget references to whatever Step 3 still uses.
- **Suggested revision**: Address the concern above.


### FINDING_29: correctness: skills/design/SKILL.md:1397
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 5c composed-plan validation is still gated on review_budget != quick. Runs with stale review_budget=quick in run-params.json may skip composed-plan validation inconsistent with design-publish.sh. Rewrite Step 5c to unconditional validation aligned with design-publish and flags.md.
- **Suggested revision**: Address the concern above.


### FINDING_30: architecture: scripts/test-design-structure.sh:89-126
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan required assert_postplan_thin_fence plus a negative fixture missing a case arm; only positive Step 2b assertion exists. A future edit can drop rc 10-13 arms while structure tests stay green. Add run_postplan_thin_fence_self_tests with a fixture missing one case arm and expect failure.
- **Suggested revision**: Address the concern above.


### FINDING_4: correctness: skills/design/SKILL.md:651
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 2a still documents review_budget quick vs full gating validator after review_budget removal and unconditional validation Orchestrator may expect quick-skip validator behavior that no longer exists Update Step 2a and related prose to unconditional validator contract
- **Suggested revision**: Address the concern above.


### FINDING_5: code-quality: scripts/test-design-structure.sh:560-570
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] assert_postplan_thin_fence applied only to Step 2b; Gate B/discussion/Step 1e use weaker grep pins Gate B could drop rc arms or reintroduce stdout KV merge without failing structure test Run assert_postplan_thin_fence on scoped regions in approval-gates.md and discussion-rounds.md
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: skills/design/SKILL.md:651
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 2a still documents review_budget gating Step 2b validator skip, but design-postplan-emit.sh validates unconditionally and write-run-params.sh no longer emits review_budget. An orchestrator following Step 2a may believe quick-tier runs skip plan-command validation at Step 2b, conflicting with actual driver behavior and tests that assert quick is ignored. Update Step 2a to remove or replace review_budget gating prose with the unconditional validation contract documented in flags.md and design-postplan-emit.md.
- **Suggested revision**: Address the concern above.


