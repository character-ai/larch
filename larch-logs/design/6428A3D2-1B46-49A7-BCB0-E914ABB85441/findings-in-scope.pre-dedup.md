### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/checks.py:2177-2358
- **Concern**: [SCOPE-REDUCTION] Drop the planned `checks.py` containment helper and new lint-fix ledger tests; `_run_lint_fix_impl` already resolves `log_path` through `_resolve_checks_log_path` against `allowed_tmpdir` and only emits `ledger_failure_detail_log=str(log_path)` on `main-agent-required` when that path is a resolved absolute file under the same root passed to `record-escalation` (`checks.py:248-259`, `checks-repair-loop.md`).. Scenario: The observed `failure-detail-log-invalid` failures come from `record_escalation` hard-failing optional evidence (chiefly oversize), not from checks emitting an outside-tmpdir path. Extra `checks.py` surface and tests do not fix the stall and expand the diff beyond the bug.
- **Proposed resolution**: Limit firm file changes to `python/larch/state/stall_recovery.py`, its tests, and `python/stall-recovery-report.md`; leave `checks.py` unchanged unless implementation discovers a real containment gap.



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



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/checks.py
- **Concern**: [SCOPE-REDUCTION] Firm checks.py containment helper and new lint-fix ledger tests duplicate existing _resolve_checks_log_path gating on both main-agent-required return sites. Scenario: The observed production failure is record-escalation hard-failing on oversize optional evidence; lint-fix already resolves an absolute path under allowed_tmpdir before emitting ledger_failure_detail_log, so extra checks.py surface and tests expand the PR without closing the stall-recovery defect
- **Proposed resolution**: Limit firm scope to stall_recovery.py (and its tests/docs); drop the ### UPDATED: python/checks.py block unless a concrete remaining path is shown that emits an outside-tmpdir ledger_failure_detail_log after _resolve_checks_log_path



### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/state/stall_recovery.py:903-945
- **Concern**: [SCOPE-REDUCTION] Oversize `record-escalation` evidence does not need a tmpdir-local sidecar.. Scenario: The feature is complete once oversize logs stop aborting the ledger and record a specific skip token. Truncation copies, no-follow reads, digest naming, and sidecar-specific tests add a new file I/O path without changing the success or failure contract.
- **Proposed resolution**: For oversize input, record a skip token and leave `failure_detail_log` empty. Drop the sidecar helper, the sidecar tests, and the doc text that promises truncated attachment.



### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/checks.py:248-259,2177-2248,2342-2358
- **Concern**: [SCOPE-REDUCTION] The lint-fix containment rewrite is already implemented in current code.. Scenario: `_resolve_checks_log_path` already canonicalizes `allowed_root` and rejects paths outside it, and both `main-agent-required` return sites emit `ledger_failure_detail_log` from that validated path. Reworking `checks.py` does not fix the `record-escalation` defect and only widens the patch surface.
- **Proposed resolution**: Leave `checks.py` unchanged unless you can point to a concrete outside-tmpdir emission path that still exists after the stall-recovery fix.



### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/checks.py:2177-2248
- **Concern**: [SCOPE-REDUCTION] Planned `checks.py` containment helper and new tests duplicate existing `_resolve_checks_log_path` gating on both `main-agent-required` return sites.. Scenario: Both branches already resolve `log_path` through `_resolve_checks_log_path(candidate=checks_log, allowed_root=allowed_root)` and only emit `ledger_failure_detail_log=str(log_path)` after that returns a canonical absolute path under `allowed_root`, which matches `--implement-tmpdir` in normal `/implement` flows. The observed `failure-detail-log-invalid` failures come from `record-escalation` hard-failing optional evidence (likely oversize), not from outside-tmpdir emission in `checks.py`. Adding another helper and tests here expands the diff without closing a remaining bug path.
- **Proposed resolution**: Limit firm file changes to `python/larch/state/stall_recovery.py`, its tests, and `python/stall-recovery-report.md`. Drop the `### UPDATED: python/checks.py` and `python/test_checks.py` sections unless a reproduction shows `ledger_failure_detail_log` escaping containment today. ### FINDING_1 — [SCOPE-REDUCTION] `checks.py` changes duplicate existing containment (`architecture`, `python/checks.py:2177-2248`) **Concern:** The plan adds a new containment helper and lint-fix ledger tests in `checks.py`, but both `main-agent-required` return paths already gate on `_resolve_checks_log_path` and only emit `str(log_path)` after resolution succeeds. **Scenario:** The 5/100 run failures are `record-escalation` rejecting optional `--failure-detail-log` (most likely oversize per issue hypothesis A). `checks.py` already emits tmpdir-contained absolute paths when `allowed_root` aligns with `--implement-tmpdir`. Extra `checks.py` work adds ~60+ lines and tests without fixing the stall-recovery hard-fail. **Suggested revision:** Remove `### UPDATED: python/checks.py` and the matching `python/test_checks.py` section from the firm plan. Keep the fix in `stall_recovery.py` only unless you can reproduce an outside-tmpdir `ledger_failure_detail_log` on HEAD. --- **Note on prior ledger:** Round 2 accepted FINDING_4 (canonical-ledger fallback) looks addressed by the plan’s explicit “do not change fallback success path” bullets. Round 2 neutral FINDING_3 (missing valid attach test) and rejected/neutral sidecar and race items are not re-raised here.



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



### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/checks.py:248-259
- **Concern**: [SCOPE-REDUCTION] Planned `checks.py` containment helper duplicates existing `_resolve_checks_log_path` gating. Scenario: Both `main-agent-required` emit sites already resolve `log_path` through `_resolve_checks_log_path` and only set `ledger_failure_detail_log=str(log_path)` when resolution succeeds; absolute resolved paths are already tmpdir-contained. The observed `failure-detail-log-invalid` failures are on the `record-escalation` validation path (chiefly oversize), not on lint-fix emitting outside paths. Adding a second helper plus new lint-fix tests expands the PR without closing a remaining bug path.
- **Proposed resolution**: Drop the `### UPDATED: python/checks.py` section and its `test_checks.py` additions; keep the fix in `stall_recovery.py` only.



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



