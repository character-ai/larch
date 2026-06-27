### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_stall_recovery.py
- **Concern**: `record-escalation` test plan covers only skip, oversize-sidecar, and truncate-failure paths; it never exercises the new classifier success branch that attaches a valid tmpdir-local log (including the `MAX_OPTIONAL_EVIDENCE_BYTES` exact-cap boundary called out in plan edge cases).. Scenario: There is currently no `record_escalation_main(... --failure-detail-log ...)` success test at all. A refactor that misclassifies valid logs (for example off-by-one at 64KiB) can still return `0` but write an empty `failure_detail_log` or an unnecessary sidecar, silently dropping the lint-fix evidence the bug is meant to preserve when attachable.
- **Proposed resolution**: Add one success test: valid absolute log under tmpdir at exactly `MAX_OPTIONAL_EVIDENCE_BYTES` asserts rc `0`, no `detail_log_skipped`, tmpdir-relative `failure_detail_log` in the ledger row, and no `Tool Failure: record-escalation`. Optionally add one below-cap control case.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_stall_recovery.py
- **Concern**: Proposed tests cover only skip, oversize, and truncate-failure paths for record-escalation detail logs. Scenario: After the classifier and soft-skip refactor, a regression on the primary success path (valid absolute tmpdir-local file at or under MAX_OPTIONAL_EVIDENCE_BYTES) could drop failure_detail_log from the ledger row or mis-handle the exact 65536-byte boundary while every planned test still passes
- **Proposed resolution**: Add one record-escalation success test with a tmpdir-local log at MAX_OPTIONAL_EVIDENCE_BYTES (and optionally one byte under) asserting rc=0, failure_detail_log set to the expected tmpdir-relative path, detail_log_skipped absent, and no Tool Failure entry

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: python/larch/state/stall_recovery.py
- **Concern**: Oversize sidecar materialization specifies no-follow reads for the source but not for the destination file create/write. Scenario: If a symlink already exists at the planned sidecar path under tmpdir, a plain write can follow it and place truncated evidence outside --implement-tmpdir before post-write revalidation; revalidation may then skip attachment but the out-of-tmpdir write already occurred
- **Proposed resolution**: Open/create the sidecar destination with O_NOFOLLOW (and O_CREAT|O_EXCL when the digest name must be new) or an equivalent fd-based write that refuses symlinks, then re-verify with fstat before recording the relative path

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/state/stall_recovery.py:877-941
- **Concern**: Deterministic oversize sidecar naming can reuse stale evidence. Scenario: Two oversize logs from the same source path and byte size can map to the same tmpdir sidecar. A later escalation can silently attach an older truncation instead of the current failure log.
- **Proposed resolution**: Create each sidecar with a per-escalation unique temp name and atomic rename, or include a content hash plus nonce so the attachment path cannot be reused across runs.

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/state/stall_recovery.py:928-942
- **Concern**: Fallback write-time failures are still uncaught. Scenario: After canonical append fails, a permission flip, disk-full error, or other OSError during `marker.write_text` or `fallback.write_text` can still escape instead of being converted into a controlled hard_fail. That loses the escalation record on the recovery path.
- **Proposed resolution**: Wrap the marker and fallback writes in their own OSError handling and hard_fail on write failure, while keeping the existing return-0 success path when both writes succeed.

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_stall_recovery.py
- **Concern**: Test plan omits the valid tmpdir-local attach success path (including the `MAX_OPTIONAL_EVIDENCE_BYTES` boundary). Scenario: Proposed `record-escalation` tests cover only skip, oversize, and truncate-failure cases. The issue still requires accepting a valid lint-fix detail log and attaching a tmpdir-relative path. A regression in the classifier `""` success branch, or an off-by-one at the 64KiB cap, could drop good evidence while all planned tests still pass.
- **Proposed resolution**: Add `record-escalation` tests: (a) valid log under cap attaches a tmpdir-relative `failure_detail_log`, returns `0`, and leaves `detail_log_skipped` empty; (b) log exactly `MAX_OPTIONAL_EVIDENCE_BYTES` attaches directly with no sidecar. ### FINDING 1 — `[SCOPE-REDUCTION]` `checks.py` rewrite is unnecessary (risk-integration) **Location:** `python/checks.py:248-259`, `python/checks.py:2248-2358` `_run_lint_fix_impl` already resolves `allowed_root` from `allowed_tmpdir`, rejects mismatched `run_parent`, and assigns `ledger_failure_detail_log` only from `_resolve_checks_log_path`, which returns a canonical absolute path under that root. The bug is `record_escalation` hard-failing optional evidence (especially oversize), not lint-fix emitting bad paths. Drop the planned `checks.py` and related `test_checks.py` work. ### FINDING 2 — Test plan omits valid attach success path (correctness) **Location:** `python/test_stall_recovery.py` The plan’s new `record-escalation` cases exercise skips and oversize handling only. The spec still requires accepting a valid detail log. Add success-path coverage for a normal under-cap log and for a file exactly at `MAX_OPTIONAL_EVIDENCE_BYTES`, asserting `rc == 0`, a populated tmpdir-relative `failure_detail_log`, and no `detail_log_skipped`. **Note:** Round-2 FINDING_4 (canonical-ledger fallback regression) looks addressed by the plan’s explicit preservation of the existing `try`/`except OSError` fallback path and `test_record_escalation_nonwritable_ledger_writes_fallback`; not re-raised.

### FINDING_13:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:77-95
- **Concern**: Missing positive-path `record-escalation` test for a valid tmpdir-local `--failure-detail-log`.. Scenario: The plan only exercises invalid, oversize, and fallback cases, so a regression that still hard-fails or drops an attachable log, including the exact `MAX_OPTIONAL_EVIDENCE_BYTES` boundary the edge cases call out, would slip through.
- **Proposed resolution**: Add one targeted test that passes a valid tmpdir-local detail log, ideally at the size cap, and asserts return code 0, a ledger row with a tmpdir-relative `failure_detail_log`, no `detail_log_skipped`, and no `Tool Failure: record-escalation`.
