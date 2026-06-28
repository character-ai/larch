## Goal
Implement issue #5765: [IMPLEMENTING] [py-code-quality] [pkg-payoff] 1/14: Enforce package import-direction layering.

## Implementation Plan
**Improvement #3 (layering enforcement).** Part of the post-#4982 packaging-payoff umbrella.

#### Problem
Packaging (#4982) created package boundaries but nothing enforces import **direction**. Agents can silently introduce cycles or upward dependencies (for example `larch.core` importing `larch.implement`). The umbrella's "make the dependency graph legible" goal is currently aspirational, not enforced.

#### Scope
- Define the allowed inter-package dependency edges (layering contract) for `larch.*`: leaf utils, then `larch.core`, then domain packages, then `larch.cli`.
- Add a deterministic check `python3 python/cli.py lint layering` (AST-based, in the style of the existing `subprocess-via-runner` / `env-via-config-constant` ratchets), or an import-linter contract.
- Baseline current violations with required reasons, the same grandfather pattern as the other ratchets.
- Wire into `make py-lint` and document in `docs/linting.md`.

#### Acceptance
- A new violating cross-package import fails `make py-lint`.
- Existing violations are baselined with reasons; the baseline shrinks as splits land.
- Docs updated.

#### Value (LLM-only repo)
Strong. A deterministic guardrail substitutes for the human architect who would otherwise resist dependency-graph erosion; agents do not resist it by taste.

#### Dependencies
Independent. Blocks the umbrella only.

## Test plan
(no test plan section in plan-file)
