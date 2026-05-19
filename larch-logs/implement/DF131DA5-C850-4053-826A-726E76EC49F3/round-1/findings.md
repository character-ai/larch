### FINDING_1: **Important** — correctness — `skills/review/scripts/collect-findings.sh:281-285`: The new catch-all `^##` skip state drops legitimate fail-open findings under common noncanonical headings like `## Findings`, contradicting the existing diff-mode contract that output without canonical headers is treated as in-scope. Concrete failing scenario: reviewer output `## Findings` followed by `- Real parser issue...` in diff mode now produces zero parser rows and can be recorded as non-substantive, so a real finding is silently lost. Narrow the skip rule to the known preamble headings, such as `## Commits since merge-base`, or skip only commit-hash bullets in that preamble; add a regression test for `## Findings` plus a bullet still producing `FINDINGS_COUNT=1`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** — correctness — `skills/review/scripts/collect-findings.sh:281-285`: The new catch-all `^##` skip state drops legitimate fail-open findings under common noncanonical headings like `## Findings`, contradicting the existing diff-mode contract that output without canonical headers is treated as in-scope. Concrete failing scenario: reviewer output `## Findings` followed by `- Real parser issue...` in diff mode now produces zero parser rows and can be recorded as non-substantive, so a real finding is silently lost. Narrow the skip rule to the known preamble headings, such as `## Commits since merge-base`, or skip only commit-hash bullets in that preamble; add a regression test for `## Findings` plus a bullet still producing `FINDINGS_COUNT=1`. I ran the requested `git log` command and checked the parser behavior with the changed awk rules.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Latent**, `risk-integration`, [`skills/review/scripts/collect-findings.sh`](skills/review/scripts/collect-findings.sh):281-284 — Any line matching `^##` starts a skip region until a canonical `### In-Scope Findings` or `### Out-of-Scope Observations` line. Reviewers who use non-canonical Markdown (for example `## In-Scope Findings` or other `##` section titles instead of the exact `###` headers) will have bullets and bodies under that region ignored, so real findings can be **silently dropped** while the raw file still reads as substantive. **Scenario:** A specialist template omits one `#` on the section header; Step 3a shows fewer findings than the reviewer intended with no hard failure. **Suggested fix:** Document the strict header grammar in the reviewer contract, add a narrow exception only if you must support `##` variants, or emit a warning when `skip` stayed 1 for the whole file but bullets existed after the first `##`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **Latent**, `risk-integration`, [`skills/review/scripts/collect-findings.sh`](skills/review/scripts/collect-findings.sh):281-284 — Any line matching `^##` starts a skip region until a canonical `### In-Scope Findings` or `### Out-of-Scope Observations` line. Reviewers who use non-canonical Markdown (for example `## In-Scope Findings` or other `##` section titles instead of the exact `###` headers) will have bullets and bodies under that region ignored, so real findings can be **silently dropped** while the raw file still reads as substantive. **Scenario:** A specialist template omits one `#` on the section header; Step 3a shows fewer findings than the reviewer intended with no hard failure. **Suggested fix:** Document the strict header grammar in the reviewer contract, add a narrow exception only if you must support `##` variants, or emit a warning when `skip` stayed 1 for the whole file but bullets existed after the first `##`. ---
- **Suggested revision**: Address the concern above.

