### FINDING_3: Statusline symlink test needs to exercise the active-run pointer path
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: The current symlink-safety test still uses a flat progress log and never sets an active `current`, so it does not cover the new active-run reader path. That lets a regression in the symlink-safe pointer lookup slip through even though the test appears to cover the feature.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: `Retarget the test to activate a run and place the symlink on the active-run `current` or run-log ancestor chain, then assert `render_statusline` still returns `""`.`


### FINDING_4: Statusline reader still needs a directory-open path that is fd-relative, not path-based
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: The proposed `read_active_run_id` flow still opens the clone directory by path after checking ancestors. That leaves a time-of-check/time-of-use gap where a symlink swap can redirect the statusline reader to another tree’s `current` and breadcrumbs, so the fd-safe lookup fix is still incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: `Add a no-create fd-relative opener for existing clone dirs, mirroring `_ensure_directory_fd` traversal without mkdir, and use it in `read_active_run_id`; return `None` on missing components.`


