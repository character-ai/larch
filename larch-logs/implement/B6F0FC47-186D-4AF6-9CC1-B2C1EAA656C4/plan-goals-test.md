## Goal
Implement issue #7305: [IMPLEMENTING] split-7272-1: Bootstrap foundations.

## Implementation Plan
## Plan

## Approach

Separate typed operations from CLI parsing and emission. Typed callables return frozen dataclasses and raise existing domain errors. Each `*_main` wrapper keeps its current arguments, exit codes, stdout, and stderr.

Keep changes within the ten approved files. Do not migrate `bootstrap.py`, `oos_filer.py`, or other consumers. Preserve legacy tuple unpacking where an existing out-of-scope caller depends on it.

## Files to modify/create

### UPDATED: python/larch/core/redact.py

- Add frozen `ScrubLogSecretsResult`, `ScrubLogDirectoryResult`, and `ScrubSubmodulePathsResult` dataclasses with the approved fields.
- Return these result types from `scrub_log_secrets()`, `scrub_log_directory()`, and `scrub_submodule_paths()`.
- Update in-file callers and CLI wrappers to read named fields.
- Preserve two-value unpacking for existing callers outside this partition. Keep secret counts, replacement text, post-scrub verification, file writes, and CLI output unchanged.
- Keep the deferred `parse_blocks` import and layering justification intact.

### UPDATED: python/larch/state/session_env.py

- Add frozen `WriteEnvResult`, `WriteImplementEnvResult`, `WriteIdResult`, and `ReadKeyResult` dataclasses. Their fields must expose the values or artifact paths currently recovered from wrapper output or filesystem state.
- Extract typed `write_env()`, `write_implement_env()`, `write_id()`, and `read_key()` callables from their `*_main` implementations.
- Expand frozen `SessionSetupResult` so `setup()` fully owns setup probes, identity writes, optional log-copy work, repo resolution, reviewer checks, and optional session-env writing without calling `write_env_main()`.
- Make `SessionSetupResult` carry named fields for every successful setup value: `session_tmpdir`, `session_id`, `render_cache_dir`, conditional `repo` and `repo_unavailable`, `codex_present`, `cursor_present`, `codex_binary_found`, `cursor_binary_found`, `claude_binary_found`, `token_session_id`, `claude_source_file`, and the optional `WriteEnvResult`.
- Include an immutable ordered setup-emission envelope for the exact successful stdout sequence, plus immutable non-KV stdout and stderr diagnostic sequences where preflight or stale-plugin handling currently emits them. This preserves conditional-key presence and output order without re-probing in the wrapper.
- Map result fields to the existing emitted KVs: always `SESSION_TMPDIR`, `SESSION_ID`, and `LARCH_RENDER_CACHE_DIR`; `REPO` and `REPO_UNAVAILABLE` only when repo checks run; reviewer `CODEX_BINARY_FOUND`, `CURSOR_BINARY_FOUND`, `CODEX_PRESENT`, and `CURSOR_PRESENT` only when produced; non-reviewer binary-found values only when available; always `CLAUDE_BINARY_FOUND`; and caller-derived `LARCH_TOKEN_SESSION_ID` and `LARCH_CLAUDE_SOURCE_FILE` only when present.
- Add typed `entry_gate()` and `setup()` callables that return `GateResult` and the complete `SessionSetupResult`.
- Keep validation, path confinement, symlink checks, atomic writes, caller-env recovery, preflight behavior, and setup side effects in the typed functions.
- Leave argument parsing and exact output rendering in the wrappers. `setup_main()` must render only the returned setup envelope and translate existing exceptions back to the same return codes, KV lines, diagnostics, and defaults.
- Preserve plugin-root-only handling, `/dev/null`, missing-file defaults, first-key-wins behavior, existing non-empty session IDs, and setup rerun behavior.

### UPDATED: python/larch/issue/issue_query.py

- Add frozen `IssueContextResult(title_file: Path, body_file: Path)`.
- Change `issue_context()` to return the named result after the same GitHub read and atomic file replacement.
- Update `issue_context_main()` to emit the existing file-path keys from named fields.
- Preserve GitHub failure handling, malformed JSON rejection, string coercion, file names, and CLI output.

### UPDATED: python/larch/issue/tracking_issue.py

- Add public `read()` around `_render_issue_task()` and public `create_issue()` around `_create_issue_cli()`, returning the existing frozen `ReadOutput` and `CreateIssueOutput`.
- Add frozen `SentinelReadResult(issue_number: str, run_id: str, adopted: str)` and public `read_sentinel(path)` over the current sentinel parser.
- Route the `read_main()` sentinel branch through `read_sentinel()` and emit `ISSUE_NUMBER`, `RUN_ID`, and `ADOPTED` solely from its named fields; route non-sentinel task modes through `read()`.
- Preserve sentinel BOM handling, first-value selection, empty valid values, and validation failures for malformed issue numbers, run IDs, and adopted booleans.
- Add frozen `AppendCommentOutput(comment_id: str, comment_url: str)` and public `append_comment_result()`.
- Route `create_issue_main()` and `append_comment_main()` through the new typed callables.
- Retain `rename_with_details()` as the typed rename operation and keep `rename()` and `append_comment()` backward compatible.
- Preserve redaction, retry behavior, lifecycle-marker validation, repository resolution, truncation limits, exception-to-exit-code mapping, and every existing KV key.

### UPDATED: python/larch/report/run_logs.py

