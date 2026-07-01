### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:40-44
- **Concern**: Step 18a classify item 3 documents only `--in-memory-stall-tracking`, not the other argv the new guard needs. Scenario: The classifier guard is keyed on `bail == "checks-child-failed"`, `step in {"3","6"}`, and raw `EXIT_CODE`. Issue reproduction already passes `--bail-reason`, `--stall-step`, `--phase`, and `--exit-code`; stall-recovery item 3 still only says to pass `BAIL_FAILURE_DETAIL_LOG` plus the memory flag. Without a normative classify template, Step 18a can pass `--in-memory-stall-tracking` and still omit bail/step/exit-code on some paths, so the new `checks-child-sigterm` branch never runs in production.
- **Proposed resolution**: Extend stall-recovery item 3 with an explicit `stall-recovery classify` template: `--in-memory-stall-tracking "${STALL_TRACKING:-false}"`, `--stall-step "${STALL_STEP}"`, `--phase "${PHASE:-checks}"`, `--bail-reason "${IMPLEMENT_BAIL_REASON:-${FINAL_BAIL_REASON}}"`, `--exit-code "${EXIT_CODE:-unknown}"`, plus validated `BAIL_FAILURE_DETAIL_LOG`. Add one bullet in checks-repair-loop section 4 to bind `STALL_STEP`, `PHASE`, `IMPLEMENT_BAIL_REASON` (from composite `FAILURE_REASON`), and `EXIT_CODE` from the captured composite stdout before skipping to Step 18 when no `REDACTED_LOG_FILE` exists.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/references/checks-repair-loop.md:7-13
- **Concern**: Structural checks-failed stall path does not bind `EXIT_CODE` for Step 18a classify. Scenario: The plan fixes classifier logic assuming `--exit-code -15`, but the Step 3 Checks Failure Entry Macro only mandates reading `REDACTED_LOG_FILE`; unlike Step 5 resume (`skills/implement/SKILL.md` line 506) it never requires token-scanning `EXIT_CODE` from the composite relay. On memory-only stalls (no `ship-pr-state.sh` seed), `classify()` falls back to `unknown` unless the orchestrator passes `--exit-code`
- **Proposed resolution**: Augment section 1: when routing structural `checks-child-failed` (or related) failures without `REDACTED_LOG_FILE` to Step 18, bind `EXIT_CODE`, `FAILURE_REASON` → `IMPLEMENT_BAIL_REASON`, `STALL_STEP`, and `PHASE` from the composite first line before Step 18a; mirror the binding in stall-recovery.md item 3 classify argv template
