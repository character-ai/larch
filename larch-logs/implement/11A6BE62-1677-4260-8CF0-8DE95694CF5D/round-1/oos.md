### FINDING_1: **correctness** `skills/shared/voting-protocol.md:59-63` — The branch restores the two-path `classify_result` rule in [`scripts/lib-vote-tally.sh`](scripts/lib-vote-tally.sh) (e.g. `0Y/0N/3E` and `0Y/1N/1E` with `eligible>=2` now label `exonerated`), but the voter-facing “After the acceptance threshold…” bullets still describe the PR #2428 narrow gate (`EXONERATE` only when `YES > 0` and `NO == 0`) and still claim all-exonerate and `0Y/1N/1E` stay `rejected`. That reintroduces the same class of doc-vs-runtime mismatch this work fixes for [`docs/voting-process.md`](docs/voting-process.md) and [`scripts/lib-vote-tally.md`](scripts/lib-vote-tally.md), with higher impact because `voting-protocol.md` is what voting prompts are built from. **Suggested fix:** Rewrite those bullets to match the restored ordering and predicate (`neutral` first, then `exonerate > 0 && (no == 0 || (exonerate >= no && exonerate > yes))` for multi-voter panels), with the same examples as in [`docs/voting-process.md`](docs/voting-process.md) so operators and voters cannot contradict `tally-code-votes.sh` / `tally-plan-review.sh`.
- **Reviewer**: dyn-logic-boundary-output.txt
- **Concern**: - **correctness** `skills/shared/voting-protocol.md:59-63` — The branch restores the two-path `classify_result` rule in [`scripts/lib-vote-tally.sh`](scripts/lib-vote-tally.sh) (e.g. `0Y/0N/3E` and `0Y/1N/1E` with `eligible>=2` now label `exonerated`), but the voter-facing “After the acceptance threshold…” bullets still describe the PR #2428 narrow gate (`EXONERATE` only when `YES > 0` and `NO == 0`) and still claim all-exonerate and `0Y/1N/1E` stay `rejected`. That reintroduces the same class of doc-vs-runtime mismatch this work fixes for [`docs/voting-process.md`](docs/voting-process.md) and [`scripts/lib-vote-tally.md`](scripts/lib-vote-tally.md), with higher impact because `voting-protocol.md` is what voting prompts are built from. **Suggested fix:** Rewrite those bullets to match the restored ordering and predicate (`neutral` first, then `exonerate > 0 && (no == 0 || (exonerate >= no && exonerate > yes))` for multi-voter panels), with the same examples as in [`docs/voting-process.md`](docs/voting-process.md) so operators and voters cannot contradict `tally-code-votes.sh` / `tally-plan-review.sh`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_10: risk-integration: skills/shared/voting-protocol.md:59-63
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Tie-break bullets still document PR #2428 narrow exoneration (YES>0 and NO==0; rejects 0Y/1N/1E and all-exonerate). Voters and tooling reading voting-protocol.md are told tally will reject outcomes that scripts/lib-vote-tally.sh::classify_result now labels exonerated; reintroduces the protocol-vs-runtime mismatch this branch fixed elsewhere. Update voting-protocol.md tie-break list to the two-path rule and examples consistent with docs/voting-process.md and lib-vote-tally.sh.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_11: risk-integration: skills/shared/voting-protocol.md:59-63
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Tie-break prose still documents the narrow YES>0 && NO==0 exoneration rule and rejects 0Y/1N/1E and all-exonerate multi-voter panels. Voter-facing protocol disagrees with restored classify_result and updated docs/voting-process.md so operators see conflicting rules vs tally output for 0Y/0N/3E, 0Y/1N/1E, 1Y/2N/3E, etc. Rewrite the tie-break bullets to the two-path rule and refresh examples to match lib-vote-tally.md.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_2: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-logic-boundary-output.txt
- **Concern**: - **code-quality** `scripts/test-lib-vote-tally.sh:207-212` — The new `grep -Fq` pin is useful against silent reverts but is whitespace- and formatting-sensitive; an equivalent refactor of the `elif (( ... ))` line could fail the harness without changing semantics. **Suggested fix:** If this becomes annoying, replace the substring pin with a small dedicated marker comment in the library or assert via sourcing and a controlled fixture, while keeping coverage of the boundary cases in `assert_eq` rows.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_3: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-logic-boundary-output.txt
- **Concern**: - **correctness** `skills/shared/voting-protocol.md:186-191` — The competition table row “Finding got 0 YES but 1+ EXONERATE → Exonerated” remains a coarse summary: counts like `0Y/2N/1E` can have `1+ EXONERATE` but still classify `rejected` under path 2; this imprecision predates the branch and was not introduced by the diff, but updating the tie-break section may be a good occasion to add a footnote that the scoreboard uses `classify_result`, not that row alone.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_4: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-logic-boundary-output.txt
- **Concern**: - **risk-integration** `larch-logs/implement/11A6BE62-1677-4260-8CF0-8DE95694CF5D/*` — The branch includes a chore commit that adds a full implement-run log tree (manifest, plan markdown, `plan-review-tally.json`, etc.); that is unrelated to tally correctness and may be undesirable noise on the plugin surface depending on your run-log retention policy, but it does not affect the `classify_result` logic itself.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_5: [OUT_OF_SCOPE] risk-integration: skills/shared/voting-protocol.md:72-75
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Protocol says all three /review voters every round; voting-process says Codex omitted round 2+. Operators may mis-estimate panel shape when comparing docs. Fix in a dedicated documentation consistency change (not this PR).
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

