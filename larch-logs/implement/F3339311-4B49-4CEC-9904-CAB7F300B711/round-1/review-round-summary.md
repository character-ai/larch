# Review Round 1

- Mode: `diff`
- Accepted findings: 10
- Rejected findings: 0
- Exonerated findings: 0
- Neutral findings: 0

## Accepted Findings

### FINDING_1: **Important** `correctness` `scripts/lib-vote-tally.sh:132` — The new EXON predicate regresses the existing `1 YES / 0 NO / 1 EXONERATE` path. `scripts/test-lib-vote-tally.sh:194` still expects `classify_result 1 0 1 3` to return `exonerated`, but the current code returns `rejected` because `exonerate > yes` is false when both are `1`; I confirmed directly with `source scripts/lib-vote-tally.sh; classify_result 1 0 1 3`. Adjust the condition so it covers the new all-EXON case without dropping the old no-NO mixed YES/EXON case, for example by preserving `no == 0` as an exoneration path or otherwise explicitly handling `1Y/0N/1E`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `scripts/lib-vote-tally.sh:132` — The new EXON predicate regresses the existing `1 YES / 0 NO / 1 EXONERATE` path. `scripts/test-lib-vote-tally.sh:194` still expects `classify_result 1 0 1 3` to return `exonerated`, but the current code returns `rejected` because `exonerate > yes` is false when both are `1`; I confirmed directly with `source scripts/lib-vote-tally.sh; classify_result 1 0 1 3`. Adjust the condition so it covers the new all-EXON case without dropping the old no-NO mixed YES/EXON case, for example by preserving `no == 0` as an exoneration path or otherwise explicitly handling `1Y/0N/1E`. Full harness note: `bash scripts/test-lib-vote-tally.sh` could not start in this sandbox because `mktemp` under the user temp directory was blocked with `Operation not permitted`; the direct classifier check above did run.
- **Suggested revision**: Address the concern above.


### FINDING_10: code-quality: scripts/test-lib-vote-tally.sh:191-202
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] New tests only cover eligible=3; no assertion for 1Y/1E split on a 2-judge quorum. Regression for classify_result 1 0 1 2 can ship without failing the harness. Add assert classify_result 1 0 1 2 expects exonerated.
- **Suggested revision**: Address the concern above.


### FINDING_11: correctness: feature_description scripts/lib-vote-tally.sh:132
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Feature description scopes the bug to all-EXON tallies; implemented condition also changes other (YES,EXON,NO) mixes whenever exonerate>yes. Downstream scoreboard labels change for cases not mentioned in the feature blurb (e.g. 1Y/1E tie) unless explicitly intended. Confirm product intent: minimal all-EXON-only fix vs broader dominance rule; align plan feature text tests and docs with chosen intent.
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: scripts/lib-vote-tally.sh:130-135
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] New exoneration condition uses exonerate > yes so yes==exonerate with no==0 no longer exonerates. classify_result 1 0 1 3 returns rejected but scripts/test-lib-vote-tally.sh:194 still expects exonerated; test harness should fail. Preserve old no==0 exoneration when yes>0 (e.g. OR (yes > 0 && no == 0) under exonerate > 0 && exonerate >= no) or update tests and documented semantics to require exonerate > yes strictly.
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: scripts/lib-vote-tally.sh:132 scripts/test-lib-vote-tally.sh:194
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan verification requires test harness to pass; new predicate matches plan text but conflicts with unchanged expectation for 1Y/0N/1E/3. bash scripts/test-lib-vote-tally.sh fails: 1Y/1E (3 elig) got rejected want exonerated. Narrow exoneration condition to preserve prior 1Y/1E behavior while fixing 0Y/0N/NE, or adopt exonerate>yes as policy and update tests and any voting docs accordingly.
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: scripts/lib-vote-tally.sh:132-133
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Replaced exoneration guard with exonerate > yes, which is false when yes==exonerate==1. 2-judge panel: one YES and one EXONERATE (no NO). classify_result 1 0 1 2 was exonerated; now returns rejected, mis-scoring the finding and contradicting prior tie handling. Preserve old yes>0 exon>0 no==0 disjunct or special-case yes==exonerate with no==0 while still fixing all-EXON 0 YES cases; add test 1 0 1 2.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: implementation_plan (Verification section)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan claims all test-lib-vote-tally harness tests pass. Harness currently fails on 1Y/1E case as above. Verify harness exit 0 before asserting green in the plan or PR description.
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: scripts/lib-vote-tally.sh:132
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] exonerate > yes tightens exoneration vs prior yes>0 && no==0 rule for mixed YES/EXON panels. Real ballots like 1Y/0N/1E on a 3-voter panel flip from exonerated to rejected if tests were the prior contract. If intentional, align tests and operator docs; if not, refine the condition.
- **Suggested revision**: Address the concern above.


