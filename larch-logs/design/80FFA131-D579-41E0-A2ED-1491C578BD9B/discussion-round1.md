## Decision 1: Registry scope — which roles are centralized
- **Question**: Should the per-role default registry cover all roles (including slot-shaped panel-composition / voter-slot / decompose roles), or only linear waterfall-order roles?
- **Resolution**: All roles in the inventory, including slot-shaped ones (review/plan panel composition, voter slot-to-tool assignment, decompose both-vendors-parallel). Full coverage per the issue's "one canonical default per role" goal.
- **Source**: user

## Decision 2: Behavior preservation — pure refactor
- **Question**: Must the overhaul preserve every role's current default exactly, or may it correct defaults that look wrong?
- **Resolution**: Preserve every role's current default order/assignment EXACTLY. Pure refactor plus regression pins. No role's effective default may change. Any intentional default change is a separate issue. Defaults must be derived from CURRENT code (v52.0.2), not the stale v50.0.2 inventory table in the issue body.
- **Source**: user (constraint); codebase (current-defaults derivation note)

## Decision 3: Env overrides — uniform mechanism, wire existing only
- **Question**: Which roles get an optional env-var override?
- **Resolution**: The registry exposes a uniform optional per-role env-override mechanism, but only the existing knob (LARCH_DESIGN_DRAFTER) stays wired and documented. LARCH_DESIGN_DRAFTER's exact name and semantics are preserved for back-compat. No new per-role env knobs are documented or tested as features now; adding one later is a one-line registry change. No speculative configurability.
- **Source**: user

## Decision 4: Docs sync — lint/test check
- **Question**: How should docs/external-reviewers.md "Roles Across the Workflow" and prose surfaces stay consistent with the registry?
- **Resolution**: Add a lint/test check that asserts the docs role table matches the registry and fails CI on drift. No generation machinery; no reliance on manual diligence alone.
- **Source**: user

## Hard constraints (derived, binding for plan drafting)
- **Pure refactor**: every role's effective dispatch behavior is preserved; the registry is the new single source but encodes today's exact values.
- **Stale inventory**: the issue body's v50.0.2 role/default table is a starting map only. The sh-to-py migration is COMPLETE (all listed .sh dispatch sites are gone). Derive each role's actual current default from the live Python dispatch site, not the issue table. Flag: `config.FIXER_TIER_ORDER` is currently `("claude","codex","cursor")`, which must be captured as-is and verified against the actual selection/availability logic before pinning.
- **Preserve LARCH_DESIGN_DRAFTER**: exact env-var name and behavior unchanged.
- **Regression isolation goal**: pins must be per-role and independent, so a PR that flips role X fails CI if it also perturbs role Y (the #4115 collateral-damage class).
- **Read-only config**: registry is static config; no new runtime state, no new single-runner concerns.

## Deferred to plan drafting (Step 2b) — internal modeling, not user scope
- Registry shape/naming/grammar (extend `python/config.py` vs. a new module/data file).
- Whether `FIXER_TIER_ORDER`'s two consumers (CI-recovery fixer in `ci_monitor.py` vs. rebase-conflict fixer in `rebase.py`) become two independent registry roles or one shared role. Leaning two independent roles to honor the regression-isolation goal; will surface at the outline.
- How slot-shaped roles are modeled (ordered-tier list vs. slot→tool map).
