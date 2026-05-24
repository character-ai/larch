# scripts/test-implement-step8-exit3-first-fixer.sh — contract

**Purpose**: offline structural regression for `/implement` Step 8+ Exit 3 when `ship-pr.sh` exits **3** with `BAIL_REASON=first-fixer-non-health` — the autonomous main-agent CI-fix sub-procedure (sentinel + counter cap, fork/repo gates, redacted log capture, explicit `git add`, `git-commit.sh`, `refresh-run-logs.sh`, push, and `ship-pr.sh` re-invocation) documented in `skills/implement/SKILL.md`.

The harness greps `skills/implement/SKILL.md` for required path tokens and runs a small `awk` window over the Step 8+ Exit 3 prose to ensure counter, tool-failure logging, `git add`, commit, refresh, and push steps remain present.

## Wiring

Wired into `make lint` via the `test-implement-step8-exit3-first-fixer` Makefile target and `test-harnesses-14`. Listed in `agent-lint.toml` so agent-lint does not flag the script as dead.

## Edit-in-sync rules

Update this harness when the Exit 3 autonomous sub-step list or sentinel/counter filenames in `skills/implement/SKILL.md` change materially.
