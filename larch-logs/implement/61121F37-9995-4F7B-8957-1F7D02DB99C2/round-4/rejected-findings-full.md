### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: risk-integration: (plan acceptance #6)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Manual /design and /implement E2E cost visibility is an acceptance gate but not CI-enforced. Shipping without manual verification could regress ROOT CAUSE G/C in real chat despite green unit tests. Keep as explicit pre-merge checklist; document in PR test plan.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: risk-integration: scripts/test-render-cost-line-callsites.sh:40-50
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Orchestrator cost-line emit and NEVER #20 are prose grep pins only. An orchestrator can still paraphrase or omit costs while callsite lints pass. Accept policy lint limit or add future E2E/golden transcript test.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: risk-integration: skills/implement/scripts/test-write-final-report.sh:503-509 / skills/design/scripts/test-render-final-summary.sh:398-404
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Chat-print FD-3 vs FD-1 branches are untested because harnesses disable quiet mode. A regression in LARCH_QUIET_PID handling could silence chat output in production quiet runs. Optional sub-test with quiet init enabled asserting non-empty print path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: correctness: skills/implement/scripts/write-final-report.sh:186-190
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Valid zero-total token JSON is treated as unavailable and renders Cost N/A. Nonzero-structure, all-zero totals after successful token-report.sh yield N/A instead of an explicit $0.00 breakdown. Limit --cost-unavailable to missing/corrupt/stderr-signaled data, or document and test zero-spend as N/A.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: skills/implement/scripts/write-final-report.sh:236-436
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] skills/design/scripts/render-final-summary.sh:213-365 Duplicated refresh_issue_counts and compose_self_fallback mirror render-run-summary.sh; design lacks implement-style schema ordering tests for self-compose. Future renderer schema edits can desync one fallback while tests still pass on the other skill. Add design assert_schema_ordered for empty-file self-compose across outcomes or extract a shared fallback helper in a follow-up.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: architecture: skills/implement/SKILL.md:1758-1760
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] ROOT CAUSE G fix relies on orchestrator prose; scripts cannot force verbatim cost emit. Model ends run after Bash without grep/re-emit; user sees collapsed Bash only with no cost line in plain text. Keep script guarantees; optional transcript lint; treat as residual model-compliance risk.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: correctness: skills/implement/SKILL.md:2162-2165
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Step 17 .step17-printed uses Bash success plus cost-line grep, not plan STATUS=ok envelope A future exit-0 path with broken summary could set sentinel and block Step 18 --print-stdout on bail paths Align SKILL edge-case text with implementation or restore STATUS=ok parsing before touch
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: skills/implement/scripts/test-write-final-report.sh:436-506
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Large harness duplication of plugin stub setup across cases. Higher maintenance cost when adding the next regression case. Extract shared setup helpers within each test script.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: correctness: skills/implement/SKILL.md:1758-1760
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] ROOT CAUSE G fix is orchestrator prose only; no mechanical emit after Bash. Model skips verbatim cost-line emit; user sees collapsed Bash output without per-agent breakdown despite successful write-final-report.sh. Add a small emit helper invoked from SKILL Bash blocks, or accept policy-only enforcement.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_9: correctness: skills/design/scripts/render-final-summary.sh:337-345
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Self-composed fallback does not normalize empty DURATION to N/A. Timing report missing; fallback shows - **Duration**: with an empty value. Normalize empty DURATION to N/A before printf, matching render-run-summary.sh na().
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

