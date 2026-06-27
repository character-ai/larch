## Plan

## Approach

- Keep this **diagnostic-only**.
- Do not change live review spawning, thresholds, tokens, proposer scores, TSV schemas, or `voting.py`.
- Leave existing `/fluff-analysis` baseline tables and shared `normalize_severity()` / `normalize_design_severity()` ingest unchanged.
- Add dedicated false-negative sections after current baseline or calibration sections.
- Apply accepted review fixes: build implement false-negative corpus outside `render()` where `log_root` is available; TSV-primary round- and token-aware implement join mirroring `rejected_analysis`; separate TSV-backed implement row schema (not `i_all`); symmetric OOS exclusion for design and implement via `scope` column (`oos`, `out_of_scope`, `out-of-scope`) plus OOS ids; design verdict gate excluding `out_of_scope` and `exonerated`; false-negative-only `blocker`/`critical`/`blocking` tier aliases applied to **raw** `body_severity` before corpus-specific normalization; implement verdicts sourced from classification TSV `voting_result` only; design verdicts sourced from TSV `voting_result` on extracted records (`record["outcome"]`); `period` on implement false-negative rows for pre/post subtables; implement eligibility limited to `{accepted, neutral, rejected}`; `voting._normalize_vote_cell` pinning for voter false-negative YES parsing; neutral panels eligible for false-negative YES (not agreement ineligible); zero-denominator rate guarding; repo/URL filtering for realized-outcomes fetch; missing-`gh` degradation including repo resolution; `--repo` and `--filed-issue-details-json` CLI wiring; and successful realized-outcomes section rendering when fetch succeeds.

## Files to modify/create

### UPDATED: `skills/fluff-analysis/scripts/fluff-analysis.py`

Add a false-negative report section, build the implement corpus where `log_root` is available, and wire both corpora into `render()`.

- Add `_scope_is_oos(scope, finding_id)` helper (or import from `rejected_analysis._scope_is_oos`): return true when `scope` is `oos`, `out_of_scope`, or `out-of-scope` (case-insensitive), or `finding_id` starts with `OOS_`.
- Define implement false-negative countable verdicts explicitly: `voting_result` in `{accepted, neutral, rejected}` only. Exclude `exonerated`, `out_of_scope`, and all other non-panel verdicts alongside OOS id/scope gates.
- Add `_reviewer_claimed_tier(body_severity, *, corpus)` helper:
  - Missing or empty `body_severity` returns `(none)`; do not fall back to `record["severity"]`, prose inference, or modal voter severity.
  - **First** inspect raw lowercased `body_severity`: when raw is `blocker`, `critical`, or `blocking`, return normalized `important` immediately (false-negative-only aliases; applies to both corpora).
  - **Otherwise** for implement rows call existing `normalize_severity(body_severity)` on non-empty raw values; for design rows call existing `normalize_design_severity(body_severity)`.
  - Do **not** extend `normalize_severity()` or `normalize_design_severity()`; baseline and pre/post buckets must remain unchanged.
- Extend `parse_design_tsv()` to retain trailing `scope` when present (23-column header superset with `body_severity` and `scope`); carry `scope` on each parsed record.
- Extend `_extract_one_design_tsv()` to copy `scope` from parsed TSV onto each design record (unchanged for baseline `i_all` / `d_inscope` behavior).
- Extend `parse_impl_tsv()` to retain per-finding `voting_result`, `body_severity`, and `scope` when present in supported header supersets alongside existing voter rating fields.
- Add `_impl_fn_rows_from_run(run_dir, jsonl_records, *, cutoff=None, since_version=None)` that builds implement false-negative corpus rows **only from classification TSV**, with optional JSONL severity enrichment:
  - Walk `round-*/findings-classification.tsv` per run (same glob as `rejected_analysis._join_run_findings`).
  - **TSV-primary driver**: iterate each eligible TSV row; panel verdict comes from TSV `voting_result` only. Do not drive the corpus from JSONL `outcome`, JSONL id keys, or `REJ_*` ids alone.
  - Build per-round JSONL side index with the same token lookup as `rejected_analysis`: `_records_by_round_and_token`, `_lookup_jsonl_record`, `_finding_tokens` (import or minimal shared helper). Resolve optional reviewer-claimed `body_severity` from matched JSONL when present, else TSV `body_severity` when retained by parser. Never require `jsonl.id == tsv.finding_id`.
  - Mirror round-scoping rules from rejected analysis: use `(round_num, token)` lookup; honor `allow_unscoped` when the run has a single round and no round-local JSONL layout.
  - Eligibility per TSV row: non-OOS finding id (`FINDING_*` / `REJ_*`, not `OOS_*`); exclude when `_scope_is_oos(scope, finding_id)`; `voting_result` in `{accepted, neutral, rejected}` only.
  - Output explicit row schema (separate from `i_all`): at minimum `voting_result`, `scope`, `body_severity`, `period`, `run_id`, `finding_id`, `round_num`, plus fields needed for tier bucketing. Do not reuse or filter `i_all`.
  - Stamp each row with `period` using the same logic as `_extract_one_implement_run`: `period_of_version(since_version, larch_version)` when `since_version` is set, else `period_of(cutoff, started_at=started)` from manifest `started_at`.
