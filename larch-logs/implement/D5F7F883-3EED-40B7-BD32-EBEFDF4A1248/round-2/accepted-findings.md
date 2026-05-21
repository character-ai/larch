### FINDING_1: **correctness** `.claude/skills/audit-runs/scans.tsv:5` — The `rej-category-blank` `pattern` uses `test("### FINDING_[0-9A-Za-z_]+:")`, which only matches a single ASCII space after `###`, while `extract_category` in `scripts/compose-review-findings.sh` matches `^###[[:space:]]+FINDING_` (any run of spaces/tabs). A rejected body whose inner heading is `###␠␠FINDING_1: …` would still yield a blank `category` from the awk rules but would not be detected by this scan (false negative relative to the stated acceptance goal). **Suggested fix:** Narrow the gap by aligning the jq regex with the awk/header grammar, e.g. use `test("###[[:space:]]+FINDING_[0-9A-Za-z_]+:")` (and keep the existing `((.prose_body//"")|…)` plumbing) so the audit signal tracks the same whitespace-flexible header the composer treats as authoritative.
- **Reviewer**: dyn-scan-pattern-output.txt
- **Concern**: - **correctness** `.claude/skills/audit-runs/scans.tsv:5` — The `rej-category-blank` `pattern` uses `test("### FINDING_[0-9A-Za-z_]+:")`, which only matches a single ASCII space after `###`, while `extract_category` in `scripts/compose-review-findings.sh` matches `^###[[:space:]]+FINDING_` (any run of spaces/tabs). A rejected body whose inner heading is `###␠␠FINDING_1: …` would still yield a blank `category` from the awk rules but would not be detected by this scan (false negative relative to the stated acceptance goal). **Suggested fix:** Narrow the gap by aligning the jq regex with the awk/header grammar, e.g. use `test("###[[:space:]]+FINDING_[0-9A-Za-z_]+:")` (and keep the existing `((.prose_body//"")|…)` plumbing) so the audit signal tracks the same whitespace-flexible header the composer treats as authoritative.
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: .claude/skills/audit-runs/scans.tsv:5
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] rej-category-blank jq matches any ### FINDING_ header with empty category Title-only inner lines and other valid REJ bodies that intentionally have blank category still match test("### FINDING_[...]:"); jq returns true for REJ_C1 with prose_body "### FINDING_18: Review finding title", contradicting scripts/test-compose-review-findings.sh:220-221 Narrow the regex or add conjuncts so the scan only fires when prose_body contains a category-shaped triple-hash line (e.g. canonical tag plus location colon) while category remains empty
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: scripts/compose-review-findings.md:31
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] category contract misstates when category is empty vs non-OOS ## lines and triple-hash REJ lines Operators or tooling infer that any unrecognized tag yields empty category only under OOS strict mode, while REJ rows can still carry arbitrary ##-derived labels and REJ ### lines can be empty for different reasons; strict canonical filtering is not OOS-only Clarify in the contract line: ## vs ### rules, strict=1 only for out_of_scope, and the stricter ### single-colon behavior
- **Suggested revision**: Address the concern above.