### FINDING_3: **[correctness]** [`skills/review/scripts/collect-findings.sh:281-284`](skills/review/scripts/collect-findings.sh) — The new `/^##/` rule matches any line whose first two characters are `##`. In awk, that includes every `### ...` line that does **not** match the two earlier exact headers (`### Out-of-Scope Observations`, `### In-Scope Findings`). A non-canonical third-level heading (e.g. `### Notes` between sections) therefore runs `flush(); skip=1; next` and subsequent list bullets are dropped until another canonical header clears `skip`, whereas before they would have been folded into the prose `NF` path. That is a real narrowing of accepted reviewer grammar introduced by this branch. **Suggested fix:** Restrict the skipper to level-2 headings only (for example require the third character not to be `#`, or match `^## ` / `^##[^#]` with an explicit `^##$` edge case), or add explicit allow patterns for benign `###` subheads if you want to keep `^##` as written.
- **Reviewer**: dyn-test-count-semantics-output.txt
- **Concern**: - **[correctness]** [`skills/review/scripts/collect-findings.sh:281-284`](skills/review/scripts/collect-findings.sh) — The new `/^##/` rule matches any line whose first two characters are `##`. In awk, that includes every `### ...` line that does **not** match the two earlier exact headers (`### Out-of-Scope Observations`, `### In-Scope Findings`). A non-canonical third-level heading (e.g. `### Notes` between sections) therefore runs `flush(); skip=1; next` and subsequent list bullets are dropped until another canonical header clears `skip`, whereas before they would have been folded into the prose `NF` path. That is a real narrowing of accepted reviewer grammar introduced by this branch. **Suggested fix:** Restrict the skipper to level-2 headings only (for example require the third character not to be `#`, or match `^## ` / `^##[^#]` with an explicit `^##$` edge case), or add explicit allow patterns for benign `###` subheads if you want to keep `^##` as written.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] **[code-quality]** [`skills/review/scripts/test-collect-findings.md`](skills/review/scripts/test-collect-findings.md) (updated in the branch) calls out the preamble/`##` skip regression but does not mention the `canonical-3-finding-guard` block added in [`test-collect-findings.sh:218-231`](skills/review/scripts/test-collect-findings.sh). Small contract-doc gap relative to the full harness; not a runtime correctness defect.
- **Reviewer**: dyn-test-count-semantics-output.txt
- **Concern**: - **[code-quality]** [`skills/review/scripts/test-collect-findings.md`](skills/review/scripts/test-collect-findings.md) (updated in the branch) calls out the preamble/`##` skip regression but does not mention the `canonical-3-finding-guard` block added in [`test-collect-findings.sh:218-231`](skills/review/scripts/test-collect-findings.sh). Small contract-doc gap relative to the full harness; not a runtime correctness defect.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] **[correctness]** Preamble fixture uses `--mode diff` only ([`test-collect-findings.sh:211-239`](skills/review/scripts/test-collect-findings.sh)) — [`skills/review/scripts/collect-findings.sh:268-295`](skills/review/scripts/collect-findings.sh) passes `-v mode="$MODE"` into `parse_output`’s awk but the program never references `mode`, so prose parsing (including `skip`) is the same in description and diff modes. A duplicate `--mode description` case would add redundancy, not fix a mode-specific bug.
- **Reviewer**: dyn-test-count-semantics-output.txt
- **Concern**: - **[correctness]** Preamble fixture uses `--mode diff` only ([`test-collect-findings.sh:211-239`](skills/review/scripts/test-collect-findings.sh)) — [`skills/review/scripts/collect-findings.sh:268-295`](skills/review/scripts/collect-findings.sh) passes `-v mode="$MODE"` into `parse_output`’s awk but the program never references `mode`, so prose parsing (including `skip`) is the same in description and diff modes. A duplicate `--mode description` case would add redundancy, not fix a mode-specific bug.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] **[correctness]** Scout note on `FINDINGS_COUNT=4` in [`skills/review/scripts/test-collect-findings.sh:224-227`](skills/review/scripts/test-collect-findings.sh) — This matches implementation semantics, not a false green. In [`skills/review/scripts/collect-findings.sh:390-404`](skills/review/scripts/collect-findings.sh), `count` is incremented for **every** row emitted into the main findings file (including `[OUT_OF_SCOPE]`-prefixed titles), and `OOS_COUNT` increments only when `title` matches `\[OUT_OF_SCOPE\]*`. The same contract is already asserted in the opening fixture ([`test-collect-findings.sh:19-33`](skills/review/scripts/test-collect-findings.sh): `FINDINGS_COUNT=2` with `OOS_COUNT=1` for one in-scope and one OOS bullet). No change required for count semantics.
- **Reviewer**: dyn-test-count-semantics-output.txt
- **Concern**: - **[correctness]** Scout note on `FINDINGS_COUNT=4` in [`skills/review/scripts/test-collect-findings.sh:224-227`](skills/review/scripts/test-collect-findings.sh) — This matches implementation semantics, not a false green. In [`skills/review/scripts/collect-findings.sh:390-404`](skills/review/scripts/collect-findings.sh), `count` is incremented for **every** row emitted into the main findings file (including `[OUT_OF_SCOPE]`-prefixed titles), and `OOS_COUNT` increments only when `title` matches `\[OUT_OF_SCOPE\]*`. The same contract is already asserted in the opening fixture ([`test-collect-findings.sh:19-33`](skills/review/scripts/test-collect-findings.sh): `FINDINGS_COUNT=2` with `OOS_COUNT=1` for one in-scope and one OOS bullet). No change required for count semantics.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] **[correctness]** [`skills/review/scripts/test-collect-findings.sh:231`](skills/review/scripts/test-collect-findings.sh) — `grep -Fq '[OUT_OF_SCOPE]'` uses fixed-string mode; `[` and `]` are literal. Same pattern as line 90 for the inline-TSV case. No issue.
- **Reviewer**: dyn-test-count-semantics-output.txt
- **Concern**: - **[correctness]** [`skills/review/scripts/test-collect-findings.sh:231`](skills/review/scripts/test-collect-findings.sh) — `grep -Fq '[OUT_OF_SCOPE]'` uses fixed-string mode; `[` and `]` are literal. Same pattern as line 90 for the inline-TSV case. No issue.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] code-quality: skills/review/scripts/collect-findings.sh:268-269
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] parse_output awk receives -v mode="$MODE" but never uses mode. Dead variable; no runtime effect unless someone expects MODE to change awk rules. Remove -v mode or implement mode-specific rules and test both.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] correctness: skills/review/scripts/collect-findings.sh (existing bullet rules)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Single-hash # preambles are not covered by the new /^##/ skip. Commit bullets under # Title could still be promoted as before. Optional follow-up: extend skip or document single-hash preambles as out of contract.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: skills/review/scripts/test-collect-findings.md:1-7
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] test-collect-findings.md omits canonical-3 guard mentioned in plan Fix 4 Readers of the contract doc do not see the second new regression test Add a short phrase documenting canonical-3-finding-guard (FINDINGS_COUNT/OOS split)
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: skills/review/scripts/test-collect-findings.sh:177-194
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] bullet-not-a-finding uses --mode diff while plan described description/dual-list context Harness still validates parser behavior but diverges from plan wording for traceability Match plan mode or note in test comment why diff mode is the intended matrix row
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: skills/review/scripts/collect-findings.sh:267-295
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Stale parse_output comment vs new skip semantics; broad /^##/ skip can contradict diff-mode single-list contract Comment claims diff mode preserves entire output when section headers absent, but any /^##/ line enables skip until a canonical ### header, so a diff-only response shaped as ## heading plus bullet list with no ### In-Scope/OOS lines produces zero findings silently Update the comment to describe skip behavior; optionally narrow the /^##/ matcher (e.g. commits/merge-base only) or gate skip on mode and presence of canonical headers
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: skills/review/scripts/collect-findings.sh:281-284
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] After any /^##/ line, skip stays 1 until an exact ### In-Scope or ### Out-of-Scope header; bullets after a different ## subheading inside an in-scope list are never parsed. ### In-Scope Findings then a bullet, then ## Notes, then more - bullets are silently dropped from FINDINGS_FILE. Narrow skip to known preamble headings, or reset skip for bullets under an active in-scope section, or log skipped bullet-shaped lines; document forbidden ## placement.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: skills/review/scripts/collect-findings.sh:281-284
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] /^##/ matches non-canonical ### lines, not only ## preambles Lines like ### Other (or ### In-Scope Finding typo) match /^##/ after the two exact ### rules miss, setting skip=1 and dropping following bullets until a recognized section resets Extend recognition (regex/fuzzy), treat unknown ### as non-skip, or document the strict header requirement
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: skills/review/scripts/test-collect-findings.md (contract intro)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Fix 4 asked test-collect-findings.md to note both new tests; only the preamble/commit-hash fixture is described explicitly. Operators or reviewers using the .md contract may miss the canonical-3-finding-guard unless they open test-collect-findings.sh. Add a short phrase or bullet for canonical-3-finding-guard (3 in-scope + 1 OOS; FINDINGS_COUNT=4; OOS_COUNT=1; FINDING_1–3).
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/review/scripts/collect-findings.sh:281-284
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Broad /^##/ skip drops all bullets until a canonical ### section. Reviewer places real list items under a non-canonical ## section before ### In-Scope Findings; those items silently disappear from the ballot. Narrow the skip pattern to known preamble headings or document unsupported grammar explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: skills/review/scripts/dispatch-panel.sh:163
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No test-dispatch-panel assertion covers the new anti-preamble printf line. Regression removes or corrupts the instruction string; CI stays green until manual review of live dyn outputs. Grep the synthesized dynamic reviewer agent markdown in an existing dynamic-archetypes harness case.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: skills/review/scripts/test-collect-findings.md:5
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Contract doc lists only the preamble regression; plan asked to note both new harness cases. Readers or future /implement steps may think only one test was added; canonical dual-list guard is undocumented. Extend test-collect-findings.md to mention the canonical-3-finding-guard case and its assertions.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: skills/review/scripts/test-collect-findings.sh:194
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Preamble regression test uses --mode diff while the reported bug path is description-style dynamic output. If parse_output later starts branching on mode, this test could pass while description regresses. Run the preamble fixture with --mode description (or add a second duplicate assertion under description) while mode remains unused.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: skills/review/scripts/test-collect-findings.sh:239
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Preamble regression test uses --mode diff though the bug narrative is description/dyn-reviewer oriented. Low risk today because awk ignores mode; future MODE-gated logic could leave this case untested. Use --mode description in the fixture if it matches production, or add a one-line comment explaining deliberate diff-mode choice.
- **Suggested revision**: Address the concern above.