### FINDING_2: **[correctness]** [`scripts/lib-vote-tally.sh:130-135`](scripts/lib-vote-tally.sh:130-135) — Replacing `yes > 0 && exonerate > 0 && no == 0` with `exonerate > 0 && exonerate >= no && exonerate > yes` drops every outcome where `no == 0`, `exonerate > 0`, and `yes == exonerate > 0` (e.g. `yes=1`, `no=0`, `exonerate=1`, `eligible=3`): `exonerate > yes` is false, so the function falls through to `rejected` even though the previous branch treated this as `exonerated`. The regression is exercised by the unchanged expectation at [`scripts/test-lib-vote-tally.sh:193-194`](scripts/test-lib-vote-tally.sh:193-194); running `bash scripts/test-lib-vote-tally.sh` reports `FAIL 1Y/1E (3 elig) → exonerated — got rejected want exonerated`. **Suggested fix:** keep the bug fix for all-EXON / zero-YES cases without breaking the old `no == 0` mixed panel, e.g. combine predicates so `no == 0 && exonerate > 0` still maps like the pre-change line, and use the stricter `exonerate >= no && exonerate > yes` only when `no > 0` (or an equivalent disjunction you can prove equivalent to the intended policy).
- **Reviewer**: dyn-voting-logic-output.txt
- **Concern**: - **[correctness]** [`scripts/lib-vote-tally.sh:130-135`](scripts/lib-vote-tally.sh:130-135) — Replacing `yes > 0 && exonerate > 0 && no == 0` with `exonerate > 0 && exonerate >= no && exonerate > yes` drops every outcome where `no == 0`, `exonerate > 0`, and `yes == exonerate > 0` (e.g. `yes=1`, `no=0`, `exonerate=1`, `eligible=3`): `exonerate > yes` is false, so the function falls through to `rejected` even though the previous branch treated this as `exonerated`. The regression is exercised by the unchanged expectation at [`scripts/test-lib-vote-tally.sh:193-194`](scripts/test-lib-vote-tally.sh:193-194); running `bash scripts/test-lib-vote-tally.sh` reports `FAIL 1Y/1E (3 elig) → exonerated — got rejected want exonerated`. **Suggested fix:** keep the bug fix for all-EXON / zero-YES cases without breaking the old `no == 0` mixed panel, e.g. combine predicates so `no == 0 && exonerate > 0` still maps like the pre-change line, and use the stricter `exonerate >= no && exonerate > yes` only when `no > 0` (or an equivalent disjunction you can prove equivalent to the intended policy).
- **Suggested revision**: Address the concern above.


### FINDING_9: code-quality: plan
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Implementation plan states exonerate > yes which conflicts with existing 1Y/1E test expectation. Planner and implementer can ship a failing test/assertion mismatch. Align plan formula with tests (e.g. exonerate >= yes) or document an intentional behavior change and update tests.
- **Suggested revision**: Address the concern above.


