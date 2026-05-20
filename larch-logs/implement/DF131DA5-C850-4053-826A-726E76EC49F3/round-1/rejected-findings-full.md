### [rejected] FINDING_11

### FINDING_11: code-quality: skills/review/scripts/test-collect-findings.sh:177-194
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] bullet-not-a-finding uses --mode diff while plan described description/dual-list context Harness still validates parser behavior but diverges from plan wording for traceability Match plan mode or note in test comment why diff mode is the intended matrix row
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

### FINDING_18: risk-integration: skills/review/scripts/test-collect-findings.md:5
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Contract doc lists only the preamble regression; plan asked to note both new harness cases. Readers or future /implement steps may think only one test was added; canonical dual-list guard is undocumented. Extend test-collect-findings.md to mention the canonical-3-finding-guard case and its assertions.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

### FINDING_19: risk-integration: skills/review/scripts/test-collect-findings.sh:194
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Preamble regression test uses --mode diff while the reported bug path is description-style dynamic output. If parse_output later starts branching on mode, this test could pass while description regresses. Run the preamble fixture with --mode description (or add a second duplicate assertion under description) while mode remains unused.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

### FINDING_20: risk-integration: skills/review/scripts/test-collect-findings.sh:239
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Preamble regression test uses --mode diff though the bug narrative is description/dyn-reviewer oriented. Low risk today because awk ignores mode; future MODE-gated logic could leave this case untested. Use --mode description in the fixture if it matches production, or add a one-line comment explaining deliberate diff-mode choice.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

