## Goal
Implement issue #3737: [IMPLEMENTING] logs-size-reduction: Phase 3c retroactive sweep — run consolidate-round-sidecars.sh\n\n## Context.

## Implementation Plan
## Context

PR #3734 (Phase 3c of logs-size-reduction) added `scripts/consolidate-round-sidecars.sh` and changed `larch-log.sh write-round` to produce `round-meta.json` for **new** rounds going forward. The ~851 already-committed round directories still carry the old individual sidecar files.

## What to do

Run the retroactive sweep on the committed `larch-logs/` tree and file a dedicated log-only PR:

```bash
# 1. Dry-run first to see what would change
scripts/consolidate-round-sidecars.sh --dry-run

# 2. Apply
scripts/consolidate-round-sidecars.sh

# 3. Commit and push
git add larch-logs/
git commit -m "chore(larch-logs): Phase 3c retroactive sidecar consolidation"
git push
```

Then open a PR titled something like `chore(larch-logs): Phase 3c retroactive sidecar consolidation`. The diff will be large (~5 K file changes) but purely mechanical — all files under `larch-logs/`.

## Expected outcome

- Every `round-N/` dir that had individual sidecars gains `round-meta.json` and loses those 7 files.
- Unique `reviewer-dyn-*.md` archetype definitions land once in `larch-logs/shared/archetypes/<sha256-12>.md`.
- `panel-manifest.ndjson` entries for `dyn-*` slots carry `archetype_ref`.
- Net: ≈ -5 000 files, ≈ -5 MB.

## References

- PR #3734 — Phase 3c code changes
- `scripts/consolidate-round-sidecars.sh` — the sweep script (see its `.md` sibling for full usage)
- `scripts/larch-log.md` — updated write-round contract
- `docs/run-logs.md` — updated round-meta.json schema

## Test plan
(no test plan section in plan-file)
