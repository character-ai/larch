### FINDING_1: code-quality: skills/design/scripts/plan-review-loop.sh:505-1050
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] _run_plan_review_round is ~545 lines and still monolithic after the refactor. Future multi-round changes will keep touching one giant function; regressions in branch order or per-round cleanup become hard to review and test in isolation. Split into phase helpers or a sourced library; keep the outer while loop thin.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/test-design-multi-round-integration.sh:1-118
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Integration harness does not exercise design-log-publish or plan acceptance #9 parity cases. Allowlist drift between snapshot and publish, symlink fail-closed behavior, and unknown-file rejection can regress without this harness failing. Build fixtures from real loop output; run publish; diff sorted file lists; add symlink/unknown/cross-entry cases per plan.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/design/scripts/test-plan-review-loop.sh:468-493
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Multi-round tally-error contract from the plan is untested; existing tally stub expects LOOP_STATUS=complete without --round-cap. Multi-round tally-error early exit (no revise) can break while legacy tests still pass. Add run_loop with --round-cap and assert LOOP_STATUS=tally-error, no revise call, and result env keys.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/design/scripts/test-plan-review-loop.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Plan-listed multi-round tests (streak converge, revision-failed, OOS accumulate, dedup reset, severity default) are largely missing. Convergence, revise parsing, and OOS dedup regressions ship undetected until manual /design runs. Add stub scenarios from acceptance #8 using LARCH_PLAN_REVIEW_REVISE_SH and controlled ACCEPTED_COUNT fixtures.
- **Suggested revision**: Address the concern above.

### FINDING_5: correctness: skills/design/scripts/plan-review-loop.sh:1174-1178
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] DEGRADED_PANEL=1 resets convergence_streak but not CONVERGENCE_STREAK. round-summary.env and stdout can show a non-zero CONVERGENCE_STREAK after a degraded round, confusing Gate B passive-summary. Assign CONVERGENCE_STREAK whenever convergence_streak changes.
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: skills/design/scripts/plan-review-loop.sh:1098-1104
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Multi-round panel-failed exits without snapshot or round-summary.env. Operators lose per-round forensics on panel dispatch failure mid-loop. Call _snapshot_round_dir and _write_round_summary before terminal exit, matching tally-error/revision-failed.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: skills/design/scripts/plan-review-loop.sh:202-236
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] _parse_collect_records rewrites a Python file on every collector evidence count. Extra temp files and Python startup per inner round add noise and failure modes under load. Use a stable parser script or bash-only STATUS=OK counting.
- **Suggested revision**: Address the concern above.

