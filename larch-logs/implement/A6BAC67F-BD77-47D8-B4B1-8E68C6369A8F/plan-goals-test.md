## Goal
Implement issue #6818: [IMPLEMENTING] Shared fixer contracts and tier selection.

## Implementation Plan
## Plan

## Approach

Add shared, importable fixer contracts at the core configuration boundary without changing active lint-fix execution or Step 8 routing.

- Pin `FIXER_LANE_TIMEOUT_SEC` to `1800`.
- Define stable action and failure-reason tokens once in `config.py`.
- Represent tier selection with a frozen `TierSelectResult`.
- Define `attempted_tiers` as membership of tiers that were **dispatched/launched**, regardless of their exit status, including failure or timeout. Tiers skipped solely because their executable is unavailable are never attempted.
- Select the first available, untried tier in configured order, including explicit launch-time availability gating for Claude.
- Distinguish a selected tier from unavailable untried tiers and full exhaustion.
- Derive role budgets from the configured tier count and the shared timeout so each tier can receive a full lane timeout.
- Keep `FIXER_TIER_ORDER`, role membership, role order, model policy, `CI_FIXER_KILL_SWITCH_INLINE_MAX_ATTEMPTS`, lint-fix execution, and Step 8 routing unchanged.

## Files to modify/create

### UPDATED: python/larch/core/config.py

- Add `FIXER_LANE_TIMEOUT_SEC: Final = 1800` near the existing subprocess and CI timeout constants.
- Add stable `FIXER_TIER_ACTION_SELECTED`, `FIXER_TIER_ACTION_UNAVAILABLE`, and `FIXER_TIER_ACTION_EXHAUSTED` tokens.
- Add stable `FIXER_TIER_FAIL_REASON_UNAVAILABLE` and `FIXER_TIER_FAIL_REASON_EXHAUSTED` tokens for non-selected outcomes.
- Build any action or reason token collections from the individual constants rather than repeating string literals.
- Preserve the existing derived `FIXER_TIER_ORDER` compatibility alias and all fixer role definitions unchanged.
- Preserve `CI_FIXER_KILL_SWITCH_INLINE_MAX_ATTEMPTS == 30`.

### UPDATED: python/larch/core/external_defaults.py

- Add a frozen `TierSelectResult` dataclass with explicit fields for the action, selected tier, and failure reason.
- Add `next_untried_tier` beside the existing role and availability resolvers.
- Document in its docstring that `attempted_tiers` contains launched/dispatched tiers regardless of success, failure, or timeout; tiers skipped only for unavailable binaries are excluded.
- Normalize `attempted_tiers` internally to a `frozenset` after validating that every value belongs to the configured role order.
- Resolve the role through `tool_order` so the registry remains the source of fixer membership and order.
- Accept explicit launch-time binary-presence inputs for all supported fixer tools, including `claude_present: bool = True`; default values preserve current callers while allowing consumers to mirror runtime binary discovery.
- Apply `codex_present`, `cursor_present`, and `claude_present` only within tier-selection availability handling. Do not change global `_available()` or `resolve_vendor` behavior in this partition.
- Treat the presence inputs as launch-time executable-found semantics: a tier whose binary is absent is unavailable and is skipped, not marked attempted.
- Iterate configured tiers in role order and select the first tier that is both untried and available.
- Return the stable selected action with the tier and an empty failure reason on success.
- Return the stable unavailable action and reason when configured untried tiers remain but none are currently available, including when Claude is configured but `claude_present` is false.
- Return the stable exhausted action and reason only when every configured tier has already been dispatched, regardless of current availability.
- Reject unknown roles, non-waterfall roles, and invalid tier inputs through the existing `ExternalDefaultError` contract instead of silently inventing an outcome.
- Add `fixer_lane_budget_sec` to derive a role's total bounded budget from `len(tool_order(role_id)) * FIXER_LANE_TIMEOUT_SEC`.
- Keep availability input explicit for tests and later fixer consumers without changing current lint-fix or Step 8 consumers in this partition.

### UPDATED: python/tests/core/test_config.py

- Pin `FIXER_LANE_TIMEOUT_SEC == 1800`.
- Pin each result-action and failure-reason literal so later partitions can import a stable wire contract.
- Verify any aggregate token collections contain the expected individual constants.
- Retain the existing pins for `FIXER_TIER_ORDER` and `CI_FIXER_KILL_SWITCH_INLINE_MAX_ATTEMPTS`.

### UPDATED: python/tests/core/test_external_role_defaults.py

