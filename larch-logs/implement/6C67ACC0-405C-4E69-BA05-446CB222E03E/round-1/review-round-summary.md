# Review Round 1

- Mode: `diff`
- 15 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Multi-round runs over-suppress post-run GitHub issue evidence
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_evidence_later_than_row` (python/analyze_issues.py:2030-2037) blocks all issue-backed matches for rows from any multi-round run when issue `createdAt` is after `started_at`, even when the issue was filed long after the run completed. A round-1 rejected finding with a matching bug issue filed later is scored `rejected_not_observed` instead of `rejected_resurfaced`, skewing voter false-negative counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Only apply intra-run round guard when issue timestamp could predate later rounds; allow post-run issues via manifest end/updated_at or per-round bounds
  - From codex-specialist-correctness-output.txt: Treat issue evidence as later when its timestamp is after the run timestamp unless there is evidence it was filed during the same run; keep same-run round ordering for run-log findings only.


### FINDING_2: Run-root / design JSONL prose join ignores missing or empty `round_num` in multi-round runs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-dyn-realized-matching-output.txt, dyn-dyn-voter-prep-output.txt
- **Severity**: important
- **Concern**: In multi-round implement/design runs, `_jsonl_record_matches_row` and run-root `review-findings-full.jsonl` binding (python/analyze_issues.py:1765-1791, 1826-1858) do not gate records with missing, empty, or zero `round_num`. Committed logs often omit `round_num` on run-root JSONL; `path_round` is 0 for run-root files so the path-round branch never fires. Round-2 `FINDING_N` prose/outcome can bind round-1 TSV rows (and vice versa), producing wrong `panel_verdict` and false decisive resurfacing/revert buckets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Require record.round_num == row.round_num for multi-round runs or ingest only round-local JSONL
  - From codex-specialist-correctness-output.txt: When the run has multiple rounds, require record.round_num == row.round_num for run-root JSONL records, or mark the prose join weak when the record has no round number.
  - From cursor-specialist-edge-cases-output.txt: Skip or weaken run-root JSONL matches when _run_has_multiple_rounds and record round is unprovable; prefer round-*/ JSONL or heading bridge.
  - From cursor-specialist-edge-cases-output.txt: Gate JSONL records by inferred round; exclude unproven run-root JSONL from disagreement checks in multi-round runs.
  - From dyn-dyn-realized-matching-output.txt: When row.round_num > 0, skip run-root JSONL records unless record.round_num == row.round_num, or ignore run-root JSONL entirely when any round-*/review-findings-full.jsonl exists for the run.
  - From dyn-dyn-voter-prep-output.txt: When _run_has_multiple_rounds(row.run_dir) is true and row.round_num is known, require an explicit round match (record.round_num == row.round_num, or JSONL loaded from the matching round-N artifact) before binding; treat missing round metadata as weak/non-decisive instead of accepting the first heading match.


### FINDING_4: Ground-truth OOS filed-record join diverges from fate-adjusted stable-id contract
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-dyn-realized-matching-output.txt, dyn-dyn-oos-verdicts-output.txt, dyn-dyn-voter-prep-output.txt
- **Severity**: important
- **Concern**: `_match_oos_filed_record` (python/analyze_issues.py:2140-2173) uses a simplified join (stable-id suffix, title-token overlap) instead of the fate-adjusted contract (`_resolve_blocks_for_stable_id`, ndjson stable-id lists, ambiguity → non-decisive). Overlapping OOS titles, `FINDING_N` vs `OOS_N` identity mismatch, and round filtering gaps (`rec_round == 0` still matches cross-round rows) can attach the wrong `oos-issues.ndjson` record. That yields false docked buckets, `missing_filed_oos_join` undercounts, and voter misalignment. Stable-id matches dropped when `_filed_record_reviewer_matches` rejects `reviewer=unknown` can fall through to token-match siblings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Reuse _resolve_blocks_for_stable_id / iter_filed_oos_records join keys; non-decisive on ambiguity
  - From cursor-specialist-edge-cases-output.txt: Require provable round match before OOS filed-record join; treat ambiguous matches as non-decisive.
  - From cursor-specialist-testing-output.txt: Reuse _resolve_blocks_for_stable_id / ambiguity non-decisive handling; add ground-truth fixture mirroring fate-adjusted ambiguous stable-id cases.
  - From dyn-dyn-realized-matching-output.txt: When row.round_num > 0, treat rec_round == 0 as non-match unless the record's artifact_relpath / identity explicitly contains that round; reuse fate-adjusted stable-id resolution where identity is ambiguous.
  - From dyn-dyn-oos-verdicts-output.txt: Resolve classification rows to filed records the same way _join_implement_run_records does: index accepted blocks, read stable IDs from ndjson / accepted markdown for the same run+round, call _resolve_blocks_for_stable_id, and treat ambiguity as non-decisive. Use title tokens only as a last resort.
  - From dyn-dyn-voter-prep-output.txt: Build the join from the same stable-id keys used when filing (oos-accepted-*:FINDING_N / heading identity + round + reviewer attribution). Reuse _resolve_blocks_for_stable_id or index iter_filed_oos_records by (run_id, round_num, finding_id, reviewer); drop token-only fallback, or mark token matches weak/non-decisive.


### FINDING_5: Missing regression tests for multi-round temporal gating and JSONL round isolation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required multi-round edge cases lack dedicated regression pins in python/test_analyze_issues.py. `_run_has_multiple_rounds` temporal gating, same-run round ordering, empty-`round_num` run-root JSONL cross-binding, and post-run issue resurfacing can ship with green `make test-analyze`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add fixtures for same-run round ordering post-run issue resurfacing and run-root JSONL round gating
  - From cursor-specialist-edge-cases-output.txt: Add two-round fixtures with empty round_num JSONL and same-run ordering assertions.
  - From cursor-specialist-testing-output.txt: Add multi-round implement fixtures with round-1/round-2 TSVs and timed issues; assert round-1 rows ignore issue-only ordering when multiple rounds exist and round-2 accepted findings can drive resurfacing.


### FINDING_9: OOS panel verdict fallback reads wrong tally artifact (`vote-tally.md` vs `voting-tally.md`)
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_ground_truth_oos_panel_verdict()` (python/analyze_issues.py:1965-1979) reads `vote-tally.md` and searches for a global `Result: accepted` string, but committed logs use round-local `voting-tally.md` tables with per-item `| FINDING_N | ... | accepted |` rows. TSV `voting_result=accepted` with `voting-tally.md` showing that OOS item rejected is still scored accepted, producing false decisive docked OOS outcomes. Regression tests (python/test_analyze_issues.py:759-775) use the non-runtime filename/shape, so real TSV/tally disagreement is never detected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Read `voting-tally.md`, parse the row for the current `finding_id`, and compare that per-item result with TSV before returning accepted or rejected.
  - From codex-specialist-edge-cases-output.txt: Read `voting-tally.md` and parse the table row keyed by `row.finding_id`; keep `vote-tally.md` only as a legacy fallback, and update tests to use the real artifact shape.
  - From codex-specialist-testing-output.txt: Read `voting-tally.md` with a compatibility fallback if needed, parse the table row for `row.finding_id`, compare that row's result with TSV `voting_result`, and update the tests to use the real artifact filename and table format.


