# test-lib-implement-round-cap.sh

Harness for `scripts/lib-implement-round-cap.sh`. The primary contract lives in
`scripts/lib-implement-round-cap.md`. Wired into `make lint` via the
`test-lib-implement-round-cap` target.

Run directly:

```bash
scripts/test-lib-implement-round-cap.sh
```

The test verifies the sourced `count_prior_degraded_rounds` function, the
direct-execution `--count-prior-degraded` CLI, usage exits, and that sourcing the
library does not trigger the CLI.
