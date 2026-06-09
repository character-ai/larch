# Review Round 1

- Mode: `diff`
- 19 accepted, 3 rejected (1 neutral)

## Accepted Findings

### FINDING_1: session_env atomic/finalize-state writes lost hardened no-follow semantics
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-writer-guard-output.txt, dyn-module-boundary-output.txt
- **Severity**: important
- **Concern**: `_atomic_write()` and migrated `finalize-state.sh` writers use `mkstemp`/`replace` rather than the hardened `O_CREAT|O_EXCL|O_NOFOLLOW` pattern, creating symlink-race exposure and splitting one artifact across different write primitives.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-writer-guard-output.txt, dyn-module-boundary-output.txt: Address the concern above.


### FINDING_10: local-cleanup flush-only reset mishandles empty git output
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `local_cleanup` requires non-empty subject/diff loop output, unlike bash vacuous-truth semantics, so flush-only local-main states can skip reset and then fail ff-only pull.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: test-lint-fix-loop fixture copies deleted reader
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-lint-fix-loop.sh` still copies `read-session-env-key.sh`, causing the harness to fail during fixture setup after the script deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: test-stall-recovery-report assertions still invoke deleted reader
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: later stall recovery harness cases still call `read-session-env-key.sh` directly, so CI coverage fails instead of validating migrated session CLI behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_15: write-id failure path bypasses contract-stream error envelope
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `write_id` uses `print()` after `quiet_init`, so fd-3 contract callers may see only exit 1 without the expected `FAILED`/`ERROR` envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_19: read-key does not default on unreadable files
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `read-key` can traceback or fail on an unreadable existing session-env file even when `--default` should cause it to print the default and exit successfully.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_2: session writer verbs lack containment checks before writing artifacts
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-writer-guard-output.txt
- **Severity**: important
- **Concern**: `persist-run-flags`, `write-run-params`, `write-id`, and/or `restore-finalize-state` can write session artifacts outside intended temp/cache session roots because they do not consistently apply `_writer_target_allowed()` / safe-parent validation before `mkdir` or `_atomic_write`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-writer-guard-output.txt: Address the concern above.


### FINDING_20: read-classification fallback can raise instead of defaulting to HARD
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `read-classification` catches an initial read failure but retries an unguarded fallback read, so unreadable or racing `run-params.json` can raise instead of warning and defaulting to `HARD`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_21: empty HOME changes cleanup cache root parity
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: with `XDG_CACHE_HOME` unset and `HOME=""`, Python builds `/.cache/larch/sessions` instead of the bash-parity `/tmp/.cache/larch/sessions`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_23: test-implement-structure still pins retired bash implementation details
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: structural CI still asserts deleted bash scripts/snippets such as restore-finalize-state and persist-run-flags details instead of the migrated Python CLI/constants.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_24: timing rehydration harness still requires retired reader
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-implement-timing-rehydration.sh` still requires `read-session-env-key.sh` in its invariant checks, so timing fence tests fail after migration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_26: entry-gate structured errors are hidden after quiet_init
- **Reviewer(s)**: dyn-parity-drift-output.txt
- **Severity**: important
- **Concern**: `entry_gate_main` calls `quiet_init` before `fail()`, and `fail()` writes `GATE_ERROR` to redirected stderr instead of the caller-visible diagnostic path, so bootstrap cannot capture the structured gate failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-parity-drift-output.txt: Address the concern above.


### FINDING_27: read-workflow-path classifier fallback still probes deleted script
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, dyn-parity-drift-output.txt
- **Severity**: important
- **Concern**: `read-workflow-path.sh` still checks for deleted `read-design-classification.sh`, so workflow fallback labels degrade to `unknown` instead of using the migrated `session read-classification`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt, dyn-parity-drift-output.txt: Address the concern above.


### FINDING_28: write-design-env lacks safe output parent validation
- **Reviewer(s)**: dyn-writer-guard-output.txt
- **Severity**: important
- **Concern**: `write_design_env_main` validates the output path but does not call `_safe_output_parent`, so a symlinked parent can redirect writes despite the intended path guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-writer-guard-output.txt: Address the concern above.


### FINDING_29: design current-env symlink refresh lacks dedicated location validator
- **Reviewer(s)**: dyn-writer-guard-output.txt
- **Severity**: important
- **Concern**: the current-design-env symlink refresh does not verify the exact hardcoded cache path or reject symlinked ancestors before mkdir/symlink/replace, allowing same-UID path redirection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-writer-guard-output.txt: Address the concern above.


### FINDING_6: cleanup-tmpdir allowlist accepts allowed roots themselves
- **Reviewer(s)**: codex-specialist-security-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `is_allowed_session_tmpdir` accepts exact roots such as `/tmp` or the cache sessions root, allowing `cleanup-tmpdir` to reach `shutil.rmtree` on a whole root instead of only a session child.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_7: stall recovery still calls deleted read-session-env-key.sh
- **Reviewer(s)**: codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: stall recovery clear/seed paths still invoke the removed `read-session-env-key.sh`, causing Step 18a verification and teardown behavior to fail instead of using `kv_get` or `python/cli.py session read-key`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_8: implement-bootstrap harness stubs impossible CLI filenames
- **Reviewer(s)**: codex-specialist-security-output.txt, codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `test-implement-bootstrap.sh` creates per-verb stub filenames with spaces rather than a real sandbox `python/cli.py` dispatcher, so setup fails or production CLI calls are not intercepted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt, codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_9: external launcher timeout reader still calls deleted read-session-env-key.sh
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `lib-external-launcher-common.sh` still uses the removed reader, so `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT` from `session-env.sh` is ignored and launchers fall back to default timeout behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.


