# scripts/test-harnesses.sh — contract

`scripts/test-harnesses.sh` is the parallel runner invoked by the Makefile's `test-harnesses` target. It enumerates harness commands by running `make -n _test-harnesses-list` (the `_test-harnesses-list` target lists every regression harness as a prerequisite — single source of truth for "what counts as a harness"), then runs them with up to `MAX_JOBS` (default 10) concurrent workers. Each worker's stdout+stderr is captured to a tmpfile; output blocks are printed serially in submission order with `===== <cmd> — PASS|FAIL (exit N) =====` headers, never interleaving. Any non-zero harness exit causes the script to exit 1 after all harnesses finish.

`scripts/test-test-harnesses.sh` is its regression test, wired into `make` via the `test-test-harnesses` target which is a prerequisite of `_test-harnesses-list` (so the runner exercises itself).

To add a new harness: define a `test-<name>:` target in `Makefile` whose recipe is `bash <path-to-script>`, then list `test-<name>` as a prerequisite of `_test-harnesses-list`. Both `make test-<name>` (direct) and `make test-harnesses` (parallel via this script) will pick it up.

The runner is bash 3.2 portable (no `wait -n`, no `mapfile`, no associative arrays) so it runs on macOS's stock `/bin/bash`.