### FINDING_8: architecture: skills/design/references/approval-gates.md:3717-3745
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Passive-summary docs precede auto-apply Presentation without an explicit skip guard. Orchestrator may auto-apply findings already applied by the inner loop on converged/cap-hit. Add explicit short-circuit before auto-apply Presentation for converged|cap-hit.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/relevant-checks.sh:47-71
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] relevant-checks does not map plan-review-loop or allowlist lib changes to new harness targets. CI may skip test-lib-design-round-artifacts and test-design-multi-round-integration on focused edits. Add case arms for those paths to append the new make targets.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: skills/design/scripts/test-plan-review-loop.sh:5351-5374
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] write_dispatch_combined_threshold duplicates write_dispatch for one KV. Future dispatch stub changes require two heredoc edits. Parameterize COMBINED_FALLBACK_COUNT in write_dispatch.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: skills/design/scripts/plan-review-loop.sh:1127-1142
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Zero-findings convergence ignores DEGRADED_PANEL set in the same round. Degraded panel (fallback/dedup/voter count) with ACCEPTED_COUNT=0 and collectors OK exits LOOP_STATUS=converged REASON=zero-findings. Gate degradation on DEGRADED_PANEL=1 before zero-findings convergence or add explicit REASON; extend tests.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: skills/design/SKILL.md:1073,1099
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Stale Step 3/3.5 prose says Step 3 never revises and Gate B always auto-applies when manual_gate_b=false. After LOOP_STATUS=converged accepted-plan-findings.md still populated; agent may double-apply at Gate B. State in-loop auto-apply when --round-cap is set; converged|cap-hit use passive-summary only.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: skills/design/references/approval-gates.md:103-107
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Auto-apply path lacks explicit exclusion for converged|cap-hit. Agent follows line 103 after manual_gate_b=false and re-applies already-applied findings. Precondition auto-apply block: only complete or revision-failed; else passive-summary.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: skills/design/scripts/plan-review-loop.sh:1065-1069
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Legacy mode maps tally-error to LOOP_STATUS=complete. Direct caller without --round-cap gets complete not tally-error; Gate B bypass keyed on LOOP_STATUS may not fire. Propagate tally-error in legacy or extend SKILL to check TALLY_PLAN_REVIEW_STATUS for bypass.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: skills/design/scripts/plan-review-loop.sh:1166-1169
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Post-apply failure writes REVISE_STATUS=skipped after successful revise. round-summary.env misreports revision on plan-validator-defects/plan-size-trigger exits. Pass revise_status=ok into _write_round_summary on post-apply failure.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: skills/design/scripts/plan-review-loop.sh:396-402
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] plan-validator-defects exits without restoring plan after revise. User sees validator prompt but plan.txt already mutated by in-loop auto-apply. Document or restore from before-revise snapshot on validator exit.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: skills/design/scripts/test-plan-review-loop.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Many plan-listed multi-round tests not implemented. Streak revision-failed tally-error OOS cases unguarded in CI. Add missing harness cases from acceptance list.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: scripts/test-design-multi-round-integration.sh:95-118
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Integration test does not exercise design-log-publish parity or fail-closed. Allowlist/publish drift could ship without FINDING_18 coverage. Run publish against loop output; assert file-list parity and unknown.bin failure.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: skills/design/scripts/plan-review-loop.sh:1090-1095
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] main-agent-vote-required omits _snapshot_round_dir. round-N forensic dir missing voter/tally artifacts on main-agent exit. Call _snapshot_round_dir before terminal exit on main-agent path.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: scripts/test-design-multi-round-integration.sh:1-118
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Integration harness does not call design-log-publish or assert publish parity/fail-closed paths promised in the plan. A regression in publish staging vs loop snapshot allowlist could ship while make test-design-multi-round-integration still passes. Build publish input from a real stubbed loop run; assert sorted file-list parity, unknown.bin PUBLISH_OK=false, symlink rejection, and cross-entry round reset.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: scripts/test-design-multi-round-integration.md:15-20
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Sibling doc documents publish and symlink tests that the shell harness does not run. Contributors may assume publish integration is covered when only lib include/exclude helpers are tested. Implement the documented cases in the .sh file or narrow the .md Coverage section to match reality.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: skills/design/scripts/test-plan-review-loop.sh:532-637
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Many plan-required multi-round scenarios are absent (streak convergence, revision-failed variants, multi-round tally-error, OOS accumulation, severity default, dedup per-round reset, full result-env schema). Convergence streak, revision failure, and tally-error branch order regressions may not fail CI until manual /design runs. Add stub cases per plan acceptance #8 using LARCH_PLAN_REVIEW_REVISE_SH and tally overrides; keep legacy tally-error test and add multi-round tally-error test.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: scripts/test-lib-design-round-artifacts.sh:28-44
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Allowlist harness does not cover every included/excluded basename from lib-design-round-artifacts.md (FINDING_16). New snapshot basenames could be added to the loop without updating tests or publish failing only at runtime. Assert all documented basenames and patterns; optionally derive cases from a golden fixture produced by test-plan-review-loop stubs.
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: scripts/relevant-checks.sh:61-64
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] relevant-checks does not route plan-review-loop, design-log-publish, or lib-design-round-artifacts changes to new Makefile targets (plan acceptance #10). During /implement, edits to core loop/publish scripts may only run pre-commit/agent-lint, not test-plan-review-loop or integration harnesses. Extend run_direct_relevant_targets case arms to invoke test-plan-review-loop, test-lib-design-round-artifacts, test-design-multi-round-integration, and test-design-log-publish when matching paths change.
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: skills/design/scripts/plan-review-loop.sh:376-412
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No test forces plan-size-trigger or plan-validator-defects from _run_post_apply_pipeline. Mid-loop validator/size exits could break SKILL.md Step 3 handling without harness signal. Stub check-plan-size.sh and invoke-plan-validator.sh in test-plan-review-loop.sh to assert LOOP_STATUS and .step3-plan-review-result.env keys.
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: scripts/test-design-structure.sh:36-48
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Structure harness lacks pins for new LOOP_STATUS branch matrix and Gate B passive-summary documentation. SKILL.md or approval-gates.md could drop converged/cap-hit/revision-failed prose while tests still pass. Add contains checks for branch-matrix strings and approval-gates passive-summary section.
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: skills/design/scripts/test-plan-review-loop.sh:532-544
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Legacy single-pass test does not prove revise/auto-apply was skipped. Legacy mode could accidentally invoke revise without failing the harness. Stub revise to exit 99 when called in a run without --round-cap on argv.
- **Suggested revision**: Address the concern above.

### FINDING_28: security: skills/design/SKILL.md:973-978
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Step 3 round cleanup uses rm -rf on round-* children without rejecting symlinks. A round-N symlink to a sensitive directory causes rm -rf to delete the symlink target during Gate C re-entry cleanup. Require ! -L on each child or use find -type d under the resolved plan-review root; verify pwd -P of each child stays under _pr_phys.
- **Suggested revision**: Address the concern above.

### FINDING_29: security: skills/design/SKILL.md:1016-1018
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Sourcing .step3-plan-review-result.env executes arbitrary shell before LOOP_STATUS validation. Malicious or malformed KV content (e.g. REVISE_STATUS=ok; rm -rf /) in the handoff file runs on source. Parse allowlisted keys like stdout fallback; validate values; refuse symlinks on the handoff file.
- **Suggested revision**: Address the concern above.

### FINDING_30: security: skills/design/scripts/plan-review-loop.sh:11-16
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] LARCH_PLAN_REVIEW_*_SH env vars can replace production helpers with arbitrary executables. Env poisoning before /design runs attacker-controlled revise/tally scripts with session paths. Limit overrides to test harnesses or unset them in the SKILL.md Bash prelude.
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] security: skills/design/SKILL.md:984-986
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Pre-existing source of .step3-review-cap.env shares injection/symlink risks. Same as result env if cap file is attacker-controlled. Apply the same parse-don't-source pattern when touching Step 3 again.
- **Suggested revision**: Address the concern above.

