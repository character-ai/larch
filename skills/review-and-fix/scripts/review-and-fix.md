# review-and-fix.sh Contract

`skills/review-and-fix/scripts/review-and-fix.sh` enumerates accepted findings for the internal `/review-and-fix` skill. It validates the accepted findings file, emits each `FINDING_ID`, and writes per-finding structured fixer input by calling `call-fixer.sh`.

Flags:

- `--findings-file FILE`
- `--review-tmpdir DIR`
- `--session-env-path FILE`

Output is `KEY=value` only through `scripts/lib-quiet.sh`:

- `FINDING_ID=<id>` once per accepted finding
- `REVIEW_AND_FIX_STATUS=complete|no-findings`
- `FIX_COUNT=N`
- `FINDING_IDS_FILE=<path>` when findings exist

The script does not apply edits. The `/review-and-fix` prompt wrapper reads each `$REVIEW_TMPDIR/FINDING_N.fixer.env`, validates `PATH_VALID=true`, applies code edits with Edit/Write tools, then records the outcome through `call-fixer.sh --mark-applied` or `--mark-skipped`.

Harness: `skills/review-and-fix/scripts/test-review-and-fix.sh`, wired through `make test-review-and-fix`.
