# Review Round 1

- Mode: `diff`
- 5 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Plan-review live tally omits dead voter slots vs TSV re-ingestion
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-calibration-parity-output.txt, dyn-legacy-tsv-schemas-output.txt
- **Severity**: important
- **Concern**: Live plan-review `compute_voter_agreement` skips unconfigured/dead voter slots (`if not voter_file: continue`), but `_write_findings_classification` and `voter_agreement_rows_from_tsv` always materialize three positional voters with fallback labels and empty votes. On degraded 2-judge panels, live `voting-tally.md` omits phantom voters (e.g. Cursor) while committed TSV re-ingestion and `/voter-calibration` count them with missing votes, so scoreboard rows and missing counts diverge for the same run even when active-judge agree/disagree rates match.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Always emit three (label vote) pairs in plan_review_tally using the same fallback labels and empty votes as voter_agreement_rows_from_tsv.
  - From cursor-specialist-edge-cases-output.txt: Build voter_votes for positions 1–3 using the same label fallbacks as _voter_label, with empty votes for unassigned slots, instead of continuing past dead slot_file entries.
  - From cursor-specialist-testing-output.txt: Build live voter_votes with the same three-slot label/vote mapping used for classification TSV rows; add a degraded 2-judge parity test comparing live and TSV-derived compute_voter_agreement output.
  - From dyn-calibration-parity-output.txt: Build `voter_votes` with the same fixed 1..3 slot loop used for classification TSV (label from `slot_tool` or the same fallback map, vote from `vote_for_id` when `slot_file[pos]` is set, else `""`), then pass that list to `voter_agreement_row_from_panel`.
  - From dyn-legacy-tsv-schemas-output.txt: Make plan-review live agreement use the same fixed three-slot `(label, vote)` shape as `review_tally.py:620-624` (always emit positions 1–3, dead slots as empty votes with `slot_tool` or canonical fallback labels), and add a degraded-panel parity test that asserts `compute_voter_agreement(agreement_rows)` equals `compute_voter_agreement(voter_agreement_rows_from_tsv(tsv))` for the emitted classification file.


### FINDING_2: Zero-voter plan-review omits Voter Agreement Scoreboard section
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The plan-review zero-voter early exit (`eligible == 0`) writes `voting-tally.md` without a Voter Agreement Scoreboard section, while the analogous code-review path renders an explicit undefined row via `render_voter_scoreboard([])`. Operators get inconsistent diagnostics across panel kinds for zero-effective-voter runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Append voting.render_voter_scoreboard([]) on the plan-review zero-voter path.
  - From cursor-specialist-edge-cases-output.txt: Append voting.render_voter_scoreboard([]) in the eligible == 0 branch before return, matching review_tally.py.


### FINDING_3: `_normalize_vote_cell` ignores EXONERATE votes in committed TSV ingestion
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_normalize_vote_cell` ignores `EXONERATE` while live tally maps it to `NO`. Historic committed design/implement classification TSVs contain `EXONERATE` in `vN_vote` cells. `/voter-calibration` under-counts disagreement and over-counts missing on accepted findings, inflating agreement rates and suppressing outlier flags.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Map EXONERATE to NO in _normalize_vote_cell (mirror vote_for_id / parse_judge_vote) and add a regression test using a committed-shape fixture row.


### FINDING_4: Voter-calibration under-counts skipped/unsupported TSV files
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-legacy-tsv-schemas-output.txt
- **Severity**: latent
- **Concern**: `skipped_files` increments only when the header line lacks `voting_result`. Files with a `voting_result` header but wrong/unsupported panel schema (e.g. `reviewer_slots` instead of `finding_reviewers` on a design path) return zero parsed rows without incrementing `skipped_files`, so corpus diagnostics report `Malformed or unsupported TSV files skipped: 0` while data is silently dropped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Treat zero parsed rows plus unrecognized schema as skipped not only missing voting_result.
  - From codex-specialist-correctness-output.txt: Return an explicit parser status or validate required header tokens in the analyzer before parsing, and increment skipped_files for unsupported schemas only.
  - From codex-specialist-edge-cases-output.txt: Return schema status from `voter_agreement_rows_from_tsv`, or add explicit required-header validation in the analyzer so unsupported files increment `skipped_files` while valid header-only, neutral-only, and single-voter files remain counted as scanned but unqualified.
  - From dyn-legacy-tsv-schemas-output.txt: After parsing, treat a file as skipped when `parsed` is empty and the header set fails the panel-specific marker check (`finding_reviewers` for design paths, `reviewer_slots` for code-review paths), independent of the `voting_result` substring heuristic; keep neutral-only or single-voter files out of that bucket.


### FINDING_7: Compact review tally omits unused third voter slot
- **Reviewer(s)**: dyn-calibration-parity-output.txt
- **Severity**: important
- **Concern**: Legacy compact tally (`three_slot=False`) builds `voter_votes` only from `enumerate(cells, start=1)`, so a 2-effective-voter run produces two `(vN, vote)` pairs while `_classification_row` still writes three `vN_vote` columns and TSV ingestion always supplies three positional voters. Committed compact TSVs report extra `missing` for unused slots (e.g. `v3`) that the live scoreboard omits, breaking live-vs-committed parity on the compact fallback path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-calibration-parity-output.txt: For compact mode, always emit three `(f"v{pos}", vote_or_empty)` pairs aligned with the three TSV columns (empty vote when `idx >= len(cells)` or the slot had no rating), matching the three-slot pattern already used at `review_tally.py:620-624`.


