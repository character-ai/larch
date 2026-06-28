# Review Round 1

- Mode: `diff`
- 5 accepted, 4 rejected (0 neutral)

## Accepted Findings

### FINDING_1: stdin sentinels `-` and `/dev/stdin` accepted as path operands
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-testing
- **Severity**: important
- **Concern**: `has_explicit_path()` treats stdin sentinels (`-`, `/dev/stdin`) as filesystem path operands. Forms like `command grep -q PATTERN -` and `rg -n PATTERN -` pass lint but still read stdin and can hang in background Bash when stdin is an open pipe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Reject stdin-alias operands after pattern parsing; add regression tests for `-` and `/dev/stdin`
  - From codex-specialist-testing: Treat - as stdin, not a path, and add regression cases in scripts/test-lint-bare-grep-probe.sh for stdin-alias operands.


### FINDING_3: `grep -l` misclassified as value-taking flag
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-generalist, dyn-dyn-contract-sync
- **Severity**: important
- **Concern**: `option_takes_value()` treats bare `grep -l` like `--label` and consumes the next token as an option argument. A safe probe like `command grep -l PATTERN file.txt` is falsely rejected: `PATTERN` is consumed as `-l`'s value and `file.txt` is misread as the pattern, so `has_explicit_path()` returns false.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generalist: Remove `-l` from the value-taking grep options, keep value handling for `--label`, and add a regression for `command grep -l PATTERN file.txt`.
  - From dyn-dyn-contract-sync: Stop treating bare `-l` as value-taking; keep `--label` / `--label=...` as the label forms. Add harness cases for `command grep -l PATTERN file` (allowed) and `command grep -l PATTERN` (rejected).


### FINDING_5: brace-wrapped bare `grep` allowed despite wrapper-exit trap
- **Reviewer(s)**: codex-generalist
- **Severity**: important
- **Concern**: Brace-wrapped bare `grep` with an explicit path is allowed, but `BASH_AUTHORING.md:11` says `{ grep ...; } || X` still triggers the Claude Code wrapper-exit trap. A fence line like `{ grep -q ABSENT file.txt; } || echo missing` can pass lint, then abort the Bash block before the fallback runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generalist: Treat `{ grep ...; }` as a wrapper violation unless it uses `command grep`, and flip `scripts/test-lint-bare-grep-probe.sh:324` to a violation case.


### FINDING_6: quoted metacharacter patterns falsely act as argv terminators
- **Reviewer(s)**: codex-generalist
- **Severity**: important
- **Concern**: Quoted shell metacharacter patterns are treated as argv terminators after tokenization strips quotes. A safe probe like `rg ';' python/` or `rg '<' python/` can be rejected before the parser reaches the explicit path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generalist: Make terminator checks token-index aware and ignore quoted operator tokens, then add regression cases for quoted `;`, `<`, and `|` patterns with paths.


### FINDING_8: unlisted value-taking flags allow false path qualification
- **Reviewer(s)**: dyn-dyn-awk-parser
- **Severity**: important
- **Concern**: In `has_explicit_path()`, options absent from `option_takes_value()` are skipped without consuming a following argv token. Unlisted value-taking flags make the next token look like the pattern and the token after that look like a path. Example: `rg -j 4 PATTERN` is treated as pattern `4` plus path `PATTERN` and is allowed without a real path operand. The same mis-parse affects other unlisted value flags (for example `--threads`, `--max-columns`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-awk-parser: For unknown `-` tokens, conservatively consume the next non-terminator token as a potential option argument when it does not itself look like an option, or expand the value-taking set for common `rg`/`ripgrep` flags used in probes. Add tests for `rg -j 4 PATTERN` (reject) and `rg -j 4 PATTERN python/` (allow).


