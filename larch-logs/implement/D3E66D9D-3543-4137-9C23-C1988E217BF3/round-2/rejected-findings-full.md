### [rejected] FINDING_16

### FINDING_16: risk-integration: scripts/dispatch-code-voters.sh:164-180
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] larch_err ordering moved before append-tool-failure vs previous branch. Minor change in stderr vs issues-log ordering for operators. Accept or restore previous order if contract matters.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_17

### FINDING_17: risk-integration: scripts/test-dispatch-code-voters.sh (Part A vs diff)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Feature asked per-case subshell isolation and sibling harness updates; only global unset in one harness appears. Coverage story does not match stated spec. Follow spec or document deviation in test-dispatch-code-voters.md.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_20

### FINDING_20: risk-integration: scripts/test-dispatch-code-voters.sh:27-32
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Plan asked subshell env isolation; only global unset at startup Lower isolation if later code exports parent vars; minor plan fidelity Use subshells per invocation or document why global unset is sufficient
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_23

### FINDING_23: security: scripts/dispatch-code-voters.sh:108-119
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Basename allowlist can match non-harness review dirs if operators reuse harness-style names. Parse-rate execution-issues append silently skipped for those runs. Tighten detection or document reserved basename patterns.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_3

### FINDING_3: architecture: scripts/dispatch-code-voters.sh:108-120
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Basename patterns test-collect-* / test-check-* / test-tally-* can suppress production parse-rate issue appends if --review-tmpdir leaf matches. Legitimate tmpdir naming collision drops Warnings from central execution-issues. Narrow patterns or add explicit harness-only sentinel; document tradeoff.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_4

### FINDING_4: architecture: scripts/test-dispatch-code-voters.sh:27-32
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Feature asked for per-case subshell env isolation; implementation uses one global unset. Minor mismatch with written requirement wording only if compliance text matters. Use subshells per test or align requirement doc to global unset.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_9

### FINDING_9: code-quality: scripts/test-dispatch-code-voters.sh:27-32
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plan asked env-isolated subshells per test case; diff uses one-time unset at harness start. Minor plan/spec drift; subshells would isolate per-test exports if any appear later. Match plan with subshell wrappers or document intentional global unset in plan.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

