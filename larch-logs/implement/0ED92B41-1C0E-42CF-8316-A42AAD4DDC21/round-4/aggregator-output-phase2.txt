Normalized aggregator output from the supplied reviewer findings. Merges follow same behavioral risk; distinct fixes or code paths stay separate.

### FINDING_1: Monolithic `python/checks.py` module
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: A single ~1544-line module owns capture parsing, dispatch, git commit, and loop escalation. Phase 7+ fixes require navigating one file; regressions in unrelated areas become more likely. Split into focused modules or add an extraction milestone before cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Missing Step 3/6 ledger marks in `run_relevant_checks`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `run_relevant_checks` omits step3/step6 token/timing ledger marks from the bash capture helper. After Python cutover, implement runs lose Step 3/6 ledger marks present today.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Mirror bash ledger shell-outs for step3 and step6 sites.

### FINDING_3: `run_check_fix_loop` skips tmpdir confinement when `allowed_tmpdir` is unset
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: On the check-first path, `run_check_fix_loop` skips log-path confinement when `allowed_tmpdir` is `None`. Direct API misuse (or crafted `ChecksResult` paths) could pass fixer logs outside the session tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Require `allowed_tmpdir` for any fixer invocation.
  - From cursor-specialist-correctness-output.txt: Require `allowed_tmpdir` for any iteration that invokes fixer, or always resolve logs with `_resolve_checks_log_path`.

### FINDING_4: Duplicated test patterns in `python/test_checks.py`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Large duplicated `StubRunner` and closure patterns across ~50 tests; each new parity case copies long scripted response lists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Shared pytest fixtures and table-driven loop transition tests.

### FINDING_5: `_post_dispatch_forbidden_revert` ignores baseline path parameters
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_post_dispatch_forbidden_revert` ignores baseline path parameters; readers may assume baseline snapshots matter for revert logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove unused parameters or wire them into revert.

### FINDING_6: Mutable `LoopResult` vs frozen result dataclasses
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `LoopResult` is mutable while other Phase 4 result dataclasses are frozen—inconsistent immutability conventions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Freeze `LoopResult` or document intentional mutation.

### FINDING_7: `run_relevant_checks` buffers full check output in memory
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `run_relevant_checks` buffers all check stdout/stderr via `proc.Runner` before writing the log; bash streams to the log file. Verbose consumer-repo output can spike memory or OOM in Python while bash stays bounded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Redirect subprocess output to the log fd or add a streaming Runner API for capture-style commands.
  - From cursor-specialist-edge-cases-output.txt: Add stream-to-path Runner mode or shell redirect for this call site; test large stub output without full capture.

### FINDING_8: Plan/acceptance still expects `agents.classify_launch_failure` (#3207)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Implementation omits `agents.classify_launch_failure` per #3207 while plan/acceptance text still requires it; Phase 7 cutover docs/tests keyed to old acceptance could expect CI-style failure classification on local fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Align acceptance/issue text with README and bash #3207 behavior.
  - From cursor-specialist-plan-fidelity-output.txt: Align plan/acceptance text with README and `lint-fix-loop.sh` behavior.

### FINDING_9: [OUT_OF_SCOPE] Shared `proc.Runner` full capture for all subprocesses
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Shared `Runner` captures full stdout/stderr for every subprocess; large outputs from other ship-pr phases share the same memory profile. Address holistically when hardening `proc.py`, not only in `checks.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_10: Case `t` linting tracked `larch-logs` conflicts with skip-ci log-flush fix
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Case `t` in `scripts/test-lint-literal-counts.sh` requires linting tracked `larch-logs` markdown in git mode, conflicting with the reverted `larch-logs` exclusion that fixed skip-ci log-flush CI breakage. A `[skip ci]` implement log-flush can commit `larch-logs` markdown with literal-count violations; later PRs fail `python-lint-literal-counts` on files the feature author never touched.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Re-apply `larch-logs/` exclusion in `iter_markdown_files` and replace case `t` with a test asserting those paths are skipped.

### FINDING_11: No bash-vs-Python parity harness for `checks.py`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Phase 4 has no bash parity harness for `checks.py` unlike redact/agents modules; Phase 7 cutover could ship Python loop/dispatch behavior that passes stubs but diverges from `lint-fix-loop.sh` accounting or argv shapes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a small bash-vs-Python parity harness for loop transitions and relevant-checks log parsing on temp fixtures.

