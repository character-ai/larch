## Decision 1: Scope of the Codex-first flip
- **Question**: Flip only the three named roles (coder default, CI fixer, merge-resolve fixer), or also sweep other cursor-first waterfall defaults found during design?
- **Resolution**: Flip exactly the three named roles. **Report** any other cursor-first external-tool defaults found during design; do NOT auto-flip them — the user decides.
- **Source**: user

## Decision 2: Part 2 documentation sync
- **Question**: Should Part 2 also update prose docs (e.g. `scripts/ship-pr.md`) that describe the waterfall as "Cursor → Codex → Claude"?
- **Resolution**: Yes — sync affected sibling/canonical docs to the new Codex-first order so they do not describe the wrong behavior.
- **Source**: user

## Decision 3: Terminal fallback tier
- **Question**: Does Claude stay the terminal fallback in all three roles?
- **Resolution**: Yes. New order is `codex → cursor → claude` everywhere; Claude remains last.
- **Source**: issue + codebase

## Decision 4: Explicit override behavior
- **Question**: Does explicit `--coder cursor` still work after the flip?
- **Resolution**: Yes. Only the omitted default changes; `_phase_coder_implicit` runs solely when no `--coder` was passed.
- **Source**: issue

## Decision 5: run_ci_fix_vendor start-tier rotation
- **Question**: Does flipping the CI-fixer default interact with the per-attempt start-tier rotation?
- **Resolution**: Preserve the rotation. `run_ci_fix_vendor` computes `offset=$((start_attempt % 3))` over a base `tiers=(...)` tuple; flip only the base tuple to `(codex cursor claude)`. Rotation and the `first-fixer-non-health` bail (keyed on `first_tier`) keep working, now starting from Codex on attempt 0.
- **Source**: codebase (`scripts/ship-pr.sh:2039`, 2069-2071, 2115-2123)

## Decision 6: Python port parity
- **Question**: Flip the Python port even though it is not wired into the live path yet?
- **Resolution**: Yes, for parity. `python/` is dev/CI-only until Phase 7, but the issue requires parity. Flip `config.FIXER_TIER_ORDER` (its consumers `ci_monitor._available_tiers()` and `rebase.py` derive from it) and update `python/test_config.py`.
- **Source**: AGENTS.md + codebase

## Decision 7: review-and-fix dispatchers out of scope
- **Question**: Are the code-review fixer/dispatchers in scope?
- **Resolution**: No. `_phase_coder_implicit`'s own comment notes "Review/fix dispatchers remain Codex-first" — they are already Codex-first and are not one of the three named roles. Out of scope.
- **Source**: codebase (`scripts/implement-bootstrap.sh:1258`)
