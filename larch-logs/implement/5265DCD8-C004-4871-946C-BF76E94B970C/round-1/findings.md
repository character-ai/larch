### FINDING_1: **code-quality** `scripts/validate-research-output.sh:362-367` — The block comment above the `--validation-mode` short-circuits still states that sentinels “must be the entire trimmed file content” and describes short-circuit rules that no longer match the implementation for `NO_ISSUES_FOUND` and the JSON sentinel (those now use `FIRST_LINE` while `CURSOR_EMPTY_RESPONSE` correctly remains a full-`TRIMMED` equality check per [`scripts/validate-research-output.md`](scripts/validate-research-output.md)). **Suggested fix:** Rewrite that comment so it matches the real invariants: first non-empty line of `TRIMMED` for the two no-findings sentinels, full `TRIMMED` for `CURSOR_EMPTY_RESPONSE`, and clarify that “partial match” means the sentinel not occupying the first non-empty line of `TRIMMED` (or inline on a line with other text), consistent with the updated header and contract doc.
- **Reviewer**: dyn-sentinel-boundary-output.txt
- **Concern**: - **code-quality** `scripts/validate-research-output.sh:362-367` — The block comment above the `--validation-mode` short-circuits still states that sentinels “must be the entire trimmed file content” and describes short-circuit rules that no longer match the implementation for `NO_ISSUES_FOUND` and the JSON sentinel (those now use `FIRST_LINE` while `CURSOR_EMPTY_RESPONSE` correctly remains a full-`TRIMMED` equality check per [`scripts/validate-research-output.md`](scripts/validate-research-output.md)). **Suggested fix:** Rewrite that comment so it matches the real invariants: first non-empty line of `TRIMMED` for the two no-findings sentinels, full `TRIMMED` for `CURSOR_EMPTY_RESPONSE`, and clarify that “partial match” means the sentinel not occupying the first non-empty line of `TRIMMED` (or inline on a line with other text), consistent with the updated header and contract doc.
- **Suggested revision**: Address the concern above.

### FINDING_2: **correctness** `scripts/test-validate-research-output.sh:4-6` — The file header still groups structured-reviewer coverage as cases **52-59**, even though new cases **62-63** are also `--structured-reviewer-mode`; the detailed index for 60-63 was added lower in the file, so the top summary is now internally inconsistent. **Suggested fix:** Update the header summary (e.g., extend the range to 52-63 or add an explicit line that 62-63 continue structured-reviewer-mode) so newcomers see one coherent case map.
- **Reviewer**: dyn-test-coverage-output.txt
- **Concern**: - **correctness** `scripts/test-validate-research-output.sh:4-6` — The file header still groups structured-reviewer coverage as cases **52-59**, even though new cases **62-63** are also `--structured-reviewer-mode`; the detailed index for 60-63 was added lower in the file, so the top summary is now internally inconsistent. **Suggested fix:** Update the header summary (e.g., extend the range to 52-63 or add an explicit line that 62-63 continue structured-reviewer-mode) so newcomers see one coherent case map.
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

### FINDING_7: [OUT_OF_SCOPE] **Commits:** `git log $(git merge-base HEAD main)..HEAD --oneline` shows a single commit: `31819bba Loosen NO_ISSUES_FOUND sentinel to first-non-empty-line match (#2455)`.
- **Reviewer**: dyn-sentinel-boundary-output.txt
- **Concern**: - **Commits:** `git log $(git merge-base HEAD main)..HEAD --oneline` shows a single commit: `31819bba Loosen NO_ISSUES_FOUND sentinel to first-non-empty-line match (#2455)`.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] **Makefile / `make lint`:** The diff does not touch the Makefile; [`Makefile`](Makefile) already defines `test-validate-research-output` and includes it in `test-harnesses-7`, so “wire into make lint” appears satisfied without this branch changing it.
- **Reviewer**: dyn-sentinel-boundary-output.txt
- **Concern**: - **Makefile / `make lint`:** The diff does not touch the Makefile; [`Makefile`](Makefile) already defines `test-validate-research-output` and includes it in `test-harnesses-7`, so “wire into make lint” appears satisfied without this branch changing it.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] **`trimmed_nonblank_content` vs comments:** The function at `scripts/validate-research-output.sh:224-226` prints every non-blank input line (each line-trimmed), not only “top and bottom” blank stripping; that wording predates this diff and is slightly misleading but unchanged by the branch.
- **Reviewer**: dyn-sentinel-boundary-output.txt
- **Concern**: - **`trimmed_nonblank_content` vs comments:** The function at `scripts/validate-research-output.sh:224-226` prints every non-blank input line (each line-trimmed), not only “top and bottom” blank stripping; that wording predates this diff and is slightly misleading but unchanged by the branch.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] The branch diff does not touch the Makefile; `test-validate-research-output` is already defined and referenced from `lint`-related phony targets in [Makefile](Makefile) (existing wiring, not introduced by this diff).
- **Reviewer**: dyn-test-coverage-output.txt
- **Concern**: - The branch diff does not touch the Makefile; `test-validate-research-output` is already defined and referenced from `lint`-related phony targets in [Makefile](Makefile) (existing wiring, not introduced by this diff).
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] code-quality: scripts/validate-research-output.sh:224-226
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] trimmed_nonblank_content naming/comments suggest top-bottom blank stripping but awk emits all non-empty lines from the file. Pre-existing mismatch with comment phrasing in section 0 not introduced by this diff. Optional doc-only cleanup if you unify terminology across the script.
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] code-quality: scripts/validate-research-output.sh:362-366
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Comment says blank lines removed top and bottom trimmed_nonblank_content omits every blank line globally not just ends When editing comments align with awk implementation
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] risk-integration: scripts/test-validate-research-output.sh:250-268
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No multi-line JSON sentinel regression case before this change. Low visibility into multi-line JSON acceptance until behavior changed. Add multi-line JSON case if contract should preserve old behavior.
- **Suggested revision**: Address the concern above.

