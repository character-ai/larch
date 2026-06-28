### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lint-bare-grep-probe.sh
- **Concern**: Brace-group `{ grep ...; }` and `{ command grep ...; }` violations are not in the regression matrix. Scenario: The scanner inventory and violations list cover `{ rg ...; }` / `{ ripgrep ...; }` brace groups but not `{ grep ...; }` or `{ command grep ...; }`. The current bare-grep branch only matches line-start `grep`, so `{ grep -n PATTERN; }` is neither caught today nor proven by the planned harness. That shape is still a first-command no-path grep-family probe and can hang on background stdin.
- **Proposed resolution**: Add explicit brace-group detection for `{ grep ...; }` and `{ command grep ...; }`, plus violation cases `{ grep -n PATTERN; }` and `{ command grep -q PATTERN; }` and allowed `{ grep -n PATTERN file.txt; }` / `{ command grep -q PATTERN file.txt; }`.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/test-lint-bare-grep-probe.md:7-13
- **Concern**: Harness contract opening still blesses unconditional subshell and `command grep` safety. Scenario: The plan only adds bullets to `scripts/test-lint-bare-grep-probe.md`. Lines 7-13 still describe twenty cases and list `command grep` and `( grep ... )` subshell wrap as unconditionally safe exit-0 forms with no path or `< /dev/null` requirement. That contradicts the updated `scripts/lint-bare-grep-probe.md` Replace language and can mislead implementers into leaving no-path grouped/command shapes allowed.
- **Proposed resolution**: Replace the opening safe-form bullets (and the fixed twenty-case count) so they require an explicit path operand or unquoted `< /dev/null`, matching the primary lint contract.



### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-lint-bare-grep-probe.sh
- **Concern**: Missing positive coverage for grouped explicit-path `rg` / `ripgrep` probes.. Scenario: The plan adds grouped no-path violations and command-wrapped positives, but it does not prove the normalized bare grouped forms stay allowed. A parser bug that over-rejects safe shapes like `{ rg -n PATTERN python/; }` or `( rg -n PATTERN python/ )` could still ship.
- **Proposed resolution**: Add allowed regression cases for bare grouped explicit-path probes, including at least `{ rg -n PATTERN python/; }`, `{ ripgrep -q PATTERN skills/; }`, and `( rg -n PATTERN python/ )`, alongside the existing no-path violations and command-wrapped positives.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lint-bare-grep-probe.md:7-13
- **Concern**: Harness contract opening still unconditionally blesses no-path subshell and command-grep forms. Scenario: The plan only adds new contract bullets for scripts/test-lint-bare-grep-probe.md. Lines 7-13 still say twenty cases and list Safe forms (`command grep ...`, explicit `( grep ... )` subshell wrap, piped grep) → exit 0 with no path-or-/dev/null requirement. That contradicts the Replace language already planned for scripts/lint-bare-grep-probe.md and round-4 FINDING_2. An implementer can follow the harness contract, keep case 7 as a blanket allow for `( grep ... )`, and ship a scanner that still permits no-path subshell probes.
- **Proposed resolution**: In scripts/test-lint-bare-grep-probe.md, replace the opening safe-form bullets the same way as the primary contract: grep-family probes need an explicit path or unquoted `< /dev/null`; subshell/command wrap alone is not sufficient. Retitle the case-count line only after the expanded matrix lands.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: code-quality
- **Location**: scripts/lint-bare-grep-probe.sh:1-11
- **Concern**: UPDATED lint script leaves stale header safe-form guidance. Scenario: The awk extension is specified, but the plan does not update the bash header or the scan_file preamble comments (lines 1-11 and 83-89). They still advertise Safe forms: `command grep PATTERN file || X` and `( grep PATTERN file ) || X` without the new stdin rule. After the scanner rejects no-path `command rg`, `( rg PATTERN )`, and `{ rg ...; }`, the first file authors read still teaches the old contract.
- **Proposed resolution**: Extend the scripts/lint-bare-grep-probe.sh change list to refresh the header comment and in-file Detection comments: producer grep-family probes require an explicit path or `< /dev/null`; wrapper-safe forms still need a path operand for background stdin safety.



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: BASH_AUTHORING.md:13-16
- **Concern**: Intro sentence still claims two patterns are fully safe without the stdin operand rule. Scenario: The plan adds a stdin subsection and amends the wrapped-grep bullets, but line 13 still says Two patterns are safe and equivalent in semantics to bare `grep` before readers reach the new material. That repeats the pre-change implication that `command grep` or subshell wrap alone is enough, which is exactly the footgun this issue targets once no-path `command grep` / `( grep ... )` hang in background mode.
- **Proposed resolution**: Reword the summary at BASH_AUTHORING.md:13 to state that wrapper-safe forms also require an explicit path operand or `< /dev/null` for producer probes. Keep the bash 3.2 blockquote, but ensure bullets 15-16 and the new stdin subsection are cross-linked from that intro.



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-bare-grep-probe.sh
- **Concern**: Brace-group inventory omits `{ grep ...; }` and `{ command grep ...; }`. Scenario: The plan adds brace-group detection and regressions for `{ rg ...; }` / `{ ripgrep ...; }` but never lists `{ grep ...; }` or `{ command grep ...; }`. A line like `{ grep -q PATTERN; }` does not match today's bare-grep anchors and would stay allowed after the awk port, even though it is a no-path producer probe that blocks on background stdin (same class as accepted `( grep ... )` violations).
- **Proposed resolution**: Add `{ grep ...; }` and `{ command grep ...; }` to grouping normalization and the scanner inventory; add matching violation and path-qualified allowed cases in `scripts/test-lint-bare-grep-probe.sh` and harness-contract bullets.



### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-lint-bare-grep-probe.md:12-13
- **Concern**: Harness contract opening still blesses unconditional subshell/command-grep safety. Scenario: Round 4 FINDING_2 is only partially addressed: the plan adds new contract bullets but does not replace lines 12-13, which still say `command grep` and `( grep ... )` subshell wrap are safe exit-0 forms with no path or `< /dev/null` requirement. That contradicts the replaced rules in `scripts/lint-bare-grep-probe.md` and can steer the awk port or case updates to keep no-path `( grep PATTERN )` passing.
- **Proposed resolution**: Replace the opening safe-form summary (not only append bullets) so subshell/command-grep allowances require an explicit path operand or unquoted `< /dev/null`, matching the parenthesized violation cases already in the plan.



### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lint-bare-grep-probe.sh:145-175
- **Concern**: Missing positive coverage for new command-prefixed grouped forms. Scenario: The plan adds negative checks for `if command rg` / `ripgrep` and grouped `command rg` / `ripgrep` probes, but it never proves that path-bearing `if command rg ... path`, `if command ripgrep ... path`, or grouped `command ripgrep` forms still pass. A parser bug in the new command or grouping normalization could over-reject these new branches while the existing grep-only tests still pass.
- **Proposed resolution**: Add allowed regression cases for `if command rg -q PATTERN python/`, `if command ripgrep -q PATTERN skills/`, and the grouped `command ripgrep` path-bearing equivalents, then mirror those cases in the harness contract.



### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lint-bare-grep-probe.md:7-13
- **Concern**: Harness contract opening still describes unconditional safe forms and a fixed case count. Scenario: `### UPDATED: scripts/test-lint-bare-grep-probe.md` only says to add bullets. Lines 7-13 still claim twenty cases and bless any `command grep` or `( grep ... )` subshell wrap as exit-0 safe forms with no path or `< /dev/null` requirement. That contradicts the new stdin rule and the Replace treatment already specified for `scripts/lint-bare-grep-probe.md`, so an implementer can leave misleading contract prose that documents the pre-change behavior.
- **Proposed resolution**: Mirror the primary contract update: replace the opening case-count and safe-form bullets so they require an explicit path operand or unquoted `< /dev/null`, note that subshell/`command` wrap alone is not stdin-safe, and describe the expanded violation/allowed matrix instead of the stale twenty-case summary.



### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lint-bare-grep-probe.sh:129-157,178-195
- **Concern**: Regression coverage still misses two parser edge cases the plan introduces. Scenario: The plan tests a quoted `'< /dev/null'` false-short-circuit and a no-path env-assignment violation, but it never proves that a commented `# < /dev/null` substring stays rejected or that an env-prefixed probe with a real path still passes. A scanner bug could still let `rg -n PATTERN # < /dev/null` slip through or falsely reject `LC_ALL=C rg -n PATTERN python/`.
- **Proposed resolution**: Add one inline-comment negative case and one env-assignment-plus-path positive case in the harness.



