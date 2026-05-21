# Review Round 1

- Mode: `diff`
- Accepted findings: 8
- Rejected findings: 0
- Exonerated findings: 6
- Neutral findings: 0

## Accepted Findings

### FINDING_1: **correctness** `.claude/skills/audit-runs/scans.tsv:5` — The jq fragment is valid for normal rows where `id` and `prose_body` are JSON strings, but `(.id|startswith("REJ_"))` and `(.prose_body|test("…"))` throw on `null`/non-string inputs (`startswith` and `test` require strings), so a malformed or partial JSONL line could make a manual `jq` pass over the file fail instead of treating the row as non-matching. **Suggested fix:** Harden the predicate with string defaults, e.g. `((.id//"")|type=="string" and startswith("REJ_"))` and `((.prose_body//"")|test("### FINDING_[0-9A-Za-z_]+:"))`, matching how `category` already uses `(.category//"")`.
- **Reviewer**: dyn-scan-jq-filter-output.txt
- **Concern**: - **correctness** `.claude/skills/audit-runs/scans.tsv:5` — The jq fragment is valid for normal rows where `id` and `prose_body` are JSON strings, but `(.id|startswith("REJ_"))` and `(.prose_body|test("…"))` throw on `null`/non-string inputs (`startswith` and `test` require strings), so a malformed or partial JSONL line could make a manual `jq` pass over the file fail instead of treating the row as non-matching. **Suggested fix:** Harden the predicate with string defaults, e.g. `((.id//"")|type=="string" and startswith("REJ_"))` and `((.prose_body//"")|test("### FINDING_[0-9A-Za-z_]+:"))`, matching how `category` already uses `(.category//"")`.
- **Suggested revision**: Address the concern above.


### FINDING_18: correctness: scripts/compose-review-findings.sh:69-88
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Triple-hash extract_category treats any no-second-colon remainder after FINDING_ as category under strict=0. Existing fixture body ### FINDING_18: Review finding title (j-impl rejected test) yields category Review finding title instead of empty, contradicting FINDING_N: <category>: intent and changing JSONL from prior empty category. Narrow ### FINDING_ parsing (e.g. require second colon or whitelist five tags for REJ) and lock behavior with an assertion on REJ_C1 category in that test.
- **Suggested revision**: Address the concern above.


### FINDING_19: correctness: scripts/compose-review-findings.sh:70-72
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] awk /^### FINDING_/ is stricter than parse_artifact ^###[[:space:]]+FINDING_ Multi-space after ### leaves category blank despite FINDING header in body Use /^###[[:space:]]+FINDING_/ aligned with parser
- **Suggested revision**: Address the concern above.


### FINDING_2: **correctness** `scripts/compose-review-findings.sh:70-71` — Rejected inner headings are appended whenever a line matches `^###[[:space:]]` (see the `code-review-rejected` path around lines 242–245), so the body can legally contain multiple spaces after `###` (for example `###   FINDING_1:`). The new `extract_category` rule only matches `/^### FINDING_/` (exactly one space before `FINDING_`) and strips the prefix with `sub(/^### FINDING_[^:]*:/, "")`, so those bodies never hit the triple-hash branch and can still end up with an empty `category` even though a `### … FINDING_…:` header is present—exactly the failure mode the scan is meant to catch. **Suggested fix:** Align the awk rule and `sub` with the parser by using a prefix pattern such as `/^###[[:space:]]+FINDING_/` and `sub(/^###[[:space:]]+FINDING_[^:]*:/, "")` (and keep trimming leading whitespace after the prefix as today).
- **Reviewer**: dyn-scan-jq-filter-output.txt
- **Concern**: - **correctness** `scripts/compose-review-findings.sh:70-71` — Rejected inner headings are appended whenever a line matches `^###[[:space:]]` (see the `code-review-rejected` path around lines 242–245), so the body can legally contain multiple spaces after `###` (for example `###   FINDING_1:`). The new `extract_category` rule only matches `/^### FINDING_/` (exactly one space before `FINDING_`) and strips the prefix with `sub(/^### FINDING_[^:]*:/, "")`, so those bodies never hit the triple-hash branch and can still end up with an empty `category` even though a `### … FINDING_…:` header is present—exactly the failure mode the scan is meant to catch. **Suggested fix:** Align the awk rule and `sub` with the parser by using a prefix pattern such as `/^###[[:space:]]+FINDING_/` and `sub(/^###[[:space:]]+FINDING_[^:]*:/, "")` (and keep trimming leading whitespace after the prefix as today).
- **Suggested revision**: Address the concern above.


