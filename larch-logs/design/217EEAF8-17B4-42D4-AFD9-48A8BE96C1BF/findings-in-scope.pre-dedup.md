### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/fluff-analysis/scripts/fluff-analysis.py:666-689
- **Concern**: Implement false-negative rows cannot be built inside `render()` without log-root access. Scenario: The plan tells `render()` to aggregate `_impl_fn_rows_from_run(...)` across implement runs, but `render(records, ...)` only receives normalized `records` from `extract()` and has no `log_root` or run-dir path. `main()` also does not pass implement run paths. An implementer either skips `i_fn_rows`, re-parses logs with no contract, or stuffs side data through globals. Implement neutral-rate and important-reject-rate stay at zero or wrong.
- **Proposed resolution**: Build `i_fn_rows` in `main()` or `extract()` where `log_root` is available (or add an explicit `log_root` / precomputed `i_fn_rows` argument to `render()`). Have `_impl_fn_rows_from_run` walk `round-*/findings-classification.tsv` per run. Pass the corpus into `_section_false_negatives` from `main()`, including the empty-corpus early-return path.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/fluff-analysis/scripts/fluff-analysis.py:344-411
- **Concern**: Implement TSV/JSONL join must be TSV-row-driven with token lookup, not id equality. Scenario: The plan says join classification TSV to JSONL for `body_severity`, but implement TSV rows are `FINDING_*` while committed JSONL neutrals/rejects use `REJ_CR*` ids with `outcome:"rejected"`. Production example: TSV `FINDING_9 ... voting_result=neutral` pairs with JSONL `REJ_CR1_4`, not `FINDING_9`. Id-equality join drops reviewer-claimed severity and can omit neutral panels. `rejected_analysis._join_run_findings` already solves this via `_records_by_round_and_token` / `_lookup_jsonl_record` / `_finding_tokens`.
- **Proposed resolution**: Make `_impl_fn_rows_from_run` iterate each eligible TSV row as authoritative for `voting_result` and `scope`. Build a per-round JSONL side index with the same token lookup used in `rejected_analysis.py`. Set reviewer-claimed tier from matched JSONL `body_severity`, else TSV `body_severity` when present. Do not drive the corpus from JSONL `outcome` or `REJ_*` ids alone.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/fluff-analysis/scripts/fluff-analysis.py:392-407
- **Concern**: False-negative implement rows need explicit TSV fields on a parallel corpus, not reused `i_all` records. Scenario: Existing implement records set `outcome` from JSONL during `_extract_one_implement_run` and do not retain TSV `voting_result`, `scope`, or TSV `body_severity`. The plan keeps baseline tables unchanged and builds `i_fn_rows` separately, but it never states that `i_all` must not be filtered by JSONL `outcome` for false-negative metrics. A shortcut reuse of `i_all` reproduces the accepted FINDING_6 failure: neutrals counted as rejects and scope=oos deferred rows included when JSONL still says `accepted`/`rejected`.
- **Proposed resolution**: Define `_impl_fn_rows_from_run` output schema explicitly (`voting_result`, `scope`, `body_severity`, `period`, `run_id`, tier bucket inputs). Build it only from TSV rows plus optional JSONL severity enrichment. Keep `i_all` untouched for baseline sections.



### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:34-54
- **Concern**: Design false-negative corpus still admits `voting_result=out_of_scope` rows. Scenario: The new design metric filters only `is_oos_id` and scope drift. A non-OOS design row classified `out_of_scope` would still enter the denominator and dilute neutral-rate and important-reject-rate even though it is not a false-negative candidate.
- **Proposed resolution**: Add an explicit design verdict gate before aggregation, mirroring the implement countable-verdict filter, so only accepted, neutral, and rejected rows feed `d_fn_inscope`.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/fluff-analysis/scripts/fluff-analysis.py:666-1047
- **Concern**: TSV-primary `i_fn_rows` has no `log_root` path in `render()`. Scenario: `render(records, ...)` only receives flattened JSONL-derived records. `_impl_fn_rows_from_run(run_dir, ...)` must scan per-run `round-*/findings-classification.tsv`, but `main()` never passes `log_root` (or prebuilt `i_fn_rows`) into `render()`. An implementer may derive false-negative rows from `records`/`i_all`, which keeps JSONL `outcome=rejected` for 1-YES neutrals and misses TSV `voting_result=neutral` on production-shaped logs.
- **Proposed resolution**: Thread `log_root` (and cutoff/since_version) into `render()`, or build `i_fn_rows` in `main()` via a dedicated implement-run glob and pass it as a new argument; do not infer implement false-negative corpora from JSONL-only `records`.



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/fluff-analysis/scripts/fluff-analysis.py
- **Concern**: Implement JSONL join must use FINDING/REJ token lookup, not id equality. Scenario: Production implement logs store panel verdict on TSV `FINDING_N` rows while JSONL uses separate `REJ_CRn_m` ids with `outcome=rejected`. `_finding_tokens()` in `python/larch/issue/rejected_analysis.py` bridges those ids via prose tokens. The plan says "joining classification TSV to JSONL" but does not pin this lookup; id-equality joins drop neutrals or mis-bucket rejects.
- **Proposed resolution**: In `_impl_fn_rows_from_run`, iterate TSV rows as primary, resolve optional JSONL `body_severity` via the same `(round_num, token)` index and `_finding_tokens()` rules as `rejected_analysis._lookup_jsonl_record()` (import or minimal shared helper); never require `jsonl.id == tsv.finding_id`.



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/fluff-analysis/scripts/fluff-analysis.py:884-920
- **Concern**: `i_fn_rows` must carry `period` for pre/post false-negative subtables. Scenario: `_section_prepost()` and the planned false-negative pre/post subtables filter on `record["period"]` (`pre`/`post`/`unknown`). `_impl_fn_rows_from_run` is specified without attaching period from manifest `started_at` / `larch_version` using existing `period_of()` / `period_of_version()`. Rows without `period` are skipped or mis-bucketed when `--cutoff` or `--since-version` is set.
- **Proposed resolution**: Pass `cutoff` and `since_version` into `_impl_fn_rows_from_run` and stamp each row with the same period logic as `_extract_one_implement_run`; mirror `_section_prepost()` by skipping `period == "unknown"` in false-negative pre/post tables.



### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/voter-calibration/scripts/voter-calibration.py:221-504
- **Concern**: Default-path false-negative ingestion still diverges from era mode. Scenario: Failure modes require feeding both corpora through `_parse_file_into_stats()`, but the implementation bullets only extend that helper for `--era` while default `main()` keeps a hand-rolled `voter_agreement_rows_from_tsv()` loop with "parallel" false-negative collection. Eligibility, malformed-row, or `_normalize_vote_cell` fixes can land in one path only, so default and `--era` false-negative tables diverge.
- **Proposed resolution**: Refactor default discovery to call `_parse_file_into_stats()` per discovered TSV (same as `_collect_era_corpora`), accumulating agreement and `false_negative_rows` from one helper; remove duplicated inline parsing in `main()`.



### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/voter-calibration/scripts/voter-calibration.py:128-143; skills/voter-calibration/scripts/test-voter-calibration.sh:181-183
- **Concern**: Offline realized-outcomes happy path has no bulk-issues injection hook. Scenario: The plan adds `--filed-issue-details-json`, but the realized-outcomes section still needs a non-empty `issues` corpus to reach `ground_truth_voter_calibration()`. Without a CLI or test hook for the bulk issues JSON, the required success-path assertion cannot run deterministically offline and falls back to a live `gh issue list` dependency.
- **Proposed resolution**: Add a test-only way to inject the bulk `issues` corpus, or explicitly stub `gh issue list` in the harness, so the realized-outcomes success path is verifiable without network access.



### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/fluff-analysis/scripts/fluff-analysis.py
- **Concern**: Implement false-negative corpus must be TSV-primary with token JSONL lookup. Scenario: Committed implement logs store panel verdict on TSV `FINDING_*` rows (`voting_result=neutral`) while JSONL uses separate `REJ_*` ids with `outcome=rejected` and prose pointing at the FINDING (e.g. `larch-logs/implement/DA79C363-2CF1-4F68-A76B-00DAB5F71C38/`). A JSONL-driven join or id-equality join yields zero implement neutral-rate or mis-buckets 1-YES neutrals as 0-YES rejects.
- **Proposed resolution**: Mandate `_impl_fn_rows_from_run` iterate each per-round classification TSV row (FINDING_* / REJ_* on TSV only), take verdict from TSV `voting_result`, and optionally resolve reviewer-claimed `body_severity` via round+FINDING token lookup mirroring `rejected_analysis._lookup_jsonl_record`; do not build the corpus from JSONL `outcome` or JSONL id keys.



### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/fluff-analysis/scripts/fluff-analysis.py
- **Concern**: Implement false-negative eligibility must exclude `exonerated` verdict rows. Scenario: Production implement TSVs carry `voting_result=exonerated` (e.g. `larch-logs/implement/D48CF6D0-0699-4DC7-829E-9E675699BA85/round-3/findings-classification.tsv`). The plan only names a vague "countable verdict set" for implement eligibility. Those rows are neither neutral nor rejected; if included they inflate tier denominators for neutral-rate and important-reject-rate and understate both signals.
- **Proposed resolution**: Define implement eligibility as TSV `voting_result` in `{accepted, neutral, rejected}` only; exclude `exonerated`, `out_of_scope`, and other non-panel verdicts alongside OOS id/scope gates. Mirror the voter-calibration false-negative gate that already limits to accepted/neutral/rejected.



### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:27-31
- **Concern**: Join key for `_impl_fn_rows_from_run()` is underspecified and can pair the wrong round. Scenario: Implement runs have per-round classification TSVs. If the helper joins only by `finding_id` or row order, a later round can borrow the wrong verdict or `body_severity` and silently skew the new false-negative rates.
- **Proposed resolution**: Require a round-aware join keyed by `round_num` plus `finding_id`, matching the existing round_tsv lookup pattern.



### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/fluff-analysis/scripts/fluff-analysis.py
- **Concern**: Implement false-negative corpus must be TSV-primary with token-based JSONL enrichment. Scenario: Committed implement logs keep panel verdict on classification TSV `FINDING_*` rows (`voting_result=neutral`) while JSONL stores separate `REJ_CR*_` ids with `outcome":"rejected"` and no matching TSV row (e.g. `FINDING_6` neutral in TSV vs `REJ_CR1_3` in JSONL for the same panel). A JSONL-driven join or id-equality join omits neutrals from `i_fn_rows` or mis-buckets them as 0-YES rejects, leaving implement neutral-rate near zero on real `larch-logs/`.
- **Proposed resolution**: In `_impl_fn_rows_from_run`, iterate each classification TSV row as the corpus driver; take `voting_result` only from TSV; enrich `body_severity` via `rejected_analysis._records_by_round_and_token` / `_lookup_jsonl_record` / `_finding_tokens` (prose-anchored `FINDING_N` tokens), not raw id match. Extend the harness with mismatched `FINDING_6` TSV + `REJ_CR1_3` JSONL pairing.



### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/fluff-analysis/scripts/fluff-analysis.py:666-671
- **Concern**: Round-2 fix incomplete: design false-negative denominators still admit `outcome == "out_of_scope"` rows. Scenario: The plan builds `d_fn_inscope` with `not r["is_oos_id"]` and `_scope_is_oos(scope, finding_id)` only. Design records set `outcome` from TSV `voting_result` (`_extract_one_design_tsv`). A non-OOS `FINDING_*` row with `voting_result=out_of_scope` and no trailing `scope` column still enters neutral-rate and important-reject denominators, violating the documented exclusion of `out_of_scope` and OOS ids from false-negative metrics.
- **Proposed resolution**: Also exclude design rows whose TSV-sourced `record["outcome"]` is `out_of_scope` (and optionally `exonerated` if treated as non-countable) from `d_fn_inscope`; add a harness row with `FINDING_*` + `voting_result=out_of_scope` and assert it does not affect false-negative totals.



### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:18-23
- **Concern**: False-negative aliasing needs to preserve raw `blocker`/`critical`/`blocking` values, not only normalized ones.. Scenario: `normalize_design_severity()` maps design `blocker` and `critical` to `(none)`, so if `_reviewer_claimed_tier()` applies aliases only after normalization, those design rows stay in the `(none)` bucket and the new important-reject-rate undercounts the alias path the plan says to cover.
- **Proposed resolution**: Make `_reviewer_claimed_tier()` inspect the raw lowercased `body_severity` before or alongside normalization and map raw `blocker`, `critical`, and `blocking` to `important`, while keeping the shared normalizers unchanged.



