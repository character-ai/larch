### FINDING_1: Design panel_verdict must bind from round-local plan-review markdown
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Design `panel_verdict` must bind from round-local plan-review markdown, not run-root cumulative files. Committed design runs can store different finding sets under `plan-review/round-N/accepted-plan-findings.md` vs run-root `accepted-plan-findings.md` (same `FINDING_<n>` id, different concerns). Step 5 says read same-round markdown first but never pins `plan-review/round-{round_num}/` ahead of run-root files. An implementer can membership-test run-root markdown for a `plan-review/round-N/findings-classification.tsv` row, mis-bind `panel_verdict`, and poison prose join plus the gated later accepted-finding index; on a large committed corpus this can invert decisive YES/NO alignment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In step 5 (and Ground-truth semantics panel-verdict binding), require design verdict membership from `plan-review/round-{round_num}/accepted-plan-findings.md` and `rejected-findings.md` derived from the classification TSV path; consult run-root markdown only when that round-local pair is absent. Treat run-root vs round-local disagreement as weak/non-decisive. Add a regression fixture where round-1 TSV `FINDING_1` is accepted in round-local markdown but absent or different at run root.
  - From Cursor-Pragmatic: In step 5 Design prose binding, require path order: for a TSV at `.../plan-review/round-N/findings-classification.tsv`, read `.../plan-review/round-N/accepted-plan-findings.md` and `.../rejected-findings.md` first (index `### FINDING_<n>:` membership), then fall back to run-root markdown only when round-local files are absent; treat run-root vs round-local disagreement as weak/non-decisive.

### FINDING_2: accepted_reverted_or_regressed must require reversal/regression language in later evidence
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: `accepted_reverted_or_regressed` must require reversal or regression language on later evidence, not step-6 path/title overlap alone. Ground-truth semantics require later text with reversal or regression language before a decisive contradicting bucket, but steps 6–7 use generic overlap matchers and step 7 buckets `accepted_reverted_or_regressed` from any later match without binding to `wasteful_findings`'s `reversal_re` (`python/analyze_issues.py:471-474`) or an equivalent regression-language check. A later issue with overlapping path/title but no revert wording can be scored decisive, inflating `false_positive_yes` / `false_negative_no` and deflating per-voter `realized_alignment_rate`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In step 7 (and step 6 if shared), gate `accepted_reverted_or_regressed` on later issue/finding text matching `wasteful_findings`'s `reversal_re` (`python/analyze_issues.py:471-474`) or equivalent regression tokens already used in `CATEGORY_PATTERNS`; path/title overlap alone stays non-decisive. Add a test where overlap exists without reversal language and assert no decisive revert bucket.
  - From Cursor-Innovation: In step 7 accepted branch, require decisive `accepted_reverted_or_regressed` only when later issue/finding text matches a hoisted shared `reversal_re` (same pattern as `wasteful_findings`) or contains an explicit regression/reversal token from the Bug-fix category rules; keep step 6 overlap as a prerequisite only. Add a negative fixture where path/title overlap without reversal/regression language stays non-decisive.
  - From Cursor-Pragmatic: In step 7, gate `accepted_reverted_or_regressed` on later evidence passing `wasteful_findings`'s `reversal_re` and/or `default_category` regression tokens (reuse `python/analyze_issues.py:471-474` / `CATEGORY_PATTERNS`), in addition to temporal ordering; keep step 6 overlap helpers for `rejected_resurfaced` only.
  - From Cursor-Requirements: In step 7, require later issue/finding prose to match `reversal_re` (or the same regression/revert token set used in semantics) before `accepted_reverted_or_regressed`; keep step-6 path/title overlap as necessary but not sufficient signals. Add a regression test where path overlap exists but later text lacks revert/regression wording and assert the row stays non-decisive.

### FINDING_3: OOS rows need explicit accepted/rejected panel verdict binding before scoring
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: OOS routed rows have no pinned accepted/rejected panel verdict source before scoring. Committed implement JSONL stores OOS records with `outcome=out_of_scope` for both accepted and rejected OOS rows, while the TSV/prose vote tally carries accepted vs rejected. The plan says implement `panel_verdict` comes from JSONL outcome and TSV `voting_result` is only for parsing, then step 8 scores each OOS classification row. An implementer can drop accepted OOS rows as non-accepted or score rejected OOS rows against docked filed issues, corrupting `realized_alignment_rate`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: In the OOS branch, bind OOS acceptedness explicitly from the classification TSV voting_result after eligibility plus MAV checks or from the parsed Vote tally Result, and restrict decisive OOS fate scoring to OOS rows whose bound OOS panel result is accepted; rejected, neutral, exonerated, or disagreement rows stay non-decisive.
```

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/voting.py:219-266
- **Concern**: [SCOPE-REDUCTION] Implement `voter_agreement_rows_from_tsv` as a thin wrapper over `classification_row_panel_inputs`, not a mirrored duplicate parser. Scenario: The plan adds `classification_row_panel_inputs` by mirroring compact/legacy selection inside `voter_agreement_rows_from_tsv` (`python/voting.py:219-266`) while forbidding tally behavior changes. That duplicates the highest-drift parser surface (~50 lines) and invites skew on the next compact/header tweak; ground-truth ingest would read stale rules while panel self-agreement reads updated ones.
- **Proposed resolution**: Implement `classification_row_panel_inputs` once, then rewrite `voter_agreement_rows_from_tsv` to map each prep object through `voter_agreement_row_from_panel` with identical ineligible/malformed counting. Keep existing `test_voter_agreement_rows_from_tsv_schema_shapes` as the regression guard; drop the "mirror internals" duplication instruction from the plan.

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:116-129
- **Concern**: [SCOPE-REDUCTION] Drop firm `findings_ledger.py` public read API and dedicated tests. Scenario: The plan marks `findings-ledger.tsv` optional and non-authoritative, yet still firm-updates `python/findings_ledger.py` with `read_rows` / `row_signature` plus `test_findings_ledger.py` expansion. The repo has zero committed `findings-ledger.tsv` files; ground-truth calibration runs on classification TSVs, JSONL/NDJSON, and markdown. This adds ~60+ lines of public surface and maintenance without clearing the necessity gate for the diagnostic corpus.
- **Proposed resolution**: Remove `### UPDATED: python/findings_ledger.py` and `### UPDATED: python/test_findings_ledger.py` from firm scope. If ledger rows are ever present, parse inline inside `analyze_issues.py` with existing `LEDGER_COLUMNS` (optional, best-effort) without new public helpers.
