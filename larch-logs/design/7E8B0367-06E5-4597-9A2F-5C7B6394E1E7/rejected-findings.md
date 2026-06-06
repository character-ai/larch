### [Plan Review] FINDING_2

### FINDING_2: Drift baseline writes need symlink-safe write-once handling
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-dyn-baseline-contract
- **Severity**: latent
- **Concern**: Planned `drift-baseline.env` creation uses a bare `[[ ! -f ]]` guard and redirection, which can mishandle symlinks or non-regular files and either write outside `DESIGN_TMPDIR` or fail a non-critical drift guard path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Use the existing phase_driver_write_result_env pattern for drift-baseline.env and guard with [[ -e "$baseline" || -L "$baseline" ]] before the write; if an existing baseline is non-regular or unreadable, warn and treat drift as disabled rather than overwriting or aborting
  - From Codex-Pragmatic: Skip when the baseline path exists or is a symlink; otherwise write through a temp file plus rename or the existing result-env helper pattern
  - From Codex-dyn-baseline-contract: Keep write-once behavior but require symlink/non-regular refusal: only create when the path is absent and not a symlink, write via temp-plus-mv or phase_driver_write_result_env, and read BASELINE_* with an allowlist rather than sourcing the file


