### FINDING_1: **code-quality** `scripts/test-validate-research-output.sh:9-12` — The top-of-file case summary still frames structured-reviewer coverage as **52–63** while the branch adds regression cases **64–69** (JSON-with-note, sentinel-not-first, and multiline JSON). The banner range is stale relative to the expanded suite. **Suggested fix:** Update that summary line to cover **52–69** (or drop a fixed upper bound and point readers to the numbered list below).
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - **code-quality** `scripts/test-validate-research-output.sh:9-12` — The top-of-file case summary still frames structured-reviewer coverage as **52–63** while the branch adds regression cases **64–69** (JSON-with-note, sentinel-not-first, and multiline JSON). The banner range is stale relative to the expanded suite. **Suggested fix:** Update that summary line to cover **52–69** (or drop a fixed upper bound and point readers to the numbered list below).
- **Suggested revision**: Address the concern above.


### FINDING_15: code-quality: scripts/test-validate-research-output.sh:9-13
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Header comment claims #2455 coverage via cases 62–63 while #2455 cases are 60–63 (and JSON extensions follow). Someone triaging failures uses the wrong case numbers when mapping to issue #2455. Reword the 52–63 blurb to reference 60–63 (and optional 64–67) accurately.
- **Suggested revision**: Address the concern above.


### FINDING_19: correctness: scripts/validate-research-output.sh:228-244
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Multi-line pretty-printed JSON no-findings plus trailing operational text fails jq on full trimmed body, so JSON short-circuit does not fire despite contract claiming trailing notes are accepted for JSON sentinels. Input matches case 68/69 heredoc then blank line and Verification: ... prose: jq parse error on second branch, validation-mode exits 2 and structured-reviewer-mode exits 5 instead of 0. Document limitation or parse only the first JSON value / strip validated suffix so notes after a multi-line object still short-circuit; add tests for pretty JSON + trailing note.
- **Suggested revision**: Address the concern above.


### FINDING_2: **correctness** `scripts/validate-research-output.md:8` and `scripts/validate-research-output.sh:65-67` — The contract and header describe the JSON no-findings short-circuit as the **first non-empty line equaling** the one-line sentinel `{"no_issues_found": true}`, but [`json_no_issues_found_short_circuit`](scripts/validate-research-output.sh) (lines 232–243) also returns success when the first line is only an opening `{` and `jq` succeeds on the **full** `TRIMMED` stream (cases 68–69), which is not the same as “first line equals” that literal. Operators reading only the markdown could mis-implement a consumer-side check. **Suggested fix:** Tighten the prose to match behavior: e.g. state that detection is `jq` on the first non-empty line, and if that fails while the first line begins `{`, `jq` is retried on the entire trimmed non-blank body so pretty-printed objects still short-circuit, with trailing prose only allowed when the first-line parse already succeeds (single-line sentinel + notes).
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - **correctness** `scripts/validate-research-output.md:8` and `scripts/validate-research-output.sh:65-67` — The contract and header describe the JSON no-findings short-circuit as the **first non-empty line equaling** the one-line sentinel `{"no_issues_found": true}`, but [`json_no_issues_found_short_circuit`](scripts/validate-research-output.sh) (lines 232–243) also returns success when the first line is only an opening `{` and `jq` succeeds on the **full** `TRIMMED` stream (cases 68–69), which is not the same as “first line equals” that literal. Operators reading only the markdown could mis-implement a consumer-side check. **Suggested fix:** Tighten the prose to match behavior: e.g. state that detection is `jq` on the first non-empty line, and if that fails while the first line begins `{`, `jq` is retried on the entire trimmed non-blank body so pretty-printed objects still short-circuit, with trailing prose only allowed when the first-line parse already succeeds (single-line sentinel + notes).
- **Suggested revision**: Address the concern above.


