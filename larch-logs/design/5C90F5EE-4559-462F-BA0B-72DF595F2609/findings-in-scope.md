### FINDING_1: Validate `state_dir` before any filesystem mutation
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: `state_dir` validation happens after `mkdir -p` and `chmod 700`, and one review also notes the read path is not pinned before `state_file` is accessed. That lets a symlinked `TMPDIR` ancestor be mutated or trusted before the guard fires, so the hardening does not close the redirection path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Reject the root chain before any filesystem mutation, or move the directory check ahead of `mkdir -p` and `chmod 700`.
  - From Codex-Innovation: Validate a symlink-free TMPDIR base before any filesystem mutation, then derive state_dir from that resolved path.
  - From Cursor-Pragmatic: Validate [ -d "$state_dir" ] && [ ! -L "$state_dir" ] immediately after binding state_dir and before mkdir -p or chmod; only create/chmod the directory when that check passes
  - From Cursor-Requirements: Pin hook order explicitly: right after `state_dir` is set (and before `state_file` is read), validate `[ -d "$state_dir" ] && [ ! -L "$state_dir" ]` and exit 0 on failure; only then run `mkdir -p`/`chmod` on a validated path and continue to read/write.

### FINDING_2: Guard promotion against directory destinations
- **Reviewer(s)**: Codex-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The promote step still uses bare `mv` into the state file, so a directory or symlink-to-directory destination can cause the temp file to be dropped into an attacker-chosen tree instead of replacing the state entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Reject non-regular destinations immediately before promotion and only rename over an absent path or plain file.
  - From Cursor-Pragmatic: Before promote, skip when [ -d "$state_file" ]; when [ -L "$state_file" ], require readlink target not be a directory (or rm -f the symlink leaf first), then mv; on guard failure rm the temp file and exit 0

### FINDING_3: Fix symlink regression setup cleanup
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The parent-directory symlink regression setup does not tear down the existing state directory first, so the symlink install can fail and the attack path is never exercised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit setup step (rm -rf "$TMPDIR/larch-read-poll" or a fresh TMPDIR for the symlink regressions) before installing the parent symlink and seeding poison state

### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: scripts/test-hook-anti-read-poll.sh
- **Concern**: [SCOPE-REDUCTION] Negative-control scaffolding requires temporarily removing or bypassing the production read guard. Scenario: The positive symlink tests already prove the feature contract. A source-mutating or bypass harness adds restore and platform-skip paths, and a failed restore can leave the hook under test changed during validation.
- **Proposed resolution**: Drop the negative-control bullet. Keep the mandatory positive assertions for no reminder, unchanged poison target, symlink replacement, and fresh row.

### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: scripts/hook-anti-read-poll.sh:38-40
- **Concern**: [SCOPE-REDUCTION] mkdir/chmod run before the directory-safety check. Scenario: With a preplaced symlink at `$TMPDIR/larch-read-poll`, `mkdir -p`/`chmod 700` can touch the attacker-chosen target before the planned fail-open exit, adding side effects the issue does not require.
- **Proposed resolution**: Validate `$state_dir` as a non-symlink directory first; call `mkdir -p` and `chmod 700` only when that check passes.

### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: <TMPDIR>/plan.txt:47-50
- **Concern**: [SCOPE-REDUCTION] Negative-control scaffolding over-serves the symlink-write fix. Scenario: The required positive regressions already prove the poisoned symlink is not read for the counter and is replaced with a fresh regular state row; adding test-only logic to remove or bypass the guard adds brittle harness complexity without needed coverage
- **Proposed resolution**: Remove the negative-control bullets and the line 71 skip path; keep the poison-row seed, no-reminder assertion, target-unchanged assertion, and observable replacement assertion mandatory
