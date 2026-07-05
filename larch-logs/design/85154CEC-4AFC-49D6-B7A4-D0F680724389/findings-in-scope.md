### FINDING_1: Blank head SHA should be exercised through the real ship outcome path
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The empty-head_sha ship integration test risks passing without covering the new blank-head_sha guard in `ship_guidelines.py` if it mocks `write_guideline_ship_outcome` instead of driving the real validation path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: State explicitly: monkeypatch git.try_rev_parse (or equivalent) to return "" so compose_head_sha is blank, call the real write_guideline_ship_outcome, and assert Outcome.STALLED plus ensure_pr/flush_logs_pre not called. Do not mock write_guideline_ship_outcome for this case.

### FINDING_2: Step 8 reachability needs direct PR-evidence coverage
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The current test plan appears to cover guideline-scan regressions but not the `_scan_required` Step 8 gating path that depends on PR evidence, so a missed `pr=` regression there could escape detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add a direct `implement_step8_reachable(..., pr=...)` unit test or a `required-file-presence` regression with a `step8`-conditioned row that exercises the `_scan_required` call path with stale-bail plus manifest `pr_number` evidence.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/issue/audit_runs.py:237-274
- **Concern**: [SCOPE-REDUCTION] Drop the optional `_manifest_bail_signal` rewrite from the plan. Scenario: Finding 2 is already fixed by adding `pr: int = 0` to `implement_step8_reachable`, passing `pr` into its `_manifest_bail_signal` calls, passing `pr` from `_guideline_ship_outcome_scan_obj` and `_scan_required` step8, and forwarding the same `pr` in `implement_step9a1_reachable(..., chain=True)`. The plan’s “if needed” bullet to treat a positive CLI `pr` as standalone PR evidence would change `manifest_pr_evidence_matches` semantics and can regress `test_scan_required_bail_and_step9a1_gating`, which expects `--pr 7` without manifest `pr_number` to keep bail skip.
- **Proposed resolution**: Delete the “If needed … make `_manifest_bail_signal` treat a positive CLI `pr` as PR evidence” bullet. Keep `_manifest_bail_signal` unchanged; only thread `pr` through `implement_step8_reachable` and its call sites.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/implement/test_ship.py:6145-6167
- **Concern**: [SCOPE-REDUCTION] Drop the optional _manifest_bail_signal CLI-only PR-evidence bullet from audit_runs.py changes. Scenario: _manifest_bail_signal already forwards pr into stale_bail_heading_with_pr_evidence; FINDING_2 is fixed by threading pr through implement_step8_reachable, its _manifest_bail_signal calls, and the chained implement_step9a1_reachable fallback. Adding separate CLI-only PR evidence can make --pr 7 without manifest pr_number stop suppressing stale-bail skip and regress test_scan_required_bail_and_step9a1_gating.
- **Proposed resolution**: Delete the "If needed... treat a positive CLI pr as PR evidence" bullet. Keep only pr threading at implement_step8_reachable call sites.

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/issue/audit_runs.py:237-246
- **Concern**: [SCOPE-REDUCTION] Drop the optional `_manifest_bail_signal` CLI-only PR-evidence bullet from the plan.. Scenario: FINDING_2 is already fixed by adding `pr: int = 0` to `implement_step8_reachable`, passing `pr` into every `_manifest_bail_signal` call there, forwarding `pr` from `_guideline_ship_outcome_scan_obj` and `_scan_required`, and passing `pr` into the chained `implement_step9a1_reachable(..., chain=True)` call. `_manifest_bail_signal` already delegates to `stale_bail_heading_with_pr_evidence`, which requires a digit `manifest.pr_number`. Treating a positive CLI `--pr` as standalone evidence would change bail gating for runs with a terminal bail heading but no manifest PR (for example `test_scan_required_bail_and_step9a1_gating` expects `--pr 7` without `pr_number` to keep the bail skip).
- **Proposed resolution**: Delete the "If needed... treat a positive CLI `pr` as PR evidence" bullet from `audit_runs.py` plan steps. Thread `pr` only through the existing call sites; leave `_manifest_bail_signal` logic unchanged.

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/issue/audit_runs.py:237-274
- **Concern**: [SCOPE-REDUCTION] Drop the optional `_manifest_bail_signal` CLI-only PR-evidence bullet. Scenario: Plan still hedges with "if needed, treat a positive CLI `pr` as PR evidence" inside `_manifest_bail_signal`. Prior review showed that change is unnecessary once `pr` threads through `implement_step8_reachable` and its call sites, and it can regress `test_scan_required_bail_and_step9a1_gating`, which expects `--pr 7` without manifest `pr_number` to keep bail skip.
- **Proposed resolution**: Delete the optional `_manifest_bail_signal` rewrite from the `audit_runs.py` section. Thread `pr` only through `implement_step8_reachable`, `_guideline_ship_outcome_scan_obj`, `_scan_required` step8 handling, and the chained `implement_step9a1_reachable(..., chain=True, pr=pr)` call.
