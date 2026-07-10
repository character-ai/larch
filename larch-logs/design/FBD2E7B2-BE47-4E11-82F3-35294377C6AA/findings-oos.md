### OOS_1: Stall-recovery docs still claim lint-fix ledgers emit only on `main-agent-required` paths
- **Description**: Stall-recovery docs still claim lint-fix ledgers emit only on `main-agent-required` paths. Scenario: After pre-ship exhaustion stalls retain tier-ledger evidence, operators following stall-recovery guidance may miss the new bounded ledger surface and mis-file stall reports
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/implement/references/stall-recovery.md:90-92
- **Phase**: design

### OOS_2: Self-review still treats any composite `NEXT_ACTION=main-agent-edit` as inline repair without a structural-only carve-out
- **Description**: Self-review still treats any composite `NEXT_ACTION=main-agent-edit` as inline repair without a structural-only carve-out. Scenario: After pre-ship exhaustion stops routing to `main-agent-edit`, self-review could still instruct inline edits on structural-unrelated repair-loop output unless narrowed
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/implement/references/self-review.md:48
- **Phase**: design

### OOS_3: Stall-recovery docs still claim lint-fix ledgers emit only on main-agent-required paths
- **Description**: Stall-recovery docs still claim lint-fix ledgers emit only on main-agent-required paths. Scenario: After pre-ship exhaustion stalls emit LINT_FIX_TIER_LEDGER_PATH instead of LINT_FIX_LEDGER_* escalation ledgers, stall-recovery guidance will mislead operators about available evidence on Step 18 recovery
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: skills/implement/references/stall-recovery.md:90-92
- **Phase**: design

### OOS_4: Module docstring still states all non-zero codex/cursor lint-fix launches map to main-agent-required
- **Description**: Module docstring still states all non-zero codex/cursor lint-fix launches map to main-agent-required. Scenario: Post-change pre-ship recoverable dispatch failures advance inside the waterfall and terminate in stall; the header comment will contradict runtime behavior and mislead maintainers
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/larch/implement/checks.py:1-6
- **Phase**: design

### OOS_5: Self-review and other references still treat any NEXT_ACTION=main-agent-edit as unconditional inline repair
- **Description**: Self-review and other references still treat any NEXT_ACTION=main-agent-edit as unconditional inline repair. Scenario: Once exhaustion no longer emits main-agent-edit, lingering prose that lacks a structural-only carve-out can cause orchestrators to attempt inline repair on structural failures only, or confuse stall versus edit routing
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: skills/implement/references/checks-repair-loop.md:56-87
- **Phase**: design

### OOS_6: Stall-recovery docs still say LINT_FIX_LEDGER_* emits only on main-agent-required paths. After pre-ship exhaustion stalls with LINT_FIX_TIER_LEDGER_PATH, operators following stall-recovery may look for the wrong ledger keys during recovery.
- **Description**: Stall-recovery docs still say LINT_FIX_LEDGER_* emits only on main-agent-required paths. After pre-ship exhaustion stalls with LINT_FIX_TIER_LEDGER_PATH, operators following stall-recovery may look for the wrong ledger keys during recovery.. Scenario: Update stall-recovery.md in a follow-up issue to document tier-ledger emission on pre-ship stall separately from escalation LINT_FIX_LEDGER_* on structural main-agent-required.
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/implement/references/stall-recovery.md:90-92
- **Phase**: design

### OOS_7: Self-review still treats any composite NEXT_ACTION=main-agent-edit as inline repair with no structural-only carve-out. After exhaustion stops routing to main-agent-edit, only structural lint-fix failures should re-enter inline edits.
- **Description**: Self-review still treats any composite NEXT_ACTION=main-agent-edit as inline repair with no structural-only carve-out. After exhaustion stops routing to main-agent-edit, only structural lint-fix failures should re-enter inline edits.. Scenario: Self-review runs could still attempt broad inline repair on a non-structural repair-loop envelope if a stale or misrouted main-agent-edit appears.
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/implement/references/self-review.md:48-48
- **Phase**: design