- Test `TierSelectResult` through public helper results.
- Cover deterministic first-tier selection and ordered fallback after one or more tiers have been dispatched.
- Add a failed-or-timed-out first-tier fallback case that confirms a launched tier remains attempted and the next configured available tier is selected.
- Verify duplicate or differently ordered attempted-tier inputs do not change deterministic selection.
- Cover unavailable external tiers, including selection of a later available tier.
- Cover explicit Claude binary gating: with Claude configured but `claude_present=False`, selection must skip Claude and choose a later available configured tier when one exists.
- Cover the unavailable result when untried tiers exist but none are launchable, including a role where external tools are unavailable and `claude_present=False`.
- Cover the exhausted result when all configured tiers were dispatched, regardless of current availability.
- Verify selected results have one configured tier and no failure reason. Verify non-selected results have no tier and the matching stable failure reason.
- Verify availability-skipped tiers are not treated as attempted or as evidence of exhaustion.
- Verify invalid attempted tiers and unsuitable role kinds fail loudly.
- Verify `fixer_lane_budget_sec` equals the configured tier count times `1800` for each fixer waterfall role, including roles with different tier order.
- Retain existing tests that pin fixer membership, order, and the `FIXER_TIER_ORDER` compatibility alias.
- Do not add tests that require changing `implement.lint_fix_coder`; this partition verifies the shared selection contract while preserving active lint-fix behavior.

### UPDATED: docs/configuration-and-permissions.md

- Add a concise sentence in `Fixer model policy` stating that each configured fixer lane has a shared `1800`-second timeout and that the derived role budget reserves that full timeout for every configured tier.
- State the evidence basis without inventing an unrecorded percentile: the committed lane-duration analysis reports Claude lane p90 of `706` seconds and observed maxima of `1636` seconds for Claude and `1752` seconds for Codex, so `1800` seconds covers the observed upper-tail durations while aligning with the existing `1800`-second subprocess and CI wait budgets.
- Do not revise fixer ordering, model descriptions, fallback policy, lint-fix behavior, or Step 8 behavior.

## Edge cases

- An empty attempted-tier set selects the first available configured tier.
- Attempted means a tier was launched, regardless of its exit code, failure, or timeout.
- Attempted tiers may arrive in any order, but configured role order controls selection.
- Unavailable tiers are skipped without being treated as attempted.
- Claude is unavailable to selection when `claude_present=False`, even if generic vendor resolution would otherwise identify Claude.
- A role with untried but unavailable tiers is not exhausted.
- A role becomes exhausted only when every configured tier is present in the dispatched-tier attempted set.
- Invalid or non-configured attempted tier names fail instead of being ignored.
- Budget derivation follows the live role registry, so future membership changes adjust the total without a second literal.

## Failure modes

- Repeated token literals may drift across later dispatch modules. Prevent this by defining and pinning each token in `config.py`.
- Treating unavailable tiers as exhausted may cause premature bailout. Cover both states with separate actions, reasons, and tests.
- Treating a missing Claude executable as available would select a lane that cannot launch. Gate Claude explicitly through `claude_present` in the new selection helper without changing global availability resolution.
- Marking availability-skipped tiers as attempted could falsely exhaust a waterfall. Restrict attempted membership to launched tiers only.
- Iterating caller-provided attempted tiers may make selection nondeterministic. Always iterate the configured role order.
- A fixed total budget may underfund roles if their tier count changes. Derive the total from `tool_order`.
- Broad documentation edits may imply routing changes that this partition does not make. Limit the doc change to the timeout and evidence-basis sentences.

## Testing strategy

- Run focused unit tests:
  - `python3 -m pytest python/tests/core/test_config.py python/tests/core/test_external_role_defaults.py -q`
- Run lint and type checks only for the changed Python files using the repository's documented changed-file workflow.
- Confirm the diff does not modify `python/larch/implement/checks_lint_fix.py`, active lint-fix routing, Step 8 routing, fixer role membership, fixer order, or model policy.
- Confirm the documentation still names the existing fixer models and order unchanged.
- Confirm selector tests cover missing-Claude behavior through the public shared helper while leaving active lint-fix behavior unchanged.

## Acceptance

- Run focused unit tests:
  - `python3 -m pytest python/tests/core/test_config.py python/tests/core/test_external_role_defaults.py -q`
- Run lint and type checks only for the changed Python files using the repository's documented changed-file workflow.
- Confirm the diff does not modify `python/larch/implement/checks_lint_fix.py`, active lint-fix routing, Step 8 routing, fixer role membership, fixer order, or model policy.
- Confirm the documentation still names the existing fixer models and order unchanged.
- Confirm selector tests cover missing-Claude behavior through the public shared helper while leaving active lint-fix behavior unchanged.

diff_added: 134
diff_deleted: 4
mechanical_churn: false
diff_lines: 138

## Test plan
(no test plan section in plan-file)