### FINDING_10: Ground-truth OOS fate matching ignores `repo`
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Ground-truth OOS fate matching (python/analyze_issues.py:2189-2201) ignores `repo` even though `ground_truth_voter_calibration()` receives and deletes it at python/analyze_issues.py:2390-2391. A filed OOS URL for another repo's `issues/12` can match the current repo's issue `#12`, producing a false docked bucket and wrong per-voter misalignment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Thread `repo` into the OOS outcome path and mirror `fate_adjusted_oos_scoring()` by skipping or marking non-decisive records whose `issue_url` repo does not match.


### FINDING_11: Design round-local verdict fallback uses parsed headings instead of file existence
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The round-local design verdict fallback (python/analyze_issues.py:1887-1922) sets `local_files_exist` from parsed heading blocks, not actual file existence. If round-local accepted/rejected files exist but are empty or unparsable, the code treats them as absent and falls back to stale run-root markdown for the same `FINDING_N`, binding the wrong `panel_verdict` and creating false decisive outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Check `Path.is_file()` for the round-local pair; when either local file exists but the row has no unambiguous local membership, mark the row weak instead of falling back to run-root files.


### FINDING_12: Missing regression test for later accepted-finding resurfacing via `accepted_index`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_ground_truth_accepted_finding_evidence` and `accepted_index` (python/analyze_issues.py:2067-2130) are new and untested for log-only resurfacing. A rejected row with no issue match but a later run accepted finding with overlapping path/title could break without a targeted CI failure; mega-test only pins issue-backed `rejected_resurfaced`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Fixture: rejected row with no issue match but a later run accepted finding with overlapping path/title; assert rejected_resurfaced and voter false_negative_no.


### FINDING_13: Missing regression test for rejected-OOS-panel non-decisive boundary
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Plan requires rejected OOS panel rows stay non-decisive even when a filed issue would dock. `_ground_truth_oos_outcome` (python/analyze_issues.py:2184-2187) has zero test references; regression could score docked OOS fate and inflate `realized_alignment_rate`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Fixture with OOS TSV voting_result=rejected plus dockable filed issue; assert rejected_oos_panel bucket and decisive_rows==0.


