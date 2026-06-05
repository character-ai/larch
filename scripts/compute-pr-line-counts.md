# compute-pr-line-counts.sh

Read-only helper that buckets merged PR file line counts from the GitHub PR
files API into **code** (every path outside `larch-logs/`) and **larch logs**
(`larch-logs/`-prefixed paths). Each bucket reports `+additions/-deletions`.

## Usage

```bash
scripts/compute-pr-line-counts.sh --pr-number <N> [--repo <owner/name>]
```

| Arg | Required | Notes |
|-----|----------|-------|
| `--pr-number` | yes | Empty or `0` → skip path (no `gh` call) |
| `--repo` | no | When set, endpoint is `repos/<repo>/pulls/<N>/files`; when empty, `repos/{owner}/{repo}/pulls/<N>/files` so `gh api` expands from the current repository context |

## KV output

| `LINES_STATUS` | Other keys | Exit |
|----------------|------------|------|
| `ok` | `CODE_ADDED`, `CODE_DELETED`, `LOGS_ADDED`, `LOGS_DELETED` (integers, zero when a bucket has no rows) | 0 |
| `skipped` | `REASON=no-pr`, `REASON=invalid-pr-number`, or `REASON=invalid-repo` | 0 |
| `unavailable` | `REASON=gh-failed` | 0 |

Failures are non-fatal: callers treat `unavailable` / `skipped` as “render
`N/A`” and continue. Invalid PR numbers and invalid repo slugs are classified
as skipped because the helper can determine locally that no GitHub request
should be attempted.

## Boundary rule

Only the `larch-logs/` path prefix counts as logs; all other paths (including
renamed targets reported by the API) count as code. Binary files with `0/0`
additions/deletions contribute nothing.

## Caller

`skills/implement/scripts/write-final-report.sh` invokes this helper after
`REPO` and `PR_NUMBER` resolve, skips it entirely when
`REPO_UNAVAILABLE=true`, and forwards the four counters to
`scripts/render-run-summary.sh` when `LINES_STATUS=ok`.

## Harness

Offline regression: `scripts/test-compute-pr-line-counts.sh` (see sibling
`scripts/test-compute-pr-line-counts.md`).
