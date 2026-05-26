## Decision 1: Fix direction
- **Question**: drop-bump-commit.sh already accepts plugin.json+CHANGELOG.md; the warning shows the bump commit ended up CHANGELOG.md-only. Which fix direction?
- **Resolution**: Hybrid — Option 2 (separate-CHANGELOG-commit refactor in sub-procedure step 4a) as primary, Option 1 (gated soft guard in drop-bump-commit.sh) as defense in depth.
- **Source**: user

## Decision 2: Refactor scope across Rebase + Re-bump Sub-procedure callers
- **Question**: Apply the separate-CHANGELOG-commit refactor to ALL sub-procedure callers (step8b, step10, step12 families), or only step8b_rebase?
- **Resolution**: All callers — step8b_rebase, step10_rebase, step10_rebase_then_evaluate, step12_rebase, step12_rebase_then_evaluate, step12_phase4, step8_apply_bump_same_version. Symmetric behavior across the family.
- **Source**: user

## Decision 3: Step 8a inclusion (initial bump CHANGELOG amend)
- **Question**: Does "all callers" include the INITIAL Step 8a path in implement-finalize.sh postbump Phase 2 (first bump after PR creation), or only sub-procedure re-bumps (Step 4a)?
- **Resolution**: YES — include Step 8a. All bump commits in implement's lifecycle stay plugin.json-only; CHANGELOG always lands as a separate commit. Symmetric, easier to reason about.
- **Source**: user

## Decision 4: Existing drop-bump-commit invariant for CHANGELOG-only commits
- **Question**: Existing tests (test-drop-bump-commit.sh Test 4 default-path and Test 15 custom-path) assert CHANGELOG-only commits CANNOT be dropped (DROPPED=false). The Option 1 soft guard conflicts with that. Preserve the invariant?
- **Resolution**: Preserve the invariant. The Option 1 soft guard MUST be gated (e.g., opt-in flag like --allow-changelog-only, OR walk back one more step to confirm the bump commit at FOUND_AT=N is supported by a real plugin.json-touching ancestor). Existing tests 4 / 15 keep passing as default behavior.
- **Source**: user

## Hard constraints (derived from decisions above)
- The legacy plugin.json + CHANGELOG.md amended-bump-commit shape (Test 2 default-path / Test 6, Test 14 custom-path) must keep returning DROPPED=true — backwards compatibility with in-flight branches that already created commits in that shape.
- The existing exit-code contract of drop-bump-commit.sh (0 on all no-op paths with DROPPED=false; 1 only on git error during the destructive step) is unchanged.
- script-md-siblings rule: every modified .sh script needs its sibling .md updated; every contract change in drop-bump-commit must propagate to skills/implement/references/rebase-rebump-subprocedure.md and bump-verification.md.

## Non-goals
- Do NOT investigate or change apply-bump.sh's underlying behavior (the root cause of producing a CHANGELOG-only commit). User selected hybrid, not "investigate root cause first". The design defends against the observed symptom without touching apply-bump.
- Do NOT add a new CHANGELOG-formatting / bullet-composition path; reuse implement-finalize.sh's existing CHANGELOG composition helpers.
- Do NOT modify CI workflows, force-push-gate logic, or ship-pr.sh's resume-phase contract — the fix is upstream of force-push-gate.
