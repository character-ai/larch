### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/bug/SKILL.md:5-7
- **Concern**: Plan does not require explicit trailing title argv when calling /issue with --body-file. Scenario: The composed body starts with ## Summary; /issue single mode without a trailing positional derives the title from the first body line, so filed issues get titles like "## Summary" instead of a bug-specific title
- **Proposed resolution**: In Step 5 specify Skill-tool args as: --sentinel-file "$BUG_TMPDIR/issue-completed.sentinel" --body-file "$BUG_TMPDIR/bug-issue-body.md" "<descriptive title derived from the report>" (title truncated to /issue 80-char rules). Do not rely on body-first-line title derivation

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/bug/SKILL.md:6-7
- **Concern**: Stdout parsing omits the deduplicated-issue URL KV contract. Scenario: On ISSUES_DEDUPLICATED>=1 /issue emits ISSUE_1_DUPLICATE=true and ISSUE_1_DUPLICATE_OF_URL=…, not ISSUE_1_URL; Step 7 "report the created or deduplicated issue URL" can finish with no URL
- **Proposed resolution**: In Steps 5-7 bind the reported URL as ISSUE_1_URL when present, else ISSUE_1_DUPLICATE_OF_URL (mirror python/stall_recovery.py and skills/implement/references/oos-pipeline.md). Parse ISSUE_1_DUPLICATE_OF_NUMBER for the issue number

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/bug/SKILL.md:2-3
- **Concern**: $BUG_TMPDIR setup is unspecified beyond "setup". Scenario: The Write hook only permits canonical /tmp paths; a relative or repo-local tmpdir makes Write fail or pushes orchestrators toward repo writes
- **Proposed resolution**: In Step 2 mandate BUG_TMPDIR=$(mktemp -d "/tmp/claude-bug-XXXXXX") (or the /issue-style clone-tagged pattern) and require all scratch artifacts under that path

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/bug/SKILL.md:5
- **Concern**: /issue --body-file invocation omits required trailing positional title. Scenario: The composed body template starts with ## Summary; /issue with --body-file alone derives ITEM_1_TITLE from the file's first non-empty line, yielding a markdown heading or wrong title instead of a bug summary
- **Proposed resolution**: Spell out Pattern B args: Invoke `/issue` via the Skill tool with `--body-file "$BUG_TMPDIR/bug-issue-body.md" --sentinel-file "$BUG_TMPDIR/issue-completed.sentinel"` plus a trailing positional title derived from the bug report (not from the body file)

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/bug/SKILL.md:2-3
- **Concern**: Plan does not pin $BUG_TMPDIR under canonical /tmp. Scenario: The skill registers deny-edit-write.sh (Write allowed only under /tmp) and composes bug-issue-body.md via Write, but Step 2 only says setup $BUG_TMPDIR without a path contract; copying session-setup or ~/.cache/larch tmpdir patterns leaves Write denied and Step 4 cannot save the body
- **Proposed resolution**: In Step 2 mandate BUG_TMPDIR=$(mktemp -d "${TMPDIR:-/tmp}/claude-bug-XXXXXX") (or equivalent under canonical /tmp) and state that all Write targets and --sentinel-file paths must live under $BUG_TMPDIR
