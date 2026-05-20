### FINDING_1: **code-quality** `scripts/validate-research-output.sh:362-367` — The block comment above the `--validation-mode` short-circuits still states that sentinels “must be the entire trimmed file content” and describes short-circuit rules that no longer match the implementation for `NO_ISSUES_FOUND` and the JSON sentinel (those now use `FIRST_LINE` while `CURSOR_EMPTY_RESPONSE` correctly remains a full-`TRIMMED` equality check per [`scripts/validate-research-output.md`](scripts/validate-research-output.md)). **Suggested fix:** Rewrite that comment so it matches the real invariants: first non-empty line of `TRIMMED` for the two no-findings sentinels, full `TRIMMED` for `CURSOR_EMPTY_RESPONSE`, and clarify that “partial match” means the sentinel not occupying the first non-empty line of `TRIMMED` (or inline on a line with other text), consistent with the updated header and contract doc.
- **Reviewer**: dyn-sentinel-boundary-output.txt
- **Concern**: - **code-quality** `scripts/validate-research-output.sh:362-367` — The block comment above the `--validation-mode` short-circuits still states that sentinels “must be the entire trimmed file content” and describes short-circuit rules that no longer match the implementation for `NO_ISSUES_FOUND` and the JSON sentinel (those now use `FIRST_LINE` while `CURSOR_EMPTY_RESPONSE` correctly remains a full-`TRIMMED` equality check per [`scripts/validate-research-output.md`](scripts/validate-research-output.md)). **Suggested fix:** Rewrite that comment so it matches the real invariants: first non-empty line of `TRIMMED` for the two no-findings sentinels, full `TRIMMED` for `CURSOR_EMPTY_RESPONSE`, and clarify that “partial match” means the sentinel not occupying the first non-empty line of `TRIMMED` (or inline on a line with other text), consistent with the updated header and contract doc.
- **Suggested revision**: Address the concern above.


### FINDING_15: code-quality: scripts/validate-research-output.sh:362-367
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Validation-mode sentinel comment still describes entire-trimmed-content semantics for all sentinels contradicting FIRST_LINE behavior for NO_ISSUES_FOUND and JSON. Maintainers may misread contract and reintroduce wrong checks or mis-document collector behavior. Reword to separate CURSOR_EMPTY_RESPONSE (full TRIMMED) from no-findings sentinels (first non-empty line with trailing content allowed).
- **Suggested revision**: Address the concern above.


### FINDING_16: code-quality: scripts/validate-research-output.sh:362-367
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Stale validation-mode short-circuit banner comment Comment still claims entire-trimmed sentinel equality and no partial short-circuit; code now first-line matches no-findings sentinels with trailing content preserved Split the contract: CURSOR_EMPTY_RESPONSE remains full TRIMMED equality; no-findings JSON/NO_ISSUES_FOUND match first non-empty line of TRIMMED
- **Suggested revision**: Address the concern above.


### FINDING_2: **correctness** `scripts/test-validate-research-output.sh:4-6` — The file header still groups structured-reviewer coverage as cases **52-59**, even though new cases **62-63** are also `--structured-reviewer-mode`; the detailed index for 60-63 was added lower in the file, so the top summary is now internally inconsistent. **Suggested fix:** Update the header summary (e.g., extend the range to 52-63 or add an explicit line that 62-63 continue structured-reviewer-mode) so newcomers see one coherent case map.
- **Reviewer**: dyn-test-coverage-output.txt
- **Concern**: - **correctness** `scripts/test-validate-research-output.sh:4-6` — The file header still groups structured-reviewer coverage as cases **52-59**, even though new cases **62-63** are also `--structured-reviewer-mode`; the detailed index for 60-63 was added lower in the file, so the top summary is now internally inconsistent. **Suggested fix:** Update the header summary (e.g., extend the range to 52-63 or add an explicit line that 62-63 continue structured-reviewer-mode) so newcomers see one coherent case map.
- **Suggested revision**: Address the concern above.


