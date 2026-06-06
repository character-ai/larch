### FINDING_1: Static Codex deny ordering test can match a comment instead of the deny arm
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The awk ordering pin can stay green if the static Codex deny case arm is removed, because it anchors on text that can also appear in a comment. This could allow static raw transcripts via the broad `*-output*` allow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_12: Python run-log readers misread quoted finalize-state values
- **Reviewer(s)**: dyn-bash-state-io-output.txt, dyn-ci-toolchain-output.txt
- **Severity**: important
- **Concern**: `python/run_logs.py` reads raw RHS values from quoted `finalize-state.sh`, so values like `'true'`, `'merged'`, or quoted run IDs fail comparisons and validation in finalize-derived log heuristics and pre-push probes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-io-output.txt: Centralize shell-value unquoting in `_read_kv_file()` (or delegate finalize-state reads to `finalize.read_finalize_state()` / shared `shlex` parsing), add regression tests with quoted `finalize-state.sh` fixtures for `_step9a1_heuristic` and `_pre_push_probe`, and keep `ship-pr-state.sh` readers unchanged if that file stays unquoted.
  - From dyn-ci-toolchain-output.txt: Reuse `finalize.read_finalize_state()` (or `shlex`-based unquoting) for finalize-state reads in `run_logs.py`, and add a unit test covering `DESIGN_ONLY_DONE='true'` / `'false'`.


### FINDING_14: Restore final-bail larch-log publish uses unnormalized RUN_ID
- **Reviewer(s)**: dyn-bash-state-io-output.txt
- **Severity**: latent
- **Concern**: `restore-finalize-state.sh` passes `read_state RUN_ID` directly to `larch-log.sh write` without shell-unquoting, unlike other restored values. Quoted state could produce a quoted run ID path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-io-output.txt: Use `_rid=$(shell_unquote_simple "$(read_state RUN_ID)")` (and reject multiline if needed) before the `larch-log.sh write` call; extend `scripts/test-restore-finalize-state.sh` with a quoted `RUN_ID` fixture.


### FINDING_17: Stall-recovery procedure omits finalize-state as an authoritative layer
- **Reviewer(s)**: dyn-python-shell-parity-output.txt
- **Severity**: important
- **Concern**: `stall-recovery.md` still instructs operators to resolve `STALL_TRACKING` from in-memory, `ship-pr-state.sh`, and `session-env.sh`, omitting the now-authoritative `finalize-state.sh` layer. Operators can skip recovery for Python stalls recorded only in finalize state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-shell-parity-output.txt: Align procedure step 1 with the four-layer order in `skills/implement/SKILL.md` (insert `finalize-state.sh` between ship-pr and session-env) and document that quoted values must be normalized the same way as `kv_get` in `skills/implement/scripts/stall-recovery-report.sh`.


### FINDING_18: Python postbump failure writes stalled finalize state without updating ship-pr state
- **Reviewer(s)**: dyn-python-shell-parity-output.txt
- **Severity**: important
- **Concern**: The postbump failure path writes `STALL_TRACKING=true` to `finalize-state.sh` but can leave `ship-pr-state.sh` at a prior non-stall checkpoint, causing consumers keyed to ship state to mis-route retries or recovery bookkeeping.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-shell-parity-output.txt: Route postbump (and any similar direct `write_finalize_state` early-exit branches) through `_write_terminal_state` so both persistence surfaces carry the same `STALL_TRACKING`, `STALL_STEP`, and phase metadata.


### FINDING_2: Dynamic Codex catch-all guard does not match the forbidden suffix-glob shape
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The structural guard looks for `dyn-*-*-codex-output`, not the forbidden `dyn-*-codex-output-*.txt` pattern, so a future broad catch-all could be reintroduced without this pin failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_20: Contract-stream fallback writes degraded JSON to redirected stdout instead of FD 3
- **Reviewer(s)**: dyn-fd-contract-output.txt
- **Severity**: important
- **Concern**: After quiet mode redirects stdout/stderr, `emit_result()` fallback prints degraded JSON to `sys.stdout`; if the primary contract stream fails, the Bash driver may receive no parseable FD 3 envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fd-contract-output.txt: On fallback, write the JSON directly to FD 3 (e.g. `os.write(3, …)` or a fresh `os.fdopen(os.dup(3), "w")`) whenever `_self_initialized_quiet` is true or FD 3 differs from the redirected stdout; keep `sys.stdout` fallback only when quiet routing was never established. Add a subprocess test that runs `quiet_init()` before forcing a broken contract stream and asserts FD 3 receives the fallback payload.


### FINDING_21: Python quiet_init can leave file descriptors half-initialized on failure
- **Reviewer(s)**: dyn-fd-contract-output.txt
- **Severity**: important
- **Concern**: `quiet_init()` mutates FD 4 before log redirection is guaranteed. If later setup fails, quiet env vars are cleared but FD 4 or FD 3 may remain altered, unlike the all-or-nothing bash quiet setup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fd-contract-output.txt: Open the log FD and complete FD 1/2 redirection before touching FD 4, or capture pre-init FD targets and restore them in the `except OSError` path; mirror bash’s “prep log, then dup contract/stderr, then redirect” ordering.


### FINDING_24: refresh-run-logs misreads quoted finalize-state values
- **Reviewer(s)**: dyn-ci-toolchain-output.txt
- **Severity**: important
- **Concern**: `refresh-run-logs.sh` reads quoted `finalize-state.sh` with a raw awk key-value parser, so booleans, merge results, and run IDs can include quote characters and break no-logs guards, post-merge skips, and log paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-toolchain-output.txt: Add the same single-quote unquote helper used in `write-final-report.sh` to `refresh-run-logs.sh` `kv()`, or pass unquoted `ship-pr-state.sh` on the Python path when those keys are authoritative; extend `scripts/test-refresh-run-logs.sh` with quoted `finalize-state.sh` fixtures.


### FINDING_5: Dynamic allow ordering is not pinned against vote-prompt and zero-byte denies
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The ordering test does not verify that vote-prompt and zero-byte deny clauses precede the dynamic Codex allow. A future reorder, especially with a broader dynamic glob, could leak prompt-shaped artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: Stall restore prefers stale finalize STALL_STEP over newer ship-pr state
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `restore-finalize-state.sh` preserves an existing `STALL_STEP` whenever prior finalize state had `STALL_TRACKING=true`, even if `ship-pr-state.sh` has advanced to a newer stall step, causing teardown/sentinel phase mislabeling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


