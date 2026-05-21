### FINDING_1: Test 49 duplicates production jstr
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-jq-output-slice-output.txt
- **Concern**: Test 49 uses an inlined `jstr_test49` (or equivalent copy) instead of exercising `jstr()` from `audit-scan-run.sh`, so the suite can stay green while shipped scan NDJSON regresses if only the script changes. The duplicated helper can also diverge from the real `jq` primary path vs `sed` fallback. One source additionally notes the current identity-style cases may miss edge inputs (empty string, embedded quotes/backslashes, control characters) where the two implementation paths differ.
- **Suggested revision**: Share one implementation with the scan script (e.g. small sourced helper, narrow wrapper that loads the production function, or assertions driven through a code path that calls production `jstr()`), and broaden the assertion vector to cover those edge cases so regressions surface on the path the script actually uses.


### FINDING_2: Test 44b duplicates git/gh stub harness from Test 44
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Test 44b repeats large `git`/`gh` stub heredocs already defined in Test 44, overlapping coverage (one slot notes only a narrow slice like `[44b0]` is uniquely additive) and increasing maintenance cost: stub contract changes require parallel edits and risk skew between tests.
- **Suggested revision**: Fold uniquely additive coverage into Test 44 or extract shared stub construction (single helper or reused heredoc pair) and keep only 44b-specific assertions separate.


