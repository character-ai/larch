# test-file-failure-report-cross-repo.sh

Offline harness for `file-failure-report-cross-repo.sh`.

The primary contract lives in `scripts/file-failure-report-cross-repo.md`. This harness stubs `gh` through `PATH` and the Rust-owned Tier B validator, descriptor, marker lookup, response URL, and request-composition verbs at the `scripts/larch.sh` boundary. It captures the actual create body and comment JSON, then injects pathname replacement, in-place append or truncation, and symlink substitution after descriptor snapshotting. It also verifies exact-marker dedup, Tier B comment safety, fallback statuses, URL normalization, dry-run no-network behavior, and the Rust-owned runtime helper.
