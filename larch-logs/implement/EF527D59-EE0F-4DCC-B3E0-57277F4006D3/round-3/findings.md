### FINDING_1: **architecture** `docs/run-logs.md:150` — The backward-compat guidance tells miners to distinguish shapes with `has("reviewer_slots")` versus `has("reviewer")`, but the same paragraph admits a third class (“Sparse historical stub rows” with other partial shapes). A literal two-way `has()` branch never handles that third class, so the example is incomplete relative to the stated log reality and can encourage jq that silently skips lines or errors on unexpected envelopes. Additionally, `has("reviewer_slots")` is true even when the value is `null` or not an array, so treating it as proof of v2 before iterating is not mechanically safe. **Suggested fix:** Document a three-way normalization (v2 array, legacy string `reviewer`, else explicit skip/unknown with logging), and use `(has("reviewer_slots") and (.reviewer_slots | type == "array"))` as the v2 discriminator; keep `has("reviewer")` as the legacy path only when v2 is absent, and align the duplicate legacy-contract sentence in `scripts/compose-review-findings.md:31` so both docs show the same jq-shaped recipe.
- **Reviewer**: dyn-schema-compat-output.txt
- **Concern**: - **architecture** `docs/run-logs.md:150` — The backward-compat guidance tells miners to distinguish shapes with `has("reviewer_slots")` versus `has("reviewer")`, but the same paragraph admits a third class (“Sparse historical stub rows” with other partial shapes). A literal two-way `has()` branch never handles that third class, so the example is incomplete relative to the stated log reality and can encourage jq that silently skips lines or errors on unexpected envelopes. Additionally, `has("reviewer_slots")` is true even when the value is `null` or not an array, so treating it as proof of v2 before iterating is not mechanically safe. **Suggested fix:** Document a three-way normalization (v2 array, legacy string `reviewer`, else explicit skip/unknown with logging), and use `(has("reviewer_slots") and (.reviewer_slots | type == "array"))` as the v2 discriminator; keep `has("reviewer")` as the legacy path only when v2 is absent, and align the duplicate legacy-contract sentence in `scripts/compose-review-findings.md:31` so both docs show the same jq-shaped recipe.
- **Suggested revision**: Address the concern above.

### FINDING_2: **correctness** `skills/review/scripts/aggregate-findings.sh:258-306` — `only_oos_reviewer_slots` labels a reviewer slot as “OOS-only” using set difference `oos - in_scope`, so any slot that appears on at least one in-scope input block is never treated as OOS-only. If an OOS-tagged input finding shares that slot with an in-scope finding, the LLM can merge everything into a single `### FINDING_N:` heading **without** `[OUT_OF_SCOPE]`, attribute only that shared slot, and still pass validation (no slot in `only_oos`, no missing-slot failure), even though `agents/orchestrator-aggregator.md` requires retaining `[OUT_OF_SCOPE]` when an OOS-tagged source is merged with in-scope text. **Suggested fix:** Track OOS at the finding-block level (or merge provenance), and reject in-scope-tagged merged output whenever any OOS-tagged input block was collapsed into it unless the output heading still carries `[OUT_OF_SCOPE]` (or the OOS input remains a separate `FINDING_N` block), instead of keying this solely on “reviewer appears only on OOS-tagged inputs.”
- **Reviewer**: dyn-oos-invariant-output.txt
- **Concern**: - **correctness** `skills/review/scripts/aggregate-findings.sh:258-306` — `only_oos_reviewer_slots` labels a reviewer slot as “OOS-only” using set difference `oos - in_scope`, so any slot that appears on at least one in-scope input block is never treated as OOS-only. If an OOS-tagged input finding shares that slot with an in-scope finding, the LLM can merge everything into a single `### FINDING_N:` heading **without** `[OUT_OF_SCOPE]`, attribute only that shared slot, and still pass validation (no slot in `only_oos`, no missing-slot failure), even though `agents/orchestrator-aggregator.md` requires retaining `[OUT_OF_SCOPE]` when an OOS-tagged source is merged with in-scope text. **Suggested fix:** Track OOS at the finding-block level (or merge provenance), and reject in-scope-tagged merged output whenever any OOS-tagged input block was collapsed into it unless the output heading still carries `[OUT_OF_SCOPE]` (or the OOS input remains a separate `FINDING_N` block), instead of keying this solely on “reviewer appears only on OOS-tagged inputs.”
- **Suggested revision**: Address the concern above.

