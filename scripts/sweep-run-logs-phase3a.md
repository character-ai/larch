# sweep-run-logs-phase3a.sh

One-shot retroactive sweep: applies Phase 3a log-size-reduction deletions to committed run dirs.

## Usage

```
scripts/sweep-run-logs-phase3a.sh [--dry-run]
```

Pass `--dry-run` to print what would be removed without touching the index.

## What it deletes

- `plan-goals-test.md` from every run dir (issue body via `manifest.json::issue_number` is canonical).
- `findings.md`, `accepted-findings.md`, `oos.md`, `rejected-findings-full.md` from round dirs where `review-findings-full.jsonl` exists. Legacy rounds without the jsonl are skipped (their markdown is the only copy).

## After running

Stage and commit the deletions as a single "log-only" PR.
`scripts/render-findings-view.sh` reconstructs any dropped view on demand.

## Edit-in-sync

This is a one-off migration script; no ongoing callers. Remove or archive after the sweep PR merges.
