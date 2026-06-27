### OOS_1: [OUT_OF_SCOPE] Plan implementation matches optional-evidence stall-recovery contract
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: The change implements the plan: `record-escalation` no longer hard-fails on optional `--failure-detail-log` validation misses; it records specific `detail_log_skipped=failure-detail-log-<cause>` tokens or attaches a truncated sidecar and returns `0`. Generic `failure-detail-log-invalid` is removed from the `record-escalation` path. `classify` / `compose-report` still use `validate_failure_detail_log` soft-skip with byte-compatible stderr (`outside implement tmpdir`, `exceeds 64KiB`). `checks.py` both `main-agent-required` return sites use `ledger_log_path` from `_resolve_ledger_failure_detail_log_path`; outside logs fail closed with `checks-log-invalid` and empty `ledger_failure_detail_log`. Oversize logs truncate via `_materialize_truncated_failure_detail_log` (Hypothesis A). `_resolve_ledger_failure_detail_log_path` plus the existing `allowed_tmpdir` gate keeps emitted ledger paths under the same tmpdir `record-escalation` validates (Hypothesis B). Canonical-ledger `OSError` fallback is unchanged. Tests cover non-fatal misses, oversize truncation, truncate failure, and nonwritable-ledger fallback; `test_checks.py` assertions updated for resolved paths. `python/stall-recovery-report.md` contract updated.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] Missing record-escalation success test at exact evidence cap
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: `python/test_stall_recovery.py` — No dedicated `record-escalation` success test asserts a valid in-tmpdir detail log (especially at exactly `MAX_OPTIONAL_EVIDENCE_BYTES`) attaches a tmpdir-relative `failure_detail_log` with no `detail_log_skipped`. Oversize sidecar coverage exercises attachment plumbing; the direct-attach happy path is untested. Coverage polish, not a feature blocker under the acceptance rubric.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add one `record_escalation_main` success case at the cap and optionally one below-cap control.

### OOS_3: [OUT_OF_SCOPE] Fallback TSV path does not assert detail_log_skipped propagation
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `python/test_stall_recovery.py:1531-1550` — `test_record_escalation_nonwritable_ledger_writes_fallback` does not pass `--failure-detail-log` or assert `detail_log_skipped` propagates into fallback TSV when canonical append fails. Row is built before the `try`/`except`, so behavior is likely correct but unverified on the fallback path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Extend the test with an invalid or oversize detail log and assert the fallback row carries the same skip/attach fields.

### OOS_4: [OUT_OF_SCOPE] record-escalation skip path omits live stderr diagnostics
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: `python/larch/state/stall_recovery.py:966-983` — `_resolve_detail_log` classifies skips without calling `_emit_failure_detail_log_message`, so live stderr diagnostics for skip reasons appear only on `classify` / `compose-report`, not on `record-escalation`. The plan targets ledger `detail_log_skipped` tokens as the run-visible contract; stderr on the record path was not required.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_5: [OUT_OF_SCOPE] Redundant second resolve in checks.py is belt-and-suspenders only
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-evidence-paths
- **Severity**: nit
- **Concern**: `python/larch/implement/checks.py:2211-2224` — `_resolve_ledger_failure_detail_log_path` re-resolves against the same `allowed_root` already used for `log_path`; in current call geometry it cannot fail independently of the first `_resolve_checks_log_path` except on a concurrent delete/symlink swap between two synchronous calls. Plan-required defense-in-depth; the race window is pre-existing and not introduced by this diff's core fix. The added `checks-log-invalid` guard and tests correctly stop outside-tmpdir ledger emission at the lint-fix source.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: None required for merge; drop the second resolve if you want less duplication later.

### OOS_6: [OUT_OF_SCOPE] record-escalation trusts --implement-tmpdir without local-file validation
- **Reviewer(s)**: dyn-dyn-evidence-paths
- **Severity**: nit
- **Concern**: `python/larch/state/stall_recovery.py:985-1011` — `record_escalation` still trusts `--implement-tmpdir` without `_validate_tmpdir_local_file`-style validation used elsewhere in the module. That predates this branch; the new optional-evidence path inherits the same assumption that the orchestrator passes a trusted session tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_7: [OUT_OF_SCOPE] stat() symlink-following window can leak external metadata
- **Reviewer(s)**: dyn-dyn-evidence-paths
- **Severity**: nit
- **Concern**: `python/larch/state/stall_recovery.py:239-250` — `_stat_and_open_check` uses `path.stat()` with default symlink following between the earlier `path.is_symlink()` gate and the later `O_NOFOLLOW` open. A swap to a symlink in that window can leak external file metadata via `stat()` even though attachment is blocked later. This pattern existed in the old validator; the refactor preserves it rather than introducing it.
- **Suggested revisions (informational for voters; coder decides)**:

