### FINDING_1: **Important** `correctness` `skills/review/scripts/collect-findings.sh:392` — The new OOS normalizer matches any OOS title that starts with bold markdown, including the severity-first prose format required by the reviewer templates (`**Important**`, `**Nit**`, `**Latent**`). Concrete failing scenario: an OOS bullet like `- **Latent** \`code-quality\` \`scripts/old.sh:5\` Pre-existing issue` is parsed as `[OUT_OF_SCOPE] **Latent** ...`, then rewritten to just `[OUT_OF_SCOPE] Latent`, dropping the focus area, file reference, and issue title in both `findings.md` and `oos.md`. Restrict normalization to bold tokens that are valid focus areas (`code-quality|risk-integration|correctness|architecture|security`) and add a regression test for a severity-first OOS bullet.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `skills/review/scripts/collect-findings.sh:392` — The new OOS normalizer matches any OOS title that starts with bold markdown, including the severity-first prose format required by the reviewer templates (`**Important**`, `**Nit**`, `**Latent**`). Concrete failing scenario: an OOS bullet like `- **Latent** \`code-quality\` \`scripts/old.sh:5\` Pre-existing issue` is parsed as `[OUT_OF_SCOPE] **Latent** ...`, then rewritten to just `[OUT_OF_SCOPE] Latent`, dropping the focus area, file reference, and issue title in both `findings.md` and `oos.md`. Restrict normalization to bold tokens that are valid focus areas (`code-quality|risk-integration|correctness|architecture|security`) and add a regression test for a severity-first OOS bullet.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_2: [OUT_OF_SCOPE] architecture: skills/review/scripts/collect-findings.sh:268-277
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Double [OUT_OF_SCOPE] prefix can prevent bold-markdown normalization when reviewers self-prefix bullets Reviewer writes [OUT_OF_SCOPE] **cat** in OOS section; awk adds another prefix; normalization guard does not match Pre-existing prefix behavior; not introduced by this diff
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=rejected

### FINDING_3: [OUT_OF_SCOPE] architecture: skills/review/scripts/collect-findings.sh:268-296
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] parse_output awk receives -v mode="$MODE" but never references mode. Dead binding; slight maintenance noise when reading the collector. Remove unused -v mode=... or start using it (separate change).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=rejected

### FINDING_4: [OUT_OF_SCOPE] code-quality: skills/review/scripts/collect-findings.sh:268
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] parse_output awk receives mode but never uses it. Dead parameter; no runtime effect from this branch. Optional cleanup in a separate change if desired.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

