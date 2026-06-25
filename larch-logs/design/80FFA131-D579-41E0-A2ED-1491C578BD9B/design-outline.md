## Proposed Design Outline

### Goals
- One canonical Python registry mapping each external-tool role to its default: waterfall tier order, or slot-to-tool assignment.
- Repoint every dispatch site to read its default from the registry, with no effective behavior change.
- Pin each role's default independently in tests, so a PR that flips role X fails CI if it also perturbs role Y.

### Non-goals
- Changing any role's current default order or assignment. Pure refactor; defaults derived from live code, not the stale v50.0.2 issue table.
- Adding new per-role env knobs beyond the existing `LARCH_DESIGN_DRAFTER`.
- Touching dispatch mechanics, vendor launch, or fallback-on-failure behavior.

### Approach sketch
- Add the registry to `python/config.py` as `Final` data (precedent: `FIXER_TIER_ORDER`; guideline G-Cfg-1), with frozen-dataclass entries where the value is composite.
- One resolver returns a role's default and applies the uniform optional per-role env override; only `LARCH_DESIGN_DRAFTER` stays wired.
- Repoint all in-scope sites across `/implement` and `/design` to the resolver; delete the inline literals.
- Add one regression test module that pins every role default independently.
- Add a lint/test asserting `docs/external-reviewers.md` "Roles Across the Workflow" matches the registry.

### Surfaces in scope
- `python/config.py` (registry + resolver), plus the dispatch sites: `python/bootstrap.py`, `python/ci_monitor.py`, `python/rebase.py`, `python/design_lifecycle.py`, `python/plan_review.py`, and the review/voter/aggregator/scout dispatch sites.
- `docs/external-reviewers.md` role table; `brainstorm.md` prose role notes.
- New: a per-role-defaults regression test module and a docs-sync lint.

### Open questions
- Whether `FIXER_TIER_ORDER`'s two consumers (CI-recovery fixer vs. rebase-conflict fixer) become two independent registry roles or stay one shared role. Leaning two, for independent pins.