### FINDING_12: `validate_tmpdir` `/tmp` paths untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `validate_tmpdir` `/tmp` acceptance paths are untested; implement sessions under `/tmp` could be rejected in Python while bash accepts them (or vice versa) after a refactor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add parametrized `validate_tmpdir` / `run_relevant_checks` tests for `/tmp` and `/private/tmp` session dirs.

### FINDING_13: Serial-lock wrapper around external-agent dispatch untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Serial-lock wrapper around external-agent dispatch is not covered by argv parity tests; lock acquire/release or delay-env handling could regress without test failure while leaf argv still matches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert `lib-external-launcher-common.sh` sourcing and tool/delay args in codex/cursor dispatch tests.

### FINDING_14: No `run_checks_phase` happy-path integration without monkeypatching sub-calls
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No `run_checks_phase` happy-path integration without monkeypatching `run_relevant_checks` / `run_lint_fix`; wiring bugs (site split, tmpdir guard ordering) could slip past loop-only unit tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add one StubRunner-backed fail→fix→pass `run_checks_phase` test without monkeypatching `run_relevant_checks`/`run_lint_fix`.

### FINDING_15: Missing direct unit test for `run_relevant_checks` invalid tmpdir
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Missing direct unit test for `run_relevant_checks` invalid tmpdir; direct callers could see wrong `exit_code`/`detail` vs bash captured script.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `test_run_relevant_checks_rejects_invalid_tmpdir` asserting `exit_code` 2 and `ok=False`.

### FINDING_16: [OUT_OF_SCOPE] Pre-existing git-mode `larch-logs` scanning on main
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Pre-existing git-mode scanning of `larch-logs` on main predates this branch's Phase 4 work; same skip-ci log-flush CI failure mode exists on main even if case `t` were absent. Track as separate CI-hygiene fix; not introduced by `checks.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Poll interval exports (positive harness change)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Poll interval exports moved to file top speed up stub-backed design harness runs—positive change; no action required for Phase 4 review.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_18: `run_lint_fix` log confinement via `run_parent.parent` can widen allowed root
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `run_lint_fix` confines `checks_log` using `parent.parent` of `run_parent` without proving `run_parent` is `{session}/lint-fix-loop`. A miswired caller could set `run_parent` to the session dir (not `…/lint-fix-loop`), widening the allowed root to all of `larch/sessions` and passing a sibling session’s redacted log into codex/cursor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Pass `canonical_tmp` from `validate_tmpdir` into `run_lint_fix` and resolve logs only under it, or assert `Path(run_parent).resolve() == canonical_tmp / "lint-fix-loop"` before `_resolve_checks_log_path`.

### FINDING_19: 60KB tail used for marker parsing and failure redaction (bash uses full log)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `run_relevant_checks` (and related loop paths) parse phase/coverage/warn markers and build failure `.redacted.log` from `_read_log_text_bounded(..., _PROMPT_TAIL_BYTES)` (60KB tail only). Bash greps/redacts the full log (`run-relevant-checks-captured.sh`, `ship-pr.sh` / `lint-fix-loop.sh`); plan bounds apply only to fixer prompt. Large pre-commit/agent-lint output can drop header markers → wrong phase/coverage; fixer receives truncated redacted log vs bash full capture. `_redacted_log_for_dispatch` has the same truncation when `checks.redacted_log_path` is absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Split concerns: full-file (or head-window) marker scan + full-file redact for sidecar; keep 60KB tail only for prompt composition.
  - From cursor-specialist-plan-fidelity-output.txt: Read full log for markers; redact full log to `*.redacted.log`; reserve `_PROMPT_TAIL_BYTES` for `_compose_prompt` only.
  - From dyn-bash-parity-output.txt: scan the full log for markers (streaming `grep` or a full-file pass without loading unbounded memory into prompts); run `redact.redact()` on the complete failure log when building `redacted_log_path`; keep the 60 000-byte tail limit only in `_compose_prompt` / `_read_log_tail`, matching `lint-fix-loop.sh:89-96`.
  - From dyn-bash-parity-output.txt: redact the entire raw log here (same as above); reserve `_PROMPT_TAIL_BYTES` for prompt composition only.

### FINDING_20: `_read_log_text_bounded` loads entire file before tail slice (OOM risk)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_read_log_text_bounded` loads the entire file via `read_bytes()` before applying the tail slice. Multi-MB `relevant-checks.log` can OOM the implement agent despite a 60KB logical limit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Implement seek-based tail read; cap bytes read; add test with >max_bytes fixture without loading whole file.

