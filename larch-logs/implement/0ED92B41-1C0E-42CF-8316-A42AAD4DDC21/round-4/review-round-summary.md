# Review Round 4

- Mode: `diff`
- 14 accepted, 8 rejected (8 exonerated)

## Accepted Findings

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


### FINDING_15: Missing direct unit test for `run_relevant_checks` invalid tmpdir
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Missing direct unit test for `run_relevant_checks` invalid tmpdir; direct callers could see wrong `exit_code`/`detail` vs bash captured script.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `test_run_relevant_checks_rejects_invalid_tmpdir` asserting `exit_code` 2 and `ok=False`.


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


### FINDING_2: Missing Step 3/6 ledger marks in `run_relevant_checks`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `run_relevant_checks` omits step3/step6 token/timing ledger marks from the bash capture helper. After Python cutover, implement runs lose Step 3/6 ledger marks present today.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Mirror bash ledger shell-outs for step3 and step6 sites.


### FINDING_20: `_read_log_text_bounded` loads entire file before tail slice (OOM risk)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_read_log_text_bounded` loads the entire file via `read_bytes()` before applying the tail slice. Multi-MB `relevant-checks.log` can OOM the implement agent despite a 60KB logical limit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Implement seek-based tail read; cap bytes read; add test with >max_bytes fixture without loading whole file.


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


### FINDING_5: `_post_dispatch_forbidden_revert` ignores baseline path parameters
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_post_dispatch_forbidden_revert` ignores baseline path parameters; readers may assume baseline snapshots matter for revert logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove unused parameters or wire them into revert.


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


