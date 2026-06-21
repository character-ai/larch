# Review Round 5

- Mode: `diff`
- 15 accepted, 4 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Legacy `Combined into #N` regex matches issue body and false-docks combined-away
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `has_combined_away_marker` applies `_LEGACY_COMBINED_RE` to the issue body as well as comments. A closed filed OOS issue whose body quotes `Combined into #N` in discussion (but whose close comments lack that signal) is fate-docked to combined-away with adjusted 0. New `/combine-issues` closures write only the HTML `larch:combined-away` marker; the legacy regex should not treat incidental body prose as closure evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Apply `_LEGACY_COMBINED_RE` only to `issue_comments()`; keep HTML marker check on body and comments.
  - From cursor-specialist-edge-cases-output.txt: Apply `_LEGACY_COMBINED_RE` only to `issue_comments()`; keep HTML combined-away marker checks on body plus comments if desired.


### FINDING_8: No test for HTML `larch:combined-away` marker in `classify_oos_issue_fate`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tests exercise only legacy `Combined into #N` text. New `/combine-issues` closures write only the HTML marker; a regex bug would leave them undocked while CI passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a `classify_oos_issue_fate` test with comments containing `<!-- larch:combined-away source=#1 target=#99 -->` and assert docked combined-away / adjusted 0.


### FINDING_9: Missing end-to-end test for targeted `gh issue view` failure with degraded comment fetch
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No scoring-output assertion covers bulk CLOSED issue plus `__fetch_failed__` sidecar. Regression could yield wrong bucket or silent mis-scoring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Fixture with bulk CLOSED only, failed `filed_issue_details`, assert `degraded comment fetch` plus provisional unknown and adjusted still +1.


### FINDING_10: No positive cap-rollup fallback test for exact candidate-count match
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Fallback selection logic in `_expand_cap_rollup_records` has no positive test. Only ambiguous-path tests would catch regressions when exactly N unfiled same-source blocks match the rollup count.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add fixture with two unfiled same-source blocks and one aggregate stable id; assert two scored rows from join/scoring.


### FINDING_11: Missing non-rollup single-URL anti-fan-out test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: A join bug could score every unattached same-run block for one filed URL and inflate reviewer totals. No test asserts exactly one scored row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Fixture with one ndjson URL and three unjoined blocks; assert exactly one scored row.


### FINDING_14: Legacy filed rows can drop the first cited OOS/FINDING id
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `_extract_legacy_stable_ids_from_ndjson_body` slices from the first `Filed` token, so a row like `FINDING_1 ... Filed as https://github.com/o/r/issues/10` loses `FINDING_1`. Later rows may be attributed instead. This undercounts fate-adjusted OOS points and misassigns reviewer attribution for legacy records.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Extract ids from the full filed line, table row, or bullet containing each filed marker, not only from the substring starting at `Filed`.


### FINDING_16: Cap-rollup fallback expansion runs after ambiguous stable-id resolution
- **Reviewer(s)**: dyn-oos-reconciler-output.txt
- **Severity**: important
- **Concern**: `_expand_cap_rollup_records` sets `ambiguous = True` and emits `ambiguous stable id` rows, but the count-based fallback at lines 1128–1159 still runs whenever `expected > 0` and `len(scored_rows) < expected`, without checking `ambiguous`. It can pick any N unfiled same-source blocks solely because `len(candidates) == expected`, even when cited stable ids were `OOS_1` and `OOS_2` and blocks share headings across rounds. That violates the plan rule to avoid arbitrary picks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-reconciler-output.txt: After any ambiguous stable-id match in the explicit resolution loop, skip count-based fallback and return `_rollup_expansion_shortfall_result(...)` or a pure `ambiguous rollup expansion` row; only run fallback when no stable id in the record was marked ambiguous.


### FINDING_17: `_is_cap_rollup_record` treats any multi–Stable-ID row as cap rollup
- **Reviewer(s)**: dyn-oos-reconciler-output.txt
- **Severity**: important
- **Concern**: `_is_cap_rollup_record` routes any ndjson row with two or more cited `Stable ID` lines through `_expand_cap_rollup_records`, even without an `Aggregated rollup of N capped OOS items` title. Production combined filings commonly use multiple `Stable ID` lines under one `Filed URL`. Behavior diverges from the normal join path on partial ambiguity: cap path emits per-stable-id `ambiguous stable id` buckets while normal path only emits that bucket when `ambiguous and not matched_any`. Combined filings can get different fate-adjusted totals depending on stable-id collision shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-reconciler-output.txt: Limit the secondary heuristic to real rollups (rollup title regex, `Aggregated rollup` prose, or aggregate stable ids), and route multi-stable-id single-URL filings through the normal per-stable-id join path described in the plan.


### FINDING_18: Design `OOS_FILE_MAP` indexing uses last-write-wins for duplicate headings
- **Reviewer(s)**: dyn-oos-reconciler-output.txt
- **Severity**: important
- **Concern**: Design `OOS_FILE_MAP` indexing uses `by_heading = {heading_id: block}` with last-write-wins semantics. Duplicate `### OOS_N:` headings in `oos-accepted-design.md` silently drop earlier blocks, losing reviewers/URLs. The implement path avoids this via `(artifact_relpath, heading_id)` keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-reconciler-output.txt: Index design blocks by `(artifact_relpath, heading_id)` (or a list per heading) and disambiguate map joins the same way implement runs do; emit `ambiguous stable id` when multiple blocks share a heading.