### FINDING_21: correctness: scripts/compose-review-findings.sh:70-89
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] ### FINDING_ awk rule can run when the inner-heading prefix strip did not match Malformed prose line matching /^### FINDING_/ without ### FINDING_<id>: can yield the entire line as category when strict=0. Guard on successful sub() or use a stricter anchored regex before treating the line as an inner FINDING heading.
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: scripts/compose-review-findings.sh:70-90
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Triple-hash awk anchor is stricter than rejected inner-heading matcher on whitespace after `###` Producers using tabs or multiple spaces before `FINDING_` could still populate prose_body but leave category empty. Match flexible whitespace after `###` in awk (align with `^###[[:space:]]+` semantics) before parsing the FINDING id and category.
- **Suggested revision**: Address the concern above.


### FINDING_23: risk-integration: scripts/test-compose-review-findings.sh:221-242
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Missing regression for plan-listed no-second-colon triple-hash shape CI could stay green if the no-colon remainder branch in extract_category regressed for REJ_* bodies. Add a harness row using `### FINDING_<id>: <canonical-tag>` with no trailing location colon and assert `category` on the synthetic REJ id.
- **Suggested revision**: Address the concern above.


### FINDING_4: **correctness** `scripts/compose-review-findings.sh:70-90` — The new `/^### FINDING_/` rule runs before `^## /` and, on the first matching inner-heading line, takes the text after the stripped `### FINDING_<id>:` prefix and treats everything up to the next `:` as the category, or the whole remainder if there is no `:` (same structure as the `^## /` branch). For rejected blocks whose inner line is the title-only shape `### FINDING_<id>: <free-form title>` with no second `:` (for example the existing fixture `### FINDING_18: Review finding title` in `scripts/test-compose-review-findings.sh:241-245`), that remainder is a sentence-style title, not a focus-area tag; the script previously left `category` empty because no `##` line matched, but with this change `category` becomes non-empty junk (e.g. `Review finding title`), which is a behavioral regression for any consumer that assumed “non-empty category means a real focus-area tag” or that relied on emptiness for title-only rejections. **Suggested fix:** Narrow the `### FINDING_` branch so single-colon bodies only yield a category when the candidate is one of the five canonical tags (matching the spirit of the new `rej-category-blank` guardrail), or require a second `:` in the line (true `### FINDING_n: <tag>: <location>` form) before treating the first segment as `category`, while still allowing the documented `### FINDING_n: architecture` case if you explicitly whitelist the tag when no second colon is present.
- **Reviewer**: dyn-awk-parsing-output.txt
- **Concern**: - **correctness** `scripts/compose-review-findings.sh:70-90` — The new `/^### FINDING_/` rule runs before `^## /` and, on the first matching inner-heading line, takes the text after the stripped `### FINDING_<id>:` prefix and treats everything up to the next `:` as the category, or the whole remainder if there is no `:` (same structure as the `^## /` branch). For rejected blocks whose inner line is the title-only shape `### FINDING_<id>: <free-form title>` with no second `:` (for example the existing fixture `### FINDING_18: Review finding title` in `scripts/test-compose-review-findings.sh:241-245`), that remainder is a sentence-style title, not a focus-area tag; the script previously left `category` empty because no `##` line matched, but with this change `category` becomes non-empty junk (e.g. `Review finding title`), which is a behavioral regression for any consumer that assumed “non-empty category means a real focus-area tag” or that relied on emptiness for title-only rejections. **Suggested fix:** Narrow the `### FINDING_` branch so single-colon bodies only yield a category when the candidate is one of the five canonical tags (matching the spirit of the new `rej-category-blank` guardrail), or require a second `:` in the line (true `### FINDING_n: <tag>: <location>` form) before treating the first segment as `category`, while still allowing the documented `### FINDING_n: architecture` case if you explicitly whitelist the tag when no second colon is present.
- **Suggested revision**: Address the concern above.