### FINDING_3: **correctness** `skills/review/scripts/test-aggregate-findings.sh:1-267` — The regression harness covers `oos_drop_tag` only for a reviewer that exists solely on an OOS input (`cursor-b-output.txt`); it never asserts the shared-slot case where the same reviewer appears on both an in-scope and an OOS-tagged input, so the gap above can ship without CI signal. **Suggested fix:** Add a stubbed merge fixture where both findings list the same slot, the model emits a single untagged in-scope block listing that slot once, and assert `REASON=validation-failed` and an unchanged `findings.md` (or adjust the validator first, then assert pass/fail accordingly).
- **Reviewer**: dyn-oos-invariant-output.txt
- **Concern**: - **correctness** `skills/review/scripts/test-aggregate-findings.sh:1-267` — The regression harness covers `oos_drop_tag` only for a reviewer that exists solely on an OOS input (`cursor-b-output.txt`); it never asserts the shared-slot case where the same reviewer appears on both an in-scope and an OOS-tagged input, so the gap above can ship without CI signal. **Suggested fix:** Add a stubbed merge fixture where both findings list the same slot, the model emits a single untagged in-scope block listing that slot once, and assert `REASON=validation-failed` and an unchanged `findings.md` (or adjust the validator first, then assert pass/fail accordingly).
- **Suggested revision**: Address the concern above.

