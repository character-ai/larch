### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/checks.py:2177-2358
- **Concern**: [SCOPE-REDUCTION] Drop the planned `checks.py` containment helper and new lint-fix ledger tests; `_run_lint_fix_impl` already resolves `log_path` through `_resolve_checks_log_path` against `allowed_tmpdir` and only emits `ledger_failure_detail_log=str(log_path)` on `main-agent-required` when that path is a resolved absolute file under the same root passed to `record-escalation` (`checks.py:248-259`, `checks-repair-loop.md`).. Scenario: The observed `failure-detail-log-invalid` failures come from `record_escalation` hard-failing optional evidence (chiefly oversize), not from checks emitting an outside-tmpdir path. Extra `checks.py` surface and tests do not fix the stall and expand the diff beyond the bug.
- **Proposed resolution**: Limit firm file changes to `python/larch/state/stall_recovery.py`, its tests, and `python/stall-recovery-report.md`; leave `checks.py` unchanged unless implementation discovers a real containment gap.

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

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/checks.py:248-259
- **Concern**: [SCOPE-REDUCTION] Planned `checks.py` containment helper duplicates existing `_resolve_checks_log_path` gating. Scenario: Both `main-agent-required` emit sites already resolve `log_path` through `_resolve_checks_log_path` and only set `ledger_failure_detail_log=str(log_path)` when resolution succeeds; absolute resolved paths are already tmpdir-contained. The observed `failure-detail-log-invalid` failures are on the `record-escalation` validation path (chiefly oversize), not on lint-fix emitting outside paths. Adding a second helper plus new lint-fix tests expands the PR without closing a remaining bug path.
- **Proposed resolution**: Drop the `### UPDATED: python/checks.py` section and its `test_checks.py` additions; keep the fix in `stall_recovery.py` only.
