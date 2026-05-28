## Decision 1: Dedup fix direction (B-a)
- **Question**: How should `_run_post_apply_pipeline` dedup be tightened to avoid collapsing intentionally repeated lines?
- **Resolution**: Skip dedup inside `## Constraints` and similarly-prefixed sections only (minimal regex change scoped to those sections). Do NOT introduce a feature flag and do NOT broaden to general context-aware dedup.
- **Source**: user (Step 1c)

## Decision 2: `revise.env` disposition (B-c)
- **Question**: How to resolve the stale `revise.env` allowlist entry that is never written by `revise-plan-with-waterfall.sh`?
- **Resolution**: Remove `revise.env` from the allowlist in `scripts/lib-design-round-artifacts.sh`. Do NOT add new code to emit it.
- **Source**: user (Step 1c)

## Decision 3: Document loop dedup vs Gate B dedup divergence (B-b)
- **Question**: Should the divergence between loop dedup (regex) and Gate B dedup (LLM) be documented in operator-facing docs?
- **Resolution**: Add a short note in `skills/design/references/plan-review.md` explaining that loop dedup is regex-based and weaker than Gate B's LLM-driven dedup; converged/cap-hit outputs may retain semantic duplicates Gate B would have removed.
- **Source**: user (Step 1c)

## Decision 4: Scope coverage — all three groups
- **Question**: Should this design address all three combined sub-issues (A docs, B dedup hygiene, C tests) in one plan?
- **Resolution**: Yes — issue #3143 is an explicit combination of #3139/#3140/#3141; all three groups are in-scope.
- **Source**: codebase (issue body explicitly combined three sub-issues)

## Decision 5: Behavior preservation
- **Question**: Must existing runtime behavior outside the scoped dedup fix remain unchanged?
- **Resolution**: Yes — this is a cleanup design. The only intentional runtime behavior change is the bounded dedup tightening (Decision 1). All other items are docs, allowlist hygiene, and new tests. Existing tests must continue to pass.
- **Source**: codebase (issue body characterizes work as "follow-up cleanup")

## Decision 6: Test additions scope
- **Question**: Should all three regression tests called out in group C be added (streak convergence, important-count streak reset, degraded-round streak reset)?
- **Resolution**: Yes — all three. They drive the loop via existing `LARCH_PLAN_REVIEW_*_SH` stub override hooks and assert `LOOP_STATUS`, `REASON`, `CONVERGENCE_STREAK`, `IMPORTANT_ACCEPTED_COUNT` at exit.
- **Source**: codebase (issue body specifies all three concretely)
