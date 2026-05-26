Partition piece 1 of 5 split from #2677.

**Scope**: `scripts/launch-claude-review.sh`, `scripts/launch-claude-review.md`; add repeatable `--context-files`, containment validation, `--allow-root` forwarding, and role-orthogonality docs.

**Dependencies (from panel)**: none

```
<!-- larch:plan:start -->
## Plan

(needs /design — operator runs `/design` on this issue after partition lands.)

<!-- larch:plan:end -->
```

**Original feature context (excerpt)**:

Title: [DESIGNING] Multi-round plan-review loop + plan revision waterfall (Piece 2b from #2644; multi-round half of #2666 split — needs design)

## Context

This issue is the **multi-round half** of the original #2666 (split per a planning discussion — see closing comment on #2666). #2666 originally bundled two distinct concerns:

- **(a) Refactor** (separate issue): move `/design` Step 3's currently orchestrator-driven single-round flow into a script-managed shape, with no behavior change.
- **(b) Multi-round on top** (this issue): add the loop iteration, plan revision waterfall, convergence semantics, per-round artifact discipline, Voter 1 launcher fix, and the rest of the multi-round mechanics that came out of 4 rounds of review on #2644's monolithic plan.

This issue carries the full multi-round design content originally drafted in #2666. Most of the work below has been validated through 4 review rounds on the monolithic #2644 (see that issue's close comment for the round-by-round data). Round 4 surfaced **2 implementation-level blockers** that this issue must still resolve via `/design`:

1. **R4/FINDING_1** (ALL 10 reviewers): The Voter 1 launch design specified `launch-claude-review.sh --context-files <ballot>`, but the `--context-files` flag does NOT exist on `launch-claude-review.sh`. Resolution options: (a) extend the launcher with `--context-files`, (b) reuse existing `--scope-files` to carry the ballot, (c) compose ballot inline into the prompt file.
2. **R4/FINDING_2** (8 reviewers): The two-pass aggregator design (R3/F9 for OOS round-trip) passed `--findings-file <round-N>/findings-in-scope.md` with `--review-tmpdir <round-N>/agg-in-scope/`, but `aggregate-findings.sh` requires `--findings-file` to be UNDER `--review-tmpdir`. Resolution options: stage findings files inside each `agg-*` directory, or change `aggregate-findings.sh`'s allowed input-root contract.

The plan content below is the **end-of-Round-3 spec from #2666**, retained here for `/design` to refine.

Do NOT add `[DESIGNED]` to this issue's title until `/design` completes.

## Why we're not in design-ready state

By Round 4 of the monolithic review on #2644, acceptance precision had improved (96.3% → 90.5% → 72.7%) but the finding count plateaued (27 → 21 → 22 → 20) — every plan revision exposed new defects in the new spec roughly as fast as it resolved prior ones. The partition into refactor + multi-round + Gate-B-and-docs separates concerns enough that each piece's `/design` can naturally converge.

This issue's `/design` should expect ~2-3 rounds (vs the monolith's 4 that still hadn't converged).

## Plan content (working draft from monolithic Round 3 — `/design` to refine)

​### Summary

Add a bounded multi-round plan-review loop (cap `${LARCH_DESIGN_ROUND_CAP:-5}`) to `/design` Step 3 on top of the refactor's single-pass driver. **Convergence predicate**: two consecutive non-degraded rounds both satisfy `ACCEPTED_COUNT <= ${LARCH_DESIGN_CONVERGENCE_THRESHOLD:-3}` AND `IMPORTANT_ACCEPTED_COUNT == 0` (counting only accepted in-scope `### FINDING_N:` blocks marked `- **Severity**: important`). Between-round revision uses a Codex → Cursor → Claude waterfall emitting LLM-generated diff/patch.

Both HARD and SIMPLE tiers run the new flow; `--trivial` is unchanged. Final-round and convergence-round accepted findings are NEVER auto-applied — they flow to Gate B for user-driven application.

​### Files to modify (sketch — needs `/design`)

​#### Extended: `skills/design/scripts/plan-review-loop.sh` (created in refactor issue)

Extend the single-pass driver into a loop:
- Per-round directory layout: `$DESIGN_TMPDIR/plan-review/round-<N>/`.
- Loop iteration up to `--round-cap "${LARCH_DESIGN_ROUND_CAP:-5}"`.
- Convergence check (two consecutive non-degraded rounds with low accepted + zero important).
- Between-round revision via new `revise-plan-with-waterfall.sh`.
- Zero-findings short-circuit (gated on collector evidence per R4/F7).
- Final cumulative a
