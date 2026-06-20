### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/progress_report.py:824-826
- **Concern**: Top reviewers still jsonl-first; plan only removes the design-only fallback. Scenario: `render_phase_detail` always calls `_top_reviewers(findings_file)` before any classification path, so `/implement` runs with both `review-findings-full.jsonl` and per-round `findings-classification.tsv` keep flat +1 Top reviewers and never apply severity weighting despite the new TSV helpers
- **Proposed resolution**: Replace the unconditional `_top_reviewers` call with an explicit branch: when `_classification_tsv_available(round_dirs)` use weighted `_top_reviewers_from_classification(..., label_map=label_map)` for both skills; call `_top_reviewers` only when no classification TSV exists in any round



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/progress_report.py:851-868
- **Concern**: Weighted Top reviewers copy not fully specified. Scenario: After weighting, the round-sum footnote still says Top reviewers count "per-round accepted suggestions" and the section header still says "accepted suggestions", so operators see +2/+1 point totals explained as flat suggestion counts
- **Proposed resolution**: Update both the `**Top reviewers** (...)` header and the `_The Total (round-sum) row..._` footnote to "accepted-point score" / weighted-point semantics (high-severity accepted rows contribute 2 per round per reviewer)



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/plan_review_tally.py:236-275
- **Concern**: python/plan_review_tally.py:510-575. Scenario: YES-voter severity collection is duplicated across `_write_findings_classification` and `_render` with no shared helper
- **Proposed resolution**: Drift between inline competition scoreboard weights and `findings-classification.tsv` severities would make `voting-tally.md` Score disagree with TSV-driven Top reviewers even when tests cover only one surface Extract one `_yes_voter_cells(item_id)` (or similar) used by both writers; compute `accepted_weight` and TSV severity columns from the same parsed cell list



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_tally.py:627-635
- **Concern**: `is_oos` / `kind` are computed after `_classification_row` is appended, so rows can emit `scope=in_scope` for legacy `[OUT_OF_SCOPE]` / `_scope_drift` items. Scenario: Main loop writes classification before `is_oos` is known; OOS rows can get wrong `scope`, in-scope `+2` weighting, and Top reviewers inclusion for `FINDING_N` + `scope=oos`
- **Proposed resolution**: Reorder per plan: compute `is_oos` (prefix, title tag, `_scope_drift`) before `_classification_row`; pass `is_oos` into the row builder; mirror the same ordering on the `effective == 0` branch



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_tally.py:674-685
- **Concern**: Inline scoreboard `Score` still sums unweighted `row["accepted"]`; extending `score_rows` to 4-tuples without rewriting this loop raises `ValueError` or leaves flat scoring. Scenario: `for reviewer, kind, result in score_rows` unpack fails on 4-tuples; even with `row[:3]`, `score = row["accepted"] + ...` ignores `accepted_weight`
- **Proposed resolution**: Accumulate per-reviewer `accepted_weight` while iterating `score_rows`; set `Score = sum(weights) + oos_accepted - rejected - oos_rejected`; update every 3-tuple unpack (`_append_manifest_dead_rows`, `_write_yield_tsv`, stats loop) to tolerate the fourth field



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/plan_review_tally.py:532-535
- **Concern**: `_render` still comma-splits `finding_reviewers` proposer cells when building `score_rows`. Scenario: Whitespace-merged design cells like `Cursor-Pragmatic Codex-Arch` credit only the first comma segment; co-proposers lose weighted points despite full attribution in the TSV
- **Proposed resolution**: Build labels via `_attribution_labels()` and split with `voting.split_classification_attribution(..., column="finding_reviewers", labels=...)` before extending `score_rows`; give each matched label the same `accepted_weight`



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/progress_report.py:851-856
- **Concern**: Plan omits explicit update of the round-sum footnote that still says Top reviewers count flat per-round accepted suggestions. Scenario: After weighted Top reviewers ship, the Total row explainer still claims leaderboard math matches unweighted Accepted columns, misleading operators comparing scoreboard Score to Top reviewers
- **Proposed resolution**: Extend the progress_report.py plan bullet to require rewriting the lines 851-856 footnote (and the empty-state string at 873 if still present) to describe accepted-point scoring, not suggestion counts



### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/progress_report.py:851-873
- **Concern**: Review Phase Detail footnote and empty-state copy still describe flat per-round accepted-suggestion counts while Top reviewers switches to weighted accepted-point totals when classification TSV exists. Scenario: After weighted scoring, the caption still says Top reviewers "counts per-round accepted suggestions the same way" and the header/empty line still say "accepted suggestions"; operators misread +2/+1 point totals as raw accepted counts, especially on implement runs that now prefer classification TSV over jsonl
- **Proposed resolution**: In `render_phase_detail`, update the round-sum caption (~851-856), Top reviewers header (~868), and empty-state line (~873) to "accepted-point score" wording; state that per-round Accepted columns stay unweighted counts while Top reviewers sums weighted in-scope points when `_classification_tsv_available` is true, and retains flat accepted-count semantics on jsonl-only fallback; extend `test_render_phase_detail_top_reviewers_from_classification` and `test_render_phase_detail_total_relabeled_round_sum_under_recurrence` to assert the new copy



### FINDING_9:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review_round.py:770-842; python/plan_review_tally.py:530-535
- **Concern**: Design tally label vocabulary is produced after the scoreboard needs it. Scenario: Fresh design rounds can under-credit merged findings like Cursor-Pragmatic Codex-Arch because plan-review-prune-label-map.tsv is written after plan-review tally, voter labels are Claude/Codex/Cursor, and panel-manifest.ndjson is materialized later. The proposed tokenizer may not have the human reviewer labels needed to split co-proposers before scoring.
- **Proposed resolution**: Create the human label map before invoking plan-review tally, or have plan_review_tally._attribution_labels read plan-review-slots.ndjson directly before falling back.



### FINDING_10:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: docs/voting-process.md:44; docs/run-logs.md:144-158,239-246; skills/shared/voting-protocol.md:71
- **Concern**: Classification TSV wire-schema docs stay on the old column contract. Scenario: The plan appends scope to classification TSVs, but exact schema docs still advertise 21/22-column headers. Consumers of committed run logs and voting protocol docs can miss the new scope contract and mishandle OOS rows.
- **Proposed resolution**: Add docs/voting-process.md and docs/run-logs.md to the plan, and update the existing voting-protocol schema sentence with the new trailing scope column and counts.



