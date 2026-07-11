---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_1

### FINDING_1: Define `-s` as a valueless boolean flag
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: `-s` is pinned as the `--file` short alias but its boolean grammar is not defined. Scenario: An operator invoking `/learn-from-bugs -s closed` (or `-s` with any trailing token) can enable filing mode while treating `closed` as verbal search text instead of `--state closed`, mining the wrong issue set before batch filing
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In Step 1, define `-s`/`--file` as boolean flags that take no value; keep `--state` long-form only; reject `-f` and any unknown flag; abort before Step 2 when argv is malformed (for example `-s closed` or `-s` combined with a second short option)


### [Plan Review] FINDING_8

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:--file-branch
- **Concern**: [SCOPE-REDUCTION] Pre-create validation conflates `/issue --dry-run` with parse validation. Scenario: The plan validates "parse output" via `/issue --dry-run`, but dry-run counts are dedup-adjusted (`ISSUES_CREATED`, `ISSUE_<i>_DUPLICATE`) and can diverge from batch item count even when parsing is correct, causing false stops or weak validation.
- **Proposed resolution**: Validate structure with `python3 ... issue parse-input --input-file "$RUN_DIR/batch-issues.md" --output-dir "$RUN_DIR/issue-parse-check"` and require `ITEMS_TOTAL` plus per-item titles to match; treat `/issue --dry-run` as optional dedup preview, not the parse gate.


---LARCH-REJECTED-END---