- Add `build_impl_fn_rows(log_root, *, cutoff=None, since_version=None)` (in `extract()` or beside it) that globs implement run dirs under `log_root`, loads JSONL per run, and aggregates `_impl_fn_rows_from_run(...)` across runs. **`main()` builds `i_fn_rows` here** (or inside `extract()` return tuple) where `log_root`, `cutoff`, and `since_version` are available.
- Extend `render(records, cutoff, min_group, since_version=None, assessment_coverage=None, i_fn_rows=None)` with explicit `i_fn_rows` argument (default empty list). **`main()` passes prebuilt `i_fn_rows`**; `render()` must not re-glob logs or infer implement false-negative rows from JSONL-only `records`.
- In `render()`, build design false-negative slice beside existing slices:
  - Keep `d_inscope = [r for r in design if not r["is_oos_id"]]` for existing baseline sections.
  - Add `d_fn_inscope` for design false-negative metrics only:
    - Exclude OOS ids and `_scope_is_oos(r.get("scope", ""), r["finding_id"])`.
    - **Also exclude** rows whose TSV-sourced `record["outcome"]` (`voting_result`) is `out_of_scope` or `exonerated` (verdict gate mirroring implement countable set).
  - Use passed-in `i_fn_rows` (not `i_all`) for implement false-negative metrics.
- Add `_section_false_negatives(i_fn_rows, d_fn_inscope, cutoff=None, since_version=None)`.
- **Wire unconditionally in `render()`**:
  - On the empty-corpus path (`not i_all and not d_inscope`), still call `_section_false_negatives(i_fn_rows or [], d_fn_inscope, cutoff=cutoff, since_version=since_version)` **before** returning so zero-finding runs print `## False-negative / under-acceptance metrics` with `n/a` rows instead of omitting the section.
  - On the normal path, after `_section_accepted_low_value(...)` and before `_section_prepost(...)`, always call:
    - `out += _section_false_negatives(i_fn_rows or [], d_fn_inscope, cutoff=cutoff, since_version=since_version)`
  - Do not gate the whole section on `cutoff` or `since_version`; only pre/post subtables inside the helper are cutoff-gated.
- Render **## False-negative / under-acceptance metrics** with:
  - **Neutral-rate by severity tier**:
    - Include implement false-negative corpus (`i_fn_rows`) and design false-negative in-scope (`d_fn_inscope`).
    - Count implement neutral from TSV `voting_result == "neutral"`; count design neutral from TSV-sourced `record["outcome"] == "neutral"`.
    - Bucket tiers from reviewer-claimed `body_severity` via `_reviewer_claimed_tier()` only.
    - Show `neutral / total` by corpus and tier.
    - Include per-run count when runs are available.
  - **Important-reject-rate**:
    - Use the same `_reviewer_claimed_tier()` on reviewer-claimed `body_severity` (raw alias path included).
    - Include only rows whose normalized tier is `important`.
    - Count implement 0-YES rejection as `voting_result == "rejected"`; count design as TSV-sourced `record["outcome"] == "rejected"`.
    - Show rejected count, total important count, and rate.
    - Exclude OOS ids, scope-drift rows, and non-countable verdicts from denominators.
