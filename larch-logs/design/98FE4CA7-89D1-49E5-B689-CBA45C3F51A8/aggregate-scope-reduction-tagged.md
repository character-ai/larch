### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/learn-from-bugs/SKILL.md:--file-branch
- **Concern**: [SCOPE-REDUCTION] Pre-create validation conflates `/issue --dry-run` with parse validation. Scenario: The plan validates "parse output" via `/issue --dry-run`, but dry-run counts are dedup-adjusted (`ISSUES_CREATED`, `ISSUE_<i>_DUPLICATE`) and can diverge from batch item count even when parsing is correct, causing false stops or weak validation.
- **Proposed resolution**: Validate structure with `python3 ... issue parse-input --input-file "$RUN_DIR/batch-issues.md" --output-dir "$RUN_DIR/issue-parse-check"` and require `ITEMS_TOTAL` plus per-item titles to match; treat `/issue --dry-run` as optional dedup preview, not the parse gate.

### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: plan.txt:7
- **Concern**: [SCOPE-REDUCTION] Explicitly rejecting `-f` and every unknown flag breaks the existing contract that all unrecognized arguments are verbal search text. Scenario: An operator can currently mine bugs involving a CLI flag with input such as `--admin permission failures` or `-f handling`; the proposed parser would abort instead of translating that text into a GitHub search
- **Proposed resolution**: Parse `--file` and `-s` as new Boolean flags, validate values only for recognized value-taking flags, and preserve all other tokens as verbal description text; omit `-f` from the documented and recognized aliases without explicitly rejecting it
