# Review Round 1

- Mode: `diff`
- 3 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_3: Tmpdir-relative path args are still expanded too early
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-launcher
- **Severity**: important
- **Concern**: Several post-Step-0 fences still interpolate `$IMPLEMENT_TMPDIR`-derived file args before the runner exports `IMPLEMENT_TMPDIR`. In a fresh shell those become root-relative paths, so manifest normalization, recovery-path computation, and run-log append/write can read or write the wrong files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Move all tmpdir-derived path assembly behind the rehydrated launcher, for example by letting these CLI entrypoints derive conventional paths from `IMPLEMENT_TMPDIR` when those path args are omitted, or by adding thin wrapper scripts that construct the argv after `IMPLEMENT_TMPDIR` is exported.
  - From cursor-specialist-edge-cases: Derive conventional tmpdir-relative paths in affected Python entrypoints when argv paths are missing/invalid, or drop redundant path args from fences like route-exit --json-file.
  - From dyn-dyn-launcher: Either derive all tmpdir-relative file args inside `recovery_paths_main` from the resolved tmpdir (ignore or rebase empty-root-relative argv), or change the fence to pass only repo-root plus `--tmpdir` and let Python construct the conventional paths under `IMPLEMENT_TMPDIR`.
  - From dyn-dyn-launcher: Teach `run-log` append/write helpers to fall back to `IMPLEMENT_TMPDIR/larch-logs` when `--log-root` is empty or root-relative-under-`/`, and default record-file paths from the resolved tmpdir when the argv path is missing or root-relative.
  - From dyn-dyn-launcher: Default `--input` to `tmpdir / "scout-coder-manifest.raw.json"` when argv is empty or resolves outside the session tmpdir, mirroring the tmpdir fallback pattern.


### FINDING_4: Step 8 pointer-probe allowlist is too broad
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: blocking
- **Concern**: The Step 8 probe allowlist in `scripts/hook-bg-poll-guard.sh` uses a broad `awk .*current-implement-env-$PPID.sh.*` matcher, which can admit extra shell commands inside the command substitution before the generic denials run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Replace the broad regex in both `probe_target_live_dir_step8` and `bash_is_step8_handoff_foreground_probe` with an exact matcher for the documented awk command, or parse the prefix structurally and reject any command substitution body that is not exactly the approved reader.


### FINDING_5: Resume bootstrap still assumes `IMPLEMENT_TMPDIR` is already exported
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: important
- **Concern**: The resume bootstrap fence still relies on an already-exported `IMPLEMENT_TMPDIR`. In a fresh Step 0 recovery shell, bootstrap rejects `--mode resume` before the stable launcher can be refreshed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Resolve and export `IMPLEMENT_TMPDIR` from `current-implement-env-$PPID.sh` in the resume fence, or route resume through a PID-keyed bootstrap runner that can recover the tmpdir before invoking `step-0-bootstrap.sh --mode resume`.


