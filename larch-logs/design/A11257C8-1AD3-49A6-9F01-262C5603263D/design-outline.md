## Proposed Design Outline

### Goals
- Implement the three combined follow-up groups (A docs, B dedup hygiene, C tests) from #3143 as a single SIMPLE-tier cleanup pass.
- Tighten loop dedup so consecutive identical lines inside `## Constraints` (and similarly-prefixed) sections are preserved instead of collapsed.
- Remove the stale `revise.env` allowlist entry and document the loop-vs-Gate-B dedup divergence and legacy single-pass mode reachability.

### Non-goals
- No env flag to gate loop dedup behavior.
- No new code in `revise-plan-with-waterfall.sh` to emit `revise.env`.
- No behavior changes outside the bounded dedup scope and allowlist hygiene.
- No broader generalization of dedup to "identical surrounding context"; the fix is scoped to section-prefix awareness only.

### Approach sketch
- Patch `_run_post_apply_pipeline` Python deduper in `skills/design/scripts/plan-review-loop.sh` to track section headers and skip dedup while inside any section whose heading starts with `## Constraints` (and similarly-prefixed sections — heuristic to be finalized in the plan).
- Drop `revise.env` from the `design_round_revise_artifact_included` case in `scripts/lib-design-round-artifacts.sh` and from the matching enumeration in `scripts/lib-design-round-artifacts.md`.
- Add a docs note in `skills/design/references/plan-review.md` covering (a) the loop dedup vs Gate B dedup divergence and (b) one-line clarity that legacy single-pass mode is reachable only via direct script invocation, not through normal `/design`.
- Add three focused regression tests in `skills/design/scripts/test-plan-review-loop.sh` using existing `LARCH_PLAN_REVIEW_*_SH` stubs: streak convergence, important-finding streak reset, degraded-round streak reset.
- Add a small allowlist-coverage assertion in `scripts/test-lib-design-round-artifacts.sh` to lock in `oos-accepted-design.md` and the absence of `revise.env`.

### Surfaces in scope
- `skills/design/scripts/plan-review-loop.sh` — `_run_post_apply_pipeline` section-aware dedup.
- `scripts/lib-design-round-artifacts.sh` and `scripts/lib-design-round-artifacts.md` — drop `revise.env`.
- `skills/design/references/plan-review.md` — dedup divergence + legacy-mode reachability notes.
- `skills/design/scripts/test-plan-review-loop.sh` — three new harness cases.
- `scripts/test-lib-design-round-artifacts.sh` — allowlist regression assertion.

### Open questions
- None.