### FINDING_4: **risk-integration** `skills/review/scripts/aggregate-findings.sh:331-337` — The only successful merge path replaces the live ballot with `awk 1 "$cand" > "$FINDINGS_FILE"`, which opens `findings.md` with truncate-on-open before `awk` finishes copying; any abrupt failure after open (I/O error, `awk` non-zero exit, `SIGKILL`/`SIGPIPE`, full disk) can leave `findings.md` empty or truncated. `skills/review/scripts/review-core.sh:505-512` only treats a non-zero aggregator exit as unexpected and logs it, then `skills/review/scripts/review-core.sh:527-537` still dispatches voters against whatever is on disk, so the “non-fatal fallback preserves the raw ballot” contract is not guaranteed on this branch—only the earlier branches that never reach line 332 are safe. **Suggested fix:** Stage the merged text to a new regular file under the resolved review tmpdir (for example `findings.md.new.$$` or `mktemp` there), run `awk` into that staging file, verify it is non-empty and passes the same validation as today, then atomically replace the ballot with `mv` (same filesystem) so any failure before the final `mv` leaves the original `findings.md` untouched; optionally add an explicit guard that the dispatch output path is not the same resolved path as the ballot before running any in-place consumer logic.
- **Reviewer**: dyn-ballot-mutation-output.txt
- **Concern**: - **risk-integration** `skills/review/scripts/aggregate-findings.sh:331-337` — The only successful merge path replaces the live ballot with `awk 1 "$cand" > "$FINDINGS_FILE"`, which opens `findings.md` with truncate-on-open before `awk` finishes copying; any abrupt failure after open (I/O error, `awk` non-zero exit, `SIGKILL`/`SIGPIPE`, full disk) can leave `findings.md` empty or truncated. `skills/review/scripts/review-core.sh:505-512` only treats a non-zero aggregator exit as unexpected and logs it, then `skills/review/scripts/review-core.sh:527-537` still dispatches voters against whatever is on disk, so the “non-fatal fallback preserves the raw ballot” contract is not guaranteed on this branch—only the earlier branches that never reach line 332 are safe. **Suggested fix:** Stage the merged text to a new regular file under the resolved review tmpdir (for example `findings.md.new.$$` or `mktemp` there), run `awk` into that staging file, verify it is non-empty and passes the same validation as today, then atomically replace the ballot with `mv` (same filesystem) so any failure before the final `mv` leaves the original `findings.md` untouched; optionally add an explicit guard that the dispatch output path is not the same resolved path as the ballot before running any in-place consumer logic.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] In-repo shell consumers of committed `review-findings-full.jsonl` were checked for `.reviewer` / `has("reviewer")`-style access: there are no remaining jq/bash readers of a JSONL `.reviewer` field, and `derive_code_review_tally_from_composed_findings` in `skills/review-and-fix/scripts/review-and-fix.sh:514-527` only filters on `phase`/`outcome`, so the runtime tally path is not coupled to the renamed field.
- **Reviewer**: dyn-schema-compat-output.txt
- **Concern**: - In-repo shell consumers of committed `review-findings-full.jsonl` were checked for `.reviewer` / `has("reviewer")`-style access: there are no remaining jq/bash readers of a JSONL `.reviewer` field, and `derive_code_review_tally_from_composed_findings` in `skills/review-and-fix/scripts/review-and-fix.sh:514-527` only filters on `phase`/`outcome`, so the runtime tally path is not coupled to the renamed field.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Large `larch-logs/implement/EF527D59-…` artifacts appearing in the branch diff are operational run-log noise relative to schema-compat auditing, not a consumer contract bug.
- **Reviewer**: dyn-schema-compat-output.txt
- **Concern**: - Large `larch-logs/implement/EF527D59-…` artifacts appearing in the branch diff are operational run-log noise relative to schema-compat auditing, not a consumer contract bug.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] The `only_oos` / `oos - in_scope` classification for slots that appear **only** on OOS-tagged inputs matches the intended “not only-OOS” behavior when a slot also appears in-scope; the `oos_drop_tag` test correctly exercises rejection for a strictly-OOS-only reviewer on an untagged merged block.
- **Reviewer**: dyn-oos-invariant-output.txt
- **Concern**: - The `only_oos` / `oos - in_scope` classification for slots that appear **only** on OOS-tagged inputs matches the intended “not only-OOS” behavior when a slot also appears in-scope; the `oos_drop_tag` test correctly exercises rejection for a strictly-OOS-only reviewer on an untagged merged block.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] `LARCH_AGGREGATOR_DISABLED=1` forces `INPUT_COUNT=0` / `MERGED_COUNT=0` in `aggregate-findings.sh:112-117`, which misreports real findings counts on the KV stream (behavior adjacent to this script but outside the OOS-invariant scout scope).
- **Reviewer**: dyn-oos-invariant-output.txt
- **Concern**: - `LARCH_AGGREGATOR_DISABLED=1` forces `INPUT_COUNT=0` / `MERGED_COUNT=0` in `aggregate-findings.sh:112-117`, which misreports real findings counts on the KV stream (behavior adjacent to this script but outside the OOS-invariant scout scope).
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] `SECURITY.md:58` still lists only `id`, `phase`, `outcome`, `round_num` as “script-derived” bounded fields and omits the new literal `schema_version` / structured `reviewer_slots` envelope; that is documentation drift around the new batch shape, not a functional regression in the diff itself.
- **Reviewer**: dyn-schema-compat-output.txt
- **Concern**: - `SECURITY.md:58` still lists only `id`, `phase`, `outcome`, `round_num` as “script-derived” bounded fields and omits the new literal `schema_version` / structured `reviewer_slots` envelope; that is documentation drift around the new batch shape, not a functional regression in the diff itself.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] architecture: scripts/lib-vote-tally.sh:100-112
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] split_ballot_to_blocks last-wins on duplicate headings unchanged by this PR. Any pre-existing duplicate-heading ballot could truncate earlier blocks; not introduced here. Future hardening belongs in lib-vote-tally or tally stage if desired globally.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] risk-integration: scripts/test-lib-vote-tally.sh (unchanged in diff)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] No direct unit assertion added for Reviewer(s) spellings on reviewer_for_block despite lib change. Regression in reviewer_for_block could slip until higher-level tally tests fail. Add a small harness case mirroring the new tally-code-votes comma-reviewer fixture.
- **Suggested revision**: Address the concern above.

