## Goal
Implement issue #5170: [IMPLEMENTING] [py-code-quality] Packaging 4/9: move agent launchers and dispatch into larch.agents.

## Implementation Plan
**Problem.** The fixer/reviewer launcher surface is concentrated in `agents.py` (6,179 LOC, the largest module) plus dispatch helpers, all flat. `agents` has 9 importers. The flat layout is why this module grew without a package to split into.

**Proposed change.** Move the agent surface into `larch.agents`: `agents`, `agent_waterfall`, `agent_voters`, `collect_results`, `review_dispatch`. Rewrite all importers to `from larch.agents import ...`. Update the many `cli.py` `_REGISTRY` `agent ...` entries that target these modules. Exact module set is finalized in this child's `/design`.

**Out of scope / don't-touch.** No behavior change. Keep the invocation contract and all wire formats. Pure move plus import rewrites. Do not split `agents.py` internals here (separate concern).

**Acceptance.** Agent modules live under `larch.agents`; importers and registry repointed; `make py-lint` / `make py-test` green; consumer invocations unchanged.

**Effort / risk.** Medium / medium.

**Dependencies.** Blocked by the foundation packaging child (1/9). Tracked under umbrella #4982. Wired via `/block-issue`.

## Test plan
(no test plan section in plan-file)
