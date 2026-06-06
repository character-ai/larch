### FINDING_1:
- **Reviewer(s)**: Cursor-Edge, Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh
- **Concern**: Step-4 wiring grep only requires the issue-input-file token. Scenario: The plan pins step 4 with a grep for issue-input-file plus a vague feeds-output-to --input-file check. Step 4 could still call issue-input-file yet pass stall-recovery-bug-body.md to /larch:issue --input-file. The grep passes and ITEMS_TOTAL=0 silent no-file filing returns
- **Proposed resolution**: Require step 4 to reference stall-recovery-issue-input.md on the /larch:issue --input-file line, or assert stall-recovery-bug-body.md is not that target (e.g. grep -Fq stall-recovery-issue-input.md on the --input-file path)

### FINDING_2:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:19; skills/issue/SKILL.md:378-384
- **Concern**: Step 4 still names ISSUE_NUMBER/ISSUE_URL as if /issue batch mode emits those keys directly. Scenario: After the proposed switch to /larch:issue --input-file, /issue batch mode emits ISSUE_1_NUMBER and ISSUE_1_URL for a created single item. A literal parse for ISSUE_NUMBER/ISSUE_URL leaves stall-recovery-issue.env empty, so later terminal-failure comments cannot target the recovery-created issue.
- **Proposed resolution**: In the Step 4 rewrite, state that stdout from /issue batch mode must be normalized: persist ISSUE_1_NUMBER/ISSUE_1_URL as ISSUE_NUMBER/ISSUE_URL, and use ISSUE_1_DUPLICATE_OF_NUMBER/URL when the item deduplicates.

### FINDING_3:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:19; skills/issue/SKILL.md:378-382
- **Concern**: Step 4 still plans to persist top-level ISSUE_URL and ISSUE_NUMBER from a batch /larch:issue --input-file call, but batch mode emits ISSUE_1_URL and ISSUE_1_NUMBER.. Scenario: A first-detection stall issue can be created successfully, but stall-recovery-issue.env stays empty or missing normalized keys; a later terminal comment cannot target the recovery-created issue and falls back to manual filing.
- **Proposed resolution**: Make Step 4 explicitly normalize ISSUE_1_NUMBER and ISSUE_1_URL from /larch:issue stdout into ISSUE_NUMBER and ISSUE_URL in stall-recovery-issue.env when the single-item batch create succeeds.

### FINDING_4:
- **Reviewer(s)**: Codex-dyn-script-inventory
- **Severity**: important
- **Focus area**: security
- **Location**: skills/implement/scripts/stall-recovery-report.sh:792-798,991-993
- **Concern**: safe_step_value is not actually parser-safe for step-family values because globs like 8[[:alnum:]-]* allow arbitrary trailing bytes after the first safe character, and issue-input-file copies the result into the public ### title. Scenario: A malformed classification env with STALL_STEP=8a unsafe text produces a public issue title outside the claimed sanitized step token, so the plan's no-script-change assumption is false
- **Proposed resolution**: Tighten safe_step_value with a full-string regex or closed enum for the intended step tokens before composing the title, and add one regression fixture for an 8a-prefixed unsafe value

### FINDING_5:
- **Reviewer(s)**: Codex-dyn-harness-completeness
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/implement/scripts/test-stall-recovery-report.md:7-29
- **Concern**: The cited sibling rule is not documented in this harness contract; the file lists invariants and case coverage but no rule requiring .md updates alongside .sh changes.. Scenario: Implementer may add broad policy prose or justify extra doc churn from a nonexistent contract, which works against the SIMPLE minimum-change lane.
- **Proposed resolution**: Revise the plan to drop the sibling-rule rationale; if the new parser case is added, update only the relevant case-map/coverage line.
