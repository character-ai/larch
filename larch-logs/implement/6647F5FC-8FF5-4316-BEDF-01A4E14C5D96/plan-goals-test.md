## Goal
Implement issue #7083: [IMPLEMENTING] [FOLLOW-UP] Complete deferred /implement plan work.

## Implementation Plan
## Plan

Use one private coverage predicate for live coverage, artifact validation, and frozen-fallback porcelain selection. Preserve raw touched child paths for fallback provenance while mapping coverage to ordered firm plan paths.

Confidence: High. The frozen fallback’s exact pre-filter is directly identified.

## Files to modify/create

### UPDATED: python/larch/implement/scope_disposition.py

- Add a private predicate that treats exact firm paths as covered and, only for firm paths ending in `/`, accepts descendants with that exact prefix.
- Use the predicate in `compute_coverage` to map raw touched files to ordered firm plan paths.
- Use the same predicate in `_coverage_from_mapping` when recomputing untouched paths.
- Apply the predicate in `_frozen_fallback_touched_paths` when selecting porcelain paths relevant to firm plan paths, replacing exact-membership filtering that drops directory descendants.
- Preserve raw porcelain child paths in frozen-fallback provenance and signature inputs; only coverage output maps them back to persisted firm plan-path spelling.
- Preserve deterministic fingerprint behavior and existing committed/porcelain attribution.

### UPDATED: python/tests/implement/test_scope_disposition.py

- Add live-coverage regression coverage for a trailing-slash firm directory with a touched nested file.
- Assert the firm directory appears once in `touched_paths`, is absent from `untouched_paths`, and does not produce a partial disposition.
- Include a non-directory firm path or similarly prefixed sibling to prove descendant matching is limited to trailing-slash directory paths and exact prefixes.
- Write and reload the coverage artifact to exercise `_coverage_from_mapping`, fingerprint validation, and internal consistency.
- Add a frozen-fallback regression that forces symbolic-ref resolution failure and supplies porcelain changes under a trailing-slash firm directory.
- Assert the nested porcelain path is retained for fallback provenance/signature handling while the coverage result records the firm directory path, remains complete, and reloads successfully.

## Edge cases

- An exact touched path remains covered whether or not the firm path ends in `/`.
- A similarly named sibling outside a trailing-slash prefix does not count.
- A descendant does not cover a non-directory firm path.
- Multiple touched descendants credit one firm directory once.
- Frozen fallback applies the same directory-aware selection before coverage mapping, rather than dropping nested porcelain paths through exact plan-path membership.

## Failure modes

- Exact-only frozen-fallback filtering can discard nested porcelain changes before the shared coverage mapper runs, incorrectly leaving a firm directory untouched.
- Persisting mapped firm paths instead of raw fallback child paths would alter provenance and signature semantics.
- Different matching rules across compute, reload, and frozen fallback would make coverage or artifacts internally inconsistent.
- Stripping the trailing slash before matching could credit similarly prefixed siblings.

## Testing strategy

- Run `python3 -m pytest python/tests/implement/test_scope_disposition.py -q`.
- Run changed-file Ruff, Pylint, and Pyright checks for the production module and regression test.
- Do not modify `python/tests/support/` or add a broader lint.

## Acceptance

- Run `python3 -m pytest python/tests/implement/test_scope_disposition.py -q`.
- Run changed-file Ruff, Pylint, and Pyright checks for the production module and regression test.
- Do not modify `python/tests/support/` or add a broader lint.

diff_lines: 70

## Test plan
(no test plan section in plan-file)
