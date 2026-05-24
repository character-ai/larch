### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: risk-integration: skills/design/scripts/design-driver.sh:143-146
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] ARGS for driver actions are parsed with read -a from a single line; spaced paths would split incorrectly If TMPDIR or plugin paths ever contain spaces the validate action could target the wrong file or fail open Keep space-free path invariant explicit in callers or use safer argv framing
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: architecture: skills/design/scripts/parse-plan-commands.awk:372-455 and skills/design/scripts/validate-plan-commands.sh:327-353
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Tier 3 argv omits positional plan arguments; only long flags are replayed. Dry-run registry script needs positional args to exercise path-containment checks; Tier 3 may pass while real plan command would fail. Document limitation in validate-plan-commands.md and/or extend TSV with argv tail behind existing metacharacter rules.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: architecture: skills/design/scripts/design-driver.sh:125-170
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] no_sentinel prevents skip-on-replay but success still writes a completion sentinel; naming suggests otherwise. Future contributor changes resume logic assuming no sentinel file exists for VALIDATE_PLAN_COMMANDS. Clarify inline that sentinel is written for bookkeeping only and must not gate skipping.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_22: risk-integration: skills/design/references/approval-gates.md:86-87; skills/design/references/discussion-rounds.md:121
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Gate B / discussion docs show raw ACTION=VALIDATE_PLAN_COMMANDS pipe instead of invoke-plan-validator-if-not-quick.sh An executor copy-pastes the ACTION line without the review_budget guard and runs validation on trivial (review_budget=quick), violating the tier skip contract Point Gate B and discussion-round2 prose at invoke-plan-validator-if-not-quick.sh "$DESIGN_TMPDIR/plan.txt" like SKILL Step 2b
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_23: architecture: skills/design/scripts/parse-plan-commands.md:16-20; skills/design/scripts/validate-plan-commands.sh:218-247
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Parser TSV adds cmd_uid beyond the six-column plan schema Fixtures and consumer awk target seven fields; external readers of the old plan could mis-implement column offsets Amend archived plan text to seven columns or remove cmd_uid if strict six-column wire is required
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: skills/design/scripts/invoke-plan-validator-if-not-quick.sh:21-22|skills/design/scripts/design-driver.sh:144-146
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Extra wrapper indirection and word-split ARGS parsing for VALIDATE_PLAN_COMMANDS. Low risk today because tmp paths are space-free; slightly harder to trace than a single callsite. Document the space-free ARGS contract or quote ARGS; keep wrapper if DRY outweighs indirection.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: skills/design/scripts/parse-plan-commands.sh:73-74|skills/design/scripts/parse-plan-commands.awk:5-6
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] TSV gains cmd_uid and logic spans awk+sh beyond the original “one helper script” sketch. Slightly higher maintenance burden when evolving the schema. Document cmd_uid as normative internal column or absorb into fewer artifacts if complexity grows.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