- Add frozen `LogInitResult`, `LogWriteResult`, `LogAppendResult`, `LogAppendFailureResult`, and `LogExistsResult` dataclasses. Model the current envelopes with typed paths, booleans, and append state.
- Add public `log_init()`, `log_write()`, `log_append()`, `log_append_failure()`, and `log_exists()` callables over the existing manifest, batch, and execution-issue helpers.
- Keep validation and filesystem work in the typed functions. Keep CLI parsing, `_larch_log_fail()` handling, and exact envelope emission in the `*_main` wrappers.
- Preserve idempotent init and write behavior, batch validation, hashes and byte counts, redaction, diagram sanitization, fallback diagnostic text, retry suffixes, and failure categories.

### UPDATED: python/tests/core/test_redact.py

- Assert the three scrub functions return the expected frozen dataclass types and named fields.
- Cover clean and secret-bearing text, directory counts, residual-secret failure, and submodule scrub results.
- Verify legacy two-value unpacking remains available to out-of-scope consumers.
- Keep CLI parity assertions for scrub counts and boolean formatting.

### UPDATED: python/tests/state/test_session_env.py

- Add direct-call tests for every new typed session callable and result type.
- Cover successful writes, existing session IDs, read defaults, missing or unsafe paths, plugin-root-only mode, entry-gate branches, and setup results.
- For `setup()`, assert the complete result fields and ordered immutable emission envelope against the setup stdout contract: core keys, conditional repo keys, both reviewer probe branches, binary-found fallback behavior, caller-derived keys, and optional session-env write results.
- Assert frozen results reject mutation.
- Retain wrapper tests that pin stdout, stderr, exit codes, written file contents, symlink defenses, atomic behavior, and the absence of duplicate setup side effects.

### UPDATED: python/tests/issue/test_issue_query.py

- Update direct `issue_context()` assertions to use `IssueContextResult`.
- Assert the result is frozen and its files contain the expected title and body.
- Retain malformed JSON, GitHub failure, write failure, and wrapper KV-output coverage.

### UPDATED: python/tests/issue/test_tracking_issue.py

- Add direct tests for `read()`, `read_sentinel()`, `create_issue()`, `append_comment_result()`, and the existing typed rename path.
- Assert result types, fields, immutability, redaction, marker validation, retry behavior, and expected failures.
- Cover sentinel success with `ISSUE_NUMBER`, `RUN_ID`, and `ADOPTED`, plus missing or unreadable sentinels and each malformed sentinel value.
- Verify the three affected CLI wrappers still emit identical success and failure envelopes, including sentinel KV ordering and values.

### UPDATED: python/tests/report/test_run_logs.py

- Add direct-call coverage for init, write, append, append-failure, and exists.
- Assert frozen result fields for created, unchanged, existing, missing, and appended cases.
- Cover invalid slugs and batches, malformed records, filesystem failures, redaction, diagram warnings, retry suffixes, and idempotent reruns.
- Preserve byte-for-byte wrapper envelope and exit-code assertions.

## Edge cases

- Existing redaction consumers outside this partition still unpack two-item results.
- A repeated operation must report the same unchanged state as its CLI wrapper.
- Missing files with defaults remain successful; missing files without defaults remain failures.
- Empty, malformed, or unsafe values fail before writes.
- Redaction results remain verifiable after mutation, with no secret surviving the scrub.
- Frozen results must not expose mutable replacement state except the approved findings mapping.
- Setup output must distinguish an intentionally skipped conditional key from an emitted empty value and must preserve the existing key order without wrapper probes.
- Sentinel reads preserve valid empty fields while rejecting malformed non-empty `ISSUE_NUMBER`, `RUN_ID`, or `ADOPTED` values.

## Failure modes

- Wrapper extraction can change output ordering, diagnostic text, or exit codes. Pin those contracts in wrapper tests.
- Moving validation into typed callables can accidentally bypass path and symlink guards. Exercise rejected targets through direct and CLI paths.
- Partial extraction can duplicate side effects when a wrapper performs work after calling the typed function. Ensure each mutation has one owner.
- Tuple-to-dataclass conversion can break out-of-scope redaction consumers. Retain and test temporary unpacking compatibility.
- An incomplete setup result would force `setup_main()` to re-probe caller state or omit bootstrap-consumed KVs. Keep every success KV and its emission order in the typed result.
- Leaving sentinel adoption in `read_main()` would retain an in-package CLI-only path. Exercise the public sentinel API and wrapper branch together.

## Testing strategy

- Run the five targeted test modules:
  - `python/tests/core/test_redact.py`
  - `python/tests/state/test_session_env.py`
  - `python/tests/issue/test_issue_query.py`
  - `python/tests/issue/test_tracking_issue.py`
  - `python/tests/report/test_run_logs.py`
- Run `make py-lint`.
- Run `make py-test`.
- Compare affected wrapper success and failure stdout against existing assertions, including key names and ordering.
- Compare direct `setup()` result emissions with the canonical setup-output key contract and verify `setup_main()` does not invoke a CLI wrapper for session-env writing.

## Acceptance

- Run the five targeted test modules:
  - `python/tests/core/test_redact.py`
  - `python/tests/state/test_session_env.py`
  - `python/tests/issue/test_issue_query.py`
  - `python/tests/issue/test_tracking_issue.py`
  - `python/tests/report/test_run_logs.py`
- Run `make py-lint`.
- Run `make py-test`.
- Compare affected wrapper success and failure stdout against existing assertions, including key names and ordering.
- Compare direct `setup()` result emissions with the canonical setup-output key contract and verify `setup_main()` does not invoke a CLI wrapper for session-env writing.

oversize_override: operator
diff_lines: 700

## Test plan
(no test plan section in plan-file)
