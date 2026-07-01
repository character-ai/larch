### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/SKILL.md
- **Concern**: Review Step 0 Retain parse/bind list still omits SESSION_TMPDIR and the four reviewer stdout keys despite Testing step 3 and Failure modes requiring all seven keys. Scenario: The UPDATED section Retain bullets list only token-session fields and LARCH_TIMING_LEDGER. Testing step 3, Approach item 5, and Failure modes require SESSION_TMPDIR plus CODEX_BINARY_FOUND, CURSOR_BINARY_FOUND, CODEX_PRESENT, and CURSOR_PRESENT alongside the shared citation. Current Step 0 parses all seven and passes reviewer keys into agent degraded-tools-gate. A section-scoped edit can drop tmpdir or presence parsing while leaving gate prose intact, breaking degraded-tools routing. This is an incomplete fix for prior accepted FINDING_1 (rounds 3-4).
- **Proposed resolution**: Expand the Review Step 0 Retain parse/bind enumeration to match Testing step 3: SESSION_TMPDIR, all four reviewer keys, token-session fields, and LARCH_TIMING_LEDGER. Keep the shared session-setup-output.md citation as additive prose only.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/issue/SKILL.md, skills/set-up-forked-open-source-repo/SKILL.md
- **Concern**: Two --run-id consumers still lack explicit replace-with-cite instructions in their UPDATED sections. Scenario: Approach items 1-3 and Testing grep #1 require zero hits for the shared long --run-id phrase across all eight current SKILL.md consumers. alias, cleanup, block-issue, upgrade-larch, report-tokens, and research now have explicit replace steps. skills/issue/SKILL.md (line 45) and skills/set-up-forked-open-source-repo/SKILL.md (line 70) still ship the long phrase today, but their UPDATED sections only say preserve behavior or cite is flag-doc only without naming skills/shared/run-id-flag.md or instructing replacement. A literal section-scoped implementer can leave both long phrases in place and fail grep acceptance. Incomplete fix for prior accepted FINDING_2 (round 4).
- **Proposed resolution**: Add explicit replace-with-cite steps to both UPDATED sections: replace the long inline --run-id flag prose with a short cite of skills/shared/run-id-flag.md. Keep issue parsing behavior and set-up-forked Step 52 strip --run-id before coordinator invocation unchanged.

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/issue/SKILL.md:45
- **Concern**: Blank UPDATED section omits the explicit replacement of the long `--run-id` flag line with `skills/shared/run-id-flag.md`. Scenario: A section-scoped implementer can leave the current long `--run-id` prose untouched, so one of the measured duplication copies remains and the acceptance goal still fails
- **Proposed resolution**: Add the replacement instruction to `### UPDATED: skills/issue/SKILL.md`

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/set-up-forked-open-source-repo/SKILL.md:70
- **Concern**: Blank UPDATED section omits the explicit replacement of the long `--run-id` flag line with `skills/shared/run-id-flag.md`. Scenario: The file can ship unchanged, leaving the duplicate `--run-id` boilerplate in the published repo and preventing the targeted n-gram drop
- **Proposed resolution**: Add the replacement instruction to `### UPDATED: skills/set-up-forked-open-source-repo/SKILL.md`

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/SKILL.md
- **Concern**: Review Step 0 Retain parse/bind list still omits SESSION_TMPDIR and the four reviewer stdout keys. Scenario: The UPDATED section lists only token-session fields and LARCH_TIMING_LEDGER under Retain, while Testing step 3, Failure modes, and current Step 0 require SESSION_TMPDIR plus CODEX_BINARY_FOUND, CURSOR_BINARY_FOUND, CODEX_PRESENT, and CURSOR_PRESENT before degraded-tools gating. An implementer who edits only the Retain bullets can drop tmpdir or presence parsing while leaving the gate prose intact, breaking degraded-tools routing.
- **Proposed resolution**: Expand the Review Step 0 Retain enumeration to match Testing step 3: SESSION_TMPDIR, all four reviewer keys, token-session fields, and LARCH_TIMING_LEDGER, with the same explicit parse/bind wording used for design and research.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/issue/SKILL.md
- **Concern**: Two --run-id consumers still lack explicit replace-with-cite instructions. Scenario: Approach items 1-3 and Testing grep #1 require zero hits for the shared long --run-id phrase across all eight current SKILL.md consumers. UPDATED sections for skills/issue/SKILL.md and skills/set-up-forked-open-source-repo/SKILL.md only preserve behavior (issue mentions cite is flag-doc only; set-up-forked says do not alter fork rules) and never instruct replacing the inline long phrase with a cite of skills/shared/run-id-flag.md, unlike cleanup, alias, upgrade-larch, report-tokens, block-issue, and research.
- **Proposed resolution**: A section-scoped implementer can leave both files unchanged, grep acceptance fails, and the targeted --run-id duplication remains. Add explicit replace-with-cite steps to both UPDATED sections, mirroring cleanup and alias: replace the long inline --run-id prose with a short cite of skills/shared/run-id-flag.md while preserving issue parsing or set-up-forked strip-before-coordinator behavior.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/SKILL.md
- **Concern**: The UPDATED Step 0 **Retain** parse/bind list still names only token-session fields and `LARCH_TIMING_LEDGER`, while Testing step 3 and Failure modes require `SESSION_TMPDIR` plus all four reviewer stdout keys before degraded-tools gating.. Scenario: An implementer who edits only the Retain bullets can drop `SESSION_TMPDIR` or `CODEX_PRESENT`/`CURSOR_PRESENT` parsing while leaving degraded-tools gate prose intact, breaking Step 0 routing the same way prior rounds flagged.
- **Proposed resolution**: Expand the Retain parse/bind enumeration to match Testing step 3: `SESSION_TMPDIR`, `CODEX_BINARY_FOUND`, `CURSOR_BINARY_FOUND`, `CODEX_PRESENT`, `CURSOR_PRESENT`, token-session fields, and `LARCH_TIMING_LEDGER`.

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/issue/SKILL.md:45, skills/set-up-forked-open-source-repo/SKILL.md:70
- **Concern**: Two `--run-id` consumer UPDATED sections still lack an explicit replace-with-cite step. `issue` only says preserve parsing behavior; `set-up-forked` only says do not alter fork safety.. Scenario: Both files still contain the shared long phrase grep targets. A section-scoped implementer can satisfy those sparse UPDATED blocks and leave two of eight n-gram hits in place, failing Testing grep #1 and issue acceptance.
- **Proposed resolution**: Add explicit replace instructions mirroring `cleanup`/`alias`: replace the long inline `--run-id` prose with a short cite of `skills/shared/run-id-flag.md`, keeping issue strip behavior and fork `--run-id` stripping unchanged.

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/set-up-forked-open-source-repo/SKILL.md:70, skills/issue/SKILL.md:45
- **Concern**: UPDATED sections never tell the implementer to replace the existing inline `--run-id` sentence with a cite of `skills/shared/run-id-flag.md`.. Scenario: Those two files keep their current long `--run-id` prose, so the eight-file duplication set still has two live hits and the acceptance grep in the plan will not clear.
- **Proposed resolution**: Add explicit replacement instructions in both UPDATED sections, and keep only the fork / issue behavior notes local.

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/review/SKILL.md:29
- **Concern**: The Step 0 retain list drops `SESSION_TMPDIR` and the reviewer presence keys from the explicit parse/bind enumeration.. Scenario: A plan-conforming edit can keep only the token-session fields and `LARCH_TIMING_LEDGER`, which breaks `REVIEW_TMPDIR=$SESSION_TMPDIR` binding and the `--codex-present` / `--cursor-present` gate inputs on the active review path.
- **Proposed resolution**: Expand the retained parse list to include `SESSION_TMPDIR`, `CODEX_BINARY_FOUND`, `CURSOR_BINARY_FOUND`, `CODEX_PRESENT`, and `CURSOR_PRESENT` alongside the token-session fields and timing ledger.

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/SKILL.md
- **Concern**: The `skills/review/SKILL.md` UPDATED Step 0 Retain parse/bind list still names only token-session fields and `LARCH_TIMING_LEDGER`, omitting `SESSION_TMPDIR` and the four reviewer stdout keys the skill already parses before `agent degraded-tools-gate`. Prior-round fix remains incomplete.. Scenario: Testing step 3, Failure modes, and current Step 0 all require `SESSION_TMPDIR`, `CODEX_BINARY_FOUND`, `CURSOR_BINARY_FOUND`, `CODEX_PRESENT`, and `CURSOR_PRESENT` alongside the shared citation. An implementer who edits only the Retain bullets can drop tmpdir or presence parsing while leaving degraded-tools gate prose intact, breaking Step 0 setup or the gate contract.
- **Proposed resolution**: Expand the Retain parse/bind enumeration to match Testing step 3: `SESSION_TMPDIR`, all four reviewer keys, token-session fields, and `LARCH_TIMING_LEDGER`, with the same explicit-list pattern used for design and research.

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/issue/SKILL.md
- **Concern**: The `skills/issue/SKILL.md` UPDATED section preserves `/issue` behavior but never instructs replacing the long inline `--run-id` flag prose with a cite of `skills/shared/run-id-flag.md`.. Scenario: Approach items 1-3 and Testing grep #1 require zero hits for `when set, used as the run ID for this invocation instead of the auto-generated one` across all eight current consumers. A section-scoped implementer can satisfy the sparse UPDATED block and leave the hotspot in place, failing primary n-gram acceptance.
- **Proposed resolution**: Add an explicit step: replace the flags-table `--run-id` line with a short cite of `skills/shared/run-id-flag.md`; keep all parsing, dedup, dependency, and redaction behavior unchanged.

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/set-up-forked-open-source-repo/SKILL.md
- **Concern**: The `skills/set-up-forked-open-source-repo/SKILL.md` UPDATED section only says to preserve fork safety rules and never instructs replacing the long inline `--run-id` flag prose with a cite of `skills/shared/run-id-flag.md`.. Scenario: Same eight-file grep acceptance as `skills/issue/SKILL.md`: the shared long phrase at line 70 can survive while the implementer believes fork remote rules were the only touch surface. Primary `--run-id` dedup then ships incomplete.
- **Proposed resolution**: Add an explicit step: replace the flags `--run-id` line with a short cite of `skills/shared/run-id-flag.md`; retain the existing Step 1 strip-`--run-id` instruction and all fork remote-configuration behavior.

### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:97-110
- **Concern**: Design Step 0a dedup stays untested. Scenario: The plan’s session-setup grep only checks research and review, so design could keep the long inline session-setup prose and still pass every listed validation step, leaving one of the three targeted consumers duplicated.
- **Proposed resolution**: Add a design-specific grep or before/after check that proves the Step 0a bare session-setup prose was rewritten to the shared-cite form while preserving the single Bash block.
