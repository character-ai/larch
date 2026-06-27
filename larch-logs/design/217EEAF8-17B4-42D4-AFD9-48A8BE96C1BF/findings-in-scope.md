### FINDING_1: Implement false-negative corpus needs `log_root` outside `render()`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: `_impl_fn_rows_from_run(...)` must scan per-run `round-*/findings-classification.tsv`, but `render(records, ...)` only receives normalized JSONL-derived `records` from `extract()` and has no `log_root` or implement run paths. `main()` does not pass `log_root` or prebuilt `i_fn_rows` into `render()`. An implementer may skip `i_fn_rows`, re-parse logs without contract, stuff side data through globals, or derive false-negative rows from JSONL-only `records`/`i_all`, leaving implement neutral-rate and important-reject-rate at zero or wrong (including missing TSV `voting_result=neutral` when JSONL says `outcome=rejected`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Build `i_fn_rows` in `main()` or `extract()` where `log_root` is available (or add an explicit `log_root` / precomputed `i_fn_rows` argument to `render()`). Have `_impl_fn_rows_from_run` walk `round-*/findings-classification.tsv` per run. Pass the corpus into `_section_false_negatives` from `main()`, including the empty-corpus early-return path.
  - From Cursor-Innovation: Thread `log_root` (and cutoff/since_version) into `render()`, or build `i_fn_rows` in `main()` via a dedicated implement-run glob and pass it as a new argument; do not infer implement false-negative corpora from JSONL-only `records`.

### FINDING_2: Implement TSV/JSONL join must be TSV-primary with round- and token-aware lookup
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Implement classification TSV rows use `FINDING_*` ids with panel verdict on `voting_result` (e.g. `neutral`), while committed JSONL often uses separate `REJ_CR*` ids with `outcome:"rejected"` and prose tokens pointing at the FINDING. Id-equality join or JSONL-outcome-driven corpus construction drops reviewer-claimed severity, omits neutral panels, mis-buckets 1-YES neutrals as 0-YES rejects, and can pair the wrong round if join ignores `round_num`. `rejected_analysis._join_run_findings` already solves token lookup via `_records_by_round_and_token` / `_lookup_jsonl_record` / `_finding_tokens`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Make `_impl_fn_rows_from_run` iterate each eligible TSV row as authoritative for `voting_result` and `scope`. Build a per-round JSONL side index with the same token lookup used in `rejected_analysis.py`. Set reviewer-claimed tier from matched JSONL `body_severity`, else TSV `body_severity` when present. Do not drive the corpus from JSONL `outcome` or `REJ_*` ids alone.
  - From Cursor-Innovation: In `_impl_fn_rows_from_run`, iterate TSV rows as primary, resolve optional JSONL `body_severity` via the same `(round_num, token)` index and `_finding_tokens()` rules as `rejected_analysis._lookup_jsonl_record()` (import or minimal shared helper); never require `jsonl.id == tsv.finding_id`.
  - From Cursor-Pragmatic: Mandate `_impl_fn_rows_from_run` iterate each per-round classification TSV row (FINDING_* / REJ_* on TSV only), take verdict from TSV `voting_result`, and optionally resolve reviewer-claimed `body_severity` via round+FINDING token lookup mirroring `rejected_analysis._lookup_jsonl_record`; do not build the corpus from JSONL `outcome` or JSONL id keys.
  - From Codex-Pragmatic: Require a round-aware join keyed by `round_num` plus `finding_id`, matching the existing round_tsv lookup pattern.
  - From Cursor-Requirements: In `_impl_fn_rows_from_run`, iterate each classification TSV row as the corpus driver; take `voting_result` only from TSV; enrich `body_severity` via `rejected_analysis._records_by_round_and_token` / `_lookup_jsonl_record` / `_finding_tokens` (prose-anchored `FINDING_N` tokens), not raw id match. Extend the harness with mismatched `FINDING_6` TSV + `REJ_CR1_3` JSONL pairing.

### FINDING_3: Implement false-negative rows need a separate TSV-backed corpus, not reused `i_all`
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Existing implement records in `i_all` set `outcome` from JSONL during `_extract_one_implement_run` and do not retain TSV `voting_result`, `scope`, or TSV `body_severity`. Reusing or filtering `i_all` by JSONL `outcome` for false-negative metrics reproduces accepted failure modes: neutrals counted as rejects and `scope=oos` deferred rows included when JSONL still says `accepted`/`rejected`, even though baseline tables must stay unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Define `_impl_fn_rows_from_run` output schema explicitly (`voting_result`, `scope`, `body_severity`, `period`, `run_id`, tier bucket inputs). Build it only from TSV rows plus optional JSONL severity enrichment. Keep `i_all` untouched for baseline sections.

