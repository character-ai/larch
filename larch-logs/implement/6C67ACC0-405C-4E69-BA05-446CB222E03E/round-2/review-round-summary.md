# Review Round 2

- Mode: `diff`
- 8 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Design verdict binding skips JSONL disagreement check
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-generic-output.txt, dyn-dyn-voter-prep-output.txt
- **Severity**: important
- **Concern**: `_design_markdown_verdict` returns round-local or run-root markdown verdicts before consulting run-root `review-findings-full.jsonl`. When round-local markdown accepts a finding but JSONL records `outcome="rejected"` (or vice versa), the row is scored as accepted instead of weak/non-decisive, violating the authoritative-source contract and mis-bucketing decisive resurfacing/revert outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Cross-check run-root JSONL after markdown bind; mark weak/non-decisive on disagreement.
  - From codex-generic-output.txt: When JSONL evidence exists for the same design row, compare its authoritative outcome with the markdown verdict before returning; mark the row weak on disagreement.
  - From dyn-dyn-voter-prep-output.txt: After round-local markdown resolves a verdict, consult JSONL for the same `FINDING_n` and mark weak/non-decisive on disagreement; only use JSONL when round-local markdown is absent or ambiguous.


### FINDING_2: GC-slimmed runs still feed decisive ground-truth scoring
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-dyn-voter-prep-output.txt
- **Severity**: important
- **Concern**: Runs marked `gc-slimmed` increment corpus counters but their leftover `findings-classification.tsv` rows still enter ingest and receive decisive realized-outcome scoring and per-voter metrics. Incomplete voter evidence from gc-slimmed runs can produce false `rejected_resurfaced`, docked OOS, or alignment rates contrary to the plan requirement that such runs count only as weak/unknown.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Tag gc-slimmed run rows and exclude them from decisive buckets and per-voter metrics.
  - From cursor-specialist-edge-cases-output.txt: Skip ingest or force weak/non-decisive for all rows when `run_dir/gc-slimmed` exists; do not count them in decisive metrics.
  - From cursor-specialist-testing-output.txt: Skip or mark non-decisive rows from gc-slimmed runs; add fixture with gc-slimmed marker plus leftover TSV asserting zero decisive ballots.
  - From dyn-dyn-voter-prep-output.txt: After detecting `(run_dir / "gc-slimmed").exists()`, skip classifier ingest for that run (or mark every row from it `weak_reason="gc-slimmed"` and exclude them from outcome/metrics), while still counting the run in corpus bullets via `_ground_truth_gc_slimmed_fallback`.


### FINDING_3: Run-root implement JSONL lacks round isolation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-generic-output.txt, dyn-dyn-voter-prep-output.txt
- **Severity**: important
- **Concern**: For run-root `review-findings-full.jsonl` where `path_round == 0`, JSONL records are not consistently gated by `record.round_num` vs `row.round_num`. Multi-round implement runs can cross-bind round-2 prose to round-1 TSV rows (or vice versa), mis-setting `panel_verdict` and producing false decisive voter alignment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Require `record.round_num` to match TSV round or degrade to weak on ambiguity.
  - From cursor-specialist-edge-cases-output.txt: Apply `rec_round` vs `row.round_num` gating for all JSONL paths, not only round-scoped files.
  - From codex-generic-output.txt: Compare `rec_round` to `row.round_num` whenever both are non-zero, independent of `path_round`; keep the path-derived round fallback only for records without `round_num`.
  - From dyn-dyn-voter-prep-output.txt: When joining from run-root JSONL, require an explicit `round_num` on the JSONL record that matches the TSV path's round, or index run-root prose separately per round via heading/alias bridges; treat ambiguous cross-round run-root matches as weak/non-decisive.


