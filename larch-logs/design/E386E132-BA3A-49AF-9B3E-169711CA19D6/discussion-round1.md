## Decision 1: Suppression mechanism
- **Question**: Which mechanism suppresses WARN_PLAN_FILES_UNTOUCHED for conditionally-scoped plan files?
- **Resolution**: Add a new `### MAY_UPDATE: <path>` scope heading. The coverage check excludes MAY_UPDATE paths; other heading consumers still see them. (Issue's preferred Option A.)
- **Source**: user

## Decision 2: PR scope
- **Question**: Fix only the dispatcher, or also update /design authoring + docs in the same PR?
- **Resolution**: Same PR. Update plan-drafting guidance, the reviewer-prompt grammar note, and `docs/issue-anchored-plan.md` so MAY_UPDATE is live and documented.
- **Source**: user

## Decision 3: Exclusion is coverage-only
- **Question**: Exclude MAY_UPDATE from every heading consumer, or only the coverage warning?
- **Resolution**: Only the coverage warning (`WARN_PLAN_FILES_UNTOUCHED`). MAY_UPDATE paths stay visible to `plan scope-paths`, dirty-tree scope, and plan-size counting; those treat MAY_UPDATE as a legitimate candidate path. Only `_explicit_plan_scope_paths` (coverage) excludes it.
- **Source**: codebase (`extract_scope_paths` has 3 callers; only the dispatcher coverage path produces the false positive)

## Decision 4: Backward compatibility
- **Question**: Will existing `### UPDATED:` conditional plans be retroactively re-flagged?
- **Resolution**: No. The warning is computed live during `/implement` Step 2 dispatch, never recomputed from stored run logs. Existing plans that used `### UPDATED:` conditionally keep warning (warn-only, non-gating); they are not broken. MAY_UPDATE is opt-in going forward.
- **Source**: codebase (`implement_dispatch.py:1514-1531`, emitted only during dispatch)

## Decision 5: Hard constraints to preserve
- **Question**: What must not break?
- **Resolution**: Keep `### NEW: / ### UPDATED: / ### REWRITTEN:` parsing byte-stable; MAY_UPDATE is additive. Add MAY_UPDATE to the readability-style Precision Contract list. Per `.claude/rules/launcher-argv-test-coverage.md`, the dispatcher output-grammar change requires same-PR regression coverage in `python/test_implement_dispatch.py`. The `issue_wire` / `plan_quality` changes need same-PR tests in `python/test_issue_wire.py` and `python/test_plan_quality.py`.
- **Source**: codebase + repo rules

Decisions resolved: 5
