# scripts/test-implement-fork-env.sh — contract

Offline harness for `scripts/implement-fork-env.sh`. It creates temporary git repositories and checks the happy path, missing-`upstream` abort, parse-failure abort, stdout fork metadata, and atomic caller-env content (`REPO=<fork-repo>` only).