### FINDING_14: Top-50 evidence cap drops later accepted-finding candidates
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_candidate_evidence_for_row` (python/analyze_issues.py:2115-2132) fills `candidates` with up to 50 issue records first, then appends accepted-finding evidence, then truncates back to 50. A rejected source row with 50 weak issue candidates and one later accepted finding never sees the accepted finding, reporting `rejected_not_observed` instead of decisive `rejected_resurfaced`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Keep separate caps or prioritize accepted-finding candidates for rejected rows before the final cap, and add a regression where issue candidates fill the cap but a later accepted finding must still score decisively.


### FINDING_15: Standalone review prose binding lacks round isolation
- **Reviewer(s)**: dyn-dyn-realized-matching-output.txt
- **Severity**: important
- **Concern**: `_standalone_review_prose_for_row` (python/analyze_issues.py:1765-1770, 1862-1868) passes `path_round=0` (review run dir has no `round-N` segment) and NDJSON/JSONL records without `round_num` match any `review-findings-classification-round-N.tsv` row with the same `FINDING_N`. That can bind the wrong `outcome` and drive incorrect decisive resurfacing/revert scoring across review rounds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-realized-matching-output.txt: Require record.round_num == row.round_num when the classification filename carries a round, or index NDJSON by parsed ### FINDING_N: round-local identity instead of bare id containment.


### FINDING_16: `_ground_truth_oos_panel_verdict` called before `row.prose_text` is set
- **Reviewer(s)**: dyn-dyn-realized-matching-output.txt
- **Severity**: important
- **Concern**: `_ground_truth_oos_panel_verdict` is invoked before `row.prose_text` is assigned (python/analyze_issues.py:1940-1946, 1978-1979), so its `prose_tally_match = _GT_VOTE_TALLY_RESULT_RE.search(row.prose_text)` fallback always sees an empty string. OOS rows with neutral/missing TSV `voting_result` and no `vote-tally.md` cannot bind `oos_panel_verdict` from prose even when `Result:` is present in joined prose, pushing scorable accepted-OOS rows into `weak_oos_panel_verdict` (undercount).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-realized-matching-output.txt: Pass joined prose into _ground_truth_oos_panel_verdict (or set row.prose_text before calling it) so the tally regex can consult prose when round-local vote-tally.md is absent.


### FINDING_17: Issue-backed candidate selection hard-capped at 50 after overlap ranking
- **Reviewer(s)**: dyn-dyn-realized-matching-output.txt
- **Severity**: important
- **Concern**: Issue-backed candidate selection (python/analyze_issues.py:2095-2115, 2237-2243) still hard-caps at 50 rows after token overlap ranking. A resurfacing/revert issue ranked 51+ by overlap is never considered, so rows can land in `rejected_not_observed` or `accepted_no_counterevidence` instead of a decisive bucket, skewing `false_negative_no` / `realized_alignment_rate`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-realized-matching-output.txt: Index issues by cleaned path signature and distinctive tokens (as done for accepted-finding evidence) and only cap per-query result sets, or raise/remove the global 50 limit once overlap-ranked.


### FINDING_20: Stable-id OOS matches dropped when filed-record reviewer is `unknown`
- **Reviewer(s)**: dyn-dyn-oos-verdicts-output.txt
- **Severity**: important
- **Concern**: Stable-id matches require `_filed_record_reviewer_matches` (python/analyze_issues.py:1817-1823, 2155-2165), which returns `False` when the filed record reviewer is `unknown`. `iter_filed_oos_records` emits `reviewer: unknown` for recovered rows (python/analyze_issues.py:1305-1308). A matching `stable_id` is then dropped with no token fallback, so accepted OOS rows with clear TSV/tally verdicts can land in `missing_filed_oos_join` even when `issue_number` / `issue_url` are present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-oos-verdicts-output.txt: When stable-id identity matches unambiguously, do not require reviewer agreement; or fall through to issue-number join when reviewer is unknown / Main agent recovered rows.


### FINDING_21: Large corpus row cap disables accepted-OOS filed-record scoring silently
- **Reviewer(s)**: dyn-dyn-oos-verdicts-output.txt
- **Severity**: important
- **Concern**: When the corpus exceeds 5000 classification rows, `filed_records` is forced to `[]` (python/analyze_issues.py:2468-2479), so accepted OOS fate scoring is disabled entirely while the report still renders per-voter tables and corpus bullets. Large repos can show structurally complete ground-truth output with zero accepted-OOS docked evidence and no prominent qualification beyond `large_corpus_skip`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-oos-verdicts-output.txt: Keep iter_filed_oos_records(log_root) independent of row-count cap (the cap can still limit accepted-finding index / issue-evidence scanning), or emit a prominent qualification that OOS docked buckets were not evaluated.


