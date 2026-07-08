### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/progress_report.py:461-481
- **Concern**: [SCOPE-REDUCTION] Step 5 routes Gantt cross-vendor reconciliation through `_fallback_reconciled_manifest_label` / `_manifest_fallback_base_label`, which emit Top-reviewers human titles (e.g. `Cursor Arch`) or `(via <Tool>)` strings, not the `tool/slot` labels `_progress_label_map_from_manifests` stores (`codex/cursor-plan-arch`).. Scenario: On a plan-review phase2 row whose normalized manifest label is `codex/cursor-plan-arch` but ledger `vendor=cursor`, calling those helpers can render a human title or the wrong grammar instead of `cursor/cursor-plan-arch (via fallback)`, regressing design Gantt labels while implement voter rows (derived `codex/validity-vote`) happen to look fine.
- **Proposed resolution**: Reconcile only `tool/slot` labels: when `norm_base != raw_base` and `vendor` differs from the label's leading tool token, replace that token with `vendor`, then append ` (via fallback)`. Do not call `_manifest_fallback_base_label` or `_fallback_reconciled_manifest_label` from `_derive_progress_label`.

### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/report/progress_report.py:561-568
- **Concern**: [SCOPE-REDUCTION] Plain retry rows are treated as vendor fallbacks. Scenario: The plan uses norm_base != raw_base as the fallback predicate, but _progress_normalize_output_base also strips -retry. Existing timing ledgers contain phase1 retry rows such as cursor-plan-requirements-output-ns-retry.txt; the proposed path would normalize that to cursor-plan-requirements-output-ns.txt, append (via fallback), and reserve it under the cap even though no phase2 or phase3 vendor fallback ran.
- **Proposed resolution**: Use a separate chart fallback predicate that requires a stripped -phase2 or -phase3 suffix. Keep plain -retry and -ns-retry rows on the existing raw-label path, and add a focused regression case for a phase1 retry row with no fallback suffix.
