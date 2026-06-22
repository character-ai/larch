## Goal
Implement issue #5003: [IMPLEMENTING] Audit Python codebase for # noqa use and remove as many of these as feasible, fixing lint errors properly, and enabling proper linting.

## Implementation Plan
Mechanizes several criterion-2 items from #4659: enable proper linting, boolean-trap cleanup, and signature-annotation enforcement.

## Goal

Drive down `# noqa` suppressions in `python/`, fixing the underlying issues properly, and un-ignore rule families that should be enforced.

## Current state (at filing)

- ruff runs `select = ["ALL"]` with an ignore list in `python/ruff.toml`.
- Several modules carry `# noqa: FBT001` / `FBT003` (boolean-trap) suppressions: e.g. `agents.py`, `clarify.py`, `review_pipeline.py`, `audit_runs.py`, `review_and_fix.py`, `issue_query.py`, `analyze_issues.py`.
- `FBT002` (boolean default positional arg) and the entire `ANN` family are in the ignore list.

## Specific high-value targets

1. **Boolean-trap cleanup (FBT001/FBT003).** Replace `# noqa: FBT*` sites by converting behavior-selecting bool parameters to enums per **G-Py-3** in #4659 (`do(*, mode=Mode.DELETE)`, not `do(True)`). Leave bools that are genuinely data.
2. **Re-enable `FBT002`** once positional bool defaults are gone.
3. **Enable `ANN001` / `ANN201`** to mechanize signature-annotation presence. Complements the local-typing audit in #5001, which `ANN` does not cover.
4. **General `# noqa` audit.** Remove as many suppressions as feasible, fixing the real finding rather than suppressing. Keep only suppressions with a documented, defensible reason.

## Approach

Tackle per rule family. Each un-ignore lands together with the code fixes that make it pass, so diffs stay reviewable.

## Carve-outs

Suppressions that are legitimately correct (e.g. a documented false positive) stay, but each must carry an inline reason.

## Related

#4659 (G-Py-3, criterion-2), #5001 (local typing), #5002 (keyword-only).

## Acceptance

FBT noqas gone or justified; `FBT002` re-enabled; `ANN001`/`ANN201` enabled; net `# noqa` count down; `make py-lint` and `make py-test` green.

## Test plan
(no test plan section in plan-file)