- When `cutoff` or `since_version` is present, add pre/post subtables for both metrics inside the helper; filter implement rows on `record["period"]`, design rows on `record["period"]`.
- Skip `period == "unknown"` rows in pre/post subtables (mirror `_section_prepost()` period filtering).
- Keep existing `_section_prepost()` output unchanged.
- Update `main()`: after `extract(...)`, call `build_impl_fn_rows(log_root, cutoff=cutoff, since_version=args.since_version)` and pass result into `render(..., i_fn_rows=...)`.

### UPDATED: `skills/fluff-analysis/scripts/fluff-analysis.md`

Document the new section.

- Add neutral-rate and important-reject-rate to the Purpose section.
- Define:
  - neutral-rate as `neutral / total` by reviewer-claimed severity tier.
  - important-reject-rate as `rejected / reviewer-claimed-important`.
- State that **both metrics** tier from normalized `body_severity` only via `_reviewer_claimed_tier()`; missing `body_severity` buckets as `(none)` and does not count toward reviewer-claimed-important.
- State that raw `blocker`, `critical`, and `blocking` map to reviewer-claimed `important` **before** corpus-specific normalization inside `_reviewer_claimed_tier()` only; shared `normalize_severity()` / `normalize_design_severity()` remain unchanged for baseline tables (design shared normalizer still maps raw `blocker`/`critical` to `(none)` for baselines).
- State that **both implement and design** panel verdicts use TSV `voting_result` as authoritative: implement via TSV-primary join with optional JSONL `body_severity` enrichment; design via `record["outcome"]` populated from TSV in `_extract_one_design_tsv`. JSONL `outcome` alone is not used for implement or design false-negative metrics.
- State that implement false-negative rows are built in `main()` / `extract()` from per-run classification TSV (not inside `render()`).
- State that implement join is round- and token-aware (mirrors `rejected_analysis._lookup_jsonl_record`); id equality between TSV `FINDING_*` and JSONL `REJ_*` is not required.
- State that eligibility excludes OOS ids, scope-drift deferred rows (`scope` in `oos`, `out_of_scope`, `out-of-scope`), and non-countable verdicts (`out_of_scope`, `exonerated`, etc.; countable set is `accepted`, `neutral`, `rejected` only) for both corpora.
- State that the metrics are diagnostic-only.
- Note that existing baseline tables still lump `neutral` into not-accepted math and may use legacy severity fallbacks.
- Note that empty log roots still emit the false-negative section with `n/a` rows.

### UPDATED: `skills/fluff-analysis/scripts/test-fluff-analysis.sh`

Extend the synthetic fixture and assertions.

- Add production-shaped implement neutral coverage: TSV row with `FINDING_*` id, `voting_result=neutral`, reviewer-claimed `body_severity=important`, paired JSONL row with mismatched `REJ_CR*` id and `outcome:"rejected"` linked via prose/`FINDING_N` token (not id equality); assert implement neutral-rate counts the TSV verdict.
- Add at least one design in-scope `neutral` row with `body_severity=important` and TSV `voting_result=neutral` (include a design row with `body_severity=blocker` or `critical` to cover false-negative-only raw aliases before normalization).
- Add at least one reviewer-claimed-important rejected implement row with `body_severity=blocking` in TSV/JSONL to cover the false-negative alias path.
- Add at least one design in-scope row with non-OOS id and `scope=oos` in TSV; assert it does **not** affect false-negative denominators.
- Add at least one design in-scope `FINDING_*` row with `voting_result=out_of_scope` (no trailing `scope` column); assert it does **not** affect false-negative denominators.
- Add implement rows excluded by OOS id, `scope=oos` (production-shaped deferred OOS on `FINDING_*` ids), `voting_result=out_of_scope`, or `voting_result=exonerated`; assert they do **not** affect false-negative denominators.
- Assert the new section heading appears on default runs (no `--cutoff` / `--since-version`).
- Assert the new section heading appears on empty-log-root / zero-finding runs.
- Assert neutral-rate rows include both implement and design in-scope corpora.
- Assert important-reject-rate appears and includes the `body_severity=blocking` implement row.
- Assert `--since-version` or `--cutoff` renders pre/post false-negative rows (implement rows carry `period`).
- Adjust total record-count assertions affected by added fixture rows.

