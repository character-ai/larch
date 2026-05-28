### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: skills/design/scripts/plan-review-loop.sh:505-1050
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] _run_plan_review_round is ~545 lines and still monolithic after the refactor. Future multi-round changes will keep touching one giant function; regressions in branch order or per-round cleanup become hard to review and test in isolation. Split into phase helpers or a sourced library; keep the outer while loop thin.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: code-quality: skills/design/scripts/test-plan-review-loop.sh:5351-5374
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] write_dispatch_combined_threshold duplicates write_dispatch for one KV. Future dispatch stub changes require two heredoc edits. Parameterize COMBINED_FALLBACK_COUNT in write_dispatch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: correctness: skills/design/scripts/plan-review-loop.sh:1065-1069
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Legacy mode maps tally-error to LOOP_STATUS=complete. Direct caller without --round-cap gets complete not tally-error; Gate B bypass keyed on LOOP_STATUS may not fire. Propagate tally-error in legacy or extend SKILL to check TALLY_PLAN_REVIEW_STATUS for bypass.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: correctness: skills/design/scripts/plan-review-loop.sh:396-402
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] plan-validator-defects exits without restoring plan after revise. User sees validator prompt but plan.txt already mutated by in-loop auto-apply. Document or restore from before-revise snapshot on validator exit.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: risk-integration: skills/design/scripts/plan-review-loop.sh:376-412
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No test forces plan-size-trigger or plan-validator-defects from _run_post_apply_pipeline. Mid-loop validator/size exits could break SKILL.md Step 3 handling without harness signal. Stub check-plan-size.sh and invoke-plan-validator.sh in test-plan-review-loop.sh to assert LOOP_STATUS and .step3-plan-review-result.env keys.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: risk-integration: skills/design/scripts/test-plan-review-loop.sh:532-544
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Legacy single-pass test does not prove revise/auto-apply was skipped. Legacy mode could accidentally invoke revise without failing the harness. Stub revise to exit 99 when called in a run without --round-cap on argv.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_30: security: skills/design/scripts/plan-review-loop.sh:11-16
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] LARCH_PLAN_REVIEW_*_SH env vars can replace production helpers with arbitrary executables. Env poisoning before /design runs attacker-controlled revise/tally scripts with session paths. Limit overrides to test harnesses or unset them in the SKILL.md Bash prelude.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_37

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_37: correctness: skills/design/scripts/plan-review-loop.sh:255-258
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] symlink sources skipped during snapshot with WARN only Incomplete round-N tree may still publish partial forensics Fail closed or refuse publish when snapshot incomplete
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_39

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_39: correctness: skills/design/scripts/plan-review-loop.sh:1065-1068
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] legacy mode sets LOOP_STATUS=complete on tally-error Callers omitting --round-cap skip tally rollback behavior documented for multi-round Propagate tally-error in legacy block or document legacy exception
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_42

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_42: correctness: skills/design/scripts/plan-review-loop.sh:1122
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] ACCEPTED_COUNT grep pattern looser than inner round counter Malformed FINDING heading could affect convergence Use grep -cE '^### FINDING_[0-9]+:' consistently
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_48

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_48: correctness: skills/design/scripts/plan-review-loop.sh:45,507
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Global _dedup_failed=0 remains despite plan requiring per-round-only init in _run_plan_review_round. Future refactor calling round helpers without the outer loop could inherit stale dedup degradation state. Remove line 45 global init; keep only line 507 reset.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: code-quality: skills/design/scripts/plan-review-loop.sh:202-236
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] _parse_collect_records rewrites a Python file on every collector evidence count. Extra temp files and Python startup per inner round add noise and failure modes under load. Use a stable parser script or bash-only STATUS=OK counting.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

