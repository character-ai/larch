### FINDING_1: **Important** `correctness` `skills/review/scripts/collect-findings.sh:392` — The new OOS normalizer matches any OOS title that starts with bold markdown, including the severity-first prose format required by the reviewer templates (`**Important**`, `**Nit**`, `**Latent**`). Concrete failing scenario: an OOS bullet like `- **Latent** \`code-quality\` \`scripts/old.sh:5\` Pre-existing issue` is parsed as `[OUT_OF_SCOPE] **Latent** ...`, then rewritten to just `[OUT_OF_SCOPE] Latent`, dropping the focus area, file reference, and issue title in both `findings.md` and `oos.md`. Restrict normalization to bold tokens that are valid focus areas (`code-quality|risk-integration|correctness|architecture|security`) and add a regression test for a severity-first OOS bullet.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `skills/review/scripts/collect-findings.sh:392` — The new OOS normalizer matches any OOS title that starts with bold markdown, including the severity-first prose format required by the reviewer templates (`**Important**`, `**Nit**`, `**Latent**`). Concrete failing scenario: an OOS bullet like `- **Latent** \`code-quality\` \`scripts/old.sh:5\` Pre-existing issue` is parsed as `[OUT_OF_SCOPE] **Latent** ...`, then rewritten to just `[OUT_OF_SCOPE] Latent`, dropping the focus area, file reference, and issue title in both `findings.md` and `oos.md`. Restrict normalization to bold tokens that are valid focus areas (`code-quality|risk-integration|correctness|architecture|security`) and add a regression test for a severity-first OOS bullet.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] architecture: skills/review/scripts/collect-findings.sh:268-277
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Double [OUT_OF_SCOPE] prefix can prevent bold-markdown normalization when reviewers self-prefix bullets Reviewer writes [OUT_OF_SCOPE] **cat** in OOS section; awk adds another prefix; normalization guard does not match Pre-existing prefix behavior; not introduced by this diff
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] architecture: skills/review/scripts/collect-findings.sh:268-296
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] parse_output awk receives -v mode="$MODE" but never references mode. Dead binding; slight maintenance noise when reading the collector. Remove unused -v mode=... or start using it (separate change).
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: skills/review/scripts/collect-findings.sh:268
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] parse_output awk receives mode but never uses it. Dead parameter; no runtime effect from this branch. Optional cleanup in a separate change if desired.
- **Suggested revision**: Address the concern above.

### FINDING_5: architecture: scripts/compose-review-findings.sh:61-72 vs skills/review/scripts/collect-findings.sh:392-403
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Bold-markdown category parsing differs between compose (awk first index **) and collect (bash longest %% ** strip). Same bullet shape with extra ** can produce different category strings at different pipeline stages, weakening the cross-script contract for JSONL and markdown artifacts. Align algorithms (shared helper or matching first-** semantics in both places).
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/compose-review-findings.md:149-150
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Docs omit that OOS FINDING headers drop the '[OUT_OF_SCOPE]' token from the text prepended as the synthetic '## ' line. Readers may think the bold branch must handle '## [OUT_OF_SCOPE] **…' on the first line; actual composed bodies use '## **…' for those entries. Add a short note that the OOS FINDING regex captures the suffix after '[OUT_OF_SCOPE]' before building the '## ' line.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: skills/review/scripts/collect-findings.md:15
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Doc claims normalization always yields [OUT_OF_SCOPE] category: path. Code emits [OUT_OF_SCOPE] category when fileref regex misses; readers expect a path segment always. Document both normalized forms (with path when link present, category-only fallback otherwise).
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: skills/review/scripts/collect-findings.md:313
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Normalization wording mentions 'file:lines' while the bash path copies only the backtick path into the short title. Docs imply line ranges are always present; they are not extracted by the new regex block. Align the sentence with backtick-only fileref behavior or add line-range extraction if product requires it.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/compose-review-findings.sh:65-69
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Bold-branch category uses first substring match of ** after stripping leading **, not guaranteed closing bold token. Malformed heading with an extra ** inside the intended category text yields a truncated category in JSONL category field. Prefer a delimiter-aware parse or explicitly document unsupported inner ** sequences.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: skills/review/scripts/collect-findings.sh:392-404
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] OOS bold-title normalization uses an exact '[OUT_OF_SCOPE] **' prefix match. A reviewer bullet with an extra space so the collected title is '[OUT_OF_SCOPE] **cat** …' (double space) skips normalization; sprawling title and downstream formatting persist despite being bold-markdown OOS. Normalize flexible whitespace between the OUT_OF_SCOPE token and '**', or trim runs of spaces before the predicate.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: skills/review/scripts/collect-findings.sh:393-394
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] OOS category uses longest-suffix %% strip against **+tail, not first closing bold span. Reviewer OOS bullet text contains multiple ** pairs before the bracketed file link (e.g. extra inline bold); category collapses to a wrong short prefix while still looking like a valid token (bash check: oos_body=risk** note **alpha** tail yields category risk). Strip category using the first closing ** after the opening bold, or reuse the same rule as extract_category() in compose-review-findings.sh.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: skills/review/scripts/collect-findings.md:313
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Doc implies normalized titles always include : path. Code path without a [\`...\`] match writes [OUT_OF_SCOPE] $category only (collect-findings.sh:401-402). Document optional : path when the backtick link is absent.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: skills/review/scripts/test-collect-findings.sh:407-427;skills/review/scripts/collect-findings.sh:392-403
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Plan-documented OOS edge case (bold markdown without bracketed backtick link) has no regression test Refactor could drop or corrupt the fileref-empty branch; CI would not fail because the new test always includes [`path`] Add a second OOS bullet with **category** and no [`...`] link; assert compact [OUT_OF_SCOPE] title and OOS_COUNT
- **Suggested revision**: Address the concern above.

