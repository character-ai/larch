# Review Round 2

- Mode: `diff`
- 15 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: _classify_text() step 3/6 precedence vs bash
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-parity-output.txt
- **Severity**: important
- **Concern**: `_classify_text()` scans pytest/lint evidence before applying bash step-prefix guards. For `STALL_STEP` 3 or 6 with pytest or lint text in evidence, Python classifies as `test-failure` or `lint-failure` instead of `contract-failure`, diverging from retired `classify_from_evidence()` and harness cases 5a/5b.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port bash step 3|6 and merge-loop-iteration-cap handling to the top of classification
  - From dyn-parity-output.txt: Move the `step in {"3", "6"}` branch to the top of `_classify_text()` (immediately after the `rebase-failed` guard), matching bash ordering, and add pytest coverage for step 3/6 with pytest/lint evidence present.


### FINDING_11: test_init_attempts_rejects_outside_tmpdir uncovered by shard -k filters
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-cutover-output.txt
- **Severity**: important
- **Concern**: `test_init_attempts_rejects_outside_tmpdir` is not selected by any `test-stall-recovery-report-{1,2,3}` `-k` filter while `python/test_stall_recovery.py` is ENFORCED for strict partition. `test_normalize_issue_env_dedup_success` is double-covered across shards. `make test-harness-shards-coverage` / `make lint` partition guard fails; the new attempts-file containment case may never run in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add init_attempts to shard-1 -k expression or rename test to match an existing keyword then re-run make test-harness-shards-coverage
  - From dyn-cutover-output.txt: Extend shard 1 with `init_attempts` (e.g. `... or record_attempt or init_attempts`) and remove the overlap by narrowing one selector (e.g. use `normalize_issue_env` instead of broad `normalize_issue`, or drop `dedup` from shard 2 for that test). Re-run the partition guard to confirm full=union.


### FINDING_12: record-escalation non-writable ledger fallback untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Retired bash case 23 asserted non-writable canonical ledger fallback after `plan_review.py` in-process cutover. Step 3 escalation evidence could silently stop writing fallback rows on degraded ledger chmod failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add test with non-writable ledger asserting ESCALATION_RECORDED=false ESCALATION_FALLBACK_WRITTEN=true exit 0


### FINDING_16: Tier B sensitive-token allowlist incomplete for classification enums
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `_sensitive_value_is_allowlisted` does not allowlist all enum values the Python port generates. Generic classification can write `DISPATCHER=design-step3-review` and classifier patterns such as `dispatch-bail-token` in the chat-print body. `build_sensitive_corpus_from_evidence` then treats those class-file values as sensitive, so `compose-report --surface chat-print` can fail for valid `/design` or dispatch-bail reports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: In `_sensitive_value_is_allowlisted`, also allow `_safe_token("source-script", value, generic=True)` and `_safe_matched_pattern_value(value) != "redacted"`, or add the full dispatcher and matched-pattern enum set used by classification.


### FINDING_17: _latest_attempt_signature() last_signature fallback breaks bash parity
- **Reviewer(s)**: dyn-parity-output.txt
- **Severity**: important
- **Concern**: `_latest_attempt_signature()` falls back to `last_signature` when `attempt.${count}.signature` is empty. Retired bash only reads `attempt.${count}.signature`. A partially written or legacy attempts file with populated `last_signature` but missing indexed row can promote `same-cause-repeat` in Python when bash would not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-parity-output.txt: Drop the `last_signature` fallback so parity matches bash and same-cause detection keys only off `attempt.${attempt_count}.signature`.


### FINDING_2: implement classify() uses _classify_text hints instead of resume_hint_for()
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-parity-output.txt
- **Severity**: important
- **Concern**: On the implement profile, `classify()` builds `FAILURE_SIGNATURE` and emits `RESUME_HINT` from `_classify_text()` hint tuples. Bash computes both from `resume_hint_for(failure_class, stall_step, phase)` after classification. They diverge when class and step disagree (e.g. `test-failure` at step 8 yields `step2-impl` in Python vs `step8-shippr` in bash), breaking same-cause-repeat detection vs bash-recorded attempts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add _resume_hint_for(class, step, phase) and use it after classification
  - From dyn-parity-output.txt: Port `resume_hint_for()` (bash lines 672–696) and use it for signature hashing and `RESUME_HINT` emission on the implement profile path; keep `_classify_text()` for class/pattern only.


### FINDING_20: _redact_text() fail-open on missing/failed redactor
- **Reviewer(s)**: dyn-public-surface-output.txt
- **Severity**: important
- **Concern**: `_redact_text()` returns original text unchanged when `python/cli.py` is missing or `redact secrets` exits non-zero. Retired bash `redact_to_file()` was fail-closed. Tier A issue-input bodies, Tier A escalation/root-cause slices, and Tier B chat-print bodies depend on this helper before upstream filing; redactor failure can publish session evidence without the secrets-family backstop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-public-surface-output.txt: Mirror bash fail-closed behavior: if the redactor is missing or returns non-zero, abort `compose_report` (and any other publish path) with a non-zero exit and fallback-print status instead of writing or filing unredacted content.