### UPDATED: `skills/voter-calibration/scripts/voter-calibration.py`

Add a per-voter false-negative view without using `voter_agreement_rows_from_tsv()` for neutral-inclusive counting.

- Extend `CorpusStats` with a parallel store, e.g. `false_negative_rows: list[dict[str, object]]`, separate from agreement `rows`.
- Add a direct TSV reader helper in this file, e.g. `_false_negative_rows_from_tsv(text, *, panel_kind)`.
  - Use `voting._dict_rows_from_tsv` (or `_legacy_compact_rows_from_tsv` when compact) plus local header checks.
  - Import and use `voting._normalize_vote_cell` for every YES/NO parse; count only normalized `YES` votes (so `EXONERATE` and other non-YES normalized cells do not increment `yes_votes`).
  - Preserve supported TSV shapes as header supersets, not exact-width matches:
    - 23-column design (current `FINDINGS_CLASSIFICATION_HEADER` with trailing `body_severity` and `scope`).
    - 22-column design.
    - 21-column design.
    - 21-column code-review.
    - compact 18-column code-review.
  - Require the same core fields as `classification_tsv_schema_supported()`; treat trailing columns (`scope`, etc.) as optional.
  - Mirror `_voter_label()` fallback rules for design, code-review, and compact labels (`v1`, `v2`, `v3`).
  - Retain `scope` on each parsed row.
- **Eligibility gate** (distinct from agreement ingest):
  - Skip rows that would increment `malformed_rows` (bogus `voting_result`, unparseable vote patterns).
  - Skip rows where `scope` is `oos`, `out_of_scope`, or `out-of-scope` (mirror `voting._classification_row_is_oos` / `rejected_analysis._scope_is_oos`).
  - Skip single-voter panels (fewer than two parseable YES/NO votes via `_normalize_vote_cell`).
  - **Include** rows with `voting_result in {"accepted", "neutral", "rejected"}` that pass the above gates and have at least two parseable votes. Do **not** treat neutral panels as `ineligible_rows` for this view.
  - Count ineligible single-voter and malformed rows separately; do not reuse `voter_agreement_rows_from_tsv()` neutral exclusion.
- For each eligible row:
  - Count each parseable normalized `YES` vote.
  - Count a false-negative YES when the outcome is `neutral` or `rejected`.
  - Aggregate by panel and voter.
  - Add global rows by reusing the existing global pattern.
- Update `_parse_file_into_stats()` to accumulate agreement rows unchanged **and** append false-negative rows from the new reader into `stats.false_negative_rows`.
- Update default-path discovery in `main()` to collect false-negative rows in parallel with agreement rows.
- Update `_collect_era_corpora()` / `_render_era_slice()` to pass `stats.false_negative_rows` into false-negative rendering for each era slice; leave agreement math on existing `stats.rows`.
- Update `_render()` to accept false-negative rows and render **## Per-voter False-negative YES Rate**:
  - Columns/fields: panel, voter, yes_votes, neutral_yes, rejected_yes, false_negative_yes, false_negative_yes_rate.
  - `false_negative_yes_rate` is `false_negative_yes / yes_votes` when `yes_votes > 0`; otherwise emit `n/a` (match other zero-denominator handling; never divide by zero).
  - Include empty `n/a` row when no rows qualify.
