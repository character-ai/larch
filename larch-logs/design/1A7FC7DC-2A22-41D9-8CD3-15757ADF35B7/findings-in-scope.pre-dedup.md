### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:222-226
- **Concern**: `test-design-structure.sh` mirror empty-qualifier section omits the two `not_contains` literals. Scenario: Accepted round-4 empty-qualifier work adds a mirror block whose `not_contains` list is blank (lines 224-26). An implementer following only that section adds smoke positives but no negative pins; mid-body `only after an empty` / `only after the empty` text can survive in `orchestrator-never.md` while `test-design-structure.sh` passes.
- **Proposed resolution**: Copy the exact literals from plan lines 183-184 into the mirror section: `only after an empty \`<task-notification>\`` and `only after the empty \`<task-notification>\``.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:208
- **Concern**: Implement harness update for all-premature recovery lacks pinned substrings. Scenario: Plan line 208 requires updating lines 358-360 for all-premature notification-only wording, but names no exact literals. Current harness only checks `end the turn and wait for the next \`<task-notification>\`; do not probe \`$DESIGN_TMPDIR\`...` and does not ban `empty stdout` in the When clause. CI can pass if NEVER #8 keeps empty-stdout-only gating while satisfying the do-not-probe substring.
- **Proposed resolution**: Add explicit harness pins: positive `empty or non-empty` (or equivalent from plan line 62) in `$IMPL_MD` NEVER #8; negative `not_contains` for premature-notification recovery gated only on `empty stdout`.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:84-87
- **Concern**: `orchestrator-never.md` top-contract rewrite lacks `/research` carve-out. Scenario: Plan rewrites the header to say skills read the file only when explicitly referenced, but `skills/research/SKILL.md:110-114` still mandates session-start full read via `MANDATORY at session start`. Post-change shared authority contradicts an existing lint-pinned consumer; implementers may delete eager-load wording research still depends on.
- **Proposed resolution**: Add an explicit carve-out: `/research` retains session-start full read; conditional-read wording applies to `/design` and `/implement` only.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:222-225
- **Concern**: test-design-structure.sh mirror empty-qualifier section truncates with an empty `for:` list after requiring `not_contains` checks. Scenario: The accepted full-file bans on `only after an empty` / `only after the empty` are spelled out for test-implement-anti-polling-rule.sh (plan.txt:179-186) but the parallel test-design-structure.sh block stops at line 225 with no literals; an implementer can ship without the mirror negatives while believing the plan satisfied FINDING_4
- **Proposed resolution**: Copy the two literals from plan.txt:183-184 into the test-design-structure.sh subsection at lines 224-225 (same `not_contains` targets as anti-polling)



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:208
- **Concern**: Implement harness retarget for lines 358-360 names all-premature wording but pins no harness-exact substring. Scenario: Plan stub line 62 requires notification-only recovery for premature notifications with empty or non-empty output, yet the existing check substring `end the turn and wait for the next <task-notification>; do not probe $DESIGN_TMPDIR` still matches if NEVER #8 regresses to `fires prematurely with empty stdout` only
- **Proposed resolution**: Add a positive `check` on skills/implement/SKILL.md for `empty or non-empty task output` (or equivalent all-premature gate) and/or a `check_absent` banning empty-stdout-only as the sole premature-notification qualifier; enumerate the exact literal in plan.txt:208 like other harness pins



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:210-232
- **Concern**: [SCOPE-REDUCTION] Firm test-design-structure.sh recovery mirror duplicates test-implement-anti-polling-rule.sh while the mirror spec is incomplete. Scenario: Anti-polling already owns full negative pins (179-206) and positive split-branch pins (188-193); promoting test-design-structure.sh adds parallel maintenance without new coverage, and the truncated mirror block (224-225) is error-prone
- **Proposed resolution**: Drop the firm test-design-structure.sh anti-polling mirror (keep existing design-structure concerns only) or, if retained, paste lines 183-193 verbatim into that subsection and drop duplicate assertions from the anti-polling harness only after parity is explicit



### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:224-230
- **Concern**: `scripts/test-design-structure.sh`'s mirrored `not_contains` stanza is left empty.. Scenario: Without the actual `only after an empty \`<task-notification>\`` and `only after the empty \`<task-notification>\`` strings, the new smoke test can pass while `skills/shared/orchestrator-never.md` still carries the stale empty-only carve-outs, so the split is not protected if the anti-polling harness is bypassed.
- **Proposed resolution**: Fill in the two empty-qualifier `not_contains` assertions in the design-structure rewrite and keep the promised split-branch smoke checks in the same script.



### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:222-226
- **Concern**: Prior accepted mirror empty-qualifier fix is still incomplete: `test-design-structure.sh` section ends with `Add not_contains checks on orchestrator-never.md for:` and lists no literals before jumping to positive pins.. Scenario: The firm `scripts/test-design-structure.sh` promotion promises file-wide bans on `only after an empty` / `only after the empty` as backup to anti-polling, but an implementer following only the Files section can ship without any mirror negatives; mid-body empty-only carve-outs could survive if the primary harness is edited incorrectly.
- **Proposed resolution**: Complete the mirror block by naming the same two `not_contains` literals as lines 181-184 (`only after an empty \`<task-notification>\`` and `only after the empty \`<task-notification>\``) and require they apply anywhere in NEVER #3/#4 body text.



### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:188-193
- **Concern**: Split-branch positive pin guidance for `$ORCH_NEVER_MD` cites the harness literal `Foreground terminal-sentinel probe: after a premature notification with non-empty task output` as an example even though the plan retargets that substring to `skills/shared/design-background-wait.md`, not `orchestrator-never.md`.. Scenario: An implementer can satisfy the positive ORCH_NEVER assertion by copying the relocated design-wait literal into shared NEVER prose, duplicating authority across files, or omit it from ORCH_NEVER and fail the positive pin while the split is otherwise correct.
- **Proposed resolution**: Restrict ORCH_NEVER positive pins to `/design`-branch substrings that belong there (330-332 variant plus empty vs non-empty gating such as `with non-empty task output` / `#5240` empty no-probe). Pin `Foreground terminal-sentinel probe: after a premature notification with non-empty task output` only under the `design-background-wait.md` harness retarget rows.



### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:208
- **Concern**: Implement harness update for lines 358-360 is underspecified: it asks for all-premature notification-only wording but does not pin an exact substring or a negative ban on the current empty-only qualifier.. Scenario: Today's check matches only `end the turn and wait for the next \`<task-notification>\`; do not probe \`$DESIGN_TMPDIR\` or design-only sentinels`. An edit can drop `prematurely with empty stdout` from NEVER #8 while leaving no CI guard, so a later trim can reintroduce empty-only implement recovery and re-open design-sentinel probing on non-empty premature notifications.
- **Proposed resolution**: Add explicit harness pins on `skills/implement/SKILL.md`: positive `empty or non-empty task output` (or equivalent all-premature phrasing from the stub) and `check_absent` for `prematurely with empty stdout on an \`/implement\`` / similar empty-only qualifier.



### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:222-226
- **Concern**: `test-design-structure.sh` mirror empty-qualifier section lists no `not_contains` literals after `for:`. Scenario: The firm `### UPDATED: scripts/test-design-structure.sh` block labels **Mirror empty-qualifier negative pins (accepted finding)** and says to add `not_contains` checks on `orchestrator-never.md`, but lines 225-226 are blank and never name `only after an empty \`<task-notification>\`` or `only after the empty \`<task-notification>\``. The full enumeration exists only under `test-implement-anti-polling-rule.sh` (plan lines 181-184) and in Notes (line 290). An implementer following the `test-design-structure.sh` subsection alone can add positive split-branch smoke checks while skipping the accepted full-file negative pins, leaving the mirror harness unable to catch mid-body empty-only qualifiers if the anti-polling harness is bypassed or regresses.
- **Proposed resolution**: In the `test-design-structure.sh` subsection, copy the two literal `not_contains` targets from plan lines 183-184 under the `for:` line (or state explicitly: mirror the same two strings from the anti-polling **Empty-notification qualifier removal** block). Keep line 290 as a cross-reference only.



