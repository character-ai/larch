### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: risk-integration: scripts/test-render-cost-line-callsites.sh:41-48
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Planned stable grep substring for orchestrator cost-line emit was not used; SKILL uses alternate wording. Prose can drift away from collapse-resistant emit instructions without failing callsite lint. Align SKILL.md to planned substring or add redundant minimal grep anchors shared by implement and design.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: security: skills/implement/SKILL.md:1760, skills/design/SKILL.md:288
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Orchestrator verbatim cost-line emit trusts any line starting with - **Cost**: from session summary files. An attacker or race that rewrites summary-final.md before orchestrator read can inject instruction text into plain chat outside collapsed Bash output. Emit or validate a dedicated cost-line file from scripts with a strict format check before orchestrator re-emission.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: correctness: scripts/test-render-cost-line-callsites.sh:837-845
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Callsite lint does not include the plan-required grep for emit one line of plain chat text containing the cost line verbatim from. Future SKILL edits could drop the orchestrator-text emit while alternate grep anchors still pass, weakening ROOT CAUSE G protection exactly where the plan pinned it. Add grep -Fq for the plan substring in both skills/implement/SKILL.md and skills/design/SKILL.md per acceptance criterion 5.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: skills/implement/scripts/write-final-report.sh:367-437, skills/design/scripts/render-final-summary.sh:313-365
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Duplicated compose_self_fallback mirrors render-run-summary schema in two scripts. Future renderer bullet-order or field changes can update one fallback and miss the other despite tests. Defer per plan; add follow-up to extract shared fallback composer once schema stabilizes.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: scripts/test-render-cost-line-callsites.sh:830-845
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Grep pins full SKILL.md/bash lines for contracts. Whitespace or refactors fail lint without behavioral regression. Use shorter stable substrings unless full-line pins are intentional.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

