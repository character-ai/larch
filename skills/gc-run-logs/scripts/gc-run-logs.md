# gc-run-logs.sh

Age-based retention script for committed larch run-log directories.

## Purpose

Slims or deletes run dirs in `larch-logs/{design,implement,review}/` whose run
date is older than `--older-than DAYS` (default 90). On the non-dry-run path,
creates a dedicated branch, commits the changes, pushes, and creates a log-only
PR for operator review and merge.

## Primary caller

`skills/gc-run-logs/SKILL.md` — invoked directly by the `/gc-run-logs` skill.

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--older-than DAYS` | 90 | Process run dirs older than DAYS days. |
| `--delete` | false | Fully delete qualifying dirs instead of slimming. |
| `--dry-run` | false | Print per-dir plan without making changes or creating a PR. |

## Stdout contract (KEY=value)

| Key | Value |
|-----|-------|
| `DIRS_SCANNED` | Total run dirs examined. |
| `DIRS_QUALIFYING` | Dirs old enough to process. |
| `DIRS_SLIMMED` | Dirs slimmed (non-delete mode). |
| `DIRS_DELETED` | Dirs fully deleted (--delete mode). |
| `DIRS_SKIPPED` | Dirs skipped (guard matched or already slimmed). |
| `BYTES_FREED` | Approximate bytes freed (0 in dry-run). |
| `DRY_RUN` | `true` or `false`. |
| `PR_URL` | PR URL (empty when `--dry-run` or no qualifying dirs). |
| `STATUS` | `ok` or `error`. |

## Invariants

- Refuses to run when the git working tree is dirty.
- Refuses to run when not on the `main` branch.
- Skips dirs with `pause-state.txt` (resumable design sessions).
- Skips dirs already carrying a `gc-slimmed` marker (idempotent).
- Skips dirs with no resolvable run date (warns and continues).
- Run date resolved from `manifest.json::started_at`; falls back to first-commit date from `git log --diff-filter=A`.

## Makefile wiring

None — not registered as a lint or test target. Harness coverage via `make lint` (shellcheck, markdownlint, bash syntax check).

## Edit-in-sync

Changes to the slim keep set or flag surface require updates to `skills/gc-run-logs/SKILL.md` and `docs/run-logs.md` (Retention section) in the same PR.
