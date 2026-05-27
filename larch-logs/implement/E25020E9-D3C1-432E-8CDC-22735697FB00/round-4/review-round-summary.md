# Review Round 4

- Mode: `diff`
- 5 accepted, 6 rejected (4 exonerated)

## Accepted Findings

### FINDING_1: Loader drops pause marker before failed restore install
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/design-pause-load.sh` deletes the `larch:design-pause` marker before copying restored artifacts into `DESIGN_TMPDIR`. If install fails, the issue no longer has the pause marker even though the snapshot still exists, preventing normal auto-resume. The related harness case only checks `ERROR=restore-install-failed`, so it does not catch marker retention regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_10: Loader emits unvalidated marker fields
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `scripts/design-pause-load.sh` emits marker fields such as `SESSION_ID`, `TIER`, and `BRAINSTORM_DONE` without validation. A malicious or malformed issue body could inject newline-delimited fake KV lines into loader stdout, causing orchestrator mis-parse or poisoned environment exports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_5: Final summary fence does not honor pending pause
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The final summary Bash fence in `skills/design/SKILL.md` lacks the pause-check prelude. If `.pause-requested` is set during the terminal summary path, the pause may not be honored until a later fence, or not at all for that terminal path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


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


