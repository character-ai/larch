# Review Round 3

- Mode: `diff`
- Accepted findings: 10
- Rejected findings: 0
- Exonerated findings: 11
- Neutral findings: 0

## Accepted Findings

### FINDING_1: **architecture** `docs/run-logs.md:150` — The backward-compat guidance tells miners to distinguish shapes with `has("reviewer_slots")` versus `has("reviewer")`, but the same paragraph admits a third class (“Sparse historical stub rows” with other partial shapes). A literal two-way `has()` branch never handles that third class, so the example is incomplete relative to the stated log reality and can encourage jq that silently skips lines or errors on unexpected envelopes. Additionally, `has("reviewer_slots")` is true even when the value is `null` or not an array, so treating it as proof of v2 before iterating is not mechanically safe. **Suggested fix:** Document a three-way normalization (v2 array, legacy string `reviewer`, else explicit skip/unknown with logging), and use `(has("reviewer_slots") and (.reviewer_slots | type == "array"))` as the v2 discriminator; keep `has("reviewer")` as the legacy path only when v2 is absent, and align the duplicate legacy-contract sentence in `scripts/compose-review-findings.md:31` so both docs show the same jq-shaped recipe.
- **Reviewer**: dyn-schema-compat-output.txt
- **Concern**: - **architecture** `docs/run-logs.md:150` — The backward-compat guidance tells miners to distinguish shapes with `has("reviewer_slots")` versus `has("reviewer")`, but the same paragraph admits a third class (“Sparse historical stub rows” with other partial shapes). A literal two-way `has()` branch never handles that third class, so the example is incomplete relative to the stated log reality and can encourage jq that silently skips lines or errors on unexpected envelopes. Additionally, `has("reviewer_slots")` is true even when the value is `null` or not an array, so treating it as proof of v2 before iterating is not mechanically safe. **Suggested fix:** Document a three-way normalization (v2 array, legacy string `reviewer`, else explicit skip/unknown with logging), and use `(has("reviewer_slots") and (.reviewer_slots | type == "array"))` as the v2 discriminator; keep `has("reviewer")` as the legacy path only when v2 is absent, and align the duplicate legacy-contract sentence in `scripts/compose-review-findings.md:31` so both docs show the same jq-shaped recipe.
- **Suggested revision**: Address the concern above.


### FINDING_12: architecture: skills/review/scripts/review-core.md:1610-1614
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 3 doc lists aggregate before dirty-tree recovery Operators trust the contract for ordering; actual code runs recover_dirty_tree right after collect, before aggregate. Reword Step 3 to match review-core.sh or change code if doc order is canonical.
- **Suggested revision**: Address the concern above.


### FINDING_15: code-quality: skills/review/scripts/collect-findings.sh:371-372
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Implementation plan specified replacing sort -u with cp so duplicate identical TSV rows still reach the LLM aggregator; branch uses awk '!seen[$0]++' which still drops identical full rows before aggregation. Two overlapping collector paths could emit the same title/label/body line twice; with awk they collapse to one pre-aggregator row, so the aggregator never sees the duplicate attribution the plan assumed would still exist. Use cp as planned if aggregator-owned dedup is desired, or keep awk and update plan/docs with explicit rationale for row-level dedup vs aggregator dedup.
- **Suggested revision**: Address the concern above.


### FINDING_18: correctness: skills/review/scripts/aggregate-findings.sh:286-315 scripts/lib-vote-tally.sh:100-112
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Aggregator validation omits uniqueness checks for FINDING headings while split_ballot_to_blocks truncates duplicate ids. LLM emits two ### FINDING_1 blocks; first body is silently dropped when splitting; tallies look sane but merged content and votes refer to wrong prose. Add validation for unique contiguous FINDING ids or teach split_ballot_to_blocks to fail on duplicate ids.
- **Suggested revision**: Address the concern above.


### FINDING_19: correctness: skills/review/scripts/aggregate-findings.sh:331-332
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] In-place redirect overwrites findings.md after validation without an atomic replace. Signal during write disk full or partial write yields truncated or corrupt ballot while voting still runs on that file. Write temp in same tmpdir then atomic mv rename into findings.md.
- **Suggested revision**: Address the concern above.


### FINDING_21: correctness: skills/review/scripts/collect-findings.sh:1565-1567
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Plan item 4 specified `cp` after removing `sort -u`; implementation uses awk line dedup Plan-to-code traceability gap; behavior differs from literal `cp` (duplicate TSV rows). Amend plan/issue or switch to specified `cp` if that was the agreed contract.
- **Suggested revision**: Address the concern above.


