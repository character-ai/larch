# test-commit-review-fixes.sh

Offline harness covering the Step 7 commit wrapper's default message, usage
failure, and `COMMITTED` / `SHA` output envelope.

Covers `--stage-all` by creating an untracked review-fix file and asserting it appears in `git diff --cached --name-only` after the wrapper runs.
