### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: risk-integration: skills/design/scripts/test-snapshot-plan-round.sh:1-61
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Atomic mktemp+rename under failure/interrupt (FINDING_12) is not exercised. Failed write-after could leave corrupt snapshots; next-round assessor compares wrong plans. Simulate mv/cp failure; assert destination absent and cursor unchanged.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: security: skills/design/scripts/assess-plan-round.sh:204-213
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Dispatch KV paths override tally input paths without DESIGN_TMPDIR re-anchoring. Same-UID tampering of assessor-round-N.dispatch.kv could make tally read arbitrary local files. Ignore KV path overrides or canonicalize paths under validated DESIGN_TMPDIR before tally.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: risk-integration: skills/design/SKILL.md:1189
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Full assessor verdict file is printed without the untrusted-data guard used for QUALIFICATIONS_SUMMARY. External assessor REASONING in WORSE verdict could prompt-inject the orchestrating agent at Continue/Stop. Label verdict text untrusted; prefer bounded WORSE line plus QUALIFICATIONS_SUMMARY only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: security: scripts/design-log-publish.sh:239-244
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] New top-level assessor artifacts are published to larch-logs with full inlined plans and assessor prose. Secrets in plans may reach committed design logs if redact-secrets misses a pattern. Exclude assessor-prompt from publish or add redaction regression tests for new basenames.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: risk-integration: skills/design/scripts/assess-plan-round.sh:215-226
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Fail-open degradation proceeds on panel-wide failure with only a chat warning. Operator may believe round-over-round quality was checked when EFFECTIVE_ASSESSORS=0. Keep fail-open but make 0/3 banner hard to miss or document as explicit integrity tradeoff.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: architecture: skills/design/SKILL.md:1103-1104,1119-1121
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Step 3 short-circuits skip Gate B and Step 3.6 so plan-after-round snapshots and cursor advancement never occur for that pass. degraded-empty-collector or panel-failed on round 1 delays assessor until a later full Gate B settle; operators may think quality gate ran. Document in assessor.md or add best-effort write-after on HARD short-circuit paths when plan.txt exists.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: correctness: skills/design/SKILL.md:1189 + skills/design/references/approval-gates.md:115
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Gate B switch-to-discussion bypasses Step 3.6 and write-after. Post-review discussion re-entry keeps cursor at 1 and skips assessor for that cycle. Document contract or snapshot before switch on HARD settled plans.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: correctness: skills/design/scripts/tally-plan-assessor.sh:126-129
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Single parseable WORSE assessor yields worse-majority and operator Continue/Stop. Only one of three models returns parseable WORSE; operator sees full gate UX from 1/3 panel. Require successful>=2 for worse-majority or show explicit 1/3 banner before AskUserQuestion.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_28

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_28: architecture: skills/design/scripts/snapshot-plan-round.sh:86-88
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] write-after write-once preserves first snapshot if same round re-enters Step 3.6. Resume or abnormal re-entry compares stale plan-after-round-N to updated plan.txt. Allow refresh when plan.txt is newer and no verdict exists yet.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_33

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_33: correctness: skills/design/SKILL.md:1189-1210
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] QUALIFICATIONS_SUMMARY is prose-only; Step 3.6 Bash does not read the .env sidecar. WORSE-majority AskUserQuestion may omit assessor qualifications if the orchestrator skips prose instructions. Parse QUALIFICATIONS_SUMMARY from ASSESSOR_VERDICT_ENV in the Step 3.6 fence before AskUserQuestion.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: skills/design/SKILL.md:1055-1160
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate ROUND_CURSOR parse loops in Step 3 and Step 3.6. Future KV contract change might be updated in one fence only. Document single read-cursor contract or deduplicate parsing guidance.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: skills/shared/scripts/render-assessor-prompt.sh:1-75
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] render-assessor-prompt.sh omits lib-quiet conventions used by sibling scripts. Quiet mode / stderr routing may differ from voter and design scripts under automation. Adopt lib-quiet.sh and larch_err like render-voter-prompt.sh.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: code-quality: skills/design/scripts/test-snapshot-plan-round.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Harness omits FINDING_12 interrupt or partial temp-file atomicity check. Temp+rename regression might not be caught until production disk edge cases. Add simulated failed rename test or document deferral in test md.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

