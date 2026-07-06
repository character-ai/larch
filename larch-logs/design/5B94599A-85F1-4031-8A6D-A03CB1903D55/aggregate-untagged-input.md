### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/lint-bash32.sh:scan_file awk rule
- **Concern**: The worked example regex matches only `if`, not `elif`, despite the plan requiring both. Scenario: The live defect at `skills/design/scripts/design-step3b-tail.sh:154` is `elif command grep`. An awk rule using only `/( if |[\t;]if )/` never matches `elif command grep`, so the new lint leaves the reported bug class unenforced and the planned failing `elif command grep` harness case would not trip the linter
- **Proposed resolution**: Anchor at line start with `^[[:space:]]*(if|elif)[[:space:]]+(![[:space:]]+)?command[[:space:]]+(grep|egrep|fgrep|rg|ripgrep)` (POSIX-awk boundaries), keep the `!/\([[:space:]]*command/` guard, and assert the rule text against an `elif command grep` fixture

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: scripts/lint-bash32.sh:scan_file awk rule
- **Concern**: FINDING_1 anchoring is still incomplete: the worked `( if |[\t;]if )` shape matches ` if command grep` inside quoted harness labels, not only real conditionals. Scenario: `scripts/test-lint-bare-grep-probe.sh` is in `scripts/residual-bash-paths.txt` and contains lines like `assert_fence_line_violation "no-path if command grep" 'if command grep ...'`. Substring matching on those labels would make repo-wide `make lint-bash32` fail after the rule lands, blocking the enforcement change
- **Proposed resolution**: Require the conditional keyword at line start (after whitespace): `^[[:space:]]*(if|elif)...` rather than any inline ` if ` token; keep piped and `( command ... )` negatives; add a regression fixture modeled on the bare-grep-probe assert label line to prove it stays clean

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/lint-bash32.sh:102-122
- **Concern**: Prior FINDING_1 is only partially incorporated: the plan still offers a substring-style awk shape and does not pin a code-start or shell-separator boundary, so labels or quoted fixture text can match the new rule.. Scenario: `make lint-bash32` can fail on existing manifest-covered fixture lines such as `scripts/test-lint-bare-grep-probe.sh:230`, where `"no-path if command grep"` or a quoted fixture contains `if command grep` but is not executable shell syntax.
- **Proposed resolution**: Tighten the plan to require matching only real condition starts, for example line start or shell separators before `if`/`elif`, optional `!`, then `command <grep-family>`, and add an existing-fixture negative case or suppress only real committed fixture lines that remain unavoidable.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/lint-bash32.sh:scan_file awk block
- **Concern**: Plan awk example omits elif while the live defect is elif command grep. Scenario: The workable regex `/( if |[\t;]if )(![ \t]+)?command.../` does not match `elif command grep` because `elif` is not preceded by space/tab/semicolon before a standalone `if` token. An implementer copying the example ships a lint that passes `elif command grep` fixtures in tests but still misses `skills/design/scripts/design-step3b-tail.sh:154` if tests are written before the rule is finalized, or misses future elif sites. Replace the example with a line-anchored pattern that includes elif, e.g. `^[[:space:]]*(if|elif)[[:space:]]+(![[:space:]]+)?command[[:space:]]+(grep|egrep|fgrep|rg|ripgrep)` plus `&& !/\([[:space:]]*command/`, and require a failing fixture that quotes the exact tail.sh elif line.
- **Proposed resolution**:

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/lint-bash32.sh:scan_file awk block
- **Concern**: [ALREADY_ADDRESSED] FINDING_1 anchoring is still incomplete in the worked example. Scenario: The plan requires anchored matching but the sample `/( if |[\t;]if ).../` still matches the substring ` if command grep` inside `scripts/test-lint-bare-grep-probe.sh:230` assert label text (`"no-path if command grep"`). After the rule lands, repo-wide `make lint-bash32` fails on harness prose, not unsafe shell. Require `^[[:space:]]*(if|elif)` (or equivalent statement-start anchor) so only real conditional probes match; keep the subshell and pipeline negatives.
- **Proposed resolution**:

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: scripts/residual-bash-paths.txt:86
- **Concern**: Insert site for design-step3b-tail.sh should be before design-step5.sh. Scenario: The manifest has `skills/design/scripts/design-step5*.sh` but no `design-step3*` rows. Alphabetical insert is immediately before `skills/design/scripts/design-step5.sh`, not after `design-step5c.sh` or mixed into `test-design-step3*` harness rows. Wrong placement is easy to misread as out-of-scope and can delay pre-commit coverage. Pin the exact neighbor row in the plan.
- **Proposed resolution**:

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: .pre-commit-config.yaml:408-412
- **Concern**: FINDING_4 fix is incomplete: the plan adds `skills/design/scripts/design-step3b-tail.sh` to `scripts/residual-bash-paths.txt`, but the `lint-bash32` pre-commit hook still has a hardcoded `files` allowlist that omits the live tail script.. Scenario: `make lint-bash32` would scan the new manifest row, but CI `lint-local` and relevant-checks invoke `pre-commit`, which selects files from `.pre-commit-config.yaml` before `scripts/lint-bash32.sh` runs. The new rule therefore still would not cover the changed live defect site on the pre-commit path the plan claims to fix.
- **Proposed resolution**: Add `skills/design/scripts/design-step3b-tail.sh` to the `lint-bash32` hook `files` regex, near the other `skills/design/scripts/design-step*.sh` entries.

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/lint-bash32.sh
- **Concern**: The planned awk example matches only `if`, not `elif`, despite requiring both. Scenario: The live jq-less defect is `elif command grep` at `design-step3b-tail.sh:154`. A rule using `/( if |[\t;]if )...` would not flag `elif command grep` or `elif ! command grep`, so the primary bug class can recur after the one-site rewrite
- **Proposed resolution**: Extend the matcher to `(^|[;{&|])[ \t]*(if|elif)([ \t]+![ \t]+|[ \t]+)command[ \t]+(grep|egrep|fgrep|rg|ripgrep)` (keep the `!/\([ \t]*command/` guard). Add a failing `elif command grep` fixture to `scripts/test-lint-bash32.sh`

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: scripts/lint-bash32.sh:102-122
- **Concern**: FINDING_1 anchoring is still incomplete: substring `( if |[\t;]if )` matches inside double-quoted assert labels. Scenario: `scripts/test-lint-bare-grep-probe.sh` is in `residual-bash-paths.txt`. Labels such as `"path if command rg"` and `"no-path if command grep"` contain ` if command rg` / ` if command grep`, so repo-wide `make lint-bash32` would fail after the rule lands
- **Proposed resolution**: Anchor probes to statement starts only: `(^|[;{&|])[ \t]*(if|elif)...`, not bare ` if ` anywhere on the line. Re-run `make lint-bash32` against `scripts/test-lint-bare-grep-probe.sh` before merge

### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: .pre-commit-config.yaml:327-463
- **Concern**: FINDING_4 fix is incomplete: the plan adds the live script to residual-bash-paths.txt but omits the pre-commit file filter. Scenario: After the plan lands, pre-commit and checks run-relevant still skip lint-bash32 for changes to skills/design/scripts/design-step3b-tail.sh because the lint-bash32 hook files regex does not include that path
- **Proposed resolution**: Add a firm UPDATED section for .pre-commit-config.yaml and insert skills/design/scripts/design-step3b-tail.sh into the lint-bash32 hook files block; include a focused pre-commit run for that path in validation

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/lint-bash32.sh
- **Concern**: The plan's sample awk pattern omits `elif` even though the live defect is `elif command grep` at skills/design/scripts/design-step3b-tail.sh:154. Scenario: An implementer who copies the "workable shape" would not flag the jq-less fallback the issue targets; the new lint could pass harness fixtures while the production site stays unguarded until residual-path scanning alone catches a post-fix file
- **Proposed resolution**: Replace the sample with a pattern that includes `elif`, e.g. match `^[[:space:]]*(if|elif)[[:space:]]+(![[:space:]]+)?command[[:space:]]+(grep|egrep|fgrep|rg|ripgrep)` plus a same-line `;[[:space:]]*(if|elif)` branch if needed, still with `&& !/\([[:space:]]*command/`

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: scripts/lint-bash32.sh:FINDING_1 anchoring
- **Concern**: Accepted FINDING_1 is only partially delivered: the sample uses mid-line ` if ` matching, which hits quoted label text in scripts/test-lint-bare-grep-probe.sh (e.g. :230, :232, :234, :324, :325) that is already in residual-bash-paths.txt. Scenario: After the rule lands, repo-wide `make lint-bash32` fails on the existing bare-grep-probe harness even though those lines are not shell probes, blocking CI and the stated validation commands
- **Proposed resolution**: Anchor on statement-leading `if`/`elif` only (`^[[:space:]]*(if|elif)[[:space:]]+...`) or match the existing lint-bash32 boundary style without matching inside quoted strings; add an explicit `make lint-bash32` / test-lint-bare-grep-probe pass to the testing strategy if suppressions are unavoidable ## Findings ### 1. **correctness** — `scripts/lint-bash32.sh` (planned awk rule) The plan requires matching `elif command grep` and lists it as a positive case, but the exemplar regex only matches ` if ` and `[\t;]if`. The live bug at `skills/design/scripts/design-step3b-tail.sh:154` is `elif command grep`, which that sample does not match (`elif` is not ` if `, and `[\t;]if` does not match the `if` inside `elif`). **Suggested revision:** Pin the awk rule to token-aware `(if|elif)` anchors at line start (with optional leading whitespace), not the incomplete sample. ### 2. **risk-integration** — FINDING_1 anchoring (`scripts/test-lint-bare-grep-probe.sh`) Round 1 accepted FINDING_1 because a substring rule would false-flag `scripts/test-lint-bare-grep-probe.sh`. The plan repeats FINDING_1 language but still proposes mid-line ` if ` matching. That substring appears inside double-quoted test labels on lines such as 230, 232, 234, 324, and 325. That file is already in `scripts/residual-bash-paths.txt`, so a literal copy of the sample breaks `make lint-bash32` without fixing any real probe. **Suggested revision:** Use statement-leading `(if|elif)` anchoring (same fix as finding 1). Optionally note in the testing strategy that `make lint-bash32` must stay clean on the full residual manifest, which implicitly covers `test-lint-bare-grep-probe.sh`. ## Coverage notes (no additional in-scope gaps) - Live defect site, subshell redirect placement, `residual-bash-paths.txt` entry (FINDING_4), harness cases for `if`/`elif`/`if !`, sanctioned subshell and piped negatives, and implementation order (fix sites before enabling the lint) are adequately specified. - Re-raising rejected FINDING_2 (`elif ! command grep` fixture) or FINDING_3 (pinned stderr label) is not warranted under the necessity gate. - Optional `MAY_UPDATE` doc edits and the harness consistency pass on `scripts/test-lint-awk-multibyte-regex.sh` are appropriately scoped; repo grep shows only one unsafe committed probe under `skills/` (`design-step3b-tail.sh:154`).

### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: .pre-commit-config.yaml:327-464
- **Concern**: Prior FINDING_4 fix is incomplete: the plan adds `skills/design/scripts/design-step3b-tail.sh` to `scripts/residual-bash-paths.txt`, but not to the `lint-bash32` pre-commit file filter.. Scenario: CI `lint-local` runs `make lint-only`, so `lint-bash32` only sees paths matched by `.pre-commit-config.yaml`; future edits to the live Step 4b tail file would still bypass the committed-script lint in pre-commit and CI.
- **Proposed resolution**: Add `.pre-commit-config.yaml` as a firm update and include `skills/design/scripts/design-step3b-tail.sh` in the `lint-bash32` hook `files` regex; validate the hook against that path.
