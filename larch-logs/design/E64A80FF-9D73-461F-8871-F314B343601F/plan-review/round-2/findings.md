### FINDING_1:
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-postplan-emit.sh planned _postplan_pause_checkpoint; skills/design/scripts/lib-phase-driver.sh:14-22; scripts/write-design-current-env.sh:198-203
- **Concern**: Planned pause checkpoint resolves ISSUE_NUMBER from source-env.sh with phase_driver_session_get, but source-env.sh writes export ISSUE_NUMBER=... and phase_driver_session_get only matches bare KEY= lines. Scenario: A .pause-requested file between EMIT, snapshot, and validator causes the new driver to fail closed with exit 2 instead of execing design-pause-save.sh, regressing the pause behavior the extraction is meant to preserve
- **Proposed resolution**: Resolve the issue from ${ISSUE_NUMBER:-} after the orchestrator prelude, or source/parse source-env.sh using its export format; make the pause harness fixture use export ISSUE_NUMBER=... or generate it through write-design-current-env.sh

### FINDING_2:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-postplan-emit.sh (new _postplan_pause_checkpoint); skills/design/scripts/lib-phase-driver.sh:14-17; scripts/write-design-current-env.sh:198-203
- **Concern**: Pause checkpoint is specified to read ISSUE_NUMBER from source-env.sh via phase_driver_session_get, but that helper only recognizes bare KEY= lines while source-env.sh writes export ISSUE_NUMBER=.... Scenario: When .pause-requested appears inside the consolidated driver, the checkpoint cannot resolve the issue and exits 2 instead of execing design-pause-save.sh, regressing the pause behavior the plan says it preserves
- **Proposed resolution**: Have the checkpoint use the already-sourced ISSUE_NUMBER when present or source the generated source-env.sh/read export ISSUE_NUMBER= grammar explicitly; update the pause harness to create source-env.sh with export ISSUE_NUMBER=... rather than a bare KEY= fixture

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:157-159
- **Concern**: skills/design/references/discussion-rounds.md:126. Scenario: Re-emit reference updates only require design-postplan-emit.sh plus KV parse and defects-found routing; they omit the Step 2b-equivalent orchestrator contract (canonical prelude, set +e capture, .design-postplan-emit-result.env file-first symlink guard, exit 2 abort, exit 1 hard-failure keyed on POSTPLAN_EMIT_STATUS) that Approach assigns to prose-only sites and that Gate A gets explicitly
- **Proposed resolution**: Gate B Shared post-apply and discussion-round2 plan revision are executed from reference prose without a SKILL.md fence; under-specified handoff can let exit 1/2 fall through to Step 2b.5, skip missing-diff-lines repair, or parse stdout-only without the result-env guard Mirror the Step 5c / planned Step 2b block in approval-gates.md steps 7-8 and discussion-rounds.md Plan revision authority: require prelude + set +e driver capture + file-first .design-postplan-emit-result.env parse + exit 2/1 branches before Step 2b.5; or normatively point to the Step 2b driver handoff subsection

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-postplan-emit.sh:approach
- **Concern**: skills/design/SKILL.md:762-811. Scenario: Driver consolidates three Step 2b subshells into one fence subshell; inter-step checkpoints call design-pause-save only and do not re-run the canonical prelude between EMIT, snapshot, and validator
- **Proposed resolution**: Today each inline fence re-sources current-design-env-$PPID.sh; a long postplan driver call will not pick up env refreshed mid-flight (rare) and pause granularity vs three separate fences may differ on resume Document in design-postplan-emit.md that one orchestrator prelude per invocation is intentional; if parity with three fences is required, call _postplan_pause_checkpoint only and keep session re-source out of driver OR accept documented single-subshell semantics in Approach edge cases

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:824
- **Concern**: skills/design/SKILL.md:973. Scenario: skills/design/SKILL.md:1001
- **Proposed resolution**: Plan UPDATED scope does not list refreshing Step 2b.5 Callable from or Step 3.5 Gate B cross-refs that still say ACTION=EMIT_PLAN after the driver lands Stale normative text can send implementers or operators to reintroduce inline EMIT/validator fences at re-emit boundaries Add grep-backed edits: Step 2b.5 Callable from and Gate B settled-path prose should name design-postplan-emit.sh (keep ACTION=EMIT_PLAN only in shared validator-failure and loop-out-of-scope paths per plan)

### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-postplan-emit.sh:NEW; scripts/write-design-current-env.sh:195-203; skills/design/scripts/lib-phase-driver.sh:14-16
- **Concern**: The proposed pause checkpoint resolves ISSUE_NUMBER from source-env.sh via phase_driver_session_get, but source-env.sh is written as export ISSUE_NUMBER=... while phase_driver_session_get only matches bare KEY= lines.. Scenario: If .pause-requested appears after the driver starts, before snapshot or validator, the checkpoint fails to resolve the issue and exits 2 instead of execing design-pause-save.sh, regressing the pause contract the extraction is meant to preserve.
- **Proposed resolution**: Use inherited ISSUE_NUMBER from the orchestrator prelude first; if absent, source $DESIGN_TMPDIR/source-env.sh or add an explicit export-aware parser. Add the pause harness fixture with export ISSUE_NUMBER=... so this path is covered.

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:147-160,skills/design/references/discussion-rounds.md:126
- **Concern**: Prose-only re-emit sites omit set +e capture and result-env parse that Approach assigns to them. Scenario: Approach requires approval-gates.md and discussion-rounds.md to direct a prelude + design-postplan-emit.sh run inside set +e with file-first .design-postplan-emit-result.env parsing (Step 5c pattern). The ### UPDATED bullets only swap in the driver call and defects-found routing; they do not repeat set +e, symlink guard, or exit-2/exit-1 handoff. An implementer editing only those subsections can leave default set -e subshells, so exit 1 aborts before POSTPLAN_EMIT_STATUS / VALIDATE_STATUS parsing and defects-found never reaches the shared AskUserQuestion (failure mode #2).
- **Proposed resolution**: Add to both reference updates the same minimal orchestration block used in SKILL.md Step 2b / Gate A: canonical prelude, set +e driver capture, file-first .design-postplan-emit-result.env read with symlink guard, exit 2 abort, exit 1 branch on POSTPLAN_EMIT_STATUS, then defects-found / Step 2b.5 on exit 0.

### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:49-73; skills/design/SKILL.md:762-771
- **Concern**: Finding 1: missing-diff-lines is collapsed to POSTPLAN_EMIT_STATUS=emit-failed while the orchestrator branch is described as keyed on POSTPLAN_EMIT_STATUS. Scenario: The existing contract repairs plan.txt when EMIT_PLAN_STATUS=missing-diff-lines. With the proposed status mapping, a call site that keys only on POSTPLAN_EMIT_STATUS can generic-abort instead of entering the repair path.
- **Proposed resolution**: Either set POSTPLAN_EMIT_STATUS=missing-diff-lines for that case, or require every exit-1 call site to check EMIT_PLAN_STATUS=missing-diff-lines before POSTPLAN_EMIT_STATUS.

### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:40-45; scripts/write-design-current-env.sh:150-203; skills/design/scripts/lib-phase-driver.sh:14-16
- **Concern**: Finding 2: pause checkpoint issue lookup uses phase_driver_session_get on source-env.sh, but source-env.sh writes export ISSUE_NUMBER=... lines. Scenario: When .pause-requested appears between EMIT, snapshot, and validator, _issue resolves empty and the driver exits 2 instead of execing design-pause-save.sh, regressing cooperative pause.
- **Proposed resolution**: Resolve from inherited ISSUE_NUMBER after the orchestrator prelude, source source-env.sh safely, or extend the helper to parse export KEY= lines. Add the pause harness fixture using the real source-env.sh format.

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: scripts/test-design-structure.sh:163
- **Concern**: Finding 3: an existing structural pin still requires discussion-rounds.md to mention invoke-plan-validator.sh. Scenario: The plan removes the inline validator call from discussion-rounds.md, so this unmigrated pin can fail CI even if the new driver wiring is correct.
- **Proposed resolution**: Retarget this pin to design-postplan-emit.sh or include it explicitly in the pin migration list with the other discussion-rounds.md validator pins.

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-call-site-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/discussion-rounds.md:126
- **Concern**: Unified driver applies review_budget=quick skip at discussion-round2 but current prose always runs invoke-plan-validator.sh with no quick guard. Scenario: Scope locks no behavior change yet Edge cases require validator skipped at every call site; today only Step 2b/Gate A/Gate B gate on full/quick while discussion-round2 re-emit always validates — quick runs lose that validation after the swap
- **Proposed resolution**: Revise Scope to document intentional quick alignment at discussion-round2 or add an explicit driver/prose exception if parity with current unconditional validation is required

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-call-site-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:522; scripts/test-design-structure.sh:201-202,260-264
- **Concern**: Gate A is a distinct in-scope SKILL.md call site, but the planned structure-test migration only requires SKILL.md to mention the new driver somewhere; Step 2b can satisfy that while the Gate A optional-trailer paragraph still retains inline ACTION=EMIT_PLAN and invoke-plan-validator.sh.. Scenario: The PR can land with only three of the four in-scope prompt-side call sites converted, leaving Gate A on the old direct call path despite green structure tests.
- **Proposed resolution**: Add a bounded Gate A assertion in scripts/test-design-structure.sh: locate the Optional trailer guard (Gate A re-entry rewrites) paragraph/block and require design-postplan-emit.sh plus the shared defects-found body/site there; do not rely on a file-level SKILL.md grep.

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-call-site-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/write-design-current-env.sh:195-210; skills/design/scripts/lib-phase-driver.sh:14-22
- **Concern**: The plan says design-postplan-emit.sh should resolve ISSUE_NUMBER from source-env.sh via phase_driver_session_get for driver-internal pause checkpoints, but source-env.sh is written as export ISSUE_NUMBER=... and phase_driver_session_get only parses bare KEY= lines.. Scenario: If .pause-requested appears between the driver's internal EMIT/snapshot/validator steps, the checkpoint cannot resolve the issue and exits 2 instead of execing design-pause-save.sh, regressing the pause behavior the plan says to preserve.
- **Proposed resolution**: Resolve ISSUE_NUMBER from the already-sourced environment first, or source/parse source-env.sh with export syntax support; add the pause harness case using a real write-design-current-env.sh-style source-env.sh.

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-kv-contract-coherence
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:49-67,93-103; skills/design/scripts/emit-plan.sh:50-83; skills/design/scripts/validate-plan.sh:78-103
- **Concern**: The proposed driver contract lists mandatory KVs but does not define values for every 0/1 path; POSTPLAN_EMIT_STATUS is never defined on clean exit 0, and not-run/skipped paths leave DIFF_LINES, SNAPSHOT_STATUS, and VALIDATE_* ambiguous.. Scenario: Current wrapped helpers only emit subsets: emit-plan omits DIFF_LINES on missing-diff-lines, and validate-plan emits counts/log only when it runs. A clean or skipped/failure path can produce a result-env that violates the plan's own KV list or leaves orchestrator branches reading empty/stale values.
- **Proposed resolution**: Add a compact default/status matrix for design-postplan-emit.sh: initialize every listed key before EMIT, set POSTPLAN_EMIT_STATUS=ok on exit-0 success including defects-found/skipped-quick, set explicit not-run/skipped/failed values for snapshot and validator fields, and make the emit-failure POSTPLAN_EMIT_STATUS versus EMIT_PLAN_STATUS branch consistent.

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-kv-contract-coherence
- **Severity**: important
- **Focus area**: security
- **Location**: <TMPDIR>/plan.txt:128-153,161-163; skills/design/SKILL.md:1330-1357; skills/design/references/approval-gates.md:147-160; skills/design/references/discussion-rounds.md:126
- **Concern**: The plan requires file-first symlink-guarded parsing only for SKILL.md, while approval-gates.md and discussion-rounds.md are specified as generic KV parse sites.. Scenario: The cited Step 5c pattern reads the result-env first, refuses symlinks, then merges stdout. If the prose-only re-emit sites parse stdout directly or omit the symlink guard, they diverge from the driver handoff contract and from the hardening the plan cites.
- **Proposed resolution**: Revise the approval-gates.md and discussion-rounds.md entries to require the same .design-postplan-emit-result.env file-first, symlink-refusing parse with stdout fallback, and extend the structure-test pin beyond SKILL.md to all three orchestrator surfaces.
