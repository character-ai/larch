### [Plan Review] FINDING_2

### FINDING_2: accepted_reverted_or_regressed must require reversal/regression language in later evidence
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: `accepted_reverted_or_regressed` must require reversal or regression language on later evidence, not step-6 path/title overlap alone. Ground-truth semantics require later text with reversal or regression language before a decisive contradicting bucket, but steps 6–7 use generic overlap matchers and step 7 buckets `accepted_reverted_or_regressed` from any later match without binding to `wasteful_findings`'s `reversal_re` (`python/analyze_issues.py:471-474`) or an equivalent regression-language check. A later issue with overlapping path/title but no revert wording can be scored decisive, inflating `false_positive_yes` / `false_negative_no` and deflating per-voter `realized_alignment_rate`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In step 7 (and step 6 if shared), gate `accepted_reverted_or_regressed` on later issue/finding text matching `wasteful_findings`'s `reversal_re` (`python/analyze_issues.py:471-474`) or equivalent regression tokens already used in `CATEGORY_PATTERNS`; path/title overlap alone stays non-decisive. Add a test where overlap exists without reversal language and assert no decisive revert bucket.
  - From Cursor-Innovation: In step 7 accepted branch, require decisive `accepted_reverted_or_regressed` only when later issue/finding text matches a hoisted shared `reversal_re` (same pattern as `wasteful_findings`) or contains an explicit regression/reversal token from the Bug-fix category rules; keep step 6 overlap as a prerequisite only. Add a negative fixture where path/title overlap without reversal/regression language stays non-decisive.
  - From Cursor-Pragmatic: In step 7, gate `accepted_reverted_or_regressed` on later evidence passing `wasteful_findings`'s `reversal_re` and/or `default_category` regression tokens (reuse `python/analyze_issues.py:471-474` / `CATEGORY_PATTERNS`), in addition to temporal ordering; keep step 6 overlap helpers for `rejected_resurfaced` only.
  - From Cursor-Requirements: In step 7, require later issue/finding prose to match `reversal_re` (or the same regression/revert token set used in semantics) before `accepted_reverted_or_regressed`; keep step-6 path/title overlap as necessary but not sufficient signals. Add a regression test where path overlap exists but later text lacks revert/regression wording and assert the row stays non-decisive.


### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/voting.py:219-266
- **Concern**: [SCOPE-REDUCTION] Implement `voter_agreement_rows_from_tsv` as a thin wrapper over `classification_row_panel_inputs`, not a mirrored duplicate parser. Scenario: The plan adds `classification_row_panel_inputs` by mirroring compact/legacy selection inside `voter_agreement_rows_from_tsv` (`python/voting.py:219-266`) while forbidding tally behavior changes. That duplicates the highest-drift parser surface (~50 lines) and invites skew on the next compact/header tweak; ground-truth ingest would read stale rules while panel self-agreement reads updated ones.
- **Proposed resolution**: Implement `classification_row_panel_inputs` once, then rewrite `voter_agreement_rows_from_tsv` to map each prep object through `voter_agreement_row_from_panel` with identical ineligible/malformed counting. Keep existing `test_voter_agreement_rows_from_tsv_schema_shapes` as the regression guard; drop the "mirror internals" duplication instruction from the plan.


### [Plan Review] FINDING_5

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:116-129
- **Concern**: [SCOPE-REDUCTION] Drop firm `findings_ledger.py` public read API and dedicated tests. Scenario: The plan marks `findings-ledger.tsv` optional and non-authoritative, yet still firm-updates `python/findings_ledger.py` with `read_rows` / `row_signature` plus `test_findings_ledger.py` expansion. The repo has zero committed `findings-ledger.tsv` files; ground-truth calibration runs on classification TSVs, JSONL/NDJSON, and markdown. This adds ~60+ lines of public surface and maintenance without clearing the necessity gate for the diagnostic corpus.
- **Proposed resolution**: Remove `### UPDATED: python/findings_ledger.py` and `### UPDATED: python/test_findings_ledger.py` from firm scope. If ledger rows are ever present, parse inline inside `analyze_issues.py` with existing `LEDGER_COLUMNS` (optional, best-effort) without new public helpers.


