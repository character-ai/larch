# scripts/local-cleanup.sh — contract

`scripts/local-cleanup.sh` is the post-merge local-tidy-up step invoked by `/implement` Step 14: switch to `main`, fetch + pull latest, then delete the feature branch named via `--branch`. Treats branch deletion failure as non-fatal (the branch may already be gone, e.g. if the operator manually deleted it). Refuses to run with `--branch main` for safety. Outputs `CLEANUP_SUCCESS=true|false`, `CURRENT_BRANCH=<name>`, `BRANCH_DELETED=true|false` so the caller can report partial-success warnings without interrupting the post-merge flow.

After fetching and before pulling, the script checks whether local `main` is ahead of `origin/main` only by prior larch-log flush commits. The cleanup is deliberately narrow: every ahead commit subject must begin with the `chore(larch-logs): flush` prefix and the aggregate diff must stay under `larch-logs/`. When both predicates pass, the script warns on stderr and resets local `main` to `origin/main` so stale prior-run flush commits do not block the pull. Non-flush ahead work is left untouched.

When `git pull origin main` fails and local `main` is ahead of `origin/main`, stderr reports the ahead count and tells the operator to push or reconcile local `main` before retrying; the stdout failure envelope and exit-zero behavior are unchanged.
