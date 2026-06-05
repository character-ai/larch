## Decision 1: Scope coverage
- **Question**: Title focuses on the Step 8+ contract (section A), but the body tracks ~15 items across A–F. What does the plan cover?
- **Resolution**: All sections A–F. Close the full tracker in one design.
- **Source**: user

## Decision 2: Structure
- **Question**: One combined design+implementation, or decompose #3446 into per-area issues now?
- **Resolution**: One combined plan → one /implement run. The Step 2b.5 plan-size gate may still offer to split if it grows too large.
- **Source**: user

## Decision 3: Bash driver frozen
- **Question**: Modify bash ship-pr.sh / ship-pr-state.sh, or stay Python-side?
- **Resolution**: Python modules + the `LARCH_SHIP_PR_IMPL=python` branch of SKILL.md + test-implement-structure.sh + docs only. Leave bash ship-pr.sh / ship-pr-state.sh frozen (still the live path pre-Phase-7). Bash gaps I notice become OOS, not edits.
- **Source**: user

## Decision 4: Test coverage depth
- **Question**: How much new test coverage should the plan require?
- **Resolution**: A test for every behavioral change — argparse JSON envelope, in-driver 3.11 guard, redacted INTERNAL_ERROR, quiet-routing parity, RunContext alias-drift guard, XDG_CACHE_HOME allowlists, EXIT_STALL-removal regression — plus the shared RecordingRunner helper.
- **Source**: user

## Decision 5: argparse-failure exit code (B1)
- **Question**: When folding a bad-argv argparse failure into the JSON envelope, which exit code does it carry?
- **Resolution**: INTERNAL_ERROR (exit 1) via the existing catch-all envelope + OUTCOME_EXIT_MAP. `--help` / exit-0 stays plain help text.
- **Source**: user

## Decision 6: EXIT_STALL removal is safe; EXIT_BAIL stays
- **Question**: Is EXIT_STALL truly unused, and EXIT_BAIL truly live?
- **Resolution**: `EXIT_STALL` (config.py:17) has no consumers → remove. `EXIT_BAIL` (config.py:16) is live in report_tokens_cli.py:72,111,121 (+ test) → keep, with a distinguishing comment.
- **Source**: codebase

## Decision 7: pr_view_current removal is safe
- **Question**: Is the bare `pr_view_current` wrapper unused?
- **Resolution**: `pr_view_current` (gh.py:258) has no callers; `pr_view_current_read` (gh.py:238) is wired into recovery at gh.py:264 → remove only the bare wrapper.
- **Source**: codebase

## Decision 8: F is a one-line wiring
- **Question**: Does pr_create support --base?
- **Resolution**: `gh.pr_create` already accepts `base` (gh.py:467,490-491). F = pass `base=` from `ensure_pr` (pr.py:67). Lowest priority, harmless for main-default repos.
- **Source**: codebase

## Decision 9: Honor the issue's exclusion list
- **Question**: Re-file or re-implement the "Excluded" items?
- **Resolution**: No. The "Already fixed in main" set and the cross-tracked items (#3404 conflict handoff [IMPLEMENTING], #3448 test-matrix, #3449 docs/linting row) stay out of this plan. Verify the "already fixed" claims for any file I touch; do not duplicate.
- **Source**: issue

## Decision 10: Preserve the JSON-stdout contract shape
- **Question**: Must the existing ship-result JSON shape be preserved?
- **Resolution**: Yes — the ship-result event, `version_info`, and `"outcome":"STALLED"` shape are pinned by tests and consumed by /implement Step 8+. New behaviors (argparse envelope, redaction, 3.11 guard) must not change the existing happy-path contract bytes.
- **Source**: codebase / constraint

## Decision 11: ship-pr-state.sh is not fully retired
- **Question**: Should the SKILL.md prose say the Python path never reads ship-pr-state.sh?
- **Resolution**: No. exit-6 PHASE budgeting + fork flags legitimately still read ship-pr-state.sh. Section A corrects the over-absolute "don't read ship-pr-state.sh" line; the cutover targets routing / CI-fix / transient / OOS paths (JSON + finalize-state).
- **Source**: issue
