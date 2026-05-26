### [rejected] FINDING_16

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_16: code-quality: skills/implement/scripts/test-step2-dispatch.md:39-42
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Doc lists four M tests while plan promises M1-M20. Reviewers assume CI covers M9b submodule dirty-file case. Sync doc with implemented tests or add missing harness cases.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: risk-integration: scripts/test-extract-plan-scope-paths.sh:17-70
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Single synthetic fixture; no golden diff vs prior scout write_scope_files corpus. Helper/scout divergence on edge plan headings may break plan-scope alignment in production recovery. Extend harness with scout fixture corpus golden diffs.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: risk-integration: skills/implement/scripts/test-step2-dispatch.sh:1335-1338
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] M17 Step 7a publication of recovery-metadata.json not asserted (only sidecar file existence). Step 7a could publish wrong artifact; M1 would still pass. Add stub Step 7a assertion on published log artifact.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: skills/implement/scripts/step2-implement.sh:375-490
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Triple copy of NUL porcelain parsing Python in one shell file Porcelain rule changes require three edits and can desync digest vs delta vs submodule scan Factor one shared parser module or helper script
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_4: code-quality: skills/implement/scripts/test-step2-dispatch.md:39-42
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Contract documents 4 M-tests while plan promised M1-M20 docs Reviewers assume full gate matrix is tested when harness only covers four cases Document implemented M-tests only or add remaining bullets when tests land
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_5: correctness: skills/implement/scripts/step2-implement.sh:797-798
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] schema_version gate uses jq -r string compare not tostring coercion Numeric schema_version 1 may diverge from prompt-side jq self-validation Align dispatcher gate with (.schema_version | tostring) == "1"
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: code-quality: skills/implement/scripts/step2-implement.sh:536-546
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Recovery runs per-path submodule check then full-repo submodule scan Minor redundant work on recovery path Document intent or narrow scan to recovery paths only
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

