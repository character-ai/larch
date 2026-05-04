# skills/research/scripts/test-validate-citations-budget.sh — Contract

Offline budget-exhaustion regression harness for `validate-citations.sh`.
Split from `test-validate-citations.sh` so the real-time sleep scenarios can
run on a separate CI shard from the CPU-bound citation validator scenarios.

## What it pins

| Scenario | Assertion target |
|---|---|
| Darwin budget exhaustion (Test 20, Darwin-only) | hung fake-curl + `--budget-seconds 1` -> exit 0, sidecar present with `UNKNOWN`/`timeout` rows for hung URLs, no surviving fake-curl PIDs after kill loop. Exercises the macOS `set -m` per-PG-kill branch. Linux runners skip; Test 21 covers the Linux no-setsid path. Test 20 runs on developer macOS (current CI is Ubuntu-only). |
| Linux no-setsid budget exhaustion (Test 21, Linux-only, #849) | outer `setsid -w` wraps the validator in its own session; hermetic clean-bin (symlinks excluding `setsid`, including `uname`) makes `command -v setsid` fail inside the validator so the no-setsid branch (`validate-citations.sh:765`) is exercised; hung fake-curl honoring `--max-time` + `--budget-seconds 1` -> exit 0, sidecar present, `UNKNOWN`/`timeout` rows for both hung URLs, no orphan fake-curl PIDs after the shortened `--per-fetch-timeout` window. Runs when `setsid` is available on the runner PATH; otherwise skipped with note. Demonstrably fails if the `__VC_SETSID_DONE` marker gate at `validate-citations.sh:765` is reverted to unconditional `kill -- -$$` (validator gets SIGTERM under outer setsid -> exit 143). Test 21 is exercised by current Ubuntu CI. |

## Test seams

| Var | Effect on `validate-citations.sh` |
|---|---|
| `__VC_FAKE_CURL` | replaces real `curl` with PID-recording fake-curl shims |
| `__VC_LAST_ARGV` | absolute path the fake-curl shim writes argv records to |
| `__VC_SKIP_DNS` | skip real DNS resolution |
| `__VC_STUB_RESOLVE` | `host=ip;host=ip;...` for fake resolution |

## Edit-in-sync

When this harness changes:

1. This `.md` (the contract).
2. `test-validate-citations-budget.sh` (the harness body).
3. `test-validate-citations.sh` / `test-validate-citations.md` when moving
   coverage between the CPU-bound and real-time-bound harnesses.
4. `Makefile` `test-validate-citations-budget` target and shard assignment.
5. `validate-citations.md` § Test harness (the validator contract's mirrored
   summary).

## Wiring

`make lint` invokes this harness via the `test-validate-citations-budget`
target, which is a prerequisite of exactly one `test-harnesses-N:` shard. The
harness exits non-zero on any assertion failure; CI fails the same way.
