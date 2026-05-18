### [rejected] FINDING_12

### FINDING_12: code-quality: scripts/collect-agent-results.sh:902-978
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated META parsing loops Extra complexity and drift risk when keys change Extract a single meta reader helper
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_14

### FINDING_14: code-quality: scripts/test-collect-agent-results.sh:237-39
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] C_IT1 fixture contains unrelated LLM conversational lines. Confuses maintainers about what the test proves. Use minimal neutral prose around the fenced TSV.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_26

### FINDING_26: correctness: scripts/collect-agent-results.md scripts/collect-agent-results.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Retry documented as section 3.7 vs plan section 3.6 Numbering mismatch only; structured pass is 3.6. Rename sections in docs/comments to match plan or add explicit cross-reference.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_35

### FINDING_35: correctness: skills/review/scripts/tally-code-votes.sh:2567
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Dead-slot awk skips dyn- manifest basenames Dynamic manifest slots with no score_rows never appear as dead rows. Include dyn rows or document intentional exclusion vs feature text.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_36

### FINDING_36: correctness: skills/review/scripts/tally-code-votes.sh:427-434
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Fragile NDJSON output extraction via awk gsub Manifest formatting changes could mis-parse output paths and mis-label dead vs live slots Parse manifest with jq or a dedicated NDJSON reader consistent with other tooling
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_41

### FINDING_41: risk-integration: scripts/collect-agent-results.sh:1009-1011
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] NS-retry wait uses || true masking wait fatals Silent loss of wait errors can strand NOT_SUBSTANTIVE despite retriable work Align with documented initial-wait stderr contract or document the divergence
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_44

### FINDING_44: risk-integration: scripts/github-remote-repo.sh:1988-1995
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Unrelated regex tweak bundled with #2323 Noise for reviewers bisecting functional changes Revert or split to a separate PR
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_49

### FINDING_49: risk-integration: skills/review/scripts/tally-code-votes.sh:351-377,382-437
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Dead-slot scoreboard rows use non-numeric final column Automated parsers assume column 11 is numeric Score and mis-handle appended STATUS rows Use a separate STATUS column or keep Score numeric and move status into an extra column
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=1

### [rejected] FINDING_51

### FINDING_51: security: scripts/collect-agent-results.sh:936-1001
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] NOT_SUBSTANTIVE retry exec trusts .meta OUTER_LAUNCHER paths without section-3 canonical checks. A non-canonical or hostile .meta can cause exec of an arbitrary executable under the collector UID while empty-output retry would reject the same metadata. Reuse section 3 outer-launcher validation (.. guards canonical launch-review.sh path expected .prompt sidecar non-symlink rules) before spawning 3.7.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=1

