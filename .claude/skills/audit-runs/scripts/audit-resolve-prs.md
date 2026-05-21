# .claude/skills/audit-runs/scripts/audit-resolve-prs.sh — contract

Resolves a verbal description to a concrete PR list for `/audit-runs`.

## Output KV (stdout)

```
IMPLICIT_SINCE_LAST_AUDIT=true|false
PRIOR_REPORT_NUMBER=<N or empty>
PR_LIST=N,M,...
PR_COUNT=<N>
RESOLVED_ECHO=<human-readable confirmation line>
ERROR=<empty when ok; error message when PR_LIST is empty>
```

Normal outcomes exit `0`; caller reads `PR_LIST` and `ERROR`. **Unknown argv** exits `1` with a stderr-only diagnostic (no KV lines on stdout) — treat a missing `ERROR=` line as a hard parse failure, not an empty PR list.

## Supported forms

| Input | Behavior |
|---|---|
| empty / omitted | Implicit `since last audit`; `IMPLICIT_SINCE_LAST_AUDIT=true` |
| `since last audit` | Reads most-recent `audit-report` issue, parses `audited_pr_range.last`, queries PRs merged after that PR's `mergedAt` |
| `last N PRs` | Paginated `gh api repos/{owner}/{repo}/pulls` (merged to `main`), sorted by `merged_at`, then the last *N* PRs by merge time (not `gh pr list` default order) |
| `since <ISO8601>` | Filters PRs with `mergedAt > <ISO>`; `<ISO>` must be a **full instant** (`YYYY-MM-DDThh:mm[:ss][.frac][Z\|±hh:mm]`) — date-only prefixes are rejected |
| `#N` / `PR #N` | Exactly one PR |

## Error cases

- No prior `audit-report` issue → `ERROR=no prior audit-report issue found`
- Malformed frontmatter → `ERROR=prior audit-report #N has malformed or missing frontmatter`
- Zero new PRs → `ERROR=no new PRs merged after prior audit`
- `since <ISO>` not a full instant → `ERROR=since <ISO> must be a full instant ...`
- Unrecognized form → `ERROR=unrecognized verbal description: ...`

## Pagination

Merged-PR discovery pages `gh api repos/{owner}/{repo}/pulls` until a page returns fewer than 100 closed PRs (or zero), up to a high safety cap — not a hard 100-page truncation.

## Edit-in-sync

Update tests in `test-audit-runs.sh` (resolve-prs section) when behavior changes.
