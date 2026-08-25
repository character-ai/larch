# test-resolve-upstream-larch-repo.sh

Offline delegation harness for `resolve-upstream-larch-repo.sh`.

The primary contract lives in `scripts/resolve-upstream-larch-repo.md`. This harness verifies adjacent-root binding, exact `plugin resolve-repository` delegation, failure propagation, and the thin wrapper. Rust integration coverage verifies accepted GitHub metadata forms and fail-closed rejection of missing, non-GitHub, malformed, and newline-bearing repository values.
