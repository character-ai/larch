### FINDING_1: Top reviewers still jsonl-first before classification
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `render_phase_detail` always calls `_top_reviewers(findings_file)` before any classification path, so `/implement` runs that have both `review-findings-full.jsonl` and per-round `findings-classification.tsv` keep flat +1 Top reviewers and never apply severity weighting despite the new TSV helpers. The plan only removes the design-only fallback; it does not fix this unconditional jsonl-first call.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace the unconditional `_top_reviewers` call with an explicit branch: when `_classification_tsv_available(round_dirs)` use weighted `_top_reviewers_from_classification(..., label_map=label_map)` for both skills; call `_top_reviewers` only when no classification TSV exists in any round

### FINDING_2: Operator copy still describes flat accepted-suggestion counts
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: After weighted Top reviewers ship, `render_phase_detail` operator-facing copy still describes flat per-round accepted-suggestion counts. The round-sum footnote, Top reviewers header, and empty-state line can mislead operators into reading +2/+1 point totals as raw accepted counts, especially when classification TSV is preferred over jsonl. Per-round Accepted columns may stay unweighted while Top reviewers sums weighted in-scope points.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Update both the `**Top reviewers** (...)` header and the `_The Total (round-sum) row..._` footnote to "accepted-point score" / weighted-point semantics (high-severity accepted rows contribute 2 per round per reviewer)
  - From Cursor-Pragmatic: Extend the progress_report.py plan bullet to require rewriting the lines 851-856 footnote (and the empty-state string at 873 if still present) to describe accepted-point scoring, not suggestion counts
  - From Cursor-Requirements: In `render_phase_detail`, update the round-sum caption (~851-856), Top reviewers header (~868), and empty-state line (~873) to "accepted-point score" wording; state that per-round Accepted columns stay unweighted counts while Top reviewers sums weighted in-scope points when `_classification_tsv_available` is true, and retains flat accepted-count semantics on jsonl-only fallback; extend `test_render_phase_detail_top_reviewers_from_classification` and `test_render_phase_detail_total_relabeled_round_sum_under_recurrence` to assert the new copy

### FINDING_3: Duplicated YES-voter severity collection in plan_review_tally
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: YES-voter severity collection is duplicated across `_write_findings_classification` and `_render` in `plan_review_tally.py` with no shared helper. Drift between inline competition scoreboard weights and `findings-classification.tsv` severities would make `voting-tally.md` Score disagree with TSV-driven Top reviewers even when tests cover only one surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extract one `_yes_voter_cells(item_id)` (or similar) used by both writers; compute `accepted_weight` and TSV severity columns from the same parsed cell list

### FINDING_4: OOS scope computed after classification row is written
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: In `review_tally.py`, `is_oos` / `kind` are computed after `_classification_row` is appended, so rows can emit `scope=in_scope` for legacy `[OUT_OF_SCOPE]` / `_scope_drift` items. OOS rows can get wrong `scope`, in-scope +2 weighting, and Top reviewers inclusion for `FINDING_N` + `scope=oos`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Reorder per plan: compute `is_oos` (prefix, title tag, `_scope_drift`) before `_classification_row`; pass `is_oos` into the row builder; mirror the same ordering on the `effective == 0` branch

### FINDING_5: Inline scoreboard Score ignores accepted_weight
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Inline scoreboard `Score` still sums unweighted `row["accepted"]`. Extending `score_rows` to 4-tuples without rewriting this loop raises `ValueError` or leaves flat scoring. Even with `row[:3]`, `score = row["accepted"] + ...` ignores `accepted_weight`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Accumulate per-reviewer `accepted_weight` while iterating `score_rows`; set `Score = sum(weights) + oos_accepted - rejected - oos_rejected`; update every 3-tuple unpack (`_append_manifest_dead_rows`, `_write_yield_tsv`, stats loop) to tolerate the fourth field

### FINDING_6: Design tally comma-splits co-proposer attribution
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `plan_review_tally._render` still comma-splits `finding_reviewers` proposer cells when building `score_rows`. Whitespace-merged design cells like `Cursor-Pragmatic Codex-Arch` credit only the first comma segment; co-proposers lose weighted points despite full attribution in the TSV.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Build labels via `_attribution_labels()` and split with `voting.split_classification_attribution(..., column="finding_reviewers", labels=...)` before extending `score_rows`; give each matched label the same `accepted_weight`

### FINDING_7: Design tally label map available too late
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Design tally label vocabulary is produced after the scoreboard needs it. Fresh design rounds can under-credit merged findings like `Cursor-Pragmatic Codex-Arch` because `plan-review-prune-label-map.tsv` is written after plan-review tally, voter labels are Claude/Codex/Cursor, and `panel-manifest.ndjson` is materialized later. The proposed tokenizer may not have the human reviewer labels needed to split co-proposers before scoring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Create the human label map before invoking plan-review tally, or have plan_review_tally._attribution_labels read plan-review-slots.ndjson directly before falling back.

### FINDING_8: Classification TSV schema docs still on old contract
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Classification TSV wire-schema docs stay on the old column contract. The plan appends `scope` to classification TSVs, but exact schema docs still advertise 21/22-column headers. Consumers of committed run logs and voting protocol docs can miss the new scope contract and mishandle OOS rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add docs/voting-process.md and docs/run-logs.md to the plan, and update the existing voting-protocol schema sentence with the new trailing scope column and counts.