- Add the same false-negative section inside each era slice when `--era` is used.
- Add optional realized-outcome diagnostic section:
  - Add flags `--realized-outcomes`, `--repo`, and `--filed-issue-details-json` to `_parse_args()`; thread both through the realized-outcomes loader.
  - When set, resolve repo via `--repo` override when provided; otherwise use a fail-open resolver that tries git-only `remote.origin.url` parsing first (or wraps `_detect_repo()` / `gh repo view` in `FileNotFoundError` handling) so missing `gh` CLI does not abort before degraded rendering.
  - Before issue lookup, filter filed-OOS candidate numbers from `iter_filed_oos_records()` against the resolved repo using each record's `issue_url` and `extract_repo_from_url()` (mirror `run_main()`); skip cross-repo/fork candidates before `_fetch_filed_oos_issue_details()`.
  - Fetch issue data before calling calibration:
    - When `--filed-issue-details-json` is provided, load filed issue details from that path (offline harness path).
    - Otherwise bulk issue load via existing analyze-issues fetch helpers (`fetch_main` + `load_issues`) when repo is available.
    - Write the bulk issue JSON dump to a **per-run unique temp file** (e.g. `tempfile.NamedTemporaryFile` or `tempfile.mkstemp` under the process temp dir), not a shared repo-named dump path, so concurrent calibration runs cannot clobber each other.
    - Wrap `fetch_main()` and `_fetch_filed_oos_issue_details()` in `FileNotFoundError` handling (missing `gh` CLI) and route to the degraded-note path with exit code **0**, not a fatal report abort.
    - Wrap `load_issues()` in the existing degraded-note path: catch `SystemExit` from `load_issues()` (parse failures, malformed dumps, duplicate-heavy skips above threshold) and treat it as a degraded realized-outcomes path with exit code **0**.
    - Collect repo-filtered filed-OOS candidate numbers and fetch filed issue details via `_fetch_filed_oos_issue_details()` (or load from `--filed-issue-details-json` when provided).
  - On successful load, call `ground_truth_voter_calibration()` from `larch.issue.analyze_issues` with `verdict_mode=False`, passing non-empty `issues`, `filed_issue_details`, `repo`, `log_root`, `enrichment_degraded`, and `targeted_fetch_degraded`.
  - **Append the returned markdown** into `_render()` output (and into each era slice when `--era` is set); do not stop at fetch/load wiring alone.
  - Catch narrow expected failures from missing GitHub, missing repo, bulk fetch failure, `FileNotFoundError`, `load_issues` `SystemExit`, repo-filtered empty candidate sets, or insufficient corpus.
  - Render a short skipped/degraded note instead of failing the report or changing exit status on those paths.
  - Do not make this path required for the core offline metrics.

### UPDATED: `skills/voter-calibration/scripts/voter-calibration.md`

Update the contract.

- Add the false-negative YES section to the output list.
- Define the denominator as each voter's parseable normalized `YES` votes on eligible panels (`accepted`, `neutral`, `rejected`), using `voting._normalize_vote_cell` (so `EXONERATE` does not count as YES).
- Define the numerator as YES votes on `neutral` or `rejected` findings.
- State that `false_negative_yes_rate` is `n/a` when `yes_votes` is zero.
- State that neutral panels are included in this false-negative view (eligible when `voting_result` is `neutral` or `rejected` with two or more parseable votes) but remain excluded from existing agreement denominators.
- State that rows with `scope=oos` / `out_of_scope` / `out-of-scope` are excluded from false-negative YES totals.
- Document supported design header supersets (23-column current shape with optional trailing columns).
- Document the optional `--realized-outcomes` flag plus `--repo` override and `--filed-issue-details-json` offline input; per-run isolated issue-dump temp storage; repo/`issue_url` filtering before targeted fetch; fail-open repo resolution and `FileNotFoundError` / missing-`gh` degradation; `load_issues()` `SystemExit` degradation; successful `ground_truth_voter_calibration(verdict_mode=False)` rendering; and degraded fallback when GitHub/repo data is unavailable or the dump is malformed.
- State that all new outputs are diagnostic-only.

### UPDATED: `skills/voter-calibration/scripts/test-voter-calibration.sh`

Extend the fixture and assertions.

- Reuse existing neutral rows where possible.
- Add fixture coverage for:
  - YES on accepted.
  - YES on neutral.
  - YES on rejected.
  - `EXONERATE` vote cell that must **not** increment `yes_votes` or false-negative YES totals.
  - compact code-review labels.
  - compact 18-column TSV rows with `voting_result=neutral` and `voting_result=rejected` where at least one voter casts normalized YES; assert those rows affect `false_negative_yes` totals and appear in **## Per-voter False-negative YES Rate**.
  - design fallback voter labels.
  - 23-column design header with `scope` trailing column.
  - design row with non-OOS id and `scope=oos` that must **not** enter false-negative YES totals.
  - bogus `voting_result` row that must stay out of false-negative totals but still count as malformed.
  - at least one voter row with zero parseable YES votes; assert `false_negative_yes_rate` renders `n/a`.
