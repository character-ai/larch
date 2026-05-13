# ballot-parse.sh Contract

`skills/shared/scripts/ballot-parse.sh` parses review ballot files with `### FINDING_N:` blocks.

Primary callers: `skills/review/scripts/tally-votes.sh`, `skills/review/scripts/emit-tally.sh`, and test harnesses that need deterministic finding counts.

Stdout is `KEY=value` only: `FINDING_COUNT`, plus per-finding title, concern, and OOS flags. Free-form values are single-line normalized text.

Harness: `skills/shared/scripts/test-ballot-parse.sh`, wired through `make test-ballot-parse`.

Edit in sync with `skills/review/scripts/collect-findings.sh` if the ballot block header or body field names change.
