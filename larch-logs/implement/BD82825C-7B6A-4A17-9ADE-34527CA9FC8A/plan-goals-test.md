## Goal
Implement issue #5792: [IMPLEMENTING] [BUG] audit-runs title helper emits titles >256 chars for large batches → GitHub rejects createIssue (Title too long).

## Implementation Plan
**Summary.** `python/cli.py audit-runs title` builds the report title by listing every audited PR number. For large batches the title exceeds GitHub's 256-char `createIssue` limit and filing fails with `GraphQL: Title is too long (maximum is 256 characters)`.

**Repro.** Implement audit (2026-06-28), scope `last 300 PRs` → 2159-char title → `ISSUE_FAILED=true ISSUE_ERROR=GraphQL: Title is too long`. The default `since last audit` for implement resolved to 1138 PRs (~8.5k-char title), which would always fail. The same-day design audit at 100 PRs / 756 chars filed OK (#5776), so the break is somewhere between ~100 and ~300 PRs.

**Impact.** Any audit with a large backlog — especially the implement `since last audit` default after a hiatus — cannot file its chain-of-history report through the documented path. The large-scope case is exactly when audits matter most.

**Suggested fix.** Cap the title PR enumeration, e.g. `PRs #<first>-#<last> (<count> PRs)`, with the full explicit list living in the `audited_prs` frontmatter (already present). Keep the `[Implement Run Logs Audit … Report]` prefix intact for title-matching / close-priors. Optionally enforce a hard 256-char clamp in `audit-runs title`.

**Note.** Worked around in audit #5789 by filing with a compact 120-char title manually.

**Evidence.** Implement audit report #5789.

## Test plan
(no test plan section in plan-file)
