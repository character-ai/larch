# scripts/test-create-pr.sh — contract

Offline harness for `scripts/create-pr.sh`. It uses temporary git repositories plus a PATH-stubbed `gh` binary to assert that `--repo OWNER/REPO` is threaded through every `gh pr view` and `gh pr create` path, including existing-PR title backfill and PR-number fallback. It also verifies malformed `--repo` is rejected before any GitHub call.
