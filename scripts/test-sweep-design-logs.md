# scripts/test-sweep-design-logs.sh — contract

Regression harness for `scripts/sweep-design-logs.sh` (the SessionStart hook
that launches `python3 python/cli.py ship design-log-sweep` as a detached
background process). Wired into `make lint` via the `test-sweep-design-logs`
target in `test-harnesses-7`. The full contract, including the always-exit-0
invariant, skip-when-unavailable behavior, and background spawn/disown
discipline, is owned by `scripts/sweep-design-logs.md`.

Coverage includes: python3 missing (exits 0 silently), cli.py missing (exits 0
silently), normal run (exits 0, no stdout), background spawn (sentinel-based
CLI invocation verification), and source-level spawn contract assertions
(`2>&1 &` background operator and `disown`).