- Assert the false-negative section appears on default and era reports.
- Assert at least one voter has a non-zero neutral/rejected YES rate.
- Assert existing agreement counts still exclude neutral rows.
- Assert era reports include the false-negative section per emitted era.
- Assert malformed/ineligible rows do not inflate false-negative YES counts.
- Add a degraded realized-outcome assertion for `--realized-outcomes` with no live GitHub dependency (missing repo, missing `gh` / `FileNotFoundError`, or empty fetch path renders skipped note, exit 0).
- Add a degraded realized-outcome assertion for malformed/truncated issue dump or `load_issues()` threshold abort (renders degraded/skipped note, exit 0, no `SystemExit` escape).
- Add a success-path assertion that `--realized-outcomes` with injected issues via offline fixture and `--filed-issue-details-json` (and optional `--repo` override) appends the realized-outcome markdown section when load succeeds.

## Edge cases

- Empty corpora should render `n/a` rows, not crash; the false-negative section must still appear on zero-finding / empty-log-root runs.
- Unknown severity should use `(none)`.
- Missing `body_severity` should not count as reviewer-claimed-important and should not use prose/modal severity fallback in false-negative metrics.
- Raw design `blocker`/`critical`/`blocking` must alias to `important` in `_reviewer_claimed_tier()` **before** `normalize_design_severity()` (which maps `blocker`/`critical` to `(none)`).
- `scope=oos`, `out_of_scope`, `out-of-scope`, and OOS ids should remain out of implement and design false-negative denominators.
- Design rows with TSV `voting_result=out_of_scope` or `exonerated` must be excluded from `d_fn_inscope` even when id is non-OOS and `scope` is empty.
- Implement 1-YES neutrals appear as JSONL `outcome:"rejected"` with TSV `voting_result=neutral`; metrics must use TSV verdict and token-aware join, not JSONL id or outcome.
- Design neutral/reject counts must use TSV `voting_result` on `d_fn_inscope` records, not JSONL (design logs have no `review-findings-full.jsonl`).
- Implement false-negative rows must not be built inside `render()` without `log_root`; `main()` passes prebuilt `i_fn_rows`.
- Malformed TSV rows should keep current skipped or malformed accounting and must not enter false-negative YES totals.
- `EXONERATE` and other non-YES normalized vote cells must not increment false-negative `yes_votes`.
- Voters with only NO or missing votes must render `n/a` rate, not divide by zero.
- Compact code-review TSVs must preserve `v1`, `v2`, `v3` labels and support neutral/rejected false-negative counting.
- 23-column design TSVs with trailing `scope` must parse and exclude `scope=oos` for false-negative metrics.
- Implement `voting_result=exonerated` and other non-countable verdicts must not enter `i_fn_rows`.
- Era mode must exclude runs with invalid `started_at` as it does today.
- Realized-outcome matching can undercount resurfaced bugs; render it as conservative and diagnostic.
- Filed-OOS candidates from other repos/forks must be filtered via `extract_repo_from_url()` before targeted fetch.
- Concurrent `--realized-outcomes` runs must not share a repo-named issue dump path.
- Missing `gh` during repo resolution, `fetch_main()` failures, `load_issues()` failures (including `SystemExit`), and repo-filter mismatches must degrade the realized-outcomes section without changing report exit status.
- Successful realized-outcomes fetch must still append the calibration markdown section.
- Neutral panels must be eligible for false-negative YES counting; only single-voter and malformed rows stay ineligible.
- Pre/post false-negative subtables require `period` on implement rows; skip `period == "unknown"`.

## Failure modes