### FINDING_23: correctness: skills/review/scripts/tally-code-votes.sh:334-342
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Duplicate comma-separated reviewer labels in merged attribution emit multiple score_rows lines for one finding. LLM or hand-edited merged output can repeat the same slot (e.g. two identical comma tokens); tally-code-votes increments per-row counters so Proposed/Accepted/Rejected/OOS scoreboard cells over-count relative to actual findings. Dedupe slot tokens per finding before appending score rows; optionally reject duplicate tokens in aggregate-findings validation.
- **Suggested revision**: Address the concern above.


### FINDING_24: risk-integration: scripts/lib-vote-tally.sh:36-51 vs scripts/lib-vote-tally.md:38-40
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] lib-vote-tally.sh supports Reviewer(s) forms; lib-vote-tally.md contract still omits them. Operators/readers rely on the .md API summary and may misunderstand which attribution lines tally accepts after aggregation. Update lib-vote-tally.md reviewer attribution section in sync with the code.
- **Suggested revision**: Address the concern above.


### FINDING_3: **correctness** `skills/review/scripts/test-aggregate-findings.sh:1-267` — The regression harness covers `oos_drop_tag` only for a reviewer that exists solely on an OOS input (`cursor-b-output.txt`); it never asserts the shared-slot case where the same reviewer appears on both an in-scope and an OOS-tagged input, so the gap above can ship without CI signal. **Suggested fix:** Add a stubbed merge fixture where both findings list the same slot, the model emits a single untagged in-scope block listing that slot once, and assert `REASON=validation-failed` and an unchanged `findings.md` (or adjust the validator first, then assert pass/fail accordingly).
- **Reviewer**: dyn-oos-invariant-output.txt
- **Concern**: - **correctness** `skills/review/scripts/test-aggregate-findings.sh:1-267` — The regression harness covers `oos_drop_tag` only for a reviewer that exists solely on an OOS input (`cursor-b-output.txt`); it never asserts the shared-slot case where the same reviewer appears on both an in-scope and an OOS-tagged input, so the gap above can ship without CI signal. **Suggested fix:** Add a stubbed merge fixture where both findings list the same slot, the model emits a single untagged in-scope block listing that slot once, and assert `REASON=validation-failed` and an unchanged `findings.md` (or adjust the validator first, then assert pass/fail accordingly).
- **Suggested revision**: Address the concern above.


### FINDING_4: **risk-integration** `skills/review/scripts/aggregate-findings.sh:331-337` — The only successful merge path replaces the live ballot with `awk 1 "$cand" > "$FINDINGS_FILE"`, which opens `findings.md` with truncate-on-open before `awk` finishes copying; any abrupt failure after open (I/O error, `awk` non-zero exit, `SIGKILL`/`SIGPIPE`, full disk) can leave `findings.md` empty or truncated. `skills/review/scripts/review-core.sh:505-512` only treats a non-zero aggregator exit as unexpected and logs it, then `skills/review/scripts/review-core.sh:527-537` still dispatches voters against whatever is on disk, so the “non-fatal fallback preserves the raw ballot” contract is not guaranteed on this branch—only the earlier branches that never reach line 332 are safe. **Suggested fix:** Stage the merged text to a new regular file under the resolved review tmpdir (for example `findings.md.new.$$` or `mktemp` there), run `awk` into that staging file, verify it is non-empty and passes the same validation as today, then atomically replace the ballot with `mv` (same filesystem) so any failure before the final `mv` leaves the original `findings.md` untouched; optionally add an explicit guard that the dispatch output path is not the same resolved path as the ballot before running any in-place consumer logic.
- **Reviewer**: dyn-ballot-mutation-output.txt
- **Concern**: - **risk-integration** `skills/review/scripts/aggregate-findings.sh:331-337` — The only successful merge path replaces the live ballot with `awk 1 "$cand" > "$FINDINGS_FILE"`, which opens `findings.md` with truncate-on-open before `awk` finishes copying; any abrupt failure after open (I/O error, `awk` non-zero exit, `SIGKILL`/`SIGPIPE`, full disk) can leave `findings.md` empty or truncated. `skills/review/scripts/review-core.sh:505-512` only treats a non-zero aggregator exit as unexpected and logs it, then `skills/review/scripts/review-core.sh:527-537` still dispatches voters against whatever is on disk, so the “non-fatal fallback preserves the raw ballot” contract is not guaranteed on this branch—only the earlier branches that never reach line 332 are safe. **Suggested fix:** Stage the merged text to a new regular file under the resolved review tmpdir (for example `findings.md.new.$$` or `mktemp` there), run `awk` into that staging file, verify it is non-empty and passes the same validation as today, then atomically replace the ballot with `mv` (same filesystem) so any failure before the final `mv` leaves the original `findings.md` untouched; optionally add an explicit guard that the dispatch output path is not the same resolved path as the ballot before running any in-place consumer logic.
- **Suggested revision**: Address the concern above.


