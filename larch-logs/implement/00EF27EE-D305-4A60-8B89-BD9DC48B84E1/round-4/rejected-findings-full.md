### [rejected] FINDING_10

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_10: correctness: skills/design/scripts/parse-plan-commands.awk:381-384
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] eval detection is case-sensitive on the command segment. Unusual uppercase EVAL token might bypass the parse_note skip intended for eval. Use a case-insensitive match or document lowercase-only detection.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: security: skills/design/scripts/validate-plan-commands.sh:115-118
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Tier2 --help probes inherit full parent environment Expanded per-plan help probes increase opportunity for a hostile repo script to observe inherited session env during --help Run Tier2 probes under env -i with the same minimal allowlist as Tier3 where compatible
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_20: correctness: skills/design/references/approval-gates.md:86-87 skills/design/references/discussion-rounds.md:121
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] References gate post-Apply validation on review_budget=full while invoke-plan-validator gates on not quick. Today equivalent for quick|full only; a future third budget value could desync docs and behavior. Align prose with invoke-plan-validator-if-not-quick.sh or cite read-design-review-budget.sh as normative.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: correctness: skills/design/scripts/parse-plan-commands.awk:373-376
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Any $( outside arithmetic skips the entire command segment as subshell parse_note. Plans using command substitution only inside quoted values skip Tier 2/Tier 3 entirely for that segment. Tighten substitution detection after tokenization or document conservative skip and require static paths for validated commands.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: risk-integration: skills/design/SKILL.md:516-526
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] VALIDATE_* stdout parsing assumes one KEY=value pair per line without embedded structure in values. Future composite machine lines could mis-parse if case arms broaden. Keep emit_kv one-field-per-value invariant; add regression grep if composite lines are introduced.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: skills/design/SKILL.md:5402-5420;5477-5496
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated KV-parse while loops for validate driver stdout. Future edits may update Step 2b but not Step 5c (or vice versa), causing subtle behavior drift. Extract a shared helper or single sourced snippet for parsing VALIDATE_* lines.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

