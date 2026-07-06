## Proposed Design Outline

### Goals
- Fix the live bash 3.2 defect in `design-step3b-tail.sh:154` by using the sanctioned `( command grep ... )` subshell form.
- Add a lint rule to `lint-bash32.sh` that flags `if`/`elif` `command grep` (and grep-family variants) in committed shell scripts.
- Add regression fixtures to `test-lint-bash32.sh` covering the new rule.

### Non-goals
- Do not change the jq path; only the fallback `elif` branch needs fixing.
- Do not add a new standalone lint script; extend the existing `lint-bash32.sh`.
- Do not fix the `test-lint-awk-multibyte-regex.sh` sites as bugs (they run under `set +e`); fix unconditionally for consistency.

### Approach sketch
- Rewrite `design-step3b-tail.sh:154` from `elif command grep -Eq '...'` to `elif ( command grep -Eq '...' ... ) 2>/dev/null;`.
- Add an awk pattern to `lint-bash32.sh` that flags `if command grep`, `elif command grep`, `if ! command grep`, and grep-family equivalents; suppress with `# lint-bash32: ok`.
- Add positive and negative test cases to `test-lint-bash32.sh`.
- Optionally update `BASH_AUTHORING.md` with a pointer to the new lint rule.

### Surfaces in scope
- `skills/design/scripts/design-step3b-tail.sh` (line ~154)
- `scripts/lint-bash32.sh` (new awk rule in `scan_file`)
- `scripts/test-lint-bash32.sh` (new regression cases)
- `scripts/test-lint-awk-multibyte-regex.sh` (unconditional cleanup)
- `BASH_AUTHORING.md` (optional lint pointer)

### Open questions
- None.
