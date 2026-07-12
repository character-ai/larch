## Decision 1: Pivot issue scope from a no-op deferral to the root-cause bug fix
- **Question**: Issue #7083 asks to "complete deferred /implement plan work" on `python/tests/support/`, but that path is already fully implemented on main (PR #7085, commit 70193fab5) and its 9 tests pass. How should the design proceed?
- **Resolution**: Pivot #7083 to fix the underlying bug in `python/larch/implement/scope_disposition.py` that spuriously classified the directory firm-path as untouched. The deferred path itself needs no further work.
- **Source**: user

## Decision 2: In-scope surface for the fix
- **Question**: What is the minimal surface that fixes the false "untouched" classification for directory firm-paths?
- **Resolution**: Make plan-path coverage matching credit a firm plan path ending in `/` as touched when any touched path lives beneath that directory. Apply the same rule consistently in both `compute_coverage` (touched/untouched computation, lines ~710-713) and `_coverage_from_mapping` (validation recompute of `expected_untouched_paths`, lines ~842-844), so persisted coverage stays internally consistent. Add a regression test in `python/tests/implement/test_scope_disposition.py`.
- **Source**: user + codebase

## Decision 3: Explicit non-goals
- **Question**: What is out of scope?
- **Resolution**: Do NOT re-touch `python/tests/support/` (already complete). Do NOT add a broader proactive lint/assertion guard (user chose the surgical fix, not "Fix + proactive guard"). Do NOT change exact-match behavior for file (non-directory) firm-paths.
- **Source**: user

## Decision 5: Fix the class — extend to the frozen-fallback sibling
- **Question**: A rejected plan-review finding flagged that `_frozen_fallback_touched_paths` (line 514) applies the identical `path in plan_paths` exact filter, dropping directory-firm-path descendants before `compute_coverage` runs in the frozen-fallback baseline path. Extend the fix to that sibling, or keep it surgical?
- **Resolution**: Extend. Route `_frozen_fallback_touched_paths` through the same shared coverage predicate so directory firm-paths are credited in both the live and frozen-fallback paths (G-Fix-1: fix the class). Keep the `_coverage_from_mapping` predicate usage as well (panel rejected dropping it), so all three sites share one predicate. Add a frozen-fallback regression case.
- **Source**: user

## Decision 4: Hard constraint — coverage self-consistency
- **Question**: What must not break?
- **Resolution**: `load_coverage` re-derives `expected_untouched_paths` via `_coverage_from_mapping` and raises "coverage artifact is internally inconsistent" if `compute_coverage` and `_coverage_from_mapping` disagree; both must use identical directory-aware matching. The coverage fingerprint (over plan_paths/touched_paths/todos_left) must remain deterministic. Directory firm-paths must be normalized consistently so touched/untouched partitioning and the fingerprint agree.
- **Source**: codebase
