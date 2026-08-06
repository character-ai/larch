# test-file-failure-report-cross-repo.sh

Offline harness for `file-failure-report-cross-repo.sh`.

The primary contract lives in `scripts/file-failure-report-cross-repo.md`. This harness stubs `gh` through `PATH` and the Rust-owned Tier B validator at the `scripts/larch.sh` boundary. It verifies exact-marker dedup, cross-repo create behavior, Tier B comment safety, fallback statuses, URL normalization, and dry-run no-network behavior.
