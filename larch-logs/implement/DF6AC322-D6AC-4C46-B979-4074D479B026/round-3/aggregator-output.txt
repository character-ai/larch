### FINDING_1: Static Codex deny ordering test can match a comment instead of the deny arm
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The awk ordering pin can stay green if the static Codex deny case arm is removed, because it anchors on text that can also appear in a comment. This could allow static raw transcripts via the broad `*-output*` allow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Dynamic Codex catch-all guard does not match the forbidden suffix-glob shape
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The structural guard looks for `dyn-*-*-codex-output`, not the forbidden `dyn-*-codex-output-*.txt` pattern, so a future broad catch-all could be reintroduced without this pin failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_3: Finalize-state quoting helpers are duplicated across scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `restore-finalize-state.sh` duplicates unquote/truthy/quote logic from `implement-finalize.sh`, creating a risk that future quote escaping or boolean handling fixes land in only one path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Dynamic Codex allowlist assertions are duplicated across harnesses
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The same dynamic Codex allowlist expectations appear in both unit and write-round integration tests, so future sidecar additions require duplicate manual updates and one harness can drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Dynamic allow ordering is not pinned against vote-prompt and zero-byte denies
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The ordering test does not verify that vote-prompt and zero-byte deny clauses precede the dynamic Codex allow. A future reorder, especially with a broader dynamic glob, could leak prompt-shaped artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Run-log publication still relies on scrubbers for secret safety
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Committed run logs remain dependent on pattern-based redaction before flush; dynamic Codex outputs can contain sensitive content if scrubbers miss a family. The reviewer marked this as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_7: Stall restore prefers stale finalize STALL_STEP over newer ship-pr state
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `restore-finalize-state.sh` preserves an existing `STALL_STEP` whenever prior finalize state had `STALL_TRACKING=true`, even if `ship-pr-state.sh` has advanced to a newer stall step, causing teardown/sentinel phase mislabeling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: Retry-shaped dynamic Codex outputs are documented but not explicitly matched
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Docs mention retry dynamic Codex outputs, but matcher retention for retry-shaped artifacts depends on broad `*-output*` allows. Future deny changes could silently drop them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: Missing negative fixture for phased dynamic vote-prompt basename
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The write-round tests do not include `dyn-*-codex-output-phase*-vote-prompt.txt`, so a regression in phased dynamic vote-prompt exclusion could slip past that harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Bash ship finalize writer still emits unquoted values
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-python-shell-parity-output.txt
- **Severity**: latent
- **Concern**: `scripts/ship-pr.sh` still writes raw `KEY=value` finalize state while restore/Python paths now quote values, leaving mixed formats and unsafe sourcing for special characters. Reviewers marked this as pre-existing or outside this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-python-shell-parity-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Static phased Codex sidecar fixtures are incomplete
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Phased static Codex `.json` and `.cap-hit` sidecars lack explicit fixtures even though broad allows include them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: Python run-log readers misread quoted finalize-state values
- **Reviewer(s)**: dyn-bash-state-io-output.txt, dyn-ci-toolchain-output.txt
- **Severity**: important
- **Concern**: `python/run_logs.py` reads raw RHS values from quoted `finalize-state.sh`, so values like `'true'`, `'merged'`, or quoted run IDs fail comparisons and validation in finalize-derived log heuristics and pre-push probes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-io-output.txt: Centralize shell-value unquoting in `_read_kv_file()` (or delegate finalize-state reads to `finalize.read_finalize_state()` / shared `shlex` parsing), add regression tests with quoted `finalize-state.sh` fixtures for `_step9a1_heuristic` and `_pre_push_probe`, and keep `ship-pr-state.sh` readers unchanged if that file stays unquoted.
  - From dyn-ci-toolchain-output.txt: Reuse `finalize.read_finalize_state()` (or `shlex`-based unquoting) for finalize-state reads in `run_logs.py`, and add a unit test covering `DESIGN_ONLY_DONE='true'` / `'false'`.

### FINDING_13: [OUT_OF_SCOPE] Final-report reader strips quotes without unescaping embedded apostrophes
- **Reviewer(s)**: dyn-bash-state-io-output.txt, dyn-python-shell-parity-output.txt
- **Severity**: latent
- **Concern**: `write-final-report.sh` only removes outer single quotes and does not reverse POSIX shell escaping for embedded apostrophes, so quoted finalize-state fields containing `'` can be decoded incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-io-output.txt: Reuse the same unescape path as `implement-finalize.sh` (`unquote_state_value` / `sed "s/'\\\\''/'/g"`) or call a small shared helper instead of the naive awk `substr()` unquote; add a harness case with an embedded apostrophe in a finalize-state field.

