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


