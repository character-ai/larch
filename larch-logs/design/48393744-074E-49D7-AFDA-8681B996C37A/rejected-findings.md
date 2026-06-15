### [Plan Review] FINDING_1

### FINDING_1: `/issue --body-file` must include an explicit trailing title
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: blocking
- **Concern**: The plan invokes `/issue` with `--body-file` but does not require a trailing positional title. In `/issue` single mode, `--body-file` alone derives `ITEM_1_TITLE` from the file's first non-empty line. Because the composed bug body starts with `## Summary`, the filed issue title becomes a markdown heading (e.g. `## Summary`) instead of a bug-specific title.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In Step 5 specify Skill-tool args as: --sentinel-file "$BUG_TMPDIR/issue-completed.sentinel" --body-file "$BUG_TMPDIR/bug-issue-body.md" "<descriptive title derived from the report>" (title truncated to /issue 80-char rules). Do not rely on body-first-line title derivation
  - From Cursor-Innovation: Spell out Pattern B args: Invoke `/issue` via the Skill tool with `--body-file "$BUG_TMPDIR/bug-issue-body.md" --sentinel-file "$BUG_TMPDIR/issue-completed.sentinel"` plus a trailing positional title derived from the bug report (not from the body file)


### [Plan Review] FINDING_2

### FINDING_2: Stdout parsing must handle deduplicated-issue URL KVs
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Step 7 tells the orchestrator to report the created or deduplicated issue URL, but the plan does not parse the dedup stdout contract. When `/issue` deduplicates (`ISSUES_DEDUPLICATED>=1`), it emits `ISSUE_1_DUPLICATE=true` and `ISSUE_1_DUPLICATE_OF_URL=…`, not `ISSUE_1_URL`. Parsing only `ISSUE_1_URL` can finish with no URL and no issue number.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In Steps 5-7 bind the reported URL as ISSUE_1_URL when present, else ISSUE_1_DUPLICATE_OF_URL (mirror python/stall_recovery.py and skills/implement/references/oos-pipeline.md). Parse ISSUE_1_DUPLICATE_OF_NUMBER for the issue number


### [Plan Review] FINDING_3

### FINDING_3: `$BUG_TMPDIR` must be pinned under canonical `/tmp`
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: Step 2 only says to set up `$BUG_TMPDIR` without a path contract. If orchestrators copy session-setup or `~/.cache/larch` tmpdir patterns, Write targets and `--sentinel-file` paths may fall outside canonical `/tmp`. With a `deny-edit-write.sh` hook (Write allowed only under `/tmp`), body composition via Write fails and Step 4 cannot save `bug-issue-body.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In Step 2 mandate BUG_TMPDIR=$(mktemp -d "/tmp/claude-bug-XXXXXX") (or the /issue-style clone-tagged pattern) and require all scratch artifacts under that path
  - From Cursor-Pragmatic: In Step 2 mandate BUG_TMPDIR=$(mktemp -d "${TMPDIR:-/tmp}/claude-bug-XXXXXX") (or equivalent under canonical /tmp) and state that all Write targets and --sentinel-file paths must live under $BUG_TMPDIR
  - From Cursor-Requirements: In Step 2 mandate BUG_TMPDIR=$(mktemp -d "${TMPDIR:-/tmp}/claude-bug-XXXXXX") (or equivalent under canonical /tmp) and state that all Write targets and --sentinel-file paths must live under $BUG_TMPDIR