### FINDING_21: correctness: scripts/validate-research-output.sh:362-367
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Validation-mode sentinel comment still claims entire trimmed content for all sentinels Developers or /implement may believe NO_ISSUES_FOUND/JSON still require whole-file equality and miss that trailing lines are allowed; contradicts new contract Split comment: CURSOR_EMPTY_RESPONSE vs first-line no-findings rules; align with validate-research-output.md
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: scripts/validate-research-output.sh:362-367
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Validation-mode short-circuit block comment still describes entire-trimmed-content sentinel matching for all sentinels Maintainers or future edits may reintroduce strict full-file equality or mis-diagnose intentional first-line behavior as a bug Update the comment to split CURSOR_EMPTY_RESPONSE (full trimmed match) from no-findings sentinels (first non-empty line) and note non-first-line sentinels fall through to normal validation
- **Suggested revision**: Address the concern above.


### FINDING_23: correctness: scripts/validate-research-output.sh:362-367
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Stale comment claims entire-trimmed-content sentinel rule while code uses first-non-empty-line matching for no-findings sentinels. Maintainers may “fix” behavior back to full-content matching or mis-gauge security/short-circuit semantics when editing. Rewrite the section-0 comment to describe first-line no-findings sentinels and unchanged full-content rule for CURSOR_EMPTY_RESPONSE.
- **Suggested revision**: Address the concern above.


### FINDING_25: risk-integration: scripts/validate-research-output.sh:362-367
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Validation-mode comment still claims entire-trimmed-body sentinel match Maintainers or auditors may believe CURSOR_EMPTY_RESPONSE and no-findings gates share the same trimming rule and miss that trailing prose is accepted without citation/word-count checks after a first-line sentinel. Rewrite the block comment for first-non-empty-line no-findings sentinels vs full-body CURSOR_EMPTY_RESPONSE to match validate-research-output.md.
- **Suggested revision**: Address the concern above.


### FINDING_3: **correctness** `scripts/test-validate-research-output.sh:540-561` — Cases 60-63 lock in the `NO_ISSUES_FOUND` first-line / not-first-line behavior, but there is **no** symmetric regression for the **JSON** no-findings sentinel on the first line with trailing operational prose, even though `scripts/validate-research-output.sh` applies the same `FIRST_LINE` + `jq` short-circuit for JSON in both structured-reviewer and validation paths. **Suggested fix:** Add fixtures mirroring 60/61 (and optionally 62/63) using `{"no_issues_found": true}` as the first non-empty line with trailing notes so both sentinel branches are covered.
- **Reviewer**: dyn-test-coverage-output.txt
- **Concern**: - **correctness** `scripts/test-validate-research-output.sh:540-561` — Cases 60-63 lock in the `NO_ISSUES_FOUND` first-line / not-first-line behavior, but there is **no** symmetric regression for the **JSON** no-findings sentinel on the first line with trailing operational prose, even though `scripts/validate-research-output.sh` applies the same `FIRST_LINE` + `jq` short-circuit for JSON in both structured-reviewer and validation paths. **Suggested fix:** Add fixtures mirroring 60/61 (and optionally 62/63) using `{"no_issues_found": true}` as the first non-empty line with trailing notes so both sentinel branches are covered.
- **Suggested revision**: Address the concern above.


### FINDING_4: **correctness** `scripts/test-validate-research-output.sh:547-548` — The case 61 comment claims “9 words” for the fixture `Verification: mktemp failed.` plus a later `NO_ISSUES_FOUND` line, but the validator’s word-count `awk` sums `NF` per non-fence line and this fixture yields **four** fields total (`Verification:`, `mktemp`, `failed.`, `NO_ISSUES_FOUND`), not nine; exit **2** is still the right expectation because 4 is below the validation-mode default `--min-words` floor. **Suggested fix:** Replace the incorrect word count in the comment with the actual count (or drop the numeric claim) and describe exit 2 as the thin-body path without citing a wrong tally.
- **Reviewer**: dyn-test-coverage-output.txt
- **Concern**: - **correctness** `scripts/test-validate-research-output.sh:547-548` — The case 61 comment claims “9 words” for the fixture `Verification: mktemp failed.` plus a later `NO_ISSUES_FOUND` line, but the validator’s word-count `awk` sums `NF` per non-fence line and this fixture yields **four** fields total (`Verification:`, `mktemp`, `failed.`, `NO_ISSUES_FOUND`), not nine; exit **2** is still the right expectation because 4 is below the validation-mode default `--min-words` floor. **Suggested fix:** Replace the incorrect word count in the comment with the actual count (or drop the numeric claim) and describe exit 2 as the thin-body path without citing a wrong tally.
- **Suggested revision**: Address the concern above.