### FINDING_4: Issue-backed evidence lacks same-run round ordering
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-generic-output.txt, dyn-dyn-voter-prep-output.txt
- **Severity**: important
- **Concern**: `_ground_truth_issue_evidence` emits issues with `run_id=""` and `round_num=0`, so `_evidence_later_than_row` relies on `createdAt > started_at` alone. Issues filed mid-run but before a later review round can be treated as decisive later evidence for earlier rounds, falsely producing `rejected_resurfaced` or `accepted_reverted_or_regressed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add same-run round gating for issue-backed evidence or degrade to non-decisive.
  - From cursor-specialist-edge-cases-output.txt: Restrict issue-backed decisive matches to cross-run evidence or run-linked issue metadata; do not treat bare `createdAt` as later within the same run.
  - From codex-generic-output.txt: Carry any available run/round provenance for filed issues and apply same-run round ordering; when provenance is unavailable and the timestamp falls within the source run window, keep the match non-decisive or timestamp-degraded.
  - From dyn-dyn-voter-prep-output.txt: Either attach run/round context to issue evidence when issues are filed during a known run, or require a stricter later signal for issue-backed matches (for example cross-run `started_at` only, or explicit issue-to-run linkage), and degrade same-run issue matches to non-decisive when round ordering cannot be proved.


### FINDING_5: Substring finding_id matching causes false prose binds
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-generic-output.txt, dyn-dyn-voter-prep-output.txt
- **Severity**: important
- **Concern**: Standalone review prose join (`_standalone_review_prose_for_row`) and design JSONL fallback still use substring `finding_id in haystack` containment. `FINDING_1` can match `FINDING_10` NDJSON/JSONL prose, binding the wrong `panel_verdict` and driving incorrect decisive resurfacing/revert buckets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use `_gt_finding_id_pattern` word-boundary matching.
  - From cursor-specialist-edge-cases-output.txt: Reuse `_gt_finding_id_pattern` exact/boundary matching and ambiguity weakening in those join paths.
  - From codex-generic-output.txt: Reuse `_gt_finding_id_pattern(row.finding_id)` or exact `id` equality for standalone review joins, matching the implement prose path.
  - From dyn-dyn-voter-prep-output.txt: Reuse `_gt_finding_id_pattern` / exact-id matching in `_standalone_review_prose_for_row`, mirroring `_implement_prose_for_row`; use the same word-boundary matcher as `_implement_prose_for_row` for design JSONL joins.


### FINDING_6: OOS filed-record matching uses simplified join without round, reviewer, or fate-adjusted semantics
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-generic-output.txt, dyn-dyn-oos-verdicts-output.txt, dyn-dyn-voter-prep-output.txt
- **Severity**: important
- **Concern**: `_match_oos_filed_record` uses a parallel, simplified join instead of the fate-adjusted contract (`iter_filed_oos_records`, `_resolve_blocks_for_stable_id`, ambiguity skips, reviewer attribution). It ignores round identity, `reviewer_column` / `finding_reviewers`, and stable-id ambiguity rules. Similar OOS rows in multi-round runs can match the wrong filed record via stable-id suffix or token overlap, producing false decisive docked outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Reuse `_resolve_blocks_for_stable_id` and fate join ambiguity rules.
  - From cursor-specialist-edge-cases-output.txt: Filter candidates by normalized reviewer attribution before stable-id/token matching; stay non-decisive on ambiguity.
  - From codex-generic-output.txt: Require round-aware identity when the record exposes round/source metadata, or treat same-run duplicate bare IDs across rounds as ambiguous and non-decisive.
  - From dyn-dyn-oos-verdicts-output.txt: Require round agreement between `row.round_num` and the filed record's `artifact_relpath` / identity tuple (or explicit round metadata), reuse `_resolve_blocks_for_stable_id` semantics for stable-id collisions, and fall back to non-decisive when round-aware matching is ambiguous.
  - From dyn-dyn-oos-verdicts-output.txt: Drop token-only fallback unless reviewer labels align (or stable-id resolution is unambiguous); otherwise return `None` and bucket as `missing_filed_oos_join` / ambiguous join, matching the conservative fate-adjusted join contract.
  - From dyn-dyn-voter-prep-output.txt: Build OOS ground-truth rows by joining classification prep to the already-resolved `iter_filed_oos_records` output (or extract a shared join helper used by both fate and ground-truth), preserving stable-id ambiguity handling and reviewer attribution.


### FINDING_7: Plan-mandated ground-truth fixture categories largely untested
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The plan lists many ground-truth fixture categories (~25) but only a consolidated mega-test plus minimal dedicated coverage exists. Regressions in gc-slimmed handling, temporal ordering, JSONL disagreement, substring matching, enrichment-degraded suppression, tally disagreement, NOT_PLANNED weakening, and related paths can ship with green `make test-analyze`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add focused fixtures per plan category.
  - From cursor-specialist-testing-output.txt: Add focused offline fixtures per plan category or split the mega-test; meet acceptance criterion for all new fixture categories.
  - From cursor-specialist-testing-output.txt: Add three small fixtures for enrichment-degraded suppression, tally disagreement, and NOT_PLANNED non-decisive `rejected_resurfaced`.


### FINDING_13: OOS prose weakness blocks authoritative panel-verdict binding
- **Reviewer(s)**: dyn-dyn-oos-verdicts-output.txt
- **Severity**: important
- **Concern**: `_bind_ground_truth_prose` returns early when implement/design prose join sets `prose["weak"]` (for example multi-match JSONL ambiguity), so `_ground_truth_oos_panel_verdict` never runs. Accepted OOS rows with clear TSV `accepted` can be scored as `weak_oos_panel_verdict` and excluded from decisive docked fate and per-voter alignment, violating the plan contract that OOS accepted/rejected must come from TSV `voting_result` / round-local `vote-tally.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-oos-verdicts-output.txt: For `row.is_oos`, always call `_ground_truth_oos_panel_verdict(row)` before any early return; treat prose weakness as non-authoritative context only (title/token join), not as a blocker on `oos_panel_verdict` binding.


