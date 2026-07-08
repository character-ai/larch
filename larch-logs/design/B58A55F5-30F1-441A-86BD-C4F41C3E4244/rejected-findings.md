### [Plan Review] FINDING_3

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/progress_report.py:461-481
- **Concern**: [SCOPE-REDUCTION] Step 5 routes Gantt cross-vendor reconciliation through `_fallback_reconciled_manifest_label` / `_manifest_fallback_base_label`, which emit Top-reviewers human titles (e.g. `Cursor Arch`) or `(via <Tool>)` strings, not the `tool/slot` labels `_progress_label_map_from_manifests` stores (`codex/cursor-plan-arch`).. Scenario: On a plan-review phase2 row whose normalized manifest label is `codex/cursor-plan-arch` but ledger `vendor=cursor`, calling those helpers can render a human title or the wrong grammar instead of `cursor/cursor-plan-arch (via fallback)`, regressing design Gantt labels while implement voter rows (derived `codex/validity-vote`) happen to look fine.
- **Proposed resolution**: Reconcile only `tool/slot` labels: when `norm_base != raw_base` and `vendor` differs from the label's leading tool token, replace that token with `vendor`, then append ` (via fallback)`. Do not call `_manifest_fallback_base_label` or `_fallback_reconciled_manifest_label` from `_derive_progress_label`.


