# test-check-main-sync.sh

Regression harness for `scripts/check-main-sync.sh`. Uses sterile git repo pairs (bare remote + local clone with `origin/main`) to cover: in-sync, not-on-main, all-flush-ahead (auto-reset), non-log-ahead (blocked), mixed-ahead (blocked), unknown-flag exit, missing `origin/main` (probe-error / exit 2), and dirty-tree refusal before reset (probe-error / exit 2).

See `scripts/check-main-sync.md` for the primary contract.

Run via `make test-check-main-sync`.
