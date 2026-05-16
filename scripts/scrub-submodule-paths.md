# scrub-submodule-paths.sh Contract

`scripts/scrub-submodule-paths.sh` removes accepted review findings that reference checked-out submodule paths before a coder is dispatched to apply fixes.

Flags:

- `--input FILE`: markdown containing `### FINDING_N:` blocks.
- `--output FILE`: destination markdown for non-submodule findings.
- `--log FILE`: audit log for removed findings.

The script discovers submodule roots from `.gitmodules` and `git submodule foreach --quiet 'echo $sm_path'`. An empty submodule list is valid and makes the script copy all findings through.

Output is `KEY=value` only through `scripts/lib-quiet.sh`:

- `SCRUB_COUNT=N`
- `SCRUB_OK=true|false`

On missing or invalid input it emits `SCRUB_OK=false` and exits 2. Output and log parent directories are created when needed.

Primary caller: `skills/review-and-fix/scripts/review-and-fix.sh`, before Codex/Cursor/Claude-subagent fix application.

Harness: `scripts/test-scrub-submodule-paths.sh`.