### FINDING_32: correctness: skills/design/scripts/plan-review-loop.sh:1098-1104
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] panel-failed path calls _count_collector_evidence using uncleared _last_collect_out from a prior round After round 1 succeeds and round 2 panel dispatch fails COLLECT_OK_COUNT in .step3-plan-review-result.env can show round-1 collector OK counts while LOOP_STATUS=panel-failed misleading operators and any consumer trusting collector KVs Clear _last_collect_out each round and skip or zero collector counts on panel-failed
- **Suggested revision**: Address the concern above.

### FINDING_33: architecture: skills/design/scripts/plan-review-loop.sh:1090-1095
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] main-agent-vote-required exits without _snapshot_round_dir Gate B passive-summary and design-log-publish lack ballot accepted findings and tally for that round Snapshot before _write_round_summary on main-agent-vote-required
- **Suggested revision**: Address the concern above.

### FINDING_34: architecture: skills/design/scripts/plan-review-loop.sh:1098-1104
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] multi-round panel-failed omits _snapshot_round_dir Publish and Gate B see only header-only findings-classification.tsv for failed rounds Snapshot best-effort before terminal panel-failed exit
- **Suggested revision**: Address the concern above.

### FINDING_35: correctness: skills/design/scripts/plan-review-loop.sh:391-394
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] EMIT_PLAN missing-diff-lines mapped to LOOP_STATUS=plan-size-trigger User gets Step 2b.5 Split/Cancel instead of an emit/revise failure path after auto-apply Add distinct LOOP_STATUS e.g. emit-plan-failed and wire SKILL.md branch matrix
- **Suggested revision**: Address the concern above.

### FINDING_36: risk-integration: skills/design/scripts/plan-review-loop.sh:397
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] invoke-plan-validator under set -e without rc guard Validator/driver non-zero exit aborts loop without write_step3_result.env SKILL treats as panel-failed Wrap validator with set +e parse VALIDATE_STATUS and _terminal_exit plan-validator-defects
- **Suggested revision**: Address the concern above.

### FINDING_37: correctness: skills/design/scripts/plan-review-loop.sh:255-258
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] symlink sources skipped during snapshot with WARN only Incomplete round-N tree may still publish partial forensics Fail closed or refuse publish when snapshot incomplete
- **Suggested revision**: Address the concern above.

