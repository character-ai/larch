## Goal
Implement issue #5078: [IMPLEMENTING] [BUG] Review pipeline drops format-divergent reviewer TSV and voter output.

## Implementation Plan
## Summary

Two related defects surfaced during a single `/design` run (issue #4984, design-log PR #5074). In both, a review-pipeline agent produced **content-valid but format-divergent** output, and a strict parser rejected the whole contribution with no salvage path:

1. A Cursor plan-review reviewer's structured TSV rows had **7 tab columns instead of 8**, so every data row was dropped and the entire slot was discarded as `NOT_SUBSTANTIVE`.
2. The Claude voter emitted votes as a **markdown table** instead of anchored `FINDING_N: YES …` lines, so all 8 ballot items parsed as `JUDGE_ERROR`, the voter was removed from quorum, and the round-2 panel went `panel-failed` (2/3 effective judges).

Both are the **same robustness class** as #4994 (closed), #5022 (closed), and #5077 (open): a vendor/LLM agent emits a plausible-but-non-exact token that a strict validator rejects, dropping recoverable output with no retry/salvage. This issue is **distinct** from those: #4994 fixed *value/enum* TSV defects (the column-count path here is uncovered), #5022/#5077 are in the **aggregator** (`review_aggregate.py`), and this issue is in the **collector** (`research_eval.py`) and the **voter** (`voting.py`). See "Root cause analysis" for the version check confirming Problem 1 is not a #4994 version-skew recurrence.

## Original report

From a completed `/design` run on issue #4984 (run ID `86E48928-1889-457B-92BC-8F3A50E145DC`), the final summary reported `Exec issues: 1` and `Warnings: 1`. Investigation of the published `execution-issues.md` (in design-log PR #5074) found two distinct problems:

- **Exec issue:** the round-1 reviewer slot `cursor-plan-innovation` was dropped as `NOT_SUBSTANTIVE`. The Cursor agent itself ran fine (exit 0, ~3621 bytes of output containing genuinely useful findings), but its structured TSV rows had 7 tab columns instead of the required 8, so the collector rejected every row (`REJECT structured TSV row: expected 8 tab columns, got 7`, repeated) and emitted `structured records not found after repair`.
- **Warning:** the Claude voter's parse-rate check reported `judge_error_count=8` of `total_ballot_items=8`. The captured voter output began with a markdown table (`| Item | Vote | Key reason |` … `| FINDING_1 | **YES** | …`) rather than the required anchored `FINDING_N: YES …` grammar. This removed the voter from the effective quorum and produced the round-2 `panel-failed` / "2 of 3 effective judges" status.

Request: file one bug with root cause, run data, and suggested fixes for both, cross-referencing #5077/#4994/#5022 and confirming whether the #4994 fix was present in the running version.

## Reproduction scenario

Not deterministically reproducible on demand, because both depend on a specific LLM/vendor producing off-spec output. Synthetic reproduction of each validator is straightforward:

- **Problem 1:** feed `research_eval.validate_structured_reviewer_output` (or `agent collect-results --structured-reviewer-validation`) a structured block whose header is the canonical 8-column header but whose data rows contain only 7 tab-separated fields (for example, a space where a tab delimiter belongs). Expected current behavior: every row rejected with `expected 8 tab columns, got 7`, `structured records not found after repair`, rc 5, slot dropped. Note: this is the column-count path, NOT the schema/focus value path that #4994 already canonicalizes.
- **Problem 2:** run `voting check_voter_parse_rate` over a voter file whose votes are a markdown table (`| FINDING_1 | YES | … |`) instead of `FINDING_1: YES …`. Expected current behavior: `judge_error_count == len(ids)`, threshold (0.8) tripped, voter removed from quorum.

## Expected behavior

- A reviewer that produces complete, useful findings should not have its entire contribution discarded over a single missing/space-substituted tab delimiter. The validator should salvage off-by-one-delimiter rows, or at least retry/repair before dropping the whole slot. (#4994 established this principle for value/enum defects via canonicalization; the same tolerance should extend to the column-count path.)
- A voter that casts clear YES/NO decisions in a recognizable (if non-canonical) layout, such as a markdown table, should be parsed and counted, or reliably re-prompted into the canonical grammar, rather than silently removed from quorum.

## Observed behavior

- **Problem 1:** all data rows in the Cursor reviewer output were rejected because each had 7 tab columns; with only the header surviving (`len(out) <= 1`), the validator returned empty and the slot was marked `NOT_SUBSTANTIVE`. The reviewer's findings (which overlapped with high-value points other reviewers raised and that were ultimately applied) never reached the ballot.
- **Problem 2:** all 8 ballot items from the Claude voter parsed as `JUDGE_ERROR`; `8/8 = 1.0 >= 0.8` tripped the threshold; the voter was removed from the effective quorum, degrading the panel to 2 of 3 effective judges and yielding `panel-failed` for round 2.

## Root cause analysis

**Problem 1 — strict 8-column TSV reject with no salvage (distinct from #4994).**
- `python/research_eval.py` `_split_structured_tsv_row` does `line.split("\t", 7)` and returns `None` (rejecting the row) when `len(fields) < 8` (the `expected 8 tab columns, got N` reject).
- `_validate_structured_tsv` drops every rejected row; `if len(out) <= 1: return ""` — `out` is seeded with the header only, so if no data row survives it returns empty.
- `validate_structured_reviewer_output` then emits `structured records not found after repair` and returns `5`, which the collector maps to `NOT_SUBSTANTIVE`.
- **The #4994 fix was present in the running version.** The plugin cache that actually ran (`larch-local/larch/51.3.8/python/research_eval.py`) is byte-identical to main (HEAD `0c61c9498`) and contains the #4994 fix: `_canonical_schema_version` (any digit → `1`) and `_canonical_focus` (`completeness → code-quality`), from PR #5013 / commit `0934a1bf6`. So Problem 1 is NOT a version-skew recurrence of #4994. The #4994 fix canonicalizes field *values*; it does not relax the 8-column *count* check, so a row that is off by one tab delimiter still fails. The captured reject was purely `got 7` (column count), never a schema/focus value reject. This is a genuinely uncovered sub-case in the same family.

**Problem 2 — voter markdown-table votes counted as JUDGE_ERROR.**
- `python/voting.py` `check_voter_parse_rate` parses each ballot id's vote; unparsed items become `JUDGE_ERROR`. Threshold `_DEFAULT_JUDGE_ERROR_PARSE_THRESHOLD = 0.8`; `judge_error_count / len(ids) >= threshold` flags the voter and warns that it "likely produced prose without FINDING_N:/OOS_N: VOTE lines."
- The Claude voter produced a markdown table of votes, which the anchored-line parser does not recognize, so all 8 items were `JUDGE_ERROR`. A `_parse_rate_retry` path exists (`python/plan_review_panel.py`) but the final state was still 8/8 `JUDGE_ERROR`, so either the retry did not fire or the voter repeated the table format. (Inference that the model repeated the format; observation that the final `judge_error_count=8`.)

Common root across this issue and its siblings (#4994/#5022/#5077): review-pipeline validators enforce one exact textual shape and discard the entire unit (reviewer slot / aggregator merge / voter) when the shape is off, with no normalization for a recognizable alternative layout.

## Evidence

- Run: `/design` issue #4984, run ID `86E48928-1889-457B-92BC-8F3A50E145DC`; final summary `Exec issues: 1`, `Warnings: 1`; design-log PR #5074. Repo HEAD at investigation: `0c61c9498`.
- Problem 1 capture (`execution-issues.md`, External Reviewer Issues): `Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)`; structured record `TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair REJECT structured TSV row: expected 8 tab columns, got 7 …`; launcher log `cursor agent: completed (exit code 0, output 3621 bytes)`.
- Problem 2 capture (`execution-issues.md`, Warnings): `Step plan-review voter-dispatch claude — agent launch-claude-review (voter parse-rate check) warning (exit 0)`; `slot=1 voter_tool=claude judge_error_count=8 total_findings=8 total_ballot_items=8`; voter output first bytes show a `| Item | Vote | Key reason |` markdown table.
- Version check: `diff` of `larch-local/larch/51.3.8/python/research_eval.py` against the working tree (main) returned IDENTICAL; `git log` shows `0934a1bf6 Fixes #4994: Implement issue #4994 (#5013)` already in HEAD. Confirms the #4994 fix shipped in the running version.
- Code: `python/research_eval.py` (`_split_structured_tsv_row`, `_validate_structured_tsv`, `validate_structured_reviewer_output`); `python/voting.py` (`check_voter_parse_rate`, `_DEFAULT_JUDGE_ERROR_PARSE_THRESHOLD`); `python/plan_review_panel.py` (`_parse_rate_retry`); `python/review_tally.py` (`_parse_rate_ok`).
- Related issues: #4994 (closed — Cursor reviewer dropped on value/enum TSV defects; fixed via value canonicalization), #5022 (closed — aggregator reviewer-slot mismatch not retried), #4996 (closed — aggregator forensics overwritten), #5077 (open — aggregator missing-reviewer validation not covered by retry loop). This issue is the collector column-count and voter parse-rate facets of the same class.

## Affected files

- `python/research_eval.py` — `_split_structured_tsv_row`, `_validate_structured_tsv`, `validate_structured_reviewer_output`: the strict 8-column reject and whole-slot drop (Problem 1). The #4994 value-canonicalization helpers live here too but do not cover the column-count path.
- `python/voting.py` — `check_voter_parse_rate` and `_DEFAULT_JUDGE_ERROR_PARSE_THRESHOLD`: the JUDGE_ERROR counting and 0.8 quorum-removal threshold (Problem 2).
- `python/plan_review_panel.py` — `_parse_rate_retry`: the existing re-prompt path that did not recover the table-format voter (Problem 2).
- Reviewer/voter prompt renderers (`python/cli.py render plan-review`, `render voter`; `python/rendering.py`): where the required output grammar is instructed (both problems, prompt-side hardening). #4994 already hardened the plan-review reviewer prompt for schema/focus values; the tab-delimiter and voter-grammar instructions are the relevant surfaces here.
- `python/review_tally.py` — `_parse_rate_ok`: the code-review-side parse-rate gate that shares the same risk (Problem 2 generalization).

## Suggested fix(es)

**Problem 1 (structured TSV reject):**
- Add a salvage path in `_split_structured_tsv_row` / `_validate_structured_tsv`: when a row has 7 fields but the leading typed fields (`schema_version`, `scope`, `severity`, `focus_area`, `location`) are individually valid, treat the trailing remainder as merged `what` / `scenario_or_breakage` / `suggested_fix` (or pad a missing trailing field) instead of dropping the row. Optionally normalize runs of 2+ spaces to a tab before splitting when the row otherwise fails the 8-column count. This extends #4994's tolerance principle from value defects to the column-count defect.
- When data rows exist but all are rejected (`len(out) <= 1` after seeing real rows), emit a more actionable diagnostic and consider a repair/relaunch retry (mirroring the voter `parse-rate-retry` and the #5077 aggregator retry direction) before declaring `NOT_SUBSTANTIVE`.
- Harden the reviewer prompt: state "exactly 8 tab-separated columns; use a literal TAB between columns, never spaces" and include one example row.

**Problem 2 (voter table-format votes):**
- Extend the vote parser used by `check_voter_parse_rate` to recognize a markdown-table vote layout (`| FINDING_1 | YES | … |` / `| OOS_1 | NO | … |`) and normalize it to the anchored `FINDING_N: <VOTE>` form before counting `JUDGE_ERROR`.
- Strengthen the `parse-rate-retry` prompt to show the voter its own rejected output and restate the required anchored grammar explicitly forbidding tables.
- Harden the voter prompt (`render voter`) to forbid markdown tables and require one anchored line per ballot item.

Cross-cutting (shared with #5077): prefer "normalize or retry, then drop" over "drop on first format mismatch" across reviewer-collector, aggregator, and voter validation, so format-divergent-but-content-valid agent output is not silently lost.

## Open questions

- For Problem 1, what exactly caused the 7-column rows (space-for-tab substitution vs. an omitted column)? The raw Cursor output was not preserved post-cleanup; capturing a rejected-row sample in `execution-issues.md` would disambiguate.
- For Problem 2, did `_parse_rate_retry` fire and fail, or not fire? Logging the retry attempt count and the post-retry parse rate would confirm.
- Should the collector column-count salvage and the #5077 aggregator retry land as one shared "review-pipeline validation robustness" change, or stay independent given the different files?
- Should the 0.8 quorum-removal threshold stay once a table-tolerant parser lands, or be revisited?

## Test plan
(no test plan section in plan-file)
