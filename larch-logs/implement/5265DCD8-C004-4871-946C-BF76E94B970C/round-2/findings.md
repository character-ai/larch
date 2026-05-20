### FINDING_1: **code-quality** `scripts/test-validate-research-output.sh:9-12` — The top-of-file case summary still frames structured-reviewer coverage as **52–63** while the branch adds regression cases **64–69** (JSON-with-note, sentinel-not-first, and multiline JSON). The banner range is stale relative to the expanded suite. **Suggested fix:** Update that summary line to cover **52–69** (or drop a fixed upper bound and point readers to the numbered list below).
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - **code-quality** `scripts/test-validate-research-output.sh:9-12` — The top-of-file case summary still frames structured-reviewer coverage as **52–63** while the branch adds regression cases **64–69** (JSON-with-note, sentinel-not-first, and multiline JSON). The banner range is stale relative to the expanded suite. **Suggested fix:** Update that summary line to cover **52–69** (or drop a fixed upper bound and point readers to the numbered list below).
- **Suggested revision**: Address the concern above.

### FINDING_2: **correctness** `scripts/validate-research-output.md:8` and `scripts/validate-research-output.sh:65-67` — The contract and header describe the JSON no-findings short-circuit as the **first non-empty line equaling** the one-line sentinel `{"no_issues_found": true}`, but [`json_no_issues_found_short_circuit`](scripts/validate-research-output.sh) (lines 232–243) also returns success when the first line is only an opening `{` and `jq` succeeds on the **full** `TRIMMED` stream (cases 68–69), which is not the same as “first line equals” that literal. Operators reading only the markdown could mis-implement a consumer-side check. **Suggested fix:** Tighten the prose to match behavior: e.g. state that detection is `jq` on the first non-empty line, and if that fails while the first line begins `{`, `jq` is retried on the entire trimmed non-blank body so pretty-printed objects still short-circuit, with trailing prose only allowed when the first-line parse already succeeds (single-line sentinel + notes).
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - **correctness** `scripts/validate-research-output.md:8` and `scripts/validate-research-output.sh:65-67` — The contract and header describe the JSON no-findings short-circuit as the **first non-empty line equaling** the one-line sentinel `{"no_issues_found": true}`, but [`json_no_issues_found_short_circuit`](scripts/validate-research-output.sh) (lines 232–243) also returns success when the first line is only an opening `{` and `jq` succeeds on the **full** `TRIMMED` stream (cases 68–69), which is not the same as “first line equals” that literal. Operators reading only the markdown could mis-implement a consumer-side check. **Suggested fix:** Tighten the prose to match behavior: e.g. state that detection is `jq` on the first non-empty line, and if that fails while the first line begins `{`, `jq` is retried on the entire trimmed non-blank body so pretty-printed objects still short-circuit, with trailing prose only allowed when the first-line parse already succeeds (single-line sentinel + notes).
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] The diff does not touch the Makefile; [`test-validate-research-output`](Makefile) remains on the `lint` path via `test-harnesses-7`, consistent with the “wire into make lint” intent without a new Makefile hunk.
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - The diff does not touch the Makefile; [`test-validate-research-output`](Makefile) remains on the `lint` path via `test-harnesses-7`, consistent with the “wire into make lint” intent without a new Makefile hunk.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] This review did not execute `make lint-bash32` or `bash scripts/test-validate-research-output.sh`; correctness beyond static inspection was not machine-verified here.
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - This review did not execute `make lint-bash32` or `bash scripts/test-validate-research-output.sh`; correctness beyond static inspection was not machine-verified here.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] [`set -uo pipefail`](scripts/validate-research-output.sh:134) without `-e` means failed `jq` probes inside `if` conditions do not abort the script; here-strings and `command -v jq` match existing patterns in the same file.
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - [`set -uo pipefail`](scripts/validate-research-output.sh:134) without `-e` means failed `jq` probes inside `if` conditions do not abort the script; here-strings and `command -v jq` match existing patterns in the same file.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] `git log $(git merge-base HEAD main)..HEAD --oneline`: `31819bba Loosen NO_ISSUES_FOUND sentinel to first-non-empty-line match (#2455)`; `544129bc Address code review feedback (round 1)`.
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - `git log $(git merge-base HEAD main)..HEAD --oneline`: `31819bba Loosen NO_ISSUES_FOUND sentinel to first-non-empty-line match (#2455)`; `544129bc Address code review feedback (round 1)`.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: docs/linting.md:225
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Linting catalog row still describes validation-mode sentinels generically without first-line / multi-line JSON detail. Not modified on this branch; catalog lags the validator contract slightly. Optional follow-up edit to linting.md when convenient.
- **Suggested revision**: Address the concern above.