### FINDING_4: Design false-negative denominators must exclude `out_of_scope` verdict rows
- **Reviewer(s)**: Codex-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: Design false-negative filtering only gates `is_oos_id` and scope drift. Design records set `outcome` from TSV `voting_result` via `_extract_one_design_tsv`. A non-OOS `FINDING_*` row with `voting_result=out_of_scope` (including when no trailing `scope` column) still enters `d_fn_inscope`, diluting neutral-rate and important-reject-rate even though it is not a false-negative candidate and violates documented exclusion of `out_of_scope` from false-negative metrics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add an explicit design verdict gate before aggregation, mirroring the implement countable-verdict filter, so only accepted, neutral, and rejected rows feed `d_fn_inscope`.
  - From Cursor-Requirements: Also exclude design rows whose TSV-sourced `record["outcome"]` is `out_of_scope` (and optionally `exonerated` if treated as non-countable) from `d_fn_inscope`; add a harness row with `FINDING_*` + `voting_result=out_of_scope` and assert it does not affect false-negative totals.

### FINDING_5: `i_fn_rows` must carry `period` for pre/post false-negative subtables
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `_section_prepost()` and planned false-negative pre/post subtables filter on `record["period"]` (`pre`/`post`/`unknown`). `_impl_fn_rows_from_run` is specified without attaching period from manifest `started_at` / `larch_version` using existing `period_of()` / `period_of_version()`. Rows without `period` are skipped or mis-bucketed when `--cutoff` or `--since-version` is set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pass `cutoff` and `since_version` into `_impl_fn_rows_from_run` and stamp each row with the same period logic as `_extract_one_implement_run`; mirror `_section_prepost()` by skipping `period == "unknown"` in false-negative pre/post tables.

### FINDING_6: Implement false-negative eligibility must exclude `exonerated` and other non-panel verdicts
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Production implement TSVs carry `voting_result=exonerated` and other non-panel verdicts. The plan only names a vague "countable verdict set" for implement eligibility. Including `exonerated`, `out_of_scope`, or similar rows inflates tier denominators for neutral-rate and important-reject-rate and understates both signals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Define implement eligibility as TSV `voting_result` in `{accepted, neutral, rejected}` only; exclude `exonerated`, `out_of_scope`, and other non-panel verdicts alongside OOS id/scope gates. Mirror the voter-calibration false-negative gate that already limits to accepted/neutral/rejected.

### FINDING_7: Default-path false-negative ingestion diverges from `--era` mode in voter-calibration
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Failure modes require feeding both corpora through `_parse_file_into_stats()`, but implementation bullets only extend that helper for `--era` while default `main()` keeps a hand-rolled `voter_agreement_rows_from_tsv()` loop with "parallel" false-negative collection. Eligibility, malformed-row, or `_normalize_vote_cell` fixes can land in one path only, so default and `--era` false-negative tables diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Refactor default discovery to call `_parse_file_into_stats()` per discovered TSV (same as `_collect_era_corpora`), accumulating agreement and `false_negative_rows` from one helper; remove duplicated inline parsing in `main()`.

### FINDING_8: Offline realized-outcomes success path lacks bulk-issues injection hook
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The plan adds `--filed-issue-details-json`, but the realized-outcomes section still needs a non-empty `issues` corpus to reach `ground_truth_voter_calibration()`. Without a CLI or test hook for the bulk issues JSON, the required success-path assertion cannot run deterministically offline and falls back to a live `gh issue list` dependency.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add a test-only way to inject the bulk `issues` corpus, or explicitly stub `gh issue list` in the harness, so the realized-outcomes success path is verifiable without network access.

### FINDING_9: False-negative severity aliasing must inspect raw `blocker`/`critical`/`blocking` before normalization
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: `normalize_design_severity()` maps design `blocker` and `critical` to `(none)`. If `_reviewer_claimed_tier()` applies aliases only after normalization, those design rows stay in the `(none)` bucket and important-reject-rate undercounts the alias path the plan says to cover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Make `_reviewer_claimed_tier()` inspect the raw lowercased `body_severity` before or alongside normalization and map raw `blocker`, `critical`, and `blocking` to `important`, while keeping the shared normalizers unchanged.
