### FINDING_1: step0-parsed reaper uses wrong cache root
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-Session Cleanup Auditor, Codex-dyn-Session Cleanup Auditor
- **Severity**: major
- **Concern**: The planned reaper builds `step0-parsed-{pid}.env` under `cleanup_cache_sessions_root()`, but the write path hardcodes `Path.home() / ".cache" / "larch" / "sessions"`. With `XDG_CACHE_HOME` set, the abort/cleanup flow can remove the symlink and launcher while leaving the parsed env behind, so one PID residual survives.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Build the step0-parsed path the same way as design_step0_env._parsed_cache_path (Path.home() / ".cache" / "larch" / "sessions" / f"step0-parsed-{claude_pid}.env"), or add a shared _step0_parsed_path(pid) helper next to _design_run_path and use it from both sites
  - From Cursor-Innovation: Build all three reap targets with the same Path.home()/.cache/larch/sessions helpers used at write time (_design_symlink_path, _design_run_path, and the _parsed_cache_path shape); do not use cleanup_cache_sessions_root for only step0-parsed
  - From Cursor-Pragmatic: Build the step0-parsed target with the same Path.home()/.cache/larch/sessions layout as _parsed_cache_path (e.g. add _step0_parsed_env_path beside _design_run_path) and use that helper in reap_pid_residuals instead of cleanup_cache_sessions_root()
  - From Codex-Pragmatic: Reap the parsed env via `_parsed_cache_path(claude_pid)` or move both write and reap onto one shared path helper.
  - From Cursor-Requirements: Add a Path.home()-based helper (e.g. _step0_parsed_cache_path) beside _design_symlink_path/_design_run_path and use it in reap_pid_residuals; do not use cleanup_cache_sessions_root() for this file.
  - From Cursor-dyn-Session Cleanup Auditor: Use the same path as _parsed_cache_path (Path.home()/.cache/larch/sessions/step0-parsed-{pid}.env) or a shared helper; do not use cleanup_cache_sessions_root() for this file
  - From Codex-dyn-Session Cleanup Auditor: Use the same path as _parsed_cache_path (Path.home()/.cache/larch/sessions/step0-parsed-{pid}.env) or a shared helper; do not use cleanup_cache_sessions_root() for this file


### FINDING_2: Abort caller still hardcodes degraded-tools messaging
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Innovation
- **Severity**: major
- **Concern**: The new `--reason`/`--tool` plumbing never reaches the only documented Abort caller, so `step0-abort-cleanup` still falls back to the degraded-tools banner and log. That leaves the operator-postpone / non-degraded abort path misleading.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Thread `--reason 'operator postpone; resume later' --tool operator-postpone` into that Abort invocation, or split postpone into its own verb if it is a distinct path.
  - From Cursor-Innovation: Document non-degraded abort fences in skills/design/SKILL.md with explicit --reason/--tool (launcher already forwards $@), or invert defaults to neutral abort text and pass degraded strings only from the degraded-tools Abort branch
  - From Codex-Innovation: Thread `--reason` and `--tool` through the Abort caller, or split a dedicated postpone/cancel cleanup verb and route that branch to it.


