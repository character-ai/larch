### FINDING_1: Anchor the new grep-probe lint rule
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements, Cursor-dyn-Bash32 Portability
- **Severity**: major
- **Concern**: The planned `lint-bash32` rule needs line-start anchoring and token-sensitive matching. A substring-style rule would false-flag sanctioned `if ( command grep ... )` / piped probes and literal fixture strings in `scripts/test-lint-bare-grep-probe.sh`, which would make repo-wide `make lint-bash32` fail after the rule lands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: "Anchor the awk rule to ^[[:space:]]*(if|elif)[[:space:]]+!?[[:space:]]*command[[:space:]]+(grep|egrep|fgrep|rg). Add an edge case and lint-bash32.md contract line that piped if ... | command grep stays permitted. Add a passing piped-probe fixture in scripts/test-lint-bash32.sh."
  - From Cursor-Innovation: "Pin the awk predicate to line-start `^[[:space:]]*(if|elif)[[:space:]]+(![[:space:]]+)?command[[:space:]]+(grep|egrep|fgrep|rg)([[:space:];|&)]|$)`. Reject matches when the next token after `if`/`elif` is `(`. Add test-lint-bash32.sh passing cases for subshell and piped forms so over-broad regex cannot regress"
  - From Cursor-Requirements: "Add ### UPDATED: scripts/test-lint-bare-grep-probe.sh with trailing # lint-bash32: ok <reason> on each embedded fixture line that contains if/elif command grep-family text, and include scripts/test-lint-bare-grep-probe.sh in the focused lint-bash32 verification command or require make lint-bash32 before ship"
  - From Cursor-dyn-Bash32 Portability: "Document and implement the rule as ^[[:space:]]*(if|elif)[[:space:]]+!?[[:space:]]*command[[:space:]]+(grep|egrep|fgrep|rg)([[:space:]]|;|\)|$)/ with an early reject when the token after if/elif optional ! is ( so if ( command grep ... ) and if ! ( command grep ... ) stay allowed; only add # lint-bash32: ok suppressions if a reviewed exception still matches after anchoring"


### FINDING_4: Add the live defect site to lint-bash32 scan surfaces
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: `skills/design/scripts/design-step3b-tail.sh` is still outside the repo-wide `lint-bash32` / pre-commit scan surface, so the live jq-less bash 3.2 abort can remain untested in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: "Add `skills/design/scripts/design-step3b-tail.sh` to `scripts/residual-bash-paths.txt` and the `lint-bash32` hook `files:` stanza in `.pre-commit-config.yaml` beside the existing `design-step5c.sh` rows. Extend the testing strategy with `make lint-bash32` (not only positional `bash scripts/lint-bash32.sh skills/design/scripts/design-step3b-tail.sh`)."


