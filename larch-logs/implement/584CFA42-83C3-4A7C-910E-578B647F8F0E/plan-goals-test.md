## Goal
Implement issue #5775: [IMPLEMENTING] [py-code-quality] [pkg-payoff] 11/14: Split larch/review/plan_review.py (2,872 LOC).

## Implementation Plan
**Improvement #1 (god-module split).** Part of the post-#4982 packaging-payoff umbrella.

#### Problem
`python/larch/review/plan_review.py` is **2,872 LOC**, a god-module. Packaging (#4982) gave it a home under `larch/review/` but did not split it. Large single modules raise per-edit context and error rate for agents, are merge-conflict hotspots under concurrent runs, and carry grandfathered complexity-baseline debt.

#### Scope
- Split `plan_review.py` into cohesive sibling modules under `python/larch/review/` by responsibility.
- No behavior change. Keep the `python3 python/cli.py` invocation contract and all wire formats.
- Update importers to the new module paths; keep the public surface stable where practical.
- Remove this module's now-obsolete rows from `python/complexity-baseline.json` and any per-file ignores in `python/ruff.toml` the split makes unnecessary.

#### Acceptance
- `plan_review.py` decomposed; no resulting module is itself a new god-module.
- `make py-lint` and `make py-test` green.
- CLI / consumer contract unchanged.
- Complexity-baseline rows for the split functions removed.

#### Out of scope
Behavior changes, API changes, cross-package moves.

#### Dependencies
Independent of the other splits. Blocks the umbrella and the complexity re-tighten capstone (13/14).

## Test plan
(no test plan section in plan-file)
