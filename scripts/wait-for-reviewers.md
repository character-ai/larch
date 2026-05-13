# scripts/wait-for-reviewers.md — contract

`scripts/wait-for-reviewers.sh` polls the `.done` sentinel files emitted by `scripts/run-external-agent.sh` and reports per-reviewer completion / timeout on stdout in a machine-parseable shape. Stderr carries human-readable progress (dot ticks, per-minute status lines, final summary). The script always exits `0` for normal operation — including the all-timed-out case — so callers must inspect stdout (`DONE <idx> <basename>: exit=<code>` vs `TIMEOUT <idx> <basename>`) to drive their own fallback logic. Exit `1` is reserved for usage errors (missing sentinel arguments, bad `--timeout`, bad `WAIT_FOR_REVIEWERS_POLL_INTERVAL`).

## Callers

- `/review` Step 3a (collect-agent-results.sh's caller-side wait). Default `--timeout 1860` matches `run-external-agent.sh`'s 30-minute review timeout plus a 1-minute grace.
- `/design` Step 2a (sketches) and Step 3 (plan review) via the same collector.
- `/implement` does not invoke this script directly — it runs through `/review` and `/design`.

## Timeout (`--timeout`)

Wrapper timeout in seconds. The validator accepts positive integer values, normalizes accepted leading-zero positive values as base-10 decimal, and rejects empty, non-numeric, `0`, or zero-valued padded forms such as `00` / `000` with exit `1`.

The polling loop converts this wall-clock timeout into a maximum poll count
from `TIMEOUT` and `WAIT_FOR_REVIEWERS_POLL_INTERVAL`. `$SECONDS` is retained
for progress and summary text, but timeout termination is poll-budget based so
a host suspend does not consume the whole reviewer wait window while the shell
process is asleep.

## Poll interval (`WAIT_FOR_REVIEWERS_POLL_INTERVAL`)

Sentinel-file check cadence. Default `5` seconds for production callers — real reviewers take many minutes, so the 5s noise floor is negligible. Test harnesses that wrap stub binaries via `run-external-agent.sh` (e.g. `scripts/test-check-reviewers.sh`) export `WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05` to avoid paying a 5s sleep per probe when stubs exit in microseconds. The validator accepts positive integer or decimal seconds and rejects `0`, zero-valued padded integer forms such as `00` / `000`, negative, or non-numeric input with exit `1`.

## Stdout contract

- One line per sentinel, in argv order: `DONE <idx> <basename>: exit=<code>` if the sentinel materialized within the timeout, `TIMEOUT <idx> <basename>` otherwise.
- `<idx>` is the 1-based argv position of the sentinel path and is the only stable machine key. Callers MUST key on `<idx>`, not basename.
- `<basename>` is the basename of the sentinel path with `.done` stripped. It is informational only and may collide across directories.
- `<code>` is the integer exit code read from the sentinel file, or the literal `unknown` if the file is empty / non-numeric.

## Stderr contract

- Per-poll dot tick (`.`).
- One status line per elapsed minute boundary: `⏳ Waiting: <m>m elapsed, <checks> checks, <found>/<total> done`. Driven by `$SECONDS / 60` (not by iteration count) so the cadence stays minute-based regardless of `WAIT_FOR_REVIEWERS_POLL_INTERVAL`.
- Per-completion line: `✓ <name>: exit=<code>`.
- Suspend warning: `⚠ suspend detected — iteration took <s>s, not counting toward poll budget` when one poll iteration takes more than 60 seconds. The script decrements the poll counter for that iteration so the long sleep does not exhaust `MAX_POLLS`.
- Final summary: `✓ All <total> reviewer(s) completed in <s>s` or `⚠ <n>/<total> reviewer(s) timed out after <T> seconds`.

## Test coverage

Dedicated harness: `scripts/test-wait-for-reviewers.sh` pins `--timeout 0` / `00` / `000` / non-numeric / no-value-supplied rejection (exit 1 + stderr), `WAIT_FOR_REVIEWERS_POLL_INTERVAL=00` / `000` rejection, the indexed `DONE` / `TIMEOUT` stdout grammar, a duplicate-basename fixture proving indices distinguish otherwise-identical sentinel names, and suspend-delta detection that discounts a long iteration from the poll budget. It also covers the collector's wait-passthrough fix from #1188 (collector `--timeout 0` / `abc` exits 1 with no `STATUS=` records). The reviewer-launcher harness `scripts/test-check-reviewers.sh` additionally exercises the wait script end-to-end via PATH-stubbed reviewer binaries with `WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05`.

## Edit-in-sync rules

Changes to the stdout grammar (`DONE <idx> <basename>: exit=<code>`, `TIMEOUT <idx> <basename>`) MUST update this file in the same PR and verify all callers (grep for `wait-for-reviewers.sh` across `scripts/`, `skills/`, `.claude/`). Changes to `WAIT_FOR_REVIEWERS_POLL_INTERVAL`'s validator must update the test harnesses listed above so they continue to set a value the validator accepts.
