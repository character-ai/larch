### OOS_1: [OUT_OF_SCOPE] staging dir derives from raw log_root
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness
- **Severity**: important
- **Concern**: The staging directory for the write-tally path is derived from the raw `log_root` instead of the resolved log root, so relative or root-relative `--log-root` values can stage in the wrong place and fail before the tally file is written.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] redaction scratch creation still depends on ambient TMPDIR
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: The redaction scratch path still relies on ambient `mkstemp` selection, so a broken `TMPDIR` can prevent scratch creation even after the input-path fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] absolute inputs can escape session confinement
- **Reviewer(s)**: codex-specialist-edge-cases, cursor-specialist-testing
- **Severity**: important
- **Concern**: The shared run-log helper no longer confines absolute input paths to `IMPLEMENT_TMPDIR`, which can let a caller copy or read an arbitrary host file when a trusted path is supplied.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Keep the generic helper fail-closed on absolute paths outside IMPLEMENT_TMPDIR and move the write-tally workaround into a narrowly scoped internal helper or explicit trusted-path flag.
  - From cursor-specialist-testing: Document the contract or add boundary validation if untrusted callers are ever exposed to this CLI surface.

### OOS_4: [OUT_OF_SCOPE] regression coverage is too weak
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: The current regression/integration coverage does not reliably exercise the fixed temp-path bug or prove the positive staging location, so the test can stay green on buggy code and still miss the required caller or live-run path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Assert write-tally-record.* exists only under tmp_path
  - From cursor-specialist-testing: Add an integration test that stages a record outside IMPLEMENT_TMPDIR and asserts larch_log_write_main succeeds (optional hardening).
  - From codex-specialist-testing: Use a live decoy TMPDIR or in-process tempfile monkeypatching so the buggy path is selected, and add one poisoned-TMPDIR integration test through a caller entrypoint that asserts code-review-tally.json lands with no code-review-tally.flush.err sidecar.
