### OOS_1: Step 18 cleanup docs still derive stall state from dead `.bg-wait-active` markers
- **Description**: Step 18 cleanup docs still derive stall state from dead `.bg-wait-active` markers. Scenario: The fifth stall-recovery layer in `step18-cleanup.md` still describes dead-PID `.bg-wait-active` for checks legs. After `_tokens.py` moves abandoned-checks detection to bgjob registry rows, operators following Step 18 prose may misread stall cause or retry path even when code classifies correctly.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/implement/references/step18-cleanup.md:15
- **Phase**: design



### OOS_2: Step 18 cleanup prose still documents `.bg-wait-active` fifth-layer stall detection
- **Description**: Step 18 cleanup prose still documents `.bg-wait-active` fifth-layer stall detection. Scenario: The plan migrates abandoned-checks classification in `python/larch/state/_tokens.py` and `stall-recovery.md` to bgjob registry rows, but `step18-cleanup.md` is not listed. Step 18 still loads that reference, so operators may follow retired marker guidance after Python routes through registry liveness.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/implement/references/step18-cleanup.md
- **Phase**: design



