### FINDING_4: [OUT_OF_SCOPE] **[code-quality]** [`skills/review/scripts/test-collect-findings.md`](skills/review/scripts/test-collect-findings.md) (updated in the branch) calls out the preamble/`##` skip regression but does not mention the `canonical-3-finding-guard` block added in [`test-collect-findings.sh:218-231`](skills/review/scripts/test-collect-findings.sh). Small contract-doc gap relative to the full harness; not a runtime correctness defect.
- **Reviewer**: dyn-test-count-semantics-output.txt
- **Concern**: - **[code-quality]** [`skills/review/scripts/test-collect-findings.md`](skills/review/scripts/test-collect-findings.md) (updated in the branch) calls out the preamble/`##` skip regression but does not mention the `canonical-3-finding-guard` block added in [`test-collect-findings.sh:218-231`](skills/review/scripts/test-collect-findings.sh). Small contract-doc gap relative to the full harness; not a runtime correctness defect.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=rejected

### FINDING_5: [OUT_OF_SCOPE] **[correctness]** Preamble fixture uses `--mode diff` only ([`test-collect-findings.sh:211-239`](skills/review/scripts/test-collect-findings.sh)) — [`skills/review/scripts/collect-findings.sh:268-295`](skills/review/scripts/collect-findings.sh) passes `-v mode="$MODE"` into `parse_output`’s awk but the program never references `mode`, so prose parsing (including `skip`) is the same in description and diff modes. A duplicate `--mode description` case would add redundancy, not fix a mode-specific bug.
- **Reviewer**: dyn-test-count-semantics-output.txt
- **Concern**: - **[correctness]** Preamble fixture uses `--mode diff` only ([`test-collect-findings.sh:211-239`](skills/review/scripts/test-collect-findings.sh)) — [`skills/review/scripts/collect-findings.sh:268-295`](skills/review/scripts/collect-findings.sh) passes `-v mode="$MODE"` into `parse_output`’s awk but the program never references `mode`, so prose parsing (including `skip`) is the same in description and diff modes. A duplicate `--mode description` case would add redundancy, not fix a mode-specific bug.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_6: [OUT_OF_SCOPE] **[correctness]** Scout note on `FINDINGS_COUNT=4` in [`skills/review/scripts/test-collect-findings.sh:224-227`](skills/review/scripts/test-collect-findings.sh) — This matches implementation semantics, not a false green. In [`skills/review/scripts/collect-findings.sh:390-404`](skills/review/scripts/collect-findings.sh), `count` is incremented for **every** row emitted into the main findings file (including `[OUT_OF_SCOPE]`-prefixed titles), and `OOS_COUNT` increments only when `title` matches `\[OUT_OF_SCOPE\]*`. The same contract is already asserted in the opening fixture ([`test-collect-findings.sh:19-33`](skills/review/scripts/test-collect-findings.sh): `FINDINGS_COUNT=2` with `OOS_COUNT=1` for one in-scope and one OOS bullet). No change required for count semantics.
- **Reviewer**: dyn-test-count-semantics-output.txt
- **Concern**: - **[correctness]** Scout note on `FINDINGS_COUNT=4` in [`skills/review/scripts/test-collect-findings.sh:224-227`](skills/review/scripts/test-collect-findings.sh) — This matches implementation semantics, not a false green. In [`skills/review/scripts/collect-findings.sh:390-404`](skills/review/scripts/collect-findings.sh), `count` is incremented for **every** row emitted into the main findings file (including `[OUT_OF_SCOPE]`-prefixed titles), and `OOS_COUNT` increments only when `title` matches `\[OUT_OF_SCOPE\]*`. The same contract is already asserted in the opening fixture ([`test-collect-findings.sh:19-33`](skills/review/scripts/test-collect-findings.sh): `FINDINGS_COUNT=2` with `OOS_COUNT=1` for one in-scope and one OOS bullet). No change required for count semantics.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_7: [OUT_OF_SCOPE] **[correctness]** [`skills/review/scripts/test-collect-findings.sh:231`](skills/review/scripts/test-collect-findings.sh) — `grep -Fq '[OUT_OF_SCOPE]'` uses fixed-string mode; `[` and `]` are literal. Same pattern as line 90 for the inline-TSV case. No issue.
- **Reviewer**: dyn-test-count-semantics-output.txt
- **Concern**: - **[correctness]** [`skills/review/scripts/test-collect-findings.sh:231`](skills/review/scripts/test-collect-findings.sh) — `grep -Fq '[OUT_OF_SCOPE]'` uses fixed-string mode; `[` and `]` are literal. Same pattern as line 90 for the inline-TSV case. No issue.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_8: [OUT_OF_SCOPE] code-quality: skills/review/scripts/collect-findings.sh:268-269
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] parse_output awk receives -v mode="$MODE" but never uses mode. Dead variable; no runtime effect unless someone expects MODE to change awk rules. Remove -v mode or implement mode-specific rules and test both.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=rejected

### FINDING_9: [OUT_OF_SCOPE] correctness: skills/review/scripts/collect-findings.sh (existing bullet rules)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Single-hash # preambles are not covered by the new /^##/ skip. Commit bullets under # Title could still be promoted as before. Optional follow-up: extend skip or document single-hash preambles as out of contract.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=rejected

