# scripts/test-persist-post-plan-keys.sh — contract

Regression harness for `scripts/persist-post-plan-keys.sh`. See the primary contract at `scripts/persist-post-plan-keys.md`.

Covers: argv validation (missing flags, unknown options, invalid `--workflow-path` enum, newline in argument), file checks (missing / empty plan-file, missing session-env), happy paths (SIMPLE / HARD), idempotent re-run replacement, and anchored filter preservation of unrelated keys whose names contain `PLAN_FILE` / `FEATURE_FILE` / `POST_PLAN_WORKFLOW_PATH` substrings.

## Edit-in-sync

Update when adding accept paths, reject paths, validation message text, or exit-code branches to `persist-post-plan-keys.sh`. Per `.claude/rules/launcher-argv-test-coverage.md`, changes to that script's argv surface require same-PR coverage here.
