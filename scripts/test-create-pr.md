# scripts/test-create-pr.sh — contract

Offline harness for `scripts/create-pr.sh`. It uses temporary git repositories plus a PATH-stubbed `gh` binary to assert that `--repo OWNER/REPO` is threaded through every `gh pr view` and `gh pr create` path, including existing-PR title backfill and PR-number fallback. It covers explicit `--base`, detected default-branch base, fallback-to-`main` base selection, and malformed `--repo` rejection before any GitHub call.

Conflict-recovery coverage includes transient `gh pr list` retry success (`create_exists_transient_list`), persistent list failure falling through to the conflict-text URL fallback (`create_exists_persistent_list`), and a no-op `sleep-seconds.sh` stub via `SLEEP_SCRIPT_DIR` so retry tests do not sleep.
