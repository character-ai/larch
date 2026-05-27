### FINDING_1: Loader drops pause marker before failed restore install
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/design-pause-load.sh` deletes the `larch:design-pause` marker before copying restored artifacts into `DESIGN_TMPDIR`. If install fails, the issue no longer has the pause marker even though the snapshot still exists, preventing normal auto-resume. The related harness case only checks `ERROR=restore-install-failed`, so it does not catch marker retention regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: Duplicate Step 1c completion sentinel guidance
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md` contains duplicate Step 1c completion-sentinel instructions, creating drift risk for future edits and confusing orchestrators or structure checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Duplicate pause-state redaction pass
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/design-pause-save.sh` runs duplicate secret-redaction passes over unchanged pause-state content, adding subprocess cost and duplicated failure handling on every pause save.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Marker parse and classify logic is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Marker parse/classify logic is implemented separately in `scripts/design-pause-save.sh`, `scripts/design-pause-load.sh`, and `scripts/named-block-write.sh`, so malformed-marker behavior and grammar changes require coordinated edits across multiple scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Final summary fence does not honor pending pause
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The final summary Bash fence in `skills/design/SKILL.md` lacks the pause-check prelude. If `.pause-requested` is set during the terminal summary path, the pause may not be honored until a later fence, or not at all for that terminal path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Plan marker read logic is not consolidated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `scripts/plan-block-read.sh` has plan marker read logic that is not consolidated with named-block write/read helpers, so future marker grammar changes may need parallel updates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Pause prelude lines are duplicated across fences
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md` contains many copies of identical pause prelude lines, leaving drift risk for fences outside the harness-checked range.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: Loader requires plan.txt before early pause steps create it
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `scripts/design-pause-load.sh` requires `plan.txt` in the restored snapshot, but `plan.txt` is only created at Step 2b while acceptance allows pausing after Step 1c. Resuming an early pause can fail with `LOAD_OK=false ERROR=missing-restored-artifact`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: Pause prelude ignores failed save status
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The defensive pause prelude execs `design-pause-save.sh`, which can exit 0 with `PAUSE_OK=false`. Without parsing stdout, a failed defensive pause at a Bash boundary lets `/design` continue without a marker or error banner even though `.pause-requested` was set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: Loader emits unvalidated marker fields
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `scripts/design-pause-load.sh` emits marker fields such as `SESSION_ID`, `TIER`, and `BRAINSTORM_DONE` without validation. A malicious or malformed issue body could inject newline-delimited fake KV lines into loader stdout, causing orchestrator mis-parse or poisoned environment exports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: Empty-porcelain pause publish can skip changed local state
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/design-log-publish.sh` can return `PUBLISH_OK=true` on empty porcelain without committing local tmpdir changes. A second pause after resume may record a step from local sentinels while restoring an older default-branch snapshot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: Recovery branch rejected after push failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Push failure recovery uses or requires a recovery ref such as `larch-log-design-recovery-RUN_ID`, but `design-pause-save.sh` rejects it or writes no marker. A recoverable local snapshot can therefore produce `PAUSE_OK=false` with no cross-session resume path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_13: Synchronous pause can race defensive prelude save
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `/larch:pause` arms `.pause-requested` and then runs synchronous save, while the `/design` prelude may also exec save. Concurrent saves can race on the issue body and log branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Legacy step-5 snapshots may resume at the wrong step
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The registry walker skips step id `5` in favor of `5b`/`5c`/`5d`, so old `.completed/step-5` snapshots may resume at `5b` and repeat plan-write behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
