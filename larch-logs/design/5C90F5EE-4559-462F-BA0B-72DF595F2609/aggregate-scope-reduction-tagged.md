### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: scripts/test-hook-anti-read-poll.sh
- **Concern**: [SCOPE-REDUCTION] Negative-control scaffolding requires temporarily removing or bypassing the production read guard. Scenario: The positive symlink tests already prove the feature contract. A source-mutating or bypass harness adds restore and platform-skip paths, and a failed restore can leave the hook under test changed during validation.
- **Proposed resolution**: Drop the negative-control bullet. Keep the mandatory positive assertions for no reminder, unchanged poison target, symlink replacement, and fresh row.

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: scripts/hook-anti-read-poll.sh:38-40
- **Concern**: [SCOPE-REDUCTION] mkdir/chmod run before the directory-safety check. Scenario: With a preplaced symlink at `$TMPDIR/larch-read-poll`, `mkdir -p`/`chmod 700` can touch the attacker-chosen target before the planned fail-open exit, adding side effects the issue does not require.
- **Proposed resolution**: Validate `$state_dir` as a non-symlink directory first; call `mkdir -p` and `chmod 700` only when that check passes.

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: <TMPDIR>/plan.txt:47-50
- **Concern**: [SCOPE-REDUCTION] Negative-control scaffolding over-serves the symlink-write fix. Scenario: The required positive regressions already prove the poisoned symlink is not read for the counter and is replaced with a fresh regular state row; adding test-only logic to remove or bypass the guard adds brittle harness complexity without needed coverage
- **Proposed resolution**: Remove the negative-control bullets and the line 71 skip path; keep the poison-row seed, no-reminder assertion, target-unchanged assertion, and observable replacement assertion mandatory
