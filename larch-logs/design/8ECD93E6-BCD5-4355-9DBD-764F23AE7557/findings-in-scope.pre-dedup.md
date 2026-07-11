### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-file-failure-report-cross-repo.sh:248,298
- **Concern**: Case-variant suppressions omit assert_eq lines that still contain [Bug]. Scenario: The plan and FINDING_2 fix focus on the two printf payload lines, but lines 248 and 298 also embed literal [Bug] in assert_eq expected strings that document legacy-heading rejection. A line scanner will flag those tokens too, so repo-wide prefix-case-variant can still exit 1 after only suppressing the printf lines.
- **Proposed resolution**: Extend the scripts/test-file-failure-report-cross-repo.sh update to add a trailing reason-bearing # lint-prefix-case-variant: ok pragma on all four [Bug]-bearing manifest lines (246, 248, 295, 298), or explicitly list 248 and 298 in the file section and keep the acceptance check that every such line is covered.



### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-file-failure-report-cross-repo.sh:248,298
- **Concern**: Residual-Bash suppression plan omits assert_eq lines that still contain `[Bug]`. Scenario: The plan adds trailing suppressions only on the two `printf` legacy-heading fixture lines (246, 295). The same manifest-listed script also has `[Bug]` on the `assert_eq` lines 248 and 298 in assertion message strings. The new hard-ban lint scans every line in residual Bash files, so repo-wide `python3 python/cli.py lint prefix-case-variant` will still report those two lines and fail acceptance criterion 2.
- **Proposed resolution**: Extend the `scripts/test-file-failure-report-cross-repo.sh` update and the testing-strategy checklist to cover all four `[Bug]`-bearing lines (246, 248, 295, 298), each with its own trailing `# lint-prefix-case-variant: ok <reason>` (or rewrite the assert messages to avoid bracketed case variants). ## Findings ### 1. [correctness] Residual-Bash suppression plan omits assert_eq lines that still contain `[Bug]` **Location:** `scripts/test-file-failure-report-cross-repo.sh:248,298` **Concern:** Round 1 correctly accepted fixture suppressions for legacy `[Bug]` headings, and the plan now updates the residual-Bash harness. It only calls out the two `printf` payload lines that embed `### [Bug]` headings (246 and 295). Lines 248 and 298 are also in the manifest-listed script and contain bracketed `[Bug]` inside `assert_eq` message strings: assert_eq fallback-print-required "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "tier-b: legacy [Bug] raw heading rejected" The L2 lint scans residual Bash files line by line with no heading-only carve-out. Those assertion lines are case variants of the canonical `[BUG]` token and will be reported. **Scenario:** Implementer adds suppressions only to the `printf` lines per the plan. `python3 python/cli.py lint prefix-case-variant` still exits 1 on lines 248 and 298. Acceptance criterion 2 (repo-wide zero findings) fails. **Suggested revision:** Treat all four `[Bug]` occurrences in this script as in-scope for line-local suppressions, or rewrite the assert messages to describe legacy casing without a bracketed token (for example, "legacy mixed-case bug-prefix raw heading rejected"). Update the testing-strategy bullets to validate all four lines, not only the `printf` fixtures.



### FINDING_3:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-file-failure-report-cross-repo.sh:248,298
- **Concern**: Case-variant suppressions omit assert message lines that still contain `[Bug]`. Scenario: The plan only adds trailing `# lint-prefix-case-variant: ok` suppressions to the two `printf` fixture lines at 246 and 295. Lines 248 and 298 also contain literal `[Bug]` tokens inside `assert_eq` expected strings. A line-oriented scan will flag them, so `python3 python/cli.py lint prefix-case-variant` cannot meet the acceptance zero-findings gate after only those two suppressions.
- **Proposed resolution**: Add reason-bearing trailing suppressions to lines 248 and 298 as well, or reword those assertions to avoid bracketed tokens; update the testing-strategy checklist to cover all four `[Bug]` occurrences in this script.