### FINDING_12: architecture: skills/review/scripts/review-core.md:1610-1614
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 3 doc lists aggregate before dirty-tree recovery Operators trust the contract for ordering; actual code runs recover_dirty_tree right after collect, before aggregate. Reword Step 3 to match review-core.sh or change code if doc order is canonical.
- **Suggested revision**: Address the concern above.

### FINDING_13: code-quality: aggregate-findings.sh:218-321; scripts/lib-vote-tally.sh:36-54; scripts/compose-review-findings.sh:148-162
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Reviewer attribution parsing is triplicated across Python and two awk implementations with slightly different anchoring rules. A future label variant might be accepted by tally/compose but rejected by aggregate validation (or vice versa), causing unnecessary aggregator fallback and unchanged ballots. Document a single canonical grammar shared by all three, or consolidate parsing in one helper sourced by all callers.
- **Suggested revision**: Address the concern above.

### FINDING_14: code-quality: scripts/lib-vote-tally.sh:32-35
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] reviewer_for_block comment omits Reviewer(s) variants already implemented in awk. Readers misread the supported ballot shapes and patch only one layer. Align the comment with compose-review-findings.md / orchestrator-aggregator template bullets.
- **Suggested revision**: Address the concern above.

### FINDING_15: code-quality: skills/review/scripts/collect-findings.sh:371-372
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Implementation plan specified replacing sort -u with cp so duplicate identical TSV rows still reach the LLM aggregator; branch uses awk '!seen[$0]++' which still drops identical full rows before aggregation. Two overlapping collector paths could emit the same title/label/body line twice; with awk they collapse to one pre-aggregator row, so the aggregator never sees the duplicate attribution the plan assumed would still exist. Use cp as planned if aggregator-owned dedup is desired, or keep awk and update plan/docs with explicit rationale for row-level dedup vs aggregator dedup.
- **Suggested revision**: Address the concern above.

