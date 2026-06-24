## Goal
Implement issue #5127: [IMPLEMENTING] review-points-overhaul-II Ground-truth voter loop (score findings against realized outcomes).

## Implementation Plan
## Plan

## Scope

Implement the diagnostic in `/analyze-issues`, not `/voter-calibration`.

Reason:
- `/analyze-issues` already owns issue-fate enrichment and OOS reconciliation.
- The new signal needs GitHub issue state and committed run logs.
- `/voter-calibration` can stay focused on panel self-agreement and severity spread.

`approach-synthesis.txt` is `NO_SKETCHES`, so this plan uses direct repository inspection only.

## Approach

Add a new `## Ground-truth Voter Calibration` section to the `/analyze-issues` report.

The section should:
- Scan committed `larch-logs`.
- Ingest classification TSV rows through a **ground-truth-specific** shared prep helper (`classification_row_panel_inputs`), **not** `voter_agreement_rows_from_tsv()`.
- Retain raw TSV dicts, compact flags, normalized `voter_votes`, and the post-selection parsed header for every row.
- Bind `panel_kind` per discovered TSV path (`design` vs `code-review`) and thread it through schema gating, prep, and voter attribution.
- Branch each row on OOS identity before in-scope bucket assignment, passing `(row, header)` into the OOS predicate.
- Drop ineligible rows (neutral verdicts, MAV placeholders, fewer than two parseable `vN_vote` cells) before realized-outcome bucketing.
- Use `voter_agreement_row_from_panel` only for eligibility and per-voter `voter`/`vote`/`missing` extraction; **never** copy `agree`/`disagree` into ground-truth metrics.
- Bind `panel_verdict` from authoritative prose sources, not TSV `voting_result` alone.
- For OOS rows, bind a separate `oos_panel_verdict` (`accepted` / `rejected` / weak) before fate scoring; do not infer OOS acceptedness from implement JSONL `outcome=out_of_scope`.
- Join finding prose across implement alias ids and design/review log shapes.
- Anchor temporal matching on per-run `manifest.json` `started_at` for cross-run ordering and on `round_num` for same-run ordering.
- Match rejected findings against later issues or later accepted findings with conservative signatures using a cleaned diagnostic path extractor.
- Score accepted OOS rows through the same filed-issue join contract as `fate_adjusted_oos_scoring`; restrict decisive OOS fate scoring to accepted OOS rows only.
- Compute per-voter aligned/misaligned from decisive realized outcomes only; never reuse panel self-agreement `agree`/`disagree` bits.
- Count only decisive realized-outcome buckets in per-voter accuracy rates and error counters.
- Compute `realized_alignment_rate` from decisive aligned/misaligned ballots only.
- Label weak evidence, ineligible rows, provisional OOS fates, gc-slimmed voter loss, timestamp-degraded matches, and enrichment degradation as non-decisive or qualified.
- State that the report is diagnostic only.

Do not change:
- Live voting thresholds.
- Reviewer points.
- Token allocation.
- `/voter-calibration` behavior.
- OOS filing behavior.
- The existing `## Fate-adjusted OOS Scoring` section.

## Ground-truth semantics

Use conservative buckets.

**Ground-truth row prep (not panel self-agreement):**
- `voter_agreement_rows_from_tsv()` is **panel-self-agreement only**. Its `.rows` are agreement-shaped dicts that omit raw TSV fields and the post-selection parsed header. **Do not call it for ground-truth ingest or later-run index construction.**
- Ground-truth ingest **must** use `classification_row_panel_inputs(text, *, panel_kind)` (or equivalent shared helper in `python/voting.py`) that mirrors the internal steps of `voter_agreement_rows_from_tsv` but returns per-row prep objects containing:
  - raw `dict[str, str]` row retention (`finding_id`, `scope`, `reviewer_slots` / `finding_reviewers`, `voting_result`, `vN_*`, run/round metadata),
  - compact / `label_compact` flags,
  - `_voter_label`-built `voter_votes` and optional `voter_severities`,
  - the **parsed header after compact/legacy selection** for `(row, header)` OOS routing.