### FINDING_5: **correctness** `scripts/validate-research-output.sh:328-337,375-381` — The JSON no-findings short-circuit now feeds only `FIRST_LINE` into `jq` instead of the full `TRIMMED` string. Any producer that emitted a pretty-printed or otherwise line-wrapped JSON object (first physical line is `{` or similar, with the rest of the object on following lines) used to pass because `jq` parsed the entire `TRIMMED` document; after this change those inputs fall through and can fail later (e.g. exit 2 in `--validation-mode`, exit 5 in `--structured-reviewer-mode`). That is a semantic narrowing beyond “allow trailing notes after a one-line sentinel,” and there is no regression test covering multi-line JSON. **Suggested fix:** Either document this as an intentional breaking change and keep the current behavior, or preserve backward compatibility—for example by trying `jq` on `FIRST_LINE` first and, on failure, retrying with the full `TRIMMED` only when the first line looks like incomplete JSON (e.g. starts with `{` but `jq` on `FIRST_LINE` fails), or by adding an explicit multi-line parse path; add a test that locks the chosen contract.
- **Reviewer**: dyn-sentinel-boundary-output.txt
- **Concern**: - **correctness** `scripts/validate-research-output.sh:328-337,375-381` — The JSON no-findings short-circuit now feeds only `FIRST_LINE` into `jq` instead of the full `TRIMMED` string. Any producer that emitted a pretty-printed or otherwise line-wrapped JSON object (first physical line is `{` or similar, with the rest of the object on following lines) used to pass because `jq` parsed the entire `TRIMMED` document; after this change those inputs fall through and can fail later (e.g. exit 2 in `--validation-mode`, exit 5 in `--structured-reviewer-mode`). That is a semantic narrowing beyond “allow trailing notes after a one-line sentinel,” and there is no regression test covering multi-line JSON. **Suggested fix:** Either document this as an intentional breaking change and keep the current behavior, or preserve backward compatibility—for example by trying `jq` on `FIRST_LINE` first and, on failure, retrying with the full `TRIMMED` only when the first line looks like incomplete JSON (e.g. starts with `{` but `jq` on `FIRST_LINE` fails), or by adding an explicit multi-line parse path; add a test that locks the chosen contract.
- **Suggested revision**: Address the concern above.


### FINDING_6: **correctness** `scripts/validate-research-output.sh:362-367` — The `--- 0. Validation-mode short-circuits` comment block still states that sentinels must equal the **entire** trimmed file and that only “partial matches inside larger prose” are excluded, which no longer matches the implementation: `NO_ISSUES_FOUND` and the JSON no-findings object are now accepted when they match the **first non-empty line** of `trimmed_nonblank_content` output (while `CURSOR_EMPTY_RESPONSE` correctly remains a full-trimmed equality check). **Suggested fix:** Rewrite that comment to describe first-non-empty-line matching for the two no-findings short-circuits and keep the “entire trimmed content” wording only for `CURSOR_EMPTY_RESPONSE` (and any other full-content rules).
- **Reviewer**: dyn-test-coverage-output.txt
- **Concern**: - **correctness** `scripts/validate-research-output.sh:362-367` — The `--- 0. Validation-mode short-circuits` comment block still states that sentinels must equal the **entire** trimmed file and that only “partial matches inside larger prose” are excluded, which no longer matches the implementation: `NO_ISSUES_FOUND` and the JSON no-findings object are now accepted when they match the **first non-empty line** of `trimmed_nonblank_content` output (while `CURSOR_EMPTY_RESPONSE` correctly remains a full-trimmed equality check). **Suggested fix:** Rewrite that comment to describe first-non-empty-line matching for the two no-findings short-circuits and keep the “entire trimmed content” wording only for `CURSOR_EMPTY_RESPONSE` (and any other full-content rules).
- **Suggested revision**: Address the concern above.


