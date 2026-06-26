### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/design/references/validator-failure.md:100-109
- **Concern**: NEW validator-failure.md subsection still omits column-0 Consumer header spec. Scenario: Round-4 accepted header-triplet fix covers sentinel-host-table, step2b-drafter-failsafe, and step2b5-rc-handling only. The validator-failure NEW block documents Contract and When to load prose but never pins line-anchored **Consumer**: at column 0 like the other three NEW files. An implementer can ship prose-only headers and fail make test-references-headers (^**Consumer**:).
- **Proposed resolution**: Mirror the other NEW subsections: require **Consumer**:, **Contract**:, and **When to load**: each at column 0 (not bullet-prefixed) before the moved body in validator-failure.md.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:25-29
- **Concern**: Validator-failure split lacks explicit special-case-before-auto-repair execution order. Scenario: The plan pins MANDATORY READ before Step 5c special-case evaluation while moving auto-repair and _autofix_status into validator-failure.md. Live SKILL.md:884 orders special cases first, then auto-repair. The move drops that inline ordering sentence and the UPDATED bullets do not replace it. An orchestrator can run reference auto-repair before missing-composition or review-provenance guards and break Step 5c short-circuit behavior.
- **Proposed resolution**: In the SKILL.md UPDATED validator-failure bullets add an explicit execution-order pin: after shared entry and MANDATORY READ, evaluate inline Step 5c special-case blocks before the inline autofix fence and before any reference auto-repair or _autofix_status body. Align validator-failure.md When to load to load-after-entry but execute reference auto-repair only after inline special cases pass.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/step2b5-rc-handling.md:74-84
- **Concern**: Verbatim move inventory omits Step 2b.5 self-log paragraph. Scenario: The step2b5-rc-handling Include list covers rc 0/2/other and branches 4-7 but omits the standalone paragraph at skills/design/SKILL.md:522 (Launcher-routed Python design verbs should self-log when they own the failed capture). It sits between item-3 rc bullets and branch 4. A partial move following only the Include list can drop the breadcrumb-only rule for rc=2/other retained paths and duplicate or skip execution-issues.md logging.
- **Proposed resolution**: Add an explicit move line for the self-log paragraph between item 3 and branch 4 in the step2b5-rc-handling.md NEW subsection, or state that the verbatim move must include that paragraph even though it is outside the numbered branch list.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:884-894
- **Concern**: Validator shared entry loses explicit special-case-before-auto-repair execution pin after bind/fence split. Scenario: The plan moves `_validator_target_file` binding and auto-repair prose to `validator-failure.md` while keeping the `design-step-validator-autofix.sh` fence inline, and pins only that the reference is READ before special-case evaluation (load order). Live `SKILL.md:884` orders special-case checks before auto-repair; that one-line pin is not retained. An implementer can run the inline autofix fence before inline Step 5c special cases or before binding `_validator_target_file`, breaking review-provenance and missing-composition short-circuits.
- **Proposed resolution**: In the `skills/design/SKILL.md` UPDATED validator-failure bullets, add an explicit execution-order pin: after the mandatory READ, evaluate inline Step 5c special-case blocks first and short-circuit when they apply; only then bind `_validator_target_file` per `validator-failure.md` and invoke the inline autofix fence; then branch on `_autofix_status` per the reference. Keep a one-line inline reminder mirroring current `SKILL.md:884` special-cases-first ordering.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/step2b5-rc-handling.md:74-82
- **Concern**: Step 2b.5 self-log paragraph omitted from verbatim move inventory. Scenario: The `step2b5-rc-handling.md` move list covers rc 0/2/other bullets and branches 4-7 but omits the standalone paragraph at `skills/design/SKILL.md:522` between Step 2b.5 item 3 and item 4. That text governs rc=2/other retained paths where the Python verb already logged to `execution-issues.md`. A partial move following the inventory can drop the breadcrumb-only rule and cause duplicate logging or missing operator warnings on retained paths.
- **Proposed resolution**: Add `skills/design/SKILL.md:522` (`Launcher-routed Python design verbs should self-log…`) to the `step2b5-rc-handling.md` verbatim move inventory, placed after the rc=2/other bullets and before branch 4 hard trigger.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/validator-failure.md:100-116
- **Concern**: `validator-failure.md` NEW subsection lacks per-file column-0 header triplet spec unlike sibling NEW references. Scenario: Round-4 accepted fix added global edge-case text, but the `validator-failure.md` NEW subsection still has no `Create…` block with column-0 `**Consumer**:` / `**Contract**:` / `**When to load**:` lines. Sibling NEW subsections (`step2b5-rc-handling.md`, `step2b-drafter-failsafe.md`, `sentinel-host-table.md`) pin the harness shape locally. An implementer editing only that subsection can ship bullet-prefixed or prose-only headers and fail `make test-references-headers`.
- **Proposed resolution**: Mirror the `step2b5-rc-handling.md` NEW subsection header-triplet block in `validator-failure.md`, requiring line-anchored column-0 `**Consumer**:`, `**Contract**:`, and `**When to load**:` before the moved body.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:20-22
- **Concern**: Override-after-defects misclassified as direct-entry without items 1-2. Scenario: Live retained Step 2b.5 runs `design-step2b5.sh` for Override-after-defects and Gate B after validator Override (`SKILL.md:507-515`). Plan line 20 lists Override-after-defects hard-size recovery among paths where items 1-2 did not run and line 21 binds only sidecar KVs; line 22 also classifies Override-after-defects as a full-procedure retained caller before item 3. An implementer can skip the fence, treat stale `.design-postplan-emit-result.env` as authoritative, and run branches 4-7 with wrong or empty metrics.
- **Proposed resolution**: Remove Override-after-defects from the direct-entry list (lines 20-21, failure-mode bullets at 169/184, and `step2b5-rc-handaling.md` When-to-load line 94). Keep it only on the retained full-procedure path: items 1-2 inline, MANDATORY READ immediately before item 3.

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/validator-failure.md:100-116
- **Concern**: NEW validator-failure subsection still omits explicit column-0 **Consumer**: header. Scenario: Round-4 header-triplet fix is incomplete. `step2b5-rc-handling.md` and `sentinel-host-table.md` pin the `**Consumer**:` / `**Contract**:` / `**When to load**:` triplet per file; `validator-failure.md` documents only Contract and When-to-load. `scripts/test-references-headers.sh` requires `^\*\*Consumer\*\*:` at line start; prose-only or bullet-prefixed headers fail `make test-references-headers`.
- **Proposed resolution**: Add the same column-0 triplet spec used in the other NEW reference subsections (`**Consumer**:`, `**Contract**:`, `**When to load**:` each at column 0, not bullet-prefixed) before the body-move bullets in `### NEW: skills/design/references/validator-failure.md`.

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/step2b5-rc-handling.md:68-84
- **Concern**: Step 2b.5 self-log paragraph omitted from verbatim move inventory. Scenario: The standalone paragraph at `SKILL.md:522` (`Launcher-routed Python design verbs should self-log when they own the failed capture. Prompt-side orchestration should only print the warning breadcrumb and continue.`) sits between item-3 rc handling and branch 4 and governs rc=2/other retained paths where the verb already logged to `execution-issues.md`. The move inventory lists rc bullets and branches 4-7 only; a partial move can drop the rule and cause duplicate logging or missing warning breadcrumbs on retained paths.
- **Proposed resolution**: Explicitly include the `SKILL.md:522` paragraph in the `step2b5-rc-handling.md` verbatim move inventory (between rc=2/other-rc handling and branch 4) or add a Contract bullet requiring it verbatim in the reference.

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/validator-failure.md:100-116
- **Concern**: validator-failure NEW subsection still omits explicit column-0 Consumer/Contract/When-to-load triplet spec. Scenario: step2b5-rc-handling and the other NEW subsections pin harness-shaped headers at column 0; validator-failure only describes Contract/When-to-load body prose. An implementer can ship prose-only headers and fail make test-references-headers despite global edge-case reminders
- **Proposed resolution**: Mirror the other NEW subsections: add Create with line-anchored header triplet at column 0 (**Consumer**:, **Contract**:, **When to load**:) before the move-inventory bullets

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:507-523
- **Concern**: Override-after-defects is misclassified as a direct-entry path that skips Step 2b.5 items 1-2. Scenario: Live SKILL.md retains Override-after-defects as a full Step 2b.5 procedure (items 1-2 plus design-step2b5.sh). Plan lines 20, 94, and 136 route it through direct-entry branches 4-7 with sidecar KV bind only, skipping the launcher fence and fresh PLAN_LINES/DIFF_LINES capture
- **Proposed resolution**: Remove Override-after-defects from all items-1-2-skipped / direct-entry lists and from settle-rc-dispatch routing prose; keep it only under retained callers with MANDATORY READ immediately before item 3 (plan line 22)

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:882-894
- **Concern**: Shared validator-failure move lacks an execution pin between inline special cases and the inline autofix fence. Scenario: Plan moves auto-repair coordinator prose to validator-failure.md but keeps the autofix fence inline. Deleting line 884 without a replacement bridge lets an orchestrator jump from READ/special-cases to the fence without _validator_target_file binding or reference auto-repair steps
- **Proposed resolution**: Add an inline SKILL.md pin after the Step 5c special-case blocks: when no special case applies, execute validator-failure.md auto-repair coordinator before the inline design-step-validator-autofix.sh fence; keep _autofix_status branching in the reference after the fence The plan is largely aligned with the issue after prior rounds, but three gaps remain: the `validator-failure.md` subsection still lacks an explicit header triplet, **Override-after-defects** is wrongly treated as a direct-entry path, and the validator shared section needs an explicit bridge between inline special cases and the autofix fence.