### FINDING_21: No umask 077 / chmod on raw capture log
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: No `umask 077` or post-write chmod on raw capture log (redacted log chmods only). Under a loose umask, pre-redaction failure logs in shared `/tmp` or cache sessions may be readable by other local users.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Match `run-relevant-checks-captured.sh`: umask 077 around write; chmod 600 raw log; fail closed on chmod error.
  - From cursor-specialist-plan-fidelity-output.txt: Wrap allocation/redaction with `os.umask(0o077)` like `run-relevant-checks-captured.sh`.

### FINDING_22: `mkdtemp` `run_dir` per lint-fix dispatch never removed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `mkdtemp` `run_dir` per lint-fix dispatch is never removed; long `/implement` runs with many fix attempts can fill session tmpdir with codex/cursor artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: `rmtree` in `finally` after dispatch completes or gate retention behind debug env.

### FINDING_23: Dispatch-first loop uses `is_file()` without symlink-safe re-resolve
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Dispatch-first loop checks `is_file()` without symlink-safe re-resolve; race in session dir could redirect fixer input after path validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Re-call `_resolve_checks_log_path` each iteration before `fixer(log_path)`.

### FINDING_24: `log_fd` leak if `runner.run` raises before `fdopen`
- **Reviewer(s)**: dyn-resource-cleanup-output.txt
- **Severity**: latent
- **Concern**: `_allocate_log_file` opens `log_fd` with `os.open`, then `runner.run([...])` runs before the `try`/`os.fdopen` block. If `runner.run` raises (stub, timeout, future `check=True`), the exception bypasses the `except OSError` handler and the descriptor is never closed. Bash truncates with `: >` then redirects afterward.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resource-cleanup-output.txt: Wrap allocation through log write in `try`/`finally` (or move `runner.run` before `os.open` and write via `Path.write_text`/`open()` like bash). Ensure `os.close(log_fd)` runs on every exit path when `fdopen` has not taken ownership, e.g. `finally: contextlib.suppress(OSError); os.close(log_fd)` guarded by a flag set once `fdopen` succeeds.

### FINDING_25: Failed redaction leaves partial `.redacted` file on disk
- **Reviewer(s)**: dyn-resource-cleanup-output.txt
- **Severity**: latent
- **Concern**: `_redacted_log_for_dispatch` and `run_relevant_checks` write fallback `*.redacted` then `chmod(0o600)`; on `OSError` (including chmod after successful write) they return `None` but leave the partial file. Bash removes failed redaction artifacts (`rm -f` in `run-relevant-checks-captured.sh`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resource-cleanup-output.txt: In the `except OSError` branch, `unlink(missing_ok=True)` the redacted path before returning; optionally defer `write_text` until after path validation, or write to a temp name and atomically rename after `chmod`.

### FINDING_26: [OUT_OF_SCOPE] Plan lists `errors` import; module does not
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Plan lists `errors` import; module does not import `errors`—no runtime impact unless helpers are needed later.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Import `errors` only when used, or drop from plan import list.

### FINDING_27: [OUT_OF_SCOPE] `run_dir` retention matches bash (session teardown owns cleanup)
- **Reviewer(s)**: dyn-resource-cleanup-output.txt
- **Severity**: latent
- **Concern**: `tempfile.mkdtemp` `run_dir` directories are not removed on early `FixOutcome` returns; this matches bash (`lint-fix-loop.sh` emits `LINT_FIX_RUN_DIR` without deleting; `cleanup-tmpdir.sh` owns final cleanup)—not a Python-specific leak vs bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resource-cleanup-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] Double-close on `log_fd` — no defect
- **Reviewer(s)**: dyn-resource-cleanup-output.txt
- **Severity**: nit
- **Concern**: When `os.fdopen` succeeds, the `with` manager closes the FD; the `except OSError` path’s `contextlib.suppress(OSError)` around `os.close(log_fd)` correctly handles `fdopen` failure. No defect found.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_29: [OUT_OF_SCOPE] Orphaned fallback `.redacted` on validation-only failure
- **Reviewer(s)**: dyn-resource-cleanup-output.txt
- **Severity**: latent
- **Concern**: When write and `chmod` succeed but `_resolve_checks_log_path` returns `None`, the file remains in session tmpdir—session-scoped debris (cleaned with implement tmpdir), lower severity than partial-write/`chmod` failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resource-cleanup-output.txt: Address the concern above.
