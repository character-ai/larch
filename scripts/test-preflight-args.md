# scripts/test-preflight-args.sh — contract

Regression harness for `scripts/preflight.sh`. It creates temporary git repositories with local bare `origin` remotes, then exercises the `--skip-branch-check` and `--skip-clean-check` matrix plus stalled-run sentinel clearing. Wired through `make test-preflight-args`; the primary behavioral contract lives in `scripts/preflight.md`.
