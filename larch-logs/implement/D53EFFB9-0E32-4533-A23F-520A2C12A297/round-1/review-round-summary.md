# Review Round 1

- Mode: `diff`
- 2 accepted, 6 rejected (2 neutral)

## Accepted Findings

### FINDING_3: Waterfall cleanup regression is static grep only, not behavioral TERM test
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The plan promised a behavioral EXIT/TERM-trap regression, but `scripts/test-dispatch-with-waterfall.sh` only grep-checks for trap strings. A trap present in source but broken at runtime (wrong PIDs, never invoked, cleared `pids` before exit) would still pass CI, and mid-phase launcher or collector orphans could return undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Add the bounded background dispatcher test from the plan, including leftover PID cleanup on failure.
  - From cursor-specialist-edge-cases-output.txt: Add the planned test: sleeping stub launchers, background dispatcher, TERM dispatcher, assert stub PID is dead; harness cleanup trap for leftovers.
  - From cursor-specialist-testing-output.txt: Add the planned behavioral test: sleeping stub launcher recording PID, background dispatcher, TERM to dispatcher, assert stub PID is gone, with harness cleanup for leftovers.
  - From codex-specialist-testing-output.txt: Add the bounded runtime TERM test with a sleeper launcher PID file, dispatcher TERM, kill -0 assertion, and cleanup trap.


### FINDING_9: `kill_background_processes_main` accepts symlinked leaf tmpdir paths
- **Reviewer(s)**: dyn-tmpdir-validation-output.txt
- **Severity**: important
- **Concern**: `kill_background_processes_main` accepts a leaf directory symlink after `session_env.validate_design_tmpdir` (which permits resolving directory symlinks under the allowlist) and never requires the caller path itself to be a real directory. A local attacker can create `/tmp/claude-design-<name>` as a symlink to another user's live session directory; the victim's real `source-env.sh` satisfies the marker check, and the CLI then calls `kill_session_background_processes` with the victim's resolved tmpdir. The new `session kill-background-processes` entry point makes this reachable outside `/implement` teardown, where `_cleanup_target_ok` adds extra ownership checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tmpdir-validation-output.txt: In `kill_background_processes_main`, reject `path.is_symlink()` (and require `path.is_dir()` on the literal caller path), or require `path.resolve(strict=True)` to equal `resolved` with `not path.is_symlink()`. Add a harness case that symlinks one design tmpdir to another and expects exit `2` with no kill.


