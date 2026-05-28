# snapshot-plan-round.sh

Write-once plan snapshots and `plan-review-round-cursor.txt` for the HARD-only assessor (`assessor.md`).

Subcommands: `write-original`, `write-after`, `read-cursor`, `write-cursor`. Cursor file must be a single positive decimal integer ≥ 1; malformed values default to `1` with stderr warning.