### FINDING_14: code-quality: scripts/validate-research-output.sh:328,375
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated FIRST_LINE awk pipeline Two independent copies of the same extraction increase maintenance noise if the idiom changes Optionally extract one helper used by both structured-reviewer and validation branches
- **Suggested revision**: Address the concern above.

### FINDING_15: code-quality: scripts/validate-research-output.sh:362-367
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Validation-mode sentinel comment still describes entire-trimmed-content semantics for all sentinels contradicting FIRST_LINE behavior for NO_ISSUES_FOUND and JSON. Maintainers may misread contract and reintroduce wrong checks or mis-document collector behavior. Reword to separate CURSOR_EMPTY_RESPONSE (full TRIMMED) from no-findings sentinels (first non-empty line with trailing content allowed).
- **Suggested revision**: Address the concern above.

### FINDING_16: code-quality: scripts/validate-research-output.sh:362-367
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Stale validation-mode short-circuit banner comment Comment still claims entire-trimmed sentinel equality and no partial short-circuit; code now first-line matches no-findings sentinels with trailing content preserved Split the contract: CURSOR_EMPTY_RESPONSE remains full TRIMMED equality; no-findings JSON/NO_ISSUES_FOUND match first non-empty line of TRIMMED
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: scripts/validate-research-output.sh:326-337
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Structured-reviewer first-line no-findings short-circuit exits before JSONL/TSV parsing on INPUT; --write-structured can write an empty sidecar despite valid records after the sentinel line. File: first line NO_ISSUES_FOUND then valid JSONL record; old strict TRIMMED equality failed so JSONL ran and could fill sidecar; new code matches FIRST_LINE and exits 0 with empty structured output losing records. Only short-circuit when no structured records exist after the sentinel line (or parse INPUT and prefer records); add regression for --write-structured with sentinel plus JSONL.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: scripts/validate-research-output.sh:327-334;375-382
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] jq runs on FIRST_LINE only Pretty-printed multi-line JSON no-findings object can fail jq on first line while full TRIMMED remains valid JSON; previously jq saw full TRIMMED. Document single-line JSON sentinel requirement or parse a multi-line JSON object safely from TRIMMED if that format must remain valid.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: scripts/validate-research-output.sh:328-336;scripts/validate-research-output.sh:375-381
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] jq no-findings check uses FIRST_LINE only Pretty-printed multi-line JSON with first line just { fails jq on FIRST_LINE though full TRIMMED parses; unnecessary NOT_SUBSTANTIVE/retry Use TRIMMED for jq JSON probe or try TRIMMED then FIRST_LINE; or document and test single-line JSON only
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: scripts/validate-research-output.sh:333-334,379-380
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] jq no-findings check uses FIRST_LINE only Multi-line pretty-printed JSON sentinel may no longer short-circuit if the first line is not valid standalone JSON Document one-line JSON requirement or add an explicit regression test for multi-line JSON behavior
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

### FINDING_24: risk-integration: scripts/validate-research-output.sh:333-334 scripts/validate-research-output.sh:379-380
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] jq no-findings check runs on FIRST_LINE only, not full TRIMMED multi-line blob. Pretty-printed multi-line {"no_issues_found": true} that previously passed jq on full TRIMMED can now fail short-circuit and hit word-count/citation gates. Decide contract: if intentional, document + add test; if not, parse JSON from full TRIMMED or merge lines until jq succeeds with bounded input.
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: scripts/validate-research-output.sh:362-367
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Validation-mode comment still claims entire-trimmed-body sentinel match Maintainers or auditors may believe CURSOR_EMPTY_RESPONSE and no-findings gates share the same trimming rule and miss that trailing prose is accepted without citation/word-count checks after a first-line sentinel. Rewrite the block comment for first-non-empty-line no-findings sentinels vs full-body CURSOR_EMPTY_RESPONSE to match validate-research-output.md.
- **Suggested revision**: Address the concern above.