### FINDING_21: populate_sensitive_corpus() lacks tmpdir containment on output path
- **Reviewer(s)**: dyn-public-surface-output.txt
- **Severity**: important
- **Concern**: `populate_sensitive_corpus()` writes the rebuilt effective sensitive corpus to `--sensitive-corpus-file` with no tmpdir containment check. Retired bash required `validate_tmpdir_write_file`. Out-of-tmpdir destination can persist plan text, session state, execution issues, URLs, and absolute paths outside the session boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-public-surface-output.txt: Reject unless `_validate_tmpdir_write_path(tmpdir, sensitive_file)` passes before writing; return exit `1` with the same `--sensitive-corpus-file outside implement tmpdir` grammar used elsewhere.


### FINDING_22: dedup_tier_a_report() omits --body-file tmpdir validation
- **Reviewer(s)**: dyn-public-surface-output.txt
- **Severity**: important
- **Concern**: `dedup_tier_a_report()` no longer validates that `--body-file` resolves under `--implement-tmpdir`. Retired bash enforced `validate_tmpdir_local_file`. Mistyped or adversarial CLI invocation can point dedup at another session’s issue-input artifact, breaking the session-scoped containment contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-public-surface-output.txt: Call `_validate_tmpdir_local_file(tmpdir, body_file)` (and the same for optional slice overrides) before invoking `file-failure-report-cross-repo.sh`; fail closed with exit `1` when validation fails.


### FINDING_23: public-surface redaction harness cases 13/16/23 not ported to pytest
- **Reviewer(s)**: dyn-public-surface-output.txt
- **Severity**: important
- **Concern**: Retired bash harness asserted `ghp_` tokens stay out of Tier B public outputs (case 13), redactor strips them from composed bodies (case 16), and Tier A redacts raw bail text containing secrets (case 23). Those scenarios were deleted and are not replaced by equivalent pytest coverage while `docs/linting.md` still claims public-surface sentinel redaction is exercised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-public-surface-output.txt: Port cases 13, 16, and 23 into `python/test_stall_recovery.py` (compose-report Tier B, `_redact_text` failure/missing-redactor paths, and Tier A `BAIL_REASON_RAW` handling) and wire them into the `test-stall-recovery-report-{1,2,3}` pytest shards.


### FINDING_3: dispatch-failure bail token set incomplete vs bash
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-parity-output.txt
- **Severity**: important
- **Concern**: Dispatch-failure classification recognizes only four bail/evidence substrings. Bash used a closed bail-token list (`branch-changed`, `manifest-missing`, `cursor-runtime-failure`, and others). Stalls with allowlisted bail reasons but without those four literals fall through to `unrecoverable`/`fallback` in Python, changing retry policy and report classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port bash dispatch bail case list and envelope evidence grep
  - From dyn-parity-output.txt: Add a bail-token set matching bash’s dispatch case (lines 756–760 in the retired script) and evaluate it on the bail field before the generic fallback.


### FINDING_4: init_attempts() omits ATTEMPTS_FILE and ATTEMPT_COUNT KVs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `init_attempts()` does not emit `ATTEMPTS_FILE` and `ATTEMPT_COUNT` stdout KVs on successful init. Callers expecting the bash KV envelope get silent success on re-init.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Emit ATTEMPTS_FILE and ATTEMPT_COUNT on every successful init


### FINDING_5: REPORT_DEDUP_SIGNATURE behavioral tests not ported
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Retired bash cases 24/25 asserted `REPORT_DEDUP_SIGNATURE` stability and profile separation (implement vs design). Pytest only checks key presence. Implement and design reports could share signatures or regress Tier B exact-marker dedup without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add pytest comparing implement vs design-failure dedup signatures
  - From cursor-specialist-testing-output.txt: Add pytest fixtures asserting signature stability across excluded fields changes with bail token and differs across generic vs implement profiles


### FINDING_8: record_escalation writes unsanitized dispatcher/exit_code to TSV
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `record_escalation` writes unsanitized `dispatcher` and `exit_code` to the escalation ledger TSV. Deleted bash sanitized both. Tab or newline in dispatcher breaks TSV parsing; Tier A issue bodies embed raw ledger rows and may leak path-like dispatcher values into filed issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Sanitize dispatcher via _safe_dispatcher_value and exit_code via the classify numeric/unknown guard before formatting the row; add pytest for metacharacter dispatcher input


### FINDING_9: record_escalation hard-fail paths omit execution-issues Tool Failure marker
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-cutover-output.txt
- **Severity**: important
- **Concern**: Retiring `stall-recovery-report.sh` removed bash-side `write_record_escalation_tool_failure()` on hard-fail paths. Native `record_escalation()` prints stderr and returns `1` without tagging `execution-issues.md` on ledger validation failure, invalid tokens, invalid detail log, etc. `/implement` Step 5 is covered via `review_and_fix.py`, but `/design` cutovers (`plan_review.py`, `review-design-step3-loop.sh`, `design-step-validator-autofix.sh`) only WARN or ignore non-zero exit. Failed design escalation can lose both ledger rows and the evidence marker, so approved-run escalation-success reporting may skip with `no-escalation-evidence`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Write Tool Failure to execution-issues.md on ledger validation failure before return 1; assert in test_record_escalation_rejects_symlink_ledger
  - From dyn-cutover-output.txt: Restore bash-parity tool-failure writes inside `record_escalation()` for validation/hard-fail paths (using the shared append helper), or make every caller mirror `review_and_fix._append_record_escalation_tool_failure()` on non-zero exit; add pytest coverage for the design-failure evidence gate when ledger write fails closed.


