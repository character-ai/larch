### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: nit
- **Focus area**: correctness
- **Location**: plan.txt:49
- **Concern**: Edge cases claim a two-column inventory row has exactly two pipe boundary characters. Scenario: A 2-column Markdown table row needs three pipes (`| cell1 | cell2 |`); following two-pipe guidance can drop the closing delimiter and break the Makefile Targets table
- **Proposed resolution**: Reword to require the same three-pipe, single-line shape as sibling rows (leading, column delimiter, trailing)


### FINDING_10:
- **Reviewer(s)**: Codex-dyn-count-audit
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:19-26 skills/implement/scripts/test-step-7a.sh:376-399 skills/implement/scripts/step-7a.sh:376-385
- **Concern**: Proposed sanitizer prose says skip-upsert coverage, but the harness asserts all four sanitizer rejection cases still call tracking-issue-summary.sh and emit COMMENT_URL. Scenario: The rewritten docs would preserve a misleading behavior claim: sanitizer rejection skips diagram content but does not skip the summary upsert
- **Proposed resolution**: Rewrite that category as sanitizer-skipped diagram coverage with summary upsert for all four Mermaid REASON_TOKEN values, or similarly avoid saying skip-upsert


### FINDING_11:
- **Reviewer(s)**: Codex-dyn-count-audit
- **Severity**: nit
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:13 skills/implement/scripts/test-step-7a.sh:342-541
- **Concern**: Plan says 21 current new_case invocations, but the file has 19 direct new_case call sites; it reaches 21 runtime cases only because the sanitizer loop at lines 389-400 invokes one call site three times. Scenario: The count audit can be misread as a direct source invocation count, conflicting with the instruction to count new_case invocations directly
- **Proposed resolution**: Change the plan wording to 21 runtime cases from 19 new_case call sites, with the sanitizer loop contributing three runtime cases


### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: code-quality
- **Location**: docs/linting.md:263, skills/implement/scripts/test-step-7a.sh:376-399
- **Concern**: Proposed row still contains drift-prone cardinal prose and preserves inaccurate sanitizer wording. Scenario: The replacement removes "Covers 18 cases" but keeps "all four Mermaid REASON_TOKEN values"; if sanitizer tokens change, the same doc-drift class returns. The phrase "sanitizer skip-upsert coverage" also conflicts with the harness, which asserts sanitizer rejection cases still call tracking-issue-summary.sh and emit COMMENT_URL.
- **Proposed resolution**: Replace that category with non-cardinal accurate wording such as "Mermaid sanitizer rejection-token variants" or "sanitizer rejection-token coverage"; avoid "all four" and "skip-upsert".


### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:48-49
- **Concern**: Edge-case guidance says a valid inventory row has exactly two pipe boundary characters. Scenario: Two-column markdown rows require three pipes (`| target | description |`). An implementer verifying only two pipes may accept a row that breaks the linting.md table and fails markdownlint or mis-parses columns
- **Proposed resolution**: Revise the edge case to require one physical line with three pipe delimiters (two columns), matching sibling rows in docs/linting.md:258-263


### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: code-quality
- **Location**: docs/linting.md:263
- **Concern**: Proposed replacement still contains hardcoded cardinality prose: "all four Mermaid `REASON_TOKEN` values" and "both rebase-outcome and diagram-skip paths". Scenario: The PR is meant to remove drift-prone numeric coverage claims, but the new row would still bake derived counts into docs; adding another sanitizer token or quiet contract case silently makes the row stale again
- **Proposed resolution**: Rewrite those clauses without cardinality, e.g. "sanitizer skip-upsert coverage across Mermaid `REASON_TOKEN` variants" and "quiet contract replay for rebase-outcome and diagram-skip paths"


### FINDING_5:
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: docs/linting.md:263
- **Concern**: Proposed row retains a spelled-out hardcoded count: "all four Mermaid `REASON_TOKEN` values". Scenario: If a fifth sanitizer `REASON_TOKEN` is added, the row still drifts while the current literal-count lint may not catch word-number phrasing
- **Proposed resolution**: Replace with qualitative wording such as "the Mermaid sanitizer `REASON_TOKEN` vocabulary" or "sanitizer rejection-token variants"; also remove "the four sanitizer tokens" from plan guidance


### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: AGENTS.md:18
- **Concern**: Testing strategy permits a markdownlint-only fallback despite the repo contract requiring `bash scripts/relevant-checks.sh` or `make lint` after any change. Scenario: An implementer may run only markdownlint and miss repo-wide hooks that are relevant for markdown changes, including always-run policy hooks and secret scanning
- **Proposed resolution**: Require `bash scripts/relevant-checks.sh` or `make lint`; mention markdownlint only as an optional diagnostic after failure


### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/linting.md:263
- **Concern**: Proposed row keeps phrase sanitizer skip-upsert coverage. Scenario: Contradicts skills/implement/scripts/step-7a.md:50 and step-7a.sh:378-394 which always call tracking-issue-summary.sh upsert-summary when ISSUE_NUMBER is set; harness cases diagram-rejected* and diagram-failure-sanitizer assert still posts comment
- **Proposed resolution**: While rewriting the row replace skip-upsert with accurate prose e.g. sanitizer-rejection placeholder summary coverage for four Mermaid REASON_TOKEN values


### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: docs/linting.md:263 planned via plan.txt:19
- **Concern**: Proposed row still hardcodes a derived count with "all four Mermaid REASON_TOKEN values". Scenario: The issue resolution explicitly aims to address drift-prone hardcoded counts; if sanitizer tokens change, this prose can drift again even after dropping "Covers 18 cases"
- **Proposed resolution**: Revise the planned row to avoid the count, e.g. "sanitizer skip-upsert coverage across Mermaid REASON_TOKEN rejection variants"


### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: AGENTS.md:18; plan.txt:55-56
- **Concern**: Testing strategy allows markdownlint as a minimum gate. Scenario: Repository instructions require `bash scripts/relevant-checks.sh` or `make lint` after any change; a markdownlint-only run would miss the required validation contract
- **Proposed resolution**: Make `bash scripts/relevant-checks.sh` or `make lint` mandatory, with markdownlint only as an optional faster diagnostic after failure


