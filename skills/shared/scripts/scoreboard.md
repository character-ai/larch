# scoreboard.sh Contract

`skills/shared/scripts/scoreboard.sh` renders a small markdown reviewer scoreboard.

Primary callers: `skills/review/scripts/tally-votes.sh` and `skills/review/scripts/emit-tally.sh`.

The script writes the table to `--output-file` and emits only `SCOREBOARD_FILE=<path>` on stdout.

Harness: `skills/shared/scripts/test-scoreboard.sh`, wired through `make test-scoreboard`.
