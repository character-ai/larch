### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/voting.py:219-266
- **Concern**: [SCOPE-REDUCTION] Implement `voter_agreement_rows_from_tsv` as a thin wrapper over `classification_row_panel_inputs`, not a mirrored duplicate parser. Scenario: The plan adds `classification_row_panel_inputs` by mirroring compact/legacy selection inside `voter_agreement_rows_from_tsv` (`python/voting.py:219-266`) while forbidding tally behavior changes. That duplicates the highest-drift parser surface (~50 lines) and invites skew on the next compact/header tweak; ground-truth ingest would read stale rules while panel self-agreement reads updated ones.
- **Proposed resolution**: Implement `classification_row_panel_inputs` once, then rewrite `voter_agreement_rows_from_tsv` to map each prep object through `voter_agreement_row_from_panel` with identical ineligible/malformed counting. Keep existing `test_voter_agreement_rows_from_tsv_schema_shapes` as the regression guard; drop the "mirror internals" duplication instruction from the plan.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:116-129
- **Concern**: [SCOPE-REDUCTION] Drop firm `findings_ledger.py` public read API and dedicated tests. Scenario: The plan marks `findings-ledger.tsv` optional and non-authoritative, yet still firm-updates `python/findings_ledger.py` with `read_rows` / `row_signature` plus `test_findings_ledger.py` expansion. The repo has zero committed `findings-ledger.tsv` files; ground-truth calibration runs on classification TSVs, JSONL/NDJSON, and markdown. This adds ~60+ lines of public surface and maintenance without clearing the necessity gate for the diagnostic corpus.
- **Proposed resolution**: Remove `### UPDATED: python/findings_ledger.py` and `### UPDATED: python/test_findings_ledger.py` from firm scope. If ledger rows are ever present, parse inline inside `analyze_issues.py` with existing `LEDGER_COLUMNS` (optional, best-effort) without new public helpers.
