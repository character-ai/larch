## Goal
Implement issue #5733: [IMPLEMENTING] [BUG] reviewer-prune ledger all-zero from bare-token join mismatch; /implement round 2 prunes entire panel.

## Implementation Plan
## Summary

The `/implement` reviewer-prune ledger records **all-zero** round-1 reviewer productivity, so the round-2 prune test treats every reviewer combo as unproductive and prunes the entire panel. Round 2 then launches **0 reviewers**. Root cause is a slot-label **join-key mismatch**: the prune recorder keys on the reviewer output **filename** (`...-output.txt`) while the classification attribution tokens are now **bare** slot labels (`cursor-specialist-correctness`), and the shared normalizer does not reconcile the two.

Observed in run `F6070E45` (issue #5642, PR #5724): round 1 ran the full 11-slot panel and accepted 10 findings; round 2 pruned all 11 combos (`round-2/prune-decision.env`: `PANEL_PRUNED_EMPTY=true`, `PRUNED_COUNT=11`).

## Scope

- **`/implement` code review only.** `/design` plan review is **not** affected: its prune join keys on the plan-review label-map human labels (e.g. `Cursor-Arch`), which match the design classification `finding_reviewers` tokens exactly. Verified: every committed design run's ledger populates non-zero and no design run has ever pruned a panel empty.
- Every `/implement` run on **v52.1.4+** that reaches round 2 will prune the panel empty (the bare-token era is universal from v52.1.4). Round 1 still runs (round 1 is never pruned), so round-1 findings are still applied; the round-2+ re-review is silently skipped.

## Root cause (two parts)

**1. The unpatched join (the defect).** `reviewer_prune_record` builds each ledger key from `_output_label(row)` = the suffixed output basename (`cursor-specialist-correctness-output.txt`). `_read_classification_counts` matches that key against the classification `reviewer_slots` tokens via `_normalize_code_label`, which strips `.txt`, `-phase2`, `-phase3`, and `-retry` but **not** `-output`. When the tokens are bare (`cursor-specialist-correctness`), `key not in tokens` is always true, so every count stays `0 0 0 0`. At round 2 (and 3-4), `weighted_accepted - rejected = 0 - 0 <= 0` is true for every combo, so all combos are pruned and the panel is empty.

**2. The token-format flip (the trigger).** PR #5627 (issue #5606, commit `499e2555a`, first released in **v52.1.4**) injected a `_normalize_slot`-derived **bare** reviewer-slot inventory into the aggregator prompt (`_required_reviewer_slots_prompt_section` / `_required_reviewer_slots_prompt_parts` in `python/larch/review/review_aggregate.py`), plus a hard fidelity rule: *"Use only slots from this inventory ... Do not invent, rename, or merge slot names."* The committed `reviewer_slots` is harvested from the aggregator-rewritten `findings.md` `- **Reviewer(s)**:` line, so this prompt change deterministically steers the aggregator LLM to emit **bare** slot labels. Before #5606 the aggregator echoed the raw `-output.txt` filenames most of the time (with occasional self-normalization), so bare tokens appeared only sporadically; #5606 made bare **universal** from v52.1.4 onward.

This is prompt-level steering of the aggregator, not a deterministic code rewrite, which is why pre-#5606 runs were a suffixed/bare mix and post-#5606 runs are uniformly bare.

## Empirical correlation (token form determines the join outcome)

| run | version | classification tokens | round-1 ledger non-zero |
|---|---|---|---|
| E32F4EE4 | 52.1.1 | suffixed | 8/11 (populated) |
| 820CC625 | 52.1.3 | suffixed | 10/13 (populated) |
| 030F84F9 | 52.0.4 | bare | 0/10 (all-zero) |
| 2321D021 | 52.1.4 | bare | 0/9 (all-zero) |
| F6070E45 | 52.1.6 | bare | 0/11 (all-zero) → round-2 panel wiped |

Suffixed → populates; bare → all-zero. No exceptions in the sample.

## Relationship to #5730 (the amplifier)

#5463 moved reviewer-prune activation from round 3 to round 2 with `min_recent=1`, so a single all-zero round-1 ledger now wipes the panel at **round 2** (more runs reach round 2 than round 3, so the failure became visible). #5730 restores round-3 activation. That is a useful blast-radius reduction, but it does **not** fix this defect: an all-zero ledger mis-prunes at whatever round pruning activates. This issue is the real fix.

## Recommended fix (prune side, one line)

Make `_normalize_code_label` strip a trailing `-output` (after its existing `.txt` removal) so both `cursor-specialist-correctness-output.txt` and `cursor-specialist-correctness` canonicalize to `cursor-specialist-correctness`. This reconciles static, dynamic, and `-codex` dynamic slots.

**Why prune-side, not emit-side:**

- The **bare** slot label is the intended post-#5606 form. The aggregator deliberately normalizes; the JSONL `reviewer_slots` and the `orchestrator-aggregator.md` fidelity rules are now bare. Re-suffixing on emit would fight that and require steering an LLM back to filenames (brittle).
- `_normalize_code_label` already exists to canonicalize labels for exactly this join; it merely has a gap. Closing it is surgical.
- A prune-side fix is robust to **both** historical (suffixed) and current (bare) runs; an emit-side "restore the suffix" only helps future runs and leaves bare/historical output unmatched.

## Acceptance criteria

- `reviewer_prune_record` populates non-zero accepted/rejected/total counts for productive round-1 slots in a bare-token `/implement` run (assert via a regression test that feeds bare classification tokens against suffixed manifest output labels).
- A round-2 panel is no longer pruned empty when round 1 was productive.
- Add a `_normalize_code_label` unit test covering `-output`, `-output.txt`, and `-output-ns-retry` forms reconciling to the bare token.

## References

- **Trigger commit**: `499e2555a` (PR #5627, issue #5606), first released in v52.1.4.
- **Failing run**: `F6070E45` (issue #5642, PR #5724) — `round-2/prune-decision.env` `PANEL_PRUNED_EMPTY=true`.
- **Code**: `python/larch/review/review_pipeline.py` (`_normalize_code_label`, `_output_label`, `reviewer_prune_record`, `_read_classification_counts`, `reviewer_prune_filter`); `python/larch/review/review_aggregate.py` (`_required_reviewer_slots_prompt_section`, `_normalize_slot`).
- **Amplifier mitigation**: #5730.

## Test plan
(no test plan section in plan-file)
