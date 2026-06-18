# Review Round 1

- Mode: `diff`
- 16 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Failure-detail log accepted without 64 KiB validation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-public-surface-output.txt
- **Severity**: important
- **Concern**: `classify()` and related paths accept `--failure-detail-log` files under the tmpdir without enforcing the documented ≤65536-byte cap (and without bash-parity `O_NOFOLLOW`/regular-file checks). Oversize logs can be marked valid, persisted as `FAILURE_DETAIL_LOG`, used as primary classification evidence, and re-read by sensitive-corpus construction, diverging from retired bash case9 and `SECURITY.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add shared ≤65536-byte validation for detail logs; reject with --failure-detail-log exceeds 64KiB and detail_log_valid=false
  - From codex-specialist-correctness-output.txt: Add a shared validated-detail-log reader with size, symlink, regular-file, absolute-path, and containment checks before reading.
  - From cursor-specialist-edge-cases-output.txt: Add a shared validated detail-log reader with st_size<=65536, O_NOFOLLOW open, and invalid-on-oversize; wire classify validate_terminal_state record_escalation and Tier A compose through it
  - From codex-specialist-edge-cases-output.txt: Add a shared validated-detail-log reader that checks non-symlink regular file status and `st_size <= MAX_OPTIONAL_EVIDENCE_BYTES` before reading. Use it in both implement and generic classify paths.
  - From cursor-specialist-testing-output.txt: Add >64KiB classify fixture pinning ignore/reject behavior and stderr contract
  - From codex-specialist-testing-output.txt: Check stat size against MAX_OPTIONAL_EVIDENCE_BYTES before reading and port the oversize-log test
  - From dyn-public-surface-output.txt: Add a dedicated `validate_failure_detail_log()` helper matching the documented contract (canonical, regular, non-symlink, under tmpdir, ≤65536 bytes, fail closed), use it everywhere `--failure-detail-log` / `FAILURE_DETAIL_LOG` is accepted or embedded, and add pytest cases for oversize rejection and Tier A non-embedding beyond the cap.


### FINDING_10: Tier B sensitive-token validation missing repo-relative path and assignment deny-list
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-public-surface-output.txt
- **Severity**: important
- **Concern**: `_sensitive_token_rejects_file()` omits repo-relative path regex and uppercase assignment deny-list checks from the retired bash helper. Bounded root-cause text containing `docs/private-plan.md` or `CUSTOMER_SECRET=…` can pass when not already in the sensitive corpus, allowing disclosure via Tier B filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Port the repo-relative regex and candidate_has_sensitive_assignment logic and cover both in pytest.
  - From dyn-public-surface-output.txt: Port the bash candidate-side scans into `_sensitive_token_rejects_file()` (repo-relative path regex plus assignment-shape scan with the same allowlist/safe-token rules), wire them through both `compose_report()` pre-redaction checks and `validate_tier_b_public_file()`, and restore pytest coverage for the retired Case 23 repo-relative and allowlisted-assignment scenarios.


### FINDING_11: Implement vs generic classify use different detail-log read limits
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Implement `classify()` truncates detail-log evidence at 8192 bytes while generic classify allows 65536. The same stall with a 20 KiB detail log can classify differently across profiles (`FAILURE_CLASS` / signature divergence).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Unify on MAX_OPTIONAL_EVIDENCE_BYTES and the same validated reader in both classify paths


### FINDING_17: Bash bail-precedence fixtures (case7g–7k6) not ported
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Deleted bash classifier bail-precedence fixtures (case7g–7k6) lack pytest ports for dispatch-failure and submodule-restricted patterns. Stale network-timeout text in ship-pr-state can misclassify submodule-restricted or wrapper-validation stalls as transient-infra with wrong `RESUME_HINT`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port case7g-7k6 as parametrized classify tests covering bail tokens, resume hints, and MATCHED_CLASSIFIER_PATTERN with stale-evidence fixtures


### FINDING_18: Same-cause-repeat promotion logic lacks pytest
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Same-cause-repeat promotion logic changed but has no pytest. A repeated failure signature after `record_attempt` may not promote to `same-cause-repeat` in CI, so retry-cap / `RESUME_HINT=none` regressions can ship silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add init-attempts + dual record-attempt + classify test asserting FAILURE_CLASS=same-cause-repeat and RESUME_HINT=none


### FINDING_19: Tier B compose-report / filing / fallback paths lack pytest coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `SECURITY.md` claims Tier B create/fallback coverage, but pytest only exercises Tier A dry-run dedup (and related narrow paths). `compose-report` chat-print / `gh create` failure and fallback routing can regress without CI signal after harness deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stub-gh compose-report test with LARCH_STALL_RECOVERY_ENABLE_TEST_FILING=1 expecting fallback-print-required and bounded chat artifact
  - From codex-specialist-testing-output.txt: Port the old stubbed gh resolver and cross-repo helper scenarios into pytest


### FINDING_2: Tier A issue-input embeds unbounded failure-detail log
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-public-surface-output.txt
- **Severity**: important
- **Concern**: `_compose_tier_a_issue()` copies the full failure-detail log into Tier A issue input without the same size-bounded validated reader used for classification. After loose validation, large logs can be embedded verbatim (`## Validated failure-detail log`), risking memory blow-up and wider secret/path leakage into consumer-repo issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use the same size-limited validated reader as classify before appending the section
  - From cursor-specialist-edge-cases-output.txt: Bound Tier A detail-log embedding to the same 64KiB validated reader used for classification
  - From dyn-public-surface-output.txt: Add a dedicated `validate_failure_detail_log()` helper matching the documented contract (canonical, regular, non-symlink, under tmpdir, ≤65536 bytes, fail closed), use it everywhere `--failure-detail-log` / `FAILURE_DETAIL_LOG` is accepted or embedded, and add pytest cases for oversize rejection and Tier A non-embedding beyond the cap.


