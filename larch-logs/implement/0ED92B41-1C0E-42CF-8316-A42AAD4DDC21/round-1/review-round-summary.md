# Review Round 1

- Mode: `diff`
- 23 accepted, 11 rejected (11 exonerated)

## Accepted Findings

### FINDING_1: Plan-mandated agents launch classifiers never wired
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan and acceptance call for `agents.classify_launch_failure` / `is_transient_infra_failure` on failed local fixer dispatch, but `python/checks.py` does not import or call `agents`. Non-zero dispatch gets no classifier-based transient vs user-input split; behavior diverges from planned post-dispatch surface (bash local path also uses exit codes only).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Wire agents classifiers after each failed codex/cursor dispatch using launcher output paths; do not use launch-*-ci.sh or run_waterfall


### FINDING_10: Post-dispatch git state uses two HEAD reads (TOCTOU)
- **Reviewer(s)**: dyn-toctou-atomicity-output.txt
- **Severity**: important
- **Concern**: `_head_changed_after_dispatch` and later `run_lint_fix` logic re-read `HEAD`; concurrent movement can enter committed-delta/`applied` paths without re-running ancestry guards. Bash uses one `current_head` snapshot for guard and all branching (`lint-fix-loop.sh:434-506`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toctou-atomicity-output.txt: Read `HEAD` once immediately after dispatch, run the full head-change validation inline on that value (matching the bash structure), and pass the captured `current_head` through forbidden-path, revert, delta, and commit logic without a second `rev-parse`.


### FINDING_11: Relevant-checks log allocation TOCTOU before write
- **Reviewer(s)**: dyn-toctou-atomicity-output.txt
- **Severity**: important
- **Concern**: `_allocate_log_file` creates the path with `O_EXCL` then closes the fd; checks run; output is written later by path. A same-user race can replace the file with a symlink so check output (pre-redaction) lands on an attacker-chosen target—worse than bash redirecting subprocess stdout/stderr into the fd (`run-relevant-checks-captured.sh:171-188`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toctou-atomicity-output.txt: Stream subprocess output into the exclusively-created fd (or reopen with `O_WRONLY|O_NOFOLLOW` on the known inode under the validated `log_dir`) and reject the path if it is no longer a regular file under `log_dir` immediately before writing; mirror the bash redirect ordering so no long-lived empty placeholder exists.


### FINDING_12: Invalid/unvalidated `tmpdir` escalates to STALLED or allows early fixer I/O
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Bad `IMPLEMENT_TMPDIR` is counted as repeated empty-check failures and can exhaust to STALLED instead of immediate structural tmpdir failure (bash exit 2). `run_checks_phase` also uses unvalidated `tmpdir` for `run_parent` before `validate_tmpdir`, so `dispatch_first` can mkdir/fix under an unapproved path.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_13: Unknown `site` raises uncaught `ValueError`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Invalid/typo `site` crashes `run_checks_phase` via `_site_label` instead of a structured failed `FixOutcome` / `ChecksResult` / `StepResult`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Validate site keys and return failed FixOutcome before dispatch


### FINDING_14: Site validation allows `..` substrings rejected by bash
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Python accepts sites like `evil..step6` that `run-relevant-checks-captured.sh` site-validation rejects.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_15: Plan acceptance and dispatch-path tests largely missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/test_checks.py` lacks plan-listed cases: dispatch-first multi-apply, forbidden-path, cursor argv, git-commit applied path, non-executable relevant-checks, and related stub-runner coverage—regressions in script-dir resolution, forbidden revert, cursor fallback, and loop accounting could pass `make py-test`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add stub-Runner tests listed in the plan Testing strategy


### FINDING_17: Skipped relevant-checks not tested through `run_check_fix_loop`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No loop test with `ChecksResult(skipped=True)` ensuring fixers do not run when consumer has no `relevant-checks.sh`; regression could invoke fixers in Step 6.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_18: Non-executable `relevant-checks.sh` fail-closed semantics
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Missing test for present but non-executable script (exit 126). Implementation may map this to `dispatch-failed` / TRANSIENT via missing redacted log instead of bash structural `check-script-not-executable` fail-closed before the fix loop.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_19: `cursor-wrap-prompt.sh` invoked without `cwd=repo_root`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Wrap script assumes repo CWD; dispatch from another directory mis-wraps or fails cursor fix attempts.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_2: Codex dispatch omits `codex.events.jsonl` stdout redirect
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Bash redirects codex stdout to `codex.events.jsonl` before telemetry; Python does not. `codex_launcher_record_usage_from_events` never sees events JSONL (or recording is skipped/gated differently), so usage accounting and sidecar input diverge from `lint-fix-loop.sh` at Phase 7 cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Mirror bash shell redirects and stderr-tail helper calls around run-external-agent.sh invocations


### FINDING_20: `LARCH_EXTERNAL_SERIAL_LOCK_DELAY` embedded in `bash -c` script text
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-shell-inject-output.txt
- **Severity**: important
- **Concern**: Python interpolates delay into the `bash -c` body; malicious values can break quoting and execute arbitrary commands. Bash passes delay as a function argument to `sleep`, not as re-parsed script syntax—regression from the Python wrapper pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-inject-output.txt: Do not interpolate `delay` into the script text. Pass it as a positional parameter to `bash -c` (e.g. `bash -c '… release_after "$_SERIAL_LOCK" "$2" …' bash "$lib" "$delay" "$tool" …`) and/or validate with a strict numeric pattern (e.g. `^[0-9]+(\.[0-9]+)?$`) before use; default to `0.5` when validation fails.


### FINDING_21: Other `bash -c` helpers embed paths via f-strings without quoting
- **Reviewer(s)**: dyn-shell-inject-output.txt
- **Severity**: important
- **Concern**: Serial-lock, codex, and related `bash -c` fragments double-quote `lib`, logs, `plugin_root`, and event paths from Python f-strings without `shlex.quote()` or positional `$1`/`$2` parameters. `repo_root` and paths with `"`, newlines, `` ` ``, or `$` can break out or expand unexpectedly; `_run_cursor` prompt passing is the safe pattern to mirror.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-inject-output.txt: For every `bash -c` helper, pass all dynamic values as positional arguments after the script name (`bash -c 'source "$1"; … 2>>"$2"' bash "$lib" "$preflight_log" …`) or wrap each interpolation with `shlex.quote()`. Optionally reject `repo_root` paths that contain shell metacharacters before dispatch.


### FINDING_23: No redaction-failed fail-closed path for redacted logs
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Redacted log write failures are not handled like bash `redaction-failed` envelope (`run-relevant-checks-captured.sh:225-232`).
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_24: Dispatch-first redacted log write omits `chmod 0o600`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Redacted CI/lint output may be world-readable under default umask; prefer validated session `log_dir` and mode `0600` after write.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_29: Failure-path `run_relevant_checks` test omits phase/coverage asserts
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Canned failing stdout test does not assert `phase` / `coverage` parsing.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_3: Forbidden committed-path reset ignores git reset failure
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After forbidden submodule/gitmodules commits, Python does not verify `git reset --hard` success or `HEAD == baseline_head`. Failed reset can still surface as `forbidden-path-violation` while forbidden commits remain; bash emits `forbidden-path-reset-failed` (`lint-fix-loop.sh:159-168` parity).
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_34: `lint-literal-counts` git-mode excludes `larch-logs/*.md` (in-scope harness signal)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Unrelated markdown under `larch-logs/` could violate literal-count invariants without CI signal; confirm intent or add alternate guard.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_4: `run_checks_phase` does not pass `target_cmd_display` into `run_lint_fix`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `target_cmd_display` is not threaded through `run_checks_phase` → `run_lint_fix`, so ship-pr per-job prompts will show generic `relevant-checks.sh` wording at cutover instead of job-specific display text.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_6: Missing stderr-tail and cursor-wrapper log redirect parity on dispatch
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Python dispatch paths do not mirror bash `write_failed_agent_stderr_tail` on non-zero codex/cursor launch, and plan fidelity notes missing cursor wrapper log redirect vs `lint-fix-loop.sh`, weakening recovery diagnostics and ship-pr STDERR_TAIL surfacing at cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Mirror bash shell redirects and stderr-tail helper calls around run-external-agent.sh invocations


### FINDING_7: Fixer dispatch uses consumer `scripts/` instead of larch plugin `SCRIPT_DIR`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Fixer dispatch resolves `repo_root/scripts` for `run-external-agent.sh` instead of the larch plugin scripts dir like `lint-fix-loop.sh`. Consumer repos without that script always fail local fix while bash ship-pr still dispatches via plugin scripts. `repo_root` should be cwd/target for checks/git only.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_8: Post-dispatch forbidden revert uses baseline untracked set
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_post_dispatch_forbidden_revert` chooses `rm` vs `checkout` from `baseline_untracked`; bash uses current untracked after dispatch. New forbidden untracked files may not be removed; checkout no-ops while violation may still be reported.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_9: Failed post-dispatch `rev-parse` proceeds with empty HEAD
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Empty `current_head` after failed `rev-parse` is treated like HEAD moved into the committed-delta branch, yielding invalid diff ranges and wrong `applied` / `delta_paths`. Should return failed `FixOutcome` when `rev-parse` fails after dispatch.
- **Suggested revisions (informational for voters; coder decides)**:


