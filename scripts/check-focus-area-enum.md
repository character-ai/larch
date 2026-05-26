# scripts/check-focus-area-enum.sh Contract

`scripts/check-focus-area-enum.sh` is the local equivalent for the focus-area
enum assertion embedded in the CI `agent-sync` job.

It checks the canonical reviewer focus-area surfaces for enum text that includes
`security` in both backticked and unquoted prompt forms. It prints GitHub
Actions-style `::error` diagnostics and exits non-zero on drift.

Primary caller: the `agent-sync` Makefile target, which also runs
`scripts/check-generators.sh` and `scripts/check-topology-rule-paths.py`.

Harness: covered indirectly by the `agent-sync` target and by
`scripts/test-ci-failed-jobs.sh` mapping drift coverage.
