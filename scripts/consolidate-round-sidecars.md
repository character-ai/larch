# consolidate-round-sidecars.sh

One-shot retroactive sweep script for the Phase 3c logs-size-reduction series
(issue #3716). Converts existing committed round directories from individual
sidecar files to the consolidated `round-meta.json` format and pools
`reviewer-dyn-*.md` archetype definitions into the content-addressed pool at
`larch-logs/shared/archetypes/<sha256-12>.md`.

## Purpose

Phase 3c changes `larch-log.sh write-round` to produce one `round-meta.json`
per round instead of committing `review-tally.env`, `collector-results.env`,
`collect-agent-results.log`, `review-summary.json`, `coder.env`, and
`coder-*.wrapper.log` individually. This script applies that transformation
retroactively to all already-committed round directories so that the historical
backlog (~851 rounds, ~5 000 files) is consolidated.

## When to run

Run once, after deploying the Phase 3c code changes (`larch-log.sh` updated),
in a dedicated log-only PR. Do not run while any `/implement` or `/review` is
active — it modifies the committed `larch-logs/` tree.

## Usage

```bash
# Dry-run first (see what would change)
scripts/consolidate-round-sidecars.sh --dry-run

# Apply to the default larch-logs/ tree
scripts/consolidate-round-sidecars.sh

# Commit the result
git add larch-logs/
git commit -m "chore(larch-logs): Phase 3c retroactive sidecar consolidation"
```

## Callers

This script is not called by any automated workflow. It is operator-invoked
as a one-time migration step.

## Idempotency

Rounds with an existing `round-meta.json` are skipped. Running the script
multiple times is safe.

## What it does

For each `larch-logs/<skill>/<run-id>/round-N/` directory that lacks
`round-meta.json`:

1. Collects present sidecar files (`review-tally.env`, `collector-results.env`,
   `collect-agent-results.log`, `review-summary.json`, `coder.env`,
   `coder-codex.wrapper.log`, `coder-cursor.wrapper.log`).
2. Composes `round-meta.json` with sections `tally`, `collector`,
   `summary`, `coder`, and `wrapper_logs`. (`collect-agent-results.log` is
   detected and deleted but no longer written into `round-meta.json` — the live
   `larch-log.sh write-round` path dropped `collect_log` from the schema.)
3. Removes the individual sidecar files.
4. Hashes each `reviewer-dyn-*.md` and writes it once to
   `larch-logs/shared/archetypes/<sha256-12>.md` (idempotent).
5. Removes the per-round `reviewer-dyn-*.md` copies.
6. Updates `panel-manifest.ndjson` entries for dynamic slots with
   `archetype_ref: <sha256-12>`.

## Related

- `scripts/larch-log.sh` — `write-round` subcommand (produces round-meta.json
  for new rounds going forward)
- `scripts/larch-log.md` — write-round contract documentation
- `docs/run-logs.md` — round-meta.json schema and archetype pool documentation
- Issue #3716 — Phase 3c design