### FINDING_16: code-quality: skills/review/scripts/test-review-core.sh:2195-2221
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Collect stub emits FINDINGS_COUNT from TEST_FINDINGS while agg-order fixture writes two findings. Machine KV FINDINGS_COUNT disagrees with ballot for ordering test only. Emit matching FINDINGS_COUNT for the two-block fixture.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: skills/review/scripts/aggregate-findings.sh:112-117; skills/review/scripts/test-aggregate-findings.sh:114-117
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] LARCH_AGGREGATOR_DISABLED reports INPUT_COUNT=0 and MERGED_COUNT=0 even when findings.md has multiple blocks. Downstream telemetry or operator dashboards keyed on INPUT_COUNT may misinterpret disabled runs as zero findings. Count blocks before the disabled early exit (and adjust tests) while keeping AGGREGATED=false REASON=disabled.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: skills/review/scripts/aggregate-findings.sh:286-315 scripts/lib-vote-tally.sh:100-112
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Aggregator validation omits uniqueness checks for FINDING headings while split_ballot_to_blocks truncates duplicate ids. LLM emits two ### FINDING_1 blocks; first body is silently dropped when splitting; tallies look sane but merged content and votes refer to wrong prose. Add validation for unique contiguous FINDING ids or teach split_ballot_to_blocks to fail on duplicate ids.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: skills/review/scripts/aggregate-findings.sh:331-332
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] In-place redirect overwrites findings.md after validation without an atomic replace. Signal during write disk full or partial write yields truncated or corrupt ballot while voting still runs on that file. Write temp in same tmpdir then atomic mv rename into findings.md.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: skills/review/scripts/aggregate-findings.sh:90-137
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] count_finding_blocks uses grep -c with || true; empty stdout makes INPUT_COUNT empty; [[ -lt 2 ]] is true on bash 3.2 so aggregation is skipped as insufficient-input even when findings.md has many FINDING blocks if grep fails without emitting a count line. Unreadable findings.md or grep I/O failure: aggregation pass is silently skipped (wrong REASON) instead of running merge or failing into the documented dispatch/validation warning paths. Use a counter that cannot conflate failure with zero (e.g. awk-based block count with explicit error handling) or validate numeric INPUT_COUNT before the -lt gate and branch to dispatch-failed/validation path when counting fails.
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: skills/review/scripts/collect-findings.sh:1565-1567
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Plan item 4 specified `cp` after removing `sort -u`; implementation uses awk line dedup Plan-to-code traceability gap; behavior differs from literal `cp` (duplicate TSV rows). Amend plan/issue or switch to specified `cp` if that was the agreed contract.
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: skills/review/scripts/collect-findings.sh:365-367
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Plan specified cp tmp to tmp.sorted; implementation uses awk ordered unique-line compaction instead of cp. Differs from written plan; could drop identical duplicate TSV rows that cp would have preserved (likely rare). Match plan (cp) or update the plan/docs to explicitly require ordered unique-line compaction.
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: skills/review/scripts/tally-code-votes.sh:334-342
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Duplicate comma-separated reviewer labels in merged attribution emit multiple score_rows lines for one finding. LLM or hand-edited merged output can repeat the same slot (e.g. two identical comma tokens); tally-code-votes increments per-row counters so Proposed/Accepted/Rejected/OOS scoreboard cells over-count relative to actual findings. Dedupe slot tokens per finding before appending score rows; optionally reject duplicate tokens in aggregate-findings validation.
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: scripts/lib-vote-tally.sh:36-51 vs scripts/lib-vote-tally.md:38-40
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] lib-vote-tally.sh supports Reviewer(s) forms; lib-vote-tally.md contract still omits them. Operators/readers rely on the .md API summary and may misunderstand which attribution lines tally accepts after aggregation. Update lib-vote-tally.md reviewer attribution section in sync with the code.
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: scripts/test-lib-vote-tally.sh:89-131
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] reviewer_for_block lacks a direct **Reviewer(s)** fixture after regex broadening. Regression in lib-vote-tally would only be caught indirectly via tally harnesses. Add one reviewer_for_block case for **Reviewer(s)** spelling.
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: skills/review/scripts/aggregate-findings.sh:112-117
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Disabled aggregator emits INPUT_COUNT/MERGED_COUNT as zero regardless of findings.md size. Telemetry or automation that interprets those KVs as pre-merge ballot cardinality will misreport runs where aggregation is intentionally off. Count FINDING blocks before the disabled early return and emit accurate INPUT_COUNT/MERGED_COUNT while keeping AGGREGATED=false.
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: skills/review/scripts/aggregate-findings.sh:1329-1332
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] jq used under set -e before soft-failure paths; jq missing or failing exits non-zero. Environment without jq or transient jq IO failure surfaces as unexpected aggregate rc in review-core instead of standardized degraded aggregation. Pre-check jq or map jq failure to append_warning and exit 0 with REASON tooling-failed.
- **Suggested revision**: Address the concern above.

### FINDING_28: risk-integration: skills/review/scripts/aggregate-findings.sh:216-225
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No harness for dispatch helper exiting non-zero (distinct from DISPATCH_OK=false). A future change that mishandles non-zero rc from dispatch-with-waterfall could regress without a failing test. Extend stub dispatch to exit non-zero and assert dispatch-failed semantics and unchanged findings.
- **Suggested revision**: Address the concern above.

### FINDING_29: risk-integration: skills/review/scripts/aggregate-findings.sh:307-310
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Validator rejects phantom reviewer slots but tests do not exercise that rejection path. Unknown-slot merge output could stop being caught if validator edits drift. Add stub output with an extra unknown slot and assert validation-failed pass-through.
- **Suggested revision**: Address the concern above.

### FINDING_30: risk-integration: skills/review/scripts/review-core.sh:506-507
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Bash process substitution used for aggregate stderr tee Bash 3.2 (repo portability baseline) rejects `>(…)`; review-core may fail to parse/run before voting. Replace with Bash 3.2–safe stderr capture (plain redirect / post-run cat) without process substitution.
- **Suggested revision**: Address the concern above.

