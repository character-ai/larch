# scripts/wait-for-reviewers.md — contract

`scripts/wait-for-reviewers.sh` polls the `.done` sentinel files emitted by `scripts/run-external-agent.sh` and reports per-reviewer completion / timeout on stdout in a machine-parseable shape. Stderr carries human-readable progress (dot ticks, per-minute status lines, final summary). The script always exits `0` for normal operation — including the all-timed-out case — so callers must inspect stdout (`DONE <name>: exit=<code>` vs `TIMEOUT <name>`) to drive their own fallback logic. Exit `1` is reserved for usage errors (missing sentinel arguments, bad `--timeout`, bad `WAIT_FOR_REVIEWERS_POLL_INTERVAL`).

## Callers

- `/review` Step 3a (collect-agent-results.sh's caller-side wait). Default `--timeout 1860` matches `run-external-agent.sh`'s 30-minute review timeout plus a 1-minute grace.
- `/design` Step 2a (sketches) and Step 3 (plan review) via the same collector.
- `/implement` does not invoke this script directly — it runs through `/review` and `/design`.

## Timeout (`--timeout`)

Wrapper timeout in seconds. The validator accepts positive integer values and rejects empty, non-numeric, or `0` values with exit `1`.

## Poll interval (`WAIT_FOR_REVIEWERS_POLL_INTERVAL`)

Sentinel-file check cadence. Default `5` seconds for production callers — real reviewers take many minutes, so the 5s noise floor is negligible. Test harnesses that wrap stub binaries via `run-external-agent.sh` (e.g. `scripts/test-check-reviewers.sh`) export `WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05` to avoid paying a 5s sleep per probe when stubs exit in microseconds. The validator accepts positive integer or decimal seconds and rejects `0`, negative, or non-numeric input with exit `1`.

## Stdout contract

- One line per sentinel: `DONE <name>: exit=<code>` if the sentinel materialized within the timeout, `TIMEOUT <name>` otherwise.
- `<name>` is the basename of the sentinel path with `.done` stripped.
- `<code>` is the integer exit code read from the sentinel file, or the literal `unknown` if the file is empty / non-numeric.

## Stderr contract

- Per-poll dot tick (`.`).
- One status line per elapsed minute boundary: `⏳ Waiting: <m>m elapsed, <checks> checks, <found>/<total> done`. Driven by `$SECONDS / 60` (not by iteration count) so the cadence stays minute-based regardless of `WAIT_FOR_REVIEWERS_POLL_INTERVAL`.
- Per-completion line: `✓ <name>: exit=<code>`.
- Final summary: `✓ All <total> reviewer(s) completed in <s>s` or `⚠ <n>/<total> reviewer(s) timed out after <T> seconds`.

## Test coverage

Dedicated harness: `scripts/test-wait-for-reviewers.sh` pins `--timeout 0` / non-numeric / no-value-supplied rejection (exit 1 + stderr) and the `DONE` / `TIMEOUT` stdout grammar; it also covers the collector's wait-passthrough fix from #1188 (collector `--timeout 0` / `abc` exits 1 with no `STATUS=` records). The reviewer-launcher harness `scripts/test-check-reviewers.sh` additionally exercises the wait script end-to-end via PATH-stubbed reviewer binaries with `WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05`.

## Edit-in-sync rules

Changes to the stdout grammar (`DONE <name>: exit=<code>`, `TIMEOUT <name>`) MUST update this file in the same PR and verify all callers (grep for `wait-for-reviewers.sh` across `scripts/`, `skills/`, `.claude/`). Changes to `WAIT_FOR_REVIEWERS_POLL_INTERVAL`'s validator must update the test harnesses listed above so they continue to set a value the validator accepts.