### FINDING_8: architecture: implementation_plan JSON sentinel step
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Plan specified jq only on FIRST_LINE; implementation adds full-TRIMMED retry for leading {. Future plan-fidelity passes may report a false mismatch unless the plan archive is updated. Amend the plan or add a short note that multiline pretty-printed JSON required a deliberate extension beyond first-line-only jq.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/test-validate-research-output.sh:107-166
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Regression count exceeds the four-case plan (60–63) with additional 64–69 cases. Minor plan-vs-PR scope drift; not wrong, just more harness to maintain. Document intentional expansion in PR/issue or trim cases if minimalism is required.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/test-validate-research-output.sh:5-6
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Case-range header still says structured cases stop at 63 while 64-69 exist. Maintainers may add overlapping case numbers or misgrep coverage. Update the 52-63 banner to 52-69 (or equivalent) so the index matches the file.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: scripts/test-validate-research-output.sh:5-6
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Test header still lists structured-reviewer coverage as cases 52-63 but suite extends to 69. Maintainers grep the wrong range when adding cases. Update the summary line to 52-69 (or equivalent accurate range).
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: scripts/test-validate-research-output.sh:5-6
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Structured-reviewer case summary still claims 52-63 while cases extend through 69. Maintainers skimming the header get a wrong case count and may miss newer regressions. Update the summary range (e.g. 52-69) to match the documented case list.
- **Suggested revision**: Address the concern above.

### FINDING_13: code-quality: scripts/test-validate-research-output.sh:5-6
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Structured-reviewer case-range comment stops at 63 while cases 66-67 and 69 also exercise --structured-reviewer-mode. Readers scanning the header miss that #2455-style coverage continues through case 69. Update the summary line to cover 52-69 (or split validation vs structured ranges) and mention 66-67/69 alongside 62-63.
- **Suggested revision**: Address the concern above.

### FINDING_14: code-quality: scripts/test-validate-research-output.sh:9-13
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Case-range summary says 52-63 while harness defines cases through 69. Maintainers skimming the file header can miss cases 64-69 or assume the file ends at 63. Change the summarized range to 52-69 or remove the misleading upper bound.
- **Suggested revision**: Address the concern above.

### FINDING_15: code-quality: scripts/test-validate-research-output.sh:9-13
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Header comment claims #2455 coverage via cases 62–63 while #2455 cases are 60–63 (and JSON extensions follow). Someone triaging failures uses the wrong case numbers when mapping to issue #2455. Reword the 52–63 blurb to reference 60–63 (and optional 64–67) accurately.
- **Suggested revision**: Address the concern above.

### FINDING_16: code-quality: scripts/validate-research-output.md:3 scripts/validate-research-output.sh:65-67
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Contract/help say first line equals full one-line JSON sentinel; implementation accepts leading { with multi-line object (cases 68-69). Operators expect only the exact one-line literal on the first line; pretty-printed output is easy to misconfigure. Reword contract and header to match json_no_issues_found_short_circuit semantics (and any trailing-note limitation).
- **Suggested revision**: Address the concern above.

### FINDING_17: code-quality: scripts/validate-research-output.sh:65-67 scripts/validate-research-output.md:3
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Contract says the first non-empty line must equal the one-line JSON sentinel, but code also accepts pretty-printed JSON when the first line is only `{` via json_no_issues_found_short_circuit. A maintainer or operator reads the header or sibling markdown, ships pretty-printed JSON with first line `{`, and believes it will fail validation despite cases 68–69 proving it passes. Document JSON acceptance as first-line parse OR first-line `{` plus full trimmed body parse; mirror in structured-mode prose.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: scripts/validate-research-output.md:4;scripts/validate-research-output.sh:65-67,385-389
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Contract and header text claim the JSON no-findings short-circuit requires the first non-empty line to equal the one-line canonical JSON literal. Pretty-printed JSON (cases 68-69) uses first line `{` and succeeds via jq on the full trimmed body, so published contract and --help bullets disagree with real behavior and with tests. Document JSON acceptance as first-line one-line sentinel OR full trimmed pretty-printed object starting with `{` that jq parses with no_issues_found true; align script header and inline comments with json_no_issues_found_short_circuit.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: scripts/validate-research-output.sh:228-244
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Multi-line pretty-printed JSON no-findings plus trailing operational text fails jq on full trimmed body, so JSON short-circuit does not fire despite contract claiming trailing notes are accepted for JSON sentinels. Input matches case 68/69 heredoc then blank line and Verification: ... prose: jq parse error on second branch, validation-mode exits 2 and structured-reviewer-mode exits 5 instead of 0. Document limitation or parse only the first JSON value / strip validated suffix so notes after a multi-line object still short-circuit; add tests for pretty JSON + trailing note.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: scripts/validate-research-output.sh:232-243
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] First-line-only jq success ignores whether later trimmed lines form valid JSON with the first value. One-line canonical sentinel plus trailing lines that are not valid continuation of a single JSON document still exit 0; whole-body jq could have failed before. Document as intentional or narrow the fast path (e.g. single-line trim only) or always validate the full trimmed stream when multiple lines exist.
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: scripts/validate-research-output.sh:65-67; scripts/validate-research-output.md:1
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Header and markdown claim JSON short-circuit requires first line to equal one-line {"no_issues_found": true}. Pretty-printed multi-line JSON is accepted when first line is only { via full-trimmed jq retry (cases 68-69), contradicting the literal contract and sed-extracted --help text. Update header and validate-research-output.md to document the opening-brace plus full-trimmed parse fallback in lockstep with json_no_issues_found_short_circuit.
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: scripts/validate-research-output.sh:65-67; scripts/validate-research-output.sh:385-389; scripts/validate-research-output.md:3
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Contract and header say JSON no-findings short-circuit requires the first non-empty line to equal the one-line sentinel. Regression tests 68-69 accept pretty-printed JSON whose first non-empty line is only `{` because jq runs on the full trimmed body; readers of --help or validate-research-output.md can misconfigure reviewers or file false bugs. Document JSON as: first-line one-line sentinel OR first line opens `{` and jq on full trimmed_nonblank_content stream validates the canonical no-findings object; sync header, inline comment block, and validate-research-output.md paragraph.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: scripts/validate-research-output.sh:65-66 scripts/validate-research-output.md:3
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Contract and --help text say first line must equal one-line JSON sentinel while code accepts multi-line JSON via full-body jq retry. External tooling or humans implementing strict first-line string equality reject pretty-printed no-findings outputs that cases 68-69 assert pass. Align header, md opening paragraph, and help text with json_no_issues_found_short_circuit (first-line literal OR complete first-line JSON OR leading { plus full trimmed object parse).
- **Suggested revision**: Address the concern above.

