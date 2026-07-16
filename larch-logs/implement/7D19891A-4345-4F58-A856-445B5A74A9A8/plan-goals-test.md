## Goal
Implement issue #7012: [IMPLEMENTING] contract-unification [FEATURE] Legacy-lint burndown onto the engine.

## Implementation Plan
#### Problem

After #6988-#6992 land, the engine hosts three rules while ~40 legacy lint modules in `python/larch/lint/` keep standalone argparse and baseline plumbing — 15 of them with private baseline I/O against sibling `python/*-baseline.json` files. The #6992 adoption ratchet grandfathers them with per-row reasons, which prevents regrowth but does not retire the existing duplication (~10k+ lines of per-module plumbing).

#### Goal

An opportunistic burndown: port the highest-cost legacy modules first (the 15 with private baseline I/O), each port equivalence-tested against pre-port goldens per the #6988 fixture pattern, measured by the lint-engine-adoption baseline shrinking toward zero rows. No behavior changes; committed baseline paths and schemas preserved per the #6989-#6991 precedent.

#### Size

Gradual; potential reduction 3,000-5,000 lines across `python/larch/lint/` as modules drop from 550-900 lines to 100-250.

#### Dependencies

Blocked by #6992 (the ratchet and its baseline are the burndown's measurement instrument).

## Test plan
(no test plan section in plan-file)
