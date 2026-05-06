# scripts/test-cleanup-tmpdir.sh - contract

Regression harness for `scripts/cleanup-tmpdir.sh`'s cleanup audit record. It creates a throwaway `/tmp/cleanup-test-XXXXXX` directory, runs the cleanup helper with `TMPDIR` pointed at a private harness directory, and asserts that the target is removed and exactly one parseable audit line lands in the private `${TMPDIR}/larch-cleanup-audit.log`. The harness scopes its writes to its private `TMPDIR` sandbox and does not assert anything about the real `/tmp/larch-cleanup-audit.log` (which other concurrent processes may legitimately be writing).

Wired through `make test-cleanup-tmpdir`; included in the `test-harnesses-N` shard partition. The primary behavioral contract lives in `scripts/cleanup-tmpdir.md`.
