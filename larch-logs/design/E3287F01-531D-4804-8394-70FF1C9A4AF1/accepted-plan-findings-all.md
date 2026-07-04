### FINDING_1: Keep `git.log_path_commits()` fail-closed on malformed NUL rows
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Requirements, Cursor-dyn-History Parser Correctness, Codex-dyn-History Parser Correctness
- **Severity**: important
- **Concern**: The planned `partition("\x00")` migration can let malformed `git log` output slip through unless the parser still rejects both delimiter-free rows and rows with an empty SHA. The coverage also needs to pin those malformed shapes so `ShipError` remains the fail-closed outcome.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In log_path_commits, either keep split("\x00", 1) plus len(parts)!=2 (and not parts[0]), or after partition require sep (or "\x00" in line) before building PathCommit; state that guard explicitly in the git.py plan bullet
  - From Codex-Requirements: Add a second malformed-output test that feeds a row with an empty SHA and asserts `ShipError`.
  - From Cursor-dyn-History Parser Correctness: Prefer one mandated approach in the plan.
  - From Codex-dyn-History Parser Correctness: Add a dedicated empty-SHA StubRunner case and assert `ShipError` with the existing malformed-line message.


### FINDING_6:
- **Reviewer(s)**: Cursor-dyn-History Parser Correctness
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/git/git.py:224-227
- **Concern**: [SCOPE-REDUCTION] Pin NUL split to split("\x00", 1) or require an explicit sep check if using partition. Scenario: line.partition("\x00") on a delimiter-free row yields ("missing-delimiter", "", ""); a naive swap keeps a non-empty sha and accepts an empty subject, so test_log_path_commits_raises_on_malformed_output regresses and fail-closed parsing breaks
- **Proposed resolution**: In log_path_commits(), replace the plan's "partition or split" fork with one rule: sha, subject = line.split("\x00", 1) and keep len(parts) == 2 and not parts[0]; if partition is kept, reject when sep == ""


### FINDING_1: Missing exit-code assertion for unresolved `--since-tag`
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The unresolved `--since-tag` path is only checking stderr in the planned test, so a regression that prints the expected missing-tag message but returns a non-2 exit code could still pass CI. This leaves the required exit-2 contract unverified for the `--since-tag` failure case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the planned unresolved `--since-tag` test, add `assert rc == 2` alongside the stderr substring check, mirroring the invalid `--root` test.
  - From Codex-Innovation: Add `assert rc == 2` to the unresolved `--since-tag` test, matching the invalid-`--root` test.
  - From Cursor-Pragmatic: Add assert rc == 2 (or TOOL_FAILURE_EXIT) to the missing-tag ledger_main test, matching the invalid --root case.
  - From Codex-Pragmatic: Add `assert rc == 2` to the unresolved `--since-tag` test, matching the invalid `--root` test.
  - From Codex-Requirements: Add `Assert rc 2` to the unresolved `--since-tag` test steps