- Building `i_fn_rows` inside `render()` leaves implement metrics at zero because `log_root` is unavailable. Build in `main()` / `extract()` and pass explicitly.
- Id-equality TSV/JSONL join drops neutrals and mis-pairs rounds. Iterate TSV rows as primary; enrich via `_records_by_round_and_token` / `_lookup_jsonl_record` / `_finding_tokens`.
- Reusing `i_all` reproduces JSONL-outcome bugs and missing TSV fields. Keep a separate TSV-backed implement false-negative schema.
- Design `out_of_scope` / `exonerated` verdict rows in `d_fn_inscope` dilute rates. Add explicit verdict gate alongside OOS id/scope filters.
- Post-normalization alias for design `blocker`/`critical` leaves rows in `(none)`. Inspect raw severity before corpus normalizers.
- A direct TSV helper can drift from `voting.py` label fallback rules or vote normalization. Keep the helper small, mirror existing fallback labels, gate eligibility separately from agreement ingest, and pin YES parsing to `voting._normalize_vote_cell`.
- Parallel false-negative row collection can drift from era/default agreement ingestion if not updated together. Feed both paths through `_parse_file_into_stats()`.
- Empty-corpus early return can skip the false-negative section if wired after the guard. Always call `_section_false_negatives()` on both empty and non-empty paths before any early return that omits later sections.
- Design `scope=oos` rows with non-OOS ids can overstate false-negative signal if only `is_oos_id` is filtered. Use `d_fn_inscope` with `_scope_is_oos()` and verdict gate.
- Implement `scope=oos` deferred rows can inflate denominators if only `out_of_scope` is checked. Match `rejected_analysis._scope_is_oos` (`oos`, `out_of_scope`, `out-of-scope`).
- Vague "countable verdict set" can admit `exonerated`. Pin to `{accepted, neutral, rejected}`.
- Missing `period` on `i_fn_rows` breaks pre/post false-negative tables. Stamp in `_impl_fn_rows_from_run` using existing `period_of*` helpers.
- Extending shared `normalize_severity()` with `blocking` would silently shift baseline buckets. Keep aliases local to `_reviewer_claimed_tier()` only.
- JSONL-only implement neutral fixtures can pass CI while production logs stay broken. Mirror TSV `voting_result=neutral` + mismatched `REJ_*` JSONL + token join in harness coverage.
- Copying agreement neutral ineligibility yields zero false-negative YES signal. Eligibility must include neutral panels with two or more parseable votes.
- Unfiltered filed-OOS candidates can fetch wrong-repo issues. Apply the same repo/`issue_url` guard as `analyze_issues.run_main()`.
- Unguarded `_detect_repo()` / `gh repo view` can abort before degraded path. Wrap repo resolution fail-open.
- `yes_votes == 0` can crash or print bogus rates. Guard with `n/a`.
- Missing `gh` can raise `FileNotFoundError` and abort the report. Catch at repo resolution and both fetch call sites.
- Realized-outcomes wiring that stops at fetch/load leaves the flag non-functional on success. Append `ground_truth_voter_calibration()` markdown on the happy path.
- Compact neutral/rejected rows without harness coverage can ship with accepted-only parsing bugs.

## Testing strategy

- Run `bash skills/fluff-analysis/scripts/test-fluff-analysis.sh`.
- Run `bash skills/voter-calibration/scripts/test-voter-calibration.sh`.
- Run `make test-fluff-analysis`.
- Run `make test-voter-calibration`.
- For quick manual checks:
  - `python3 skills/fluff-analysis/scripts/fluff-analysis.py --log-root larch-logs --since-version 49.0.0`
  - `python3 skills/voter-calibration/scripts/voter-calibration.py --log-root larch-logs --min-votes 1`
  - optional: `python3 skills/voter-calibration/scripts/voter-calibration.py --log-root larch-logs --realized-outcomes`
  - optional offline: `python3 skills/voter-calibration/scripts/voter-calibration.py --log-root larch-logs --realized-outcomes --repo owner/repo --filed-issue-details-json /path/to/fixture.json`

## Acceptance

- Run `bash skills/fluff-analysis/scripts/test-fluff-analysis.sh`.
- Run `bash skills/voter-calibration/scripts/test-voter-calibration.sh`.
- Run `make test-fluff-analysis`.
- Run `make test-voter-calibration`.
- For quick manual checks:
  - `python3 skills/fluff-analysis/scripts/fluff-analysis.py --log-root larch-logs --since-version 49.0.0`
  - `python3 skills/voter-calibration/scripts/voter-calibration.py --log-root larch-logs --min-votes 1`
  - optional: `python3 skills/voter-calibration/scripts/voter-calibration.py --log-root larch-logs --realized-outcomes`
  - optional offline: `python3 skills/voter-calibration/scripts/voter-calibration.py --log-root larch-logs --realized-outcomes --repo owner/repo --filed-issue-details-json /path/to/fixture.json`

review_status: complete
rounds_completed: 5
diff_added: 640
diff_deleted: 45
mechanical_churn: false
diff_lines: 685
