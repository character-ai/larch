### [Plan Review] FINDING_2

### FINDING_2: Harness contract opening still blesses unconditional subshell and `command grep` safety
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: `scripts/test-lint-bare-grep-probe.md` lines 7–13 still describe a fixed twenty-case matrix and list `command grep` and `( grep ... )` subshell wrap as unconditionally safe exit-0 forms with no path or `< /dev/null` requirement. The plan only appends new contract bullets and does not replace this opening summary. That contradicts the updated `scripts/lint-bare-grep-probe.md` Replace language and can mislead implementers into leaving no-path grouped or command-wrapped shapes allowed (e.g. case 7 still passing blanket `( grep ... )`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace the opening safe-form bullets (and the fixed twenty-case count) so they require an explicit path operand or unquoted `< /dev/null`, matching the primary lint contract.
  - From Cursor-Innovation: In scripts/test-lint-bare-grep-probe.md, replace the opening safe-form bullets the same way as the primary contract: grep-family probes need an explicit path or unquoted `< /dev/null`; subshell/command wrap alone is not sufficient. Retitle the case-count line only after the expanded matrix lands.
  - From Cursor-Pragmatic: Replace the opening safe-form summary (not only append bullets) so subshell/command-grep allowances require an explicit path operand or unquoted `< /dev/null`, matching the parenthesized violation cases already in the plan.
  - From Cursor-Requirements: Mirror the primary contract update: replace the opening case-count and safe-form bullets so they require an explicit path operand or unquoted `< /dev/null`, note that subshell/`command` wrap alone is not stdin-safe, and describe the expanded violation/allowed matrix instead of the stale twenty-case summary.


### [Plan Review] FINDING_4

### FINDING_4: Stale safe-form guidance in `scripts/lint-bare-grep-probe.sh` header and scan preamble
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The awk extension is specified, but the plan does not update the bash header (lines 1–11) or `scan_file` preamble comments (lines 83–89). They still advertise Safe forms such as `command grep PATTERN file || X` and `( grep PATTERN file ) || X` without the new stdin rule. After the scanner rejects no-path `command rg`, `( rg PATTERN )`, and `{ rg ...; }`, the first file authors read still teaches the old contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend the scripts/lint-bare-grep-probe.sh change list to refresh the header comment and in-file Detection comments: producer grep-family probes require an explicit path or `< /dev/null`; wrapper-safe forms still need a path operand for background stdin safety.


