### FINDING_3: Symlink regression does not require observable replacement
- **Reviewer(s)**: Codex-Arch, Cursor-Requirements, Codex-dyn-Hook Security
- **Severity**: major
- **Concern**: The regression can pass without proving that the hook successfully replaced the symlinked state path, so a broken implementation that reads poisoned state but fails promotion can still satisfy the test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Require the happy path to observe a successful replacement. Assert the state path becomes a regular file with the fresh row after the run, and fail the regression if promotion cannot be observed; keep the target-unchanged check as a second invariant.
  - From Cursor-Requirements: After a successful hook run with working mktemp, assert [ ! -L "$state_path" ] && [ -f "$state_path" ] in addition to target unchanged and no reminder
  - From Codex-dyn-Hook Security: Require an observed successful replacement on the happy path: assert the state path becomes a regular file with the fresh row after the run, and fail the regression if promotion cannot be observed. Keep the target-unchanged check as a second invariant.


### FINDING_4: Temp-state creation still trusts the parent directory
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: Temporary state creation still trusts `$state_dir`, so a preplaced symlinked parent can redirect where the temp file lands and where the later move operates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Reject non-regular or symlinked `$state_dir` before `mktemp`, and fail open if the directory check fails. Add a regression that symlinks the parent directory, not just the leaf state file.


### FINDING_5: Symlink regression seed contract is under-specified
- **Reviewer(s)**: Cursor-dyn-Hook Security
- **Severity**: major
- **Concern**: The poison-row seed can be stale enough to reset the counter, so a symlink-reading implementation may still exit 0 and escape detection without proving the read guard worked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Hook Security: In the test section, require the poison row to use computed path_hash and offset matching run_hook args and prev_time within the 30s window of the chosen HOOK_ANTI_READ_POLL_NOW; optionally add a negative control that fails if -L is removed from the read guard


### FINDING_1: Validate `state_dir` before any filesystem mutation
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: `state_dir` validation happens after `mkdir -p` and `chmod 700`, and one review also notes the read path is not pinned before `state_file` is accessed. That lets a symlinked `TMPDIR` ancestor be mutated or trusted before the guard fires, so the hardening does not close the redirection path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Reject the root chain before any filesystem mutation, or move the directory check ahead of `mkdir -p` and `chmod 700`.
  - From Codex-Innovation: Validate a symlink-free TMPDIR base before any filesystem mutation, then derive state_dir from that resolved path.
  - From Cursor-Pragmatic: Validate [ -d "$state_dir" ] && [ ! -L "$state_dir" ] immediately after binding state_dir and before mkdir -p or chmod; only create/chmod the directory when that check passes
  - From Cursor-Requirements: Pin hook order explicitly: right after `state_dir` is set (and before `state_file` is read), validate `[ -d "$state_dir" ] && [ ! -L "$state_dir" ]` and exit 0 on failure; only then run `mkdir -p`/`chmod` on a validated path and continue to read/write.


### FINDING_3: Fix symlink regression setup cleanup
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The parent-directory symlink regression setup does not tear down the existing state directory first, so the symlink install can fail and the attack path is never exercised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit setup step (rm -rf "$TMPDIR/larch-read-poll" or a fresh TMPDIR for the symlink regressions) before installing the parent symlink and seeding poison state


