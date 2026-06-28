## Goal
Implement issue #5767: [IMPLEMENTING] [py-code-quality] [pkg-payoff] 3/14: Split larch/design/design_lifecycle.py (5,172 LOC).

## Implementation Plan
**Improvement #1 (god-module split).** Part of the post-#4982 packaging-payoff umbrella.

#### Problem
`python/larch/design/design_lifecycle.py` is **5,172 LOC**, a god-module. Packaging (#4982) gave it a home under `larch/design/` but did not split it. Large single modules raise per-edit context and error rate for agents, are merge-conflict hotspots under concurrent runs, and carry grandfathered complexity-baseline debt.

#### Scope
- Split `design_lifecycle.py` into cohesive sibling modules under `python/larch/design/` by responsibility.
- No behavior change. Keep the `python3 python/cli.py` invocation contract and all wire formats.
- Update importers to the new module paths; keep the public surface stable where practical.
- Remove this module's now-obsolete rows from `python/complexity-baseline.json` and any per-file ignores in `python/ruff.toml` the split makes unnecessary.

#### Acceptance
- `design_lifecycle.py` decomposed; no resulting module is itself a new god-module.
- `make py-lint` and `make py-test` green.
- CLI / consumer contract unchanged.
- Complexity-baseline rows for the split functions removed.

#### Out of scope
Behavior changes, API changes, cross-package moves.

#### Dependencies
Independent of the other splits. Blocks the umbrella and the complexity re-tighten capstone (13/14).

## Test plan
(no test plan section in plan-file)
