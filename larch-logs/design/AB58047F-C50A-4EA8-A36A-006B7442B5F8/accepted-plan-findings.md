### FINDING_1: Missing `{ grep ...; }` and `{ command grep ...; }` brace-group coverage
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan adds brace-group detection and regressions for `{ rg ...; }` / `{ ripgrep ...; }` but omits `{ grep ...; }` and `{ command grep ...; }`. The bare-grep branch only matches line-start `grep`, so shapes like `{ grep -n PATTERN; }` and `{ command grep -q PATTERN; }` are neither caught today nor proven by the planned harness. These are still first-command no-path grep-family probes that can hang on background stdin.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add explicit brace-group detection for `{ grep ...; }` and `{ command grep ...; }`, plus violation cases `{ grep -n PATTERN; }` and `{ command grep -q PATTERN; }` and allowed `{ grep -n PATTERN file.txt; }` / `{ command grep -q PATTERN file.txt; }`.
  - From Cursor-Pragmatic: Add `{ grep ...; }` and `{ command grep ...; }` to grouping normalization and the scanner inventory; add matching violation and path-qualified allowed cases in `scripts/test-lint-bare-grep-probe.sh` and harness-contract bullets.


### FINDING_5: `BASH_AUTHORING.md` intro still claims wrapper forms are fully safe without stdin operand rule
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan adds a stdin subsection and amends wrapped-grep bullets, but line 13 still says "Two patterns are safe and equivalent in semantics to bare `grep`" before readers reach the new material. That repeats the pre-change implication that `command grep` or subshell wrap alone is sufficient, which is the footgun this issue targets once no-path `command grep` / `( grep ... )` hang in background mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Reword the summary at BASH_AUTHORING.md:13 to state that wrapper-safe forms also require an explicit path operand or `< /dev/null` for producer probes. Keep the bash 3.2 blockquote, but ensure bullets 15-16 and the new stdin subsection are cross-linked from that intro.


### FINDING_6: Missing positive coverage for command-prefixed grouped path-bearing forms
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan adds negative checks for `if command rg` / `ripgrep` and grouped `command rg` / `ripgrep` probes but never proves that path-bearing `if command rg ... path`, `if command ripgrep ... path`, or grouped `command ripgrep` forms still pass. A parser bug in the new command or grouping normalization could over-reject these branches while existing grep-only tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add allowed regression cases for `if command rg -q PATTERN python/`, `if command ripgrep -q PATTERN skills/`, and the grouped `command ripgrep` path-bearing equivalents, then mirror those cases in the harness contract.


### FINDING_7: Regression coverage misses inline-comment and env-prefixed path parser edge cases
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan tests a quoted `'< /dev/null'` false-short-circuit and a no-path env-assignment violation but never proves that a commented `# < /dev/null` substring stays rejected or that an env-prefixed probe with a real path still passes. A scanner bug could let `rg -n PATTERN # < /dev/null` slip through or falsely reject `LC_ALL=C rg -n PATTERN python/`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add one inline-comment negative case and one env-assignment-plus-path positive case in the harness.


