### [Plan Review] FINDING_2

### FINDING_2: `*.patch` glob omits `*.cached.patch` in hardening
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan assumes `pre-coder-path-diffs/*.patch` covers `*.cached.patch`, but Bash `*.patch` does not match names ending in `.cached.patch`. `harden_pre_coder_snapshot_perms` would skip indexed carryover snapshots, leaving them writable if a grant ever reached the directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In harden_pre_coder_snapshot_perms, chmod both pre-coder-path-diffs/*.patch and pre-coder-path-diffs/*.cached.patch (or one loop over all files in that dir); extend the 0444 harness fixture to assert mode 444 on a .cached.patch file