### FINDING_38: correctness: skills/design/scripts/plan-review-loop.sh:383-384
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] global duplicate-line awk dedup in post-apply pipeline Intentional repeated plan lines removed corrupting plan.txt before next round Narrow dedup scope or defer to Gate B LLM dedup
- **Suggested revision**: Address the concern above.

### FINDING_39: correctness: skills/design/scripts/plan-review-loop.sh:1065-1068
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] legacy mode sets LOOP_STATUS=complete on tally-error Callers omitting --round-cap skip tally rollback behavior documented for multi-round Propagate tally-error in legacy block or document legacy exception
- **Suggested revision**: Address the concern above.

### FINDING_40: risk-integration: skills/design/scripts/test-plan-review-loop.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Missing harness cases for streak revision-failed multi-round tally-error OOS accumulation Load-bearing branches can regress without CI signal Add stub cases from implementation plan acceptance list
- **Suggested revision**: Address the concern above.

### FINDING_41: risk-integration: scripts/test-design-multi-round-integration.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] No design-log-publish parity or fail-closed tests Allowlist drift between snapshot and publish may ship undetected Extend harness with publish staging and sorted path parity per plan
- **Suggested revision**: Address the concern above.

### FINDING_42: correctness: skills/design/scripts/plan-review-loop.sh:1122
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] ACCEPTED_COUNT grep pattern looser than inner round counter Malformed FINDING heading could affect convergence Use grep -cE '^### FINDING_[0-9]+:' consistently
- **Suggested revision**: Address the concern above.

### FINDING_43: architecture: skills/design/scripts/plan-review-loop.sh:1166-1168
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] post-apply failure writes REVISE_STATUS=skipped after successful revise round-summary.env misstates revise outcome Pass ok or actual revise status when post-apply fails only
- **Suggested revision**: Address the concern above.

### FINDING_44: correctness: skills/design/scripts/test-plan-review-loop.sh:532-639
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Missing plan-required multi-round test cases (streak converge, revision-failed x2, multi-round tally-error, OOS dedup, severity default, dedup per-round reset, durable env keys). CI passes while streak/revision-failed/tally-error branches regress; production /design mis-converges or mis-routes Gate B. Add stub scenarios from plan acceptance #8; run tally stub with --round-cap and assert LOOP_STATUS=tally-error.
- **Suggested revision**: Address the concern above.

### FINDING_45: correctness: scripts/test-design-multi-round-integration.sh:1-118
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Integration harness does not invoke design-log-publish.sh or assert source/staged file-list parity per FINDING_18. Allowlist drift between snapshot and publish ships until a full make test or manual publish run fails in production. Build tmpdir from loop output; run publish; diff sorted file lists; add unknown/symlink/cross-entry cases.
- **Suggested revision**: Address the concern above.

### FINDING_46: correctness: scripts/test-design-multi-round-integration.md:15-20
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Markdown claims publish and symlink tests that the .sh file does not implement. Reviewers and operators assume publish integration is regression-tested when it is not. Implement publish/symlink tests or correct the markdown to match the script.
- **Suggested revision**: Address the concern above.

### FINDING_47: risk-integration: scripts/relevant-checks.sh:61-70
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] No direct-target mapping for plan-review-loop / design-log-publish / lib-design-round-artifacts changes. Edits to core scripts skip test-plan-review-loop and new harnesses under relevant-checks-only workflows. Add case arms mapping those paths to test-plan-review-loop test-lib-design-round-artifacts test-design-multi-round-integration.
- **Suggested revision**: Address the concern above.

### FINDING_48: correctness: skills/design/scripts/plan-review-loop.sh:45,507
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Global _dedup_failed=0 remains despite plan requiring per-round-only init in _run_plan_review_round. Future refactor calling round helpers without the outer loop could inherit stale dedup degradation state. Remove line 45 global init; keep only line 507 reset.
- **Suggested revision**: Address the concern above.

### FINDING_49: code-quality: skills/design/SKILL.md:1046-1055
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Nine duplicate focus-area enum anchor comments added inside Step 3 bash block. Noise in normative skill; harder to review Step 3 driver instructions. Collapse to a single anchor comment line.
- **Suggested revision**: Address the concern above.