### FINDING_20: `normalize-issue-env` dedup/failure/outside-tmpdir paths untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `SECURITY.md` claims normalize-issue-env dedup/failure paths are tested, but only the create path exists in pytest. Partial `/larch:issue` stdout or dedup comment handling can break while docs still claim coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add pytest for dedup success, failed filing, and outside-tmpdir stdout rejection


### FINDING_24: Generic `classify()` consults attempts file without `--attempts-file`
- **Reviewer(s)**: dyn-parity-output.txt
- **Severity**: important
- **Concern**: `_classify_generic_from_terminal_state()` always resolves an attempts file (e.g., `design-failure-attempts.env`) even when `classify` is called without `--attempts-file`. Retired bash only ran the same-cause-repeat guard when the flag was explicit. Design-failure callers that `init-attempts` then `classify` without `--attempts-file` can spuriously promote to `FAILURE_CLASS=same-cause-repeat` with wrong retry policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-parity-output.txt: Match bash: only consult attempts history when `args.attempts_file` is non-empty; otherwise skip the same-cause-repeat block in the generic branch (and add a pytest case mirroring deleted bash case 7/20b).


### FINDING_25: `classify()` reads `--attempts-file` without tmpdir containment validation
- **Reviewer(s)**: dyn-parity-output.txt, dyn-cutover-output.txt
- **Severity**: important
- **Concern**: Both implement and generic `classify()` paths read `--attempts-file` (or default resolved paths) without `_validate_tmpdir_local_file` / `_validate_tmpdir_write_path` before `_latest_attempt_signature()`. Outside-tmpdir or symlinked attempts files can skew same-cause-repeat / retry-cap behavior instead of failing closed (retired harness case 13f).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-parity-output.txt: When `args.attempts_file` is set, require `_validate_tmpdir_local_file(tmpdir, Path(args.attempts_file))` and exit `1` with the legacy stderr token on failure; only run the same-cause guard when that validation passes.
  - From dyn-cutover-output.txt: Reject `--attempts-file` paths outside the implement tmpdir (and symlinks) in both `classify()` branches before reading; add pytest parity for outside-tmpdir and symlink rejection, and wire it into the `test-stall-recovery-report-*` Makefile shards.


