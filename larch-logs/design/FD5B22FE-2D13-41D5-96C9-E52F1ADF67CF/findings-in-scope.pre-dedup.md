### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/analyze_issues.py:181-189
- **Concern**: Design panel_verdict must bind from round-local plan-review markdown, not run-root cumulative files. Scenario: Committed design runs store different finding sets under `plan-review/round-N/accepted-plan-findings.md` vs run-root `accepted-plan-findings.md` (same `FINDING_1` id, different concerns). Step 5 only says read same-round markdown first; it never pins `plan-review/round-{round_num}/` ahead of run-root files. An implementer can membership-test run-root markdown for a `plan-review/round-1/findings-classification.tsv` row, mis-bind `panel_verdict`, and poison prose join plus the gated later accepted-finding index.
- **Proposed resolution**: In step 5 (and Ground-truth semantics panel-verdict binding), require design verdict membership from `plan-review/round-{round_num}/accepted-plan-findings.md` and `rejected-findings.md` derived from the classification TSV path; consult run-root markdown only when that round-local pair is absent. Treat run-root vs round-local disagreement as weak/non-decisive. Add a regression fixture where round-1 TSV `FINDING_1` is accepted in round-local markdown but absent or different at run root.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/analyze_issues.py:191-206
- **Concern**: `accepted_reverted_or_regressed` must require reversal/regression language on later evidence. Scenario: Ground-truth semantics (lines 77-79) require later text with reversal or regression language, but step 6 matchers only require cleaned path overlap plus title tokens, and step 7 buckets `accepted_reverted_or_regressed` from any later match without a language gate. A later bug issue with overlapping path/title but no revert wording would be scored decisive and flip YES/NO alignment (`false_positive_yes` / `false_negative_no`).
- **Proposed resolution**: In step 7 (and step 6 if shared), gate `accepted_reverted_or_regressed` on later issue/finding text matching `wasteful_findings`'s `reversal_re` (`python/analyze_issues.py:471-474`) or equivalent regression tokens already used in `CATEGORY_PATTERNS`; path/title overlap alone stays non-decisive. Add a test where overlap exists without reversal language and assert no decisive revert bucket.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/analyze_issues.py:191-207
- **Concern**: Ground-truth step 7 must gate `accepted_reverted_or_regressed` on reversal/regression language, not step 6 path/token overlap alone. Scenario: Ground-truth semantics (lines 77-79) require later text with reversal or regression language before a decisive contradicting bucket. Steps 6-7 share generic overlap matchers and step 7 only says "detect later regression/revert" without binding to `wasteful_findings`' `reversal_re` (`python/analyze_issues.py:471-474`) or an explicit regression-language check. An implementer following steps 6-7 can bucket `accepted_no_counterevidence` rows into `accepted_reverted_or_regressed` on path plus title-token overlap alone, inflating `false_positive_yes` and deflating calibration.
- **Proposed resolution**: In step 7 accepted branch, require decisive `accepted_reverted_or_regressed` only when later issue/finding text matches a hoisted shared `reversal_re` (same pattern as `wasteful_findings`) or contains an explicit regression/reversal token from the Bug-fix category rules; keep step 6 overlap as a prerequisite only. Add a negative fixture where path/title overlap without reversal/regression language stays non-decisive.



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
- **Focus area**: correctness
- **Location**: plan.txt:185-189
- **Concern**: Design panel_verdict must resolve round-local markdown before run-root files. Scenario: Multi-round design runs store per-round `plan-review/round-N/accepted-plan-findings.md` / `rejected-findings.md` beside the classification TSV, while many runs also have run-root copies. Step 5 says "same-round" markdown-first but never pins the sibling round directory. An implementer can read only run-root cumulative markdown for a round-2 TSV, mis-bind `panel_verdict`, and invert decisive YES/NO alignment on a large committed corpus.
- **Proposed resolution**: In step 5 Design prose binding, require path order: for a TSV at `.../plan-review/round-N/findings-classification.tsv`, read `.../plan-review/round-N/accepted-plan-findings.md` and `.../rejected-findings.md` first (index `### FINDING_<n>:` membership), then fall back to run-root markdown only when round-local files are absent; treat run-root vs round-local disagreement as weak/non-decisive.



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:203-206
- **Concern**: `accepted_reverted_or_regressed` must not reuse generic resurfacing overlap alone. Scenario: Semantics require reversal or regression language, but step 6 matchers only need cleaned path overlap plus title tokens (or high token overlap). Step 7 does not add a reversal gate for accepted rows. Unrelated later issues with shared paths can bucket `accepted_reverted_or_regressed` decisively and inflate `false_positive_yes`.
- **Proposed resolution**: In step 7, gate `accepted_reverted_or_regressed` on later evidence passing `wasteful_findings`'s `reversal_re` and/or `default_category` regression tokens (reuse `python/analyze_issues.py:471-474` / `CATEGORY_PATTERNS`), in addition to temporal ordering; keep step 6 overlap helpers for `rejected_resurfaced` only.



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:116-129
- **Concern**: [SCOPE-REDUCTION] Drop firm `findings_ledger.py` public read API and dedicated tests. Scenario: The plan marks `findings-ledger.tsv` optional and non-authoritative, yet still firm-updates `python/findings_ledger.py` with `read_rows` / `row_signature` plus `test_findings_ledger.py` expansion. The repo has zero committed `findings-ledger.tsv` files; ground-truth calibration runs on classification TSVs, JSONL/NDJSON, and markdown. This adds ~60+ lines of public surface and maintenance without clearing the necessity gate for the diagnostic corpus.
- **Proposed resolution**: Remove `### UPDATED: python/findings_ledger.py` and `### UPDATED: python/test_findings_ledger.py` from firm scope. If ledger rows are ever present, parse inline inside `analyze_issues.py` with existing `LEDGER_COLUMNS` (optional, best-effort) without new public helpers.



### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/analyze_issues.py:191-206
- **Concern**: `accepted_reverted_or_regressed` must gate on reversal/regression language in later evidence, not step-6 path/title overlap alone. Scenario: Ground-truth semantics (lines 77-79) require later issue/finding text with reversal or regression language before a decisive `accepted_reverted_or_regressed` bucket, but steps 6-7 only define conservative path/title overlap matchers and step 7 says "detect later regression/revert" without binding to `wasteful_findings`'s `reversal_re` (`python/analyze_issues.py:471-474`) or an equivalent text check. An implementer can decisive-bucket from a later Bug fix issue that merely shares a cleaned path and two title tokens, inflating `false_positive_yes` and deflating per-voter `realized_alignment_rate` on unrelated accepted findings.
- **Proposed resolution**: In step 7, require later issue/finding prose to match `reversal_re` (or the same regression/revert token set used in semantics) before `accepted_reverted_or_regressed`; keep step-6 path/title overlap as necessary but not sufficient signals. Add a regression test where path overlap exists but later text lacks revert/regression wording and assert the row stays non-decisive.



### FINDING_9:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/analyze_issues.py:1411-1505; larch-logs/implement/0199F1E2-2238-403D-9F89-F37CA698998C/review-findings-full.jsonl:16-19
- **Concern**: OOS routed rows have no pinned accepted/rejected panel verdict source before scoring. Scenario: Committed implement JSONL stores OOS records with outcome=out_of_scope for both accepted and rejected OOS rows, while the TSV/prose vote tally carries accepted vs rejected. The plan says implement panel_verdict comes from JSONL outcome and TSV voting_result is only for parsing, then step 8 scores each OOS classification row. An implementer can drop accepted OOS rows as non-accepted or score rejected OOS rows against docked filed issues, corrupting realized_alignment_rate.
- **Proposed resolution**: In the OOS branch, bind OOS acceptedness explicitly from the classification TSV voting_result after eligibility plus MAV checks or from the parsed Vote tally Result, and restrict decisive OOS fate scoring to OOS rows whose bound OOS panel result is accepted; rejected, neutral, exonerated, or disagreement rows stay non-decisive.