### FINDING_14: Restore final-bail larch-log publish uses unnormalized RUN_ID
- **Reviewer(s)**: dyn-bash-state-io-output.txt
- **Severity**: latent
- **Concern**: `restore-finalize-state.sh` passes `read_state RUN_ID` directly to `larch-log.sh write` without shell-unquoting, unlike other restored values. Quoted state could produce a quoted run ID path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-io-output.txt: Use `_rid=$(shell_unquote_simple "$(read_state RUN_ID)")` (and reject multiline if needed) before the `larch-log.sh write` call; extend `scripts/test-restore-finalize-state.sh` with a quoted `RUN_ID` fixture.

### FINDING_15: [OUT_OF_SCOPE] Dynamic Codex matcher appears correctly ordered in this branch
- **Reviewer(s)**: dyn-bash-state-io-output.txt, dyn-python-shell-parity-output.txt, dyn-ci-toolchain-output.txt
- **Severity**: nit
- **Concern**: Multiple reviewers reported no defect in the scoped dynamic Codex matcher ordering and negative fixture coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-io-output.txt: Address the concern above.
  - From dyn-python-shell-parity-output.txt: Address the concern above.
  - From dyn-ci-toolchain-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Finalize-state readers are split between quoted and raw parsers
- **Reviewer(s)**: dyn-bash-state-io-output.txt
- **Severity**: latent
- **Concern**: `ship.py` reads finalize state through the quoted-aware parser while `run_logs.py` uses a raw key-value reader, creating an architecture split underlying the quoted finalize-state regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-io-output.txt: Address the concern above.

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

### FINDING_19: Python ship-pr state remains raw while finalize state is quoted
- **Reviewer(s)**: dyn-python-shell-parity-output.txt
- **Severity**: important
- **Concern**: `_write_ship_state` still emits raw `KEY=value` lines, widening the contract split after finalize-state hardening. Special characters in fields like `PR_TITLE`, `PR_URL`, or `BRANCH_NAME` remain unsafe for checkpoint consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-shell-parity-output.txt: Reuse the same `_shell_single_quote` helper for `_write_ship_state` emission and add matching unquote support wherever `ship-pr-state.sh` values are parsed (at minimum `scripts/read-session-env-key.sh` or a shared normalizer), with parity tests mirroring `scripts/test-implement-finalize.sh` quoted-boolean coverage.

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

### FINDING_22: [OUT_OF_SCOPE] Dynamic retention comment overstates independence from broad output globs
- **Reviewer(s)**: dyn-fd-contract-output.txt
- **Severity**: latent
- **Concern**: The explicit dynamic Codex allow pins scoped shapes, but retention for future or retry-shaped dynamic outputs still relies on the broad `*-output*` allow. The inline comment may overstate isolation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fd-contract-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] Python quiet logs append while bash quiet logs truncate
- **Reviewer(s)**: dyn-fd-contract-output.txt
- **Severity**: nit
- **Concern**: Python quiet logs are append-only, unlike bash quiet logs, so re-invocation or crash retry can accumulate multiple runs in one log file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fd-contract-output.txt: Address the concern above.

### FINDING_24: refresh-run-logs misreads quoted finalize-state values
- **Reviewer(s)**: dyn-ci-toolchain-output.txt
- **Severity**: important
- **Concern**: `refresh-run-logs.sh` reads quoted `finalize-state.sh` with a raw awk key-value parser, so booleans, merge results, and run IDs can include quote characters and break no-logs guards, post-merge skips, and log paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-toolchain-output.txt: Add the same single-quote unquote helper used in `write-final-report.sh` to `refresh-run-logs.sh` `kv()`, or pass unquoted `ship-pr-state.sh` on the Python path when those keys are authoritative; extend `scripts/test-refresh-run-logs.sh` with quoted `finalize-state.sh` fixtures.

### FINDING_25: [OUT_OF_SCOPE] OOS disposition finalize-state fallback does not unquote values
- **Reviewer(s)**: dyn-ci-toolchain-output.txt
- **Severity**: latent
- **Concern**: `oos-disposition-checkpoint.sh` fallback reads finalize-state values with `grep`/`cut` and no unquoting, so quoted fallback keys could mis-route the gate if ship-pr state lacks them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-toolchain-output.txt: Address the concern above.