### FINDING_26: Implement `classify()` missing `ship-pr-state.sh` symlink/malformed preflight
- **Reviewer(s)**: dyn-parity-output.txt
- **Severity**: important
- **Concern**: Implement-profile `classify()` no longer enforces the retired bash symlink/malformed `ship-pr-state.sh` preflight (harness case 21-state-symlink, exit 3). `_read_state_file()` and `_merged_state()` can read symlinked state as normal evidence, allowing classification on attacker-swapped state instead of failing closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-parity-output.txt: Before reading implement state layers, mirror bash/`clear_stall`/`seed_terminal_state`: reject symlinked or malformed `ship-pr-state.sh` (and optionally `finalize-state.sh` / `session-env.sh`) with exit `3` and no classification output.


### FINDING_28: `SECURITY.md` / relevant-check mappings overstate pytest coverage
- **Reviewer(s)**: dyn-cutover-output.txt
- **Severity**: important
- **Concern**: `SECURITY.md` and `python/checks.py` mappings claim attempts-file write containment and sanitized classification KV emission, but retired cases 13d/e/f and several filing paths lack pytest replacements after harness deletion. CI relevant-check rows can overstate what `make test-stall-recovery-report` actually guards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cutover-output.txt: Sanitize step/phase (and emit KV) on the implement path the same way as generic, or narrow `SECURITY.md` to the generic-profile guarantee; port case **13d/e/f** into `python/test_stall_recovery.py` so `python/checks.py`'s `test-stall-recovery-report` mapping matches real coverage.


### FINDING_3: `record_escalation()` does not validate ledger paths before write
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `record_escalation()` appends/writes ledger, fallback, and marker paths without `_validate_tmpdir_write_path()` (or equivalent non-symlink regular-file write guards). A symlink under the session tmpdir can redirect append/write outside the tmpdir while still reporting success, unlike the retired bash helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Call _validate_tmpdir_write_path() before append; fail closed with Tool Failure on invalid paths per bash
  - From codex-specialist-correctness-output.txt: Validate the ledger as an in-tmpdir non-symlink regular write target before appending, and degrade to fallback evidence on validation failure.
  - From codex-specialist-edge-cases-output.txt: Validate ledger, fallback, and marker paths with the tmpdir write guard before any read or write, reject symlinks/special files, and use a no-follow atomic append/write helper.
  - From codex-specialist-testing-output.txt: Validate ledger fallback and marker paths with tmpdir-local non-symlink write checks before writing and add a symlink regression test


### FINDING_4: Retired bash harness cases 7/9/13/20b not ported to pytest
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Deleted bash classifier harness scenarios (cases 7, 9, 13, 20b) were not re-homed in `python/test_stall_recovery.py`. Regressions in same-cause guard, attempts-file containment, oversize detail-log rejection, and related classify behavior can merge without CI catching Step 18a mis-routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port case7, case9, case13, and case20b scenarios into python/test_stall_recovery.py
  - From cursor-specialist-testing-output.txt: Add >64KiB classify fixture pinning ignore/reject behavior and stderr contract


### FINDING_8: Generic terminal-state validation lacks local non-symlink containment
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Generic terminal-state validation accepts allowlisted keys from a symlinked or outside-tmpdir `design-failure-terminal-state.env` without enforcing local non-symlink primary-state-file containment, unlike the retired bash helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Require _validate_tmpdir_local_file(tmpdir, state_file) before reading and add outside, relative, and symlink tests.


### FINDING_9: Implement-profile `classify()` persists unsanitized `STALL_STEP` / `PHASE` / `DISPATCHER`
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-cutover-output.txt
- **Severity**: important
- **Concern**: The implement-profile classifier persists raw `STALL_STEP`, `PHASE`, and `DISPATCHER` values to stdout and `stall-recovery-classification.env`. Values such as absolute paths or operational secrets can leak into classification artifacts, while the generic branch sanitizes and `SECURITY.md` claims sanitized emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Sanitize through _safe_step_value, _safe_phase_value, and a dispatcher allowlist helper before emitting and writing.
  - From dyn-cutover-output.txt: Sanitize step/phase (and emit KV) on the implement path the same way as generic, or narrow `SECURITY.md` to the generic-profile guarantee; port case **13d/e/f** into `python/test_stall_recovery.py` so `python/checks.py`'s `test-stall-recovery-report` mapping matches real coverage.


