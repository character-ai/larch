### FINDING_1: **Important** — correctness — `skills/review/scripts/collect-findings.sh:281-285`: The new catch-all `^##` skip state drops legitimate fail-open findings under common noncanonical headings like `## Findings`, contradicting the existing diff-mode contract that output without canonical headers is treated as in-scope. Concrete failing scenario: reviewer output `## Findings` followed by `- Real parser issue...` in diff mode now produces zero parser rows and can be recorded as non-substantive, so a real finding is silently lost. Narrow the skip rule to the known preamble headings, such as `## Commits since merge-base`, or skip only commit-hash bullets in that preamble; add a regression test for `## Findings` plus a bullet still producing `FINDINGS_COUNT=1`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** — correctness — `skills/review/scripts/collect-findings.sh:281-285`: The new catch-all `^##` skip state drops legitimate fail-open findings under common noncanonical headings like `## Findings`, contradicting the existing diff-mode contract that output without canonical headers is treated as in-scope. Concrete failing scenario: reviewer output `## Findings` followed by `- Real parser issue...` in diff mode now produces zero parser rows and can be recorded as non-substantive, so a real finding is silently lost. Narrow the skip rule to the known preamble headings, such as `## Commits since merge-base`, or skip only commit-hash bullets in that preamble; add a regression test for `## Findings` plus a bullet still producing `FINDINGS_COUNT=1`. I ran the requested `git log` command and checked the parser behavior with the changed awk rules.
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


### FINDING_16: risk-integration: skills/review/scripts/collect-findings.sh:281-284
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Broad /^##/ skip drops all bullets until a canonical ### section. Reviewer places real list items under a non-canonical ## section before ### In-Scope Findings; those items silently disappear from the ballot. Narrow the skip pattern to known preamble headings or document unsupported grammar explicitly.
- **Suggested revision**: Address the concern above.


### FINDING_17: risk-integration: skills/review/scripts/dispatch-panel.sh:163
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No test-dispatch-panel assertion covers the new anti-preamble printf line. Regression removes or corrupts the instruction string; CI stays green until manual review of live dyn outputs. Grep the synthesized dynamic reviewer agent markdown in an existing dynamic-archetypes harness case.
- **Suggested revision**: Address the concern above.


### FINDING_2: **Latent**, `risk-integration`, [`skills/review/scripts/collect-findings.sh`](skills/review/scripts/collect-findings.sh):281-284 — Any line matching `^##` starts a skip region until a canonical `### In-Scope Findings` or `### Out-of-Scope Observations` line. Reviewers who use non-canonical Markdown (for example `## In-Scope Findings` or other `##` section titles instead of the exact `###` headers) will have bullets and bodies under that region ignored, so real findings can be **silently dropped** while the raw file still reads as substantive. **Scenario:** A specialist template omits one `#` on the section header; Step 3a shows fewer findings than the reviewer intended with no hard failure. **Suggested fix:** Document the strict header grammar in the reviewer contract, add a narrow exception only if you must support `##` variants, or emit a warning when `skip` stayed 1 for the whole file but bullets existed after the first `##`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **Latent**, `risk-integration`, [`skills/review/scripts/collect-findings.sh`](skills/review/scripts/collect-findings.sh):281-284 — Any line matching `^##` starts a skip region until a canonical `### In-Scope Findings` or `### Out-of-Scope Observations` line. Reviewers who use non-canonical Markdown (for example `## In-Scope Findings` or other `##` section titles instead of the exact `###` headers) will have bullets and bodies under that region ignored, so real findings can be **silently dropped** while the raw file still reads as substantive. **Scenario:** A specialist template omits one `#` on the section header; Step 3a shows fewer findings than the reviewer intended with no hard failure. **Suggested fix:** Document the strict header grammar in the reviewer contract, add a narrow exception only if you must support `##` variants, or emit a warning when `skip` stayed 1 for the whole file but bullets existed after the first `##`. ---
- **Suggested revision**: Address the concern above.


### FINDING_3: **[correctness]** [`skills/review/scripts/collect-findings.sh:281-284`](skills/review/scripts/collect-findings.sh) — The new `/^##/` rule matches any line whose first two characters are `##`. In awk, that includes every `### ...` line that does **not** match the two earlier exact headers (`### Out-of-Scope Observations`, `### In-Scope Findings`). A non-canonical third-level heading (e.g. `### Notes` between sections) therefore runs `flush(); skip=1; next` and subsequent list bullets are dropped until another canonical header clears `skip`, whereas before they would have been folded into the prose `NF` path. That is a real narrowing of accepted reviewer grammar introduced by this branch. **Suggested fix:** Restrict the skipper to level-2 headings only (for example require the third character not to be `#`, or match `^## ` / `^##[^#]` with an explicit `^##$` edge case), or add explicit allow patterns for benign `###` subheads if you want to keep `^##` as written.
- **Reviewer**: dyn-test-count-semantics-output.txt
- **Concern**: - **[correctness]** [`skills/review/scripts/collect-findings.sh:281-284`](skills/review/scripts/collect-findings.sh) — The new `/^##/` rule matches any line whose first two characters are `##`. In awk, that includes every `### ...` line that does **not** match the two earlier exact headers (`### Out-of-Scope Observations`, `### In-Scope Findings`). A non-canonical third-level heading (e.g. `### Notes` between sections) therefore runs `flush(); skip=1; next` and subsequent list bullets are dropped until another canonical header clears `skip`, whereas before they would have been folded into the prose `NF` path. That is a real narrowing of accepted reviewer grammar introduced by this branch. **Suggested fix:** Restrict the skipper to level-2 headings only (for example require the third character not to be `#`, or match `^## ` / `^##[^#]` with an explicit `^##$` edge case), or add explicit allow patterns for benign `###` subheads if you want to keep `^##` as written.
- **Suggested revision**: Address the concern above.


