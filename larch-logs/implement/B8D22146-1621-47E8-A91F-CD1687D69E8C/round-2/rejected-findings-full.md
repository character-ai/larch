### [rejected] FINDING_13

### FINDING_13: code-quality: scripts/dispatch-code-voters.sh (retry path vs plan text)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plan named fixed diag basename and specific relaunchers; implementation uses output-adjacent diag paths and launch-review.sh for externals. None if dispatch and tally agree; confusion only for plan-as-spec readers. Reconcile plan or add a short comment in dispatch tying behavior to #2336 parity intent.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_16

### FINDING_16: code-quality: scripts/dispatch-code-voters.sh:99-105 skills/review/scripts/tally-code-votes.sh:198-204
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate voter_parse_rate_diag_path helper in dispatch and tally. Future edits to diag naming risk updating one site and not the other. Source a single shared helper or small sourced library function.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_23

### FINDING_23: correctness: skills/review/scripts/tally-code-votes.sh (live scoreboard awk per diff)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Second sub(/\.txt$/, "", label) after stripping -output.txt can over-normalize unusual live basenames. Rare label mismatch between live and dead scoreboard rows. Restrict normalization to the planned -output.txt strip only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_25

### FINDING_25: risk-integration: scripts/dispatch-code-voters.sh:178-200
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Codex/Cursor parse retries use launch-review.sh instead of dispatch-with-waterfall.sh. If waterfall and launch-review diverge in the future, retries may not mirror first-pass behavior. Comment invariant or share one launcher path for waterfall and retry.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_36

### FINDING_36: security: skills/review/scripts/tally-code-votes.sh:219-224
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Parse-rate failure is inferred solely from existence of a sibling *-parse-rate-diag.txt next to each voter file path. A writer with the same filesystem access as vote outputs can force EFFECTIVE_VOTERS down without plausible structured votes, biasing outcomes toward neutral tiers. Document trust boundary for REVIEW_TMPDIR or bind diag detection to verified dispatch output (manifest/KV) before counting a slot as parse-failed.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