- After prep, call `voter_agreement_row_from_panel` on each prep object for eligibility only; extract `voter`/`vote`/`missing` from that output and ignore `agree`/`disagree`.

Row routing:
- Before any in-scope accepted/rejected bucket logic, branch each classification row with the same OOS predicate as `voting._classification_row_is_oos(row, header)` (`scope == oos` when `"scope" in header`, else `finding_id` prefixed `OOS_`).
- The shared prep helper must retain the parsed header after compact/legacy selection and pass that header into every OOS predicate call. Do not call the predicate with an empty header or a pre-compact header when the committed row carries `scope=oos` on a `FINDING_*` id.
- OOS rows never enter in-scope accepted/rejected resurfacing buckets.

Eligibility gate (before realized-outcome work):
- After OOS branching, retain a row for ground-truth work only when shared TSV prep plus `voter_agreement_row_from_panel` returns non-`None`.
- Mirror `voter_agreement_rows_from_tsv` ineligible handling: neutral verdicts, fewer than two parseable `vN_vote` cells, and MAV placeholder rows (`voting_result=rejected` with empty `vN_*` cells) are excluded from steps 7–9.
- Count excluded rows in corpus bullets as ineligible/weak-unknown; they never receive decisive realized-outcome buckets and never contribute per-voter ballots.
- TSV `voting_result` is used only for vote-cell parsing, ineligible detection, and **OOS accepted/rejected binding**; it is not used for in-scope accepted/rejected resurfacing branching once `panel_verdict` is bound.

