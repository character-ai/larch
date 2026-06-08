# retro-sweep-design-logs-phase3d.sh

One-time retroactive sweep applying the Phase 3d cuts (#3721) across all
committed `larch-logs/design/` run directories.

## Purpose

- **Cut 1**: Delete round-level `accepted-plan-findings.md` / `rejected-findings.md`
  from each `plan-review/round-<N>/` directory when the round copy is a
  prefix-subset of the top-level cumulative file (containment check). Keeps
  round copies on mismatch (unexpected non-cumulative content).
- **Cut 2**: Delete GitHub-redundant top-level snapshots: `issue-body.txt`,
  `issue.json`, `architecture-diagram.md`.

Skips any run dir containing `pause-state.txt` (resumable runs).

## Usage

```bash
# Dry-run first (no files removed):
scripts/retro-sweep-design-logs-phase3d.sh --dry-run

# Apply to default larch-logs/design/:
scripts/retro-sweep-design-logs-phase3d.sh

# Apply to a custom root:
scripts/retro-sweep-design-logs-phase3d.sh --design-logs-root /path/to/design
```

## Workflow

Run with `--dry-run` first to audit what would be deleted. Then run without
`--dry-run` to apply. Stage and commit the deletions in a dedicated log-only PR
per `docs/run-logs.md` bulk-edit disclosure.

## Callers

Operator-run once. Not invoked by any skill or hook.
