### FINDING_1: Step 3 monitor-mode regression test cannot detect `set +m` omission
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-process-cleanup
- **Severity**: important
- **Concern**: The proposed monitor-mode regression in `test-run-step3-review.sh` cannot reliably fail if `set +m` is removed from the loop path. Two gaps compound: (1) `RUN_STEP3_PLAN_REVIEW_LOOP_SH` overrides `plan-review-loop.sh` (`run-step3-review.sh:291`), but loop mode hard-sources `review-design-step3-loop.sh` at `run-step3-review.sh:474` with no env override, so a stub behind that variable never runs at the `set +m` site; (2) even if stubbed, the harness calls `run-step3-review.sh --mode loop` directly without first enabling monitor mode, and in typical non-interactive shells job control is already off, so a stub seeing no `m` flag can pass even when the production `set +m` line is deleted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Enable monitor mode in the test harness before launching loop mode (for example set -m 2>/dev/null || true) and assert the stub records monitor disabled only after that precondition; or stub review-design-step3-loop.sh to record $- at loop entry
  - From Cursor-dyn-process-cleanup: Add a real hook (for example `RUN_STEP3_REVIEW_LOOP_SH` defaulting to `review-design-step3-loop.sh`) or a static `grep -Fq 'set +m' run-step3-review.sh` guard plus a sourced stub that records `case $- in *m*)` immediately after `set +m` and before `run_design_step3_loop`


### FINDING_2: Kill-background-processes CLI uses weaker tmpdir validation than other design surfaces
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-dyn-cli-safety, Codex-dyn-cli-safety
- **Severity**: important
- **Concern**: The planned `kill_background_processes_main` CLI validates `--design-tmpdir` with the generic session tmpdir allowlist (`is_allowed_session_tmpdir`) instead of `session_env.validate_design_tmpdir`, diverging from every other `--design-tmpdir` surface (`write_design_env_main`, `plan revise-waterfall`, `decompose`, etc.). Weaker checks accept relative paths, `..` segments, and newline-bearing argv that `validate_design_tmpdir` rejects. Because `kill_session_background_processes` substring-matches `ps` output and sends SIGTERM, a mistyped, relative, or overly broad in-allowlist path (for example `/tmp/x` or a shallow `/var/folders` child) can terminate unrelated same-UID processes. `/design` accepts TMPDIR-backed design tmpdirs through `validate_design_tmpdir`, but the proposed CLI may reject those valid sessions; `design-step3-review.sh` then ignores the helper failure and skips fallback cleanup for a supported path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Validate --design-tmpdir with session_env.validate_design_tmpdir, then keep the same return-2 behavior on validation failure
  - From Codex-Innovation: Require an absolute design tmpdir, resolve it once, validate the resolved path, and pass the canonical absolute path into RunContext; add a focused rejection test for relative input
  - From Cursor-dyn-cli-safety: In `kill_background_processes_main`, call `validate_design_tmpdir` (same as `write_design_env_main` at `python/session_env.py:679-681`). On failure, emit stderr `ERROR=<message>` and exit `2` without calling kill.
  - From Codex-dyn-cli-safety: Tighten validation before calling kill_session_background_processes. Reuse validate_design_tmpdir, require an existing real design session directory such as a claude-design mkdtemp basename plus session-id marker, and add a negative test that an allowed-root non-design path returns 2 and performs no kill.