Panel verdict binding:
- After prose join, bind `panel_verdict` from authoritative sources in priority order:
  - **Implement**: joined JSONL `outcome` (`accepted` / `rejected`; `out_of_scope` is not an in-scope verdict).
  - **Design**: for a classification TSV at `.../plan-review/round-{round_num}/findings-classification.tsv`, bind membership from the **same-round round-local** pair `.../plan-review/round-{round_num}/accepted-plan-findings.md` and `.../plan-review/round-{round_num}/rejected-findings.md` first (index `### FINDING_<n>:` membership derived from the TSV path's `round_num`). Consult run-root `accepted-plan-findings.md` / `rejected-findings.md` only when that round-local pair is absent. When both round-local and run-root markdown exist and disagree on membership for the same `FINDING_<n>`, mark weak/non-decisive. Use run-root `review-findings-full.jsonl` only when round-local markdown is absent or ambiguous; on markdown/JSONL disagreement mark weak/non-decisive.
  - **Standalone review**: joined NDJSON `outcome`.
- When authoritative verdict sources disagree with TSV `voting_result`, or the round is MAV-degraded (`main-agent-vote-required` placeholder semantics), mark the row weak/non-decisive instead of bucketing from TSV alone.
- All in-scope accepted/rejected resurfacing and revert helpers consume the bound `panel_verdict` field only.

**OOS panel verdict binding (before fate scoring):**
- Implement JSONL and similar prose often store `outcome=out_of_scope` for both accepted and rejected OOS rows; **do not** use JSONL `outcome` alone to decide whether an OOS row was panel-accepted.
- After OOS routing and eligibility, bind `oos_panel_verdict` for each OOS row from, in order:
  1. normalized TSV `voting_result` when it is `accepted` or `rejected` (post-MAV-placeholder eligibility), or
  2. parsed round-local vote-tally `Result` when present and unambiguous, else weak/non-decisive.
- Restrict decisive OOS fate scoring and per-voter OOS ground-truth alignment to rows with `oos_panel_verdict == accepted`.
- Rows with `oos_panel_verdict == rejected`, neutral/exonerated TSV results, verdict disagreement, or missing `oos_panel_verdict` stay non-decisive for OOS fate buckets and per-voter counters even when a filed issue later docks.

Accepted in-scope findings (`panel_verdict == accepted`):
- `accepted_no_counterevidence`: accepted finding with no later matching reversal signal. Non-decisive; absence of evidence is weak.
- `accepted_reverted_or_regressed`: accepted finding with later matching issue/finding text that includes reversal or regression language. **Decisive**; contradicts acceptance (NO aligned, YES misaligned).

Rejected in-scope findings (`panel_verdict == rejected`):
- `rejected_resurfaced`: rejected finding whose title, cleaned file path, or concern strongly matches a later bug/fix issue or later accepted finding. **Decisive**; false negative for NO voters (YES aligned, NO misaligned).
- `rejected_not_observed`: no later strong match. Non-decisive.

Accepted OOS findings:
- Only after `oos_panel_verdict == accepted`, reuse `classify_oos_issue_fate` after the same filed-OOS join used by `fate_adjusted_oos_scoring`.
- **Decisive contradicting OOS outcomes only**: `docked closed-unfixed`, `docked combined-away`.
- **Non-decisive / weak buckets**: rejected/neutral/exonerated OOS panel results, `kept by PR`, `provisional open`, `provisional unknown`, `enrichment unavailable`, ambiguous stable-id buckets, and missing filed-issue joins.
- Provisional OOS fates and rejected OOS panel results must not inflate `realized_alignment_rate`.
- Keep the existing fate-adjusted OOS section unchanged.

Temporal ordering:
- **Cross-run**: later evidence must be after source run `manifest.json` `started_at` when present; fallback `createdAt` / issue timestamps for ordering hints only when `started_at` is absent.
- **Same-run**: when `run_id` matches, treat evidence as later only when `round_num` is greater (from TSV path, JSONL `round_num`, or round-local artifacts). Do not treat a round-2 accepted finding as later evidence for a round-1 source row using `started_at` alone.
- Without provable ordering, keep matches timestamp-degraded / non-decisive unless another later-ordering signal is present.

Per-voter ground-truth alignment (not panel self-agreement):
- From `voter_agreement_row_from_panel`, take only `voter`, `vote`, and `missing`. Ignore `agree` and `disagree`; those encode panel self-agreement, not realized outcomes.
- For a decisive realized outcome that supports acceptance (`rejected_resurfaced`): YES is aligned, NO is misaligned.
- For a decisive realized outcome that contradicts acceptance (`accepted_reverted_or_regressed`, docked OOS fates on accepted OOS rows): NO is aligned, YES is misaligned.
- Missing and `JUDGE_ERROR` votes stay missing.
- Neutral panel verdicts, ineligible rows, rejected OOS panel results, and weak `oos_panel_verdict` rows stay excluded.

Per-voter `realized_alignment_rate`:
- Compute only from decisive realized-outcome ballots: `realized_alignment_rate = aligned / (aligned + misaligned)`.
- Exclude missing, ineligible, weak, provisional, verdict-disagreement, rejected-OOS-panel, and timestamp-degraded rows from numerator and denominator.
- When `aligned + misaligned == 0`, emit `n/a` (or omit the rate); never divide by eligible rows or include missing/`JUDGE_ERROR` in the denominator.

Explicit error counters (decisive buckets only):
- `false_positive_yes`: increment when the voter cast YES but the decisive realized outcome contradicts acceptance (`accepted_reverted_or_regressed`, docked OOS contradicting buckets on accepted OOS rows).
- `false_negative_no`: increment when the voter cast NO but the decisive realized outcome supports acceptance (`rejected_resurfaced`).
- Exclude missing/`JUDGE_ERROR` and all non-decisive buckets from both counters.

## Files to modify/create

### UPDATED: python/findings_ledger.py

Add read-only helpers for ledger-shaped evidence.

Suggested helpers:
- `read_rows(path: Path) -> list[dict[str, str]]`
- `row_signature(row: Mapping[str, str]) -> str` or equivalent local utility if useful.

Constraints:
- Keep existing write behavior unchanged.
- Treat malformed headers as empty evidence.
- Use existing column constants.
- Do not create directories or files from the new helpers.
- Preserve existing sanitization assumptions.

### UPDATED: python/voting.py

Add ground-truth ingest surface (required, not optional):
- Export a small public wrapper for `_classification_row_is_oos(row, header)`.
- Add `classification_row_panel_inputs(text, *, panel_kind) -> list[ClassificationRowPrep]` that mirrors `voter_agreement_rows_from_tsv` internals but returns ground-truth prep objects:
  - `classification_tsv_schema_supported` gate.
  - `_dict_rows_from_tsv` / `_legacy_compact_rows_from_tsv` selection.
  - Compact flag and `label_compact` detection.
  - Header-aware `finding_reviewers` vs `reviewer_slots` selection (same rule as `voting.py` scoreboard path).
  - `_voter_label`-built `voter_votes` and optional `voter_severities`.
  - Raw `dict[str, str]` row retention (`finding_id`, `scope`, `reviewer_slots`, `voting_result`, `vN_*`, run/round metadata).
  - **Return the parsed header used after compact/legacy selection** alongside each prep object so callers pass `(row, header)` into the OOS predicate.
- Prep objects must be suitable for `voter_agreement_row_from_panel` without dropping join keys or header context.
- Document in helper docstring that `voter_agreement_rows_from_tsv()` remains panel-self-agreement only and must not be used for ground-truth row materialization.

Do not change live tally or scoreboard behavior.

### UPDATED: python/analyze_issues.py

Add the diagnostic section.

Implementation outline:

1. Add small immutable dataclasses or typed dictionaries for:
   - classification row evidence (raw TSV fields, parsed header, panel kind, run id, round, path, reviewer attribution column).
   - finding prose evidence (`panel_verdict`, `oos_panel_verdict`, category, paths, text).
   - realized outcome evidence.
   - per-voter realized metrics.

2. Add a classifier discovery helper that mirrors `/voter-calibration` `_discover` and **pins `panel_kind` per path**:
   - Return `list[tuple[panel_kind, path]]`.
   - `larch-logs/design/*/plan-review/round-*/findings-classification.tsv` → `panel_kind="design"`.
   - `larch-logs/implement/*/round-*/findings-classification.tsv` → `panel_kind="code-review"`.
   - `larch-logs/review/*/review-findings-classification-round-*.tsv` → `panel_kind="code-review"` only when `classification_tsv_schema_supported(text, panel_kind="code-review")` passes.
   - Thread `panel_kind` through schema gate, `classification_row_panel_inputs`, and per-voter attribution for every discovered file.

3. Parse classification TSVs with ground-truth shared prep (**never `voter_agreement_rows_from_tsv()`**):
   - Gate each file with `voting.classification_tsv_schema_supported(text, panel_kind=...)`.
   - Parse through `classification_row_panel_inputs(text, panel_kind=...)` to raw rows, normalized `voter_votes`, compact flags, reviewer-column attribution, and the **post-selection parsed header**.
   - Retain `finding_id`, `scope`, `finding_reviewers` or `reviewer_slots`, `voting_result`, `vN_vote`, `vN_tool`, `vN_severity`, and path-derived run/round metadata.
   - **Branch first** with `voting._classification_row_is_oos(row, header)` (or exported wrapper) on every row before bucket assignment; never call the predicate without the header returned by prep.
   - **Eligibility gate**: call `voter_agreement_row_from_panel`; if it returns `None`, count the row ineligible/weak-unknown and skip steps 4–9 for that row.
   - For eligible rows, extract per-voter `voter`/`vote`/`missing` only from the panel helper output. Do not copy `agree`/`disagree` into ground-truth metrics.
   - For OOS rows, bind `oos_panel_verdict` from TSV `voting_result` or parsed vote-tally `Result`; do not use JSONL `outcome=out_of_scope` as accepted/rejected signal.

4. Add per-run manifest binding while scanning each run dir:
   - Best-effort read `manifest.json` `started_at` via existing `parse_iso`; fallback `updated_at` only for cross-run ordering hints.
   - Pass `started_at` into cross-run conservative matchers.
   - Derive `round_num` from TSV path and joined prose for same-run ordering.
   - When `started_at` is absent, allow matching only with `timestamp-degraded` reason and exclude from decisive counts unless a later `createdAt`, greater `round_num`, or later-run timestamp proves ordering.

5. Add finding prose extraction across log shapes:
   - **Implement**: prefer `larch-logs/implement/*/review-findings-full.jsonl`; use `prose_body`, `category`, `outcome`, `round_num`, and `id`.
   - **Implement id bridge (primary)**: for rejected in-scope rows, resolve TSV `FINDING_N` to JSONL ids like `REJ_CR<round>_<suffix>` by indexing prose headings such as `### FINDING_N:` within the same `run_id` + `round_num`; do not assume JSONL numeric suffix equals TSV N. Keep `OOS_CR<round>_<n>` as a secondary alias path.
   - **Implement id bridge (secondary)**: direct `finding_id` join when ids match; otherwise index both JSON `id` and parsed `FINDING_<n>` / `OOS_<n>` tokens from `prose_body`, keyed by `run_id` + `round_num`. Use normalized `finding_reviewers` / `reviewer_slots` from step 3 in the alias bridge. Secondary bridge: scope/outcome mapping (`oos` vs `out_of_scope`) and bound `panel_verdict` / `oos_panel_verdict`. Round-local markdown is last resort only.
   - **Design**: for same-round verdict binding on a TSV at `.../plan-review/round-N/findings-classification.tsv`, read `.../plan-review/round-N/accepted-plan-findings.md` and `.../plan-review/round-N/rejected-findings.md` **first** (index `### FINDING_<n>:` membership). Fall back to run-root `accepted-plan-findings.md` / `rejected-findings.md` only when the round-local pair is absent. When round-local and run-root markdown both exist and disagree, mark weak/non-decisive. Use run-root `review-findings-full.jsonl` only when round-local markdown is absent or ambiguous; best-effort parse round `findings.md` for prose context.
   - **Standalone review**: read `review-findings.ndjson` beside `review-findings-classification-round-N.tsv` when present.
   - Optionally read `findings-ledger.tsv` when present; do not require it.
   - Join only on unambiguous run/round/finding keys; otherwise treat prose as missing.
   - **Bind `panel_verdict`** from joined prose per panel-kind priority above. When prose verdict disagrees with TSV `voting_result` or the row is MAV-placeholder degraded, mark weak/non-decisive and skip decisive bucketing.

6. Add conservative matching helpers:
   - Normalize titles with lowercase tokens and `STOP_WORDS`.
   - Extract file paths with a **diagnostic-local cleaned path extractor**:
     - Use `finditer` over `voting.FILE_LINE_REGEXES["any-re"]` and `voting.FILE_LINE_REGEXES["extensionless-re"]` (or equivalent multi-extension regex).
     - Strip surrounding markdown delimiters (`*`, `` ` ``, `_`, `#`, brackets), trailing punctuation, and line-range suffixes for identity comparison.
     - Lowercase, dedupe, and reject unsafe paths (reuse `file_oos` clean/path-safety patterns where practical).
     - Do **not** reuse `analyze_issues.FILE_RE` for ground-truth matching.
   - Match later issue/finding evidence only when either:
     - cleaned file path overlaps and at least two distinctive title/concern tokens overlap, or
     - title-token overlap is high enough for a short exact-ish match.
   - Apply temporal gate: cross-run later evidence requires `started_at` ordering when present; same-run later evidence requires greater `round_num` even when `started_at` is identical.

7. Add in-scope realized-outcome helpers (eligible rows with bound `panel_verdict` only):
   - Branch accepted vs rejected resurfacing/revert logic from the bound `panel_verdict` field only; never from TSV `voting_result`.
   - For rows with `panel_verdict == accepted`, detect later regression/revert issues or findings and bucket as `accepted_reverted_or_regressed` when decisive. Gate `accepted_reverted_or_regressed` on later issue/finding text matching `wasteful_findings`'s `reversal_re` (`python/analyze_issues.py:471-474`) or equivalent regression tokens from `CATEGORY_PATTERNS`; path/title overlap alone stays non-decisive.
   - For rows with `panel_verdict == rejected`, treat bug/fix/regression categories and strong later matches as `rejected_resurfaced`.
   - Build a conservative **later accepted-finding index** from later committed logs using the **same gates as source-row ingest**:
     - parse through `classification_row_panel_inputs`, not `voter_agreement_rows_from_tsv()`,
     - `_classification_row_is_oos(row, header)` must be false,
     - `voter_agreement_row_from_panel` eligibility must pass,
     - bound `panel_verdict == accepted` from authoritative prose only (design rows use round-local markdown-first binding),
     - exclude verdict-disagreement / weak / MAV-placeholder rows.
   - Index keyed by `run_id`, `round_num`, cleaned path signature, and normalized title tokens; use alongside `_merged_issue_index(issues, filed_issue_details)` so resurfacing visible only in later run logs can bucket decisively.
   - Use existing `default_category`, `_merged_issue_index`, and `parse_iso`.
   - Treat closed `NOT_PLANNED` matches as weaker unless they carry regression/revert wording.
   - When `enrichment_degraded` is set, suppress or qualify in-scope issue-backed decisive buckets the same way the fate section does; do not render zero decisive in-scope rows as perfect calibration without a degradation note.
   - Compute per-voter aligned/misaligned from decisive bucket direction and each voter's YES/NO vote per Ground-truth semantics above.

8. Add accepted OOS per-voter ground-truth join:
   - Reuse `iter_filed_oos_records`, `_OOS_HEADING_RE`, `_resolve_blocks_for_stable_id`, stable-id helpers, and `_record_issue_numbers` / issue-number resolution from the `fate_adjusted_oos_scoring` path.
   - For each OOS classification row (via `(row, header)` predicate), bind `oos_panel_verdict` before fate work; skip decisive OOS scoring unless `oos_panel_verdict == accepted`.
   - Resolve the filed issue through run id plus normalized title/stable id / `OOS_<n>` identity, using step-3 reviewer attribution where needed.
   - Fetch issue state from `_merged_issue_index(issues, filed_issue_details)`; honor `enrichment_degraded` the same way as `fate_adjusted_oos_scoring`.
   - Apply `classify_oos_issue_fate` only for accepted OOS rows; map only docked buckets to decisive contradicting outcomes.
   - Rejected, neutral, exonerated, or ambiguous OOS panel results and ambiguous stable-id rows stay non-decisive.

9. Handle gc-slimmed runs:
   - When `run_dir/gc-slimmed` exists or round `findings-classification.tsv` is absent, increment a gc-slimmed corpus bullet and count affected rows as weak/unknown.
   - Do **not** treat JSONL/NDJSON prose alone as substitute voter ballots.

10. Add renderer:
    - Heading: `## Ground-truth Voter Calibration`
    - When `enrichment_degraded` is set, print a note mirroring the fate section: GitHub issue enrichment unavailable; in-scope realized-outcome buckets may be suppressed or partial.
    - Corpus bullets: classification rows scanned, eligible rows with parseable voter ballots, ineligible rows (neutral/MAV placeholder/insufficient votes), rows with prose evidence, gc-slimmed runs / missing voter TSV rows, decisive realized rows, unknown/weak/provisional/timestamp-degraded/verdict-disagreement/rejected-OOS-panel/enrichment-degraded rows.
    - Outcome bucket table including `accepted_reverted_or_regressed` and OOS docked buckets.
    - Per-voter table: panel kind, voter, decisive, aligned, misaligned, missing, realized_alignment_rate, false_positive_yes, false_negative_no.
    - Examples capped by `top_k`; include run id, finding id, bucket, and short reason.
    - Notes: diagnostic only; no live scoring changes; ground-truth alignment is against realized outcomes, not panel self-agreement; conservative matching can undercount; provisional OOS fates and rejected OOS panel results are non-decisive; `realized_alignment_rate` uses decisive aligned/misaligned ballots only.

11. Wire `_build_analyze_report`:
    - Add a ground-truth helper with the same signature inputs as `fate_adjusted_oos_scoring`: `issues`, `log_root`, `filed_issue_details`, `repo`, `enrichment_degraded`, and `top_k`.
    - Append the new section after `## Fate-adjusted OOS Scoring`.
    - Catch exceptions like the existing fate section does.
    - Emit a warning to stderr if the diagnostic cannot render.

12. Add CLI flags only if needed: prefer default-on section with existing inputs; add `--no-ground-truth` only if tests or report noise justify it.

### UPDATED: python/test_findings_ledger.py

Add coverage for read-only ledger helpers: valid TSV reads into dict rows; malformed header returns empty evidence; empty or missing file returns empty evidence; no write side effects occur.

### UPDATED: python/test_voting.py

Add coverage for `classification_row_panel_inputs`: returns raw row dict and parsed header alongside `voter_votes`; design vs `code-review` `panel_kind` attribution matches existing `voter_agreement_rows_from_tsv` label behavior; `scope=oos` on `FINDING_*` rows route correctly when header includes `scope`; helper output is suitable for `voter_agreement_row_from_panel` eligibility without using `voter_agreement_rows_from_tsv().rows`.

### UPDATED: python/test_analyze_issues.py

Add offline regression tests for the new diagnostic covering: rejected resurfacing with non-.sh/.md path; non-decisive non-match; accepted revert decisive bucket; docked OOS decisive; provisional OOS non-decisive; scope=oos on FINDING_N routes OOS; primary/secondary implement alias join; ineligible MAV row exclusion; shared prep attribution; panel vs ground-truth divergence; verdict binding; design round-local markdown-first; round-local vs run-root disagreement weak; realized-outcome branching from panel_verdict; OOS panel verdict binding; error counters; realized_alignment_rate; later accepted finding resurfacing; same-run round ordering; later-index gate parity; missing prose no crash; gc-slimmed handling; enrichment degradation note; report appends after Fate-adjusted OOS Scoring; per-voter counts match synthetic TSV; conservative non-match; cleaned path overlap.

### UPDATED: .claude/skills/analyze-issues/SKILL.md

Update to document: ground-truth voter calibration section; `classification_row_panel_inputs` ingest (not `voter_agreement_rows_from_tsv`); panel_kind-pinned discovery; OOS-row routing with parsed header; `oos_panel_verdict` binding from TSV/tally; decisive OOS fate for accepted OOS rows only; ineligible-row exclusion; authoritative `panel_verdict` binding; design round-local markdown-first with run-root fallback; realized-outcome branching from bound `panel_verdict`; conservative matching; manifest `started_at` cross-run temporal gating; same-run `round_num` ordering; realized-outcome alignment distinct from panel self-agreement; decisive-only `realized_alignment_rate`; enrichment-degraded qualification; diagnostic-only status.

### UPDATED: docs/skills.md

Update `/analyze-issues` entry to mention ground-truth voter calibration, `panel_kind`-pinned discovery, `classification_row_panel_inputs` ingest, OOS-row routing with parsed header, `oos_panel_verdict` binding, decisive OOS fate for accepted OOS rows, ineligible-row exclusion, authoritative `panel_verdict` binding, design round-local markdown-first verdict resolution, conservative realized-outcome matching, manifest `started_at` cross-run temporal gating, same-run `round_num` ordering, decisive-only `realized_alignment_rate`, enrichment-degraded qualification, diagnostic-only status.

### UPDATED: README.md

Update the `/analyze-issues` skill row only if the short description needs the new diagnostic; keep the table concise.

### UPDATED: docs/linting.md

Update `make test-analyze` coverage text to mention all new fixture categories.

## Edge cases

- Missing run logs: render a zero-evidence section, not an error.
- GC-slimmed runs: when `gc-slimmed` exists or classification TSV is absent, count voter rows as weak/unknown; never substitute JSONL prose for missing ballots.
- Ineligible rows: neutral verdicts, MAV placeholders, and rows with fewer than two parseable votes are weak/unknown only.
- Legacy classification TSVs: parse only `classification_tsv_schema_supported` schemas; mirror compact-row handling from `classification_row_panel_inputs`.
- OOS routing without header: never call `_classification_row_is_oos` without the post-selection parsed header; `scope=oos` on `FINDING_*` ids must not fall back to prefix-only routing.
- Verdict disagreement: TSV `voting_result` vs authoritative prose mismatch yields weak/non-decisive, not inverted alignment.
- Design round-local vs run-root disagreement: weak/non-decisive; round-local markdown membership is authoritative when consulted first and both exist but conflict.
- OOS JSONL `out_of_scope`: does not encode accepted vs rejected; bind `oos_panel_verdict` from TSV/tally only.
- Rejected OOS panel rows: non-decisive for fate scoring even when filed issue later docks.
- Same-run multi-round runs: `started_at` alone cannot order round-1 vs round-2; require `round_num`.
- Duplicate finding ids across rounds: key by run id, panel kind, round, and finding id.
- Ambiguous OOS stable ids: preserve existing ambiguity buckets; stay non-decisive.
- Low-confidence text matches: exclude from decisive counts.
- `JUDGE_ERROR`: count as missing, not misaligned.
- OOS provisional fates: weak/unknown only; never decisive.
- Enrichment degraded: qualify in-scope buckets may be partial; surface explicitly.
- Secret-like content in prose: reuse existing redaction where already present. Do not print long prose.

## Failure modes

- Matching can undercount true resurfacing — acceptable for a conservative diagnostic.
- Same-run undercount if `round_num` is missing from path/prose — prefer path-derived round; degrade to non-decisive rather than false cross-round matches.
- Matching can still false-positive on common titles — require cleaned file-path overlap or high distinctive-token overlap.
- Issue dumps may be stale — report the issue corpus date range and keep the diagnostic qualified.
- Live `run` may fail bulk issue fetch — existing degraded path should still render log-only/OOS evidence and note enrichment degradation for in-scope buckets.
- gc-slimmed corpora understate voter evidence — surface gc-slimmed counts explicitly rather than inferring ballots from prose.
- Reusing panel `agree` bits would falsely equate self-agreement with accuracy — ground-truth metrics must derive alignment only from decisive realized buckets.
- Branching from TSV placeholders would invert YES/NO alignment on MAV-degraded rounds — realized-outcome helpers must consume bound `panel_verdict` only.

## Testing strategy

Run:
- `make test-analyze`
- `make py-lint`
- `make py-test`
- `make lint`

## Non-goals

Do not:
- Change live scoring, reviewer points, token allocation, or add allocation recommendations.
- Add a new skill.
- Fetch extra GitHub data from `/voter-calibration`.
- Use `voter_agreement_rows_from_tsv()` for ground-truth row materialization or later-run index construction.
- Treat weak no-counterevidence accepted findings as proof of accuracy.
- Treat provisional OOS fates as decisive YES alignment.
- Score rejected OOS panel rows as decisive OOS fate contradicting outcomes.
- Infer OOS accepted/rejected from implement JSONL `outcome=out_of_scope`.
- Reuse `voter_agreement_row_from_panel` `agree`/`disagree` as ground-truth alignment.
- Bucket ineligible or verdict-disagreement rows as decisive resurfacing outcomes.
- Branch accepted/rejected resurfacing from TSV `voting_result` after `panel_verdict` is bound.
- Bind design `panel_verdict` from run-root markdown when round-local plan-review markdown exists and disagrees.
- Order same-run rounds by `started_at` alone.

## Acceptance

- `make test-analyze` passes with all new fixture cases.
- `make py-lint` and `make py-test` pass.
- `make lint` passes.
- `python3 python/cli.py analyze-issues run` produces a report that includes `## Ground-truth Voter Calibration` after `## Fate-adjusted OOS Scoring`.
- The new section renders corpus bullet counts, an outcome bucket table, and a per-voter table with `realized_alignment_rate`.
- Zero decisive rows renders as a zero-evidence section with a note, not an error or misleading calibration claim.
- Enrichment-degraded run renders a qualified note alongside any OOS or in-scope decisive buckets.

diff_lines: 1085

## Test plan
(no test plan section in plan-file)
