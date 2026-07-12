### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/implement/ship.py:557-585
- **Concern**: operator_waived sidecars are marked only after the pre-PR guideline flush. Scenario: _compose_assessment_gate_before_pr still runs _guidelines_gate_before_pr with flush_outcome=True, and _flush_guideline_outcome_before_pr commits the guideline outcome before _combined_assessment_result can apply a waiver. Proceed or partial-waiver paths can commit unavailable receipts without operator_waived and leave post-mark sidecars unflushed.
- **Proposed resolution**: Load the validated waiver inside the pre-PR gate path, stamp operator_waived on waived unavailable sidecars before _flush_guideline_outcome_before_pr, and add a test that asserts the flushed run-log batch contains operator_waived.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:725
- **Concern**: The plan omits binding waive-assessment --kinds to route-exit DETAIL. Scenario: Task 1 defines --kinds, and architectural-assessment-unavailable puts kind CSV in DETAIL, but planned SKILL and ship-pr-exit-matrix updates only say proceed writes a waiver and relaunches Step 8. An empty or wrong --kinds write fails closed or waives the wrong assessment kinds.
- **Proposed resolution**: In SKILL.md and ship-pr-exit-matrix.md, read DETAIL or DETAIL_FILE from .ship-route-exit-handoff.env and invoke python/cli.py ship waive-assessment --implement-tmpdir "$IMPLEMENT_TMPDIR" --kinds "<csv>"; pin the fence in scripts/test-implement-fence-shape.sh when added.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/tests/implement/test_ship.py
- **Concern**: Testing strategy item 4 has no named postmerge replay test. Scenario: AC1 and testing strategy item 4 require unavailable assessments, a full waiver, and stubbed shipping through postmerge, but the firm test list only covers resume through PR creation. The operator-bail to merged end state can ship without a reproducible regression for the primary failure mode.
- **Proposed resolution**: Add a named test in test_ship.py or test_ship_recovery.py that stubs ship through postmerge after waiver and asserts merged terminal state, manifest done with pr_number, and summary-final.md outcome merged with a PR line.



### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py:581-595
- **Concern**: operator_waived sidecars are still marked only after the pre-PR guideline outcome flush. Scenario: On waiver resume `_guidelines_gate_before_pr` writes unavailable sidecars and `_flush_guideline_outcome_before_pr` commits them before `_combined_assessment_result` runs; marking `operator_waived` afterward leaves committed run logs without the waiver audit trail the issue requires
- **Proposed resolution**: Load the validated waiver before composing gates; write `operator_waived: true` into waived unavailable sidecars before any `_flush_guideline_outcome_before_pr` call, or defer the pre-PR flush until after waiver application when the gate will proceed



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/implement/ship_recovery.py
- **Concern**: The reconcile clear step may reuse stall-recovery clear-stall and miss bail overlays. Scenario: `stall-recovery clear-stall` clears `STALL_TRACKING`/`STALL_STEP`/`BAIL_REASON` but not `BAIL_NEEDS_USER_INPUT`; stale finalize rows can still normalize to `bailed-needs-user-input` after a verified merged PR
- **Proposed resolution**: Name the bail keys reconcile must clear on all three layers (`BAIL_NEEDS_USER_INPUT`, `BAIL_REASON`, `BAIL_FAILURE_DETAIL_LOG`, etc.) or reuse the same terminal `phase=done` field set as `ship_state._write_ship_state`; post-read verification must fail if any bail overlay remains



### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py:581-721
- **Concern**: operator_waived sidecars are marked only after the pre-PR run-log flush. Scenario: On a waived resume, `_guidelines_gate_before_pr` still calls `_flush_guideline_outcome_before_pr` before `_combined_assessment_result` loads the waiver and marks `operator_waived`. Committed run logs can show bare `unavailable` receipts with no waiver audit trail despite the plan mandating `operator_waived` in sidecars and `docs/run-log-batches.md`.
- **Proposed resolution**: Load and apply a valid waiver before gate flush on the resume path: mark waived unavailable sidecars (or write waiver-aware outcomes) before `_flush_guideline_outcome_before_pr`, or re-flush immediately after marking. Pin ordering in `test_ship.py`.



### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: plan.txt:Testing strategy §4-5
- **Concern**: [BUG] recovery lacks a named committed replay harness. Scenario: Testing items 4-5 are manual "Exercise …" steps with no committed test or harness name. For this `[BUG]` on implement ship/recovery surfaces, G-Fix-2 requires a named offline replay of the BD267D84 failure chain or an explicit one-line no-repro justification. Without that, the operator-bail → early Steps 16-17 → manual merge → reconcile → terminal-emit regressions can ship without CI reproduction.
- **Proposed resolution**: Add a named `python/tests/implement/test_ship_recovery.py` case (or `scripts/test-implement-operator-bail-recovery.sh`) replaying unavailable assessment bail, waiver proceed, stubbed ship through postmerge, and reconcile-before-16-18 gating; or add a one-line no-repro justification in Testing strategy.



### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:725
- **Concern**: Assessment-unavailable operator prompt omits required exact choices. Scenario: The binding issue Task 4 requires `AskUserQuestion` options `proceed-without-assessment (Recommended)` and `stop`. The plan rewrites proceed/stop behavior but does not pin those exact strings in `skills/implement/SKILL.md` or `skills/implement/references/ship-pr-exit-matrix.md`, so implementers may ship paraphrased prompts that fail the documented operator-bail contract.
- **Proposed resolution**: Add the exact option strings and recommended marker to the SKILL and exit-matrix operator-bail bullets; pin them in `scripts/test-implement-anti-halt.sh` or structure harness needles. ## Findings ### 1. (correctness) `operator_waived` must precede pre-PR flush — `python/larch/implement/ship.py:581-721` The plan puts waiver handling in `_combined_assessment_result`, but `_guidelines_gate_before_pr` already flushes guideline outcomes at line 581 before that function runs. On a waived resume, committed logs can still show `unavailable` without `operator_waived`, which conflicts with the planned run-log contract. **Suggested revision:** Apply the waiver and mark sidecars before `_flush_guideline_outcome_before_pr`, or re-flush after marking; add an ordering assertion in `test_ship.py`. ### 2. (risk-integration) Named BUG replay harness missing — Testing strategy §4-5 Items 4-5 describe manual exercises only. For this `[BUG]` on ship/recovery paths, the plan needs either a committed test/harness that replays the BD267D84 failure sequence or an explicit no-repro line. **Suggested revision:** Name a concrete test (for example in `test_ship_recovery.py`) or shell harness, or document why full replay is infeasible in one line. ### 3. (correctness) Exact operator-bail prompt strings not pinned — `skills/implement/SKILL.md:725` The issue requires exact `proceed-without-assessment (Recommended)` / `stop` choices. The plan updates behavior but not the literal prompt contract in SKILL or exit-matrix prose. **Suggested revision:** Pin the exact strings in SKILL, `ship-pr-exit-matrix.md`, and an anti-halt or structure harness needle.



