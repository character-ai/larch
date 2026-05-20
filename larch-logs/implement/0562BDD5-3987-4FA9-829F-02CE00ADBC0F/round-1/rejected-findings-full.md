### [rejected] FINDING_11

### FINDING_11: correctness: skills/review/scripts/collect-findings.sh:393-394
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] OOS category uses longest-suffix %% strip against **+tail, not first closing bold span. Reviewer OOS bullet text contains multiple ** pairs before the bracketed file link (e.g. extra inline bold); category collapses to a wrong short prefix while still looking like a valid token (bash check: oos_body=risk** note **alpha** tail yields category risk). Strip category using the first closing ** after the opening bold, or reuse the same rule as extract_category() in compose-review-findings.sh.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_12

### FINDING_12: risk-integration: skills/review/scripts/collect-findings.md:313
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Doc implies normalized titles always include : path. Code path without a [\`...\`] match writes [OUT_OF_SCOPE] $category only (collect-findings.sh:401-402). Document optional : path when the backtick link is absent.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

### FINDING_5: architecture: scripts/compose-review-findings.sh:61-72 vs skills/review/scripts/collect-findings.sh:392-403
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Bold-markdown category parsing differs between compose (awk first index **) and collect (bash longest %% ** strip). Same bullet shape with extra ** can produce different category strings at different pipeline stages, weakening the cross-script contract for JSONL and markdown artifacts. Align algorithms (shared helper or matching first-** semantics in both places).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

### FINDING_8: code-quality: skills/review/scripts/collect-findings.md:313
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Normalization wording mentions 'file:lines' while the bash path copies only the backtick path into the short title. Docs imply line ranges are always present; they are not extracted by the new regex block. Align the sentence with backtick-only fileref behavior or add line-range extraction if product requires it.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_9

### FINDING_9: correctness: scripts/compose-review-findings.sh:65-69
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Bold-branch category uses first substring match of ** after stripping leading **, not guaranteed closing bold token. Malformed heading with an extra ** inside the intended category text yields a truncated category in JSONL category field. Prefer a delimiter-aware parse or explicitly document unsupported inner ** sequences.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