### FINDING_21: Upstream fetch failure classifies filed OOS as `skipped missing issue` without integration degradation signal
- **Reviewer(s)**: dyn-gh-fate-fetch-output.txt
- **Severity**: important
- **Concern**: When repo detection fails or bulk fetch is skipped, `issues` stays empty, targeted `gh issue view` is not run, and filed OOS rows land in `skipped missing issue` because `index.get(parsed_number)` is `None`. stderr warns, but the fate section does not record integration degradation as the plan requires. Operators can read log evidence loss as missing issues rather than failed GitHub enrichment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-fate-fetch-output.txt: Thread an explicit degradation flag (`repo_unavailable`, `bulk_fetch_failed`) into `fate_adjusted_oos_scoring`, add a fate-section note and/or bucket for unavailable enrichment, and avoid classifying known filed numbers as `skipped missing issue` when the failure is upstream fetch integration.


### FINDING_22: Uncaught `load_issues` `SystemExit` aborts entire run after successful fetch
- **Reviewer(s)**: dyn-gh-fate-fetch-output.txt
- **Severity**: important
- **Concern**: After a successful `fetch_main`, `load_issues` is uncaught. A corrupt or non-list dump raises `SystemExit` and aborts the entire run, including legacy sections and fate-adjusted scoring. That breaks the stated degrade-without-abort goal for fetch failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-fate-fetch-output.txt: Wrap `load_issues` in `try/except SystemExit` (or return a result object), emit a stderr warning, continue with `issues=[]`, and still render the rest of `_build_analyze_report`.


### FINDING_26: `plan-review.md` has contradictory/stale OOS scoring contract in multiple places
- **Reviewer(s)**: dyn-scoring-contract-docs-output.txt
- **Severity**: important
- **Concern**: The **Competition notice** blockquote (lines 30–32) still tells reviewers that accepted OOS items earn a permanent **+1 point**, while the adjacent rubric says panel acceptance earns a **provisional +1 at vote time** and `/analyze-issues` may retroactively dock filed OOS to 0. The **Competition scoring** bullet (line 177) still says **"OOS stays flat at +1/0/-1"** with no provisional qualifier or fate-adjusted note. Reviewers and operators see contradictory scoring contracts in one injected prompt surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scoring-contract-docs-output.txt: Align the first blockquote sentence with `docs/point-competition.md` and `skills/shared/voting-protocol.md`: accepted OOS is **provisional +1 at vote time**, fate-adjusted docking is **diagnostic-only**, and live tallies are unchanged.
  - From dyn-scoring-contract-docs-output.txt: Mirror the `### OOS Scoring` language from `skills/shared/voting-protocol.md`: provisional +1 at vote time, diagnostic fate-adjusted reporting via `/analyze-issues`, and explicit statement that live scoreboards are not retroactively rewritten.


### FINDING_27: `rendering.py` `--competition-notice` prose still promises permanent +1 for accepted OOS
- **Reviewer(s)**: dyn-scoring-contract-docs-output.txt
- **Severity**: important
- **Concern**: The runtime `--competition-notice` prose still promises a permanent **+1** for accepted OOS and **"+1"** in the rubric follow-up, with no provisional or fate-adjusted distinction. The branch updated `skills/shared/reviewer-templates.md` and generated agent prompts, but this alternate emission path was left behind. Code-review launches that use `--competition-notice` therefore still teach the old contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scoring-contract-docs-output.txt: Update the embedded `competition_notice` text to match reviewer-templates: provisional +1 at vote time, `/analyze-issues` fate-adjusted docking for filed OOS only, and no change to live vote tallies. Add or extend a render test that greps for the new wording.


### FINDING_28: `voting-protocol.md` mixes retired exoneration terminology with OOS neutral
- **Reviewer(s)**: dyn-scoring-contract-docs-output.txt
- **Severity**: important
- **Concern**: Line 251 still describes **"exonerated vote pattern"** for OOS neutral rows while the table at lines 255–257 uses **"OOS neutral"**; line 266's OOS Scoreboard example still shows **OOS-Exonerated** even though the main scoreboard at line 210 and live tally headers use **OOS-Neutral**. That blurs the live neutral outcome with retired exoneration terminology right next to new provisional/fate-adjusted language.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scoring-contract-docs-output.txt: Replace "exonerated vote pattern" with "OOS neutral (≥1 YES, not accepted)" in the live-scoring paragraph, and change the OOS Scoreboard example column to **OOS-Neutral** to match `python/plan_review_tally.py` / `python/review_tally.py`.


### FINDING_29: `docs/skills.md` `/combine-issues` entry omits `larch:combined-away` marker contract
- **Reviewer(s)**: dyn-scoring-contract-docs-output.txt
- **Severity**: important
- **Concern**: The `/combine-issues` catalog entry still describes only deduplication and closure, with no mention that `close-sources` writes the `larch:combined-away` marker consumed by `/analyze-issues` fate docking. The skill prose documents that cross-skill contract, but the generated skills catalog does not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scoring-contract-docs-output.txt: Add one sentence to the `/combine-issues` blurb: post-combination `close-sources` comments include the durable `larch:combined-away` marker used by `/analyze-issues` combined-away docking; stale-only `close-stale` must not carry it.


